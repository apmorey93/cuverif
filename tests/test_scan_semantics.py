"""
Tier 1 Verification: Scan Chain Semantics
=========================================
Strict verification of Zero-Time Scan Load behavior.
Ensures that scan_load() correctly "teleports" data into registers.

Contract Checked:
1. Pattern columns map to registers in chain order (Col 0 -> Reg 0).
2. Values are loaded correctly (0->0, 1->1).
3. X states are loaded correctly if provided.
4. Batch dimension is preserved.
"""

import sys
import os
import pytest
import numpy as np

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
import cuverif.modules as modules

def test_scan_load_values():
    """Test loading valid 0/1 values into a chain of 3 registers."""
    batch_size = 5
    
    # Create Chain: Reg0 -> Reg1 -> Reg2
    r0 = modules.DFlipFlop(batch_size)
    r1 = modules.DFlipFlop(batch_size)
    r2 = modules.DFlipFlop(batch_size)
    chain = modules.ScanChain([r0, r1, r2])
    
    # Pattern: [Batch, 3]
    # Instance 0: 0 0 0
    # Instance 1: 1 1 1
    # Instance 2: 0 1 0
    # Instance 3: 1 0 1
    # Instance 4: 0 0 1
    patterns = np.array([
        [0, 0, 0],
        [1, 1, 1],
        [0, 1, 0],
        [1, 0, 1],
        [0, 0, 1]
    ], dtype=np.uint32)
    
    # Load
    chain.scan_load(patterns)
    
    # Verify Reg 0 (Col 0)
    v0, s0 = r0.q.cpu()
    assert np.array_equal(v0, patterns[:, 0]), "Reg 0 Value Mismatch"
    assert np.array_equal(s0, np.ones(batch_size)), "Reg 0 Strength Mismatch (Should be all valid)"
    
    # Verify Reg 1 (Col 1)
    v1, s1 = r1.q.cpu()
    assert np.array_equal(v1, patterns[:, 1]), "Reg 1 Value Mismatch"
    assert np.array_equal(s1, np.ones(batch_size)), "Reg 1 Strength Mismatch"
    
    # Verify Reg 2 (Col 2)
    v2, s2 = r2.q.cpu()
    assert np.array_equal(v2, patterns[:, 2]), "Reg 2 Value Mismatch"
    assert np.array_equal(s2, np.ones(batch_size)), "Reg 2 Strength Mismatch"

def test_scan_load_x_states():
    """Test loading X states into a chain."""
    batch_size = 2
    r0 = modules.DFlipFlop(batch_size)
    chain = modules.ScanChain([r0])
    
    # Pattern Val: [0, 1]
    # Pattern X:   [0, 1] (0=X, 1=Valid)
    # Instance 0: Val=0, X=0 -> State X
    # Instance 1: Val=1, X=1 -> State 1
    
    pat_val = np.array([[0], [1]], dtype=np.uint32)
    pat_x   = np.array([[0], [1]], dtype=np.uint32)
    
    chain.scan_load(pat_val, pattern_x=pat_x)
    
    v, s = r0.q.cpu()
    
    # Instance 0: X (V=0, S=0)
    assert v[0] == 0 and s[0] == 0, "Failed to load X state"
    
    # Instance 1: 1 (V=1, S=1)
    assert v[1] == 1 and s[1] == 1, "Failed to load 1 state"

if __name__ == "__main__":
    try:
        test_scan_load_values()
        test_scan_load_x_states()
        print("[PASS] Scan Chain Semantics Verified")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
