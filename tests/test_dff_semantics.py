"""
DFF Semantics Test - Exhaustive Truth Table
============================================

This test formally locks down DFlipFlop behavior by testing all possible
combinations of (d, rst) inputs in the 4-state logic domain {0, 1, X, Z}.

The truth table enforces:
- Active-high reset: rst=1 forces Q=0
- Normal operation: rst=0 captures D
- X-propagation: X on reset or data propagates to Q
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import numpy as np
from cuverif.core import LogicTensor
from cuverif.backend.cpu_backend import CpuBackend
from cuverif.modules import DFlipFlop

# Use CPU backend for deterministic testing
backend = CpuBackend()

# 4-state encoding
STATES = {
    "0": (0, 1),
    "1": (1, 1),
    "X": (0, 0),
    "Z": (1, 0),
}

def make_tensor(state: str) -> LogicTensor:
    """Create a single-element LogicTensor with the given state."""
    v, s = STATES[state]
    return LogicTensor.from_host(np.array([v], dtype=np.uint32), 
                                   np.array([s], dtype=np.uint32), 
                                   backend=backend)

def decode_state(v: int, s: int) -> str:
    """Decode (v, s) back to state name."""
    for name, (V, S) in STATES.items():
        if v == V and s == S:
            return name
    raise ValueError(f"Unknown state: (v={v}, s={s})")

def test_dff_truth_table():
    """
    Exhaustive DFF truth table test.
    
    DFF contract (active-high reset):
    - If rst is X → Q = X (reset state unknown)
    - Elif rst = 1 → Q = 0 (forced reset)
    - Elif rst = 0:
        - If d is X → Q = X (data unknown)
        - Else → Q = d (normal capture)
    """
    
    # Expected outputs for all (d, rst) combinations
    # Format: (d_state, rst_state): expected_q_state
    truth_table = {
        # rst = 0 (inactive): Q follows D
        ("0", "0"): "0",
        ("1", "0"): "1",
        ("X", "0"): "X",
        ("Z", "0"): "Z",
        
        # rst = 1 (active): Q forced to 0
        ("0", "1"): "0",
        ("1", "1"): "0",
        ("X", "1"): "0",
        ("Z", "1"): "0",
        
        # rst = X (unknown): Q becomes X
        ("0", "X"): "X",
        ("1", "X"): "X",
        ("X", "X"): "X",
        ("Z", "X"): "X",
        
        # rst = Z (high-impedance): DFF treats weak/uncertain reset as X
        # This is correct - a high-Z reset signal cannot be trusted
        ("0", "Z"): "X",
        ("1", "Z"): "X",
        ("X", "Z"): "X",
        ("Z", "Z"): "X",
    }
    
    # Test all combinations
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("DFF EXHAUSTIVE TRUTH TABLE TEST")
    print("=" * 70)
    print()
    
    for (d_state, rst_state), expected_q in truth_table.items():
        # Create DFF (uses DEFAULT_BACKEND internally)
        dff = DFlipFlop(batch_size=1)
        
        # Create input tensors with CPU backend
        d_tensor = make_tensor(d_state)
        rst_tensor = make_tensor(rst_state)
        
        # Clock the DFF
        q_out = dff.step(d_tensor, reset=rst_tensor)
        
        # Read result
        v_actual, s_actual = q_out.cpu()
        actual_q = decode_state(v_actual[0], s_actual[0])
        
        # Check result
        if actual_q == expected_q:
            status = "[PASS]"
            passed += 1
        else:
            status = "[FAIL]"
            failed += 1
            
        print(f"{status} D={d_state}, RST={rst_state} -> Q={actual_q} (expected {expected_q})")
    
    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    assert failed == 0, f"DFF truth table test failed: {failed} cases incorrect"
    print("\n[SUCCESS] DFF semantics verified!")

if __name__ == "__main__":
    test_dff_truth_table()
