import numpy as np
import sys
import os

# Add parent directory to path to import agent.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import DQNAgent
from env_verilator import VerilatorALU

class RLVerilatorEnv:
    def __init__(self):
        self.alu = VerilatorALU()
        self.num_branches = 10
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        
        # Action space: same as mock
        # 0-31: bit flips
        # 32-37: randomize specific fields
        self.action_space_n = 38
        self.state_dim = 6 + self.num_branches
        
        self.current_instruction = 0
        
    def reset(self):
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        self.current_instruction = 0x00000033 # ADD x0, x0, x0
        
        # Reset ALU hardware
        self.alu.lib.alu_reset(self.alu.alu)
        return self._get_state()
        
    def _get_state(self):
        inst = self.current_instruction
        opcode = inst & 0x7F
        rd = (inst >> 7) & 0x1F
        funct3 = (inst >> 12) & 0x7
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        funct7 = (inst >> 25) & 0x7F
        
        state_fields = np.array([
            opcode / 127.0, rd / 31.0, funct3 / 7.0,
            rs1 / 31.0, rs2 / 31.0, funct7 / 127.0
        ], dtype=np.float32)
        
        return np.concatenate((state_fields, self.coverage))
        
    def step(self, action):
        # Apply mutation
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
            
        # Execute instruction in Verilator (with dummy rs1/rs2 data for now)
        self.alu.step(self.current_instruction, 0, 0)
        
        # Get coverage from Verilog simulation
        cov_bits = self.alu.get_coverage()
        
        reward = 0.0
        for b in range(self.num_branches):
            if (cov_bits & (1 << b)) and self.coverage[b] == 0:
                reward += 1.0
                self.coverage[b] = 1.0
                
        state = self._get_state()
        done = (np.sum(self.coverage) == self.num_branches)
        
        return state, reward, done, {}

def train_verilator():
    print("Starting Training Loop with Real Verilator Environment...")
    env = RLVerilatorEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    
    num_episodes = 500
    max_steps_per_episode = 100
    target_update_freq = 10
    
    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0
        
        for step in range(max_steps_per_episode):
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            
            agent.step(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            
            if done:
                break
                
        agent.decay_epsilon()
        if episode % target_update_freq == 0:
            agent.update_target_network()
            
        current_coverage = np.sum(env.coverage)
        if episode % 50 == 0:
            print(f"Episode {episode}, Epsilon: {agent.epsilon:.2f}, Coverage: {current_coverage}/{env.num_branches}, Reward: {total_reward}")

    print("Training finished!")
    print(f"Final Coverage: {np.sum(env.coverage)}/{env.num_branches}")

if __name__ == "__main__":
    train_verilator()
