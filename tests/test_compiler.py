"""
Tier 2 Verification: Verilog Compiler
=====================================
Tests the regex-based structural Verilog parser and Chip simulation model.
"""

import sys
import os
import pytest
import numpy as np

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import cuverif.core as cv
from cuverif.compiler import VerilogCompiler

def test_simple_combinational():
    """Test parsing and simulation of simple gates."""
    source = """
    module test_comb (a, b, y);
        input a, b;
        output y;
        wire n1;
        
        // y = (a & b) | ~a
        and g1 (n1, a, b);
        or  g2 (y, n1, a_inv);
        not g3 (a_inv, a);
    endmodule
    """
    
    batch_size = 4
    compiler = VerilogCompiler()
    chip = compiler.compile(source, batch_size)
    
    assert chip.name == "test_comb"
    assert "a" in chip.inputs
    assert "y" in chip.outputs
    assert len(chip.instances) == 3
    
    # Simulation
    # A: 0 0 1 1
    # B: 0 1 0 1
    # Y: 1 1 0 1
    # Logic: (~a) | (a&b)
    # a=0 -> 1 | 0 = 1
    # a=1, b=0 -> 0 | 0 = 0
    # a=1, b=1 -> 0 | 1 = 1
    
    a_val = np.array([0, 0, 1, 1], dtype=np.uint32)
    b_val = np.array([0, 1, 0, 1], dtype=np.uint32)
    
    t_a = cv.LogicTensor.from_host(data_v=a_val, data_s=np.ones(4, dtype=np.uint32))
    t_b = cv.LogicTensor.from_host(data_v=b_val, data_s=np.ones(4, dtype=np.uint32))
    
    chip.set_input("a", t_a)
    chip.set_input("b", t_b)
    
    chip.step()
    
    y = chip.get_output("y")
    y_v, y_s = y.cpu()
    
    expected = np.array([1, 1, 0, 1], dtype=np.uint32)
    assert np.array_equal(y_v, expected), f"Expected {expected}, got {y_v}"

def test_sequential_dff():
    """Test DFF parsing and simulation."""
    source = """
    module test_seq (clk, rst, d, q);
        input clk, rst, d;
        output q;
        
        // dff name (q, d, clk, rst)
        dff f1 (q, d, clk, rst);
    endmodule
    """
    
    batch_size = 1
    compiler = VerilogCompiler()
    chip = compiler.compile(source, batch_size)
    
    # Cycle 0: Reset=1, D=1 -> Q=0
    t_d = cv.LogicTensor.from_host(data_v=np.array([1]), data_s=np.array([1]))
    t_r = cv.LogicTensor.from_host(data_v=np.array([1]), data_s=np.array([1]))
    
    chip.set_input("d", t_d)
    chip.set_input("rst", t_r)
    chip.step()
    
    q = chip.get_output("q")
    assert q.cpu()[0][0] == 0, "Reset failed"
    
    # Cycle 1: Reset=0, D=1 -> Q=1
    t_r = cv.LogicTensor.from_host(data_v=np.array([0]), data_s=np.array([1]))
    chip.set_input("rst", t_r)
    chip.step()
    
    q = chip.get_output("q")
    assert q.cpu()[0][0] == 1, "D capture failed"

if __name__ == "__main__":
    try:
        test_simple_combinational()
        test_sequential_dff()
        print("[PASS] Verilog Compiler Verified")
    except AssertionError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
