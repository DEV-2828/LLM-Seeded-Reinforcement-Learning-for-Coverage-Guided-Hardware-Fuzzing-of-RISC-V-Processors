// fsm.v - A simple multi-cycle instruction FSM Control Unit
module fsm (
    input clk,
    input rst,
    input [6:0] opcode,
    output reg [2:0] state_out,
    output reg [7:0] coverage_bins
);

    parameter IDLE      = 3'd0;
    parameter FETCH     = 3'd1;
    parameter DECODE    = 3'd2;
    parameter EXEC_ALU  = 3'd3;
    parameter EXEC_MEM  = 3'd4;
    parameter MEM_WAIT  = 3'd5;
    parameter WRITEBACK = 3'd6;
    parameter TRAP      = 3'd7;

    reg [2:0] state;
    
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            coverage_bins <= 8'b0;
            state_out <= IDLE;
        end else begin
            case (state)
                IDLE:      state <= FETCH;
                FETCH:     state <= DECODE;
                DECODE: begin
                    if (opcode == 7'h33) state <= EXEC_ALU; // R-Type
                    else if (opcode == 7'h03 || opcode == 7'h23) state <= EXEC_MEM; // Load/Store
                    else if (opcode == 7'h7F) state <= TRAP; // Invalid/Custom
                    else state <= FETCH;
                end
                EXEC_ALU:  state <= WRITEBACK;
                EXEC_MEM:  state <= MEM_WAIT;
                MEM_WAIT: begin
                    if (opcode == 7'h00)
                        state <= WRITEBACK;
                    else
                        state <= MEM_WAIT;
                end
                WRITEBACK: state <= FETCH;
                TRAP:      state <= TRAP; // Stuck until reset
                default:   state <= IDLE;
            endcase
            
            coverage_bins[state] <= 1'b1;
            state_out <= state;
        end
    end
endmodule
