import os
import numpy as np
from chaos_image_encryption.comparison import henon_encrypt_array,henon_decrypt_array,compare_methods

def test_reference_method1_roundtrip_and_same_key_determinism():
    x=np.random.default_rng(1).integers(0,256,(20,19,3),dtype=np.uint8)
    key=os.urandom(32);nonce=os.urandom(16)
    c=henon_encrypt_array(x,key,nonce)
    assert np.array_equal(c,henon_encrypt_array(x,key,nonce))
    assert np.array_equal(x,henon_decrypt_array(c,key,nonce))

def test_both_methods_report_metrics():
    x=np.random.default_rng(123).integers(0,256,(20,19),dtype=np.uint8)
    result=compare_methods(x,os.urandom(32),os.urandom(16))
    assert len(result)==2
    assert all(r['exact_match'] for r in result.values())
    assert all(r['entropy_cipher']>6 for r in result.values())
