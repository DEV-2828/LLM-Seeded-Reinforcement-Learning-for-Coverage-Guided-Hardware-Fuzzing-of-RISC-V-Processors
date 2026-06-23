"""Milestone 5: Differential Fuzzer.

RL agent generates instructions and feeds them to:
    1. The direct Verilog hardware model (buggy ALU)
    2. The Python golden reference model

When outputs diverge -> BUG FOUND.
The agent is rewarded for both new coverage AND finding divergences.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import DQNAgent
from golden_model import golden_alu
from env_verilator import VerilatorALU


class BuggyVerilatorALU(VerilatorALU):
    def __init__(self):
        source_path = os.path.join(os.path.dirname(__file__), 'alu_buggy.v')
        super().__init__(source_path=source_path)


class DifferentialFuzzerEnv:
    """
    RL environment that uses the BUGGY direct Verilog ALU and cross-checks
    every instruction against the golden Python model.
    """
    def __init__(self):
        self.hw_alu = BuggyVerilatorALU()
        self.num_branches = 10
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        
        self.action_space_n = 38
        self.state_dim = 6 + self.num_branches
        
        self.current_instruction = 0
        self.rs1_data = 0
        self.rs2_data = 0
        
        # Bug tracking
        self.bugs_found = []
        self.unique_bug_signatures = set()
        
    def reset(self):
        self.coverage = np.zeros(self.num_branches, dtype=np.float32)
        self.current_instruction = 0x00000033
        self.rs1_data = np.random.randint(0, 2**32)
        self.rs2_data = np.random.randint(0, 2**32)
        
        self.hw_alu.reset()
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
        # Apply mutation to instruction
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
        
        # Also mutate operands for variety
        self.rs1_data = np.random.randint(0, 2**32)
        self.rs2_data = np.random.randint(0, 2**32)
            
        # === DIFFERENTIAL TEST ===
        # 1. Run through hardware (buggy direct Verilog runtime)
        hw_result = self.hw_alu.step(
            self.current_instruction, self.rs1_data, self.rs2_data
        )
        
        # 2. Run through golden model (trusted Python)
        golden_result, op_name = golden_alu(
            self.current_instruction, self.rs1_data, self.rs2_data
        )
        
        # 3. Get coverage from hardware
        cov_bits = self.hw_alu.get_coverage()
        
        # === REWARD CALCULATION ===
        reward = 0.0
        
        # Coverage reward
        for b in range(self.num_branches):
            if (cov_bits & (1 << b)) and self.coverage[b] == 0:
                reward += 1.0
                self.coverage[b] = 1.0
        
        # Divergence reward (BIG bonus for finding bugs!)
        if hw_result != golden_result:
            # Create a signature to track unique bugs
            sig = (op_name, self.current_instruction & 0x7F, (self.current_instruction >> 12) & 0x7)
            
            bug_record = {
                'instruction': hex(self.current_instruction),
                'rs1': hex(self.rs1_data),
                'rs2': hex(self.rs2_data),
                'hw_result': hex(hw_result),
                'golden_result': hex(golden_result),
                'operation': op_name,
                'xor_diff': hex(hw_result ^ golden_result),
            }
            self.bugs_found.append(bug_record)
            
            if sig not in self.unique_bug_signatures:
                self.unique_bug_signatures.add(sig)
                reward += 10.0  # Large reward for NEW unique bug class
            else:
                reward += 1.0   # Smaller reward for known bug class
                
        state = self._get_state()
        done = (np.sum(self.coverage) == self.num_branches)
        
        return state, reward, done, {}


def run_differential_fuzzer():
    print("=" * 60)
    print("  MILESTONE 5: Differential Fuzzer")
    print("  RL Agent + Buggy Direct Verilog vs Golden Model")
    print("=" * 60)
    
    env = DifferentialFuzzerEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    
    num_episodes = 500
    max_steps_per_episode = 100
    target_update_freq = 10
    
    total_bugs_found = 0
    start_time = time.time()
    
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
        new_bugs = len(env.bugs_found) - total_bugs_found
        total_bugs_found = len(env.bugs_found)
        
        if episode % 50 == 0:
            elapsed = time.time() - start_time
            print(f"Episode {episode:4d} | Eps: {agent.epsilon:.2f} | "
                  f"Coverage: {int(current_coverage)}/{env.num_branches} | "
                  f"Bugs this ep: {new_bugs:3d} | "
                  f"Total bugs: {total_bugs_found:5d} | "
                  f"Unique sigs: {len(env.unique_bug_signatures)} | "
                  f"Time: {elapsed:.1f}s")

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("  FUZZING COMPLETE")
    print("=" * 60)
    print(f"  Total episodes:       {num_episodes}")
    print(f"  Total time:           {elapsed:.1f}s")
    print(f"  Total divergences:    {len(env.bugs_found)}")
    print(f"  Unique bug classes:   {len(env.unique_bug_signatures)}")
    print(f"  Final coverage:       {int(np.sum(env.coverage))}/{env.num_branches}")
    
    if env.bugs_found:
        print(f"\n  --- Sample Bug Reports ---")
        # Show up to 5 unique examples
        shown_sigs = set()
        count = 0
        for bug in env.bugs_found:
            sig = bug['operation']
            if sig not in shown_sigs:
                shown_sigs.add(sig)
                count += 1
                print(f"\n  Bug #{count}:")
                print(f"    Operation:  {bug['operation']}")
                print(f"    Instruction: {bug['instruction']}")
                print(f"    rs1:         {bug['rs1']}")
                print(f"    rs2:         {bug['rs2']}")
                print(f"    HW result:   {bug['hw_result']}")
                print(f"    Golden:      {bug['golden_result']}")
                print(f"    XOR diff:    {bug['xor_diff']}")
                if count >= 5:
                    break
    else:
        print("\n  No bugs found. The hardware matches the golden model perfectly.")
    
    print("=" * 60)


if __name__ == "__main__":
    run_differential_fuzzer()
