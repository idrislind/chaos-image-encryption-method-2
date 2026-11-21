import numpy as np
import pytest
from web_adapter import (generate_keypair, image_from_bytes, png_bytes,
                         encrypt_image, decrypt_image, encryption_archive,
                         extract_encrypted_archive, safe_metrics, extra_experiments)

@pytest.mark.parametrize("backend", ["RSA", "ECC"])
def test_web_roundtrip(backend):
    original = np.random.default_rng(8).integers(0, 256, (12, 13, 3), dtype=np.uint8)
    priv, pub = generate_keypair(backend)
    cipher, meta = encrypt_image(original, "RGB", pub)
    archive = encryption_archive(cipher, "RGB", meta)
    got, mode, extracted_meta = extract_encrypted_archive(archive)
    assert mode == "RGB"
    assert np.array_equal(cipher, got)
    restored = decrypt_image(got, mode, extracted_meta, priv)
    assert np.array_equal(original, restored)
    assert safe_metrics(original, cipher, restored)["correctness"]["exact_match"] is True


def test_grayscale_and_image_format():
    original = np.arange(16*18, dtype=np.uint8).reshape(16,18)
    got, mode = image_from_bytes(png_bytes(original, "L"))
    assert mode == "L"
    assert np.array_equal(original, got)


def test_size_limit():
    with pytest.raises(ValueError):
        image_from_bytes(b"0" * (15*1024*1024+1))


def test_extra_evaluation():
    image = np.random.default_rng(2).integers(0, 256, (15, 15), dtype=np.uint8)
    priv, pub = generate_keypair("ECC")
    cipher, meta = encrypt_image(image, "L", pub)
    result = extra_experiments(image, cipher, meta, priv)
    assert len(result["attacks"]) == 3
    assert result["key_sensitivity"]["Wrong-key exact"] is False
