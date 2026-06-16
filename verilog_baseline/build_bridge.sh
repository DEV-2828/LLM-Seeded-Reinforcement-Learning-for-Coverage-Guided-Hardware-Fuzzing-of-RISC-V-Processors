#!/bin/bash
set -e

echo "Running Verilator..."
verilator -Wall --cc alu.v

echo "Generating static library with -fPIC..."
cd obj_dir
# Compile the generated C++ files and verilated.cpp into object files with Position Independent Code
make -f Valu.mk CXXFLAGS="-fPIC" LDFLAGS="-shared" Valu__ALL.a verilated.o verilated_threads.o
cd ..

echo "Compiling shared library..."
g++ -fPIC -shared \
    -I./obj_dir \
    -I/usr/share/verilator/include \
    -I/usr/share/verilator/include/vltstd \
    alu_wrapper.cpp \
    obj_dir/Valu__ALL.a \
    obj_dir/verilated.o \
    obj_dir/verilated_threads.o \
    -pthread -lpthread -latomic \
    -o obj_dir/libalu.so

echo "Shared library built successfully at obj_dir/libalu.so"

echo "----------------------------------------"
echo "Testing the Python wrapper:"
python3 env_verilator.py
