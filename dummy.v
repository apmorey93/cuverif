module dummy (clk, rst, q);
    input clk, rst;
    output q;
    
    // Simple AND gate: q = clk & rst
    // Since inputs are driven to 0 by harness, q will be 0.
    // This matches the mock-vcs output (all 0s).
    and g1 (q, clk, rst);
endmodule
