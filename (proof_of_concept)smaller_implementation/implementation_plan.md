# Scaled-Down RL Hardware Fuzzer Implementation Plan

This plan outlines an expanded, step-by-step approach to building the RL-guided hardware fuzzer. It is specifically designed to run on resource-constrained environments (like a 16GB RAM laptop with an iGPU) for initial phases, before eventually scaling up to environments like Google Colab.

We will use **PyTorch** for the reinforcement learning components to start, keeping the option to evaluate TensorFlow later if performance tuning dictates.

## User Review Required

> [!IMPORTANT]
> Please review the expanded milestones. I have broken down the process into 7 detailed stages. If you approve of this roadmap, we will begin execution of **Milestone 1** immediately on your local system.

## Proposed Roadmap: Iterative Scaling

To ensure smooth progress and easy debugging, we have divided the project into finer-grained milestones.

### Milestone 1: Pure Python Toy Environment (Local System - Proof of Concept)
**Goal:** Validate the PyTorch DQN logic and RL algorithms locally without any Verilator/C++ overhead.
- **Environment:** A mock RISC-V ALU written entirely in Python. It decodes 32-bit instructions (e.g., ADD, SUB, AND, OR) and returns a "coverage bitmap" based on which internal Python `if/else` branches are executed.
- **RL Agent:** A lightweight PyTorch DQN.
- **State:** 32-bit instruction broken into fields + the coverage bitmap.
- **Actions:** Bit-flips, randomizing specific instruction fields (opcode, rs1, rs2, rd).
- **Reward:** +1 for discovering a new execution branch in the Python ALU.
- **Outcome:** A working PyTorch RL loop that successfully maximizes coverage of a Python function faster than random fuzzing.

### Milestone 2: Verilog Synthesis Baseline (Toolchain Verification)
**Goal:** Verify that a simple Verilog model can be compiled into a C++ simulation locally or on Colab. No RL involved yet.
- **Target:** A simple `alu.v` (Verilog) file representing a basic RISC-V ALU.
- **Action:** Compile `alu.v` using Verilator into a C++ model (`Valu`).
- **Outcome:** A C++ executable that can run the Verilog model and print simple outputs, proving the Verilator toolchain is functional.

### Milestone 3: The Python-to-C++ Bridge
**Goal:** Establish a programmatic connection between our Python environment and the compiled C++ Verilator model.
- **Action:** Use `pybind11` (or a lightweight `subprocess` wrapper if preferred) to allow Python to instantiate the C++ ALU, feed it a 32-bit instruction, step the clock, and read the output/coverage signals.
- **Outcome:** A Python script that can directly drive the Verilog simulation cycle-by-cycle.

### Milestone 4: RL + Verilator Integration
**Goal:** Connect the PyTorch DQN from Milestone 1 to the Verilator bridge from Milestone 3.
- **Action:** Swap out the mock Python ALU for the real Verilator ALU.
- **Reward:** Extract actual toggle coverage (which wires flipped) from the Verilator simulation as the reward signal.
- **Outcome:** The RL agent successfully learns to maximize hardware toggle coverage in a real Verilog module.

### Milestone 5: Differential Testing & Bug Hunting
**Goal:** Implement the full fuzzing loop to actively find bugs.
- **Golden Model:** A trusted Python function calculating the expected result of an ALU operation.
- **The Loop:** RL agent generates instruction -> sends to Verilator `alu.v` -> sends to Golden Model -> cross-checks results.
- **Bug Injection:** We will intentionally inject a subtle logic flaw into `alu.v` and prove the RL agent can generate the specific instruction to trigger it.
- **Outcome:** A functional differential fuzzing loop capable of logging genuine divergences.

### Milestone 6: Cloud Migration & Parallel Scaling
**Goal:** Shift the working codebase to Google Colab (Linux) to unlock more compute.
- **Action:** Move the Milestone 5 codebase to Colab.
- **Scaling:** Implement a basic multi-worker architecture. Have 2-4 parallel Verilator instances feeding experience to a central PyTorch DQN.
- **Outcome:** Accelerated fuzzing throughput utilizing cloud resources.

### Milestone 7: Advanced CPU Subsystem (Future)
**Goal:** Fuzz a more complex piece of hardware than an ALU.
- **Action:** Replace the ALU with a more complex Verilog model, such as a tiny pipelined core or a specific RISC-V subsystem (like PicoRV32's control unit).
- **Metric:** Transition from basic toggle coverage to FSM (Finite State Machine) state coverage.

---

## Proposed Changes

We will implement the components described in the `smaller_implementation_explanation.md` step-by-step. All files will be placed in the `smaller_implementation/` directory.

### Milestone 1: RL Agent & Mock Environment

#### [NEW] [agent.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/agent.py)
PyTorch Deep Q-Network implementation (Replay Buffer, Q-Network, Epsilon-greedy action selection) with state vector composed of instruction fields and coverage array, and 38 possible actions.

#### [NEW] [mock_env/env_mock.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/mock_env/env_mock.py)
Python-based mock ALU environment `MockALUEnv` for early testing.

#### [NEW] [train_mock.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/train_mock.py)
The training loop for Milestone 1, running the agent through the mock environment for 500 episodes to verify learning capability.

### Milestone 2-4: Verilator Environment

#### [NEW] [verilator_env/alu.v](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/verilator_env/alu.v)
Clean Verilog implementation of a simple ALU.

#### [NEW] [verilator_env/alu_buggy.v](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/verilator_env/alu_buggy.v)
Verilog ALU with an intentionally injected bug in the AND operation.

#### [NEW] [verilator_env/alu_wrapper.cpp](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/verilator_env/alu_wrapper.cpp)
C++ wrapper exposing a simple C API to interact with the C++ model compiled by Verilator.

#### [NEW] [verilator_env/env_verilator.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/verilator_env/env_verilator.py)
Python script using `ctypes` to load the shared library and call the C API.

#### [NEW] [golden_model.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/golden_model.py)
Pure Python `golden_alu` function serving as the trusted source of truth.

### Milestone 5: Differential Fuzzer

#### [NEW] [differential_fuzzer.py](file:///home/dev/LLM-Seeded%20Reinforcement%20Learning%20for%20Coverage-Guided%20Hardware%20Fuzzing%20of%20RISC-V%20Processors/smaller_implementation/differential_fuzzer.py)
The core fuzzing script combining the RL Agent, the Buggy Verilator hardware model, and the Golden Python Model to discover logic errors and generate unique bug signatures.

## Verification Plan (Milestone 1)
1. **Convergence Check:** Run `train_mock.py`. The agent's coverage should reach 100% (all mock ALU branches visited) significantly faster than a purely random mutation baseline.
2. **Metrics:** We will plot "Coverage vs. Steps" to visually confirm the RL agent is learning over time.
