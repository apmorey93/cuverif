module simple_cpu (
    input clk,
    input rst,
    input cmd,
    output result
);

    wire w_inv_cmd;
    wire w_and_res;
    wire w_dff_out;

    // Logic Gates
    not u_not (w_inv_cmd, cmd);
    and u_and (w_and_res, w_inv_cmd, w_dff_out);

    // Flip Flop: Output feeds back into AND gate
    // dff(q, d, clk, rst)
    dff u_dff (w_dff_out, w_and_res, clk, rst);

    // Output assignment (Buffer)
    or u_buf (result, w_dff_out, w_dff_out);

endmodule
