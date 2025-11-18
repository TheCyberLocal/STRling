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
/* Port of bindings/python/src/STRling/core/errors.py */
#include "errors.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static char* dupstr(const char* s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char* p = (char*)malloc(n);
    if (p) memcpy(p, s, n);
    return p;
}

STRlingParseError* strling_parse_error_create(const char* message, int pos, const char* text, const char* hint) {
    STRlingParseError* e = (STRlingParseError*)malloc(sizeof(STRlingParseError));
    if (!e) return NULL;
    e->message = dupstr(message);
    e->pos = pos;
    e->text = dupstr(text);
    e->hint = dupstr(hint);
    return e;
}

void strling_parse_error_free(STRlingParseError* err) {
    if (!err) return;
    free(err->message);
    free(err->text);
    free(err->hint);
    free(err);
}

/* Return a newly allocated formatted message (mimics Python's _format_error) */
char* strling_parse_error_format(const STRlingParseError* err) {
    if (!err) return dupstr("Invalid error");

    if (!err->text || err->text[0] == '\0') {
        char buf[256];
        snprintf(buf, sizeof(buf), "%s at position %d", err->message ? err->message : "", err->pos);
        return dupstr(buf);
    }

    /* Find line and column */
    const char* s = err->text;
    int pos = err->pos;
    int current = 0;
    int line_num = 1;
    const char* line_start = s;
    const char* p = s;
    int col = pos;
    while (*p) {
        if (current + (int)(strchr(p, '\n') ? (strchr(p, '\n') - p + 1) : strlen(p)) > pos) {
            break;
        }
        const char* nl = strchr(p, '\n');
        if (!nl) break;
        current += (int)(nl - p + 1);
        line_num++;
        p = nl + 1;
        line_start = p;
    }
    /* compute column */
    col = pos - current;

    /* extract line text */
    const char* line_end = strchr(line_start, '\n');
    size_t line_len = line_end ? (size_t)(line_end - line_start) : strlen(line_start);

    /* build formatted message */
    size_t needed = 512 + line_len + (err->hint ? strlen(err->hint) : 0);
    char* out = (char*)malloc(needed);
    if (!out) return NULL;
    snprintf(out, needed, "STRling Parse Error: %s\n\n> %d | %.*s\n>   | %*s^%s%s",
             err->message ? err->message : "",
             line_num,
             (int)line_len, line_start,
             col, "",
             "",
             err->hint ? (char[]){'\n','\0'} : "");

    /* The above snprintf left placeholders; build properly below to include hint */
    free(out);

    /* Create properly formatted string step-by-step */
    size_t base = 128;
    needed = base + line_len + (err->hint ? strlen(err->hint) + 16 : 0) + 32;
    out = (char*)malloc(needed);
    if (!out) return NULL;
    int written = snprintf(out, needed, "STRling Parse Error: %s\n\n> %d | %.*s\n>   | ",
             err->message ? err->message : "",
             line_num,
             (int)line_len, line_start);
    /* add spaces for column */
    int i;
    for (i = 0; i < col && written + 2 < (int)needed; ++i) out[written++] = ' ';
    if (written + 2 < (int)needed) out[written++] = '^';
    out[written] = '\0';
    if (err->hint) {
        strncat(out, "\n\nHint: ", needed - strlen(out) - 1);
        strncat(out, err->hint, needed - strlen(out) - 1);
    }
    return out;
}
