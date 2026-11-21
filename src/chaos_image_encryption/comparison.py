"""Controlled A/B comparison: original Method 1 Hénon vs Method 2 2DLMUTF.

Both methods are run with the same plaintext, 256-bit session key, nonce,
permutation and v3 diffusion. Only chaotic map and its seed range differ.
No claims of formal cryptographic security follow from the test metrics.
"""
from __future__ import annotations
import math
import time
import numpy as np
from .chaos.kdf import derive_bytes,derive_iv_bytes
from .chaos.permutation import permutation_from_sequence,permute_pixels,inverse_permute_pixels
from .chaos.diffusion import diffuse_v3,inverse_diffuse_v3
from .cipher.core import encrypt_array,decrypt_array
from .evaluation.metrics import entropy,adjacent_correlations,npcr,uaci
from .chaos.logistic_utf import generate_logistic_utf

def _henon_sequence(key,nonce,shape,domain,length):
    denom=float((1<<64)-1)
    for attempt in range(16):
        raw=derive_bytes(key,nonce,shape,domain+b'|attempt='+str(attempt).encode(),16)
        ux=int.from_bytes(raw[:8],'big')/denom
        uy=int.from_bytes(raw[8:],'big')/denom
        x,y=-0.20+0.40*ux,-0.20+0.40*uy
        xs=np.empty(length,dtype=np.float64);ys=np.empty(length,dtype=np.float64)
        valid=True
        for i in range(1000+length):
            x,y=1.0-1.4*x*x+y,0.3*x
            if not(math.isfinite(x) and math.isfinite(y)) or abs(x)>1e6 or abs(y)>1e6:
                valid=False;break
            if i>=1000:
                xs[i-1000]=x;ys[i-1000]=y
        if valid:return xs,ys
    raise RuntimeError('Hénon orbit diverged after 16 attempts')

def _quantize(seq):
    return (np.floor(np.abs(seq)*1e14).astype(np.uint64)&np.uint64(255)).astype(np.uint8)

def _henon_material(image,key,nonce):
    shape=tuple(image.shape)
    x,_=_henon_sequence(key,nonce,shape,b'permutation',image.shape[0]*image.shape[1])
    x1,_=_henon_sequence(key,nonce,shape,b'diffusion-1',image.size)
    _,y2=_henon_sequence(key,nonce,shape,b'diffusion-2',image.size)
    return permutation_from_sequence(x),_quantize(x1),_quantize(y2),derive_iv_bytes(key,nonce,shape)

def henon_encrypt_array(image,key,nonce):
    perm,k1,k2,(iv1,iv2)=_henon_material(image,key,nonce)
    p=permute_pixels(image,perm)
    return diffuse_v3(p.reshape(-1),k1,k2,iv1,iv2).reshape(image.shape)

def henon_decrypt_array(cipher,key,nonce):
    perm,k1,k2,(iv1,iv2)=_henon_material(cipher,key,nonce)
    p=inverse_diffuse_v3(cipher.reshape(-1),k1,k2,iv1,iv2).reshape(cipher.shape)
    return inverse_permute_pixels(p,perm)

def compare_methods(image,key,nonce):
    image=np.asarray(image,dtype=np.uint8)
    changed=image.copy()
    if image.ndim==2:changed[image.shape[0]//2,image.shape[1]//2]^=np.uint8(1)
    else:changed[image.shape[0]//2,image.shape[1]//2,0]^=np.uint8(1)
    output={}
    for name,encrypt,decrypt in (
        ('Metode 1 - Hénon',henon_encrypt_array,henon_decrypt_array),
        ('Metode 2 - 2DLMUTF',encrypt_array,decrypt_array)):
        t=time.perf_counter(); cipher=encrypt(image,key,nonce); enc_ms=1000*(time.perf_counter()-t)
        t=time.perf_counter(); recovered=decrypt(cipher,key,nonce); dec_ms=1000*(time.perf_counter()-t)
        cipher_changed=encrypt(changed,key,nonce)
        output[name]={
            'cipher':cipher,'recovered':recovered,
            'exact_match':bool(np.array_equal(image,recovered)),
            'entropy_cipher':entropy(cipher)['overall'],
            'correlation_cipher':adjacent_correlations(cipher),
            'npcr_percent':npcr(cipher,cipher_changed),
            'uaci_percent':uaci(cipher,cipher_changed),
            'encrypt_ms':enc_ms,'decrypt_ms':dec_ms,
        }
    return output
