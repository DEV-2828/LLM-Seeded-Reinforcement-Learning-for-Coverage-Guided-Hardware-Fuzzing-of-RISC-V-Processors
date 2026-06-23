"""Minimal direct parser for the demo ALU Verilog files.

The demo only needs a tiny supported subset, so this parser validates the
known ALU structure and records whether the buggy AND mask is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class ParsedVerilogALU:
    source_path: str
    source_text: str
    module_name: str
    has_buggy_and_mask: bool
    coverage_bins_width: int = 10


class VerilogParseError(ValueError):
    pass


def parse_alu_source(source_path: str | Path) -> ParsedVerilogALU:
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Cannot find {path}")

    source_text = path.read_text(encoding="utf-8")

    module_match = re.search(r"\bmodule\s+(\w+)\s*\(", source_text)
    if not module_match:
        raise VerilogParseError(f"{path} does not define a module")

    module_name = module_match.group(1)
    if module_name != "alu":
        raise VerilogParseError(f"Unsupported module {module_name!r}; expected 'alu'")

    required_patterns = [
        r"opcode\s*=\s*inst\[6:0\]",
        r"funct3\s*=\s*inst\[14:12\]",
        r"funct7\s*=\s*inst\[31:25\]",
        r"always\s*@\(posedge\s+clk\)",
        r"coverage_bins\[0\]",
        r"coverage_bins\[9\]",
    ]
    for pattern in required_patterns:
        if not re.search(pattern, source_text):
            raise VerilogParseError(f"{path} is missing required ALU pattern: {pattern}")

    has_buggy_and_mask = bool(re.search(r"32'hFFFFFFFE", source_text, flags=re.IGNORECASE))

    return ParsedVerilogALU(
        source_path=str(path),
        source_text=source_text,
        module_name=module_name,
        has_buggy_and_mask=has_buggy_and_mask,
    )