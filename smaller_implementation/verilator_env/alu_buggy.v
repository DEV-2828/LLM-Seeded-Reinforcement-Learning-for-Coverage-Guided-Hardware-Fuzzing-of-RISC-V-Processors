// alu_buggy.v — ALU with an intentionally injected subtle bug.
//
// BUG INJECTED: The AND operation (funct3 == 3'b111) has a single-bit
// wiring error that masks out bit 0 of the result.
//   Correct:  rd_data <= rs1_data & rs2_data
//   Buggy:    rd_data <= (rs1_data & rs2_data) & 32'hFFFFFFFE
//
// This means AND(0xF, 0xF) returns 0xE instead of 0xF.
// A very subtle hardware bug that only manifests when both operands
// have bit 0 set and the AND operation is used.

module alu (
    input clk,
    input rst,
    /* verilator lint_off UNUSEDSIGNAL */
    input [31:0] inst,
    /* verilator lint_on UNUSEDSIGNAL */
    input [31:0] rs1_data,
    input [31:0] rs2_data,
    output reg [31:0] rd_data,
    output reg [9:0] coverage_bins
);

    // Simple coverage tracking (10 bins like the mock environment)

    wire [6:0] opcode = inst[6:0];
    wire [2:0] funct3 = inst[14:12];
    wire [6:0] funct7 = inst[31:25];

    always @(posedge clk) begin
        if (rst) begin
            rd_data <= 32'b0;
            coverage_bins <= 10'b0;
        end else begin
            // Simplified RV32I ALU logic
            if (opcode == 7'h33) begin // R-type instructions
                coverage_bins[0] <= 1'b1;
                case (funct3)
                    3'b000: begin
                        coverage_bins[1] <= 1'b1;
                        if (funct7 == 7'h00) begin
                            coverage_bins[2] <= 1'b1;
                            rd_data <= rs1_data + rs2_data; // ADD
                        end else if (funct7 == 7'h20) begin
                            coverage_bins[3] <= 1'b1;
                            rd_data <= rs1_data - rs2_data; // SUB
                        end else begin
                            rd_data <= 32'b0;
                        end
                    end
                    3'b111: begin 
                        coverage_bins[4] <= 1'b1;
                        // *** BUG: bit 0 masked out due to wiring error ***
                        rd_data <= (rs1_data & rs2_data) & 32'hFFFFFFFE;
                    end
                    3'b110: begin
                        coverage_bins[5] <= 1'b1;
                        rd_data <= rs1_data | rs2_data; // OR
                    end
                    default: rd_data <= 32'b0;
                endcase
            end else if (opcode == 7'h13) begin // I-type ALU (simulated)
                coverage_bins[6] <= 1'b1;
                if (funct3 == 3'b000) coverage_bins[7] <= 1'b1; // ADDI
                else if (funct3 == 3'b111) coverage_bins[8] <= 1'b1; // ANDI
                rd_data <= 32'b0; // Dummy
            end else begin
                coverage_bins[9] <= 1'b1; // Other
                rd_data <= 32'b0;
            end
        end
    end

endmodule
