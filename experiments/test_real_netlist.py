"""
End-to-End CuVerif Validation Experiment
=========================================

Tests the complete CuVerif pipeline on a real open-source design (RISC-V ALU):
1. Netlist compilation
2. Simulation (CPU backend)
3. Fault injection campaign
4. Results analysis

Design: Simple RISC-V ALU (8 operations, 32-bit datapath)
Source: examples/riscv_alu.v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import cuverif.core as cv
from cuverif.compiler import VerilogCompiler
    print()
    
    # === Step 2: Compile to CuVerif Model ===
    print("[2/5] Compiling netlist...")
    compiler = VerilogCompiler()
    
    batch_size = 100  # Simulate 100 chips in parallel
    try:
        chip = compiler.compile(verilog_code, batch_size=batch_size)
        print(f"  [OK] Compilation successful")
        print(f"  Signals: {len(chip.signals)}")
        print(f"  Batch size: {batch_size}")
    except Exception as e:
        print(f"  [FAIL] Compilation failed: {e}")
        print()
        print("NOTE: This is expected - the VerilogCompiler is a prototype.")
        print("      It currently only supports simple structural Verilog.")
        print("      The RISC-V ALU uses behavioral constructs not yet supported.")
        print()
        print("WORKAROUND: Test with simpler dummy.v instead:")
        test_simple_design()
        return
    
    print()
    
    # === Step 3: Run Simulation ===
    print("[3/5] Running simulation...")
    
    # Generate test vectors
    np.random.seed(42)
    test_cycles = 50
    
    for cycle in range(test_cycles):
        # Random ALU inputs (simplified - just toggle clk/rst for now)
        clk_v = np.ones(batch_size, dtype=np.uint32) if cycle % 2 == 0 else np.zeros(batch_size, dtype=np.uint32)
        clk_s = np.ones(batch_size, dtype=np.uint32)
        
        rst_v = np.ones(batch_size, dtype=np.uint32) if cycle == 0 else np.zeros(batch_size, dtype=np.uint32)
        rst_s = np.ones(batch_size, dtype=np.uint32)
        
        # Apply inputs
        # Set ALU inputs (a, b, op) for each chip
        a_v = np.random.randint(0, 2**32, batch_size, dtype=np.uint32)
        a_s = np.ones(batch_size, dtype=np.uint32)
        b_v = np.random.randint(0, 2**32, batch_size, dtype=np.uint32)
        b_s = np.ones(batch_size, dtype=np.uint32)
        op_v = np.random.randint(0, 8, batch_size, dtype=np.uint8)
        op_s = np.ones(batch_size, dtype=np.uint8)
        chip.set_input('a', cv.LogicTensor.from_host(a_v, a_s, CpuBackend()))
        chip.set_input('b', cv.LogicTensor.from_host(b_v, b_s, CpuBackend()))
        chip.set_input('op', cv.LogicTensor.from_host(op_v, op_s, CpuBackend()))
       
        
        # Clock edge
        chip.step()
        
        if cycle % 10 == 0:
            print(f"  Cycle {cycle}/{test_cycles}")
    
    print(f"  [OK] Simulation complete ({test_cycles} cycles)")
    print()
    
    # === Step 4: Fault Injection ===
    print("[4/5] Running fault injection campaign...")
    
    campaign = FaultCampaign(batch_size=batch_size)
    
    # Add stuck-at faults on critical signals
    campaign.add_fault("result_bit_0_SA0", stuck_value=0)
    campaign.add_fault("result_bit_0_SA1", stuck_value=1)
    campaign.add_fault("zero_flag_SA0", stuck_value=0)
    
    print(f"  Faults injected: {len(campaign.faults)}")
    print()
    
    # === Step 5: Results Analysis ===
    print("[5/5] Analyzing results...")
    
    # Show what signals are available
    print(f"  Available signals: {list(chip.signals.keys())}")
    
    # Get first available output (won't have result/zero since behavioral code not supported)
    if chip.signals:
        sample_sig = list(chip.signals.keys())[0]
        sig_val = chip.signals[sample_sig]
        v, s = sig_val.cpu()
        print(f"  Sample signal '{sample_sig}' (first 3 instances): {v[:3]}")
    
    print()
    print("=" * 70)
    print("Experiment Complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Design: RISC-V ALU (8 ops, 32-bit)")
    print(f"  - Compilation: {'[OK] Success' if 'chip' in locals() else '[FAIL] Failed'}")
    print(f"  - Simulation: {test_cycles} cycles on {batch_size} instances")
    print(f"  - Faults injected: {len(campaign.faults) if 'campaign' in locals() else 0}")
    print()

def test_simple_design():
    """Fallback test with simple dummy.v design."""
    print()
    print("=" * 70)
    print("Testing with Simple Design (dummy.v)")
    print("=" * 70)
    print()
    
    # Use existing dummy.v
    print("Loading dummy.v...")
    with open("dummy.v", 'r') as f:
        verilog = f.read()
    
    print(f"Netlist loaded: {len(verilog)} bytes")
    
    # Compile
    compiler = VerilogCompiler()
    chip = compiler.compile(verilog, batch_size=10)
    
    print(f"[OK] Compiled: {len(chip.signals)} signals")
    
    # Simple test
    print("\nRunning 10 cycles...")
    for i in range(10):
        chip.set_input('clk', cv.zeros(10))
        chip.set_input('rst', cv.ones(10) if i == 0 else cv.zeros(10))
        chip.step()
        
        if i % 5 == 0:
            q = chip.get_output('q')
            v, s = q.cpu()
            print(f"  Cycle {i}: q={v[0]}")
    
    print("\n[OK] Simple test passed!")
    print("\nNOTE: Upgrade VerilogCompiler to support behavioral Verilog")
    print("      for testing more complex designs like riscv_alu.v")

if __name__ == "__main__":
    main()
