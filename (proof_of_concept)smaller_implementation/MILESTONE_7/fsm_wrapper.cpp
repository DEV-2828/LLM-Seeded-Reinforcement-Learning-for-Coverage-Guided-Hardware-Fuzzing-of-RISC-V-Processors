#include "Vfsm.h"
#include "verilated.h"

extern "C" {
    Vfsm* fsm_init() {
        return new Vfsm();
    }
    void fsm_delete(Vfsm* fsm) {
        delete fsm;
    }
    void fsm_reset(Vfsm* fsm) {
        fsm->rst = 1;
        fsm->clk = 0;
        fsm->eval();
        fsm->clk = 1;
        fsm->eval();
        fsm->rst = 0;
        fsm->clk = 0;
        fsm->eval();
    }
    void fsm_step(Vfsm* fsm, uint32_t opcode) {
        fsm->opcode = opcode & 0x7F; // 7 bits
        fsm->clk = 1;
        fsm->eval();
        fsm->clk = 0;
        fsm->eval();
    }
    uint32_t fsm_get_state(Vfsm* fsm) {
        return fsm->state_out;
    }
    uint32_t fsm_get_coverage(Vfsm* fsm) {
        return fsm->coverage_bins;
    }
}
