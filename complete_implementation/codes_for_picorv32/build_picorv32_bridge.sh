#!/bin/bash
set -e

# Build in /tmp to avoid GNU Make's space-in-path limitation
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR=$(mktemp -d /tmp/verilator_build_XXXXXX)
PICORV32_DIR="$SCRIPT_DIR/../picorv32"

echo "Building Verilator bridge for picorv32 (build dir: $BUILD_DIR)..."

# Copy source files to temp build directory
cp "$PICORV32_DIR/picorv32.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/picorv32_top.v" "$BUILD_DIR/"
cp "$SCRIPT_DIR/picorv32_wrapper.cpp" "$BUILD_DIR/"

cd "$BUILD_DIR"

# Run Verilator
# Added -Wno-lint because picorv32.v has many stylistic warnings we don't care about
# Added --top-module picorv32_top to resolve MULTITOP warning
verilator -Wno-lint --top-module picorv32_top --cc picorv32_top.v picorv32.v

# Build with -fPIC for shared library
cd obj_dir
make -f Vpicorv32_top.mk CXXFLAGS="-fPIC" Vpicorv32_top__ALL.a verilated.o verilated_threads.o
cd ..

# Compile shared library
g++ -fPIC -shared \
    -I./obj_dir \
    -I/usr/share/verilator/include \
    -I/usr/share/verilator/include/vltstd \
    picorv32_wrapper.cpp \
    obj_dir/Vpicorv32_top__ALL.a \
    obj_dir/verilated.o \
    obj_dir/verilated_threads.o \
    -pthread -lpthread -latomic \
    -o libpicorv32.so

# Copy result back
mkdir -p "$SCRIPT_DIR/obj_dir"
cp libpicorv32.so "$SCRIPT_DIR/obj_dir/"

# Clean up
rm -rf "$BUILD_DIR"

echo "Shared library built: obj_dir/libpicorv32.so"
