#!/bin/bash
set -e

# Build in /tmp to avoid GNU Make's space-in-path limitation
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=$(mktemp -d /tmp/verilator_buggy_XXXXXX)

echo "=== Building Buggy ALU for Differential Testing ==="
echo "Build dir: $BUILD_DIR"

# Copy source files to temp build directory
cp "$SCRIPT_DIR/alu_buggy.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/alu_wrapper.cpp" "$BUILD_DIR/"

cd "$BUILD_DIR"

# Run Verilator with --prefix Valu so generated files match alu_wrapper.cpp
verilator -Wall -Wno-DECLFILENAME --prefix Valu --cc alu_buggy.v

# Build with -fPIC for shared library
cd obj_dir
make -f Valu.mk CXXFLAGS="-fPIC" Valu__ALL.a verilated.o verilated_threads.o
cd ..

# Compile shared library
VERILATOR_ROOT=$(verilator -V | grep VERILATOR_ROOT | head -n1 | awk '{print $3}')
g++ -fPIC -shared \
    -I./obj_dir \
    -I$VERILATOR_ROOT/include \
    -I$VERILATOR_ROOT/include/vltstd \
    alu_wrapper.cpp \
    obj_dir/Valu__ALL.a \
    obj_dir/verilated.o \
    obj_dir/verilated_threads.o \
    -pthread -lpthread \
    -o libalu_buggy.so

# Copy result back
mkdir -p "$SCRIPT_DIR/obj_dir_buggy"
cp libalu_buggy.so "$SCRIPT_DIR/obj_dir_buggy/"

# Clean up
rm -rf "$BUILD_DIR"

echo "Buggy shared library built: obj_dir_buggy/libalu_buggy.so"
echo "=== Done ==="
