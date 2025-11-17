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

#ifdef __cplusplus
}
#endif

#endif /* STRLING_IR_H */
