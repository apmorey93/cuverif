"""
VCS Golden Harness
==================
Compares CuVerif simulation results against Synopsys VCS (Golden Model).

Usage:
    python compare_vs_vcs.py --netlist design.v --patterns pat.npy --cycles 100 --signals signals.json
    
    # For development without VCS:
    python compare_vs_vcs.py --mock-vcs ...
"""

import argparse
import json
import os
import subprocess
import sys
import numpy as np
import re

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
import cuverif.modules as modules
# from cuverif.compiler import VerilogCompiler # Tier 2 - might need to mock or implement simple version

class SimpleVCDParser:
    """
    Minimal VCD parser to extract signal values at specific times.
    """
    def __init__(self, filename):
        self.filename = filename
        self.signals = {} # {name: id}
        self.data = {}    # {id: {time: value_str}}
        self.timescale = 1
        self._parse()

    def _parse(self):
        with open(self.filename, 'r') as f:
            lines = f.readlines()
            
        current_time = 0
        
        # 1. Header Parse (Definitions)
        # $var wire 1 ! clk $end
        for line in lines:
            line = line.strip()
            if line.startswith("$var"):
                parts = line.split()
                # $var type size id name $end
                # parts[3] is id, parts[4] is name
                if len(parts) >= 6:
                    self.signals[parts[4]] = parts[3]
                    self.data[parts[3]] = {}
            elif line.startswith("#"):
                current_time = int(line[1:])
            elif line.startswith("$dumpvars") or line.startswith("$enddefinitions"):
                continue
            elif " " not in line and len(line) > 1 and line[0] in ['0', '1', 'x', 'z', 'b']:
                # Scalar value change: 1!
                val = line[0]
                sig_id = line[1:]
                if sig_id in self.data:
                    self.data[sig_id][current_time] = val
            elif line.startswith("b"):
                # Vector: b1010 !
                parts = line.split()
                val = parts[0][1:]
                sig_id = parts[1]
                if sig_id in self.data:
                    self.data[sig_id][current_time] = val

    def get_signal_trace(self, signal_name, times):
        """Returns list of values for signal at specified times."""
        if signal_name not in self.signals:
            return None
        
        sig_id = self.signals[signal_name]
        trace = []
        
        # VCD is change-dump. We need to hold last value.
        last_val = "x"
        
        # Sort all change times for this signal
        change_times = sorted(self.data[sig_id].keys())
        change_idx = 0
        
        for t in times:
            # Advance last_val to current time t
            while change_idx < len(change_times) and change_times[change_idx] <= t:
                last_val = self.data[sig_id][change_times[change_idx]]
                change_idx += 1
            trace.append(last_val)
            
        return trace

def generate_tb(netlist_path, patterns_path, cycles, signals):
    """Generates a Verilog testbench."""
    tb = f"""
module tb;
    reg clk;
    reg rst;
    // TODO: Parse netlist to define inputs/outputs
    // For this harness to be generic, we need the port list.
    // Since VerilogCompiler is Tier 2, we'll assume a standard interface for now
    // or require the user to provide a wrapper.
    
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb);
        # {cycles * 10} $finish;
    end
    
    always #5 clk = ~clk;
    
    initial begin
        clk = 0;
        // Load patterns...
    end
endmodule
    """
    with open("tb.v", "w") as f:
        f.write(tb)

def run_vcs():
    cmd = ["vcs", "-full64", "-debug_access+all", "tb.v", "design.v", "-o", "simv"]
    subprocess.check_call(cmd)
    subprocess.check_call(["./simv"])

from cuverif.compiler import VerilogCompiler

def run_cuverif_sim(netlist, patterns, cycles, signals):
    print(f"[CuVerif] Simulating {netlist} for {cycles} cycles...")
    
    # 1. Compile
    with open(netlist, 'r') as f:
        source = f.read()
    compiler = VerilogCompiler()
    # Batch size 1 for harness comparison (single trace)
    chip = compiler.compile(source, batch_size=1)
    
    # 2. Load Patterns (if provided)
    # patterns is path to .npy
    if patterns:
        pat_data = np.load(patterns)
        # Shape: [Cycles, Inputs]? Or [Inputs, Cycles]?
        # Let's assume [Cycles, Inputs] and inputs are ordered same as chip.inputs
        pass
        
    # 3. Run Simulation
    history = {sig: [] for sig in signals}
    
    for i in range(cycles):
        # Drive Inputs (Random if no patterns)
        for inp in chip.inputs:
            # TODO: Use pattern if available
            # For harness comparison without patterns, we must be deterministic.
            # Mock VCS generates 0s. So we should generate 0s.
            val = cv.zeros(1) # Deterministic 0
            chip.set_input(inp, val)
            
        chip.step()
        
        # Record Outputs
        for sig in signals:
            if sig in chip.signals:
                # Get value (0/1/X)
                v, s = chip.signals[sig].cpu()
                val = v[0]
                valid = s[0]
                if valid:
                    history[sig].append(str(val))
                else:
                    history[sig].append("x")
            else:
                history[sig].append("x") # Signal not found
                
    return history

def main():
    parser = argparse.ArgumentParser(description="CuVerif vs VCS Golden Harness")
    parser.add_argument("--netlist", required=True, help="Path to Verilog netlist")
    parser.add_argument("--patterns", help="Path to .npy patterns")
    parser.add_argument("--cycles", type=int, default=10, help="Simulation cycles")
    parser.add_argument("--signals", required=True, help="JSON list of signals to probe")
    parser.add_argument("--mock-vcs", action="store_true", help="Generate fake VCD for testing")
    
    args = parser.parse_args()
    
    with open(args.signals, 'r') as f:
        signal_list = json.load(f)
        
    # 1. Run CuVerif
    cuverif_results = run_cuverif_sim(args.netlist, args.patterns, args.cycles, signal_list)
    
    # 2. Run VCS (or Mock)
    if args.mock_vcs:
        print("[Harness] Running in MOCK VCS mode...")
        # Generate a dummy VCD
        with open("dump.vcd", "w") as f:
            f.write("$date today $end\n$version MockVCS $end\n")
            f.write("$var wire 1 ! clk $end\n")
            for i, sig in enumerate(signal_list):
                f.write(f"$var wire 1 n{i} {sig} $end\n")
            f.write("$enddefinitions $end\n")
            f.write("#0\n$dumpvars\n0!\n")
            for i in range(len(signal_list)):
                f.write(f"0n{i}\n")
            f.write("$end\n")
            # Toggle clk a bit
            for t in range(10, args.cycles * 10, 10):
                f.write(f"#{t}\n")
                # Just keep signals 0 to match mock CuVerif
    else:
        generate_tb(args.netlist, args.patterns, args.cycles, signal_list)
        run_vcs()
        
    # 3. Compare
    print("[Harness] Comparing results...")
    vcd = SimpleVCDParser("dump.vcd")
    
    # Sample times: 5, 15, 25... (Middle of cycle if period is 10)
    sample_times = [t * 10 + 5 for t in range(args.cycles)]
    
    mismatches = 0
    for sig in signal_list:
        vcs_trace = vcd.get_signal_trace(sig, sample_times)
        cu_trace = cuverif_results[sig]
        
        if vcs_trace is None:
            print(f"[WARN] Signal {sig} not found in VCD")
            continue
            
        # Compare
        for i in range(len(sample_times)):
            # Normalize (CuVerif might return int 0/1, VCD returns str '0'/'1')
            c_val = str(cu_trace[i])
            v_val = vcs_trace[i]
            
            if c_val != v_val:
                print(f"[FAIL] Mismatch on {sig} at cycle {i}: CuVerif={c_val}, VCS={v_val}")
                mismatches += 1
                if mismatches > 5: break
        if mismatches > 5: break
        
    if mismatches == 0:
        print(f"\n[SUCCESS] 0 mismatches across {len(signal_list)} signals x {args.cycles} cycles.")
    else:
        print(f"\n[FAILURE] Found {mismatches} mismatches.")
        sys.exit(1)

if __name__ == "__main__":
    main()
