"""In-memory adapter for Method 2 (2DLMUTF with Method 1 diffusion v3).

No uploaded image or PEM key is written to the application's filesystem.
This is research/demo code, not an audited cryptographic system.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import math
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from chaos_image_encryption.cipher.core import encrypt_array, decrypt_array
from chaos_image_encryption.evaluation.metrics import summarize_triplet

MAX_PIXELS = 2_000_000
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_ZIP_MEMBER_BYTES = 24 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text, validate=True)


def generate_keypair(backend: str) -> tuple[bytes, bytes]:
    if backend == "RSA":
        priv = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    elif backend == "ECC":
        priv = X25519PrivateKey.generate()
    else:
        raise ValueError("Mode hanya RSA atau ECC")
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def get_backend(public_pem: bytes) -> str:
    pub = serialization.load_pem_public_key(public_pem)
    if isinstance(pub, rsa.RSAPublicKey) and pub.key_size >= 3072:
        return "RSA"
    if isinstance(pub, X25519PublicKey):
        return "ECC"
    raise ValueError("Public key harus RSA >=3072-bit atau X25519 (ECC)")


def _make_session(public_pem: bytes) -> tuple[bytes, dict]:
    public = serialization.load_pem_public_key(public_pem)
    if isinstance(public, rsa.RSAPublicKey):
        if public.key_size < 3072:
            raise ValueError("RSA public key harus minimal 3072 bit")
        session = os.urandom(32)
        wrapped = public.encrypt(session, padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(), label=None))
        return session, {"backend":"rsa-3072-oaep-sha256", "wrapped_session_key_b64":_b64(wrapped)}
    if isinstance(public, X25519PublicKey):
        eph = X25519PrivateKey.generate()
        salt = os.urandom(16)
        session = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                       info=b"chaos-image-encryption-v1|x25519-session").derive(eph.exchange(public))
        eph_pub = eph.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        return session, {"backend":"x25519-hkdf-sha256",
                         "ephemeral_public_key_b64":_b64(eph_pub), "ecdh_salt_b64":_b64(salt)}
    raise ValueError("Kunci publik tidak didukung")


def _recover_session(private_pem: bytes, asym: dict) -> bytes:
    private = serialization.load_pem_private_key(private_pem, password=None)
    if asym["backend"] == "rsa-3072-oaep-sha256":
        if not isinstance(private, rsa.RSAPrivateKey):
            raise ValueError("Private key bukan RSA")
        return private.decrypt(_unb64(asym["wrapped_session_key_b64"]),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None))
    if asym["backend"] == "x25519-hkdf-sha256":
        if not isinstance(private, X25519PrivateKey):
            raise ValueError("Private key bukan X25519")
        eph = X25519PublicKey.from_public_bytes(_unb64(asym["ephemeral_public_key_b64"]))
        salt = _unb64(asym["ecdh_salt_b64"])
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                    info=b"chaos-image-encryption-v1|x25519-session").derive(private.exchange(eph))
    raise ValueError("Format backend pada metadata tidak dikenali")


def _check_size(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File terlalu besar. Maksimal 15 MB per file.")


def image_from_bytes(data: bytes) -> tuple[np.ndarray, str]:
    _check_size(data)
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            if not w or not h or w*h > MAX_PIXELS:
                raise ValueError(f"Maksimum {MAX_PIXELS:,} pixel; perkecil gambar lebih dahulu")
            mode = "L" if im.mode == "L" else "RGB"
            normalized = im.copy() if mode == "L" else im.convert("RGB")
            result = np.array(normalized, dtype=np.uint8)
            return result, mode
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("File bukan gambar yang bisa dibuka oleh Pillow") from e


def png_bytes(arr: np.ndarray, mode: str) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), mode=mode).save(buf, format="PNG")
    return buf.getvalue()


def encrypt_image(original: np.ndarray, mode: str, public_pem: bytes) -> tuple[np.ndarray, dict]:
    session, asym = _make_session(public_pem)
    nonce = os.urandom(16)
    cipher = encrypt_array(original, session, nonce, diffusion_version="v3")
    meta = {
        "version":"2.0",
        "method":"2dlmutf-permutation-two-round-nonlinear-diffusion",
        "diffusion_version":"v3",
        "mode":mode,
        "shape":list(original.shape),
        "dtype":"uint8",
        "nonce_b64":_b64(nonce),
        "2dlmutf":{"r1":4.0,"r2":3.8,"burn_in":1000,"epsilon":1e-12},
        "asymmetric":asym,
    }
    return cipher, meta


def decrypt_image(cipher: np.ndarray, mode: str, meta: dict, private_pem: bytes) -> np.ndarray:
    if meta.get("mode") != mode or meta.get("shape") != list(cipher.shape):
        raise ValueError("Bentuk/mode cipher tidak sesuai metadata")
    if meta.get("dtype") != "uint8":
        raise ValueError("Metadata dtype tidak sesuai")
    if meta.get("method") != "2dlmutf-permutation-two-round-nonlinear-diffusion":
        raise ValueError("Metode cipher tidak dikenali")
    nonce = _unb64(meta["nonce_b64"])
    if len(nonce) != 16:
        raise ValueError("Nonce harus 16 byte")
    key = _recover_session(private_pem, meta["asymmetric"])
    version = meta.get("diffusion_version")
    if version != "v3":
        raise ValueError("Metode 2 hanya mendukung diffusion v3")
    return decrypt_array(cipher, key, nonce, diffusion_version=version)


def safe_metrics(original: np.ndarray, cipher: np.ndarray, restored: np.ndarray) -> dict:
    return _json_safe(summarize_triplet(original, cipher, restored))


def _json_safe(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, dict):
        return {k:_json_safe(val) for k,val in v.items()}
    if isinstance(v, (float, np.floating)):
        if math.isinf(float(v)):
            return "inf" if v > 0 else "-inf"
        if math.isnan(float(v)):
            return "nan"
        return float(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, list):
        return [_json_safe(x) for x in v]
    return v


def metadata_bytes(meta: dict) -> bytes:
    return json.dumps(_json_safe(meta), ensure_ascii=False, indent=2).encode("utf-8")


def make_archive(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buf.getvalue()


def encryption_archive(cipher: np.ndarray, mode: str, meta: dict) -> bytes:
    return make_archive({"cipher.png":png_bytes(cipher, mode), "metadata.json":metadata_bytes(meta)})


def extract_encrypted_archive(data: bytes) -> tuple[np.ndarray, str, dict]:
    _check_size(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = {i.filename:i for i in archive.infolist()}
            if "cipher.png" not in members or "metadata.json" not in members:
                raise ValueError("ZIP harus memiliki cipher.png dan metadata.json")
            for name in ("cipher.png", "metadata.json"):
                if members[name].file_size > MAX_ZIP_MEMBER_BYTES:
                    raise ValueError("Isi ZIP terlalu besar")
            cipher_bytes = archive.read("cipher.png")
            meta_bytes = archive.read("metadata.json")
    except (zipfile.BadZipFile, RuntimeError) as e:
        raise ValueError("ZIP tidak valid") from e
    cipher, mode = image_from_bytes(cipher_bytes)
    meta = json.loads(meta_bytes)
    if not isinstance(meta, dict):
        raise ValueError("Format metadata.json salah")
    return cipher, mode, meta


def metrics_csv(m: dict) -> bytes:
    c, ent, corr = m["correctness"], m["entropy"], m["correlation"]
    row = {
        "exact_match":c["exact_match"],
        "mse_original_decrypted":c["mse_original_decrypted"],
        "psnr_original_decrypted_db":c["psnr_original_decrypted_db"],
        "ssim_original_decrypted":c["ssim_original_decrypted"],
        "entropy_original":ent["original"]["overall"],
        "entropy_encrypted":ent["encrypted"]["overall"],
        "corr_h_encrypted":corr["encrypted"]["horizontal"],
        "corr_v_encrypted":corr["encrypted"]["vertical"],
        "corr_d_encrypted":corr["encrypted"]["diagonal"],
    }
    b = io.StringIO()
    writer = csv.DictWriter(b, fieldnames=list(row))
    writer.writeheader(); writer.writerow(row)
    return b.getvalue().encode("utf-8")


def extra_experiments(original: np.ndarray, cipher: np.ndarray, meta: dict, private_pem: bytes) -> dict:
    """Small, repeatable demos. Trials are intentionally limited to one.

    They are NOT a substitute for statistical experiments on many images/seeds.
    """
    from chaos_image_encryption.evaluation.metrics import npcr, uaci, ssim, psnr
    from chaos_image_encryption.attacks.cipher_attacks import salt_pepper_noise, block_erasure, jpeg_recompress

    session = _recover_session(private_pem, meta["asymmetric"])
    nonce = _unb64(meta["nonce_b64"])
    changed = original.copy()
    if changed.ndim == 2:
        changed[changed.shape[0]//2, changed.shape[1]//2] ^= np.uint8(1)
    else:
        changed[changed.shape[0]//2, changed.shape[1]//2, 0] ^= np.uint8(1)
    cipher_changed = encrypt_array(changed, session, nonce, diffusion_version=meta["diffusion_version"])

    wrong_key = bytearray(session)
    wrong_key[0] ^= 1
    cipher_wrong_key = encrypt_array(original, bytes(wrong_key), nonce, diffusion_version=meta["diffusion_version"])
    wrong_key_recovered = decrypt_array(cipher, bytes(wrong_key), nonce, diffusion_version=meta["diffusion_version"])

    attack_inputs = {
        "Noise salt-pepper 0.1%":salt_pepper_noise(cipher, 0.001, seed=42),
        "Block erasure 5%":block_erasure(cipher, 0.05, seed=42),
        "JPEG quality 90":jpeg_recompress(cipher, 90),
    }
    attack_results = []
    for label, attacked in attack_inputs.items():
        recovered = decrypt_array(attacked, session, nonce, diffusion_version=meta["diffusion_version"])
        attack_results.append({
            "Skenario":label,
            "PSNR (dB)":round(psnr(original, recovered), 3),
            "SSIM":round(ssim(original, recovered), 5),
            "Error pixel (%)":round(float(np.mean(original != recovered)*100.0), 4),
        })

    return {
        "differential":{"NPCR (%)":npcr(cipher, cipher_changed), "UACI (%)":uaci(cipher, cipher_changed)},
        "key_sensitivity":{
            "NPCR (%)":npcr(cipher, cipher_wrong_key),
            "UACI (%)":uaci(cipher, cipher_wrong_key),
            "Wrong-key SSIM":ssim(original, wrong_key_recovered),
            "Wrong-key exact":bool(np.array_equal(original, wrong_key_recovered)),
        },
        "attacks":attack_results,
    }
