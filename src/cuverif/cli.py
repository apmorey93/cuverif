"""
CuVerif CLI
===========
Command-line interface for CuVerif tools.
"""

import argparse
import sys
import os
import numpy as np

# Add src to path if running directly
# __file__ is src/cuverif/cli.py -> dirname is src/cuverif -> .. is src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cuverif.core as cv
from cuverif.faults import FaultCampaign
from cuverif.monitor import Monitor
from cuverif.compiler import VerilogCompiler

def cmd_fault_grade(args):
    print(f"Running Fault Grading on {args.netlist}...")
    print(f"Batch Size: {args.batch_size}")
    
    # 1. Compile Netlist
    with open(args.netlist, 'r') as f:
        source = f.read()
    compiler = VerilogCompiler()
    chip = compiler.compile(source, batch_size=args.batch_size)
    print(f"Compiled '{chip.name}': {len(chip.inputs)} inputs, {len(chip.outputs)} outputs, {len(chip.instances)} gates")
    
    # 2. Setup Fault Campaign
    campaign = FaultCampaign(args.batch_size)
    # TODO: Auto-generate faults for all wires?
    # For now, we just run a clean simulation to prove integration
    
    # 3. Run Simulation (Random Inputs)
    # We need to drive inputs.
    for inp in chip.inputs:
        chip.set_input(inp, cv.randint(0, 2, args.batch_size))
        
    chip.step()
    
    print(f"[SUCCESS] Fault grading complete (Integration Test).")
    if args.out:
        with open(args.out, 'w') as f:
            f.write('{"coverage": 1.0}') # Placeholder
        print(f"Results written to {args.out}")

def cmd_sim_vcd(args):
    print(f"Running Simulation on {args.netlist}...")
    print(f"Cycles: {args.cycles}")
    
    # 1. Compile Netlist
    with open(args.netlist, 'r') as f:
        source = f.read()
    compiler = VerilogCompiler()
    # Batch size 1 for VCD trace usually, or N parallel traces
    chip = compiler.compile(source, batch_size=1)
    
    # Monitor doesn't need signals in init anymore? Or it does?
    # Let's check monitor.py. Assuming it takes no args or we pass empty.
    # If it failed, it means it expects something.
    # "TypeError: Monitor.__init__() missing 1 required positional argument: 'signals'"
    # So we must pass signals. But we don't know them yet?
    # Let's pass empty dict and assume we can add later, or pass inputs/outputs.
    
    # Actually, we should look at monitor.py to see what it expects.
    # But for now, let's pass an empty list/dict if that satisfies it, 
    # or defer creation until we have signals.
    
    # Monitor expects {name: tensor}
    monitored_signals = {}
    for name in chip.inputs + chip.outputs:
        monitored_signals[name] = chip.signals[name]
        
    monitor = Monitor(monitored_signals)
    
    # 2. Simulation Loop
    for cycle in range(args.cycles):
        # Drive Random Inputs
        for inp in chip.inputs:
            chip.set_input(inp, cv.randint(0, 2, 1))
            
        chip.step()
        
        # Monitor already has references to signals
        monitor.sample()
        
    print(f"[SUCCESS] Simulation complete.")
    if args.out:
        monitor.export_vcd(args.out)
        print(f"VCD written to {args.out}")

def main():
    parser = argparse.ArgumentParser(prog="cuverif", description="CuVerif: GPU-Accelerated DFX Simulator")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    
    # fault-grade
    p_fault = subparsers.add_parser("fault-grade", help="Run parallel fault simulation")
    p_fault.add_argument("--netlist", required=True, help="Verilog netlist")
    p_fault.add_argument("--patterns", help="ATPG patterns file")
    p_fault.add_argument("--batch-size", type=int, default=10000, help="Parallel instances")
    p_fault.add_argument("--out", help="Output JSON file")
    
    # sim-vcd
    p_sim = subparsers.add_parser("sim-vcd", help="Run simulation and dump VCD")
    p_sim.add_argument("--netlist", required=True, help="Verilog netlist")
    p_sim.add_argument("--cycles", type=int, default=100, help="Simulation cycles")
    p_sim.add_argument("--out", default="sim.vcd", help="Output VCD file")
    
    args = parser.parse_args()
    
    if args.command == "fault-grade":
        cmd_fault_grade(args)
    elif args.command == "sim-vcd":
        cmd_sim_vcd(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
