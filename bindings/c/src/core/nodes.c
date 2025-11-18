/*
 * STRling AST Node implementations (ported from Python `nodes.py`)
 *
 * Implements constructors and destructors for AST nodes and class items.
 * All allocation is performed with malloc/strdup-equivalent and callers
 * are expected to use the corresponding free functions.
 */

#include "nodes.h"
#include <stdlib.h>
#include <string.h>

/* Helper: clone a C string (NULL-safe) */
static char* _str_clone(const char* s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char* r = (char*)malloc(n);
    if (!r) return NULL;
    memcpy(r, s, n);
    return r;
}

/* Flags */
STRlingFlags* strling_flags_create(void) {
    STRlingFlags* f = (STRlingFlags*)malloc(sizeof(STRlingFlags));
    if (!f) return NULL;
    f->ignoreCase = false;
    f->multiline = false;
    f->dotAll = false;
    f->unicode = false;
    f->extended = false;
    return f;
}

void strling_flags_free(STRlingFlags* f) {
    if (!f) return;
    free(f);
}

/* Class items */
STRlingClassItem* strling_class_range_create(const char* from_ch, const char* to_ch) {
    STRlingClassItem* it = (STRlingClassItem*)malloc(sizeof(STRlingClassItem));
    if (!it) return NULL;
    it->item_type = CLASS_ITEM_RANGE;
    it->v.range.from_ch = _str_clone(from_ch);
    it->v.range.to_ch = _str_clone(to_ch);
    return it;
}

STRlingClassItem* strling_class_literal_create(const char* ch) {
    STRlingClassItem* it = (STRlingClassItem*)malloc(sizeof(STRlingClassItem));
    if (!it) return NULL;
    it->item_type = CLASS_ITEM_CHAR;
    it->v.literal.ch = _str_clone(ch);
    return it;
}

STRlingClassItem* strling_class_escape_create(const char* type, const char* property) {
    STRlingClassItem* it = (STRlingClassItem*)malloc(sizeof(STRlingClassItem));
    if (!it) return NULL;
    it->item_type = CLASS_ITEM_ESCAPE;
    it->v.esc.type = _str_clone(type);
    it->v.esc.property = _str_clone(property);
    return it;
}

/* AST node constructors */
STRlingASTNode* strling_ast_lit_create(const char* value) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_LIT;
    n->u.lit.value = _str_clone(value);
    return n;
}

STRlingASTNode* strling_ast_dot_create(void) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_DOT;
    return n;
}

STRlingASTNode* strling_ast_alt_create(STRlingASTNode** branches, size_t nbranches) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_ALT;
    n->u.alt.nbranches = nbranches;
    if (nbranches) {
        n->u.alt.branches = (STRlingASTNode**)malloc(sizeof(STRlingASTNode*) * nbranches);
        if (!n->u.alt.branches) { free(n); return NULL; }
        for (size_t i = 0; i < nbranches; ++i) n->u.alt.branches[i] = branches[i];
    } else {
        n->u.alt.branches = NULL;
    }
    return n;
}

STRlingASTNode* strling_ast_seq_create(STRlingASTNode** parts, size_t nparts) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_SEQ;
    n->u.seq.nparts = nparts;
    if (nparts) {
        n->u.seq.parts = (STRlingASTNode**)malloc(sizeof(STRlingASTNode*) * nparts);
        if (!n->u.seq.parts) { free(n); return NULL; }
        for (size_t i = 0; i < nparts; ++i) n->u.seq.parts[i] = parts[i];
    } else {
        n->u.seq.parts = NULL;
    }
    return n;
}

STRlingASTNode* strling_ast_anchor_create(const char* at) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_ANCHOR;
    n->u.anchor.at = _str_clone(at);
    return n;
}

STRlingASTNode* strling_ast_charclass_create(bool negated, STRlingClassItem** items, size_t nitems) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_CHARCLASS;
    n->u.charclass.negated = negated;
    n->u.charclass.nitems = nitems;
    if (nitems) {
        n->u.charclass.items = (STRlingClassItem**)malloc(sizeof(STRlingClassItem*) * nitems);
        if (!n->u.charclass.items) { free(n); return NULL; }
        for (size_t i = 0; i < nitems; ++i) n->u.charclass.items[i] = items[i];
    } else {
        n->u.charclass.items = NULL;
    }
    return n;
}

STRlingASTNode* strling_ast_quant_create(STRlingASTNode* child, int min, int max, const char* mode) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_QUANT;
    n->u.quant.child = child;
    n->u.quant.min = min;
    n->u.quant.max = max;
    n->u.quant.mode = _str_clone(mode);
    return n;
}

STRlingASTNode* strling_ast_group_create(bool capturing, STRlingASTNode* body, const char* name, bool atomic) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_GROUP;
    n->u.group.capturing = capturing;
    n->u.group.body = body;
    n->u.group.name = _str_clone(name);
    n->u.group.atomic = atomic;
    return n;
}

STRlingASTNode* strling_ast_backref_create(int byIndex, const char* byName) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_BACKREF;
    n->u.backref.byIndex = byIndex;
    n->u.backref.byName = _str_clone(byName);
    return n;
}

STRlingASTNode* strling_ast_look_create(const char* dir, bool neg, STRlingASTNode* body) {
    STRlingASTNode* n = (STRlingASTNode*)malloc(sizeof(STRlingASTNode));
    if (!n) return NULL;
    n->type = AST_TYPE_LOOK;
    n->u.look.dir = _str_clone(dir);
    n->u.look.neg = neg;
    n->u.look.body = body;
    return n;
}

/* Free helpers */
void strling_class_item_free(STRlingClassItem* item) {
    if (!item) return;
    switch (item->item_type) {
        case CLASS_ITEM_RANGE:
            free(item->v.range.from_ch);
            free(item->v.range.to_ch);
            break;
        case CLASS_ITEM_CHAR:
            free(item->v.literal.ch);
            break;
        case CLASS_ITEM_ESCAPE:
            free(item->v.esc.type);
            free(item->v.esc.property);
            break;
    }
    free(item);
}

void strling_ast_node_free(STRlingASTNode* node) {
    if (!node) return;
    switch (node->type) {
        case AST_TYPE_ALT:
            if (node->u.alt.branches) {
                for (size_t i = 0; i < node->u.alt.nbranches; ++i)
                    strling_ast_node_free(node->u.alt.branches[i]);
                free(node->u.alt.branches);
            }
            break;
        case AST_TYPE_SEQ:
            if (node->u.seq.parts) {
                for (size_t i = 0; i < node->u.seq.nparts; ++i)
                    strling_ast_node_free(node->u.seq.parts[i]);
                free(node->u.seq.parts);
            }
            break;
        case AST_TYPE_LIT:
            free(node->u.lit.value);
            break;
        case AST_TYPE_DOT:
            /* no payload */
            break;
        case AST_TYPE_ANCHOR:
            free(node->u.anchor.at);
            break;
        case AST_TYPE_CHARCLASS:
            if (node->u.charclass.items) {
                for (size_t i = 0; i < node->u.charclass.nitems; ++i)
                    strling_class_item_free(node->u.charclass.items[i]);
                free(node->u.charclass.items);
            }
            break;
        case AST_TYPE_QUANT:
            strling_ast_node_free(node->u.quant.child);
            free(node->u.quant.mode);
            break;
        case AST_TYPE_GROUP:
            strling_ast_node_free(node->u.group.body);
            free(node->u.group.name);
            break;
        case AST_TYPE_BACKREF:
            free(node->u.backref.byName);
            break;
        case AST_TYPE_LOOK:
            free(node->u.look.dir);
            strling_ast_node_free(node->u.look.body);
            break;
    }
    free(node);
}
