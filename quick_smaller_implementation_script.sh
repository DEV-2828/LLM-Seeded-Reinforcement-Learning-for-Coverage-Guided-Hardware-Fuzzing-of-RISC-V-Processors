#!/bin/bash

source .venv/bin/activate
cd smaller_implementation/verilator_env
bash build_bridge.sh
bash build_buggy.sh
python3 differential_fuzzer.py