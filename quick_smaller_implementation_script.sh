#!/bin/bash
set -e

# Navigate to repo root (handles paths with spaces)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Activating virtual environment ==="
source .venv/bin/activate

echo ""
echo "=== Running Milestone 1: Mock Environment ==="
cd "$SCRIPT_DIR/proof_of_concept_smaller_implementation/mock_env"
python3 train_mock.py

echo ""
echo "=== Building Milestone 2-3: Verilator Bridge ==="
cd "$SCRIPT_DIR/proof_of_concept_smaller_implementation/verilator_env"
bash build_bridge.sh

echo ""
echo "=== Building Milestone 5: Buggy ALU ==="
bash build_buggy.sh

echo ""
echo "=== Running Milestone 5: Differential Fuzzer ==="
python3 differential_fuzzer.py

# echo ""
# echo "=== Running Current Limitations Demo ==="
# cd "$SCRIPT_DIR"
# python3 "$SCRIPT_DIR/proof_of_concept_smaller_implementation/demo_current_limitations.py"