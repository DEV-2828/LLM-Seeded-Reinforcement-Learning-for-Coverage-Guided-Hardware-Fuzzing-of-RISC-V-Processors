import ctypes
import os
import numpy as np
from golden_fsm import GoldenFSM

class VerilatorFSM:
    def __init__(self):
        lib_path = os.path.join(os.path.dirname(__file__), 'obj_dir_buggy', 'libfsm_buggy.so')
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Cannot find {lib_path}. Run build_fsm.sh first.")
        
        self.lib = ctypes.CDLL(lib_path)
        
        self.lib.fsm_init.restype = ctypes.c_void_p
        self.lib.fsm_delete.argtypes = [ctypes.c_void_p]
        self.lib.fsm_reset.argtypes = [ctypes.c_void_p]
        self.lib.fsm_step.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        
        self.lib.fsm_get_state.argtypes = [ctypes.c_void_p]
        self.lib.fsm_get_state.restype = ctypes.c_uint32
        
        self.lib.fsm_get_coverage.argtypes = [ctypes.c_void_p]
        self.lib.fsm_get_coverage.restype = ctypes.c_uint32
        
        self.fsm = self.lib.fsm_init()
        self.lib.fsm_reset(self.fsm)

    def reset(self):
        self.lib.fsm_reset(self.fsm)

    def step(self, opcode):
        self.lib.fsm_step(self.fsm, opcode)
        return self.lib.fsm_get_state(self.fsm)

    def get_coverage(self):
        return self.lib.fsm_get_coverage(self.fsm)


class FSMFuzzerEnv:
    def __init__(self):
        self.hw_fsm = VerilatorFSM()
        self.golden = GoldenFSM()
        
        self.num_states = 8
        self.coverage = np.zeros(self.num_states, dtype=np.float32)
        
        self.action_space_n = 42
        self.state_dim = self.num_states + self.num_states
        
        self.current_instruction = 0
        self.bugs_found = []
        self.unique_bug_signatures = set()
        
    def reset(self):
        self.hw_fsm.reset()
        self.golden.reset()
        self.coverage = np.zeros(self.num_states, dtype=np.float32)
        self.current_instruction = 0x00000033
        return self._get_state()
        
    def _get_state(self):
        hw_state = self.hw_fsm.lib.fsm_get_state(self.hw_fsm.fsm)
        state_one_hot = np.zeros(self.num_states, dtype=np.float32)
        if hw_state < self.num_states:
            state_one_hot[hw_state] = 1.0
            
        return np.concatenate((state_one_hot, self.coverage))
        
    def step(self, action):
        if action < 32:
            self.current_instruction ^= (1 << action)
        elif action == 32:
            self.current_instruction = (self.current_instruction & ~0x7F) | np.random.randint(0, 128)
        elif action == 33:
            self.current_instruction = (self.current_instruction & ~(0x7 << 12)) | (np.random.randint(0, 8) << 12)
        elif action == 34:
            self.current_instruction = (self.current_instruction & ~(0x7F << 25)) | (np.random.randint(0, 128) << 25)
        elif action == 35:
            self.current_instruction = (self.current_instruction & ~(0x1F << 15)) | (np.random.randint(0, 32) << 15)
        elif action == 36:
            self.current_instruction = (self.current_instruction & ~(0x1F << 20)) | (np.random.randint(0, 32) << 20)
        elif action == 37:
            self.current_instruction = (self.current_instruction & ~(0x1F << 7)) | (np.random.randint(0, 32) << 7)
        elif action == 38:
            self.current_instruction = (self.current_instruction & ~0x7F) | 0x7F # Dictionary: TRAP opcode
        elif action == 39:
            self.current_instruction = (self.current_instruction & ~0x7F) | 0x00 # Dictionary: EXIT WAIT opcode
        elif action == 40:
            self.current_instruction = (self.current_instruction & ~0x7F) | 0x33 # Dictionary: R-TYPE opcode
        elif action == 41:
            self.current_instruction = (self.current_instruction & ~0x7F) | 0x03 # Dictionary: LOAD opcode
            
        opcode = self.current_instruction & 0x7F
        
        hw_result_state = self.hw_fsm.step(opcode)
        golden_result_state = self.golden.step(opcode)
        
        cov_bits = self.hw_fsm.get_coverage()
        reward = 0.0
        
        for b in range(self.num_states):
            if (cov_bits & (1 << b)) and self.coverage[b] == 0:
                reward += 1.0
                self.coverage[b] = 1.0
                
        if hw_result_state != golden_result_state:
            sig = (hw_result_state, golden_result_state)
            if sig not in self.unique_bug_signatures:
                self.unique_bug_signatures.add(sig)
                reward += 10.0
            else:
                reward += 1.0
                
            bug_record = {
                'opcode': hex(opcode),
                'hw_state': hw_result_state,
                'golden_state': golden_result_state
            }
            self.bugs_found.append(bug_record)
            
        state = self._get_state()
        done = (np.sum(self.coverage) == self.num_states) or (hw_result_state != golden_result_state)
        
        return state, reward, done, {}
