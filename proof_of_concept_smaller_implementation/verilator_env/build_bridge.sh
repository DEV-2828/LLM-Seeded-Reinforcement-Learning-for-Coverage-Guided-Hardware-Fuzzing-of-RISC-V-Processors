#!/bin/bash
set -e

# Build in /tmp to avoid GNU Make's space-in-path limitation
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=$(mktemp -d /tmp/verilator_build_XXXXXX)

echo "Building Verilator bridge (build dir: $BUILD_DIR)..."

# Copy source files to temp build directory
cp "$SCRIPT_DIR/alu.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/alu_wrapper.cpp" "$BUILD_DIR/"

cd "$BUILD_DIR"

# Run Verilator
verilator -Wall --cc alu.v

# Build with -fPIC for shared library
cd obj_dir
make -f Valu.mk CXXFLAGS="-fPIC" Valu__ALL.a verilated.o verilated_threads.o
cd ..

# Compile shared library
g++ -fPIC -shared \
    -I./obj_dir \
    -I/usr/share/verilator/include \
    -I/usr/share/verilator/include/vltstd \
    alu_wrapper.cpp \
    obj_dir/Valu__ALL.a \
    obj_dir/verilated.o \
    obj_dir/verilated_threads.o \
    -pthread -lpthread -latomic \
    -o libalu.so

# Copy result back
mkdir -p "$SCRIPT_DIR/obj_dir"
cp libalu.so "$SCRIPT_DIR/obj_dir/"

# Clean up
rm -rf "$BUILD_DIR"

echo "Shared library built: obj_dir/libalu.so"

# Quick test
cd "$SCRIPT_DIR"
echo "----------------------------------------"
echo "Testing the Python wrapper:"
python3 env_verilator.py
