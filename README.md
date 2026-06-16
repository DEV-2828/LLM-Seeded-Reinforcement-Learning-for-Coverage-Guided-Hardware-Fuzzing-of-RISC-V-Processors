# LLM-Seeded Reinforcement Learning for Coverage-Guided Hardware Fuzzing of RISC-V Processors

A closed-loop automated hardware testing system that combines Large Language Models (LLMs) with Reinforcement Learning (RL) to discover elusive bugs in RISC-V processor RTL implementations. 

Traditional hardware verification methods (directed testing, constrained random verification, formal verification) struggle to cover the massive state space of modern processors, leaving a "coverage gap" where subtle, multi-instruction interaction bugs hide. This project bridges that gap by using an autonomously intelligent verification agent.

## How It Works

This system leverages three major components to find bugs that traditional methods miss:

1. **LLM Seed Generator**: A pretrained code language model (like CodeLlama or StarCoder2) synthesizes structurally diverse, multi-instruction RISC-V test programs. It is prompted with coverage gaps and pipeline stress scenarios to generate seeds that target underexplored hardware logic.
2. **RL Mutation Engine**: A Deep Q-Network (DQN) agent takes the LLM-generated seeds and learns which mutations (bit-flips, register swaps, etc.) push the hardware simulation into previously unreached states (measured via FSM state and multiplexer toggle coverage).
3. **Differential Execution Environment**: A pair of simulators running in lockstep:
   - **Verilator**: The Device Under Test (simulating the RTL design like CVA6, Ibex, or PicoRV32).
   - **Spike**: The Golden Reference (official RISC-V ISA simulator).
   
   Any divergence between Verilator and Spike—whether a functional bug, an exception failure, or a privilege escalation—indicates a hardware bug.

## Key Features

- **Multi-instruction Semantics**: Unlike typical single-instruction mutation fuzzers, the LLM generates real pipeline interactions (hazards, stalls, privilege transitions).
- **Coverage-Conditioned Prompting**: The LLM receives active feedback about which hardware states have *not* been reached, driving targeted seed generation.
- **Hardware-Agnostic Learning**: The RL agent learns online entirely from self-generated simulation experience; it does not require an external labeled dataset.
- **Ape-X Distributed Architecture**: Scales simulation across hundreds of parallel CPU workers while batching RL training and inference on a central GPU.
