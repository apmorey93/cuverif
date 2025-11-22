"""
Generate Deterministic Stimulus for VCS Equivalence Test
==========================================================

Creates a fixed stimulus sequence with a hardcoded seed for reproducibility.
Both CuVerif and VCS will use this exact same stimulus.
"""

import numpy as np
import json

def generate_stimulus(num_cycles=200, seed=42):
    """
    Generate deterministic stimulus for simple_cpu.
    
    Netlist inputs: clk, rst, a, b
    - clk: periodic 0/1
    - rst: asserted (1) for first 5 cycles, then 0
    - a, b: driven by deterministic pseudo-random (LFSR-style)
    
    Returns: List of dicts with signal values per cycle
    """
    np.random.seed(seed)
    
    stimulus = []
    for cycle in range(num_cycles):
        clk = cycle % 2  # Toggle clock
        rst = 1 if cycle < 5 else 0  # Reset for first 5 cycles
        a = np.random.randint(0, 2)  # Random bit
        b = np.random.randint(0, 2)
        
        stimulus.append({
            "cycle": cycle,
            "clk": clk,
            "rst": rst,
            "a": a,
            "b": b
        })
    
    return stimulus

def save_stimulus_json(stimulus, filename="stimulus.json"):
    """Save stimulus to JSON for both Python and Verilog consumption."""
    with open(filename, 'w') as f:
        json.dump(stimulus, f, indent=2)
    print(f"Saved {len(stimulus)} cycles to {filename}")

def save_stimulus_mem(stimulus, filename="stimulus.mem"):
    """Save stimulus to .mem format for Verilog $readmemb."""
    with open(filename, 'w') as f:
        f.write("// cycle clk rst a b\n")
        for s in stimulus:
            # Format: binary string for each signal
            f.write(f"{s['clk']} {s['rst']} {s['a']} {s['b']}\n")
    print(f"Saved {len(stimulus)} cycles to {filename}")

if __name__ == "__main__":
    print("Generating deterministic stimulus (seed=42)...")
    stim = generate_stimulus(num_cycles=200, seed=42)
    save_stimulus_json(stim, "tools/stimulus.json")
    save_stimulus_mem(stim, "tools/stimulus.mem")
    print("Done!")
