#!/bin/bash
set -e

echo "Compiling Verilog to C++ with Verilator..."
verilator -Wall --cc alu.v --exe main.cpp

echo "Building the C++ executable..."
make -j -C obj_dir -f Valu.mk Valu

echo "Running the C++ model..."
./obj_dir/Valu
