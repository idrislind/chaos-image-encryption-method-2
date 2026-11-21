"""2D Logistic Map with Unit Transfer Function + modulus (2DLMUTF).

Ahmad et al. (2025), Scientific Reports, equations (5) and (6).
https://doi.org/10.1038/s41598-025-04702-0

x_next = ((r1 + x*(1-x)) / (y*(1-y))) mod 1
y_next = ((r2 + y*(1-y)) / (x*(1-x_next))) mod 1

Experimental adaptation for Method 2; float64 finite precision and a
documented guard for singular/near-singular denominators. The underlying
paper's cipher uses S-box design, whereas this project retains Method 1's
permutation and nonlinear diffusion for an ablation comparison.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class LogisticUTFConfig:
    r1: float = 4.0
    r2: float = 3.8
    burn_in: int = 1000
    epsilon: float = 1e-12

def _interior(v: float, epsilon: float) -> float:
    # Float64 rounding can produce exact boundaries from a mod-1 operation,
    # making the next denominator zero. Map boundary points to the interior
    # using a fixed, documented numerical safeguard; this is an adaptation.
    if not math.isfinite(v):
        raise ArithmeticError('Non-finite 2DLMUTF state')
    return min(max(v, epsilon), 1.0-epsilon)

def generate_logistic_utf(x0: float, y0: float, length: int,
                          config: LogisticUTFConfig = LogisticUTFConfig()):
    if length < 0 or config.burn_in < 0:
        raise ValueError('length and burn_in must be nonnegative')
    if not (0 < x0 < 1 and 0 < y0 < 1):
        raise ValueError('x0 and y0 must be in (0,1)')
    if not (0 < config.epsilon < 0.01):
        raise ValueError('invalid epsilon')
    x = _interior(float(x0), config.epsilon)
    y = _interior(float(y0), config.epsilon)
    xs = np.empty(length, dtype=np.float64)
    ys = np.empty(length, dtype=np.float64)
    for i in range(config.burn_in + length):
        dx = max(y*(1-y),config.epsilon)
        xn = _interior(((config.r1+x*(1-x))/dx) % 1.0,config.epsilon)
        dy = max(x*(1-xn),config.epsilon)
        yn = _interior(((config.r2+y*(1-y))/dy) % 1.0,config.epsilon)
        x,y=xn,yn
        if i >= config.burn_in:
            xs[i-config.burn_in],ys[i-config.burn_in]=x,y
    return xs,ys

def quantize_to_uint8(sequence: np.ndarray) -> np.ndarray:
    seq=np.asarray(sequence,dtype=np.float64)
    if not np.all(np.isfinite(seq)):
        raise ValueError('sequence contains NaN or Inf')
    vals=np.floor(np.abs(seq)*1e14).astype(np.uint64)
    return (vals & np.uint64(255)).astype(np.uint8)
