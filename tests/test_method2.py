import os
import numpy as np
import pytest
from chaos_image_encryption.chaos.logistic_utf import LogisticUTFConfig,generate_logistic_utf,quantize_to_uint8
from chaos_image_encryption.cipher.core import encrypt_array,decrypt_array
from chaos_image_encryption.evaluation.metrics import npcr,uaci
from web_adapter import encrypt_image,decrypt_image,generate_keypair

def test_paper_equations_first_step():
    cfg=LogisticUTFConfig(burn_in=0)
    x,y=.235,.350
    ex=((cfg.r1+x*(1-x))/(y*(1-y)))%1.0
    ey=((cfg.r2+y*(1-y))/(x*(1-ex)))%1.0
    xs,ys=generate_logistic_utf(x,y,1,cfg)
    assert xs[0]==pytest.approx(ex,abs=1e-13)
    assert ys[0]==pytest.approx(ey,abs=1e-13)

def test_range_and_seed_reproducibility():
    for seed in ((.235,.350),(.1234,.7654),(.88,.1)):
        a,b=generate_logistic_utf(*seed,2000)
        aa,bb=generate_logistic_utf(*seed,2000)
        assert np.array_equal(a,aa) and np.array_equal(b,bb)
        assert np.all(np.isfinite(a)) and np.all(np.isfinite(b))
        assert np.all((a>0)&(a<1)) and np.all((b>0)&(b<1))
        assert len(np.unique(quantize_to_uint8(a)))>180

@pytest.mark.parametrize('shape',[(16,16),(23,31,3),(1,1),(1,1,3)])
def test_determinism_roundtrip(shape):
    arr=np.random.default_rng(9).integers(0,256,shape,dtype=np.uint8)
    key=os.urandom(32); nonce=os.urandom(16)
    c1=encrypt_array(arr,key,nonce); c2=encrypt_array(arr,key,nonce)
    assert np.array_equal(c1,c2)
    assert np.array_equal(arr,decrypt_array(c1,key,nonce))

def test_wrong_method_rejected():
    arr=np.zeros((12,12),dtype=np.uint8)
    priv,pub=generate_keypair('ECC')
    cipher,meta=encrypt_image(arr,'L',pub)
    bad=dict(meta,method='henon-2d-permutation-two-round-nonlinear-diffusion')
    with pytest.raises(ValueError,match='Metode'):
        decrypt_image(cipher,'L',bad,priv)

def test_differential_smoke():
    arr=np.random.default_rng(23).integers(0,256,(64,64,3),dtype=np.uint8)
    changed=arr.copy();changed[32,32,0]^=np.uint8(1)
    k=os.urandom(32);n=os.urandom(16)
    a=encrypt_array(arr,k,n); b=encrypt_array(changed,k,n)
    assert npcr(a,b)>95
    assert 25<uaci(a,b)<45
