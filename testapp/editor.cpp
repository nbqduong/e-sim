#include <string>
#include <cstring>
#include <emscripten.h>

class EditorState {
public:
    std::string buffer;
    int cursor = 0;

    void insert(char ch) {
        if (cursor < 0) cursor = 0;
        if (cursor > static_cast<int>(buffer.size())) cursor = static_cast<int>(buffer.size());
        buffer.insert(buffer.begin() + cursor, ch);
        cursor++;
    }

    void insertStr(const char* s) {
        if (!s) return;
        std::string str(s);
        if (cursor < 0) cursor = 0;
        if (cursor > static_cast<int>(buffer.size())) cursor = static_cast<int>(buffer.size());
        buffer.insert(cursor, str);
        cursor += static_cast<int>(str.size());
    }

    void deleteChar() {
        if (cursor > 0 && !buffer.empty()) {
            cursor--;
            buffer.erase(cursor, 1);
        }
    }

    const char* getContent() const {
        return buffer.c_str();
    }

    void setContent(const char* s) {
        buffer = s ? s : "";
        cursor = static_cast<int>(buffer.size());
    }

    int getCursor() const {
        return cursor;
    }

    void setCursor(int pos) {
        if (pos < 0) pos = 0;
        if (pos > static_cast<int>(buffer.size())) pos = static_cast<int>(buffer.size());
        cursor = pos;
    }

    void moveCursorLeft() {
        if (cursor > 0) cursor--;
    }

    void moveCursorRight() {
        if (cursor < static_cast<int>(buffer.size())) cursor++;
    }

    void deleteForward() {
        if (cursor < static_cast<int>(buffer.size())) {
            buffer.erase(cursor, 1);
        }
    }

    void moveCursorUp() {
        // Find start of current line
        int currentLineStart = cursor;
        while (currentLineStart > 0 && buffer[currentLineStart - 1] != '\n') {
            currentLineStart--;
        }
        
        int column = cursor - currentLineStart;
        
        // If we are on the first line, move to start
        if (currentLineStart == 0) {
            cursor = 0;
            return;
        }
        
        // Find start of previous line
        int prevLineStart = currentLineStart - 1;
        while (prevLineStart > 0 && buffer[prevLineStart - 1] != '\n') {
            prevLineStart--;
        }
        
        // Calculate the length of previous line
        int prevLineLength = (currentLineStart - 1) - prevLineStart;
        
        // Move to the same column or the end of the previous line
        int targetColumn = std::min(column, prevLineLength);
        cursor = prevLineStart + targetColumn;
    }

    void moveCursorDown() {
        // Find start of current line
        int currentLineStart = cursor;
        while (currentLineStart > 0 && buffer[currentLineStart - 1] != '\n') {
            currentLineStart--;
        }
        
        int column = cursor - currentLineStart;
        
        // Find end of current line
        int currentLineEnd = cursor;
        while (currentLineEnd < static_cast<int>(buffer.size()) && buffer[currentLineEnd] != '\n') {
            currentLineEnd++;
        }
        
        // If we are on the last line, move to end
        if (currentLineEnd == static_cast<int>(buffer.size())) {
            cursor = static_cast<int>(buffer.size());
            return;
        }
        
        // the next line starts right after currentLineEnd
        int nextLineStart = currentLineEnd + 1;
        
        // Find end of next line
        int nextLineEnd = nextLineStart;
        while (nextLineEnd < static_cast<int>(buffer.size()) && buffer[nextLineEnd] != '\n') {
            nextLineEnd++;
        }
        
        int nextLineLength = nextLineEnd - nextLineStart;
        
        // Move to the same column or the end of the next line
        int targetColumn = std::min(column, nextLineLength);
        cursor = nextLineStart + targetColumn;
    }
};

static EditorState g_editor;

extern "C" {

EMSCRIPTEN_KEEPALIVE
void editor_insert(char ch) {
    g_editor.insert(ch);
}

EMSCRIPTEN_KEEPALIVE
void editor_insert_str(const char* s) {
    g_editor.insertStr(s);
}

EMSCRIPTEN_KEEPALIVE
void editor_delete() {
    g_editor.deleteChar();
}

EMSCRIPTEN_KEEPALIVE
void editor_delete_forward() {
    g_editor.deleteForward();
}

EMSCRIPTEN_KEEPALIVE
const char* editor_get_content() {
    return g_editor.getContent();
}

EMSCRIPTEN_KEEPALIVE
void editor_set_content(const char* s) {
    g_editor.setContent(s);
}

EMSCRIPTEN_KEEPALIVE
int editor_get_cursor() {
    return g_editor.getCursor();
}

EMSCRIPTEN_KEEPALIVE
void editor_set_cursor(int pos) {
    g_editor.setCursor(pos);
}

EMSCRIPTEN_KEEPALIVE
void editor_move_left() {
    g_editor.moveCursorLeft();
}

EMSCRIPTEN_KEEPALIVE
void editor_move_right() {
    g_editor.moveCursorRight();
}

EMSCRIPTEN_KEEPALIVE
void editor_move_up() {
    g_editor.moveCursorUp();
}

EMSCRIPTEN_KEEPALIVE
void editor_move_down() {
    g_editor.moveCursorDown();
}

EMSCRIPTEN_KEEPALIVE
void init_wasm_editor() {
    g_editor.buffer = "";
    g_editor.cursor = 0;
}

} // extern "C"
