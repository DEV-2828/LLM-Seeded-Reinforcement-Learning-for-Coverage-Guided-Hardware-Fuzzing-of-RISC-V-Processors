import ctypes
import os

class VerilatorALU:
    def __init__(self):
        # Load the shared library
        lib_path = os.path.join(os.path.dirname(__file__), 'obj_dir', 'libalu.so')
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Cannot find {lib_path}. Run build_bridge.sh first.")
            
        self.lib = ctypes.CDLL(lib_path)
        
        # Define arg/restypes
        self.lib.alu_init.restype = ctypes.c_void_p
        self.lib.alu_delete.argtypes = [ctypes.c_void_p]
        self.lib.alu_reset.argtypes = [ctypes.c_void_p]
        self.lib.alu_step.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.alu_get_rd.argtypes = [ctypes.c_void_p]
        self.lib.alu_get_rd.restype = ctypes.c_uint32
        
        self.lib.alu_get_coverage.argtypes = [ctypes.c_void_p]
        self.lib.alu_get_coverage.restype = ctypes.c_uint32
        
        # Initialize
        self.alu = self.lib.alu_init()
        self.lib.alu_reset(self.alu)

    def step(self, inst, rs1, rs2):
        self.lib.alu_step(self.alu, inst, rs1, rs2)
        return self.lib.alu_get_rd(self.alu)

    def get_coverage(self):
        return self.lib.alu_get_coverage(self.alu)

    def __del__(self):
        if hasattr(self, 'lib') and hasattr(self, 'alu') and self.alu:
            self.lib.alu_delete(self.alu)
            self.alu = None

if __name__ == "__main__":
    alu = VerilatorALU()
    print("Testing Python-to-C++ Verilator Bridge...")
    
    # Test ADD (15 + 10 = 25)
    # ADD is opcode=0x33, funct3=0, funct7=0. Full inst = 0x00000033
    rd = alu.step(0x00000033, 15, 10)
    print(f"ADD (15 + 10) => Result: {rd} (Expected: 25)")
    
    # Test SUB (15 - 10 = 5)
    rd = alu.step(0x40000033, 15, 10)
    print(f"SUB (15 - 10) => Result: {rd} (Expected: 5)")
