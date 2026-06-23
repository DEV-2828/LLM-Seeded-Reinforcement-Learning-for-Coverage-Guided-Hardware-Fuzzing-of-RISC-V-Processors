# Scaled-Down RL Hardware Fuzzer Implementation Plan

This plan outlines an expanded, step-by-step approach to building the RL-guided hardware fuzzer. It is specifically designed to run on resource-constrained environments (like a 16GB RAM laptop with an iGPU) for initial phases, before eventually scaling up to environments like Google Colab.

We will use **PyTorch** for the reinforcement learning components to start, keeping the option to evaluate TensorFlow later if performance tuning dictates.

This fork removes the Verilator-generated C++ layer from the small ALU demo. The hardware side will be parsed directly from Verilog into a small internal representation, and the RISC-V side will be handled separately as an ISA-level execution path when needed.

## Decision Summary

- Keep the work scoped to `experimentation_with_risc-v` for now.
- Remove the Verilator-generated C++ layer only.
- Use a direct Verilog parser plus a bit-accurate execution engine for the ALU demo.
- Treat `libriscv` as an optional RISC-V ISA executor, not as a Verilog parser.
- Prefer bit-accurate behavior for this project; cycle accuracy can be added later if timing or pipeline behavior becomes the target.

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

### Milestone 2: Direct Verilog Parsing Baseline
**Goal:** Parse a simple Verilog model directly into an internal representation without generating C++.
- **Target:** A simple `alu.v` file representing a basic RISC-V ALU.
- **Action:** Build a Verilog front end that reads `alu.v` and produces an AST/IR for module structure, assignments, `always` blocks, and basic control flow.
- **Outcome:** A parsed hardware model that can be inspected and executed without Verilator or any generated C++ source.

### Milestone 3: Bit-Accurate Execution Engine
**Goal:** Evaluate the parsed Verilog model directly from the IR.
- **Action:** Implement a lightweight interpreter for the ALU subset we use in the demo, including combinational logic, synchronous state updates, and simple case/if logic.
- **Accuracy target:** Bit-accurate for outputs and state updates. This is the right fit for the current project because we care about logical correctness and coverage, not exact timing behavior.
- **Outcome:** A Python-accessible executor that can run the ALU model and return outputs plus coverage data.

### Milestone 4: RL + Direct Verilog Integration
**Goal:** Connect the PyTorch DQN from Milestone 1 to the direct Verilog execution engine from Milestone 3.
- **Action:** Swap out the mock Python ALU for the parsed-directly Verilog ALU.
- **Reward:** Extract branch/case/toggle-style coverage from the interpreter as the reward signal.
- **Outcome:** The RL agent successfully learns to maximize coverage in the directly parsed Verilog model.

### Milestone 5: Differential Testing & Bug Hunting
**Goal:** Implement the full fuzzing loop to actively find bugs.
- **Golden Model:** A trusted Python function calculating the expected result of an ALU operation.
- **The Loop:** RL agent generates instruction -> runs the direct Verilog model -> runs the Golden Model -> cross-checks results.
- **Bug Injection:** We will intentionally inject a subtle logic flaw into `alu_buggy.v` and prove the RL agent can generate the specific instruction to trigger it.
- **Outcome:** A functional differential fuzzing loop capable of logging genuine divergences.

### Milestone 6: RISC-V ISA Execution Path
**Goal:** Add an ISA-level execution path for cases where the test stimulus is a RISC-V program rather than a single ALU instruction.
- **Action:** Use `libriscv` as the fast RISC-V emulator/backend for running instruction sequences and producing ISA-level state transitions.
- **Why here:** `libriscv` is ideal for fast RISC-V emulation, sandboxing, and step-by-step instruction execution, but it is not a Verilog parser and does not replace the direct Verilog frontend.
- **Outcome:** A separate RISC-V execution mode that can be used for future seed generation, golden execution, or higher-level fuzzing experiments.

### Milestone 7: Scaling and Future Hardware Targets
**Goal:** Extend the working direct-parse pipeline beyond the toy ALU.
- **Action:** Generalize the parser and interpreter to larger Verilog blocks, then add parallel workers once the single-process flow is stable.
- **Metric:** Move from branch coverage in the ALU to FSM or signal-toggle coverage in larger hardware blocks.

---

## Proposed Changes

We will implement the components described in the `smaller_implementation_explanation.md` step-by-step. All files will be placed in the `experimentation_with_risc-v/` directory.

### Milestone 1: RL Agent & Mock Environment

#### [NEW] [agent.py](agent.py)
PyTorch Deep Q-Network implementation (Replay Buffer, Q-Network, Epsilon-greedy action selection) with state vector composed of instruction fields and coverage array, and 38 possible actions.

#### [NEW] [mock_env/env_mock.py](mock_env/env_mock.py)
Python-based mock ALU environment `MockALUEnv` for early testing.

#### [NEW] [train_mock.py](mock_env/train_mock.py)
The training loop for Milestone 1, running the agent through the mock environment for 500 episodes to verify learning capability.

### Milestone 2-4: Direct Verilog Environment

#### [NEW] [verilator_env/alu.v](verilator_env/alu.v)
Clean Verilog implementation of a simple ALU.

#### [NEW] [verilator_env/alu_buggy.v](verilator_env/alu_buggy.v)
Verilog ALU with an intentionally injected bug in the AND operation.

#### [NEW] [verilator_env/verilog_parser.py](experimentation_with_risc-v/verilator_env/verilog_parser.py)
Verilog frontend that parses the small ALU subset into an AST/IR.

#### [NEW] [verilator_env/verilog_runtime.py](experimentation_with_risc-v/verilator_env/verilog_runtime.py)
Bit-accurate interpreter that executes the parsed ALU model directly in Python.

#### [NEW] [verilator_env/env_verilator.py](experimentation_with_risc-v/verilator_env/env_verilator.py)
Python environment wrapper around the direct Verilog parser/runtime.

#### [NEW] [golden_model.py](verilator_env/golden_model.py)
Pure Python `golden_alu` function serving as the trusted source of truth.

### Milestone 5: Differential Fuzzer

#### [NEW] [differential_fuzzer.py](experimentation_with_risc-v/verilator_env/differential_fuzzer.py)
The core fuzzing script combining the RL Agent, the directly parsed Verilog hardware model, and the Golden Python Model to discover logic errors and generate unique bug signatures.

### Milestone 6: RISC-V Execution Path

#### [NEW] [riscv_env/](experimentation_with_risc-v/)
Planned home for a future `libriscv`-backed ISA execution path for RISC-V programs, separate from the Verilog parser/runtime used by the ALU demo.

## Verification Plan
1. **Parser Sanity Check:** Parse `alu.v` and `alu_buggy.v` directly and confirm the AST/IR exposes the expected operations, branches, and signals.
2. **Bit-Accuracy Check:** Compare direct-parser outputs against the current golden Python model over a small set of known ALU instructions and operands.
3. **Coverage Check:** Run `train_mock.py` first, then the direct-parser environment, and compare coverage growth against random mutation.
4. **Bug-Divergence Check:** Confirm `alu_buggy.v` produces at least one reproducible divergence from `golden_model.py`.
