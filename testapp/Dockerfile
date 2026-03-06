FROM emscripten/emsdk:3.1.51

WORKDIR /src

# Build script: compile editor.cpp to editor.js + editor.wasm
CMD emcc editor.cpp -o /out/editor.js \
    -s WASM=1 \
    -s "EXPORTED_RUNTIME_METHODS=['ccall','cwrap','UTF8ToString']" \
    -s "EXPORTED_FUNCTIONS=['_editor_insert','_editor_insert_str','_editor_delete','_editor_delete_forward','_editor_get_content','_editor_set_content','_editor_get_cursor','_editor_set_cursor','_editor_move_left','_editor_move_right','_malloc','_free']" \
    -s MODULARIZE=1 \
    -s EXPORT_NAME='EditorModule' \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s ENVIRONMENT='web' \
    -O2 \
    -std=c++17
