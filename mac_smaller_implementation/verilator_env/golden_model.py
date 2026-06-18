"""
Golden Reference Model for RISC-V ALU.

This is the trusted "ground truth" implementation.
If the Verilator hardware model disagrees with this, we've found a bug.
"""

def golden_alu(inst, rs1_data, rs2_data):
    """
    Compute the expected ALU result for a given 32-bit RISC-V instruction.
    
    Returns:
        (rd_data, op_name): The expected output value and a human-readable operation name.
    """
    opcode = inst & 0x7F
    funct3 = (inst >> 12) & 0x7
    funct7 = (inst >> 25) & 0x7F
    
    # Mask to 32-bit unsigned
    MASK32 = 0xFFFFFFFF
    
    if opcode == 0x33:  # R-type
        if funct3 == 0x0:
            if funct7 == 0x00:
                return ((rs1_data + rs2_data) & MASK32, "ADD")
            elif funct7 == 0x20:
                return ((rs1_data - rs2_data) & MASK32, "SUB")
            else:
                return (0, "R-type funct3=0 unknown funct7")
        elif funct3 == 0x7:
            return ((rs1_data & rs2_data) & MASK32, "AND")
        elif funct3 == 0x6:
            return ((rs1_data | rs2_data) & MASK32, "OR")
        else:
            return (0, "R-type unknown funct3")
    elif opcode == 0x13:  # I-type (dummy in our ALU)
        return (0, "I-type (dummy)")
    else:
        return (0, "Unknown opcode")


if __name__ == "__main__":
    # Quick self-test
    tests = [
        (0x00000033, 15, 10, 25, "ADD"),
        (0x40000033, 15, 10, 5,  "SUB"),
        (0x00007033, 0xF, 0xA, 0xA, "AND"),
        (0x00006033, 0xF, 0xA, 0xF, "OR"),
    ]
    
    print("Golden Model Self-Test:")
    all_pass = True
    for inst, rs1, rs2, expected, name in tests:
        result, op = golden_alu(inst, rs1, rs2)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {name}: {op}({rs1}, {rs2}) = {result} (expected {expected}) [{status}]")
    
    print(f"\n{'All tests passed!' if all_pass else 'SOME TESTS FAILED!'}")
