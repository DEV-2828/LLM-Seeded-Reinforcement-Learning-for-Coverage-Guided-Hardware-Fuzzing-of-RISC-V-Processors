import os
import ctypes

class VerilatorPicoRV32:
    def __init__(self):
        lib_path = os.path.join(os.path.dirname(__file__), 'obj_dir', 'libpicorv32.so')
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Cannot find {lib_path}.")
            
        self.lib = ctypes.CDLL(lib_path)
        self.lib.picorv32_init.restype = ctypes.c_void_p
        self.top = self.lib.picorv32_init()
        self.lib.picorv32_reset(self.top)

    def load_instruction(self, addr, inst):
        self.lib.picorv32_load_instruction(self.top, ctypes.c_uint32(addr), ctypes.c_uint32(inst))

    def step(self):
        self.lib.picorv32_step(self.top)

    def get_trap(self):
        return self.lib.picorv32_get_trap(self.top)

def test_instruction_sequence():
    print("Initializing PicoRV32 Core...")
    core = VerilatorPicoRV32()
    
    # We will load a simple multi-instruction program into memory.
    # Because PicoRV32 uses a multi-cycle architecture, we must step the 
    # clock enough times for all instructions to fetch, decode, and execute.
    
    # Assembly sequence:
    # 0x0: ADDI x1, x0, 15  => 0x00f00093
    # 0x4: ADDI x2, x0, 20  => 0x01400113
    # 0x8: ADD  x3, x1, x2  => 0x002081b3
    # 0xc: JAL  x0, 0x0     => 0xff5ff06f (infinite loop back to 0x0)
    
    program = [
        0x00f00093, # ADDI x1, x0, 15
        0x01400113, # ADDI x2, x0, 20
        0x002081b3, # ADD  x3, x1, x2
        0xff5ff06f  # JAL  x0, -12 (jump to 0x0)
    ]
    
    print("\nLoading Program into Memory:")
    for i, inst in enumerate(program):
        addr = i * 4
        print(f"Address 0x{addr:02x} : 0x{inst:08x}")
        core.load_instruction(addr, inst)
        
    print("\nExecuting Program (stepping 50 cycles)...")
    # 50 cycles is enough to execute the 4 instructions a few times (since JAL loops)
    for cycle in range(50):
        core.step()
        trap_state = core.get_trap()
        
        # If the core traps, it means it hit an illegal instruction or memory fault
        if trap_state == 1:
            print(f"Cycle {cycle}: ⚠️ TRAP TRIGGERED! (This shouldn't happen with our valid loop)")
            break
            
    if trap_state == 0:
        print("Cycle 50: Executed successfully without trapping! The infinite loop worked.")

if __name__ == "__main__":
    test_instruction_sequence()
