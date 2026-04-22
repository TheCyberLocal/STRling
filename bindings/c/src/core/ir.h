/*
 * STRling IR Node definitions (ported from Python `ir.py`)
 *
 * These mirror the AST node types but are intended for target-agnostic
 * intermediate representation. Includes constructors and free functions.
 */
#ifndef STRLING_IR_H
#define STRLING_IR_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct STRlingIROp STRlingIROp;

typedef enum {
    IR_TYPE_ALT,
    IR_TYPE_SEQ,
    IR_TYPE_LIT,
    IR_TYPE_DOT,
    IR_TYPE_ANCHOR,
    IR_TYPE_CHARCLASS,
    IR_TYPE_QUANT,
    IR_TYPE_GROUP,
    IR_TYPE_BACKREF,
    IR_TYPE_LOOK
} STRlingIROpType;

/* Class item */
typedef enum { IR_CLASS_RANGE, IR_CLASS_CHAR, IR_CLASS_ESCAPE } STRlingIRClassItemType;

typedef struct {
    char* from_ch;
    char* to_ch;
} STRlingIRClassRange;

typedef struct { char* ch; } STRlingIRClassLiteral;
typedef struct { char* type; char* property; } STRlingIRClassEscape;

typedef struct STRlingIRClassItem {
    STRlingIRClassItemType type;
    union {
        STRlingIRClassRange range;
        STRlingIRClassLiteral literal;
        STRlingIRClassEscape esc;
    } v;
} STRlingIRClassItem;

/* Concrete IR nodes */
typedef struct {
    STRlingIROp** branches;
    size_t nbranches;
} STRlingIRAlt;

typedef struct {
    STRlingIROp** parts;
    size_t nparts;
} STRlingIRSeq;

typedef struct { char* value; } STRlingIRLit;
typedef struct { char* at; } STRlingIRAnchor;

typedef struct {
    bool negated;
    STRlingIRClassItem** items;
    size_t nitems;
} STRlingIRCharClass;

typedef struct {
    STRlingIROp* child;
    int min;
    int max;
    char* mode;
} STRlingIRQuant;

typedef struct {
    bool capturing;
    STRlingIROp* body;
    char* name;
    bool atomic;
} STRlingIRGroup;

typedef struct { int byIndex; char* byName; } STRlingIRBackref;
typedef struct { char* dir; bool neg; STRlingIROp* body; } STRlingIRLook;

struct STRlingIROp {
    STRlingIROpType type;
    union {
        STRlingIRAlt alt;
        STRlingIRSeq seq;
        STRlingIRLit lit;
        STRlingIRAnchor anchor;
        STRlingIRCharClass charclass;
        STRlingIRQuant quant;
        STRlingIRGroup group;
        STRlingIRBackref backref;
        STRlingIRLook look;
    } u;
};

/* Constructors / destructors */
STRlingIROp* strling_ir_lit_create(const char* value);
STRlingIROp* strling_ir_dot_create(void);
STRlingIROp* strling_ir_alt_create(STRlingIROp** branches, size_t nbranches);
STRlingIROp* strling_ir_seq_create(STRlingIROp** parts, size_t nparts);
STRlingIROp* strling_ir_anchor_create(const char* at);

STRlingIRClassItem* strling_ir_class_range_create(const char* from_ch, const char* to_ch);
STRlingIRClassItem* strling_ir_class_literal_create(const char* ch);
STRlingIRClassItem* strling_ir_class_escape_create(const char* type, const char* property);
STRlingIROp* strling_ir_charclass_create(bool negated, STRlingIRClassItem** items, size_t nitems);

STRlingIROp* strling_ir_quant_create(STRlingIROp* child, int min, int max, const char* mode);
STRlingIROp* strling_ir_group_create(bool capturing, STRlingIROp* body, const char* name, bool atomic);
STRlingIROp* strling_ir_backref_create(int byIndex, const char* byName);
STRlingIROp* strling_ir_look_create(const char* dir, bool neg, STRlingIROp* body);

void strling_ir_node_free(STRlingIROp* node);
void strling_ir_class_item_free(STRlingIRClassItem* item);

/* ===================================================================
 * Emitter Safety Context (port of TypeScript SSOT guards)
 *
 * Tracks AST traversal depth, lookbehind state, and accumulated
 * non-fatal warnings during PCRE2 emission. The context is threaded
 * through `compile_node_to_pcre2()` so each guard (depth, VLB, ReDoS)
 * can inspect global emission state without relying on globals.
 * Mirrors `EmitContext` in
 * `bindings/typescript/src/STRling/emitters/pcre2.ts`.
 * ===================================================================
 */

/* Default cap on AST nesting depth before emission aborts to protect
 * the host stack (matches the TypeScript reference implementation). */
#define STRLING_DEFAULT_MAX_DEPTH 250

/* Stable warning code emitted when a pattern exhibits a ReDoS shape
 * (nested unbounded quantifiers such as `(a+)+`). */
#define STRLING_WARNING_CODE_REDOS "REDOS_RISK"

typedef struct {
    int depth;          /* current traversal depth (incremented per node) */
    int max_depth;      /* abort threshold; <=0 selects the default */
    bool in_lookbehind; /* set while emitting nodes under a lookbehind */
    char** warnings;    /* heap-owned "CODE: message" strings */
    size_t nwarnings;
    size_t cap_warnings;
} strling_emit_context_t;

/* Initialise a context. `max_depth <= 0` selects STRLING_DEFAULT_MAX_DEPTH.
 * The caller owns the storage; warnings are allocated on first push. */
void strling_emit_context_init(strling_emit_context_t* ctx, int max_depth);

/* Release any heap memory owned by the context (warnings array + entries). */
void strling_emit_context_free(strling_emit_context_t* ctx);

/* Returns true if a warning with the given code has already been pushed
 * (used to dedupe ReDoS warnings during a single emission). */
bool strling_emit_context_has_warning(const strling_emit_context_t* ctx,
                                      const char* code);

/* Append a "CODE: message" warning. No-op on allocation failure. */
void strling_emit_context_push_warning(strling_emit_context_t* ctx,
                                       const char* code,
                                       const char* message);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_IR_H */
