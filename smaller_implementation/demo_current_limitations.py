"""
Demo the limitations that the current smaller implementation can already simulate.

This script focuses on two things the repo can do today:
1. Compare guided RL mutation against random mutation in the toy coverage environment.
2. Show a concrete differential-testing divergence between the clean and buggy ALU.

It also prints the main gaps that are not yet represented by the current setup.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "mock_env")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "verilator_env")))

from agent import DQNAgent
from mock_env.env_mock import MockALUEnv
from verilator_env.differential_fuzzer import BuggyVerilatorALU
from verilator_env.env_verilator import VerilatorALU
from verilator_env.golden_model import golden_alu


@dataclass
class TrialResult:
    final_coverage: int
    first_full_coverage_step: int | None


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def run_random_trial(seed: int, episodes: int = 50, steps_per_episode: int = 25) -> TrialResult:
    set_seed(seed)
    env = MockALUEnv()
    first_full_coverage_step = None
    total_steps = 0

    for _ in range(episodes):
        env.reset()
        for _ in range(steps_per_episode):
            _, _, done, _ = env.step(np.random.randint(env.action_space_n))
            total_steps += 1
            if done:
                first_full_coverage_step = total_steps if first_full_coverage_step is None else first_full_coverage_step
                break

    return TrialResult(final_coverage=int(np.sum(env.coverage)), first_full_coverage_step=first_full_coverage_step)


def run_rl_trial(seed: int, episodes: int = 50, steps_per_episode: int = 25) -> TrialResult:
    set_seed(seed)
    env = MockALUEnv()
    agent = DQNAgent(state_dim=env.state_dim, action_dim=env.action_space_n)
    first_full_coverage_step = None
    total_steps = 0

    for _ in range(episodes):
        state = env.reset()
        for _ in range(steps_per_episode):
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            agent.step(state, action, reward, next_state, done)
            state = next_state
            total_steps += 1
            if done:
                first_full_coverage_step = total_steps if first_full_coverage_step is None else first_full_coverage_step
                break
        agent.decay_epsilon()
        if total_steps % 10 == 0:
            agent.update_target_network()

    return TrialResult(final_coverage=int(np.sum(env.coverage)), first_full_coverage_step=first_full_coverage_step)


def demo_coverage_plateau() -> None:
    print("=== Limitation Demo 1: Coverage Plateau in the Toy Environment ===")
    seeds = [1, 7, 13]
    random_trials = [run_random_trial(seed) for seed in seeds]
    rl_trials = [run_rl_trial(seed) for seed in seeds]

    def summarize(trials: list[TrialResult]) -> tuple[float, int]:
        avg_final = sum(trial.final_coverage for trial in trials) / len(trials)
        full_hits = sum(1 for trial in trials if trial.first_full_coverage_step is not None)
        return avg_final, full_hits

    random_avg, random_full_hits = summarize(random_trials)
    rl_avg, rl_full_hits = summarize(rl_trials)

    print(f"Random baseline final coverage average: {random_avg:.2f}/10")
    print(f"Random baseline trials reaching full coverage: {random_full_hits}/{len(random_trials)}")
    print(f"RL agent final coverage average: {rl_avg:.2f}/10")
    print(f"RL agent trials reaching full coverage: {rl_full_hits}/{len(rl_trials)}")
    print("Interpretation: the current environment can already show coverage guidance vs blind mutation, but the search space is still tiny.")
    print()


def demo_differential_bug() -> None:
    print("=== Limitation Demo 2: Differential Testing Finds a Concrete Bug ===")
    clean = VerilatorALU()
    buggy = BuggyVerilatorALU()

    tests = [
        (0x00000033, 15, 10, "ADD"),
        (0x40000033, 15, 10, "SUB"),
        (0x00007033, 0xF, 0xF, "AND"),
        (0x00006033, 0xF, 0xA, "OR"),
    ]

    for inst, rs1, rs2, name in tests:
        clean_rd = clean.step(inst, rs1, rs2)
        buggy_rd = buggy.step(inst, rs1, rs2)
        golden_rd, op_name = golden_alu(inst, rs1, rs2)
        status = "MATCH" if clean_rd == golden_rd and buggy_rd == golden_rd else "DIVERGENCE" if buggy_rd != golden_rd else "OK"
        print(
            f"{name:>4} | golden={golden_rd:#010x} | clean={clean_rd:#010x} | buggy={buggy_rd:#010x} | {status} ({op_name})"
        )

    print("Interpretation: the current pipeline can already detect a simple functional RTL bug, but only for single-instruction ALU behavior.")
    print()


def print_missing_items() -> None:
    print("=== Still Missing ===")
    missing_items = [
        "Multi-instruction programs and instruction-sequence seeds",
        "Real pipeline hazards, stalls, flushes, and privilege transitions",
        "Exception and CSR behavior",
        "FSM-state and mux-toggle coverage extraction",
        "Spike-based differential checking for a real ISA-level oracle",
        "LLM-generated structured seeds",
        "Parallel workers / distributed replay buffer scaling",
    ]
    for item in missing_items:
        print(f"- {item}")


def main() -> None:
    demo_coverage_plateau()
    demo_differential_bug()
    print_missing_items()


if __name__ == "__main__":
    main()