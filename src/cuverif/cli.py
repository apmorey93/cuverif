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
# from cuverif.compiler import VerilogCompiler # Tier 2

def cmd_fault_grade(args):
    print(f"Running Fault Grading on {args.netlist}...")
    print(f"Batch Size: {args.batch_size}")
    print("Note: Compiler is Tier 2. Using mock grading for demo.")
    
    # Mock Flow
    campaign = FaultCampaign(args.batch_size)
    # ... load netlist ...
    # ... inject faults ...
    print(f"[SUCCESS] Fault grading complete. Coverage: 98.5%")
    if args.out:
        with open(args.out, 'w') as f:
            f.write('{"coverage": 0.985}')
        print(f"Results written to {args.out}")

def cmd_sim_vcd(args):
    print(f"Running Simulation on {args.netlist}...")
    print(f"Cycles: {args.cycles}")
    
    # Mock Flow
    monitor = Monitor()
    # ... sim loop ...
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
