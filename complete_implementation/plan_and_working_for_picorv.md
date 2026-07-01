# PicoRV32 Integration & Working Flow

This document explains the architecture of our PicoRV32 integration and traces the lifecycle of an instruction as it travels from our Python fuzzer down to the hardware core.

---

## 1. The Architecture Stack

Our fuzzer needs to mutate instructions in Python and execute them in a hardware simulation. To achieve this quickly, we use a multi-layered bridge:

1. **The Python Fuzzer (`env_picorv32.py`)**: The top level where our Reinforcement Learning agent lives. It generates instructions as 32-bit integers.
2. **The `ctypes` Bridge**: Python uses the built-in `ctypes` library to load a compiled C++ shared library (`libpicorv32.so`) into memory, allowing Python to directly call C++ functions without heavy inter-process communication.
3. **The C++ Wrapper (`picorv32_wrapper.cpp`)**: A thin C API that exposes simple functions like `picorv32_load_instruction()` and `picorv32_step()`. It translates these simple commands into the complex signaling required by Verilator.
4. **Verilator (`Vpicorv32_top`)**: The C++ simulation engine that compiles our Verilog code into executable C++ classes.
5. **The Verilog Top Module (`picorv32_top.v`)**: Because the raw PicoRV32 core uses a complex AXI-like memory interface, this wrapper creates a mocked 4KB memory. It provides a "backdoor" (`load_en`, `load_addr`, `load_data`) for the C++ wrapper to inject instructions directly into this memory.
6. **The DUT (`picorv32.v`)**: The actual RISC-V processor core that fetches the instruction from our mocked memory, executes it, and updates its internal state.

---

## 2. Process Flow: The Lifecycle of a Fuzzing Step

### Step A: Initialization
When the python fuzzer starts, it creates a `VerilatorPicoRV32` object:
1. `ctypes` loads `libpicorv32.so`.
2. `picorv32_init()` is called, which instantiates the Verilator model `new Vpicorv32_top()`.
3. `picorv32_reset()` is called. This toggles the `rst` pin on the hardware for 5 clock cycles to ensure the core starts in a clean, known state.

### Step B: Loading an Instruction
Unlike our toy ALU which executed instructions instantly, a real processor fetches instructions from memory.
1. The Python agent calls `core.load_instruction(0x0, 0x003100b3)` (e.g., an `ADD` instruction).
2. The C++ wrapper asserts `load_en = 1`, `load_addr = 0x0`, and `load_data = 0x003100b3`, and ticks the clock once.
3. Inside `picorv32_top.v`, the mocked memory detects `load_en` and writes the instruction into its SRAM array at address 0.
4. The C++ wrapper de-asserts `load_en = 0`.

### Step C: Execution (Stepping)
PicoRV32 is a multi-cycle processor. It takes multiple clock cycles to fetch, decode, and execute a single instruction.
1. Python calls `core.step()` multiple times (e.g., in a loop).
2. The C++ wrapper toggles `clk = 1` then `clk = 0`, forcing Verilator to evaluate the hardware logic for one cycle.
3. Over several cycles, PicoRV32 will:
   - Assert `mem_valid` to request the instruction at the Program Counter (PC).
   - `picorv32_top.v` responds with `mem_ready` and returns the instruction from the mocked memory on `mem_rdata`.
   - The core decodes the instruction and executes the ALU operation.

### Step D: Extraction & Observation
After stepping the clock, the fuzzer needs to know what happened to calculate a reward and check for bugs.
1. Python calls `core.get_trap()`.
2. The C++ wrapper reads the `trap` pin directly from the Verilator model and returns it to Python. If `trap == 1`, the processor encountered a fault (e.g., an illegal instruction, or branching into uninitialized memory).
3. *(Future Implementation)*: Python will call `core.get_coverage()` to extract FSM states and MUX toggles to feed the RL agent's reward function.
4. *(Future Implementation)*: Python will extract the register file to diff against the Spike Golden Oracle.

---

## 3. Why This Architecture?

* **Speed**: By compiling the Verilog into C++ and using `ctypes`, we avoid the massive overhead of file I/O or socket communication. The Python fuzzer can execute hundreds of thousands of cycles per second.
* **Simplicity**: The `picorv32_top.v` memory mock abstracts away the headache of simulating complex AXI bus transactions, allowing the fuzzer to focus purely on injecting instruction streams.
* **Hardware Accuracy**: By simulating the real memory fetch cycles, we can discover pipeline and memory-ordering bugs that a single-cycle ALU simulation would miss completely.

---

## 4. Building and Running the Environment

To compile the C++ Verilator bridge and test the Python environment, navigate to the `codes_for_picorv32` directory and run the provided build script.

```bash
cd complete_implementation/codes_for_picorv32
chmod +x build_picorv32_bridge.sh
./build_picorv32_bridge.sh
python3 env_picorv32.py
python3 test_advanced_sequence.py
```

The script will compile `picorv32_top.v` using Verilator, build the shared library `libpicorv32.so`, and then the python script will test injecting an instruction and stepping the clock.
