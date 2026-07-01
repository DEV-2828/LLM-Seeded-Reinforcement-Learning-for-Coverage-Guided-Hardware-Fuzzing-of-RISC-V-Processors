`timescale 1ns / 1ps

module picorv32_top (
    input clk,
    input rst, // active high for wrapper compatibility
    
    // Instruction Loading interface
    input load_en,
    input [31:0] load_addr,
    input [31:0] load_data,
    
    // Status
    output trap
);

    // Mock Memory (1024 words = 4KB)
    reg [31:0] memory [0:1023];
    
    always @(posedge clk) begin
        if (load_en) begin
            memory[load_addr[11:2]] <= load_data; // Word addressable
        end
    end
    
    // picorv32 memory interface
    wire mem_valid;
    wire mem_instr;
    reg mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0] mem_wstrb;
    reg [31:0] mem_rdata;
    
    always @(posedge clk) begin
        if (rst) begin
            mem_ready <= 0;
            mem_rdata <= 0;
        end else begin
            mem_ready <= mem_valid && !mem_ready; // 1 cycle latency
            if (mem_valid && !mem_ready) begin
                if (mem_wstrb != 4'b0000) begin
                    // Basic write (assuming full 32-bit for simple fuzzer memory)
                    memory[mem_addr[11:2]] <= mem_wdata;
                end else begin
                    mem_rdata <= memory[mem_addr[11:2]];
                end
            end
        end
    end
    
    // Instantiate core
    picorv32 #(
        .COMPRESSED_ISA(0),
        .ENABLE_MUL(0),
        .ENABLE_DIV(0),
        .ENABLE_IRQ(0),
        .PROGADDR_RESET(32'h0000_0000)
    ) core (
        .clk(clk),
        .resetn(~rst),
        .trap(trap),
        .mem_valid(mem_valid),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr(mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata)
    );

endmodule
