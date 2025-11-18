/*
 * STRling parse error implementation (ported from Python `errors.py`)
 *
 * Provides creation, freeing, and formatting helpers for parse errors.
 */

#include "errors.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static char* _str_clone(const char* s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char* r = (char*)malloc(n);
    if (!r) return NULL;
    memcpy(r, s, n);
    return r;
}

STRlingParseError* strling_parse_error_create(const char* message, int pos, const char* text, const char* hint) {
    STRlingParseError* e = (STRlingParseError*)malloc(sizeof(STRlingParseError));
    if (!e) return NULL;
    e->message = _str_clone(message);
    e->pos = pos;
    e->text = _str_clone(text);
    e->hint = _str_clone(hint);
    return e;
}

void strling_parse_error_free(STRlingParseError* err) {
    if (!err) return;
    free(err->message);
    free(err->text);
    free(err->hint);
    free(err);
}

char* strling_parse_error_format(const STRlingParseError* err) {
    if (!err) return _str_clone("");

    if (!err->text || err->text[0] == '\0') {
        /* simple format */
        char buf[256];
        snprintf(buf, sizeof(buf), "%s at position %d", err->message ? err->message : "", err->pos);
        return _str_clone(buf);
    }

    /* Find the line and column for the position */
    const char* text = err->text;
    int pos = err->pos;
    int current = 0;
    int line_num = 1;
    int col = pos;
    const char* line_start = text;
    const char* p = text;
    while (*p) {
        if (current + 1 > pos) break;
        if (*p == '\n') {
            if (current + 1 > pos) break;
            ++line_num;
            line_start = p + 1;
        }
        ++p;
        ++current;
    }

    /* compute column */
    col = pos - (int)(line_start - text);

    /* Extract the line until newline or end */
    const char* line_end = line_start;
    while (*line_end && *line_end != '\n') ++line_end;
    size_t line_len = (size_t)(line_end - line_start);

    /* Build formatted message (conservative buffer sizing) */
    size_t cap = 200 + line_len + (err->hint ? strlen(err->hint) : 0) + (err->message ? strlen(err->message) : 0);
    char* out = (char*)malloc(cap + 1);
    if (!out) return NULL;
    int written = snprintf(out, cap, "STRling Parse Error: %s\n\n> %d | ", err->message ? err->message : "", line_num);
    if (written < 0) { free(out); return NULL; }
    /* append line */
    strncat(out, line_start, line_len);
    strncat(out, "\n>   | ", 7);
    /* append caret spacing */
    for (int i = 0; i < col; ++i) strncat(out, " ", 1);
    strncat(out, "^", 1);

    if (err->hint && err->hint[0]) {
        strncat(out, "\n\nHint: ", 8);
        strncat(out, err->hint, strlen(err->hint));
    }

    return out;
}
