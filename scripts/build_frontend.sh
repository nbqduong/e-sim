#!/bin/bash
set -e

echo "Starting frontend workflow..."

# Copy input files to public/ if IN_DIR is set
if [ -n "$IN_DIR" ] && [ -d "$IN_DIR" ]; then
    echo "Copying input files from $IN_DIR to public/..."
    mkdir -p public
    cp -r "$IN_DIR"/* public/
fi

# Install dependencies and build
echo "Installing dependencies..."
npm install

echo "Building frontend..."
npm run build

# Copy output if OUT_DIR is set
if [ -n "$OUT_DIR" ]; then
    echo "Copying build output to $OUT_DIR..."
    mkdir -p "$OUT_DIR"
    cp -r dist/* "$OUT_DIR"/
fi

echo "Frontend building process finished successfully."
