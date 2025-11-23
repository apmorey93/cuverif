// Simple RISC-V ALU (Open Source Design)
// Based on RV32I ALU subset
// License: MIT

module riscv_alu (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [3:0]  op,
    output reg  [31:0] result,
    output reg         zero
);

// ALU Operations
localparam OP_ADD  = 4'b0000;
localparam OP_SUB  = 4'b0001;
localparam OP_AND  = 4'b0010;
localparam OP_OR   = 4'b0011;
localparam OP_XOR  = 4'b0100;
localparam OP_SLT  = 4'b0101;  // Set Less Than
localparam OP_SLL  = 4'b0110;  // Shift Left Logical
localparam OP_SRL  = 4'b0111;  // Shift Right Logical

// Internal wires for combinational logic
wire [31:0] add_result;
wire [31:0] sub_result;
wire [31:0] and_result;
wire [31:0] or_result;
wire [31:0] xor_result;
wire [31:0] slt_result;
wire [31:0] sll_result;
wire [31:0] srl_result;

// Combinational logic
assign add_result = a + b;
assign sub_result = a - b;
assign and_result = a & b;
assign or_result  = a | b;
assign xor_result = a ^ b;
assign slt_result = ($signed(a) < $signed(b)) ? 32'd1 : 32'd0;
assign sll_result = a << b[4:0];
assign srl_result = a >> b[4:0];

// Sequential logic with DFFs
always @(posedge clk or posedge rst) begin
    if (rst) begin
        result <= 32'h0;
        zero <= 1'b0;
    end else begin
        case (op)
            OP_ADD:  result <= add_result;
            OP_SUB:  result <= sub_result;
            OP_AND:  result <= and_result;
            OP_OR:   result <= or_result;
            OP_XOR:  result <= xor_result;
            OP_SLT:  result <= slt_result;
            OP_SLL:  result <= sll_result;
            OP_SRL:  result <= srl_result;
            default: result <= 32'h0;
        endcase
        
        zero <= (result == 32'h0);
    end
end

endmodule
