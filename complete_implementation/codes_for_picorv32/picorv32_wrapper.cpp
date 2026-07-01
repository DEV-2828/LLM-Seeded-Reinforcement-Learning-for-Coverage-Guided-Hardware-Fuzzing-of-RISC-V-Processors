#include "Vpicorv32_top.h"
#include <verilated.h>

double sc_time_stamp() { return 0; }

extern "C" {
    Vpicorv32_top* picorv32_init() {
        return new Vpicorv32_top();
    }

    void picorv32_delete(Vpicorv32_top* top) {
        delete top;
    }

    void picorv32_reset(Vpicorv32_top* top) {
        top->clk = 0;
        top->rst = 1;
        top->load_en = 0;
        top->load_addr = 0;
        top->load_data = 0;
        
        // Assert reset for a few cycles
        for(int i=0; i<5; i++) {
            top->clk = 1; top->eval();
            top->clk = 0; top->eval();
        }
        top->rst = 0;
    }

    void picorv32_load_instruction(Vpicorv32_top* top, uint32_t addr, uint32_t inst) {
        top->load_en = 1;
        top->load_addr = addr;
        top->load_data = inst;
        
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
        
        top->load_en = 0;
    }

    void picorv32_step(Vpicorv32_top* top) {
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
    }

    uint32_t picorv32_get_trap(Vpicorv32_top* top) {
        return top->trap;
    }

    uint32_t picorv32_get_coverage(Vpicorv32_top* top) {
        // Placeholder: Will be replaced by Verilator's native coverage extraction
        // or a dedicated FSM coverage port in future iterations.
        return 0; 
    }
}
