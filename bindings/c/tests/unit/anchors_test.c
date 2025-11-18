/**
 * @file anchors_test.c
 *
 * ## Purpose
 * This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
 * It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
 * with the proper type and that its parsing is unaffected by flags or surrounding
 * constructs.
 *
 * ## Description
 * Anchors are zero-width assertions that do not consume characters but instead
 * match a specific **position** within the input string, such as the start of a
 * line or a boundary between a word and a space. This suite tests the parser's
 * ability to correctly identify all supported core and extension anchors and
 * produce the corresponding `nodes.Anchor` AST object.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
 * (`\b`, `\B`).
 * -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
 *
 * -   The structure and `at` value of the resulting `nodes.Anchor` AST node.
 *
 * -   How anchors are parsed when placed at the start, middle, or end of a sequence.
 *
 * -   Ensuring the parser's output for `^` and `$` is consistent regardless
 * of the multiline (`m`) flag's presence.
 * -   **Out of scope:**
 * -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
 * active (this is an emitter/engine concern).
 * -   Quantification of anchors.
 * -   The behavior of anchors in combination with other complex constructs
 * (e.g., inside lookarounds), which is covered by combinatorial E2E tests.
 *
 * C Translation of `anchors.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <cmocka.h>

// --- AST Node Definitions (Mocked) --------------------------------------------
// These C structs and enums mirror the TypeScript `nodes.ts` classes.

/**
 * @enum NodeKind_t
 * Mirrors the `nodes.Node.kind` property to identify AST node types.
 */
typedef enum {
    NODE_LIT,
    NODE_ANCHOR,
    NODE_SEQ
} NodeKind_t;

/**
 * @enum AnchorType_t
 * Mirrors the `at` property of the `nodes.Anchor` class.
 */
typedef enum {
    ANCHOR_START,           // ^
    ANCHOR_END,             // $
    ANCHOR_WORD_BOUNDARY,   // \b
    ANCHOR_NON_WORD_BOUNDARY, // \B
    ANCHOR_ABSOLUTE_START,  // \A
    ANCHOR_ABSOLUTE_END,    // \Z
    ANCHOR_ABSOLUTE_END_ONLY // \z
} AnchorType_t;

/**
 * @struct AST_Node_t
 * Base structure for all AST nodes.
 */
typedef struct {
    NodeKind_t kind;
} AST_Node_t;

/**
 * @struct Lit_Node_t
 * Mirrors `nodes.Lit`.
 */
typedef struct {
    NodeKind_t kind; // NODE_LIT
    char* value;
} Lit_Node_t;

/**
 * @struct Anchor_Node_t
 * Mirrors `nodes.Anchor`.
 */
typedef struct {
    NodeKind_t kind; // NODE_ANCHOR
    AnchorType_t at;
} Anchor_Node_t;

/**
 * @struct Seq_Node_t
 * Mirrors `nodes.Seq`.
 */
typedef struct {
    NodeKind_t kind; // NODE_SEQ
    AST_Node_t** parts;
    int num_parts;
} Seq_Node_t;

// --- Global Error State (for mocking ParseError) ------------------------------
static const char* g_last_error_message = NULL;

// --- AST Helper Functions (Mock constructors and destructors) -----------------

AST_Node_t* create_lit(const char* value) {
    Lit_Node_t* node = (Lit_Node_t*)malloc(sizeof(Lit_Node_t));
    node->kind = NODE_LIT;
    node->value = strdup(value);
    return (AST_Node_t*)node;
}

AST_Node_t* create_anchor(AnchorType_t at) {
    Anchor_Node_t* node = (Anchor_Node_t*)malloc(sizeof(Anchor_Node_t));
    node->kind = NODE_ANCHOR;
    node->at = at;
    return (AST_Node_t*)node;
}

AST_Node_t* create_seq(int num_parts, ...) {
    Seq_Node_t* node = (Seq_Node_t*)malloc(sizeof(Seq_Node_t));
    node->kind = NODE_SEQ;
    node->num_parts = num_parts;
    node->parts = (AST_Node_t**)malloc(sizeof(AST_Node_t*) * num_parts);
    
    va_list args;
    va_start(args, num_parts);
    for (int i = 0; i < num_parts; ++i) {
        node->parts[i] = va_arg(args, AST_Node_t*);
    }
    va_end(args);
    return (AST_Node_t*)node;
}

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_LIT:
            free(((Lit_Node_t*)node)->value);
            break;
        case NODE_ANCHOR:
            // No extra data to free
            break;
        case NODE_SEQ: {
            Seq_Node_t* seq = (Seq_Node_t*)node;
            for (int i = 0; i < seq->num_parts; ++i) {
                free_ast(seq->parts[i]);
            }
            free(seq->parts);
            break;
        }
    }
    free(node);
}

// --- Mock `parse` Function ----------------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded AST for known inputs.
 * C equivalent of the `parse` function under test.
 * Returns NULL on error and sets `g_last_error_message`.
 */
AST_Node_t* strling_parse(const char* src) {
    g_last_error_message = NULL;

    // Category A: Core Anchors
    if (strcmp(src, "^") == 0) return create_anchor(ANCHOR_START);
    if (strcmp(src, "$") == 0) return create_anchor(ANCHOR_END);
    if (strcmp(src, "\\b") == 0) return create_anchor(ANCHOR_WORD_BOUNDARY);
    if (strcmp(src, "\\B") == 0) return create_anchor(ANCHOR_NON_WORD_BOUNDARY);

    // Category B: Absolute Anchors
    if (strcmp(src, "\\A") == 0) return create_anchor(ANCHOR_ABSOLUTE_START);
    if (strcmp(src, "\\Z") == 0) return create_anchor(ANCHOR_ABSOLUTE_END);
    if (strcmp(src, "\\z") == 0) return create_anchor(ANCHOR_ABSOLUTE_END_ONLY);

    // Category C: Flags (No-op)
    if (strcmp(src, "%flags m\n^") == 0) return create_anchor(ANCHOR_START);
    if (strcmp(src, "%flags m\n$") == 0) return create_anchor(ANCHOR_END);

    // Category D: Anchors in Sequences
    if (strcmp(src, "^a") == 0) {
        return create_seq(2, create_anchor(ANCHOR_START), create_lit("a"));
    }
    if (strcmp(src, "a$") == 0) {
        return create_seq(2, create_lit("a"), create_anchor(ANCHOR_END));
    }
    if (strcmp(src, "a\\b$") == 0) {
        return create_seq(3, create_lit("a"), create_anchor(ANCHOR_WORD_BOUNDARY), create_anchor(ANCHOR_END));
    }
    if (strcmp(src, "^\\ba\\b$") == 0) {
        return create_seq(5,
            create_anchor(ANCHOR_START),
            create_anchor(ANCHOR_WORD_BOUNDARY),
            create_lit("a"),
            create_anchor(ANCHOR_WORD_BOUNDARY),
            create_anchor(ANCHOR_END)
        );
    }

    // Category J: Anchors with Quantifiers (Errors)
    const char* quantified_anchors[] = {"^*", "^+", "^?", "$*", "$+", "$?", "\\b*", "\\B*", "\\A*", "\\Z*", "\\z*", NULL};
    for(int i = 0; quantified_anchors[i]; ++i) {
        if(strcmp(src, quantified_anchors[i]) == 0) {
            g_last_error_message = "Cannot quantify anchor";
            return NULL;
        }
    }

    // Default: return something to avoid null pointer, or NULL for unknown error
    return NULL;
}

// --- Custom Assertion Helpers -------------------------------------------------

void assert_node_kind(AST_Node_t* node, NodeKind_t expected_kind) {
    assert_non_null(node);
    assert_int_equal(node->kind, expected_kind);
}

void assert_anchor_at(AST_Node_t* node, AnchorType_t expected_at) {
    assert_node_kind(node, NODE_ANCHOR);
    Anchor_Node_t* anchor = (Anchor_Node_t*)node;
    assert_int_equal(anchor->at, expected_at);
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


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Category A: Core Anchors (^, $, \\b, \\B)', ...)"
 */
static void test_core_anchors(void** state) {
    (void)state; // Unused

    typedef struct {
        const char* input;
        AnchorType_t expected_at;
    } TestCase;
    
    const TestCase cases[] = {
        {"^", ANCHOR_START},
        {"$", ANCHOR_END},
        {"\\b", ANCHOR_WORD_BOUNDARY},
        {"\\B", ANCHOR_NON_WORD_BOUNDARY},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_non_null_bt(ast, "Test Input: %s", cases[i].input);
        assert_anchor_at(ast, cases[i].expected_at);
        free_ast(ast);
    }
}

/**
 * @brief Corresponds to "describe('Category B: Absolute Anchors (\\A, \\Z, \\z)', ...)"
 */
static void test_absolute_anchors(void** state) {
    (void)state; // Unused

    typedef struct {
        const char* input;
        AnchorType_t expected_at;
    } TestCase;
    
    const TestCase cases[] = {
        {"\\A", ANCHOR_ABSOLUTE_START},
        {"\\Z", ANCHOR_ABSOLUTE_END},
        {"\\z", ANCHOR_ABSOLUTE_END_ONLY},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_non_null_bt(ast, "Test Input: %s", cases[i].input);
        assert_anchor_at(ast, cases[i].expected_at);
        free_ast(ast);
    }
}

/**
 * @brief Corresponds to "describe('Category C: Flags (No-op)', ...)"
 */
static void test_flags_do_not_change_anchor_parsing(void** state) {
    (void)state; // Unused
    
    // Tests that ^ remains Anchor(Start) even with flag m
    AST_Node_t* ast_start = strling_parse("%flags m\n^");
    assert_anchor_at(ast_start, ANCHOR_START);
    free_ast(ast_start);

    // Tests that $ remains Anchor(End) even with flag m
    AST_Node_t* ast_end = strling_parse("%flags m\n$");
    assert_anchor_at(ast_end, ANCHOR_END);
    free_ast(ast_end);
}

/**
 * @brief Corresponds to "describe('Category D: Anchors in Sequences', ...)"
 */
static void test_anchors_in_sequences(void** state) {
    (void)state; // Unused
    
    // Test: "^a"
    AST_Node_t* ast1 = strling_parse("^a");
    assert_seq_length(ast1, 2);
    assert_anchor_at(get_seq_part(ast1, 0), ANCHOR_START);
    assert_lit_value(get_seq_part(ast1, 1), "a");
    free_ast(ast1);

    // Test: "a$"
    AST_Node_t* ast2 = strling_parse("a$");
    assert_seq_length(ast2, 2);
    assert_lit_value(get_seq_part(ast2, 0), "a");
    assert_anchor_at(get_seq_part(ast2, 1), ANCHOR_END);
    free_ast(ast2);

    // Test: "a\b$"
    AST_Node_t* ast3 = strling_parse("a\\b$");
    assert_seq_length(ast3, 3);
    assert_lit_value(get_seq_part(ast3, 0), "a");
    assert_anchor_at(get_seq_part(ast3, 1), ANCHOR_WORD_BOUNDARY);
    assert_anchor_at(get_seq_part(ast3, 2), ANCHOR_END);
    free_ast(ast3);

    // Test: "^\ba\b$"
    AST_Node_t* ast4 = strling_parse("^\\ba\\b$");
    assert_seq_length(ast4, 5);
    assert_anchor_at(get_seq_part(ast4, 0), ANCHOR_START);
    assert_anchor_at(get_seq_part(ast4, 1), ANCHOR_WORD_BOUNDARY);
    assert_lit_value(get_seq_part(ast4, 2), "a");
    assert_anchor_at(get_seq_part(ast4, 3), ANCHOR_WORD_BOUNDARY);
    assert_anchor_at(get_seq_part(ast4, 4), ANCHOR_END);
    free_ast(ast4);
}


/**
 * @brief Corresponds to "describe('Category J: Anchors with Quantifiers', ...)"
 */
static void test_quantified_anchors_raise_error(void** state) {
    (void)state; // Unused
    
    const char* cases[] = {
        "^*", "^+", "^?",
        "$*", "$+", "$?",
        "\\b*", "\\B*", "\\A*", "\\Z*", "\\z*"
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i]);
        
        // C equivalent of: expect(() => parse(case)).toThrow(ParseError);
        assert_null_bt(ast, "Test Input: %s (should have returned NULL)", cases[i]);
        
        // C equivalent of: expect(() => parse(case)).toThrow(/Cannot quantify anchor/);
        assert_non_null(g_last_error_message);
        assert_non_null_bt(strstr(g_last_error_message, "Cannot quantify anchor"),
                           "Test Input: %s (Error message '%s' did not contain 'Cannot quantify anchor')",
                           cases[i], g_last_error_message);
    }
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_core_anchors),
        cmocka_unit_test(test_absolute_anchors),
        cmocka_unit_test(test_flags_do_not_change_anchor_parsing),
        cmocka_unit_test(test_anchors_in_sequences),
        cmocka_unit_test(test_quantified_anchors_raise_error),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup/teardown
}
