import ctypes
import os

class VerilatorPicoRV32:
    def __init__(self):
        # Load the shared library
        lib_path = os.path.join(os.path.dirname(__file__), 'obj_dir', 'libpicorv32.so')
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Cannot find {lib_path}. Run build_picorv32_bridge.sh first.")
            
        self.lib = ctypes.CDLL(lib_path)
        
        # Define arg/restypes
        self.lib.picorv32_init.restype = ctypes.c_void_p
        
        self.lib.picorv32_delete.argtypes = [ctypes.c_void_p]
        self.lib.picorv32_reset.argtypes = [ctypes.c_void_p]
        self.lib.picorv32_load_instruction.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.picorv32_step.argtypes = [ctypes.c_void_p]
        
        self.lib.picorv32_get_trap.argtypes = [ctypes.c_void_p]
        self.lib.picorv32_get_trap.restype = ctypes.c_uint32
        
        self.lib.picorv32_get_coverage.argtypes = [ctypes.c_void_p]
        self.lib.picorv32_get_coverage.restype = ctypes.c_uint32
        
        # Initialize
        self.top = self.lib.picorv32_init()
        self.lib.picorv32_reset(self.top)

    def load_instruction(self, addr, inst):
        self.lib.picorv32_load_instruction(self.top, addr, inst)

    def step(self):
        self.lib.picorv32_step(self.top)

    def get_trap(self):
        return self.lib.picorv32_get_trap(self.top)

    def get_coverage(self):
        return self.lib.picorv32_get_coverage(self.top)

    def __del__(self):
        if hasattr(self, 'lib') and hasattr(self, 'top') and self.top:
            self.lib.picorv32_delete(self.top)
            self.top = None

if __name__ == "__main__":
    core = VerilatorPicoRV32()
    print("Testing Python-to-C++ Verilator Bridge for PicoRV32...")
    
    # Let's load a simple ADD instruction: ADD x1, x2, x3
    # Opcode: 0110011 (0x33), rd=1 (00001), funct3=0 (000), rs1=2 (00010), rs2=3 (00011), funct7=0 (0000000)
    # Binary: 0000000 00011 00010 000 00001 0110011 = 0x003100b3
    inst = 0x003100b3
    
    print(f"Loading instruction: 0x{inst:08x} at address 0x0")
    core.load_instruction(0x0, inst)
    
    # We step the core a few times. PicoRV32 takes multiple cycles per instruction.
    print("Stepping clock 10 times...")
    for i in range(10):
        core.step()
        
    print(f"Trap state: {core.get_trap()}")
    print("Test finished successfully!")
