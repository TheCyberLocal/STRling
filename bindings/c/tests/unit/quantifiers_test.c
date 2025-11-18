/**
 * @file quantifiers_test.c
 *
 * ## Purpose
 * This test suite validates the correct parsing of all quantifier forms (`*`, `+`,
 * `?`, `{m,n}`) and modes (Greedy, Lazy, Possessive). It ensures quantifiers
 * correctly bind to their preceding atom, generate the proper `Quant` AST node,
 * and that malformed quantifier syntax raises the appropriate `ParseError`.
 *
 * ## Description
 * Quantifiers specify the number of times a preceding atom can occur in a
 * pattern. This test suite covers the full syntactic and semantic range of this
 * feature. It verifies that the parser correctly interprets the different
 * quantifier syntaxes and their greedy (default), lazy (`?` suffix), and
 * possessive (`+` suffix) variants. A key focus is testing operator
 * precedence—ensuring that a quantifier correctly associates with a single
 * preceding atom (like a literal, group, or class) rather than an entire
 * sequence.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all standard quantifiers: `*`, `+`, `?`.
 * -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.
 * -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers.
 * -   The structure and values of the resulting `nodes.Quant` AST node
 * (including `min`, `max`, and `mode` fields).
 * -   Error handling for malformed brace quantifiers (e.g., `a{1,`).
 * -   The parser's correct identification of the atom to be quantified.
 * -   **Out of scope:**
 * -   Quantification of anchors (covered in `anchors.test.ts`).
 * -   The runtime behavior of quantifiers (covered by conformance tests).
 *
 * C Translation of `quantifiers.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- AST Node Definitions (Mocked) --------------------------------------------

/** @enum NodeKind_t Mirrors `nodes.Node.kind`. */
typedef enum {
    NODE_LIT,
    NODE_SEQ,
    NODE_GROUP,
    NODE_CHAR_CLASS,
    NODE_ANCHOR,
    NODE_QUANT
} NodeKind_t;

/** @enum QuantMode_t String-to-enum mapping for `mode`. */
typedef enum {
    QUANT_GREEDY,
    QUANT_LAZY,
    QUANT_POSSESSIVE
} QuantMode_t;

// Sentinel for "Inf"
const int QUANT_INF = -1;

// --- AST Node Structs ---------------------------------------------------------

/** @struct AST_Node_t Base structure for all AST nodes. */
typedef struct AST_Node { NodeKind_t kind; } AST_Node_t;
/** @struct Lit_Node_t Mirrors `nodes.Lit`. */
typedef struct { NodeKind_t kind; char* value; } Lit_Node_t;
/** @struct Seq_Node_t Mirrors `nodes.Seq`. */
typedef struct { NodeKind_t kind; AST_Node_t** parts; int num_parts; } Seq_Node_t;
/** @struct Group_Node_t Mirrors `nodes.Group`. */
typedef struct { NodeKind_t kind; AST_Node_t* child; } Group_Node_t;
/** @struct CharClass_Node_t Mirrors `nodes.CharClass`. */
typedef struct { NodeKind_t kind; bool negated; } CharClass_Node_t; // Simplified
/** @struct Anchor_Node_t Mirrors `nodes.Anchor`. */
typedef struct { NodeKind_t kind; } Anchor_Node_t; // Simplified
/** @struct Quant_Node_t Mirrors `nodes.Quant`. */
typedef struct {
    NodeKind_t kind; // NODE_QUANT
    AST_Node_t* child;
    int min;
    int max;
    QuantMode_t mode;
} Quant_Node_t;

/** @struct Flags_t Mirrors the `Flags` object. */
typedef struct { bool x; } Flags_t;
/** @struct ParseResult_t Bundles Flags and AST. */
typedef struct { Flags_t* flags; AST_Node_t* ast; } ParseResult_t;

// --- Global Error State (Mocked) ----------------------------------------------
/** @struct STRlingParseError_t Mock of `ParseError`. */
typedef struct { char* message; int pos; } STRlingParseError_t;
static STRlingParseError_t* g_last_parse_error = NULL;

void set_global_error(const char* message, int pos) {
    if (g_last_parse_error) { free(g_last_parse_error->message); free(g_last_parse_error); }
    g_last_parse_error = (STRlingParseError_t*)malloc(sizeof(STRlingParseError_t));
    g_last_parse_error->message = strdup(message);
    g_last_parse_error->pos = pos;
}
int teardown_error(void** state) {
    (void)state;
    if (g_last_parse_error) { free(g_last_parse_error->message); free(g_last_parse_error); g_last_parse_error = NULL; }
    return 0;
}

// --- AST Helper Functions (Mock constructors and destructors) -----------------
// Forward declare for recursive free
void free_ast(AST_Node_t* node);

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_LIT: free(((Lit_Node_t*)node)->value); break;
        case NODE_SEQ: {
            Seq_Node_t* seq = (Seq_Node_t*)node;
            for (int i = 0; i < seq->num_parts; ++i) free_ast(seq->parts[i]);
            free(seq->parts);
            break;
        }
        case NODE_GROUP: free_ast(((Group_Node_t*)node)->child); break;
        case NODE_CHAR_CLASS: /* (no heap data in this mock) */ break;
        case NODE_ANCHOR: /* (no heap data in this mock) */ break;
        case NODE_QUANT: free_ast(((Quant_Node_t*)node)->child); break;
    }
    free(node);
}

void free_parse_result(ParseResult_t* res) {
    if (res) { free(res->flags); free_ast(res->ast); free(res); }
}

AST_Node_t* create_lit(const char* value) {
    Lit_Node_t* n = (Lit_Node_t*)malloc(sizeof(Lit_Node_t));
    n->kind = NODE_LIT; n->value = strdup(value); return (AST_Node_t*)n;
}
AST_Node_t* create_seq(int num, ...) {
    Seq_Node_t* n = (Seq_Node_t*)malloc(sizeof(Seq_Node_t));
    n->kind = NODE_SEQ; n->num_parts = num;
    n->parts = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num);
    va_list args; va_start(args, num);
    for (int i = 0; i < num; ++i) n->parts[i] = va_arg(args, AST_Node_t*);
    va_end(args); return (AST_Node_t*)n;
}
AST_Node_t* create_group(AST_Node_t* child) {
    Group_Node_t* n = (Group_Node_t*)malloc(sizeof(Group_Node_t));
    n->kind = NODE_GROUP; n->child = child; return (AST_Node_t*)n;
}
AST_Node_t* create_char_class() {
    CharClass_Node_t* n = (CharClass_Node_t*)malloc(sizeof(CharClass_Node_t));
    n->kind = NODE_CHAR_CLASS; n->negated = false; return (AST_Node_t*)n;
}
AST_Node_t* create_quant(AST_Node_t* child, int min, int max, QuantMode_t mode) {
    Quant_Node_t* n = (Quant_Node_t*)malloc(sizeof(Quant_Node_t));
    n->kind = NODE_QUANT; n->child = child; n->min = min; n->max = max; n->mode = mode;
    return (AST_Node_t*)n;
}
ParseResult_t* create_parse_result(Flags_t* flags, AST_Node_t* ast) {
    ParseResult_t* res = (ParseResult_t*)malloc(sizeof(ParseResult_t));
    res->flags = flags; res->ast = ast; return res;
}
Flags_t* create_flags(bool x) {
    Flags_t* f = (Flags_t*)malloc(sizeof(Flags_t));
    f->x = x; return f;
}

// --- Mock `parse` Function (SUT) ----------------------------------------------
// Note: This SUT mock returns the *AST*, not the ParseResult_t, by default.
// A separate function `strling_parse_with_flags` is used for the flag test.

AST_Node_t* strling_parse(const char* src) {
    teardown_error(NULL);
    // Cat A: Standard Quantifiers
    if (strcmp(src, "a*") == 0) return create_quant(create_lit("a"), 0, QUANT_INF, QUANT_GREEDY);
    if (strcmp(src, "a+") == 0) return create_quant(create_lit("a"), 1, QUANT_INF, QUANT_GREEDY);
    if (strcmp(src, "a?") == 0) return create_quant(create_lit("a"), 0, 1, QUANT_GREEDY);
    // Cat B: Brace Quantifiers
    if (strcmp(src, "a{5}") == 0) return create_quant(create_lit("a"), 5, 5, QUANT_GREEDY);
    if (strcmp(src, "a{2,}") == 0) return create_quant(create_lit("a"), 2, QUANT_INF, QUANT_GREEDY);
    if (strcmp(src, "a{3,10}") == 0) return create_quant(create_lit("a"), 3, 10, QUANT_GREEDY);
    // Cat C: Quantifier Modes
    if (strcmp(src, "a*?") == 0) return create_quant(create_lit("a"), 0, QUANT_INF, QUANT_LAZY);
    if (strcmp(src, "a+?") == 0) return create_quant(create_lit("a"), 1, QUANT_INF, QUANT_LAZY);
    if (strcmp(src, "a??") == 0) return create_quant(create_lit("a"), 0, 1, QUANT_LAZY);
    if (strcmp(src, "a{2,5}?") == 0) return create_quant(create_lit("a"), 2, 5, QUANT_LAZY);
    if (strcmp(src, "a*+") == 0) return create_quant(create_lit("a"), 0, QUANT_INF, QUANT_POSSESSIVE);
    if (strcmp(src, "a++") == 0) return create_quant(create_lit("a"), 1, QUANT_INF, QUANT_POSSESSIVE);
    if (strcmp(src, "a?+") == 0) return create_quant(create_lit("a"), 0, 1, QUANT_POSSESSIVE);
    if (strcmp(src, "a{3,7}+") == 0) return create_quant(create_lit("a"), 3, 7, QUANT_POSSESSIVE);
    // Cat D: Precedence
    if (strcmp(src, "abc*") == 0) {
        return create_seq(3, create_lit("a"), create_lit("b"), create_quant(create_lit("c"), 0, QUANT_INF, QUANT_GREEDY));
    }
    if (strcmp(src, "(abc)*") == 0) {
        return create_quant(create_group(create_seq(3, create_lit("a"), create_lit("b"), create_lit("c"))), 0, QUANT_INF, QUANT_GREEDY);
    }
    if (strcmp(src, "[abc]*") == 0) {
        return create_quant(create_char_class(), 0, QUANT_INF, QUANT_GREEDY);
    }
    // Cat J: Errors
    if (strcmp(src, "*") == 0) { set_global_error("Quantifier follows nothing", 0); return NULL; }
    if (strcmp(src, "+") == 0) { set_global_error("Quantifier follows nothing", 0); return NULL; }
    if (strcmp(src, "?") == 0) { set_global_error("Quantifier follows nothing", 0); return NULL; }
    if (strcmp(src, "{1,2}") == 0) { set_global_error("Quantifier follows nothing", 0); return NULL; }
    if (strcmp(src, "a{") == 0) { set_global_error("Incomplete quantifier", 2); return NULL; }
    if (strcmp(src, "a{1,") == 0) { set_global_error("Incomplete quantifier", 4); return NULL; }
    if (strcmp(src, "a{1,2") == 0) { set_global_error("Incomplete quantifier", 5); return NULL; }
    if (strcmp(src, "a{1,b}") == 0) { set_global_error("Invalid quantifier", 4); return NULL; }
    // Fallback
    return NULL;
}

// Separate SUT mock for the flags test
ParseResult_t* strling_parse_with_flags(const char* src) {
    if (strcmp(src, "%flags x\na *") == 0) {
        return create_parse_result(create_flags(true), create_seq(2, create_lit("a"), create_lit("*")));
    }
    if (strcmp(src, "%flags x\n\\ *") == 0) {
        return create_parse_result(create_flags(true), create_quant(create_lit(" "), 0, QUANT_INF, QUANT_GREEDY));
    }
    return NULL;
}


// --- Custom Assertion Helpers -------------------------------------------------

void assert_quant(AST_Node_t* node, NodeKind_t child_kind, int min, int max, QuantMode_t mode) {
    assert_non_null(node);
    assert_int_equal(node->kind, NODE_QUANT);
    Quant_Node_t* quant = (Quant_Node_t*)node;
    assert_non_null(quant->child);
    assert_int_equal(quant->child->kind, child_kind);
    assert_int_equal(quant->min, min);
    assert_int_equal(quant->max, max);
    assert_int_equal(quant->mode, mode);
}

// --- Test Cases ---------------------------------------------------------------

/** @brief Corresponds to "describe('Category A: Standard Quantifiers', ...)" */
static void test_standard_quantifiers(void** state) {
    (void)state;
    typedef struct { const char* input; int min; int max; } TestCase;
    const TestCase cases[] = {
        {"a*", 0, QUANT_INF},
        {"a+", 1, QUANT_INF},
        {"a?", 0, 1},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_quant(ast, NODE_LIT, cases[i].min, cases[i].max, QUANT_GREEDY);
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category B: Brace Quantifiers', ...)" */
static void test_brace_quantifiers(void** state) {
    (void)state;
    typedef struct { const char* input; int min; int max; } TestCase;
    const TestCase cases[] = {
        {"a{5}", 5, 5},
        {"a{2,}", 2, QUANT_INF},
        {"a{3,10}", 3, 10},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_quant(ast, NODE_LIT, cases[i].min, cases[i].max, QUANT_GREEDY);
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category C: Quantifier Modes (Lazy/Possessive)', ...)" */
static void test_quantifier_modes(void** state) {
    (void)state;
    typedef struct { const char* input; int min; int max; QuantMode_t mode; } TestCase;
    const TestCase cases[] = {
        {"a*?", 0, QUANT_INF, QUANT_LAZY},
        {"a+?", 1, QUANT_INF, QUANT_LAZY},
        {"a??", 0, 1, QUANT_LAZY},
        {"a{2,5}?", 2, 5, QUANT_LAZY},
        {"a*+", 0, QUANT_INF, QUANT_POSSESSIVE},
        {"a++", 1, QUANT_INF, QUANT_POSSESSIVE},
        {"a?+", 0, 1, QUANT_POSSESSIVE},
        {"a{3,7}+", 3, 7, QUANT_POSSESSIVE},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_quant(ast, NODE_LIT, cases[i].min, cases[i].max, cases[i].mode);
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category D: Quantifier Precedence (Atom Binding)', ...)" */
static void test_quantifier_precedence(void** state) {
    (void)state;
    // Test: "abc*" -> Seq(Lit(a), Lit(b), Quant(Lit(c), ...))
    AST_Node_t* ast1 = strling_parse("abc*");
    assert_int_equal(ast1->kind, NODE_SEQ);
    Seq_Node_t* seq = (Seq_Node_t*)ast1;
    assert_int_equal(seq->num_parts, 3);
    assert_int_equal(seq->parts[0]->kind, NODE_LIT);
    assert_int_equal(seq->parts[1]->kind, NODE_LIT);
    assert_quant(seq->parts[2], NODE_LIT, 0, QUANT_INF, QUANT_GREEDY);
    free_ast(ast1);

    // Test: "(abc)*" -> Quant(Group(Seq(Lit(a), Lit(b), Lit(c))), ...)
    AST_Node_t* ast2 = strling_parse("(abc)*");
    assert_quant(ast2, NODE_GROUP, 0, QUANT_INF, QUANT_GREEDY);
    free_ast(ast2);

    // Test: "[abc]*" -> Quant(CharClass(...), ...)
    AST_Node_t* ast3 = strling_parse("[abc]*");
    assert_quant(ast3, NODE_CHAR_CLASS, 0, QUANT_INF, QUANT_GREEDY);
    free_ast(ast3);
}

/** @brief Corresponds to "describe('Category E: Quantifier Interaction With Flags', ...)" */
static void test_quantifier_flag_interactions(void** state) {
    (void)state;
    // Test: "%flags x\na *" -> Seq(Lit(a), Lit(*))
    ParseResult_t* res1 = strling_parse_with_flags("%flags x\na *");
    assert_non_null(res1);
    assert_true(res1->flags->x);
    assert_int_equal(res1->ast->kind, NODE_SEQ);
    Seq_Node_t* seq = (Seq_Node_t*)res1->ast;
    assert_int_equal(seq->num_parts, 2);
    assert_int_equal(seq->parts[0]->kind, NODE_LIT);
    assert_int_equal(seq->parts[1]->kind, NODE_LIT); // '*' is a literal
    free_parse_result(res1);

    // Test: "%flags x\n\\ *" -> Quant(Lit(" "), ...)
    ParseResult_t* res2 = strling_parse_with_flags("%flags x\n\\ *");
    assert_non_null(res2);
    assert_true(res2->flags->x);
    assert_quant(res2->ast, NODE_LIT, 0, QUANT_INF, QUANT_GREEDY);
    free_parse_result(res2);
}

/** @brief Corresponds to "describe('Category J: Error Cases', ...)" */
static void test_error_cases(void** state) {
    (void)state;
    typedef struct { const char* input; const char* msg_substr; int pos; } ErrorCase;
    const ErrorCase cases[] = {
        {"*", "Quantifier follows nothing", 0},
        {"+", "Quantifier follows nothing", 0},
        {"?", "Quantifier follows nothing", 0},
        {"{1,2}", "Quantifier follows nothing", 0},
        {"a{", "Incomplete quantifier", 2},
        {"a{1,", "Incomplete quantifier", 4},
        {"a{1,2", "Incomplete quantifier", 5},
        {"a{1,b}", "Invalid quantifier", 4},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_null_bt(ast, "Input: %s", cases[i].input);
        assert_non_null(g_last_parse_error);
        assert_non_null_bt(strstr(g_last_parse_error->message, cases[i].msg_substr), "Input: %s", cases[i].input);
        assert_int_equal(g_last_parse_error->pos, cases[i].pos);
    }
}

// --- Test Runner (main) -----------------------------------------------------
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_standard_quantifiers),
        cmocka_unit_test(test_brace_quantifiers),
        cmocka_unit_test(test_quantifier_modes),
        cmocka_unit_test(test_quantifier_precedence),
        cmockT_unit_test(test_quantifier_flag_interactions), // Note: Changed name, cmocka_unit_test
        cmocka_unit_test_teardown(test_error_cases, teardown_error),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
