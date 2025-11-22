"""
VCD Export Verification
=======================

Tests the "Verdi Bridge" feature: exporting simulation results to VCD format.
This script runs a simulation with mixed 0, 1, and X states, then generates
a 'test_output.vcd' file that can be opened in GTKWave or Verdi.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    import cuverif.modules as modules
    import cuverif.monitor as monitor
    print("Using Real GPU CuVerif Library")
except ImportError:
    print("GPU Library not found. Using CPU Mock for VCD verification.")
    import tests.mock_cuverif as cv
    import tests.mock_cuverif as monitor
    # Mock module structure
    class Modules:
        DFlipFlop = cv.DFlipFlop
    modules = Modules()

import numpy as np

def run_vcd_test():
    print("=" * 70)
    print("VCD EXPORT TEST (The Verdi Bridge)")
    print("=" * 70)
    
    BATCH_SIZE = 5
    
    # Create signals
    clk = cv.zeros(BATCH_SIZE)
    reset = cv.zeros(BATCH_SIZE)
    data = cv.zeros(BATCH_SIZE)
    
    # Create DUT
    dff = modules.DFlipFlop(BATCH_SIZE)
    
    # Setup Monitor
    scope = monitor.Monitor({
        "clk": clk,
        "reset": reset,
        "data": data,
        "q_out": dff.q
    }, instance_id=0)
    
    print("Simulating 10 cycles with mixed states...")
    
    # Cycle 0-2: Reset Active
    reset_active = cv.LogicTensor(data_v=np.ones(BATCH_SIZE), data_s=np.ones(BATCH_SIZE))
    for _ in range(3):
        scope.sample()
        dff.step(data, reset_active)
        
    # Cycle 3-5: Normal Operation (Data=1)
    reset_inactive = cv.zeros(BATCH_SIZE)
    data_high = cv.LogicTensor(data_v=np.ones(BATCH_SIZE), data_s=np.ones(BATCH_SIZE))
    for _ in range(3):
        scope.sample()
        dff.step(data_high, reset_inactive)
        
    # Cycle 6-7: X Injection (Data=X)
    data_x = cv.unknown(BATCH_SIZE)
    for _ in range(2):
        scope.sample()
        dff.step(data_x, reset_inactive)
        
    # Cycle 8-9: Recovery (Data=0)
    data_low = cv.zeros(BATCH_SIZE)
    for _ in range(2):
        scope.sample()
        dff.step(data_low, reset_inactive)
        
    # Export VCD
    vcd_filename = "test_output.vcd"
    print(f"\nExporting waveform to {vcd_filename}...")
    scope.export_vcd(vcd_filename)
    
    # Verify file exists and has content
    if os.path.exists(vcd_filename):
        size = os.path.getsize(vcd_filename)
        print(f"[PASS] Success! Generated {vcd_filename} ({size} bytes)")
        
        # Print first few lines
        print("\n--- VCD Header Preview ---")
        with open(vcd_filename, 'r') as f:
            for _ in range(10):
                print(f.readline().strip())
        print("--------------------------")
        print("\nNow you can open this file in Verdi or GTKWave!")
    else:
        print("[FAIL] Failed to generate VCD file")

if __name__ == "__main__":
    run_vcd_test()
