#include "Valu.h"
#include <verilated.h>

extern "C" {
    Valu* alu_init() {
        return new Valu();
    }

    void alu_delete(Valu* alu) {
        delete alu;
    }

    void alu_reset(Valu* alu) {
        alu->clk = 0;
        alu->rst = 1;
        alu->inst = 0;
        alu->rs1_data = 0;
        alu->rs2_data = 0;
        alu->clk = 1; alu->eval();
        alu->clk = 0; alu->eval();
        alu->rst = 0;
    }

    void alu_step(Valu* alu, uint32_t inst, uint32_t rs1, uint32_t rs2) {
        alu->inst = inst;
        alu->rs1_data = rs1;
        alu->rs2_data = rs2;
        
        alu->clk = 1; alu->eval();
        alu->clk = 0; alu->eval();
    }

    uint32_t alu_get_rd(Valu* alu) {
        return alu->rd_data;
    }

    uint32_t alu_get_coverage(Valu* alu) {
        return alu->coverage_bins;
    }
}
