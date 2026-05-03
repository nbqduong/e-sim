#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUTPUT_DIR="$PROJECT_ROOT/frontendv1/src/wasm/generated"

mkdir -p "$OUTPUT_DIR"

emcc "$PROJECT_ROOT/simulator/simulator.cpp" \
  -O3 \
  --no-entry \
  -std=c++17 \
  -s WASM=1 \
  -s MODULARIZE=1 \
  -s EXPORT_ES6=1 \
  -s ENVIRONMENT=web \
  -s FILESYSTEM=0 \
  -s ALLOW_MEMORY_GROWTH=0 \
  -s INITIAL_MEMORY=131072 \
  -s NO_EXIT_RUNTIME=1 \
  -s EXPORT_ALL=1 \
  -s EXPORTED_FUNCTIONS='["_malloc","_free","_init_simulator","_start_loop","_pause_loop","_destroy_simulator","_get_pairs_ptr","_get_pair_count"]' \
  -o "$OUTPUT_DIR/simulator.js"
