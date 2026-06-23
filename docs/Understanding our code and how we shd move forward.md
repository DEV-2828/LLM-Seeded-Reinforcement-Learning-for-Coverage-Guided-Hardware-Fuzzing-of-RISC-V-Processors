# Understanding Our Code and the Path Forward

This document is an accurate, up-to-date map of what has been built, what milestone we are on, and exactly what needs to happen next to bridge our proof-of-concept into a research-grade hardware fuzzer.

---

## 1. Current State: What Has Already Been Built

> [!IMPORTANT]
> The previous version of this document was significantly out of date. **Milestones 6 and 7 are already implemented.** We are further along than previously documented.

Our `proof_of_concept_smaller_implementation` directory contains **five complete, layered stages** of the fuzzer:

### Stage 1–5: Core DQN on a Toy ALU (Complete ✅)
**Files:** `agent.py`, `mock_env/env_mock.py`, `verilator_env/alu.v`, `verilator_env/differential_fuzzer.py`, `verilator_env/golden_model.py`

- A **PyTorch DQN** (`agent.py`) mutates single 32-bit instructions using 38 discrete mutation actions (bit-flips, field randomization, opcode-dictionary swaps).
- A mock Python ALU (`env_mock.py`) provides a fast, zero-dependency training environment.
- A real **Verilog ALU** (`alu.v` / `alu_buggy.v`) is compiled by Verilator into a `.so` shared library, interfaced via `ctypes`.
- A **differential fuzzer** (`differential_fuzzer.py`) compares Verilator ALU output against `golden_model.py` (a trusted Python ALU) and successfully detects injected functional bugs.

### Stage 6: Multi-Worker Parallel Fuzzing (Complete ✅)
**Files:** `MILESTONE_6/parallel_fuzzer.py`

- Uses **`torch.multiprocessing`** to spawn 4 parallel worker processes, each running its own isolated Verilator + differential fuzzer instance.
- Workers push `(state, action, reward, next_state, done)` transitions into a shared **`mp.Queue`**.
- A **central global DQN agent** consumes transitions from the queue, trains, and periodically broadcasts updated weights back to workers.
- This is a working prototype of the **actor-learner** (Ape-X style) architecture pattern.

### Stage 7: DRQN Agent + FSM Environment (Complete ✅)
**Files:** `MILESTONE_7/agent_rnn.py`, `MILESTONE_7/env_fsm.py`, `MILESTONE_7/fsm.v`, `MILESTONE_7/fsm_buggy.v`

- A **Deep Recurrent Q-Network (DRQN)** (`agent_rnn.py`) with an LSTM backbone that processes instruction *sequences* over time — it has memory across timesteps, unlike the base DQN.
- A Verilog **FSM module** replaces the simple ALU as the device under test, and `env_fsm.py` extracts **FSM state coverage** (which states and transitions have been visited) as the reward signal.
- The environment includes a **buggy FSM** (`fsm_buggy.v`) with injected state-transition errors, and finds them via differential checking against `golden_fsm.py`.
- This demonstrates we already have the architectural capability for **control-path (pipeline) coverage**.

---

## 2. Known Gaps — What Is Still Missing

Despite strong progress, the following critical components for the full system do **not yet exist**:

| Gap | Impact | Priority |
|:----|:-------|:---------|
| **Multi-instruction sequence seeds** | The DRQN processes sequential steps, but we do not yet generate structured 5–10 instruction *programs* as seeds | 🔴 High |
| **Real RISC-V core as DUT** | We test a toy ALU/FSM, not PicoRV32, Ibex, or CVA6 | 🔴 High |
| **Spike as golden oracle** | `golden_model.py` is a Python stub — it only knows 4 instructions. Spike knows the entire ISA | 🔴 High |
| **Privilege / exception fuzzing** | No CSR instructions, no trap sequences, no U-mode/M-mode boundary tests | 🟠 Medium |
| **LLM seed generator** | No CodeLlama/StarCoder integration for coverage-conditioned prompt generation | 🟠 Medium |
| **Weighted coverage reward** | All FSM states/toggles treated equally — the agent chases easy states over hard ones | 🟠 Medium |
| **Redis replay buffer** | `mp.Queue` is a local IPC mechanism; a real Redis buffer scales to 10M+ transitions | 🟡 Low (scaling) |

---

## 3. The Concrete Next Steps

### Step 3.1 — Upgrade the DUT: Replace the ALU with PicoRV32 (Highest Priority)
The toy ALU has no pipeline, no branches, no exceptions. We must swap it for a real core.

- **Action:** Add `picorv32.v` from [cliffordwolf/picorv32](https://github.com/cliffordwolf/picorv32) to the project.
- **Action:** Write a `picorv32_wrapper.cpp` that exposes `reset()`, `step(instruction)`, `get_register(n)`, `get_coverage()` via a C API (mirroring `alu_wrapper.cpp`).
- **Action:** Create `env_picorv32.py` analogous to `env_fsm.py` — it sends instructions to PicoRV32 and extracts FSM-level coverage from the Verilator build.

### Step 3.2 — Upgrade the Oracle: Replace `golden_model.py` with Spike
The Python golden model is incapable of simulating exceptions, CSRs, or memory.

- **Action:** Wrap the `spike` binary in a Python class `SpikeOracle` that loads a test program, runs it, and dumps register state. Interface it via `subprocess` initially.
- **Action:** Diff the PicoRV32 register file against Spike's output at the end of each test. Any mismatch = bug report.

### Step 3.3 — Add Multi-Instruction Program Seeds
The DRQN already has temporal memory — we need to feed it instruction *sequences*, not individual instructions.

- **Action:** Create a `seed_generator.py` that builds a pool of structured 5–10 instruction RV32I programs, covering: RAW hazards, branch+load cascades, CSR writes, and ECALL sequences.
- **Action:** Modify the environment's `reset()` to load a seed program and have the agent mutate it step-by-step, using the DRQN's LSTM state to track the full sequence context.

### Step 3.4 — Add Privilege/Exception Targeting
- **Action:** Add dedicated seed templates for privilege boundary probing (CSRRS, MRET, ECALL from U-mode).
- **Action:** Extend the reward function to give bonus reward for triggering a **trap** (exception entry), since exception handling logic is where the deepest pipeline bugs hide.

---

## 4. Long-Term Research Vision (Beyond the PoC)

Once Steps 3.1–3.4 are working on PicoRV32:

1. **Scale the DUT:** PicoRV32 → **Ibex** → **CVA6** (primary paper target) → **BOOM** (stretch goal).
2. **Add LLM Seed Generation:** Integrate CodeLlama-34B or StarCoder2 to generate coverage-conditioned seeds targeting specific uncovered FSM states.
3. **Distributed Ape-X on H100:** Evolve `parallel_fuzzer.py`'s `mp.Queue` architecture into a proper Redis-backed Ape-X setup with 128–256 workers for 100× throughput.
4. **Publish:** Target USENIX Security / IEEE S&P with results comparing RL+LLM vs random, RL-only, and LLM-only baselines on CVA6 coverage and bug-finding.

---

## 5. File Map (Quick Reference)

```
proof_of_concept_smaller_implementation/
├── agent.py                         ← DQN agent (Milestones 1–6)
├── demo_current_limitations.py      ← Runs both demos; shows what's missing
├── mock_env/
│   ├── env_mock.py                  ← Pure-Python toy ALU (fast, no deps)
│   └── train_mock.py                ← Training loop for mock env
├── verilator_env/
│   ├── alu.v / alu_buggy.v          ← Verilog ALU (clean + injected bug)
│   ├── golden_model.py              ← Python ground truth (4 instructions only)
│   ├── differential_fuzzer.py       ← Finds bugs by comparing DUT vs golden
│   └── env_verilator.py             ← Python↔Verilator bridge (ctypes)
├── MILESTONE_6/
│   └── parallel_fuzzer.py           ← 4-worker actor-learner (mp.Queue)
└── MILESTONE_7/
    ├── agent_rnn.py                  ← DRQN with LSTM (sequence-aware agent)
    ├── env_fsm.py                    ← FSM coverage extraction environment
    ├── fsm.v / fsm_buggy.v           ← FSM Verilog (clean + injected bug)
    └── golden_fsm.py                 ← Golden FSM reference
```