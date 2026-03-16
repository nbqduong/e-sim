#!/bin/bash
# Build WASM artifacts from editor.cpp
# Run this from the e-sim root directory:
#   ./testapp/build.sh
#
# Requires: Docker OR Emscripten (emcc) installed locally

set -e

#should called at /home/worker/source/testapp
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"


echo "Out directory: $OUT_DIR"

mkdir -p "$OUT_DIR"

if command -v emcc &> /dev/null; then
    echo "Building with local Emscripten..."
    emcc "$SCRIPT_DIR/editor.cpp" -o "$OUT_DIR/editor.js" \
        -s WASM=1 \
        -s "EXPORTED_RUNTIME_METHODS=['ccall','cwrap','UTF8ToString']" \
        -s "EXPORTED_FUNCTIONS=['_editor_insert','_editor_insert_str','_editor_delete','_editor_delete_forward','_editor_get_content','_editor_set_content','_editor_get_cursor','_editor_set_cursor','_editor_move_left','_editor_move_right','_malloc','_free']" \
        -s MODULARIZE=1 \
        -s EXPORT_NAME='EditorModule' \
        -s ALLOW_MEMORY_GROWTH=1 \
        -s ENVIRONMENT='web' \
        -O2 \
        -std=c++17
elif command -v docker &> /dev/null; then
    echo "Building with Docker..."
    docker build -t esim-wasm-builder "$SCRIPT_DIR/"
    docker run --rm \
        -v "$SCRIPT_DIR:/src" \
        -v "$OUT_DIR:/out" \
        esim-wasm-builder
else
    echo "ERROR: Neither 'emcc' nor 'docker' found. Install Emscripten or Docker."
    exit 1
fi

echo "Build complete! Output:"
ls -la "$OUT_DIR/editor.js" "$OUT_DIR/editor.wasm"
