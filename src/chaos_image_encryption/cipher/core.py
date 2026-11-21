import numpy as np
from ..chaos.logistic_utf import LogisticUTFConfig, generate_logistic_utf, quantize_to_uint8
from ..chaos.kdf import derive_logistic_utf_seed, derive_iv_bytes
from ..chaos.permutation import permutation_from_sequence, permute_pixels, inverse_permute_pixels
from ..chaos.diffusion import diffuse_v2, inverse_diffuse_v2, diffuse_v1, inverse_diffuse_v1, diffuse_v3, inverse_diffuse_v3

CFG = LogisticUTFConfig(r1=4.0, r2=3.8, burn_in=1000)
DEFAULT_DIFFUSION_VERSION = "v3"


def _validate(arr):
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        raise ValueError("only uint8 input is supported")
    if arr.ndim == 2 or (arr.ndim == 3 and arr.shape[2] == 3):
        return arr
    raise ValueError("only L or RGB images are supported")


def _seq(session_key, nonce, shape, domain, length):
    x0, y0 = derive_logistic_utf_seed(session_key, nonce, shape, domain)
    return generate_logistic_utf(x0, y0, length, CFG)


def _diffusion_functions(version: str):
    if version == "v3":
        return diffuse_v3, inverse_diffuse_v3
    if version == "v2":
        return diffuse_v2, inverse_diffuse_v2
    if version == "v1":
        return diffuse_v1, inverse_diffuse_v1
    raise ValueError(f"unsupported diffusion version: {version}")


def encrypt_array(image, session_key: bytes, nonce: bytes, *, diffusion_version: str = DEFAULT_DIFFUSION_VERSION):
    arr = _validate(image)
    shape = tuple(int(v) for v in arr.shape)
    pixels = arr.shape[0] * arr.shape[1]
    nbytes = arr.size
    xp, _ = _seq(session_key, nonce, shape, b"permutation", pixels)
    perm = permutation_from_sequence(xp)
    p = permute_pixels(arr, perm)
    x1, _ = _seq(session_key, nonce, shape, b"diffusion-1", nbytes)
    _, y2 = _seq(session_key, nonce, shape, b"diffusion-2", nbytes)
    k1, k2 = quantize_to_uint8(x1), quantize_to_uint8(y2)
    iv1, iv2 = derive_iv_bytes(session_key, nonce, shape)
    enc, _ = _diffusion_functions(diffusion_version)
    return enc(p.reshape(-1), k1, k2, iv1, iv2).reshape(arr.shape)


def decrypt_array(cipher, session_key: bytes, nonce: bytes, *, diffusion_version: str = DEFAULT_DIFFUSION_VERSION):
    arr = _validate(cipher)
    shape = tuple(int(v) for v in arr.shape)
    pixels = arr.shape[0] * arr.shape[1]
    nbytes = arr.size
    x1, _ = _seq(session_key, nonce, shape, b"diffusion-1", nbytes)
    _, y2 = _seq(session_key, nonce, shape, b"diffusion-2", nbytes)
    k1, k2 = quantize_to_uint8(x1), quantize_to_uint8(y2)
    iv1, iv2 = derive_iv_bytes(session_key, nonce, shape)
    _, dec = _diffusion_functions(diffusion_version)
    p = dec(arr.reshape(-1), k1, k2, iv1, iv2).reshape(arr.shape)
    xp, _ = _seq(session_key, nonce, shape, b"permutation", pixels)
    return inverse_permute_pixels(p, permutation_from_sequence(xp))
