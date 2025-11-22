"""
CuVerif Trace Generator for VCS Equivalence
============================================

Simulates dummy.v netlist using CPU backend and records signal traces.
Output format matches VCS comparison script expectations.
"""

import sys
import os
import json
import numpy as np

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cuverif.compiler import VerilogCompiler
from cuverif.core import LogicTensor
from cuverif.backend.cpu_backend import CpuBackend

# 4-state decoding
STATE_MAP = {
    (0, 1): "0",
    (1, 1): "1",
    (0, 0): "X",
    (1, 0): "Z",
}

def decode_state(v, s):
    """Decode (v, s) to '0','1','X','Z' string."""
    return STATE_MAP.get((int(v), int(s)), "X")

def trace_cuverif(netlist_path, stimulus_path, output_path):
    """
    Run CuVerif simulation and record trace.
    
    Args:
        netlist_path: Path to .v file
        stimulus_path: Path to stimulus.json
        output_path: Path to save trace_cuverif.json
    """
    print(f"Loading netlist: {netlist_path}")
    
    # Read netlist content
    with open(netlist_path, 'r') as f:
        netlist_content = f.read()
    
    # Compile netlist (batch_size=1, CPU backend will be default)
    compiler = VerilogCompiler()
    chip = compiler.compile(netlist_content, batch_size=1)
    print(f"  Compiled {len(chip.signals)} signals")
    
    # Load stimulus
    with open(stimulus_path, 'r') as f:
        stimulus = json.load(f)
    print(f"Loaded {len(stimulus)} cycles of stimulus")
    
    # Run simulation and record trace
    trace = []
    backend = CpuBackend()
    
    for stim in stimulus:
        cycle = stim['cycle']
        
        # Create input tensors (batch_size=1, CPU backend)
        inputs = {}
        for sig_name in ['clk', 'rst', 'a', 'b']:
            if sig_name in stim:
                val = stim[sig_name]
                inputs[sig_name] = LogicTensor.from_host(
                    np.array([val], dtype=np.uint32),
                    np.array([1], dtype=np.uint32),  # Strong
                    backend=backend
                )
        
        # Set inputs
        for sig_name, tensor in inputs.items():
            if sig_name in chip.signals:
                chip.set_input(sig_name, tensor)
        
        # Step simulation (if not cycle 0)
        if cycle > 0:
            chip.step()
        
        # Sample outputs
        signal_values = {}
        for sig_name in ['clk', 'rst', 'a', 'b', 'y']:  # dummy.v has output y
            if sig_name in chip.signals:
                sig_tensor = chip.get_output(sig_name)
                v, s = sig_tensor.cpu()
                signal_values[sig_name] = decode_state(v[0], s[0])
            else:
                signal_values[sig_name] = "X"
        
        trace.append({
            "cycle": cycle,
            "signals": signal_values
        })
    
    # Save trace
    with open(output_path, 'w') as f:
        json.dump(trace, f, indent=2)
    print(f"Saved CuVerif trace to {output_path}")
    print(f"  Total cycles: {len(trace)}")
    
    # Show first few cycles
    print("\nFirst 5 cycles:")
    for t in trace[:5]:
        print(f"  Cycle {t['cycle']}: {t['signals']}")

if __name__ == "__main__":
    netlist = "dummy.v"
    stimulus = "tools/stimulus.json"
    output = "tools/trace_cuverif.json"
    
    trace_cuverif(netlist, stimulus, output)
