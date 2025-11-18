/*
 * STRling IR Node implementations (ported from Python `ir.py`)
 *
 * Implements simple constructors and destructors for the IR nodes. The
 * implementation intentionally mirrors the AST implementation but uses the
 * IR types and names defined in `ir.h`.
 */

#include "ir.h"
#include <stdlib.h>
#include <string.h>

static char* _str_clone(const char* s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char* r = (char*)malloc(n);
    if (!r) return NULL;
    memcpy(r, s, n);
    return r;
}

/* Class item creators */
STRlingIRClassItem* strling_ir_class_range_create(const char* from_ch, const char* to_ch) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_RANGE;
    it->v.range.from_ch = _str_clone(from_ch);
    it->v.range.to_ch = _str_clone(to_ch);
    return it;
}

STRlingIRClassItem* strling_ir_class_literal_create(const char* ch) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_CHAR;
    it->v.literal.ch = _str_clone(ch);
    return it;
}

STRlingIRClassItem* strling_ir_class_escape_create(const char* type, const char* property) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_ESCAPE;
    it->v.esc.type = _str_clone(type);
    it->v.esc.property = _str_clone(property);
    return it;
}

/* IR node constructors */
STRlingIROp* strling_ir_lit_create(const char* value) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_LIT;
    n->u.lit.value = _str_clone(value);
    return n;
}

STRlingIROp* strling_ir_dot_create(void) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_DOT;
    return n;
}

STRlingIROp* strling_ir_alt_create(STRlingIROp** branches, size_t nbranches) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_ALT;
    n->u.alt.nbranches = nbranches;
    if (nbranches) {
        n->u.alt.branches = (STRlingIROp**)malloc(sizeof(STRlingIROp*) * nbranches);
        if (!n->u.alt.branches) { free(n); return NULL; }
        for (size_t i = 0; i < nbranches; ++i) n->u.alt.branches[i] = branches[i];
    } else {
        n->u.alt.branches = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_seq_create(STRlingIROp** parts, size_t nparts) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_SEQ;
    n->u.seq.nparts = nparts;
    if (nparts) {
        n->u.seq.parts = (STRlingIROp**)malloc(sizeof(STRlingIROp*) * nparts);
        if (!n->u.seq.parts) { free(n); return NULL; }
        for (size_t i = 0; i < nparts; ++i) n->u.seq.parts[i] = parts[i];
    } else {
        n->u.seq.parts = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_anchor_create(const char* at) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_ANCHOR;
    n->u.anchor.at = _str_clone(at);
    return n;
}

STRlingIROp* strling_ir_charclass_create(bool negated, STRlingIRClassItem** items, size_t nitems) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_CHARCLASS;
    n->u.charclass.negated = negated;
    n->u.charclass.nitems = nitems;
    if (nitems) {
        n->u.charclass.items = (STRlingIRClassItem**)malloc(sizeof(STRlingIRClassItem*) * nitems);
        if (!n->u.charclass.items) { free(n); return NULL; }
        for (size_t i = 0; i < nitems; ++i) n->u.charclass.items[i] = items[i];
    } else {
        n->u.charclass.items = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_quant_create(STRlingIROp* child, int min, int max, const char* mode) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_QUANT;
    n->u.quant.child = child;
    n->u.quant.min = min;
    n->u.quant.max = max;
    n->u.quant.mode = _str_clone(mode);
    return n;
}

STRlingIROp* strling_ir_group_create(bool capturing, STRlingIROp* body, const char* name, bool atomic) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_GROUP;
    n->u.group.capturing = capturing;
    n->u.group.body = body;
    n->u.group.name = _str_clone(name);
    n->u.group.atomic = atomic;
    return n;
}

STRlingIROp* strling_ir_backref_create(int byIndex, const char* byName) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_BACKREF;
    n->u.backref.byIndex = byIndex;
    n->u.backref.byName = _str_clone(byName);
    return n;
}

STRlingIROp* strling_ir_look_create(const char* dir, bool neg, STRlingIROp* body) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_LOOK;
    n->u.look.dir = _str_clone(dir);
    n->u.look.neg = neg;
    n->u.look.body = body;
    return n;
}

/* Free helpers */
void strling_ir_class_item_free(STRlingIRClassItem* item) {
    if (!item) return;
    switch (item->type) {
        case IR_CLASS_RANGE:
            free(item->v.range.from_ch);
            free(item->v.range.to_ch);
            break;
        case IR_CLASS_CHAR:
            free(item->v.literal.ch);
            break;
        case IR_CLASS_ESCAPE:
            free(item->v.esc.type);
            free(item->v.esc.property);
            break;
    }
    free(item);
}

void strling_ir_node_free(STRlingIROp* node) {
    if (!node) return;
    switch (node->type) {
        case IR_TYPE_ALT:
            if (node->u.alt.branches) {
                for (size_t i = 0; i < node->u.alt.nbranches; ++i)
                    strling_ir_node_free(node->u.alt.branches[i]);
                free(node->u.alt.branches);
            }
            break;
        case IR_TYPE_SEQ:
            if (node->u.seq.parts) {
                for (size_t i = 0; i < node->u.seq.nparts; ++i)
                    strling_ir_node_free(node->u.seq.parts[i]);
                free(node->u.seq.parts);
            }
            break;
        case IR_TYPE_LIT:
            free(node->u.lit.value);
            break;
        case IR_TYPE_DOT:
            break;
        case IR_TYPE_ANCHOR:
            free(node->u.anchor.at);
            break;
        case IR_TYPE_CHARCLASS:
            if (node->u.charclass.items) {
                for (size_t i = 0; i < node->u.charclass.nitems; ++i)
                    strling_ir_class_item_free(node->u.charclass.items[i]);
                free(node->u.charclass.items);
            }
            break;
        case IR_TYPE_QUANT:
            strling_ir_node_free(node->u.quant.child);
            free(node->u.quant.mode);
            break;
        case IR_TYPE_GROUP:
            strling_ir_node_free(node->u.group.body);
            free(node->u.group.name);
            break;
        case IR_TYPE_BACKREF:
            free(node->u.backref.byName);
            break;
        case IR_TYPE_LOOK:
            free(node->u.look.dir);
            strling_ir_node_free(node->u.look.body);
            break;
    }
    free(node);
}
/* Port of bindings/python/src/STRling/core/ir.py to C (structures only) */
#include "ir.h"
#include <stdlib.h>
#include <string.h>

static char* dupstr(const char* s) {
    if (!s) return NULL;
    size_t n = strlen(s) + 1;
    char* p = (char*)malloc(n);
    if (p) memcpy(p, s, n);
    return p;
}

STRlingIROp* strling_ir_lit_create(const char* value) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_LIT;
    n->u.lit.value = dupstr(value);
    return n;
}

STRlingIROp* strling_ir_dot_create(void) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_DOT;
    return n;
}

STRlingIROp* strling_ir_alt_create(STRlingIROp** branches, size_t nbranches) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_ALT;
    n->u.alt.nbranches = nbranches;
    if (nbranches > 0) {
        n->u.alt.branches = (STRlingIROp**)malloc(sizeof(STRlingIROp*) * nbranches);
        if (!n->u.alt.branches) { free(n); return NULL; }
        for (size_t i = 0; i < nbranches; ++i) n->u.alt.branches[i] = branches[i];
    } else {
        n->u.alt.branches = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_seq_create(STRlingIROp** parts, size_t nparts) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_SEQ;
    n->u.seq.nparts = nparts;
    if (nparts > 0) {
        n->u.seq.parts = (STRlingIROp**)malloc(sizeof(STRlingIROp*) * nparts);
        if (!n->u.seq.parts) { free(n); return NULL; }
        for (size_t i = 0; i < nparts; ++i) n->u.seq.parts[i] = parts[i];
    } else {
        n->u.seq.parts = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_anchor_create(const char* at) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_ANCHOR;
    n->u.anchor.at = dupstr(at);
    return n;
}

STRlingIRClassItem* strling_ir_class_range_create(const char* from_ch, const char* to_ch) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_RANGE;
    it->v.range.from_ch = dupstr(from_ch);
    it->v.range.to_ch = dupstr(to_ch);
    return it;
}

STRlingIRClassItem* strling_ir_class_literal_create(const char* ch) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_CHAR;
    it->v.literal.ch = dupstr(ch);
    return it;
}

STRlingIRClassItem* strling_ir_class_escape_create(const char* type, const char* property) {
    STRlingIRClassItem* it = (STRlingIRClassItem*)malloc(sizeof(STRlingIRClassItem));
    if (!it) return NULL;
    it->type = IR_CLASS_ESCAPE;
    it->v.esc.type = dupstr(type);
    it->v.esc.property = dupstr(property);
    return it;
}

STRlingIROp* strling_ir_charclass_create(bool negated, STRlingIRClassItem** items, size_t nitems) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_CHARCLASS;
    n->u.charclass.negated = negated;
    n->u.charclass.nitems = nitems;
    if (nitems > 0) {
        n->u.charclass.items = (STRlingIRClassItem**)malloc(sizeof(STRlingIRClassItem*) * nitems);
        if (!n->u.charclass.items) { free(n); return NULL; }
        for (size_t i = 0; i < nitems; ++i) n->u.charclass.items[i] = items[i];
    } else {
        n->u.charclass.items = NULL;
    }
    return n;
}

STRlingIROp* strling_ir_quant_create(STRlingIROp* child, int min, int max, const char* mode) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_QUANT;
    n->u.quant.child = child;
    n->u.quant.min = min;
    n->u.quant.max = max;
    n->u.quant.mode = dupstr(mode);
    return n;
}

STRlingIROp* strling_ir_group_create(bool capturing, STRlingIROp* body, const char* name, bool atomic) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_GROUP;
    n->u.group.capturing = capturing;
    n->u.group.body = body;
    n->u.group.name = dupstr(name);
    n->u.group.atomic = atomic;
    return n;
}

STRlingIROp* strling_ir_backref_create(int byIndex, const char* byName) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_BACKREF;
    n->u.backref.byIndex = byIndex;
    n->u.backref.byName = dupstr(byName);
    return n;
}

STRlingIROp* strling_ir_look_create(const char* dir, bool neg, STRlingIROp* body) {
    STRlingIROp* n = (STRlingIROp*)malloc(sizeof(STRlingIROp));
    if (!n) return NULL;
    n->type = IR_TYPE_LOOK;
    n->u.look.dir = dupstr(dir);
    n->u.look.neg = neg;
    n->u.look.body = body;
    return n;
}

void strling_ir_class_item_free(STRlingIRClassItem* item) {
    if (!item) return;
    switch (item->type) {
        case IR_CLASS_RANGE:
            free(item->v.range.from_ch);
            free(item->v.range.to_ch);
            break;
        case IR_CLASS_CHAR:
            free(item->v.literal.ch);
            break;
        case IR_CLASS_ESCAPE:
            free(item->v.esc.type);
            free(item->v.esc.property);
            break;
    }
    free(item);
}

void strling_ir_node_free(STRlingIROp* node) {
    if (!node) return;
    switch (node->type) {
        case IR_TYPE_LIT:
            free(node->u.lit.value);
            break;
        case IR_TYPE_DOT:
            break;
        case IR_TYPE_ALT:
            if (node->u.alt.branches) {
                for (size_t i = 0; i < node->u.alt.nbranches; ++i) strling_ir_node_free(node->u.alt.branches[i]);
                free(node->u.alt.branches);
            }
            break;
        case IR_TYPE_SEQ:
            if (node->u.seq.parts) {
                for (size_t i = 0; i < node->u.seq.nparts; ++i) strling_ir_node_free(node->u.seq.parts[i]);
                free(node->u.seq.parts);
            }
            break;
        case IR_TYPE_ANCHOR:
            free(node->u.anchor.at);
            break;
        case IR_TYPE_CHARCLASS:
            if (node->u.charclass.items) {
                for (size_t i = 0; i < node->u.charclass.nitems; ++i) strling_ir_class_item_free(node->u.charclass.items[i]);
                free(node->u.charclass.items);
            }
            break;
        case IR_TYPE_QUANT:
            if (node->u.quant.child) strling_ir_node_free(node->u.quant.child);
            free(node->u.quant.mode);
            break;
        case IR_TYPE_GROUP:
            if (node->u.group.body) strling_ir_node_free(node->u.group.body);
            free(node->u.group.name);
            break;
        case IR_TYPE_BACKREF:
            free(node->u.backref.byName);
            break;
        case IR_TYPE_LOOK:
            free(node->u.look.dir);
            if (node->u.look.body) strling_ir_node_free(node->u.look.body);
            break;
    }
    free(node);
}
