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

## Proposed Changes for Milestone 1

We will work primarily in the `initial_smaller_implementation/` directory locally.

#### [NEW] [env_mock.py](file:///c:/Devopam/Engineering_CSE/SEM-5/SEM5_VSC_CODING/GRIND/RL-FUZZING/initial_smaller_implementation/env_mock.py)
Python-based mock ALU environment for Milestone 1.

#### [NEW] [agent.py](file:///c:/Devopam/Engineering_CSE/SEM-5/SEM5_VSC_CODING/GRIND/RL-FUZZING/initial_smaller_implementation/agent.py)
PyTorch Deep Q-Network implementation (Replay Buffer, Q-Network, Epsilon-greedy action selection).

#### [NEW] [train_mock.py](file:///c:/Devopam/Engineering_CSE/SEM-5/SEM5_VSC_CODING/GRIND/RL-FUZZING/initial_smaller_implementation/train_mock.py)
The training loop for Milestone 1, connecting the PyTorch agent to the mock environment.

## Verification Plan (Milestone 1)
1. **Convergence Check:** Run `train_mock.py`. The agent's coverage should reach 100% (all mock ALU branches visited) significantly faster than a purely random mutation baseline.
2. **Metrics:** We will plot "Coverage vs. Steps" to visually confirm the RL agent is learning over time.
