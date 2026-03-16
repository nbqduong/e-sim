#!/bin/sh
set -e

# Copy input files to public/ if IN_DIR is set
if [ -n "$IN_DIR" ]; then
    echo "Copying input files from $IN_DIR to ${APP_DIR}/frontend/public/"
    cp -r "$IN_DIR"/* "${APP_DIR}/frontend/public/"
fi

# Install dependencies and build
npm install
npm run build

# Copy output if OUT_DIR is set
if [ -n "$OUT_DIR" ]; then
    echo "Copying build output to $OUT_DIR"
    mkdir -p "$OUT_DIR"
    cp -r out/* "$OUT_DIR"/
fi
