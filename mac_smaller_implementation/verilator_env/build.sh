#!/bin/bash
set -e

# Build in /tmp to avoid GNU Make's space-in-path limitation
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=$(mktemp -d /tmp/verilator_test_XXXXXX)

echo "Compiling Verilog to C++ with Verilator..."

# Copy source files to temp build directory
cp "$SCRIPT_DIR/alu.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/main.cpp" "$BUILD_DIR/"

cd "$BUILD_DIR"

verilator -Wall --cc alu.v --exe main.cpp

echo "Building the C++ executable..."
make -j -C obj_dir -f Valu.mk Valu

echo "Running the C++ model..."
./obj_dir/Valu

# Clean up
rm -rf "$BUILD_DIR"
