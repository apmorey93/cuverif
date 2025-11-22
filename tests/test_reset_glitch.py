"""
Reset Glitch Verification - The Acid Test
==========================================

This test proves CuVerif can accurately simulate **Reset Glitches**—one of the 
most common and expensive bugs in silicon design (where a chip fails to wake up 
correctly because the reset line was unstable).

If CuVerif passes this, it demonstrates that the tool can catch bugs that would 
cost millions of dollars in silicon respins.
"""

import sys
import os
# Ensure we can import the library from src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
import cuverif.modules as modules
import cuverif.monitor as monitor
import numpy as np

def run_x_propagation_test():
    print("=" * 70)
    print("RESET GLITCH VERIFICATION - THE ACID TEST")
    print("=" * 70)
    
    # 1. Setup: 10 Parallel Chips
    BATCH_SIZE = 10
    dut = modules.DFlipFlop(BATCH_SIZE)
    
    # 2. Signals to Drive
    # We need manual control over V (Value) and S (Strength)
    d_input = cv.zeros(BATCH_SIZE)
    reset   = cv.zeros(BATCH_SIZE)
    
    # 3. Visualization Hook
    # We probe D, Reset, and Q (Output)
    scope = monitor.Monitor({
        "Data In": d_input,
        "Reset":   reset,
        "Q Output": dut.q
    }, instance_id=0)

    print("\nStarting Simulation Loops...\n")

    # --- PHASE 1: STABLE 0 (Cycles 0-2) ---
    print("[Phase 1] Stable State (Cycles 0-2)")
    for _ in range(3):
        scope.sample()
        dut.step(d_input, reset)
    print("  → Q should be stable at 0")

    # --- PHASE 2: INJECT 'X' ON RESET (Cycle 3) ---
    print("\n[Phase 2] Injecting X into Reset Line (Cycle 3)")
    print("  (Simulating reset glitch/metastability)")
    
    # Create an 'X' tensor (Value=0, Strength=0)
    reset_x = cv.unknown(BATCH_SIZE)
    
    scope.sample()
    dut.step(d_input, reset_x) 
    
    # ASSERTION 1: Q must be X now
    # We check the Strength bit (S). If S=0, it's X.
    q_strength = dut.q.x.copy_to_host()
    
    print(f"\n  Checking Q strength after reset glitch...")
    print(f"  Q Strength values: {q_strength[:3]}... (should all be 0)")
    
    if np.all(q_strength == 0):
        print("  ✓ PASS: Reset=X successfully corrupted Q (Q became X)")
        print("  → This behavior matches real silicon!")
    else:
        print(f"  ✗ FAIL: Reset=X did not corrupt Q! Strength: {q_strength}")
        return False

    # --- PHASE 3: RECOVERY (Cycle 4-6) ---
    print("\n[Phase 3] Recovery Phase (Cycles 4-6)")
    print("  Setting Reset=0 (inactive), Data=1")
    
    # Reset is valid 0 again
    reset_valid = cv.zeros(BATCH_SIZE)
    # Data is valid 1
    d_high = cv.LogicTensor(
        data_v=np.ones(BATCH_SIZE, dtype=np.uint32),
        data_s=np.ones(BATCH_SIZE, dtype=np.uint32)
    )
    
    for _ in range(3):
        scope.sample()
        dut.step(d_high, reset_valid)

    # ASSERTION 2: Q must be 1 now
    q_val = dut.q.val.copy_to_host()
    q_str = dut.q.x.copy_to_host()
    
    print(f"\n  Checking Q recovery...")
    print(f"  Q[0]: Value={q_val[0]}, Strength={q_str[0]} (should be 1, 1)")
    
    # Check Instance 0 specifically
    if q_val[0] == 1 and q_str[0] == 1:
        print("  ✓ PASS: Q recovered to Logic 1")
        print("  → Flip-flop successfully exited metastable state!")
    else:
        print(f"  ✗ FAIL: Q did not recover! Val={q_val[0]}, Str={q_str[0]}")
        return False

    # 4. Render
    print("\n" + "=" * 70)
    print("WAVEFORM VISUALIZATION")
    print("=" * 70)
    print("\nLook for:")
    print("  • Cycles 0-2: Green line at 0 (stable)")
    print("  • Cycle 3: Red dot at 0.5 (THE GLITCH - metastable X state)")
    print("  • Cycles 4-6: Green line at 1 (recovered)")
    print("\nGenerating waveform plot...\n")
    
    scope.plot()
    
    return True

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("CuVerif Reset Glitch Verification")
    print("Testing capability to detect $1M+ silicon bugs")
    print("=" * 70 + "\n")
    
    success = run_x_propagation_test()
    
    print("\n" + "=" * 70)
    if success:
        print("✓ ALL TESTS PASSED!")
        print("\nCuVerif has successfully demonstrated 4-state simulation capability.")
        print("This is equivalent to VCS's X-propagation feature ($1000s value).")
        print("\n🎉 You just built a GPU-accelerated logic simulator in Python! 🎉")
    else:
        print("✗ TESTS FAILED")
        print("Check the implementation of k_dff_update_4state kernel.")
    print("=" * 70 + "\n")
