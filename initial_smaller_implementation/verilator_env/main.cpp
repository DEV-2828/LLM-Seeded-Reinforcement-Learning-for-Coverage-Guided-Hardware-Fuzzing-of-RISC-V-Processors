#include <iostream>
#include <verilated.h>
#include "Valu.h"

int main(int argc, char** argv, char** env) {
    // Pass arguments to verilator
    Verilated::commandArgs(argc, argv);
    
    // Instantiate the generated model
    Valu* top = new Valu;
    
    // Initialize inputs
    top->clk = 0;
    top->rst = 1;
    top->inst = 0;
    top->rs1_data = 0;
    top->rs2_data = 0;

    // Apply reset pulse
    top->clk = 1; top->eval();
    top->clk = 0; top->eval();
    top->rst = 0;
    
    std::cout << "Testing RV32I ALU Operations..." << std::endl;
    std::cout << "-------------------------------" << std::endl;

    // Test ADD: rs1 = 15, rs2 = 10 -> rd should be 25
    // ADD is opcode=0x33, funct3=0, funct7=0. Full inst = 0x00000033
    top->inst = 0x00000033; 
    top->rs1_data = 15;
    top->rs2_data = 10;
    
    // Clock tick
    top->clk = 1; top->eval();
    top->clk = 0; top->eval();
    std::cout << "ADD (15 + 10)  => Result: " << top->rd_data << " (Expected: 25)" << std::endl;

    // Test SUB: rs1 = 15, rs2 = 10 -> rd should be 5
    // SUB is opcode=0x33, funct3=0, funct7=0x20. Full inst = 0x40000033
    top->inst = 0x40000033;
    top->rs1_data = 15;
    top->rs2_data = 10;
    
    // Clock tick
    top->clk = 1; top->eval();
    top->clk = 0; top->eval();
    std::cout << "SUB (15 - 10)  => Result: " << top->rd_data << " (Expected: 5)" << std::endl;

    // Test AND: rs1 = 0xC, rs2 = 0xA -> rd should be 0x8
    // AND is opcode=0x33, funct3=7, funct7=0. Full inst = 0x00007033
    top->inst = 0x00007033;
    top->rs1_data = 0xC;
    top->rs2_data = 0xA;
    
    // Clock tick
    top->clk = 1; top->eval();
    top->clk = 0; top->eval();
    std::cout << "AND (12 & 10)  => Result: " << top->rd_data << " (Expected: 8)" << std::endl;

    delete top;
    return 0;
}
