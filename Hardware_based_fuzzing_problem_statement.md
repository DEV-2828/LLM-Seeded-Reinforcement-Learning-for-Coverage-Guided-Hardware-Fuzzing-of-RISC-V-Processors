# Problem Statement: LLM-Seeded Reinforcement Learning for Coverage-Guided Hardware Fuzzing of RISC-V Processors

## 1. The Problem We Are Solving

### 1.1 The Fundamental Challenge

Modern processor design is one of the most complex engineering endeavors in existence. A single RISC-V core like CVA6 contains over **100,000 lines of SystemVerilog** describing millions of interacting logic gates, pipeline stages, privilege boundaries, memory management units, and exception handling paths. Every one of these interactions must behave correctly across every possible input — and a single logic flaw that escapes pre-silicon verification becomes **permanently embedded in silicon**.

Unlike software bugs, **hardware bugs cannot be patched after manufacturing**. A logic error in a shipped processor requires either:
- A full silicon respin (costing **$50M–$500M** and 6–18 months of delay), or
- A permanent microcode/firmware workaround that degrades performance for the lifetime of the product.

The consequences of missed hardware bugs are not theoretical:

| Bug | Year | Impact |
|:---|:---|:---|
| **Intel FDIV Bug** | 1994 | $475M recall. A single floating-point division error in the Pentium processor. |
| **Spectre & Meltdown** | 2018 | Affected every Intel/AMD/ARM processor shipped in the prior decade. Software mitigations cost 5–30% permanent performance loss across the entire cloud computing industry. |
| **Hertzbleed** | 2022 | CPU frequency-scaling side channel in Intel/AMD. Enables remote cryptographic key extraction. Cannot be fixed in hardware. |
| **GhostWrite (RISC-V)** | 2024 | A bug in T-Head's XuanTie C910 RISC-V core allowed unprivileged code to write to any physical memory address, completely bypassing all isolation. Found by researchers, not the vendor. |

### 1.2 Why Current Verification Methods Are Failing

The semiconductor industry's primary verification methods are fundamentally unable to keep pace with design complexity:

#### Directed Testing (Manual)
Engineers manually write test sequences targeting specific behaviors. This is the industry standard and accounts for **~70% of total chip development effort**. The problem:
- It only tests what engineers anticipate. It cannot discover unexpected interactions.
- A human engineer can write ~10–50 directed test scenarios per day. A modern RISC-V core has an estimated **10^18+ reachable states**. Manual testing covers a vanishingly small fraction.

#### Constrained Random Verification (CRV)
Generates random instruction sequences with programmer-defined constraints to keep inputs "valid." Widely used in SystemVerilog/UVM testbenches. The problem:
- Randomness has no memory. It re-explores already-covered states endlessly.
- Deep coverage plateaus are common — CRV typically saturates at 60–80% toggle coverage and cannot break through to the remaining 20–40% where subtle bugs hide.
- The constraints must be manually tuned. Overly tight constraints miss bugs; overly loose constraints waste cycles on illegal inputs.

#### Formal Verification
Mathematically proves properties about the design (e.g., "register x0 is always zero"). The problem:
- **State explosion**: Formal tools cannot handle the full state space of even a modest 5-stage pipeline processor. They are restricted to verifying small, isolated properties on submodules.
- Cannot discover unknown bug classes — you must specify what to look for in advance.

#### The Coverage Gap

The result of these limitations is a well-documented **coverage gap**: the space between what traditional verification achieves (60–80% coverage) and what full verification would require (100%). This gap is where the most dangerous bugs live — the ones that only trigger under rare, multi-instruction interaction sequences that no human anticipated and no random generator stumbled upon.

**This is the exact problem we are solving.**

### 1.3 Our Thesis

> Traditional hardware verification methods fail because they are either unintelligent (random) or narrowly intelligent (directed tests for anticipated behaviors). We propose an **autonomously intelligent** verification agent — a Reinforcement Learning system that learns, through interaction with a simulated processor, which instruction mutations are most likely to reach unexplored hardware states — combined with an **LLM-based seed generator** that synthesizes structurally diverse, multi-instruction test programs targeting specific pipeline stress scenarios.

The core claim: **An RL agent trained on hardware coverage feedback, seeded by LLM-generated structured programs, will achieve higher logic coverage faster and discover more hardware bugs than random fuzzing, constrained random verification, or standalone RL approaches.**

However, this claim carries risks that must be acknowledged upfront — see §8 (Limitations, Risks & Mitigations).

---

## 2. What Exactly Are We Building?

### 2.1 System Overview

We are building a closed-loop automated hardware testing system with three major components:

1. **An LLM Seed Generator** — a pretrained code language model (CodeLlama-34B or StarCoder2-15B) that synthesizes semantically meaningful multi-instruction RISC-V test programs. The LLM is prompted with descriptions of pipeline stress scenarios and coverage gaps, producing structurally diverse seeds that target underexplored hardware logic.

2. **An RL Mutation Engine** — a Deep Q-Network (Double-DQN or Dueling DQN) agent that takes LLM-generated seed programs and learns which mutations (bit-flips, register swaps, opcode substitutions) push the hardware simulation into previously unreached states. The agent's reward signal comes directly from hardware coverage metrics extracted from the simulator.

3. **A Differential Execution Environment** — a pair of simulators running in lockstep:
   - **Verilator** (compiles the RISC-V RTL into a cycle-accurate C++ model) — this is the Device Under Test.
   - **Spike** (the official RISC-V ISA simulator) — this is the Golden Reference.
   
   Every mutated instruction sequence is executed on both. Any divergence in register state, memory state, or exception behavior between them indicates a bug in the RTL implementation.

### 2.2 What Counts as a "Bug"

A bug, in this context, is any divergence between the Verilator simulation of the RTL design and the Spike golden reference. Specifically:

* **Functional Bugs:** The RTL produces a different computational result than the ISA specification requires (wrong ALU output, incorrect branch decision, misaligned memory access result).
* **Exception Bugs:** The RTL fails to raise an exception when one is required (e.g., unaligned access, illegal instruction), or raises one spuriously.
* **Privilege Escalation Bugs:** User-mode code accesses machine-mode resources without being trapped — the hardware equivalent of a kernel exploit, and the highest-impact class of bug we target.
* **Timing/Pipeline Bugs:** The RTL produces the correct result but in the wrong cycle, indicating a pipeline control error (hazard detection failure, incorrect stall logic).

### 2.3 What Counts as "Coverage"

We use two complementary hardware-specific coverage metrics:

* **Multiplexer Toggle Coverage:** Every multiplexer in the design has a set of control signals. Coverage tracks which select-line combinations have been exercised. A mux toggle that has never been flipped represents unexplored combinational logic.
* **FSM State Coverage:** The processor's control unit is a finite state machine with states for normal execution, pipeline stalls, branch flushes, exception entry, privilege transitions, etc. Coverage tracks which FSM states and state transitions have been visited.

The RL agent is rewarded for reaching **new** coverage points — toggles or states not seen in any prior execution. This ensures the agent is incentivized to explore, not to repeat.

---

## 3. The Current Research Landscape & Our Gap

### 3.1 What Exists

| System | Year | Approach | Limitations |
|:---|:---|:---|:---|
| **DifuzzRTL** | 2021 | Software-style coverage-guided fuzzing adapted for RTL | No learning — uses random mutation with coverage-based seed selection. Coverage plateaus. |
| **TheHuzz** | 2022 | First to apply ML to RTL fuzzing | Limited to simple instruction mutation, single-instruction seeds only. |
| **GenHuzz** | 2025 (USENIX) | Uses genetic algorithms + RL for instruction generation | Does not use LLM seeds. No explicit privilege escalation targeting. |
| **RLFuzz** | 2026 | Deep Q-Learning for RISC-V fuzzing | Single-instruction mutation only. Vanilla DQN (overestimates Q-values). No multi-instruction interaction fuzzing. |
| **MutaGen** | 2026 | LLM-based test generation for hardware | Uses LLM only — no RL-guided mutation feedback loop. Cannot adaptively target coverage gaps. |

### 3.2 What's Missing (Our Contribution)

No existing system combines all of the following:

1. **LLM-generated structured seeds** — multi-instruction programs that model realistic pipeline interactions (hazards, stalls, privilege transitions).
2. **RL-guided adaptive mutation** — a learned mutation policy that targets specific coverage gaps, not random exploration.
3. **Coverage-conditioned LLM prompting** — a feedback loop where the LLM is told what coverage is missing and generates seeds specifically designed to reach those states.
4. **Explicit privilege escalation fuzzing** — dedicated seed sequences and reward shaping for discovering U-mode → M-mode boundary violations.
5. **Scalable distributed execution** — an Ape-X style architecture that exploits GPU hardware for high-throughput parallel simulation.

These five elements together constitute our novel contribution.

---

## 4. What Do We Test/Train the Model On?

### 4.1 Target RISC-V Cores (Device Under Test)

These are the open-source RTL implementations we fuzz. All are written in Verilog/SystemVerilog, compatible with Verilator, and actively maintained:

| Core | Complexity | Pipeline | Why Use It | Repository |
|:---|:---|:---|:---|:---|
| **PicoRV32** | Minimal | Single-cycle / multi-cycle | Best for initial pipeline development and validation. Small RTL means fast simulation and easy debugging. | `cliffordwolf/picorv32` |
| **SERV** | Minimal | Bit-serial | World's smallest RISC-V core. Useful for unit-testing the fuzzer itself — if the fuzzer can't work on SERV, it won't work on anything. | `olofk/serv` |
| **Ibex** | Moderate | 2-stage | Google's production core used in OpenTitan. Has a real security surface and an active bug bounty. Finding bugs here has immediate industry impact. | `lowRISC/ibex` |
| **CVA6 (Ariane)** | Complex | 6-stage, in-order | **Primary paper target.** Production-grade, used in real chips (e.g., PULP platform). Complex enough to have undiscovered bugs, small enough for reasonable simulation speed. | `openhwgroup/cva6` |
| **Rocket Core** | Complex | 5-stage, in-order | Backed by UC Berkeley, used in DARPA programs. High prestige — bugs found here are citable. | `chipsalliance/rocket-chip` |
| **BOOM** | Very Complex | Out-of-order superscalar | The hardest target. Out-of-order execution introduces reorder buffer, reservation station, and speculative execution bugs. Highest impact but slowest simulation. | `riscv-boom/riscv-boom` |

**Recommended Progression:**
1. **Develop & debug** the full pipeline on PicoRV32 (fast iteration, minutes per fuzzing campaign).
2. **Validate methodology** on Ibex (moderate complexity, known security surface).
3. **Generate paper results** on CVA6 (complex enough for meaningful results, fast enough for statistical runs).
4. **Stretch goal** — run on BOOM for a "we also tested on OOO" claim.

### 4.2 Golden Reference Model

For every target core, the golden reference is the **Spike ISA Simulator** — the official RISC-V Foundation reference implementation. Spike defines "correct behavior" according to the ISA specification. Any divergence between the target core and Spike is, by definition, a bug in the target core.

**Trust Caveat:** Spike is extensively community-validated for the base RV32I/RV64I ISA, but it has had documented bugs in less-tested extensions (Vector, Hypervisor, Crypto). For base ISA fuzzing, Spike is a reliable oracle. For extension fuzzing, divergences must be manually triaged against the ISA specification to determine whether the bug is in the DUT or in Spike itself. See §8.5 for further discussion.

### 4.3 What the RL Agent Trains On

The RL agent does **not** train on any pre-existing dataset. It learns entirely online through interaction with the simulation environment:

| Training Source | Description |
|:---|:---|
| **Self-generated experience** | The agent mutates instructions, sends them to Verilator, receives coverage rewards. This is the entire training signal — no external labeled data. |
| **Seed Corpus (initial bootstrap)** | The 47 RV32I base instructions with valid encodings serve as the starting exploration point before the agent has learned anything. |
| **LLM-generated programs (H100 extension)** | CodeLlama synthesizes structured multi-instruction seeds, which the RL agent then explores mutations within. |
| **Replay buffer** | Past `(state, action, reward, next_state)` transitions are stored and randomly sampled for batch training. The agent learns from its own history. |

This is a significant advantage: **the fuzzer is hardware-agnostic**. Swap in a different RISC-V core and the agent relearns from scratch without any manual adaptation. The same system works on PicoRV32, CVA6, and BOOM without modification.

### 4.4 What the LLM Is Trained On (Pre-existing — We Don't Train It)

We use pretrained code LLMs in **inference mode only**:

| Model | Parameters | License | Why This One |
|:---|:---|:---|:---|
| **CodeLlama-34B-Instruct** | 34B | Meta (Llama license) | Strong at assembly generation, instruction-following for structured prompts. Fits in H100's 80GB HBM3. |
| **StarCoder2-15B** | 15B | BigCode (OpenRAIL) | Lighter alternative. Trained on 600+ languages including RISC-V assembly. Fits in a single A100 40GB. |
| **DeepSeek-Coder-V2** | 21B (active) | DeepSeek | Strong at code reasoning. MoE architecture means fast inference. |

**No fine-tuning is required initially.** These models already understand RISC-V assembly syntax well enough for structured prompting. Optional enhancement: fine-tune on the ~5,000 programs in the `riscv-arch-test` compliance suite to improve seed quality and reduce syntactically invalid outputs.

---

## 5. H100 GPU Scaling Strategy

> This section describes how access to NVIDIA H100 hardware (80GB HBM3, ~3,958 TFLOPS FP8) changes the performance ceiling and enables experiments that are impossible on commodity hardware.

### 5.1 The Bottleneck Without GPU

On a CPU-only machine (16GB RAM), the fuzzing pipeline is constrained to:
- **4 parallel** Verilator + Spike instances (each consuming ~2GB)
- **~50K transitions** in the replay buffer before hitting RAM limits
- **Single-threaded DQN** training with batch size 64
- **No LLM** (CodeLlama-34B requires ~70GB VRAM at FP16)
- **Estimated throughput:** ~500–1,000 mutations/second
- **Full coverage campaign on CVA6:** ~2–4 weeks

### 5.2 Distributed Ape-X Architecture (With H100)

The Ape-X DQN architecture (Horgan et al., 2018) was designed for exactly this class of problem — environments that are cheap to simulate in parallel but expensive to learn from in series.

**Architecture:**

* **Actor Workers (CPU side):** Deploy 128–256 Docker containers, each running an independent Verilator + Spike simulation pair. Each worker:
  * Pulls the latest network weights from the learner
  * Runs its own ε-greedy policy to select mutations
  * Generates `(state, action, reward, next_state)` experience tuples
  * Pushes tuples to a shared **Redis replay buffer** on the host
  * Workers are fully stateless and independently restartable

* **Learner (H100 side):** A single GPU-resident learner process that:
  * Continuously samples large mini-batches (2048–4096 transitions) from the Redis buffer
  * Performs batched DQN weight updates using H100 tensor cores
  * Pushes updated weights back to a shared store every N training steps
  * Workers pull new weights asynchronously — no synchronization barriers

* **Batched Inference Server (H100 side):** Instead of serving mutation decisions one-at-a-time:
  * Collects 256+ pending state queries from all workers into a single batch
  * Executes one batched GPU forward pass to compute Q-values for all queries simultaneously
  * Returns mutation decisions to workers with near-zero latency via NVLink/PCIe
  * Throughput: ~1K inferences/sec (CPU) → **~1M inferences/sec** (H100 batched)

### 5.3 Resource Budget

| Hardware Configuration | Verilator Instances | Replay Buffer Size | Training Batch | LLM Available | Estimated Throughput |
|:---|:---|:---|:---|:---|:---|
| 16GB RAM, CPU only | 4 workers | ~50K transitions | 64 | No | ~1K mut/sec |
| 256GB RAM + 1× H100 | 128–256 workers | ~10M transitions | 2048–4096 | CodeLlama-34B | ~100K mut/sec |
| Cloud (8× H100 node) | 512+ workers | ~50M transitions | 8192+ | Multiple LLMs | ~500K+ mut/sec |

With 10M+ transitions in the replay buffer, the agent encounters rare hardware states (deep pipeline stalls, exception cascades, privilege boundary edge cases) enough times to reliably learn to target them — something impossible at 50K buffer sizes.

### 5.4 Population-Based Hyperparameter Search

With H100 compute, train 16–32 DQN agents simultaneously with varied hyperparameters:
- Learning rate: [1e-4, 3e-4, 1e-3]
- ε decay schedule: [linear, exponential, cosine annealing]
- Network depth: [2, 4, 6 hidden layers]
- Reward shaping weights: [toggle-heavy, FSM-heavy, balanced]

Use **Population-Based Training (PBT)** to automatically evolve the best configuration during training. Poorly performing agents have their weights replaced with copies of the best-performing agent's weights (with perturbation). This eliminates manual hyperparameter tuning entirely.

### 5.5 Time Estimates (H100 vs CPU)

| Task | CPU Only (16GB) | 1× H100 (256GB) |
|:---|:---|:---|
| Full curriculum learning (4 stages) on CVA6 | 2–3 weeks | 1–2 days |
| 5× statistical repetitions for paper | 10–15 weeks | 5–10 days |
| Hyperparameter search (16 configs) | Infeasible | ~1 week |
| BOOM (OOO) fuzzing campaign | Months | 1–2 weeks |

---

## 6. LLM-Guided Seed Generation

This is the most architecturally novel component of the system. It directly addresses the single biggest limitation of all existing RL hardware fuzzers: **they only mutate individual instructions and miss bugs caused by multi-instruction interactions**.

### 6.1 Why Single-Instruction Seeds Are Insufficient

The vast majority of dangerous hardware bugs manifest from **instruction interactions**, not single instruction execution. These interaction-dependent bugs are invisible to single-instruction fuzzers:

* **Read-After-Write (RAW) Data Hazards:**
  ```asm
  ADD  x1, x2, x3    # writes to x1
  LW   x4, 0(x1)     # reads x1 as memory address — depends on ADD result
  ```
  If the pipeline's forwarding logic is broken, the load uses a stale value of x1. This only triggers when the two instructions are adjacent.

* **Branch Misprediction + Load-Use Cascade:**
  ```asm
  BEQ  x1, x2, target   # branch mispredicts → pipeline flush
  LW   x3, 0(x4)        # in the branch delay → may or may not execute
  ADD  x5, x3, x6       # depends on load result → hazard if load was squashed
  ```
  A compound pipeline flush + stall scenario. Single-instruction fuzzing cannot produce this.

* **CSR Write → Exception Race:**
  ```asm
  CSRRW x0, mtvec, x1   # writes new trap handler address
  ECALL                   # immediately triggers exception → uses mtvec
  ```
  If the CSR write hasn't committed when the exception fires, the processor jumps to the wrong handler address. This is a security-critical timing bug.

* **Privilege Boundary Probing:**
  ```asm
  # In U-mode:
  CSRRS x1, mstatus, x0   # attempt to read M-mode CSR (should trap)
  CSRRW x0, mstatus, x2   # attempt to write mstatus.MPP to escalate privilege
  MRET                      # attempt return-to-machine-mode from U-mode
  ```
  A coordinated three-instruction privilege escalation attempt. Must be tested as a sequence.

* **Memory Ordering / Store-Load Forwarding:**
  ```asm
  SW   x1, 0(x2)      # store value to memory
  BEQ  x3, x4, skip   # branch (may or may not flush pipeline)
  LW   x5, 0(x2)      # load from same address — should see stored value
  ```
  Tests whether the store-to-load forwarding path survives a branch in between.

None of these patterns are discoverable by mutating single 32-bit instruction words.

### 6.2 The LLM's Role

Host a **CodeLlama-34B** or **StarCoder2-15B** model locally on the H100 (both fit comfortably in 80GB HBM3). The LLM operates in two modes:

**Important Caveat:** RISC-V assembly constitutes a tiny fraction of these LLMs' training data compared to Python, JavaScript, or C. The LLM will sometimes generate syntactically plausible but architecturally invalid sequences (non-existent CSR addresses, wrong immediate bit-widths, invalid register names). A **post-generation validation pass** is mandatory — assemble every LLM-generated sequence through `riscv64-unknown-elf-as` and discard any that fail assembly. Empirically, expect a 20–40% rejection rate on raw LLM outputs for RISC-V, which is acceptable given the generation throughput. See §8.1 for further discussion of this risk.

#### Mode 1: Structured Prompt Generation

Give the LLM a description of a pipeline stress scenario and ask it to generate a valid RISC-V assembly sequence:

```
Prompt: "Write a 6-instruction RISC-V RV32I assembly sequence that:
1. Creates a RAW data hazard on register x5
2. Immediately follows with a conditional branch that depends on x5
3. In the branch delay slot, performs a memory store using x5 as the address
4. After the branch target, loads from the same memory address
Ensure all instructions use valid RV32I encodings."
```

The LLM outputs syntactically valid assembly that the fuzzer assembles into machine code and uses as a structured seed for RL mutation. The key insight: **the LLM understands pipeline semantics that a random generator does not**.

#### Mode 2: Coverage-Conditioned Seed Generation (Novel)

This is our most novel contribution. Feed the LLM the current **coverage gap** — which FSM states and mux toggles remain unhit — and prompt it to generate sequences specifically designed to reach those states:

```
Prompt: "The following hardware states have NOT been reached during fuzzing:
- FSM state: PIPELINE_FLUSH_ON_EXCEPTION_IN_MEMORY_STAGE
- FSM state: PRIVILEGE_TRANSITION_U_TO_M_VIA_ECALL
- Mux toggle: ALU_FORWARD_FROM_MEMORY_STAGE (never selected)

Generate a 5-instruction RV32I sequence most likely to trigger these 
specific pipeline states. Explain your reasoning."
```

This makes the LLM a **coverage-aware, targeted seed generator** — a closed-loop system where the LLM is actively directed toward the fuzzer's weak spots. No existing system does this.

### 6.3 Hybrid LLM + RL Pipeline

```
LLM (CodeLlama-34B on H100)
    ↓  generates structured multi-instruction seeds
    ↓  (coverage-conditioned prompting targets unexplored states)
Seed Queue (semantically valid, pipeline-stress programs)
    ↓  feeds into
RL Mutation Engine (applies discrete mutations within valid program structure)
    ↓  preserves program semantics while exploring variations
    ↓  sends mutated programs to
Verilator + Spike (parallel differential execution)
    ↓  returns coverage signal + divergence detection
RL Agent (learns which mutations of LLM seeds reach new hardware states)
    ↓  updated coverage bitmap fed back to
LLM (generates next batch of seeds targeting remaining coverage gaps)
```

This closed loop — where the LLM generates seeds informed by what the RL agent has already covered, and the RL agent fine-tunes those seeds through learned mutation — is a **feedback-driven test synthesis pipeline with no direct equivalent in the existing hardware fuzzing literature**.

### 6.4 Why This Is Novel

| Existing Approach | What It Does | What It Misses |
|:---|:---|:---|
| Random mutation | Mutates individual bits/bytes blindly | No structural awareness, no multi-instruction semantics |
| RL-only (RLFuzz, GenHuzz) | Learns mutation policies from coverage feedback | Single-instruction only, no pipeline interaction modeling |
| LLM-only (MutaGen) | Generates structured tests from descriptions | No adaptive feedback loop, no coverage-guided iteration |
| **Our Approach (LLM + RL)** | **LLM generates structurally diverse seeds → RL adaptively mutates → coverage feedback directs both** | **Combines structural awareness (LLM) with adaptive learning (RL) in a closed loop** |

---

## 7. Research Significance & Publication Viability

### 7.1 Why This Matters Beyond Academia

* **RISC-V is now critical infrastructure.** It powers everything from embedded controllers to data center processors. Unlike x86/ARM, RISC-V cores are developed by hundreds of independent teams worldwide, each implementing the ISA from scratch. Every custom core is a new attack surface.
* **Hardware supply chain security** is a national priority in the US, EU, and China. Government agencies (DARPA, NSF, EU Horizon) are actively funding hardware verification research.
* **The cost of failure is catastrophic.** A single missed bug in a processor core that ships in millions of devices cannot be patched. It either persists as a permanent vulnerability or requires a product recall.

### 7.2 Publication Target Assessment

| Dimension | Assessment |
|:---|:---|
| **Novelty** | The LLM + RL + coverage-conditioned feedback loop for hardware fuzzing has no direct precedent. Strong novelty claim. |
| **Impact** | Finding even one real RTL bug in CVA6, Ibex, or Rocket is an immediate, citable contribution. The RISC-V Foundation tracks these. |
| **Reproducibility** | The entire stack (Verilator, Spike, target cores, CodeLlama) is open-source. Reviewers strongly favor this. |
| **Timeliness** | RISC-V security is a hot topic in 2025–2026. GenHuzz (USENIX 2025), RLFuzz (2026), and MutaGen (2026) prove the community is active. |
| **Differentiation** | Multi-instruction seeds, coverage-conditioned LLM prompting, privilege escalation targeting, and Ape-X scaling distinguish us clearly from GenHuzz/RLFuzz. |

### 7.3 Target Venues

| Venue | Tier | Fit | Submission Cycle |
|:---|:---|:---|:---|
| **USENIX Security** | Top-tier | Published GenHuzz — very receptive to ML+hardware security | 3 deadlines/year |
| **IEEE S&P (Oakland)** | Top-tier | Hardware security track, strong fit for privilege escalation angle | Annual (December) |
| **ACM CCS** | Top-tier | Systems security, good fit for the RL methodology | Annual (May) |
| **DAC** | Top-tier (EDA) | Design Automation Conference — hardware verification angle | Annual (November) |
| **HOST** | Specialized | Hardware-Oriented Security and Trust — niche but highly respected | Annual |
| **NDSS** | Top-tier | Network and Distributed System Security — if emphasis is on IoT/embedded | Annual (May) |

### 7.4 Paper Title

> **"LLM-Seeded Reinforcement Learning for Coverage-Guided Hardware Fuzzing of RISC-V Processors"**

### 7.5 Contribution Claims (for the paper abstract)

1. First system combining LLM-generated structured multi-instruction seeds with RL-guided adaptive mutation for hardware fuzzing.
2. Coverage-conditioned LLM prompting — a novel seed generation strategy where the LLM is directed toward specific coverage gaps in real time.
3. Privilege escalation as an explicit, reward-shaped fuzzing objective with dedicated seed sequences and cross-check enhancements for detecting privilege boundary violations.
4. A scalable Ape-X distributed architecture enabling 100× throughput improvement on GPU hardware.
5. Evaluation on production-grade open-source RISC-V cores (CVA6, Ibex) with quantified coverage improvements over random, AFL-style, RL-only, and LLM-only baselines.

---

## 8. Limitations, Risks & Mitigations

> Every research approach has failure modes. A credible paper acknowledges them upfront and explains how they are managed. Reviewers will specifically look for this section.

### 8.1 LLM Assembly Quality Is Unproven at Scale

**The Risk:** CodeLlama and StarCoder2 are trained predominantly on Python, JavaScript, C, and Java. RISC-V assembly constitutes a vanishingly small fraction of their training corpora. While these models can produce syntactically plausible assembly, they may:
- Use non-existent CSR addresses or register names
- Generate immediate values that overflow the encoding bit-width
- Produce instruction sequences that are syntactically valid but architecturally nonsensical (e.g., a branch to an address that would be mid-instruction)
- Hallucinate entirely when given coverage-conditioned prompts (Mode 2), since coverage bitmaps are far outside their training distribution

**Mitigation:**
- Every LLM-generated sequence passes through `riscv64-unknown-elf-as` (the GNU assembler) before entering the seed queue. Anything that fails assembly is silently discarded.
- Track the **assembly pass rate** as a metric. If it drops below 50%, the prompt templates need revision.
- For coverage-conditioned prompting, translate the raw coverage bitmap into natural language descriptions ("the pipeline has never flushed during the memory stage") rather than passing raw binary vectors. LLMs respond far better to natural language than structured data.
- **Ablation study required:** The paper must include an ablation comparing LLM-seeded RL vs. RL-only (no LLM) to quantify whether the LLM actually helps. If the LLM seeds provide <5% coverage improvement over random seeds, the contribution claim weakens significantly.

### 8.2 Coverage Metric Quality — Not All Toggles Are Equal

**The Risk:** Multiplexer toggle coverage treats all toggles as equally valuable. In reality:
- ~80–90% of toggles are **data-path bits** (ALU operand muxes, register file read ports) that flip trivially with any arithmetic instruction. Reaching them provides no useful signal.
- ~10–20% of toggles are **control-path bits** (exception logic, privilege mode selectors, pipeline hazard detectors) that require specific instruction sequences to flip. These are where bugs hide.

If the reward function treats all toggles equally, the agent will learn to chase easy data-path toggles and plateau before reaching the hard control-path ones.

**Mitigation:**
- **Weighted coverage scoring:** Assign higher reward to toggles in control-path modules (CSR unit, exception handler, privilege checker, hazard detection unit) and lower reward to data-path modules (ALU, register file). This requires a one-time manual classification of RTL modules, which is feasible for open-source cores where the module hierarchy is documented.
- **Diminishing returns:** Apply a logarithmic decay to the reward for data-path toggles (first flip gets full reward, subsequent flips in the same module get exponentially less). Control-path toggles always get full reward.
- **FSM state coverage as primary metric:** FSM states are inherently control-path-focused. Using FSM state coverage as the primary reward and mux toggle as secondary naturally biases the agent toward meaningful exploration.

### 8.3 Simulation Speed Is the True Bottleneck

**The Risk:** The RL agent's intelligence is rate-limited by how fast the simulator can run. Verilator simulation speeds for different cores:

| Core | Approximate Verilator Speed | Time per 10-instruction test |
|:---|:---|:---|
| PicoRV32 | ~5M cycles/sec | ~2 µs |
| Ibex | ~1M cycles/sec | ~10 µs |
| CVA6 | ~200K cycles/sec | ~50 µs |
| BOOM | ~50K cycles/sec | ~200 µs |

At 50 µs per test on CVA6, a single worker processes ~20K tests/second. Even with 256 workers, that's ~5M tests/second — impressive but still far below the billions needed for deep coverage.

**Mitigation:**
- The Ape-X architecture (§5) directly addresses this by parallelizing simulation across hundreds of workers.
- **Verilator `--threads`** enables multi-threaded simulation within each instance.
- **Test batching:** Group multiple instruction sequences into a single simulation run (reset once, execute 100 tests sequentially) to amortize the simulation startup cost.
- **Early termination:** If a mutated sequence produces an illegal instruction trap in the first instruction, skip the remaining 9 instructions. Don't waste cycles on obviously dead inputs.

### 8.4 No Guarantee of Finding New Bugs

**The Risk:** Well-maintained cores like CVA6 and Ibex have been verified by professional teams for years. The open-source RISC-V community actively fuzzes these cores. It is entirely possible that our system achieves excellent coverage but discovers **zero new bugs**.

**Mitigation:**
- **The paper must be viable on coverage improvement alone.** Structure the evaluation to demonstrate:
  - Higher coverage achieved faster (coverage-vs-time curves)
  - Coverage plateau broken through (reaching states that baseline approaches never reach)
  - Ablation studies proving each component (LLM seeds, RL mutation, curriculum learning) contributes
- **Target less-tested cores as secondary targets:** While CVA6 is the primary target, also run on newer or less-verified cores (e.g., community forks, early-stage RISC-V designs) where bugs are more likely.
- **Bug seeding for controlled evaluation:** Intentionally inject known bugs into a core (e.g., break a forwarding path, corrupt a CSR access check) and measure time-to-discovery across approaches. This provides quantitative bug-finding comparison even when no organic bugs exist.

### 8.5 Spike (Golden Reference) Is Not Infallible

**The Risk:** The entire differential testing methodology assumes Spike is correct. But Spike has had documented bugs:
- In the Vector extension (V) implementation
- In the Hypervisor extension (H) privilege semantics
- In edge cases of misaligned memory access handling

A "divergence" flagged as a DUT bug could actually be a **Spike bug**, leading to wasted triage effort or, worse, false claims in the paper.

**Mitigation:**
- **Restrict to base ISA (RV32I/RV64I) for the core paper results.** Spike is extensively validated for the base ISA. Extension fuzzing should be presented as future work with appropriate caveats.
- **Triple-check with a third reference:** For any discovered divergence, cross-reference the RISC-V ISA specification manually and, if possible, test on a third simulator (e.g., QEMU's RISC-V target or the Sail formal model) to confirm which side is wrong.
- **Report divergences, not "bugs."** In the paper, use the term "behavioral divergence" until manual triage confirms the root cause. This is standard practice in differential testing literature.

### 8.6 Zero Transfer Learning Across Cores

**The Risk:** An RL agent trained on PicoRV32 learns absolutely nothing transferable to CVA6. Different cores have entirely different RTL structures, different coverage spaces, and different reward landscapes. You must retrain from scratch for every new core, which means:
- The curriculum learning investment (Phase 7) must be repeated per core.
- Hyperparameter tuning results on one core may not apply to another.
- The system is hardware-agnostic in design but hardware-specific in practice.

**Mitigation:**
- **This is actually an accepted norm in the field.** GenHuzz, RLFuzz, and DifuzzRTL all retrain per target. No existing hardware fuzzer claims cross-core transfer. Reviewers will not penalize this.
- **Frame it as a feature:** The agent learns the specific quirks of each core's implementation, which is exactly what you want — a generic agent would miss implementation-specific bugs.
- **Future work:** Propose meta-learning (learning-to-learn-to-fuzz) as a future direction where the agent learns a core-agnostic mutation strategy from experience across multiple cores.

### 8.7 Complexity Budget — Are We Over-Engineering?

**The Risk:** The system has many moving parts: LLM inference, DQN training, Ape-X distributed workers, Redis replay buffer, VPI bridge, Verilator, Spike, curriculum scheduler, coverage extractor, bug triage pipeline. Each component is a potential failure point. Integration testing this system is itself a major engineering effort.

A reviewer may reasonably ask: "Could a simpler approach (e.g., just LLM-generated tests without RL, or RL without LLM) achieve 80% of the results with 20% of the complexity?"

**Mitigation:**
- **The ablation study is the answer.** The paper must include:
  - RL-only (no LLM) → shows LLM seeds add value
  - LLM-only (no RL) → shows RL mutation adds value  
  - Random baseline → shows intelligence adds value
  - Full system → shows the combination is greater than the sum
- If any component fails to show meaningful improvement in the ablation, remove it from the contribution claims. Intellectual honesty is more publishable than overclaiming.
- **Start simple, add complexity incrementally.** Build and validate RL-only first. Add LLM seeds second. Add Ape-X scaling third. Each addition must demonstrably improve results.

### Summary: Risk Matrix

| Risk | Severity | Probability | Mitigation Quality |
|:---|:---|:---|:---|
| LLM generates invalid assembly | Medium | High (30–40% rejection expected) | Strong — assembler validation catches 100% |
| Coverage metric rewards meaningless toggles | High | Medium | Good — weighted scoring + FSM focus |
| Simulation speed bottleneck | High | Certain | Strong — Ape-X + parallelism directly addresses |
| No new bugs found | Medium | Medium-High | Good — paper viable on coverage alone + bug seeding |
| Spike golden reference has bugs | Low | Low (for base ISA) | Strong — restrict to base ISA + triple-check |
| No cross-core transfer | Low | Certain | N/A — accepted norm in the field |
| System over-complexity | Medium | Medium | Good — ablation study validates each component |
