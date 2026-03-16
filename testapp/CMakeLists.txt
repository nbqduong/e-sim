cmake_minimum_required(VERSION 3.10)
project(WasmEditor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

add_executable(editor editor.cpp)

# Emscripten-specific flags
set_target_properties(editor PROPERTIES
    SUFFIX ".js"
    LINK_FLAGS "\
        -s WASM=1 \
        -s EXPORTED_RUNTIME_METHODS=['ccall','cwrap','UTF8ToString'] \
        -s EXPORTED_FUNCTIONS=['_editor_insert','_editor_insert_str','_editor_delete','_editor_delete_forward','_editor_get_content','_editor_set_content','_editor_get_cursor','_editor_set_cursor','_editor_move_left','_editor_move_right','_malloc','_free'] \
        -s MODULARIZE=1 \
        -s EXPORT_NAME='EditorModule' \
        -s ALLOW_MEMORY_GROWTH=1 \
        -s ENVIRONMENT='web' \
    "
)
