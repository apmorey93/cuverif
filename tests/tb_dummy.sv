`timescale 1ns / 1ps

//==============================================================================
// VCS Golden Testbench for dummy.v
// Auto-generated for CuVerif equivalence testing
//==============================================================================

module tb_dummy;

// Signals
reg clk;
reg rst;
wire q;

// Instantiate DUT
dummy dut (
    .clk(clk),
    .rst(rst),
    .q(q)
);

// Stimulus from file
reg [1:0] stim_mem [0:199];  // 200 cycles, 2 bits per cycle (clk, rst)
integer cycle;

initial begin
    // Load stimulus
    $readmemb("tools/stimulus.mem", stim_mem);
    
    // VCD dump for comparison
    $dumpfile("tools/dummy_vcs.vcd");
    $dumpvars(0, tb_dummy);
    
    // Apply stimulus
    for (cycle = 0; cycle < 200; cycle = cycle + 1) begin
        {clk, rst} = stim_mem[cycle];
        #10;  // 10ns per cycle
    end
    
    $finish;
end

endmodule
