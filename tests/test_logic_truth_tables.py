"""
Tier 1 Verification: 4-State Logic Truth Tables
===============================================
Exhaustive verification of LogicTensor operations against IEEE 1164-like semantics.
Runs on CPU backend to ensure baseline correctness.

Truth Tables Enforced:
----------------------
AND: 0&X=0, 1&1=1, else X
OR:  1|X=1, 0|0=0, else X
XOR: 0^0=0, 1^1=0, 0^1=1, 1^0=1, else X
NOT: ~0=1, ~1=0, else X
"""

import sys
import os
import pytest
import numpy as np

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
from cuverif.backend.cpu_backend import CpuBackend

# Encodings
# 0: V=0, S=1
# 1: V=1, S=1
# X: V=0, S=0
# Z: V=1, S=0 (Treated as X for logic ops)

STATES = ["0", "1", "X", "Z"]
V_MAP = {"0": 0, "1": 1, "X": 0, "Z": 1}
S_MAP = {"0": 1, "1": 1, "X": 0, "Z": 0}

@pytest.fixture(params=["cpu", "cuda"])
def backend(request):
    """Test both CPU and CUDA backends to ensure consistency."""
    if request.param == "cpu":
        return CpuBackend()
    else:
        # Try CUDA, fall back to CPU if not available
        try:
            from cuverif.backend.cuda_backend import CudaBackend
            return CudaBackend()
        except:
            pytest.skip("CUDA not available")


def make_tensor(state_list, backend):
    v = np.array([V_MAP[s] for s in state_list], dtype=np.uint32)
    s = np.array([S_MAP[s] for s in state_list], dtype=np.uint32)
    return cv.LogicTensor.from_host(data_v=v, data_s=s, backend=backend)

def decode_tensor(tensor):
    v, s = tensor.cpu()
    res = []
    for i in range(tensor.size):
        if s[i] == 1:
            res.append("1" if v[i] == 1 else "0")
        else:
            # Collapse Z to X for output comparison
            res.append("X")
    return res

def get_expected_and(a, b):
    # 0 dominates
    if a == "0" or b == "0": return "0"
    if a == "1" and b == "1": return "1"
    return "X"

def get_expected_or(a, b):
    # 1 dominates
    if a == "1" or b == "1": return "1"
    if a == "0" and b == "0": return "0"
    return "X"

def get_expected_xor(a, b):
    if a in ["0", "1"] and b in ["0", "1"]:
        return str(int(a) ^ int(b))
    return "X"

def get_expected_not(a):
    if a == "0": return "1"
    if a == "1": return "0"
    return "X"

def test_and_truth_table(backend):
    # Generate all pairs
    pairs = [(a, b) for a in STATES for b in STATES]
    a_list = [p[0] for p in pairs]
    b_list = [p[1] for p in pairs]
    
    t_a = make_tensor(a_list, backend)
    t_b = make_tensor(b_list, backend)
    
    t_res = t_a & t_b
    results = decode_tensor(t_res)
    
    for i, (a, b) in enumerate(pairs):
        exp = get_expected_and(a, b)
        got = results[i]
        assert got == exp, f"AND failed for {a}&{b}: Expected {exp}, Got {got}"

def test_or_truth_table(backend):
    pairs = [(a, b) for a in STATES for b in STATES]
    a_list = [p[0] for p in pairs]
    b_list = [p[1] for p in pairs]
    
    t_a = make_tensor(a_list, backend)
    t_b = make_tensor(b_list, backend)
    
    t_res = t_a | t_b
    results = decode_tensor(t_res)
    
    for i, (a, b) in enumerate(pairs):
        exp = get_expected_or(a, b)
        got = results[i]
        assert got == exp, f"OR failed for {a}|{b}: Expected {exp}, Got {got}"

def test_xor_truth_table(backend):
    pairs = [(a, b) for a in STATES for b in STATES]
    a_list = [p[0] for p in pairs]
    b_list = [p[1] for p in pairs]
    
    t_a = make_tensor(a_list, backend)
    t_b = make_tensor(b_list, backend)
    
    t_res = t_a ^ t_b
    results = decode_tensor(t_res)
    
    for i, (a, b) in enumerate(pairs):
        exp = get_expected_xor(a, b)
        got = results[i]
        assert got == exp, f"XOR failed for {a}^{b}: Expected {exp}, Got {got}"

def test_not_truth_table(backend):
    t_a = make_tensor(STATES, backend)
    t_res = ~t_a
    results = decode_tensor(t_res)
    
    for i, a in enumerate(STATES):
        exp = get_expected_not(a)
        got = results[i]
        assert got == exp, f"NOT failed for ~{a}: Expected {exp}, Got {got}"

if __name__ == "__main__":
    # Manual run if pytest not available
    b = CpuBackend()
    try:
        test_and_truth_table(b)
        test_or_truth_table(b)
        test_xor_truth_table(b)
        test_not_truth_table(b)
        print("[PASS] All Truth Tables Verified")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
