#!/bin/bash
set -e

# Build the BUGGY version of the ALU for differential testing.
# Uses alu_buggy.v instead of alu.v.
# --prefix Valu forces the same class name so alu_wrapper.cpp works unchanged.

echo "=== Building Buggy ALU for Differential Testing ==="

echo "Cleaning previous build..."
rm -rf obj_dir_buggy

echo "Running Verilator on alu_buggy.v..."
verilator -Wall -Wno-DECLFILENAME --prefix Valu --cc alu_buggy.v --Mdir obj_dir_buggy

echo "Generating static library with -fPIC..."
cd obj_dir_buggy
make -f Valu.mk CXXFLAGS="-fPIC" LDFLAGS="-shared" Valu__ALL.a verilated.o verilated_threads.o
cd ..

echo "Compiling shared library..."
g++ -fPIC -shared \
    -I./obj_dir_buggy \
    -I/usr/share/verilator/include \
    -I/usr/share/verilator/include/vltstd \
    alu_wrapper.cpp \
    obj_dir_buggy/Valu__ALL.a \
    obj_dir_buggy/verilated.o \
    obj_dir_buggy/verilated_threads.o \
    -pthread -lpthread -latomic \
    -o obj_dir_buggy/libalu_buggy.so

echo "Buggy shared library built: obj_dir_buggy/libalu_buggy.so"
echo "=== Done ==="
