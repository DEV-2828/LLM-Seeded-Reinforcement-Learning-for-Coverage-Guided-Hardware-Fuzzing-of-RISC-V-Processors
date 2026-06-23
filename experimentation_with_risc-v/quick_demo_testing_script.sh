#!/bin/bash
set -e

# Navigate to the demo folder root (handles paths with spaces)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
	echo "=== Using active virtual environment: $VIRTUAL_ENV ==="
elif [[ -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
	echo "=== Activating demo virtual environment ==="
	# shellcheck disable=SC1091
	source "$SCRIPT_DIR/.venv/bin/activate"
elif [[ -f "$SCRIPT_DIR/../.venv/bin/activate" ]]; then
	echo "=== Activating repo virtual environment ==="
	# shellcheck disable=SC1091
	source "$SCRIPT_DIR/../.venv/bin/activate"
else
	echo "=== No virtual environment found; using system python3 ==="
	echo "    If dependencies are missing, create or activate a venv before rerunning."
fi

echo ""
echo "=== Running Milestone 1: Mock Environment ==="
cd "$SCRIPT_DIR/mock_env"
python3 train_mock.py

echo ""
echo "=== Running Direct Verilog Runtime Smoke Test ==="
cd "$SCRIPT_DIR/verilator_env"
python3 env_verilator.py

# echo ""
# echo "=== Running Current Limitations Demo ==="
# cd "$SCRIPT_DIR"
# python3 demo_current_limitations.py