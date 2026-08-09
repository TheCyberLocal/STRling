/*
 * STRling Parser Implementation - Recursive Descent Parser for C
 *
 * Implements a complete recursive-descent parser that transforms STRling
 * DSL patterns into AST nodes. Mirrors the TypeScript reference implementation.
 */

#include "parser.h"
#include "nodes.h"
#include "errors.h"
#include "hint_engine.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>

/* ============================================================================
 * Cursor - tracks position in input text
 * ============================================================================ */

typedef struct {
    const char* text;
    size_t len;
    size_t i;
    int extended_mode;
    int in_class;
} Cursor;

static void cursor_init(Cursor* c, const char* text, int extended_mode) {
    c->text = text;
    c->len = strlen(text);
    c->i = 0;
    c->extended_mode = extended_mode;
    c->in_class = 0;
}

static int cursor_eof(Cursor* c) {
    return c->i >= c->len;
}

static char cursor_peek(Cursor* c, int offset) {
    size_t j = c->i + offset;
    if (j >= c->len) return '\0';
    return c->text[j];
}

static char cursor_take(Cursor* c) {
    if (cursor_eof(c)) return '\0';
    return c->text[c->i++];
}

static int cursor_match(Cursor* c, const char* s) {
    size_t slen = strlen(s);
    if (c->i + slen > c->len) return 0;
    if (strncmp(c->text + c->i, s, slen) == 0) {
        c->i += slen;
        return 1;
    }
    return 0;
}

static void cursor_skip_ws_and_comments(Cursor* c) {
    if (!c->extended_mode || c->in_class > 0) return;
    while (!cursor_eof(c)) {
        char ch = cursor_peek(c, 0);
        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n') {
            c->i++;
            continue;
        }
        if (ch == '#') {
            while (!cursor_eof(c) && cursor_peek(c, 0) != '\r' && cursor_peek(c, 0) != '\n') {
                c->i++;
            }
            continue;
        }
        break;
    }
}

/* ============================================================================
 * Parser State
 * ============================================================================ */

typedef struct {
    Cursor cur;
    STRlingFlags flags;
    const char* src;
    const char* original;
    int cap_count;
    char** cap_names;
    size_t cap_names_count;
    size_t cap_names_capacity;
    STRlingError* error;
} Parser;

static void parser_init(Parser* p, const char* text);
static void parser_cleanup(Parser* p);
static STRlingASTNode* parser_parse(Parser* p);
static STRlingASTNode* parse_alt(Parser* p);
static STRlingASTNode* parse_seq(Parser* p);
static STRlingASTNode* parse_atom(Parser* p);
static STRlingASTNode* parse_quant_if_any(Parser* p, STRlingASTNode* child);
static STRlingASTNode* parse_group_or_look(Parser* p);
static STRlingASTNode* parse_char_class(Parser* p);
static STRlingASTNode* parse_escape_atom(Parser* p);
static STRlingClassItem* parse_class_item(Parser* p);

/* Helper: duplicate string */
static char* str_dup(const char* s) {
    if (!s) return NULL;
    size_t len = strlen(s) + 1;
    char* r = (char*)malloc(len);
    if (r) memcpy(r, s, len);
    return r;
}

/* Helper: check if name exists in cap_names */
static int has_cap_name(Parser* p, const char* name) {
    for (size_t i = 0; i < p->cap_names_count; i++) {
        if (strcmp(p->cap_names[i], name) == 0) return 1;
    }
    return 0;
}

/* Helper: add capture name */
static void add_cap_name(Parser* p, const char* name) {
    if (p->cap_names_count >= p->cap_names_capacity) {
        size_t new_cap = p->cap_names_capacity == 0 ? 8 : p->cap_names_capacity * 2;
        char** new_names = (char**)realloc(p->cap_names, new_cap * sizeof(char*));
        if (!new_names) return;
        p->cap_names = new_names;
        p->cap_names_capacity = new_cap;
    }
    p->cap_names[p->cap_names_count++] = str_dup(name);
}

/* Allocate and initialize a public STRlingError. */
static STRlingError* strling_error_create(const char* message, int position, const char* hint) {
    STRlingError* e = (STRlingError*)malloc(sizeof(STRlingError));
    if (!e) return NULL;
    e->message = str_dup(message);
    e->position = position;
    e->hint = str_dup(hint);
    return e;
}

/* Set error on parser, generating a hint via the hint engine. */
static void parser_set_error(Parser* p, const char* message, int position) {
    if (p->error) return; /* Keep first error */
    char hint_buf[512];
    strling_get_hint(message, p->src, (size_t)position, hint_buf, sizeof(hint_buf));
    p->error = strling_error_create(message, position, hint_buf);
}

/* Control escape map */
static char control_escape(char ch) {
    switch (ch) {
        case 'n': return '\n';
        case 'r': return '\r';
        case 't': return '\t';
        case 'f': return '\f';
        case 'v': return '\v';
        default: return '\0';
    }
}

static int is_control_escape(char ch) {
    return ch == 'n' || ch == 'r' || ch == 't' || ch == 'f' || ch == 'v';
}

static int is_hex_digit(char c) {
    return (c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f');
}

static int hex_val(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return 0;
}

/* Encode a unicode codepoint as UTF-8 into buf. Returns number of bytes written. */
static int utf8_encode(int cp, char* buf) {
    if (cp < 0x80) {
        buf[0] = (char)cp;
        return 1;
    } else if (cp < 0x800) {
        buf[0] = (char)(0xC0 | (cp >> 6));
        buf[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    } else if (cp < 0x10000) {
        buf[0] = (char)(0xE0 | (cp >> 12));
        buf[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    } else {
        buf[0] = (char)(0xF0 | (cp >> 18));
        buf[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
        buf[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[3] = (char)(0x80 | (cp & 0x3F));
        return 4;
    }
}

/* ============================================================================
 * Directive Parsing
 * ============================================================================ */

static void parse_directives(Parser* p, const char* text) {
    p->flags.ignoreCase = 0;
    p->flags.multiline = 0;
    p->flags.dotAll = 0;
    p->flags.unicode = 0;
    p->flags.extended = 0;

    size_t text_len = strlen(text);
    size_t pos = 0;
    int in_pattern = 0;
    size_t pattern_start = 0;
    int found_directive = 0;

    /* Process line by line */
    const char* line_start = text;
    while (pos <= text_len) {
        /* Find end of line */
        size_t line_end = pos;
        while (line_end < text_len && text[line_end] != '\n') {
            line_end++;
        }

        /* Extract line */
        size_t line_len = line_end - pos;

        /* Trim whitespace */
        size_t trimmed_start = pos;
        while (trimmed_start < line_end && (text[trimmed_start] == ' ' || text[trimmed_start] == '\t')) {
            trimmed_start++;
        }
        size_t trimmed_end = line_end;
        while (trimmed_end > trimmed_start && (text[trimmed_end-1] == ' ' || text[trimmed_end-1] == '\t' || text[trimmed_end-1] == '\r')) {
            trimmed_end--;
        }
        size_t trimmed_len = trimmed_end - trimmed_start;

        if (!in_pattern) {
            /* Skip blank lines and comments */
            if (trimmed_len == 0 || text[trimmed_start] == '#') {
                pos = line_end + 1;
                if (line_end >= text_len) break;
                continue;
            }

            /* Check for directive */
            if (text[trimmed_start] == '%') {
                /* Check for %flags */
                if (trimmed_len >= 6 && strncmp(text + trimmed_start, "%flags", 6) == 0) {
                    found_directive = 1;

                    /* Parse flag letters after %flags */
                    size_t fi = trimmed_start + 6;
                    const char* valid = "imsux";
                    while (fi < line_end) {
                        char c = text[fi];
                        if (c == ' ' || c == '\t' || c == ',' || c == '[' || c == ']') {
                            fi++;
                            continue;
                        }
                        char cl = (char)tolower(c);
                        if (strchr(valid, cl)) {
                            switch (cl) {
                                case 'i': p->flags.ignoreCase = 1; break;
                                case 'm': p->flags.multiline = 1; break;
                                case 's': p->flags.dotAll = 1; break;
                                case 'u': p->flags.unicode = 1; break;
                                case 'x': p->flags.extended = 1; break;
                            }
                            fi++;
                        } else if (isalpha(c)) {
                            /* Invalid flag */
                            char msg[64];
                            snprintf(msg, sizeof(msg), "Invalid flag '%c'", c);
                            char hint_buf[512];
                            strling_get_hint(msg, text, (int)trimmed_start, hint_buf, sizeof(hint_buf));
                            p->error = strling_error_create(msg, (int)trimmed_start, hint_buf);
                            p->src = text + text_len;
                            return;
                        } else {
                            break;
                        }
                    }

                    /* Pattern starts on next line */
                    in_pattern = 1;
                    pattern_start = line_end + 1;
                } else {
                    /* Unknown directive -> malformed */
                    char hint_buf[512];
                    strling_get_hint("Malformed directive", text, (int)trimmed_start, hint_buf, sizeof(hint_buf));
                    p->error = strling_error_create("Malformed directive", (int)trimmed_start, hint_buf);
                    p->src = text + text_len;
                    return;
                }
            } else {
                /* Pattern content starts - but check for %flags within line */
                const char* pct = strstr(text + pos, "%flags");
                if (pct && pct < text + line_end) {
                    char hint_buf[512];
                    strling_get_hint("Directive after pattern", text, (int)(pct - text), hint_buf, sizeof(hint_buf));
                    p->error = strling_error_create("Directive after pattern", (int)(pct - text), hint_buf);
                    p->src = text + text_len;
                    return;
                }
                in_pattern = 1;
                pattern_start = pos;
            }
        } else {
            /* Already in pattern - check for directive after pattern */
            /* Check if line contains %flags */
            const char* pct = strstr(text + pos, "%flags");
            if (pct && pct < text + line_end) {
                char hint_buf[512];
                strling_get_hint("Directive after pattern", text, (int)(pct - text), hint_buf, sizeof(hint_buf));
                p->error = strling_error_create("Directive after pattern", (int)(pct - text), hint_buf);
                p->src = text + text_len;
                return;
            }
            /* Also check for any % directive */
            if (trimmed_len > 0 && text[trimmed_start] == '%') {
                char hint_buf[512];
                strling_get_hint("Directive after pattern", text, (int)trimmed_start, hint_buf, sizeof(hint_buf));
                p->error = strling_error_create("Directive after pattern", (int)trimmed_start, hint_buf);
                p->src = text + text_len;
                return;
            }
        }

        pos = line_end + 1;
        if (line_end >= text_len) break;
    }

    if (!in_pattern) {
        p->src = text + text_len; /* Empty */
    } else {
        p->src = text + pattern_start;
    }
}

/* ============================================================================
 * Parser Implementation
 * ============================================================================ */

static void parser_init(Parser* p, const char* text) {
    memset(p, 0, sizeof(Parser));
    p->original = text;
    parse_directives(p, text);
    if (p->error) return;
    cursor_init(&p->cur, p->src, p->flags.extended);
    p->cap_count = 0;
    p->cap_names = NULL;
    p->cap_names_count = 0;
    p->cap_names_capacity = 0;
}

static void parser_cleanup(Parser* p) {
    for (size_t i = 0; i < p->cap_names_count; i++) {
        free(p->cap_names[i]);
    }
    free(p->cap_names);
}

static STRlingASTNode* parser_parse(Parser* p) {
    if (p->error) return NULL;

    cursor_skip_ws_and_comments(&p->cur);
    if (cursor_eof(&p->cur)) {
        return strling_ast_seq_create(NULL, 0);
    }

    STRlingASTNode* node = parse_alt(p);
    if (p->error) {
        strling_ast_node_free(node);
        return NULL;
    }
    cursor_skip_ws_and_comments(&p->cur);
    if (!cursor_eof(&p->cur)) {
        char ch = cursor_peek(&p->cur, 0);
        if (ch == ')') {
            parser_set_error(p, "Unmatched ')'", (int)p->cur.i);
        } else {
            parser_set_error(p, "Unexpected trailing input", (int)p->cur.i);
        }
        strling_ast_node_free(node);
        return NULL;
    }
    return node;
}

static STRlingASTNode* parse_alt(Parser* p) {
    if (p->error) return NULL;

    cursor_skip_ws_and_comments(&p->cur);
    if (cursor_peek(&p->cur, 0) == '|') {
        parser_set_error(p, "Alternation lacks left-hand side", (int)p->cur.i);
        return NULL;
    }

    STRlingASTNode** branches = NULL;
    size_t nbranches = 0;
    size_t capacity = 0;

    STRlingASTNode* first = parse_seq(p);
    if (p->error || !first) return NULL;

    cursor_skip_ws_and_comments(&p->cur);
    if (cursor_peek(&p->cur, 0) != '|') {
        return first;
    }

    capacity = 4;
    branches = (STRlingASTNode**)malloc(capacity * sizeof(STRlingASTNode*));
    branches[nbranches++] = first;

    while (cursor_peek(&p->cur, 0) == '|') {
        cursor_take(&p->cur);
        cursor_skip_ws_and_comments(&p->cur);

        if (cursor_eof(&p->cur) || cursor_peek(&p->cur, 0) == '|' || cursor_peek(&p->cur, 0) == ')') {
            parser_set_error(p, "Empty alternation", (int)p->cur.i);
            for (size_t i = 0; i < nbranches; i++) strling_ast_node_free(branches[i]);
            free(branches);
            return NULL;
        }

        STRlingASTNode* branch = parse_seq(p);
        if (p->error || !branch) {
            for (size_t i = 0; i < nbranches; i++) strling_ast_node_free(branches[i]);
            free(branches);
            return NULL;
        }

        if (nbranches >= capacity) {
            capacity *= 2;
            branches = (STRlingASTNode**)realloc(branches, capacity * sizeof(STRlingASTNode*));
        }
        branches[nbranches++] = branch;
        cursor_skip_ws_and_comments(&p->cur);
    }

    STRlingASTNode* alt = strling_ast_alt_create(branches, nbranches);
    free(branches);
    return alt;
}

static STRlingASTNode* parse_seq(Parser* p) {
    if (p->error) return NULL;

    STRlingASTNode** parts = NULL;
    size_t nparts = 0;
    size_t capacity = 0;

    while (1) {
        cursor_skip_ws_and_comments(&p->cur);
        char ch = cursor_peek(&p->cur, 0);

        if ((ch == '*' || ch == '+' || ch == '?' || ch == '{') && nparts == 0) {
            if (ch == '{') {
                /* Check brace content to decide error message */
                size_t save = p->cur.i;
                size_t j = p->cur.i + 1;
                char content[256];
                size_t clen = 0;
                while (j < p->cur.len && p->cur.text[j] != '}' && clen < 255) {
                    content[clen++] = p->cur.text[j];
                    j++;
                }
                content[clen] = '\0';

                if (j < p->cur.len && clen > 0) {
                    /* Check if content is numeric quantifier pattern */
                    int is_numeric = 1;
                    int has_comma = 0;
                    for (size_t k = 0; k < clen; k++) {
                        if (content[k] == ',') { has_comma = 1; continue; }
                        if (!isdigit(content[k])) { is_numeric = 0; break; }
                    }
                    if (is_numeric) {
                        char msg[64];
                        snprintf(msg, sizeof(msg), "Invalid quantifier '%c'", ch);
                        parser_set_error(p, msg, (int)p->cur.i);
                    } else {
                        parser_set_error(p, "Brace quantifier: Invalid brace quantifier content", (int)p->cur.i);
                    }
                } else if (j >= p->cur.len) {
                    parser_set_error(p, "Incomplete quantifier", (int)p->cur.i);
                } else {
                    char msg[64];
                    snprintf(msg, sizeof(msg), "Invalid quantifier '%c'", ch);
                    parser_set_error(p, msg, (int)p->cur.i);
                }
            } else {
                char msg[64];
                snprintf(msg, sizeof(msg), "Invalid quantifier '%c'", ch);
                parser_set_error(p, msg, (int)p->cur.i);
            }
            goto cleanup;
        }

        if (ch == '\0' || ch == '|' || ch == ')') break;

        STRlingASTNode* atom = parse_atom(p);
        if (p->error) goto cleanup;
        if (!atom) break;

        atom = parse_quant_if_any(p, atom);
        if (p->error) {
            strling_ast_node_free(atom);
            goto cleanup;
        }

        if (nparts >= capacity) {
            capacity = capacity == 0 ? 4 : capacity * 2;
            parts = (STRlingASTNode**)realloc(parts, capacity * sizeof(STRlingASTNode*));
        }
        parts[nparts++] = atom;
    }

    if (nparts == 0) {
        return strling_ast_seq_create(NULL, 0);
    }
    if (nparts == 1) {
        STRlingASTNode* single = parts[0];
        free(parts);
        return single;
    }

    {
        STRlingASTNode* seq = strling_ast_seq_create(parts, nparts);
        free(parts);
        return seq;
    }

cleanup:
    for (size_t i = 0; i < nparts; i++) strling_ast_node_free(parts[i]);
    free(parts);
    return NULL;
}

static STRlingASTNode* parse_atom(Parser* p) {
    if (p->error) return NULL;

    cursor_skip_ws_and_comments(&p->cur);
    char ch = cursor_peek(&p->cur, 0);

    if (ch == '\0') return NULL;

    if (ch == '.') {
        cursor_take(&p->cur);
        return strling_ast_dot_create();
    }
    if (ch == '^') {
        cursor_take(&p->cur);
        return strling_ast_anchor_create("Start");
    }
    if (ch == '$') {
        cursor_take(&p->cur);
        return strling_ast_anchor_create("End");
    }
    if (ch == '(') {
        return parse_group_or_look(p);
    }
    if (ch == '[') {
        return parse_char_class(p);
    }
    if (ch == '\\') {
        return parse_escape_atom(p);
    }
    if (ch == ')') {
        parser_set_error(p, "Unmatched ')'", (int)p->cur.i);
        return NULL;
    }
    if (ch == '|') {
        return NULL;
    }

    /* Literal character */
    char lit[5] = {0};
    unsigned char uc = (unsigned char)cursor_take(&p->cur);
    /* Handle multi-byte UTF-8 */
    if (uc < 0x80) {
        lit[0] = (char)uc;
    } else if (uc < 0xE0) {
        lit[0] = (char)uc;
        lit[1] = cursor_take(&p->cur);
    } else if (uc < 0xF0) {
        lit[0] = (char)uc;
        lit[1] = cursor_take(&p->cur);
        lit[2] = cursor_take(&p->cur);
    } else {
        lit[0] = (char)uc;
        lit[1] = cursor_take(&p->cur);
        lit[2] = cursor_take(&p->cur);
        lit[3] = cursor_take(&p->cur);
    }
    return strling_ast_lit_create(lit);
}

static STRlingASTNode* parse_quant_if_any(Parser* p, STRlingASTNode* child) {
    if (p->error || !child) return child;

    cursor_skip_ws_and_comments(&p->cur);
    char ch = cursor_peek(&p->cur, 0);

    /* Check for anchor quantification */
    if (child->type == AST_TYPE_ANCHOR && ch != '\0' && (ch == '*' || ch == '+' || ch == '?' || ch == '{')) {
        parser_set_error(p, "Cannot quantify anchor", (int)p->cur.i);
        return child;
    }

    int minv = -1, maxv = -1;
    const char* mode = "Greedy";

    if (ch == '*') {
        minv = 0; maxv = -1;
        cursor_take(&p->cur);
    } else if (ch == '+') {
        minv = 1; maxv = -1;
        cursor_take(&p->cur);
    } else if (ch == '?') {
        minv = 0; maxv = 1;
        cursor_take(&p->cur);
    } else if (ch == '{') {
        size_t start_pos = p->cur.i;
        cursor_take(&p->cur); /* consume '{' */

        /* Read content until } */
        char content[256];
        size_t clen = 0;
        size_t content_start = p->cur.i;
        while (!cursor_eof(&p->cur) && cursor_peek(&p->cur, 0) != '}' && clen < 255) {
            content[clen++] = cursor_take(&p->cur);
        }
        content[clen] = '\0';

        if (cursor_eof(&p->cur)) {
            parser_set_error(p, "Incomplete quantifier", (int)start_pos);
            return child;
        }
        cursor_take(&p->cur); /* consume '}' */

        if (clen == 0) {
            parser_set_error(p, "Brace quantifier: Invalid brace quantifier content", (int)start_pos);
            return child;
        }

        /* Validate numeric format: digits, optional comma, optional digits */
        int valid = 1;
        int comma_pos = -1;
        for (size_t k = 0; k < clen; k++) {
            if (content[k] == ',') {
                if (comma_pos >= 0) { valid = 0; break; }
                comma_pos = (int)k;
            } else if (!isdigit(content[k])) {
                valid = 0;
                break;
            }
        }
        /* Must start with digit */
        if (clen == 0 || !isdigit(content[0])) valid = 0;

        if (!valid) {
            parser_set_error(p, "Brace quantifier: Invalid brace quantifier content", (int)start_pos);
            return child;
        }

        if (comma_pos < 0) {
            minv = atoi(content);
            maxv = minv;
        } else {
            content[comma_pos] = '\0';
            minv = atoi(content);
            if (comma_pos + 1 < (int)clen) {
                maxv = atoi(content + comma_pos + 1);
            } else {
                maxv = -1; /* unbounded */
            }
            content[comma_pos] = ','; /* restore */
        }

        /* Range check */
        if (maxv >= 0 && maxv < minv) {
            parser_set_error(p, "Invalid quantifier range", (int)start_pos);
            return child;
        }
    } else {
        return child;
    }

    /* Check for lazy/possessive mode */
    char nxt = cursor_peek(&p->cur, 0);
    if (nxt == '?') {
        mode = "Lazy";
        cursor_take(&p->cur);
    } else if (nxt == '+') {
        mode = "Possessive";
        cursor_take(&p->cur);
    }

    return strling_ast_quant_create(child, minv, maxv, mode);
}

static STRlingASTNode* parse_group_or_look(Parser* p) {
    size_t start_pos = p->cur.i;
    cursor_take(&p->cur); /* consume '(' */
    cursor_skip_ws_and_comments(&p->cur);

    if (cursor_peek(&p->cur, 0) == '?') {
        cursor_take(&p->cur); /* consume '?' */
        char next = cursor_peek(&p->cur, 0);

        /* Non-capturing group */
        if (next == ':') {
            cursor_take(&p->cur);
            STRlingASTNode* body = parse_alt(p);
            if (p->error) return NULL;
            if (cursor_peek(&p->cur, 0) != ')') {
                parser_set_error(p, "Unterminated group", (int)p->cur.i);
                strling_ast_node_free(body);
                return NULL;
            }
            cursor_take(&p->cur);
            return strling_ast_group_create(0, body, NULL, 0);
        }

        /* Lookahead positive */
        if (next == '=') {
            cursor_take(&p->cur);
            STRlingASTNode* body = parse_alt(p);
            if (p->error) return NULL;
            if (cursor_peek(&p->cur, 0) != ')') {
                parser_set_error(p, "Unterminated lookahead", (int)p->cur.i);
                strling_ast_node_free(body);
                return NULL;
            }
            cursor_take(&p->cur);
            return strling_ast_look_create("Ahead", 0, body);
        }

        /* Lookahead negative */
        if (next == '!') {
            cursor_take(&p->cur);
            STRlingASTNode* body = parse_alt(p);
            if (p->error) return NULL;
            if (cursor_peek(&p->cur, 0) != ')') {
                parser_set_error(p, "Unterminated lookahead", (int)p->cur.i);
                strling_ast_node_free(body);
                return NULL;
            }
            cursor_take(&p->cur);
            return strling_ast_look_create("Ahead", 1, body);
        }

        /* Atomic group */
        if (next == '>') {
            cursor_take(&p->cur);
            STRlingASTNode* body = parse_alt(p);
            if (p->error) return NULL;
            if (cursor_peek(&p->cur, 0) != ')') {
                parser_set_error(p, "Unterminated atomic group", (int)p->cur.i);
                strling_ast_node_free(body);
                return NULL;
            }
            cursor_take(&p->cur);
            return strling_ast_group_create(0, body, NULL, 1);
        }

        if (next == '<') {
            cursor_take(&p->cur);
            char after_angle = cursor_peek(&p->cur, 0);

            /* Lookbehind positive */
            if (after_angle == '=') {
                cursor_take(&p->cur);
                STRlingASTNode* body = parse_alt(p);
                if (p->error) return NULL;
                if (cursor_peek(&p->cur, 0) != ')') {
                    parser_set_error(p, "Unterminated lookbehind", (int)p->cur.i);
                    strling_ast_node_free(body);
                    return NULL;
                }
                cursor_take(&p->cur);
                return strling_ast_look_create("Behind", 0, body);
            }

            /* Lookbehind negative */
            if (after_angle == '!') {
                cursor_take(&p->cur);
                STRlingASTNode* body = parse_alt(p);
                if (p->error) return NULL;
                if (cursor_peek(&p->cur, 0) != ')') {
                    parser_set_error(p, "Unterminated lookbehind", (int)p->cur.i);
                    strling_ast_node_free(body);
                    return NULL;
                }
                cursor_take(&p->cur);
                return strling_ast_look_create("Behind", 1, body);
            }

            /* Named capturing group (?<name>...) */
            {
                char name[256];
                size_t name_len = 0;
                while (cursor_peek(&p->cur, 0) != '>' && cursor_peek(&p->cur, 0) != '\0' && name_len < 255) {
                    name[name_len++] = cursor_take(&p->cur);
                }
                name[name_len] = '\0';

                if (cursor_peek(&p->cur, 0) != '>') {
                    parser_set_error(p, "Unterminated group name", (int)p->cur.i);
                    return NULL;
                }
                cursor_take(&p->cur); /* consume > */

                /* Validate group name */
                if (name_len == 0) {
                    parser_set_error(p, "Invalid group name ''", (int)start_pos);
                    return NULL;
                }
                if (!isalpha(name[0]) && name[0] != '_') {
                    char msg[128];
                    snprintf(msg, sizeof(msg), "Invalid group name '%s'", name);
                    parser_set_error(p, msg, (int)start_pos);
                    return NULL;
                }
                for (size_t k = 1; k < name_len; k++) {
                    if (!isalnum(name[k]) && name[k] != '_') {
                        char msg[128];
                        snprintf(msg, sizeof(msg), "Invalid group name '%s'", name);
                        parser_set_error(p, msg, (int)start_pos);
                        return NULL;
                    }
                }

                if (has_cap_name(p, name)) {
                    char msg[128];
                    snprintf(msg, sizeof(msg), "Duplicate group name '%s'", name);
                    parser_set_error(p, msg, (int)start_pos);
                    return NULL;
                }

                p->cap_count++;
                add_cap_name(p, name);

                STRlingASTNode* body = parse_alt(p);
                if (p->error) return NULL;
                if (cursor_peek(&p->cur, 0) != ')') {
                    parser_set_error(p, "Unterminated group", (int)p->cur.i);
                    strling_ast_node_free(body);
                    return NULL;
                }
                cursor_take(&p->cur);
                return strling_ast_group_create(1, body, name, 0);
            }
        }

        /* Check for inline modifiers like (?i) */
        {
            size_t save = p->cur.i;
            const char* valid_mod = "imsux";
            char modifiers[16];
            size_t mod_len = 0;
            while (mod_len < 15 && cursor_peek(&p->cur, 0) != '\0' && strchr(valid_mod, cursor_peek(&p->cur, 0))) {
                modifiers[mod_len++] = cursor_take(&p->cur);
            }
            modifiers[mod_len] = '\0';
            if (mod_len > 0 && cursor_peek(&p->cur, 0) == ')') {
                char msg[128];
                snprintf(msg, sizeof(msg), "Inline modifiers like (?%s...) are not supported", modifiers);
                parser_set_error(p, msg, (int)start_pos);
                return NULL;
            }
            p->cur.i = save; /* restore */
        }

        {
            char msg[64];
            snprintf(msg, sizeof(msg), "Unknown group modifier: ?%c", next);
            parser_set_error(p, msg, (int)(p->cur.i - 1));
            return NULL;
        }
    }

    /* Regular capturing group */
    p->cap_count++;
    STRlingASTNode* body = parse_alt(p);
    if (p->error) return NULL;
    if (cursor_peek(&p->cur, 0) != ')') {
        parser_set_error(p, "Unterminated group", (int)p->cur.i);
        strling_ast_node_free(body);
        return NULL;
    }
    cursor_take(&p->cur);
    return strling_ast_group_create(1, body, NULL, 0);
}

static STRlingASTNode* parse_char_class(Parser* p) {
    size_t start_pos = p->cur.i;
    cursor_take(&p->cur); /* consume '[' */
    p->cur.in_class++;

    int neg = 0;
    if (cursor_peek(&p->cur, 0) == '^') {
        neg = 1;
        cursor_take(&p->cur);
    }

    /* Empty char class check */
    if (cursor_peek(&p->cur, 0) == ']') {
        p->cur.in_class--;
        parser_set_error(p, "Unterminated character class", (int)p->cur.i);
        return NULL;
    }

    STRlingClassItem** items = NULL;
    size_t nitems = 0;
    size_t capacity = 0;

    while (!cursor_eof(&p->cur) && cursor_peek(&p->cur, 0) != ']') {
        STRlingClassItem* item = parse_class_item(p);
        if (p->error) goto cleanup;
        if (!item) continue;

        /* Check for range */
        if (item->item_type == CLASS_ITEM_CHAR && cursor_peek(&p->cur, 0) == '-' && cursor_peek(&p->cur, 1) != ']') {
            size_t dash_pos = p->cur.i;
            cursor_take(&p->cur); /* consume '-' */

            if (cursor_eof(&p->cur) || cursor_peek(&p->cur, 0) == ']') {
                /* Trailing dash - add as literals */
                if (nitems >= capacity) {
                    capacity = capacity == 0 ? 4 : capacity * 2;
                    items = (STRlingClassItem**)realloc(items, capacity * sizeof(STRlingClassItem*));
                }
                items[nitems++] = item;
                if (nitems >= capacity) {
                    capacity *= 2;
                    items = (STRlingClassItem**)realloc(items, capacity * sizeof(STRlingClassItem*));
                }
                items[nitems++] = strling_class_literal_create("-");
                continue;
            }

            STRlingClassItem* to_item = parse_class_item(p);
            if (p->error) {
                strling_class_item_free(item);
                goto cleanup;
            }

            if (to_item && to_item->item_type == CLASS_ITEM_CHAR) {
                /* Check range reversal */
                if (strcmp(to_item->v.literal.ch, item->v.literal.ch) < 0) {
                    p->cur.in_class--;
                    strling_class_item_free(item);
                    strling_class_item_free(to_item);
                    parser_set_error(p, "Invalid character range", (int)start_pos);
                    goto cleanup;
                }
                STRlingClassItem* range = strling_class_range_create(item->v.literal.ch, to_item->v.literal.ch);
                strling_class_item_free(item);
                strling_class_item_free(to_item);
                item = range;
            } else {
                /* Not a valid range endpoint */
                if (nitems >= capacity) {
                    capacity = capacity == 0 ? 4 : capacity * 2;
                    items = (STRlingClassItem**)realloc(items, capacity * sizeof(STRlingClassItem*));
                }
                items[nitems++] = item;
                if (nitems >= capacity) {
                    capacity *= 2;
                    items = (STRlingClassItem**)realloc(items, capacity * sizeof(STRlingClassItem*));
                }
                items[nitems++] = strling_class_literal_create("-");
                item = to_item;
            }
        }

        if (item) {
            if (nitems >= capacity) {
                capacity = capacity == 0 ? 4 : capacity * 2;
                items = (STRlingClassItem**)realloc(items, capacity * sizeof(STRlingClassItem*));
            }
            items[nitems++] = item;
        }
    }

    if (cursor_eof(&p->cur)) {
        p->cur.in_class--;
        parser_set_error(p, "Unterminated character class", (int)p->cur.i);
        goto cleanup;
    }

    cursor_take(&p->cur); /* consume ']' */
    p->cur.in_class--;

    {
        STRlingASTNode* cc = strling_ast_charclass_create(neg, items, nitems);
        free(items);
        return cc;
    }

cleanup:
    for (size_t i = 0; i < nitems; i++) strling_class_item_free(items[i]);
    free(items);
    return NULL;
}

static STRlingClassItem* parse_class_item(Parser* p) {
    char ch = cursor_peek(&p->cur, 0);

    if (ch == '\\') {
        size_t start_pos = p->cur.i;
        cursor_take(&p->cur); /* consume backslash */

        if (cursor_eof(&p->cur)) {
            parser_set_error(p, "Unexpected end of pattern after '\\'", (int)start_pos);
            return NULL;
        }

        char nxt = cursor_peek(&p->cur, 0);

        /* Shorthand classes */
        if (nxt == 'd' || nxt == 'D' || nxt == 'w' || nxt == 'W' || nxt == 's' || nxt == 'S') {
            cursor_take(&p->cur);
            char type[2] = { nxt, '\0' };
            return strling_class_escape_create(type, NULL);
        }

        /* Unicode property */
        if (nxt == 'p' || nxt == 'P') {
            char tp = cursor_take(&p->cur);
            if (cursor_peek(&p->cur, 0) != '{') {
                p->cur.in_class--;
                parser_set_error(p, "Expected { after \\p/\\P", (int)start_pos);
                return NULL;
            }
            cursor_take(&p->cur); /* consume { */
            char prop[256];
            size_t prop_len = 0;
            while (!cursor_eof(&p->cur) && cursor_peek(&p->cur, 0) != '}' && prop_len < 255) {
                prop[prop_len++] = cursor_take(&p->cur);
            }
            prop[prop_len] = '\0';
            if (cursor_eof(&p->cur)) {
                p->cur.in_class--;
                parser_set_error(p, "Unterminated \\p{...}", (int)start_pos);
                return NULL;
            }
            cursor_take(&p->cur); /* consume } */
            char type[2] = { tp, '\0' };
            return strling_class_escape_create(type, prop);
        }

        /* Control escapes */
        if (is_control_escape(nxt)) {
            cursor_take(&p->cur);
            char lit[2] = { control_escape(nxt), '\0' };
            return strling_class_literal_create(lit);
        }

        /* Hex escape \x */
        if (nxt == 'x') {
            cursor_take(&p->cur);
            if (cursor_peek(&p->cur, 0) == '{') {
                cursor_take(&p->cur);
                int val = 0;
                while (is_hex_digit(cursor_peek(&p->cur, 0))) {
                    val = val * 16 + hex_val(cursor_take(&p->cur));
                }
                if (cursor_peek(&p->cur, 0) != '}') {
                    p->cur.in_class--;
                    parser_set_error(p, "Unterminated \\x{...}", (int)start_pos);
                    return NULL;
                }
                cursor_take(&p->cur);
                char buf[5] = {0};
                utf8_encode(val, buf);
                return strling_class_literal_create(buf);
            } else {
                char h1 = cursor_peek(&p->cur, 0);
                char h2 = cursor_peek(&p->cur, 1);
                if (!is_hex_digit(h1) || !is_hex_digit(h2)) {
                    p->cur.in_class--;
                    parser_set_error(p, "Invalid \\xHH escape", (int)start_pos);
                    return NULL;
                }
                cursor_take(&p->cur);
                cursor_take(&p->cur);
                int val = hex_val(h1) * 16 + hex_val(h2);
                char buf[5] = {0};
                utf8_encode(val, buf);
                return strling_class_literal_create(buf);
            }
        }

        /* Unicode escape \u */
        if (nxt == 'u') {
            cursor_take(&p->cur);
            if (cursor_peek(&p->cur, 0) == '{') {
                cursor_take(&p->cur);
                int val = 0;
                while (is_hex_digit(cursor_peek(&p->cur, 0))) {
                    val = val * 16 + hex_val(cursor_take(&p->cur));
                }
                if (cursor_peek(&p->cur, 0) != '}') {
                    p->cur.in_class--;
                    parser_set_error(p, "Unterminated \\u{...}", (int)start_pos);
                    return NULL;
                }
                cursor_take(&p->cur);
                char buf[5] = {0};
                utf8_encode(val, buf);
                return strling_class_literal_create(buf);
            } else {
                for (int i = 0; i < 4; i++) {
                    if (!is_hex_digit(cursor_peek(&p->cur, 0))) {
                        p->cur.in_class--;
                        parser_set_error(p, "Invalid \\uHHHH escape", (int)start_pos);
                        return NULL;
                    }
                    cursor_take(&p->cur);
                }
                /* We already consumed 4 hex digits, reparse */
                int val = 0;
                for (int i = 4; i > 0; i--) {
                    val = val * 16 + hex_val(p->cur.text[p->cur.i - i]);
                }
                char buf[5] = {0};
                utf8_encode(val, buf);
                return strling_class_literal_create(buf);
            }
        }

        /* Forbidden octal */
        if (nxt == '0') {
            p->cur.in_class--;
            parser_set_error(p, "Forbidden octal escape", (int)start_pos);
            return NULL;
        }

        /* Unknown escape - alphanumeric is error */
        if (isalnum(nxt)) {
            p->cur.in_class--;
            char msg[64];
            snprintf(msg, sizeof(msg), "Unknown escape sequence \\%c", nxt);
            parser_set_error(p, msg, (int)start_pos);
            return NULL;
        }

        /* Identity escape */
        char esc_ch = cursor_take(&p->cur);
        char lit[2] = { esc_ch, '\0' };
        return strling_class_literal_create(lit);
    }

    /* Regular character */
    cursor_take(&p->cur);
    char lit[5] = {0};
    unsigned char uc = (unsigned char)ch;
    if (uc < 0x80) {
        lit[0] = ch;
    } else if (uc < 0xE0) {
        lit[0] = ch;
        lit[1] = cursor_take(&p->cur);
    } else if (uc < 0xF0) {
        lit[0] = ch;
        lit[1] = cursor_take(&p->cur);
        lit[2] = cursor_take(&p->cur);
    } else {
        lit[0] = ch;
        lit[1] = cursor_take(&p->cur);
        lit[2] = cursor_take(&p->cur);
        lit[3] = cursor_take(&p->cur);
    }
    return strling_class_literal_create(lit);
}

static STRlingASTNode* parse_escape_atom(Parser* p) {
    size_t start_pos = p->cur.i;
    cursor_take(&p->cur); /* consume backslash */

    if (cursor_eof(&p->cur)) {
        parser_set_error(p, "Unexpected end of pattern after '\\'", (int)start_pos);
        return NULL;
    }

    char nxt = cursor_peek(&p->cur, 0);

    /* Anchors */
    if (nxt == 'b') { cursor_take(&p->cur); return strling_ast_anchor_create("WordBoundary"); }
    if (nxt == 'B') { cursor_take(&p->cur); return strling_ast_anchor_create("NotWordBoundary"); }
    if (nxt == 'A') { cursor_take(&p->cur); return strling_ast_anchor_create("AbsoluteStart"); }
    if (nxt == 'Z') { cursor_take(&p->cur); return strling_ast_anchor_create("EndBeforeFinalNewline"); }

    /* Shorthand classes */
    if (nxt == 'd' || nxt == 'D' || nxt == 'w' || nxt == 'W' || nxt == 's' || nxt == 'S') {
        cursor_take(&p->cur);
        char type[2] = { nxt, '\0' };
        STRlingClassItem* items[1];
        items[0] = strling_class_escape_create(type, NULL);
        return strling_ast_charclass_create(0, items, 1);
    }

    /* Unicode property */
    if (nxt == 'p' || nxt == 'P') {
        char tp = cursor_take(&p->cur);
        if (cursor_peek(&p->cur, 0) != '{') {
            parser_set_error(p, "Expected { after \\p/\\P", (int)start_pos);
            return NULL;
        }
        cursor_take(&p->cur); /* consume { */
        char prop[256];
        size_t prop_len = 0;
        while (!cursor_eof(&p->cur) && cursor_peek(&p->cur, 0) != '}' && prop_len < 255) {
            prop[prop_len++] = cursor_take(&p->cur);
        }
        prop[prop_len] = '\0';
        if (cursor_eof(&p->cur)) {
            parser_set_error(p, "Unterminated \\p{...}", (int)start_pos);
            return NULL;
        }
        cursor_take(&p->cur); /* consume } */
        char type[2] = { tp, '\0' };
        STRlingClassItem* items[1];
        items[0] = strling_class_escape_create(type, prop);
        return strling_ast_charclass_create(0, items, 1);
    }

    /* Control escapes */
    if (is_control_escape(nxt)) {
        cursor_take(&p->cur);
        char lit[2] = { control_escape(nxt), '\0' };
        return strling_ast_lit_create(lit);
    }

    /* Named backref \k<name> */
    if (nxt == 'k') {
        cursor_take(&p->cur);
        if (cursor_peek(&p->cur, 0) != '<') {
            parser_set_error(p, "Expected '<' after \\k", (int)start_pos);
            return NULL;
        }
        cursor_take(&p->cur); /* consume < */
        char name[256];
        size_t name_len = 0;
        while (!cursor_eof(&p->cur) && cursor_peek(&p->cur, 0) != '>' && name_len < 255) {
            name[name_len++] = cursor_take(&p->cur);
        }
        name[name_len] = '\0';
        if (cursor_eof(&p->cur)) {
            parser_set_error(p, "Unterminated named backref", (int)start_pos);
            return NULL;
        }
        cursor_take(&p->cur); /* consume > */
        if (!has_cap_name(p, name)) {
            char msg[128];
            snprintf(msg, sizeof(msg), "Backreference to undefined group <%s>", name);
            parser_set_error(p, msg, (int)start_pos);
            return NULL;
        }
        return strling_ast_backref_create(-1, name);
    }

    /* Numeric backreference */
    if (nxt >= '1' && nxt <= '9') {
        int num = 0;
        while (cursor_peek(&p->cur, 0) >= '0' && cursor_peek(&p->cur, 0) <= '9') {
            num = num * 10 + (cursor_peek(&p->cur, 0) - '0');
            cursor_take(&p->cur);
        }
        if (num > p->cap_count) {
            char msg[128];
            snprintf(msg, sizeof(msg), "Backreference to undefined group \\%d", num);
            parser_set_error(p, msg, (int)start_pos);
            return NULL;
        }
        return strling_ast_backref_create(num, NULL);
    }

    /* Forbidden octal */
    if (nxt == '0') {
        parser_set_error(p, "Forbidden octal escape", (int)start_pos);
        return NULL;
    }

    /* Hex escape \xHH or \x{...} */
    if (nxt == 'x') {
        cursor_take(&p->cur);
        if (cursor_peek(&p->cur, 0) == '{') {
            cursor_take(&p->cur);
            int val = 0;
            while (is_hex_digit(cursor_peek(&p->cur, 0))) {
                val = val * 16 + hex_val(cursor_take(&p->cur));
            }
            if (cursor_peek(&p->cur, 0) != '}') {
                parser_set_error(p, "Unterminated \\x{...}", (int)start_pos);
                return NULL;
            }
            cursor_take(&p->cur);
            char buf[5] = {0};
            utf8_encode(val, buf);
            return strling_ast_lit_create(buf);
        } else {
            char h1 = cursor_peek(&p->cur, 0);
            char h2 = cursor_peek(&p->cur, 1);
            if (!is_hex_digit(h1) || !is_hex_digit(h2)) {
                parser_set_error(p, "Invalid \\xHH escape", (int)start_pos);
                return NULL;
            }
            cursor_take(&p->cur);
            cursor_take(&p->cur);
            int val = hex_val(h1) * 16 + hex_val(h2);
            char buf[5] = {0};
            utf8_encode(val, buf);
            return strling_ast_lit_create(buf);
        }
    }

    /* Unicode escape \uHHHH or \u{...} */
    if (nxt == 'u') {
        cursor_take(&p->cur);
        if (cursor_peek(&p->cur, 0) == '{') {
            cursor_take(&p->cur);
            int val = 0;
            while (is_hex_digit(cursor_peek(&p->cur, 0))) {
                val = val * 16 + hex_val(cursor_take(&p->cur));
            }
            if (cursor_peek(&p->cur, 0) != '}') {
                parser_set_error(p, "Unterminated \\u{...}", (int)start_pos);
                return NULL;
            }
            cursor_take(&p->cur);
            char buf[5] = {0};
            utf8_encode(val, buf);
            return strling_ast_lit_create(buf);
        } else {
            int val = 0;
            for (int i = 0; i < 4; i++) {
                char c = cursor_peek(&p->cur, 0);
                if (!is_hex_digit(c)) {
                    parser_set_error(p, "Invalid \\uHHHH escape", (int)start_pos);
                    return NULL;
                }
                val = val * 16 + hex_val(c);
                cursor_take(&p->cur);
            }
            char buf[5] = {0};
            utf8_encode(val, buf);
            return strling_ast_lit_create(buf);
        }
    }

    /* Unicode escape \UHHHHHHHH */
    if (nxt == 'U') {
        cursor_take(&p->cur);
        int val = 0;
        for (int i = 0; i < 8; i++) {
            char c = cursor_peek(&p->cur, 0);
            if (!is_hex_digit(c)) {
                parser_set_error(p, "Invalid \\UHHHHHHHH escape", (int)start_pos);
                return NULL;
            }
            val = val * 16 + hex_val(c);
            cursor_take(&p->cur);
        }
        char buf[5] = {0};
        utf8_encode(val, buf);
        return strling_ast_lit_create(buf);
    }

    /* Meta escape - identity */
    if (nxt == '^' || nxt == '$' || nxt == '.' || nxt == '*' || nxt == '+' ||
        nxt == '?' || nxt == '(' || nxt == ')' || nxt == '[' || nxt == ']' ||
        nxt == '{' || nxt == '}' || nxt == '|' || nxt == '\\' || nxt == '/') {
        cursor_take(&p->cur);
        char lit[2] = { nxt, '\0' };
        return strling_ast_lit_create(lit);
    }

    /* Unknown escape - alphanumeric is error */
    if (isalnum(nxt)) {
        char msg[64];
        snprintf(msg, sizeof(msg), "Unknown escape sequence \\%c", nxt);
        parser_set_error(p, msg, (int)start_pos);
        return NULL;
    }

    /* Non-alphanumeric identity escape */
    {
        char ch = cursor_take(&p->cur);
        char lit[2] = { ch, '\0' };
        return strling_ast_lit_create(lit);
    }
}

/* ============================================================================
 * Public API
 * ============================================================================ */

STRlingParseResult* strling_parse(const char* src) {
    STRlingParseResult* result = (STRlingParseResult*)malloc(sizeof(STRlingParseResult));
    if (!result) return NULL;

    Parser p;
    parser_init(&p, src);

    result->flags = p.flags;
    if (p.error) {
        result->root = NULL;
        result->error = p.error;
    } else {
        result->root = parser_parse(&p);
        result->error = p.error;
    }

    parser_cleanup(&p);

    return result;
}

void strling_parse_result_free(STRlingParseResult* result) {
    if (!result) return;
    strling_ast_node_free(result->root);
    strling_error_free(result->error);
    free(result);
}
