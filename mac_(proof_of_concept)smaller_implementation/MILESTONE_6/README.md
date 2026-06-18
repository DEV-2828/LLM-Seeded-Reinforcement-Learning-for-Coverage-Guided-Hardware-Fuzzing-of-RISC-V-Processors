# Milestone 6: Cloud Migration & Parallel Scaling (macOS)

This milestone implements a multi-worker architecture for the Reinforcement Learning Fuzzer to increase throughput and utilize parallel compute.

## How it works

We use PyTorch's `multiprocessing` to spawn `N` independent worker processes. Each worker:
1. Instantiates its own `DifferentialFuzzerEnv` which loads an isolated instance of the Verilator C++ library.
2. Uses an "actor" `DQNAgent` for pure inference to explore the environment.
3. Sends transition experiences `(state, action, reward, next_state, done)` over a multiprocessing `Queue` to the central process.
4. Periodically receives updated neural network weights from the central agent.

The main process runs the global `DQNAgent`, stores all experiences in its Replay Buffer, and continuously optimizes the network.

## Prerequisites

Before running, ensure the Verilator shared libraries are built:

```bash
cd ../verilator_env
bash build_bridge.sh   # Builds obj_dir/libalu.so
bash build_buggy.sh    # Builds obj_dir_buggy/libalu_buggy.so
```

## How to run

```bash
python3 parallel_fuzzer.py
```

### Configuration
Inside `parallel_fuzzer.py`, you can configure:
- `num_workers`: Set this to match your logical CPU cores for maximum throughput (default 4).
- `num_episodes_per_worker`: How many episodes each worker should complete.
