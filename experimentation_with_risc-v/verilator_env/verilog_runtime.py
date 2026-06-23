"""Bit-accurate runtime for the demo ALU Verilog subset."""

from __future__ import annotations

from dataclasses import dataclass

from verilog_parser import ParsedVerilogALU


MASK32 = 0xFFFFFFFF


@dataclass
class StepResult:
    rd_data: int
    coverage_bins: int
    operation: str


class VerilogALURuntime:
    def __init__(self, model: ParsedVerilogALU):
        self.model = model
        self.reset()

    def reset(self) -> None:
        self.rd_data = 0
        self.coverage_bins = 0
        self.last_operation = "RESET"

    def step(self, inst: int, rs1_data: int, rs2_data: int, rst: bool = False) -> StepResult:
        if rst:
            self.reset()
            return StepResult(self.rd_data, self.coverage_bins, self.last_operation)

        inst = inst & MASK32
        rs1_data = rs1_data & MASK32
        rs2_data = rs2_data & MASK32

        opcode = inst & 0x7F
        funct3 = (inst >> 12) & 0x7
        funct7 = (inst >> 25) & 0x7F

        rd_data = 0
        operation = "UNKNOWN"

        if opcode == 0x33:
            self.coverage_bins |= 1 << 0
            if funct3 == 0x0:
                self.coverage_bins |= 1 << 1
                if funct7 == 0x00:
                    self.coverage_bins |= 1 << 2
                    rd_data = (rs1_data + rs2_data) & MASK32
                    operation = "ADD"
                elif funct7 == 0x20:
                    self.coverage_bins |= 1 << 3
                    rd_data = (rs1_data - rs2_data) & MASK32
                    operation = "SUB"
                else:
                    rd_data = 0
                    operation = "R-type funct3=0 unknown funct7"
            elif funct3 == 0x7:
                self.coverage_bins |= 1 << 4
                and_result = rs1_data & rs2_data
                if self.model.has_buggy_and_mask:
                    rd_data = and_result & 0xFFFFFFFE
                    operation = "AND_BUGGY"
                else:
                    rd_data = and_result & MASK32
                    operation = "AND"
            elif funct3 == 0x6:
                self.coverage_bins |= 1 << 5
                rd_data = (rs1_data | rs2_data) & MASK32
                operation = "OR"
            else:
                rd_data = 0
                operation = "R-type unknown funct3"
        elif opcode == 0x13:
            self.coverage_bins |= 1 << 6
            if funct3 == 0x0:
                self.coverage_bins |= 1 << 7
                operation = "ADDI"
            elif funct3 == 0x7:
                self.coverage_bins |= 1 << 8
                operation = "ANDI"
            else:
                operation = "I-type (dummy)"
            rd_data = 0
        else:
            self.coverage_bins |= 1 << 9
            rd_data = 0
            operation = "Unknown opcode"

        self.rd_data = rd_data
        self.last_operation = operation
        return StepResult(rd_data=self.rd_data, coverage_bins=self.coverage_bins, operation=operation)

    def get_coverage(self) -> int:
        return self.coverage_bins