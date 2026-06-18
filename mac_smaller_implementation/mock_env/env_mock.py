import numpy as np

class MockALUEnv:
    """
    A mock RISC-V ALU environment.
    Takes a 32-bit instruction, decodes it into fields, and evaluates simulated branches.
    Reward is given when a new execution branch (coverage bit) is discovered.
    """
    def __init__(self):
        # We will simulate 10 distinct coverage branches
        self.num_branches = 10
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        
        # Action space: 
        # 0-31: Flip bit i in the 32-bit instruction
        # 32: Randomize opcode
        # 33: Randomize funct3
        # 34: Randomize funct7
        # 35: Randomize rs1
        # 36: Randomize rs2
        # 37: Randomize rd
        self.action_space_n = 32 + 6
        
        # State space: [opcode, rd, funct3, rs1, rs2, funct7] + coverage array
        self.state_dim = 6 + self.num_branches
        
        self.current_instruction = 0

    def reset(self):
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        # Start with a NOP or random seed
        self.current_instruction = 0x00000033 # ADD x0, x0, x0
        return self._get_state()

    def _get_state(self):
        inst = self.current_instruction
        opcode = inst & 0x7F
        rd = (inst >> 7) & 0x1F
        funct3 = (inst >> 12) & 0x7
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        funct7 = (inst >> 25) & 0x7F
        
        # Normalize fields for NN input
        state_fields = np.array([
            opcode / 127.0,
            rd / 31.0,
            funct3 / 7.0,
            rs1 / 31.0,
            rs2 / 31.0,
            funct7 / 127.0
        ], dtype=np.float32)
        
        return np.concatenate((state_fields, self.coverage))

    def step(self, action):
        """
        Apply mutation action to current instruction and evaluate coverage.
        """
        # Apply Action
        if action < 32:
            # Bit flip
            self.current_instruction ^= (1 << action)
        elif action == 32:
            # Randomize opcode
            self.current_instruction = (self.current_instruction & ~0x7F) | np.random.randint(0, 128)
        elif action == 33:
            # Randomize funct3
            self.current_instruction = (self.current_instruction & ~(0x7 << 12)) | (np.random.randint(0, 8) << 12)
        elif action == 34:
            # Randomize funct7
            self.current_instruction = (self.current_instruction & ~(0x7F << 25)) | (np.random.randint(0, 128) << 25)
        elif action == 35:
            # Randomize rs1
            self.current_instruction = (self.current_instruction & ~(0x1F << 15)) | (np.random.randint(0, 32) << 15)
        elif action == 36:
            # Randomize rs2
            self.current_instruction = (self.current_instruction & ~(0x1F << 20)) | (np.random.randint(0, 32) << 20)
        elif action == 37:
            # Randomize rd
            self.current_instruction = (self.current_instruction & ~(0x1F << 7)) | (np.random.randint(0, 32) << 7)

        # Evaluate Instruction (Mock CPU execution)
        inst = self.current_instruction
        opcode = inst & 0x7F
        funct3 = (inst >> 12) & 0x7
        funct7 = (inst >> 25) & 0x7F
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F

        hit_branches = []

        # Simulated decoder logic
        if opcode == 0x33: # R-type ALU
            hit_branches.append(0)
            if funct3 == 0x0:
                hit_branches.append(1)
                if funct7 == 0x00:
                    hit_branches.append(2) # ADD
                elif funct7 == 0x20:
                    hit_branches.append(3) # SUB
            elif funct3 == 0x7:
                hit_branches.append(4) # AND
            elif funct3 == 0x6:
                hit_branches.append(5) # OR
        elif opcode == 0x13: # I-type ALU
            hit_branches.append(6)
            if funct3 == 0x0:
                hit_branches.append(7) # ADDI
            elif funct3 == 0x7:
                hit_branches.append(8) # ANDI
        else:
            hit_branches.append(9) # Invalid / Other opcode

        # We also want to encourage varied registers, but let's stick to opcode paths for basic coverage
        
        # Calculate Reward based on NEW branches hit
        reward = 0.0
        for b in hit_branches:
            if self.coverage[b] == 0:
                reward += 1.0  # Reward for discovering a new branch!
                self.coverage[b] = 1.0
        
        # Small negative reward to discourage illegal instructions if already known
        if 9 in hit_branches and reward == 0:
            reward -= 0.01

        state = self._get_state()
        
        # End episode if we hit 100% coverage
        done = (np.sum(self.coverage) == self.num_branches)
        
        return state, reward, done, {}
