#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=$(mktemp -d /tmp/verilator_fsm_XXXXXX)

echo "=== Building Buggy FSM for Differential Testing ==="
cp "$SCRIPT_DIR/fsm_buggy.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/fsm_wrapper.cpp" "$BUILD_DIR/"
cd "$BUILD_DIR"

# Build with -Wno-lint to ignore unused signal warnings if any
verilator -Wno-lint -Wno-DECLFILENAME --prefix Vfsm --cc fsm_buggy.v

cd obj_dir
make -f Vfsm.mk CXXFLAGS="-fPIC" Vfsm__ALL.a verilated.o verilated_threads.o || make -f Vfsm.mk CXXFLAGS="-fPIC" Vfsm__ALL.a verilated.o
cd ..

g++ -fPIC -shared \
    -I./obj_dir \
    -I/usr/share/verilator/include \
    -I/usr/share/verilator/include/vltstd \
    fsm_wrapper.cpp \
    obj_dir/Vfsm__ALL.a \
    obj_dir/verilated.o \
    $(ls obj_dir/verilated_threads.o 2>/dev/null || echo "") \
    -pthread -lpthread -latomic \
    -o libfsm_buggy.so

mkdir -p "$SCRIPT_DIR/obj_dir_buggy"
cp libfsm_buggy.so "$SCRIPT_DIR/obj_dir_buggy/"
rm -rf "$BUILD_DIR"

echo "Buggy shared library built: obj_dir_buggy/libfsm_buggy.so"
echo "=== Done ==="
