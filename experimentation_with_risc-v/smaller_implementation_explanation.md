# Overview of the Smaller Implementation Models

The `smaller_implementation` folder contains a miniature version of a Coverage-Guided Hardware Fuzzing environment driven by a Reinforcement Learning (RL) agent. The goal is to use an RL agent to iteratively generate instructions that maximize code coverage within a hardware model (ALU) and eventually use those instructions to find bugs by comparing the hardware's output against a known correct "golden" model.

The system is split into three main components:
1. **The RL Agent**: A Deep Q-Network (DQN) that learns how to mutate instructions to hit new coverage paths.
2. **The Mock Environment**: A pure Python simulated environment to quickly train/test the agent's ability to discover branches.
3. **The Direct Verilog Environment**: The actual hardware-in-the-loop environment where the agent feeds instructions to a directly parsed Verilog model of an ALU, extracts coverage, and compares its output against a Golden Model to find hardware bugs.

---

## 1. The RL Agent (`agent.py`)

The heart of the learning system is `DQNAgent`, a standard Deep Q-Network implementation using PyTorch. 

### State Space
The agent receives a state vector composed of the normalized fields of the current RISC-V instruction (`opcode`, `rd`, `funct3`, `rs1`, `rs2`, `funct7`) appended with the current coverage array (a bitmask of which branches have been hit so far). 

### Action Space
The agent can choose from 38 possible actions:
- **Actions 0-31**: Flip a specific bit `i` in the 32-bit instruction.
- **Action 32**: Randomize the `opcode` field.
- **Action 33**: Randomize the `funct3` field.
- **Action 34**: Randomize the `funct7` field.
- **Action 35-37**: Randomize the register fields (`rs1`, `rs2`, `rd`).

### Learning Mechanism
- It uses a **Replay Buffer** to store past transitions `(state, action, reward, next_state, done)`.
- It employs two simple feedforward neural networks (3 layers: 64 -> 64 -> action_dim) – one for live Q-value prediction and one "target" network for stability during training.
- It uses an **epsilon-greedy** policy: it starts by exploring randomly (epsilon = 1.0) and slowly decays the randomness (epsilon decay = 0.995) to exploit its learned knowledge.

---

## 2. The Mock Environment (`mock_env/env_mock.py`)

Before dealing with the complexities of C++ Verilator bindings, the system provides a Mock Environment.

### How It Works
- The `MockALUEnv` class acts as an OpenAI Gym-like environment.
- When `env.step(action)` is called, it applies the chosen mutation action to an internal `current_instruction`.
- Instead of running hardware, it has a simple python `if/else` tree (the "Simulated decoder logic") that mimics a processor decoding an instruction.
- There are 10 unique "branches" (e.g., branch 0 for R-type, branch 2 for ADD, branch 4 for AND, etc.).
- **Reward**: The agent receives a reward of `+1.0` if its mutated instruction triggers a branch that has never been hit before. If it hits an invalid opcode, it gets a tiny negative reward `-0.01`.

The `train_mock.py` script runs the agent through this environment for 500 episodes to verify that the RL agent is capable of learning how to flip bits/fields to achieve 100% coverage (10/10 branches).

---

## 3. The Direct Verilog Environment (`verilator_env`)

Once the agent's logic is proven in the Mock environment, it moves to the Direct Verilog Environment, which brings real hardware semantics into Python without a generated C++ layer.

### The Hardware (`alu.v` & `alu_buggy.v`)
- There are two Verilog implementations of a simple ALU. `alu.v` is clean, while `alu_buggy.v` contains an intentionally injected bug in the `AND` operation.
- They take `inst`, `rs1_data`, and `rs2_data` as inputs and output `rd_data` and a 10-bit `coverage_bins` wire.
- In `alu_buggy.v`, the AND logic incorrectly masks out the least significant bit: `rd_data <= (rs1_data & rs2_data) & 32'hFFFFFFFE;`.

### The Runtime (`verilog_parser.py`, `verilog_runtime.py`, `env_verilator.py`)
- `verilog_parser.py` turns the supported Verilog subset into a normalized IR.
- `verilog_runtime.py` executes that IR directly in Python and records coverage.
- `env_verilator.py` is the environment wrapper kept for continuity in the copied demo folder; it will become the thin API layer over the direct parser/runtime path.

### The Golden Model (`golden_model.py`)
- This is a pure Python function `golden_alu(inst, rs1_data, rs2_data)` that calculates exactly what the ALU *should* output according to the RISC-V specification. It is the trusted source of truth.

---

## 4. The Differential Fuzzer (`differential_fuzzer.py`)

This is where everything comes together in **Milestone 5**. The Differential Fuzzer uses the RL Agent, the buggy direct-Verilog hardware model, and the Golden Python Model.

### The Flow of Execution:
1. **Initialization**: The `DifferentialFuzzerEnv` loads the buggy Verilog model through the local parser/runtime backend.
2. **Instruction Generation**: The environment starts with a basic instruction (e.g., `ADD x0, x0, x0`).
3. **Agent Action**: The DQN Agent looks at the state (instruction fields + current coverage) and outputs an action (e.g., "Randomize funct3").
4. **Environment Step**: 
   - The environment mutates the `current_instruction` according to the agent's action.
   - It also completely randomizes the data operands (`rs1_data` and `rs2_data`) to ensure wide data coverage.
5. **Differential Execution**:
   - The mutated instruction and random operands are fed into the **direct Verilog ALU runtime** via `self.hw_alu.step()`, yielding a `hw_result`.
   - The *exact same* instruction and operands are fed into the **Python Golden Model** via `golden_alu()`, yielding a `golden_result`.
6. **Coverage Extraction**: The coverage bits (`coverage_bins`) are pulled from the hardware model.
7. **Reward & Bug Detection**:
   - The agent gets `+1.0` reward for every new coverage bit it flips from `0` to `1`.
   - **The Cross-Check**: If `hw_result != golden_result`, a bug is found! 
   - A signature of the bug is created (based on the operation). If it's a new unique bug signature, the agent gets a massive **`+10.0` reward bonus**. If it's a bug signature it has already found, it gets `+1.0`.
8. **Logging**: The bug details (instruction, operands, differing results, and XOR difference) are saved to `self.bugs_found`.
9. **Learning**: The agent stores this transition in its replay buffer and updates its neural network to prioritize actions that led to new coverage or discovered bugs.

By combining Reinforcement Learning (to intelligently navigate the instruction space towards deep coverage) with Differential Testing (comparing a hardware model against a software model), the system creates an automated, coverage-guided fuzzing loop capable of exposing deeply buried hardware logic errors.

## 5. Future RISC-V Execution Path (`libriscv`)

If and when the demo grows from single-ALU tests to actual RISC-V instruction streams, the best next execution backend is `libriscv` unless a stronger option emerges. It is a fast, embeddable ISA-level emulator with instruction stepping, sandboxing, and low-latency execution, which fits the future RISC-V workload better than Verilator-generated code. It does not replace the Verilog parser/runtime for the ALU demo; it complements it later for program-level execution.
