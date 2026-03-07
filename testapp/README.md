# WASM Text Editor

A minimal text editor compiled from C++ to WebAssembly using Emscripten.

## Build with Docker

```bash
# From the e-sim root directory:

# 1. Build the Docker image
docker build -t esim-wasm-builder testapp/

# 2. Run the build (outputs to frontend/public/wasm/)
mkdir -p frontend/public/wasm
docker run --rm \
  -v "$(pwd)/testapp:/src" \
  -v "$(pwd)/frontend/public/wasm:/out" \
  esim-wasm-builder

# Verify output
ls frontend/public/wasm/editor.js frontend/public/wasm/editor.wasm
```

## Exported API

| Function | Signature | Description |
|----------|-----------|-------------|
| `editor_insert` | `(char) → void` | Insert character at cursor |
| `editor_insert_str` | `(const char*) → void` | Insert string at cursor |
| `editor_delete` | `() → void` | Backspace at cursor |
| `editor_delete_forward` | `() → void` | Delete forward at cursor |
| `editor_get_content` | `() → const char*` | Get buffer contents |
| `editor_set_content` | `(const char*) → void` | Set buffer contents |
| `editor_get_cursor` | `() → int` | Get cursor position |
| `editor_set_cursor` | `(int) → void` | Set cursor position |
| `editor_move_left` | `() → void` | Move cursor left |
| `editor_move_right` | `() → void` | Move cursor right |

## Usage from JavaScript

```javascript
const Module = await EditorModule();

const insert = Module.cwrap('editor_insert', null, ['number']);
const insertStr = Module.cwrap('editor_insert_str', null, ['string']);
const getContent = Module.cwrap('editor_get_content', 'string', []);
const deleteChar = Module.cwrap('editor_delete', null, []);

insertStr("Hello, World!");
console.log(getContent()); // "Hello, World!"
```
