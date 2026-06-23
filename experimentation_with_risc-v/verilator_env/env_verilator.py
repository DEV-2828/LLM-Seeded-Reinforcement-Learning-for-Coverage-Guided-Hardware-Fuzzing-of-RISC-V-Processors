from __future__ import annotations

import os
from pathlib import Path

from verilog_parser import parse_alu_source
from verilog_runtime import VerilogALURuntime


class VerilatorALU:
    def __init__(self, source_path: str | os.PathLike[str] | None = None):
        if source_path is None:
            source_path = Path(__file__).with_name("alu.v")

        self.model = parse_alu_source(source_path)
        self.runtime = VerilogALURuntime(self.model)

    def reset(self):
        self.runtime.reset()

    def step(self, inst, rs1, rs2):
        return self.runtime.step(inst, rs1, rs2).rd_data

    def get_coverage(self):
        return self.runtime.get_coverage()

if __name__ == "__main__":
    alu = VerilatorALU()
    print("Testing direct Verilog parser/runtime...")
    
    # Test ADD (15 + 10 = 25)
    # ADD is opcode=0x33, funct3=0, funct7=0. Full inst = 0x00000033
    rd = alu.step(0x00000033, 15, 10)
    print(f"ADD (15 + 10) => Result: {rd} (Expected: 25)")
    
    # Test SUB (15 - 10 = 5)
    rd = alu.step(0x40000033, 15, 10)
    print(f"SUB (15 - 10) => Result: {rd} (Expected: 5)")
