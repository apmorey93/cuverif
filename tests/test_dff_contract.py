"""
Tier 1 Contract Verification: DFlipFlop
=======================================

This test enforces the rigorous semantic contract defined for the DFlipFlop module.
It runs on the CPU backend to ensure logic correctness without GPU dependencies.

Contract Checked:
1. Reset = 1 (Active) -> Q = 0 (regardless of D)
2. Reset = 0 (Inactive) -> Q = D (including X)
3. Reset = X (Unknown) -> Q = X (regardless of D)
4. Data = X, Reset = 0 -> Q = X
"""

import sys
import os
import pytest
import numpy as np

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
import cuverif.modules as modules

# Force CPU backend for this test if possible, though core auto-selects.
# We rely on the fact that LogicTensor logic is identical across backends.

def test_dff_truth_table():
    """
    Exhaustive Truth Table Verification for DFF Step
    
    Inputs: D, Reset
    States: 0, 1, X (Z treated as X for DFF inputs usually, but we test X)
    
    We test all 3x3 = 9 combinations of (D, Reset) where values are {0, 1, X}.
    """
    
    # 4-State Encodings
    # 0: V=0, S=1
    # 1: V=1, S=1
    # X: V=0, S=0
    
    # Batch size 9 for all combinations
    batch_size = 9
    dff = modules.DFlipFlop(batch_size)
    
    # Construct Inputs
    # D:    0 0 0 | 1 1 1 | X X X
    # Rst:  0 1 X | 0 1 X | 0 1 X
    
    d_v = np.array([0,0,0, 1,1,1, 0,0,0], dtype=np.uint32)
    d_s = np.array([1,1,1, 1,1,1, 0,0,0], dtype=np.uint32)
    
    r_v = np.array([0,1,0, 0,1,0, 0,1,0], dtype=np.uint32)
    r_s = np.array([1,1,0, 1,1,0, 1,1,0], dtype=np.uint32)
    
    d_tensor = cv.LogicTensor(data_v=d_v, data_s=d_s)
    r_tensor = cv.LogicTensor(data_v=r_v, data_s=r_s)
    
    # Step
    q = dff.step(d_tensor, reset=r_tensor)
    q_v, q_s = q.cpu()
    
    # Expected Outputs
    # 1. (D=0, R=0) -> Q=0 (Sample D)
    # 2. (D=0, R=1) -> Q=0 (Reset)
    # 3. (D=0, R=X) -> Q=X (Reset X prop)
    
    # 4. (D=1, R=0) -> Q=1 (Sample D)
    # 5. (D=1, R=1) -> Q=0 (Reset dominates)
    # 6. (D=1, R=X) -> Q=X (Reset X prop)
    
    # 7. (D=X, R=0) -> Q=X (Sample D)
    # 8. (D=X, R=1) -> Q=0 (Reset dominates)
    # 9. (D=X, R=X) -> Q=X (Reset X prop)
    
    exp_v = np.array([0,0,0, 1,0,0, 0,0,0], dtype=np.uint32)
    exp_s = np.array([1,1,0, 1,1,0, 0,1,0], dtype=np.uint32)
    
    # Verification
    for i in range(batch_size):
        d_str = "0" if d_s[i] and not d_v[i] else "1" if d_s[i] else "X"
        r_str = "0" if r_s[i] and not r_v[i] else "1" if r_s[i] else "X"
        
        q_str = "0" if q_s[i] and not q_v[i] else "1" if q_s[i] else "X"
        exp_str = "0" if exp_s[i] and not exp_v[i] else "1" if exp_s[i] else "X"
        
        print(f"Case {i}: D={d_str}, R={r_str} -> Q={q_str} (Exp: {exp_str})")
        
        assert q_v[i] == exp_v[i], f"Value mismatch at index {i} (D={d_str}, R={r_str})"
        assert q_s[i] == exp_s[i], f"Strength mismatch at index {i} (D={d_str}, R={r_str})"

if __name__ == "__main__":
    try:
        test_dff_truth_table()
        print("\n[PASS] DFlipFlop Contract Verified")
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
