/*
 * STRling AST Node definitions (ported from Python `nodes.py`)
 *
 * This file defines the AST node structs and constructors/destructors.
 * Memory ownership follows the rule: constructors allocate, callers must
 * free nodes with `strling_ast_node_free` which recursively frees children.
 */
#ifndef STRLING_NODES_H
#define STRLING_NODES_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Flags container (regex modifiers) */
typedef struct STRlingFlags {
    bool ignoreCase;
    bool multiline;
    bool dotAll;
    bool unicode;
    bool extended;
} STRlingFlags;

STRlingFlags* strling_flags_create(void);
void strling_flags_free(STRlingFlags* f);

/* Forward declare AST node */
typedef struct STRlingASTNode STRlingASTNode;

/* Node types */
typedef enum {
    AST_TYPE_ALT,
    AST_TYPE_SEQ,
    AST_TYPE_LIT,
    AST_TYPE_DOT,
    AST_TYPE_ANCHOR,
    AST_TYPE_CHARCLASS,
    AST_TYPE_QUANT,
    AST_TYPE_GROUP,
    AST_TYPE_BACKREF,
    AST_TYPE_LOOK
} STRlingASTNodeType;

/* ClassItem types for character classes */
typedef enum {
    CLASS_ITEM_RANGE,
    CLASS_ITEM_CHAR,
    CLASS_ITEM_ESCAPE
} STRlingClassItemType;

/* Class item variants */
typedef struct {
    char* from_ch;
    char* to_ch;
} STRlingClassRange;

typedef struct {
    char* ch;
} STRlingClassLiteral;

typedef struct {
    char* type; /* e.g., "d", "w", "p" */
    char* property; /* optional */
} STRlingClassEscape;

typedef struct STRlingClassItem {
    STRlingClassItemType item_type;
    union {
        STRlingClassRange range;
        STRlingClassLiteral literal;
        STRlingClassEscape esc;
    } v;
} STRlingClassItem;

/* Concrete node definitions */
typedef struct {
    STRlingASTNode** branches;
    size_t nbranches;
} STRlingAlt;

typedef struct {
    STRlingASTNode** parts;
    size_t nparts;
} STRlingSeq;

typedef struct {
    char* value;
} STRlingLit;

typedef struct {
    char* at; /* e.g., "Start", "End" */
} STRlingAnchor;

typedef struct {
    bool negated;
    STRlingClassItem** items;
    size_t nitems;
} STRlingCharClass;

typedef struct {
    STRlingASTNode* child;
    int min;
    int max; /* -1 for infinity */
    char* mode; /* "Greedy" | "Lazy" | "Possessive" */
} STRlingQuant;

typedef struct {
    bool capturing;
    STRlingASTNode* body;
    char* name; /* optional */
    bool atomic;
} STRlingGroup;

typedef struct {
    int byIndex; /* -1 if not set */
    char* byName; /* optional */
} STRlingBackref;

typedef struct {
    char* dir; /* "Ahead" | "Behind" */
    bool neg;
    STRlingASTNode* body;
} STRlingLook;

/* Tagged union AST node */
struct STRlingASTNode {
    STRlingASTNodeType type;
    union {
        STRlingAlt alt;
        STRlingSeq seq;
        STRlingLit lit;
        /* Dot has no payload */
        STRlingAnchor anchor;
        STRlingCharClass charclass;
        STRlingQuant quant;
        STRlingGroup group;
        STRlingBackref backref;
        STRlingLook look;
    } u;
};

/* Constructors */
STRlingASTNode* strling_ast_lit_create(const char* value);
STRlingASTNode* strling_ast_dot_create(void);
STRlingASTNode* strling_ast_alt_create(STRlingASTNode** branches, size_t nbranches);
STRlingASTNode* strling_ast_seq_create(STRlingASTNode** parts, size_t nparts);
STRlingASTNode* strling_ast_anchor_create(const char* at);

/* Class items */
STRlingClassItem* strling_class_range_create(const char* from_ch, const char* to_ch);
STRlingClassItem* strling_class_literal_create(const char* ch);
STRlingClassItem* strling_class_escape_create(const char* type, const char* property);
STRlingASTNode* strling_ast_charclass_create(bool negated, STRlingClassItem** items, size_t nitems);

/* Quant, Group, Backref, Look */
STRlingASTNode* strling_ast_quant_create(STRlingASTNode* child, int min, int max, const char* mode);
STRlingASTNode* strling_ast_group_create(bool capturing, STRlingASTNode* body, const char* name, bool atomic);
STRlingASTNode* strling_ast_backref_create(int byIndex, const char* byName);
STRlingASTNode* strling_ast_look_create(const char* dir, bool neg, STRlingASTNode* body);

/* Memory management */
void strling_ast_node_free(STRlingASTNode* node);
void strling_class_item_free(STRlingClassItem* item);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_NODES_H */
