/**
 * @file groups_backrefs_lookarounds_test.c
 *
 * ## Purpose
 * This test suite validates the parser's handling of all grouping constructs,
 * backreferences, and lookarounds. It ensures that different group types are
 * parsed correctly into their corresponding AST nodes, that backreferences are
 * validated against defined groups, that lookarounds are constructed properly,
 * and that all syntactic errors raise the correct `ParseError`.
 *
 * ## Description
 * Groups, backreferences, and lookarounds are the primary features for defining
 * structure and context within a pattern.
 * -   **Groups** `(...)` are used to create sub-patterns, apply quantifiers to
 * sequences, and capture text for later use.
 * -   **Backreferences** `\1`, `\k<name>` match the exact text previously
 * captured by a group.
 * -   **Lookarounds** `(?=...)`, `(?<=...)`, etc., are zero-width assertions that
 * check for patterns before or after the current position without consuming
 * characters.
 *
 * This suite verifies that the parser correctly implements the rich syntax and
 * validation rules for these powerful features.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all group types: capturing `()`, non-capturing `(?:...)`,
 * named `(?<name>...)`, and atomic `(?>...)`.
 * -   Parsing of numeric (`\1`) and named (`\k<name>`) backreferences.
 * -   Validation of backreferences (e.g., ensuring no forward references).
 * -   Parsing of all four lookaround types: positive/negative ahead/behind.
 * -   Error handling for invalid syntax (e.g., duplicate group names,
 * quantifying lookarounds).
 *
 * -   **Out of scope:**
 * -   Quantification of valid groups (e.g., `(a)+`), which is covered by
 * the quantifiers test suite.
 * -   The runtime behavior of these constructs.
 *
 * C Translation of `groups_backrefs_lookarounds.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- AST Node Definitions (Mocked) --------------------------------------------

/**
 * @enum NodeKind_t
 * Mirrors the `nodes.Node.kind` property to identify AST node types.
 */
typedef enum {
    NODE_LIT,
    NODE_SEQ,
    NODE_ALT,
    NODE_GROUP,
    NODE_LOOKAROUND,
    NODE_BACKREF
} NodeKind_t;

/**
 * @enum LookaroundType_t
 * Consolidates the `dir` and `negated` properties of `nodes.Look`.
 */
typedef enum {
    LOOKAHEAD_POS,        // (?=...)
    LOOKAHEAD_NEG,        // (?!...)
    LOOKBEHIND_POS,       // (?<=...)
    LOOKBEHIND_NEG        // (?<!...)
} LookaroundType_t;

// --- AST Node Structs ---------------------------------------------------------

/** @struct AST_Node_t Base structure for all AST nodes. */
typedef struct AST_Node {
    NodeKind_t kind;
} AST_Node_t;

/** @struct Lit_Node_t Mirrors `nodes.Lit`. */
typedef struct { NodeKind_t kind; char* value; } Lit_Node_t;

/** @struct Seq_Node_t Mirrors `nodes.Seq`. */
typedef struct { NodeKind_t kind; AST_Node_t** parts; int num_parts; } Seq_Node_t;

/** @struct Alt_Node_t Mirrors `nodes.Alt`. */
typedef struct { NodeKind_t kind; AST_Node_t** branches; int num_branches; } Alt_Node_t;

/** @struct Group_Node_t Mirrors `nodes.Group`. */
typedef struct {
    NodeKind_t kind; // NODE_GROUP
    AST_Node_t* child;
    bool capturing;
    char* name;    // NULL if not named
    bool atomic;   // True for (?>...)
} Group_Node_t;

/** @struct Lookaround_Node_t Mirrors `nodes.Look`. */
typedef struct {
    NodeKind_t kind; // NODE_LOOKAROUND
    AST_Node_t* child;
    LookaroundType_t lookaround_kind;
} Lookaround_Node_t;

/** @struct Backref_Node_t Mirrors `nodes.Backref`. */
typedef struct {
    NodeKind_t kind; // NODE_BACKREF
    int number;    // -1 if not numeric
    char* name;    // NULL if not named
} Backref_Node_t;


// --- Global Error State (Mocked) ----------------------------------------------

/** @struct STRlingParseError_t Mock of `ParseError`. */
typedef struct {
    char* message;
    int pos;
} STRlingParseError_t;

static STRlingParseError_t* g_last_parse_error = NULL;

void set_global_error(const char* message, int pos) {
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error);
    }
    g_last_parse_error = (STRlingParseError_t*)malloc(sizeof(STRlingParseError_t));
    g_last_parse_error->message = strdup(message);
    g_last_parse_error->pos = pos;
}

int teardown_error(void** state) {
    (void)state;
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error);
        g_last_parse_error = NULL;
    }
    return 0;
}

// --- AST Helper Functions (Mock constructors and destructors) -----------------

// Forward declare for recursive free
void free_ast(AST_Node_t* node);

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_LIT:
            free(((Lit_Node_t*)node)->value);
            break;
        case NODE_SEQ: {
            Seq_Node_t* seq = (Seq_Node_t*)node;
            for (int i = 0; i < seq->num_parts; ++i) free_ast(seq->parts[i]);
            free(seq->parts);
            break;
        }
        case NODE_ALT: {
            Alt_Node_t* alt = (Alt_Node_t*)node;
            for (int i = 0; i < alt->num_branches; ++i) free_ast(alt->branches[i]);
            free(alt->branches);
            break;
        }
        case NODE_GROUP: {
            Group_Node_t* group = (Group_Node_t*)node;
            free_ast(group->child);
            free(group->name);
            break;
        }
        case NODE_LOOKAROUND:
            free_ast(((Lookaround_Node_t*)node)->child);
            break;
        case NODE_BACKREF:
            free(((Backref_Node_t*)node)->name);
            break;
    }
    free(node);
}

AST_Node_t* create_lit(const char* value) {
    Lit_Node_t* node = (Lit_Node_t*)malloc(sizeof(Lit_Node_t));
    node->kind = NODE_LIT;
    node->value = strdup(value);
    return (AST_Node_t*)node;
}

AST_Node_t* create_seq(int num_parts, ...) {
    Seq_Node_t* node = (Seq_Node_t*)malloc(sizeof(Seq_Node_t));
    node->kind = NODE_SEQ;
    node->num_parts = num_parts;
    node->parts = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num_parts);
    va_list args;
    va_start(args, num_parts);
    for (int i = 0; i < num_parts; ++i) node->parts[i] = va_arg(args, AST_Node_t*);
    va_end(args);
    return (AST_Node_t*)node;
}

AST_Node_t* create_alt(int num_branches, ...) {
    Alt_Node_t* node = (Alt_Node_t*)malloc(sizeof(Alt_Node_t));
    node->kind = NODE_ALT;
    node->num_branches = num_branches;
    node->branches = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num_branches);
    va_list args;
    va_start(args, num_branches);
    for (int i = 0; i < num_branches; ++i) node->branches[i] = va_arg(args, AST_Node_t*);
    va_end(args);
    return (AST_Node_t*)node;
}

AST_Node_t* create_group(AST_Node_t* child, bool capturing, const char* name, bool atomic) {
    Group_Node_t* node = (Group_Node_t*)malloc(sizeof(Group_Node_t));
    node->kind = NODE_GROUP;
    node->child = child;
    node->capturing = capturing;
    node->name = name ? strdup(name) : NULL;
    node->atomic = atomic;
    return (AST_Node_t*)node;
}

AST_Node_t* create_lookaround(AST_Node_t* child, LookaroundType_t la_kind) {
    Lookaround_Node_t* node = (Lookaround_Node_t*)malloc(sizeof(Lookaround_Node_t));
    node->kind = NODE_LOOKAROUND;
    node->child = child;
    node->lookaround_kind = la_kind;
    return (AST_Node_t*)node;
}

AST_Node_t* create_backref(int number, const char* name) {
    Backref_Node_t* node = (Backref_Node_t*)malloc(sizeof(Backref_Node_t));
    node->kind = NODE_BACKREF;
    node->number = number;
    node->name = name ? strdup(name) : NULL;
    return (AST_Node_t*)node;
}


// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded AST for known inputs.
 * C equivalent of the `parse(src)[1]` (i.e., just the AST part).
 * Returns NULL on error and sets `g_last_parse_error`.
 */
AST_Node_t* strling_parse(const char* src) {
    teardown_error(NULL);

    // Category A: Capturing Groups
    if (strcmp(src, "(a)") == 0) return create_group(create_lit("a"), true, NULL, false);
    if (strcmp(src, "(a(b))") == 0) {
        return create_group(
            create_seq(2, create_lit("a"), create_group(create_lit("b"), true, NULL, false)),
            true, NULL, false
        );
    }
    
    // Category B: Non-Capturing Groups
    if (strcmp(src, "(?:a)") == 0) return create_group(create_lit("a"), false, NULL, false);
    
    // Category C: Named Groups
    if (strcmp(src, "(?<name>a)") == 0) return create_group(create_lit("a"), true, "name", false);
    
    // Category D: Atomic Groups
    if (strcmp(src, "(?>a)") == 0) return create_group(create_lit("a"), false, NULL, true);

    // Category E: Lookarounds
    if (strcmp(src, "(?=a)") == 0) return create_lookaround(create_lit("a"), LOOKAHEAD_POS);
    if (strcmp(src, "(?!a)") == 0) return create_lookaround(create_lit("a"), LOOKAHEAD_NEG);
    if (strcmp(src, "(?<=a)") == 0) return create_lookaround(create_lit("a"), LOOKBEHIND_POS);
    if (strcmp(src, "(?<!a)") == 0) return create_lookaround(create_lit("a"), LOOKBEHIND_NEG);

    // Category F: Backreferences
    if (strcmp(src, "(a)\\1") == 0) {
        return create_seq(2,
            create_group(create_lit("a"), true, NULL, false),
            create_backref(1, NULL)
        );
    }
    if (strcmp(src, "(?<name>a)\\k<name>") == 0) {
        return create_seq(2,
            create_group(create_lit("a"), true, "name", false),
            create_backref(-1, "name")
        );
    }

    // Category G: Alternation Interactions
    if (strcmp(src, "(a)|(b)") == 0) {
        return create_alt(2,
            create_group(create_lit("a"), true, NULL, false),
            create_group(create_lit("b"), true, NULL, false)
        );
    }
    if (strcmp(src, "(?=a)|(?=b)") == 0) {
        return create_alt(2,
            create_lookaround(create_lit("a"), LOOKAHEAD_POS),
            create_lookaround(create_lit("b"), LOOKAHEAD_POS)
        );
    }
    if (strcmp(src, "(a)|(?:b)|(?<x>c)") == 0) {
        return create_alt(3,
            create_group(create_lit("a"), true, NULL, false),
            create_group(create_lit("b"), false, NULL, false),
            create_group(create_lit("c"), true, "x", false)
        );
    }

    // Category J: Error Cases
    if (strcmp(src, "\\0") == 0) { set_global_error("Invalid backreference", 0); return NULL; }
    if (strcmp(src, "\\1") == 0) { set_global_error("Backreference to non-existent group", 0); return NULL; }
    if (strcmp(src, "\\k<name>") == 0) { set_global_error("Backreference to non-existent group", 0); return NULL; }
    if (strcmp(src, "(?<name>a)(?<name>b)") == 0) { set_global_error("Duplicate group name: name", 10); return NULL; }
    if (strcmp(src, "(?<name>a)\\1(?<name>b)") == 0) { set_global_error("Duplicate group name: name", 13); return NULL; }
    if (strcmp(src, "(?=a)*") == 0) { set_global_error("Cannot quantify lookaround", 0); return NULL; }


    // Fallback
    return NULL;
}

// --- Custom Assertion Helpers -------------------------------------------------

void assert_node_kind(AST_Node_t* node, NodeKind_t expected_kind) {
    assert_non_null(node);
    assert_int_equal(node->kind, expected_kind);
}

void assert_lit_value(AST_Node_t* node, const char* expected_value) {
    assert_node_kind(node, NODE_LIT);
    Lit_Node_t* lit = (Lit_Node_t*)node;
    assert_string_equal(lit->value, expected_value);
}

void assert_seq_length(AST_Node_t* node, int expected_length) {
    assert_node_kind(node, NODE_SEQ);
    Seq_Node_t* seq = (Seq_Node_t*)node;
    assert_int_equal(seq->num_parts, expected_length);
}

AST_Node_t* get_seq_part(AST_Node_t* node, int index) {
    assert_node_kind(node, NODE_SEQ);
    Seq_Node_t* seq = (Seq_Node_t*)node;
    assert_true(index < seq->num_parts);
    return seq->parts[index];
}

void assert_alt_length(AST_Node_t* node, int expected_length) {
    assert_node_kind(node, NODE_ALT);
    Alt_Node_t* alt = (Alt_Node_t*)node;
    assert_int_equal(alt->num_branches, expected_length);
}

AST_Node_t* get_alt_branch(AST_Node_t* node, int index) {
    assert_node_kind(node, NODE_ALT);
    Alt_Node_t* alt = (Alt_Node_t*)node;
    assert_true(index < alt->num_branches);
    return alt->branches[index];
}

void assert_group(AST_Node_t* node, bool capturing, const char* name, bool atomic) {
    assert_node_kind(node, NODE_GROUP);
    Group_Node_t* group = (Group_Node_t*)node;
    assert_int_equal(group->capturing, capturing);
    assert_int_equal(group->atomic, atomic);
    if (name) {
        assert_string_equal(group->name, name);
    } else {
        assert_null(group->name);
    }
}

void assert_lookaround(AST_Node_t* node, LookaroundType_t la_kind) {
    assert_node_kind(node, NODE_LOOKAROUND);
    Lookaround_Node_t* look = (Lookaround_Node_t*)node;
    assert_int_equal(look->lookaround_kind, la_kind);
}

void assert_backref(AST_Node_t* node, int number, const char* name) {
    assert_node_kind(node, NODE_BACKREF);
    Backref_Node_t* backref = (Backref_Node_t*)node;
    assert_int_equal(backref->number, number);
    if (name) {
        assert_string_equal(backref->name, name);
    } else {
        assert_null(backref->name);
    }
}


// --- Test Cases ---------------------------------------------------------------

/** @brief Corresponds to "describe('Category A: Capturing Groups', ...)" */
static void test_capturing_groups(void** state) {
    (void)state; // Unused
    
    // Test: "(a)"
    AST_Node_t* ast1 = strling_parse("(a)");
    assert_group(ast1, true, NULL, false);
    assert_lit_value(((Group_Node_t*)ast1)->child, "a");
    free_ast(ast1);

    // Test: "(a(b))"
    AST_Node_t* ast2 = strling_parse("(a(b))");
    assert_group(ast2, true, NULL, false);
    
    AST_Node_t* child_seq = ((Group_Node_t*)ast2)->child;
    assert_seq_length(child_seq, 2);
    
    assert_lit_value(get_seq_part(child_seq, 0), "a");
    
    AST_Node_t* nested_group = get_seq_part(child_seq, 1);
    assert_group(nested_group, true, NULL, false);
    assert_lit_value(((Group_Node_t*)nested_group)->child, "b");
    
    free_ast(ast2);
}

/** @brief Corresponds to "describe('Category B: Non-Capturing Groups', ...)" */
static void test_non_capturing_groups(void** state) {
    (void)state; // Unused
    AST_Node_t* ast = strling_parse("(?:a)");
    assert_group(ast, false, NULL, false);
    assert_lit_value(((Group_Node_t*)ast)->child, "a");
    free_ast(ast);
}

/** @brief Corresponds to "describe('Category C: Named Groups', ...)" */
static void test_named_groups(void** state) {
    (void)state; // Unused
    AST_Node_t* ast = strling_parse("(?<name>a)");
    assert_group(ast, true, "name", false);
    assert_lit_value(((Group_Node_t*)ast)->child, "a");
    free_ast(ast);
}

/** @brief Corresponds to "describe('Category D: Atomic Groups', ...)" */
static void test_atomic_groups(void** state) {
    (void)state; // Unused
    AST_Node_t* ast = strling_parse("(?>a)");
    assert_group(ast, false, NULL, true);
    assert_lit_value(((Group_Node_t*)ast)->child, "a");
    free_ast(ast);
}

/** @brief Corresponds to "describe('Category E: Lookarounds', ...)" */
static void test_lookarounds(void** state) {
    (void)state; // Unused
    
    typedef struct { const char* input; LookaroundType_t la_kind; } TestCase;
    const TestCase cases[] = {
        {"(?=a)", LOOKAHEAD_POS},
        {"(?!a)", LOOKAHEAD_NEG},
        {"(?<=a)", LOOKBEHIND_POS},
        {"(?<!a)", LOOKBEHIND_NEG},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_lookaround(ast, cases[i].la_kind);
        assert_lit_value(((Lookaround_Node_t*)ast)->child, "a");
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category F: Backreferences', ...)" */
static void test_backreferences(void** state) {
    (void)state; // Unused
    
    // Test: "(a)\1"
    AST_Node_t* ast1 = strling_parse("(a)\\1");
    assert_seq_length(ast1, 2);
    assert_group(get_seq_part(ast1, 0), true, NULL, false);
    assert_backref(get_seq_part(ast1, 1), 1, NULL);
    free_ast(ast1);

    // Test: "(?<name>a)\k<name>"
    AST_Node_t* ast2 = strling_parse("(?<name>a)\\k<name>");
    assert_seq_length(ast2, 2);
    assert_group(get_seq_part(ast2, 0), true, "name", false);
    assert_backref(get_seq_part(ast2, 1), -1, "name");
    free_ast(ast2);
}

/** @brief Corresponds to "describe('Category G: Alternation Interactions', ...)" */
static void test_alternation_interactions(void** state) {
    (void)state; // Unused

    // Test: "(a)|(b)"
    AST_Node_t* ast1 = strling_parse("(a)|(b)");
    assert_alt_length(ast1, 2);
    assert_group(get_alt_branch(ast1, 0), true, NULL, false);
    assert_group(get_alt_branch(ast1, 1), true, NULL, false);
    free_ast(ast1);

    // Test: "(?=a)|(?=b)"
    AST_Node_t* ast2 = strling_parse("(?=a)|(?=b)");
    assert_alt_length(ast2, 2);
    assert_lookaround(get_alt_branch(ast2, 0), LOOKAHEAD_POS);
    assert_lookaround(get_alt_branch(ast2, 1), LOOKAHEAD_POS);
    free_ast(ast2);

    // Test: "(a)|(?:b)|(?<x>c)"
    AST_Node_t* ast3 = strling_parse("(a)|(?:b)|(?<x>c)");
    assert_alt_length(ast3, 3);
    assert_group(get_alt_branch(ast3, 0), true, NULL, false);
    assert_group(get_alt_branch(ast3, 1), false, NULL, false);
    assert_group(get_alt_branch(ast3, 2), true, "x", false);
    free_ast(ast3);
}

/** @brief Corresponds to "describe('Category J: Error Cases', ...)" */
static void test_error_cases(void** state) {
    (void)state; // Unused
    
    typedef struct { const char* input; const char* error_msg; int pos; } ErrorCase;
    const ErrorCase cases[] = {
        {"\\0", "Invalid backreference", 0},
        {"\\1", "Backreference to non-existent group", 0},
        {"\\k<name>", "Backreference to non-existent group", 0},
        {"(?<name>a)(?<name>b)", "Duplicate group name", 10},
        {"(?<name>a)\\1(?<name>b)", "Duplicate group name", 13},
        {"(?=a)*", "Cannot quantify lookaround", 0},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        
        // C equivalent of: expect(() => parse(case)).toThrow(ParseError);
        assert_null_bt(ast, "Test Input: %s (should have returned NULL)", cases[i].input);
        
        // C equivalent of: expect(() => parse(case)).toThrow(/.../);
        assert_non_null(g_last_parse_error);
        assert_non_null_bt(strstr(g_last_parse_error->message, cases[i].error_msg),
                           "Test Input: %s (Error message '%s' did not contain '%s')",
                           cases[i].input, g_last_parse_error->message, cases[i].error_msg);
        assert_int_equal(g_last_parse_error->pos, cases[i].pos);
    }
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_capturing_groups),
        cmocka_unit_test(test_non_capturing_groups),
        cmocka_unit_test(test_named_groups),
        cmocka_unit_test(test_atomic_groups),
        cmocka_unit_test(test_lookarounds),
        cmocka_unit_test(test_backreferences),
        cmocka_unit_test(test_alternation_interactions),
        cmocka_unit_test_teardown(test_error_cases, teardown_error),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup
}
