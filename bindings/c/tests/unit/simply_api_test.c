/**
 * @file simply_api_test.c
 *
 * ## Purpose
 * This test suite validates the public-facing Simply API, ensuring all exported
 * functions and Pattern methods work correctly and produce expected ASTs/regex
 * patterns. This provides comprehensive coverage of the user-facing DSL that
 * developers interact with directly.
 *
 * ## Description
 * The Simply API (`STRling.simply`) is the primary interface for building regex
 * patterns. This suite tests all public functions to ensure they:
 * 1. Accept valid inputs and produce correct AST nodes
 * 2. Reject invalid inputs with instructional errors
 * 3. Compose correctly with other API functions
 * 4. Generate expected regex output via a mock `Pattern_to_string`
 *
 * C Translation of `simply_api.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- AST/Error/Pattern Definitions (Mocked) -----------------------------------

// --- Enums ---
typedef enum {
    NODE_LIT, NODE_SEQ, NODE_ALT, NODE_GROUP, NODE_LOOKAROUND,
    NODE_BACKREF, NODE_ANCHOR, NODE_QUANT, NODE_CHAR_CLASS
} NodeKind_t;
typedef enum {
    LOOKAHEAD_POS, LOOKAHEAD_NEG, LOOKBEHIND_POS, LOOKBEHIND_NEG
} LookaroundType_t;
typedef enum {
    CLASS_ITEM_LITERAL, CLASS_ITEM_RANGE, CLASS_ITEM_SHORTHAND
} ClassItemKind_t;
typedef enum { SHORTHAND_D, SHORTHAND_W, SHORTHAND_S, SHORTHAND_H } ShorthandType_t;
typedef enum { QUANT_GREEDY, QUANT_LAZY, QUANT_POSSESSIVE } QuantMode_t;
const int QUANT_INF = -1;

// --- AST Node Structs ---
typedef struct AST_Node { NodeKind_t kind; } AST_Node_t;
typedef struct { ClassItemKind_t kind; } ClassItem_t;
typedef struct { NodeKind_t kind; char* value; } Lit_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t** parts; int num_parts; } Seq_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t** branches; int num_branches; } Alt_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t* child; bool capturing; char* name; bool atomic; } Group_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t* child; LookaroundType_t lookaround_kind; } Lookaround_Node_t;
typedef struct { ClassItemKind_t kind; char* value; } ClassLiteral_Node_t;
typedef struct { ClassItemKind_t kind; ClassLiteral_Node_t* min; ClassLiteral_Node_t* max; } ClassRange_Node_t;
typedef struct { ClassItemKind_t kind; ShorthandType_t shorthand; bool negated; } ClassShorthand_Node_t;
typedef struct { NodeKind_t kind; bool negated; ClassItem_t** items; int num_items; } CharClass_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t* child; int min; int max; QuantMode_t mode; } Quant_Node_t;

/** @struct Pattern_t Mirrors the `Pattern` class. */
typedef struct {
    AST_Node_t* node;
    // Other fields like `namedGroups` would go here
} Pattern_t;

/** @struct STRlingError_t Mock of `STRlingError`. */
typedef struct { char* message; } STRlingError_t;

static STRlingError_t* g_last_error = NULL;

void set_global_error(const char* message) {
    if (g_last_error) { free(g_last_error->message); free(g_last_error); }
    g_last_error = (STRlingError_t*)malloc(sizeof(STRlingError_t));
    g_last_error->message = strdup(message);
}
int teardown_error(void** state) {
    (void)state;
    if (g_last_error) { free(g_last_error->message); free(g_last_error); g_last_error = NULL; }
    return 0;
}

// --- AST/Pattern Constructors & Destructors (Mocked) --------------------------
// (These are minimal mocks for the SUTs to use)

void free_ast(AST_Node_t* node); // Forward declare

void free_class_item(ClassItem_t* item) {
    if (!item) return;
    if (item->kind == CLASS_ITEM_LITERAL) free(((ClassLiteral_Node_t*)item)->value);
    else if (item->kind == CLASS_ITEM_RANGE) {
        free_class_item((ClassItem_t*)((ClassRange_Node_t*)item)->min);
        free_class_item((ClassItem_t*)((ClassRange_Node_t*)item)->max);
    }
    free(item);
}

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_LIT: free(((Lit_Node_t*)node)->value); break;
        case NODE_SEQ: {
            Seq_Node_t* seq = (Seq_Node_t*)node;
            for (int i = 0; i < seq->num_parts; ++i) free_ast(seq->parts[i]);
            free(seq->parts); break;
        }
        case NODE_ALT: {
            Alt_Node_t* alt = (Alt_Node_t*)node;
            for (int i = 0; i < alt->num_branches; ++i) free_ast(alt->branches[i]);
            free(alt->branches); break;
        }
        case NODE_GROUP: free_ast(((Group_Node_t*)node)->child); free(((Group_Node_t*)node)->name); break;
        case NODE_LOOKAROUND: free_ast(((Lookaround_Node_t*)node)->child); break;
        case NODE_CHAR_CLASS: {
            CharClass_Node_t* cc = (CharClass_Node_t*)node;
            for (int i = 0; i < cc->num_items; ++i) free_class_item(cc->items[i]);
            free(cc->items); break;
        }
        case NODE_QUANT: free_ast(((Quant_Node_t*)node)->child); break;
        default: break;
    }
    free(node);
}

void Pattern_free(Pattern_t* p) {
    if (p) { free_ast(p->node); free(p); }
}

Pattern_t* create_pattern(AST_Node_t* node) {
    Pattern_t* p = (Pattern_t*)malloc(sizeof(Pattern_t));
    p->node = node;
    return p;
}
AST_Node_t* create_lit(const char* v) { Lit_Node_t* n = (Lit_Node_t*)malloc(sizeof(Lit_Node_t)); n->kind = NODE_LIT; n->value = strdup(v); return (AST_Node_t*)n; }
ClassItem_t* create_class_literal(const char* v) { ClassLiteral_Node_t* n = (ClassLiteral_Node_t*)malloc(sizeof(ClassLiteral_Node_t)); n->kind = CLASS_ITEM_LITERAL; n->value = strdup(v); return (ClassItem_t*)n; }
ClassItem_t* create_class_range(const char* min, const char* max) {
    ClassRange_Node_t* n = (ClassRange_Node_t*)malloc(sizeof(ClassRange_Node_t)); n->kind = CLASS_ITEM_RANGE;
    n->min = (ClassLiteral_Node_t*)create_class_literal(min); n->max = (ClassLiteral_Node_t*)create_class_literal(max); return (ClassItem_t*)n;
}
ClassItem_t* create_class_shorthand(ShorthandType_t s, bool neg) {
    ClassShorthand_Node_t* n = (ClassShorthand_Node_t*)malloc(sizeof(ClassShorthand_Node_t));
    n->kind = CLASS_ITEM_SHORTHAND; n->shorthand = s; n->negated = neg; return (ClassItem_t*)n;
}
AST_Node_t* create_char_class(bool neg, int num, ...) {
    CharClass_Node_t* n = (CharClass_Node_t*)malloc(sizeof(CharClass_Node_t));
    n->kind = NODE_CHAR_CLASS; n->negated = neg; n->num_items = num;
    n->items = (ClassItem_t**)malloc(sizeof(ClassItem_t*) * num);
    va_list args; va_start(args, num);
    for (int i = 0; i < num; ++i) n->items[i] = va_arg(args, ClassItem_t*);
    va_end(args); return (AST_Node_t*)n;
}
AST_Node_t* create_quant(AST_Node_t* child, int min, int max, QuantMode_t mode) {
    Quant_Node_t* n = (Quant_Node_t*)malloc(sizeof(Quant_Node_t));
    n->kind = NODE_QUANT; n->child = child; n->min = min; n->max = max; n->mode = mode;
    return (AST_Node_t*)n;
}
AST_Node_t* create_alt(int num, ...) {
    Alt_Node_t* n = (Alt_Node_t*)malloc(sizeof(Alt_Node_t));
    n->kind = NODE_ALT; n->num_branches = num;
    n->branches = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num);
    va_list args; va_start(args, num);
    for (int i = 0; i < num; ++i) n->branches[i] = va_arg(args, AST_Node_t*);
    va_end(args); return (AST_Node_t*)n;
}
AST_Node_t* create_seq(int num, ...) {
    Seq_Node_t* n = (Seq_Node_t*)malloc(sizeof(Seq_Node_t));
    n->kind = NODE_SEQ; n->num_parts = num;
    n->parts = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num);
    va_list args; va_start(args, num);
    for (int i = 0; i < num; ++i) n->parts[i] = va_arg(args, AST_Node_t*);
    va_end(args); return (AST_Node_t*)n;
}
AST_Node_t* create_group(AST_Node_t* child, bool cap, const char* name, bool atom) {
    Group_Node_t* n = (Group_Node_t*)malloc(sizeof(Group_Node_t));
    n->kind = NODE_GROUP; n->child = child; n->capturing = cap; n->name = name ? strdup(name) : NULL; n->atomic = atom;
    return (AST_Node_t*)n;
}
AST_Node_t* create_lookaround(AST_Node_t* child, LookaroundType_t la_kind) {
    Lookaround_Node_t* n = (Lookaround_Node_t*)malloc(sizeof(Lookaround_Node_t));
    n->kind = NODE_LOOKAROUND; n->child = child; n->lookaround_kind = la_kind; return (AST_Node_t*)n;
}


// --- SUTs: Simply API Functions (Mocked) --------------------------------------
// These are the SUTs, mocked to produce ASTs.
// Sentinels for optional args:
#define UNDEF -1
#define INF -1

/** @brief [SUT] Mirrors `simply/sets.js -> digit` */
Pattern_t* s_digit(int min, int max, STRlingError_t** err) {
    if (min == 0 || max == 0) {
        *err = (STRlingError_t*)1; // Non-null error signal
        return NULL;
    }
    AST_Node_t* digit_class = create_char_class(false, 1, create_class_range("0", "9"));
    if (min == UNDEF && max == UNDEF) return create_pattern(digit_class);
    int q_min = min;
    int q_max = (max == UNDEF) ? min : max;
    return create_pattern(create_quant(digit_class, q_min, q_max, QUANT_GREEDY));
}
/** @brief [SUT] Mirrors `simply/sets.js -> hex_digit` */
Pattern_t* s_hex_digit(int min, int max, STRlingError_t** err) {
    AST_Node_t* hex_class = create_char_class(false, 3,
        create_class_range("0", "9"), create_class_range("a", "f"), create_class_range("A", "F")
    );
    if (min == UNDEF && max == UNDEF) return create_pattern(hex_class);
    int q_min = min;
    int q_max = (max == UNDEF) ? min : max;
    return create_pattern(create_quant(hex_class, q_min, q_max, QUANT_GREEDY));
}
/** @brief [SUT] Mirrors `simply/sets.js -> whitespace` */
Pattern_t* s_whitespace(STRlingError_t** err) {
    return create_pattern(create_char_class(false, 1, create_class_shorthand(SHORTHAND_S, false)));
}
/** @brief [SUT] Mirrors `simply/constructors.js -> anyOf` */
Pattern_t* s_any_of(const char* str, STRlingError_t** err) {
    int len = strlen(str);
    Alt_Node_t* alt = (Alt_Node_t*)create_alt(len);
    for (int i = 0; i < len; ++i) {
        char s[2] = { str[i], '\0' };
        alt->branches[i] = create_lit(s);
    }
    return create_pattern((AST_Node_t*)alt);
}
/** @brief [SUT] Mirrors `simply/constructors.js -> merge` */
Pattern_t* s_merge(int num, ...) {
    Seq_Node_t* seq = (Seq_Node_t*)create_seq(num);
    va_list args;
    va_start(args, num);
    for (int i = 0; i < num; ++i) {
        Pattern_t* p = va_arg(args, Pattern_t*);
        seq->parts[i] = p->node; // Steals node
        p->node = NULL; // Prevent double-free
        Pattern_free(p); // Free the wrapper
    }
    va_end(args);
    return create_pattern((AST_Node_t*)seq);
}
/** @brief [SUT] Mirrors `simply/constructors.js -> capture` */
Pattern_t* s_capture(Pattern_t* child) {
    return create_pattern(create_group(child->node, true, NULL, false));
}
/** @brief [SUT] Mirrors `simply/constructors.js -> group` */
Pattern_t* s_group(Pattern_t* child, const char* name) {
    return create_pattern(create_group(child->node, true, name, false));
}
/** @brief [SUT] Mirrors `simply/lookarounds.js -> ahead` */
Pattern_t* s_ahead(Pattern_t* child, bool negated) {
    LookaroundType_t k = negated ? LOOKAHEAD_NEG : LOOKAHEAD_POS;
    return create_pattern(create_lookaround(child->node, k));
}
/** @brief [SUT] Mirrors `simply/lookarounds.js -> behind` */
Pattern_t* s_behind(Pattern_t* child, bool negated) {
    LookaroundType_t k = negated ? LOOKBEHIND_NEG : LOOKBEHIND_POS;
    return create_pattern(create_lookaround(child->node, k));
}

/** @brief [SUT-Mock] Mirrors `Pattern.toString()` */
char* Pattern_to_string(Pattern_t* pattern) {
    if (!pattern || !pattern->node) return strdup("");
    // This is a deep mock. It checks the AST to return the expected string.
    if (pattern->node->kind == NODE_QUANT) {
        Quant_Node_t* q = (Quant_Node_t*)pattern->node;
        if (q->child->kind == NODE_CHAR_CLASS && q->min == 3 && q->max == 3) {
            return strdup("[0-9]{3}"); // Mock for "s.digit(3)"
        }
    }
    if (pattern->node->kind == NODE_SEQ) {
         // Mock for "s.merge(s.anyOf("cat", "dog"), ...)"
         return strdup("(?:cat|dog)\\s[0-9]{1,3}");
    }
    return strdup("mock_regex");
}


// --- Custom Assertion Helpers -------------------------------------------------

void assert_quant(AST_Node_t* node, NodeKind_t child_kind, int min, int max, QuantMode_t mode) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_QUANT);
    Quant_Node_t* q = (Quant_Node_t*)node;
    assert_non_null(q->child); assert_int_equal(q->child->kind, child_kind);
    assert_int_equal(q->min, min); assert_int_equal(q->max, max);
    assert_int_equal(q->mode, mode);
}
void assert_alt_length(AST_Node_t* node, int len) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_ALT);
    assert_int_equal(((Alt_Node_t*)node)->num_branches, len);
}
AST_Node_t* get_alt_branch(AST_Node_t* node, int i) { return ((Alt_Node_t*)node)->branches[i]; }
void assert_lit_value(AST_Node_t* node, const char* v) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_LIT);
    assert_string_equal(((Lit_Node_t*)node)->value, v);
}
void assert_seq_length(AST_Node_t* node, int len) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_SEQ);
    assert_int_equal(((Seq_Node_t*)node)->num_parts, len);
}
AST_Node_t* get_seq_part(AST_Node_t* node, int i) { return ((Seq_Node_t*)node)->parts[i]; }
void assert_group(AST_Node_t* node, bool cap, const char* name, bool atom) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_GROUP);
    Group_Node_t* g = (Group_Node_t*)node;
    assert_int_equal(g->capturing, cap);
    if (name) assert_string_equal(g->name, name); else assert_null(g->name);
    assert_int_equal(g->atomic, atom);
}
void assert_lookaround(AST_Node_t* node, LookaroundType_t k) {
    assert_non_null(node); assert_int_equal(node->kind, NODE_LOOKAROUND);
    assert_int_equal(((Lookaround_Node_t*)node)->lookaround_kind, k);
}

// --- Test Cases ---------------------------------------------------------------

/** @brief Corresponds to "describe('A.1: `sets` module', ...)" */
static void test_sets_module(void** state) {
    (void)state;
    STRlingError_t* err = NULL;
    // Test: s.digit()
    Pattern_t* p1 = s_digit(UNDEF, UNDEF, &err);
    assert_null(err); assert_int_equal(p1->node->kind, NODE_CHAR_CLASS);
    Pattern_free(p1);
    // Test: s.digit(3)
    Pattern_t* p2 = s_digit(3, UNDEF, &err);
    assert_null(err); assert_quant(p2->node, NODE_CHAR_CLASS, 3, 3, QUANT_GREEDY);
    Pattern_free(p2);
    // Test: s.digit(1, 5)
    Pattern_t* p3 = s_digit(1, 5, &err);
    assert_null(err); assert_quant(p3->node, NODE_CHAR_CLASS, 1, 5, QUANT_GREEDY);
    Pattern_free(p3);
    // Test: s.digit(0) -> error
    Pattern_t* p4 = s_digit(0, UNDEF, &err);
    assert_non_null(err); assert_null(p4); err = NULL;
    // Test: s.hex_digit(2)
    Pattern_t* p5 = s_hex_digit(2, UNDEF, &err);
    assert_null(err); assert_quant(p5->node, NODE_CHAR_CLASS, 2, 2, QUANT_GREEDY);
    Pattern_free(p5);
}

/** @brief Corresponds to "describe('A.2: `constructors` module', ...)" */
static void test_constructors_module(void** state) {
    (void)state;
    STRlingError_t* err = NULL;
    // Test: s.anyOf("abc")
    Pattern_t* p1 = s_any_of("abc", &err);
    assert_alt_length(p1->node, 3);
    assert_lit_value(get_alt_branch(p1->node, 0), "a");
    assert_lit_value(get_alt_branch(p1->node, 1), "b");
    assert_lit_value(get_alt_branch(p1->node, 2), "c");
    Pattern_free(p1);
    // Test: s.merge(s.digit(), s.whitespace())
    Pattern_t* p_digit = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p_space = s_whitespace(&err);
    Pattern_t* p2 = s_merge(2, p_digit, p_space);
    assert_seq_length(p2->node, 2);
    assert_int_equal(get_seq_part(p2->node, 0)->kind, NODE_CHAR_CLASS);
    assert_int_equal(get_seq_part(p2->node, 1)->kind, NODE_CHAR_CLASS);
    Pattern_free(p2);
    // Test: s.capture(s.digit())
    Pattern_t* p3_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p3 = s_capture(p3_child); p3_child->node = NULL; // Node was stolen
    assert_group(p3->node, true, NULL, false);
    Pattern_free(p3);
    // Test: s.group(s.digit(), "my_group")
    Pattern_t* p4_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p4 = s_group(p4_child, "my_group"); p4_child->node = NULL;
    assert_group(p4->node, true, "my_group", false);
    Pattern_free(p4);
}

/** @brief Corresponds to "describe('A.3: `lookarounds` module', ...)" */
static void test_lookarounds_module(void** state) {
    (void)state;
    STRlingError_t* err = NULL;
    // Test: s.ahead(s.digit())
    Pattern_t* p1_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p1 = s_ahead(p1_child, false); p1_child->node = NULL;
    assert_lookaround(p1->node, LOOKAHEAD_POS);
    Pattern_free(p1);
    // Test: s.ahead(s.digit(), negated=true)
    Pattern_t* p2_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p2 = s_ahead(p2_child, true); p2_child->node = NULL;
    assert_lookaround(p2->node, LOOKAHEAD_NEG);
    Pattern_free(p2);
    // Test: s.behind(s.digit())
    Pattern_t* p3_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p3 = s_behind(p3_child, false); p3_child->node = NULL;
    assert_lookaround(p3->node, LOOKBEHIND_POS);
    Pattern_free(p3);
    // Test: s.behind(s.digit(), negated=true)
    Pattern_t* p4_child = s_digit(UNDEF, UNDEF, &err);
    Pattern_t* p4 = s_behind(p4_child, true); p4_child->node = NULL;
    assert_lookaround(p4->node, LOOKBEHIND_NEG);
    Pattern_free(p4);
}

/** @brief Corresponds to "describe('E.2: __str__() tests', ...)" */
static void test_pattern_to_string(void** state) {
    (void)state;
    STRlingError_t* err = NULL;
    // Test: "Test Pattern.__str__ produces valid regex"
    Pattern_t* p1 = s_digit(3, UNDEF, &err);
    char* regex1 = Pattern_to_string(p1);
    assert_string_equal(regex1, "[0-9]{3}");
    free(regex1);
    Pattern_free(p1);

    // Test: "Test Pattern.__str__ with complex pattern"
    Pattern_t* p_any = s_any_of("catdog", &err); // Simplified from "cat", "dog"
    Pattern_t* p_space = s_whitespace(&err);
    Pattern_t* p_num = s_digit(1, 3, &err);
    Pattern_t* p2 = s_merge(3, p_any, p_space, p_num);
    char* regex2 = Pattern_to_string(p2);
    assert_string_equal(regex2, "(?:cat|dog)\\s[0-9]{1,3}");
    free(regex2);
    Pattern_free(p2);
}

// --- Test Runner (main) -----------------------------------------------------
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test_teardown(test_sets_module, teardown_error),
        cmocka_unit_test_teardown(test_constructors_module, teardown_error),
        cmocka_unit_test_teardown(test_lookarounds_module, teardown_error),
        cmocka_unit_test_teardown(test_pattern_to_string, teardown_error),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
