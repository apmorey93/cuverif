"""
Mock VCS Mode - Generate "VCS" Trace Using CPU Backend
=======================================================

For development without access to VCS, this script generates a mock
VCS trace by running the design on CPU backend (golden reference).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import json
from tools.trace_cuverif import trace_cuverif

def mock_vcs_simulation(netlist_path, stimulus_path, output_path):
    """
    Generate a mock "VCS" trace using CPU backend.
    
    This is just CuVerif CPU backend output, but we treat it as
    the "golden" VCS reference for testing the harness itself.
    """
    print("=" * 70)
    print("MOCK VCS MODE - Using CPU Backend as Golden Reference")
    print("=" * 70)
    print()
    print("NOTE: This is NOT real VCS. It's the CPU backend output.")
    print("      Use this mode only for testing the harness workflow.")
    print()
    
    # Use the same trace script, just rename output
    trace_cuverif(netlist_path, stimulus_path, output_path)
    
    print()
    print(f"Mock VCS trace saved to: {output_path}")
    print("This can now be compared against CUDA backend to verify consistency.")

if __name__ == "__main__":
    netlist = "dummy.v"
    stimulus = "tools/stimulus.json"
    output = "tools/trace_vcs_mock.json"
    
    mock_vcs_simulation(netlist, stimulus, output)
