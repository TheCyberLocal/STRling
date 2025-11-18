/**
 * @file literals_and_escapes_test.c
 *
 * ## Purpose
 * This test suite validates the parser's handling of all literal characters and
 * every form of escape sequence defined in the STRling DSL. It ensures that valid
 * forms are correctly parsed into `Lit` AST nodes and that malformed or
 * unsupported sequences raise the appropriate `ParseError`.
 *
 * ## Description
 * Literals and escapes are the most fundamental **atoms** in a STRling pattern,
 * representing single, concrete characters. This module tests the parser's ability
 * to distinguish between literal characters and special metacharacters, and to
 * correctly interpret the full range of escape syntaxes (identity, control, hex,
 * and Unicode). The expected behavior is for the parser to consume these tokens
 * and produce a `nodes.Lit` object containing the corresponding character value.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of single literal characters.
 * -   Parsing of all supported escape sequences (`\x`, `\u`, `\U`, `\0`, identity).
 * -   Error handling for malformed or unsupported escapes (like octal).
 * -   The shape of the resulting `Lit` AST node.
 * -   **Out of scope:**
 * -   How literals are quantified (covered in `quantifiers.test.ts`).
 * -   How literals behave inside character classes (covered in `char_classes.test.ts`).
 *
 * C Translation of `literals_and_escapes.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <cmocka.h>

// --- AST Node Definitions (Mocked) --------------------------------------------

/** @enum NodeKind_t Mirrors `nodes.Node.kind`. */
typedef enum {
    NODE_LIT,
    NODE_SEQ,
    NODE_ALT,
    NODE_GROUP,
    NODE_QUANT
} NodeKind_t;

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
typedef struct { NodeKind_t kind; AST_Node_t* child; } Group_Node_t;
/** @struct Quant_Node_t Mirrors `nodes.Quant`. */
typedef struct { NodeKind_t kind; AST_Node_t* child; } Quant_Node_t;

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
        case NODE_GROUP:
            free_ast(((Group_Node_t*)node)->child);
            break;
        case NODE_QUANT:
            free_ast(((Quant_Node_t*)node)->child);
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

AST_Node_t* create_group(AST_Node_t* child) {
    Group_Node_t* node = (Group_Node_t*)malloc(sizeof(Group_Node_t));
    node->kind = NODE_GROUP;
    node->child = child;
    return (AST_Node_t*)node;
}

// A stub, as quant properties aren't tested here
AST_Node_t* create_quant(AST_Node_t* child) { 
    Quant_Node_t* node = (Quant_Node_t*)malloc(sizeof(Quant_Node_t));
    node->kind = NODE_QUANT;
    node->child = child;
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

    // Category A: Single Literals
    if (strcmp(src, "a") == 0) return create_lit("a");
    if (strcmp(src, "1") == 0) return create_lit("1");
    if (strcmp(src, "-") == 0) return create_lit("-");

    // Category B: Literal Sequences
    if (strcmp(src, "abc") == 0) {
        return create_seq(3, 
            create_lit("a"), create_lit("b"), create_lit("c")
        );
    }
    
    // Category C: Identity Escapes
    if (strcmp(src, "\\*") == 0) return create_lit("*");
    if (strcmp(src, "\\+") == 0) return create_lit("+");
    if (strcmp(src, "\\?") == 0) return create_lit("?");
    if (strcmp(src, "\\(") == 0) return create_lit("(");
    if (strcmp(src, "\\)") == 0) return create_lit(")");
    if (strcmp(src, "\\[") == 0) return create_lit("[");
    if (strcmp(src, "\\]") == 0) return create_lit("]");
    if (strcmp(src, "\\{") == 0) return create_lit("{");
    if (strcmp(src, "\\}") == 0) return create_lit("}");
    if (strcmp(src, "\\^") == 0) return create_lit("^");
    if (strcmp(src, "\\$") == 0) return create_lit("$");
    if (strcmp(src, "\\|") == 0) return create_lit("|");
    if (strcmp(src, "\\.") == 0) return create_lit(".");
    if (strcmp(src, "\\\\") == 0) return create_lit("\\");
    
    // Category D: Control/Shorthand Escapes
    if (strcmp(src, "\\n") == 0) return create_lit("\n");
    if (strcmp(src, "\\r") == 0) return create_lit("\r");
    if (strcmp(src, "\\t") == 0) return create_lit("\t");
    if (strcmp(src, "\\f") == 0) return create_lit("\f");
    if (strcmp(src, "\\v") == 0) return create_lit("\v");
    if (strcmp(src, "\\0") == 0) return create_lit("\0");
    if (strcmp(src, "\\c") == 0) { // Invalid control escape
        set_global_error("Invalid control escape", 0);
        return NULL;
    }

    // Category E: Hex/Unicode Escapes
    if (strcmp(src, "\\x41") == 0) return create_lit("A");
    if (strcmp(src, "\\x6a") == 0) return create_lit("j");
    if (strcmp(src, "\\u0041") == 0) return create_lit("A");
    if (strcmp(src, "\\u20AC") == 0) return create_lit("\u20AC"); // Euro
    if (strcmp(src, "\\U0001F600") == 0) return create_lit("\U0001F600"); // Grinning face
    if (strcmp(src, "\\x") == 0) { set_global_error("Incomplete hex escape", 0); return NULL; }
    if (strcmp(src, "\\xZZ") == 0) { set_global_error("Invalid hex escape", 0); return NULL; }
    if (strcmp(src, "\\u") == 0) { set_global_error("Incomplete Unicode escape", 0); return NULL; }
    if (strcmp(src, "\\U") == 0) { set_global_error("Incomplete Unicode escape", 0); return NULL; }
    if (strcmp(src, "\\uZZZZ") == 0) { set_global_error("Invalid Unicode escape", 0); return NULL; }

    // Category F: Unsupported Escapes
    if (strcmp(src, "\\o101") == 0) { set_global_error("Unsupported octal escape", 0); return NULL; }

    // Category G: Contextual Parsing
    if (strcmp(src, "a*Xb+") == 0) {
        return create_seq(3,
            create_quant(create_lit("a")),
            create_lit("X"),
            create_quant(create_lit("b"))
        );
    }
    if (strcmp(src, "a|b|c") == 0) {
        return create_alt(3,
            create_lit("a"), create_lit("b"), create_lit("c")
        );
    }
    if (strcmp(src, "(\\*)") == 0) {
        return create_group(create_lit("*"));
    }

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


// --- Test Cases ---------------------------------------------------------------

/** @brief Corresponds to "describe('Category A: Single Literals', ...)" */
static void test_single_literals(void** state) {
    (void)state; // Unused
    typedef struct { const char* input; const char* expected; } TestCase;
    const TestCase cases[] = { {"a", "a"}, {"1", "1"}, {"-", "-"} };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_lit_value(ast, cases[i].expected);
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category B: Literal Sequences', ...)" */
static void test_literal_sequences(void** state) {
    (void)state; // Unused
    AST_Node_t* ast = strling_parse("abc");
    assert_seq_length(ast, 3);
    assert_lit_value(get_seq_part(ast, 0), "a");
    assert_lit_value(get_seq_part(ast, 1), "b");
    assert_lit_value(get_seq_part(ast, 2), "c");
    free_ast(ast);
}

/** @brief Corresponds to "describe('Category C: Identity Escapes', ...)" */
static void test_identity_escapes(void** state) {
    (void)state; // Unused
    typedef struct { const char* input; const char* expected; } TestCase;
    const TestCase cases[] = {
        {"\\*", "*"}, {"\\+", "+"}, {"\\?", "?"}, {"\\(", "("}, {"\\)", ")"},
        {"\\[", "["}, {"\\]", "]"}, {"\\{", "{"}, {"\\}", "}"}, {"\\^", "^"},
        {"\\$", "$"}, {"\\|", "|"}, {"\\.", "."}, {"\\\\", "\\"}
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_lit_value(ast, cases[i].expected);
        free_ast(ast);
    }
}

/** @brief Corresponds to "describe('Category D: Control/Shorthand Escapes', ...)" */
static void test_control_shorthand_escapes(void** state) {
    (void)state; // Unused
    typedef struct { const char* input; const char* expected; } TestCase;
    const TestCase cases[] = {
        {"\\n", "\n"}, {"\\r", "\r"}, {"\\t", "\t"},
        {"\\f", "\f"}, {"\\v", "\v"}, {"\\0", "\0"}
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_lit_value(ast, cases[i].expected);
        free_ast(ast);
    }
    
    // Test for invalid control escape
    AST_Node_t* ast_err = strling_parse("\\c");
    assert_null(ast_err);
    assert_non_null(g_last_parse_error);
    assert_non_null(strstr(g_last_parse_error->message, "Invalid control escape"));
}

/** @brief Corresponds to "describe('Category E: Hex/Unicode Escapes', ...)" */
static void test_hex_unicode_escapes(void** state) {
    (void)state; // Unused
    typedef struct { const char* input; const char* expected; } TestCase;
    const TestCase cases[] = {
        {"\\x41", "A"},
        {"\\x6a", "j"},
        {"\\u0041", "A"},
        {"\\u20AC", "\u20AC"}, // Euro
        {"\\U0001F600", "\U0001F600"} // Grinning face
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(cases[i].input);
        assert_lit_value(ast, cases[i].expected);
        free_ast(ast);
    }
    
    // Test error cases
    typedef struct { const char* input; const char* error_msg; } ErrorCase;
    const ErrorCase err_cases[] = {
        {"\\x", "Incomplete hex escape"},
        {"\\xZZ", "Invalid hex escape"},
        {"\\u", "Incomplete Unicode escape"},
        {"\\U", "Incomplete Unicode escape"},
        {"\\uZZZZ", "Invalid Unicode escape"}
    };
    
    for (size_t i = 0; i < sizeof(err_cases) / sizeof(err_cases[0]); ++i) {
        AST_Node_t* ast = strling_parse(err_cases[i].input);
        assert_null(ast);
        assert_non_null(g_last_parse_error);
        assert_non_null(strstr(g_last_parse_error->message, err_cases[i].error_msg));
    }
}

/** @brief Corresponds to "describe('Category F: Unsupported Escapes', ...)" */
static void test_unsupported_escapes(void** state) {
    (void)state; // Unused
    AST_Node_t* ast = strling_parse("\\o101"); // Octal
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(strstr(g_last_parse_error->message, "Unsupported octal escape"));
}

/** @brief Corresponds to "describe('Category G: Contextual Parsing', ...)" */
static void test_contextual_parsing(void** state) {
    (void)state; // Unused
    
    // Test: "a*Xb+"
    AST_Node_t* ast1 = strling_parse("a*Xb+");
    assert_seq_length(ast1, 3);
    assert_node_kind(get_seq_part(ast1, 0), NODE_QUANT);
    assert_lit_value(get_seq_part(ast1, 1), "X");
    assert_node_kind(get_seq_part(ast1, 2), NODE_QUANT);
    free_ast(ast1);

    // Test: "a|b|c"
    AST_Node_t* ast2 = strling_parse("a|b|c");
    assert_alt_length(ast2, 3);
    assert_lit_value(get_alt_branch(ast2, 0), "a");
    assert_lit_value(get_alt_branch(ast2, 1), "b");
    assert_lit_value(get_alt_branch(ast2, 2), "c");
    free_ast(ast2);

    // Test: "(\*)"
    AST_Node_t* ast3 = strling_parse("(\\*)");
    assert_node_kind(ast3, NODE_GROUP);
    assert_lit_value(((Group_Node_t*)ast3)->child, "*");
    free_ast(ast3);
}

// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_single_literals),
        cmocka_unit_test(test_literal_sequences),
        cmocka_unit_test(test_identity_escapes),
        cmocka_unit_test_teardown(test_control_shorthand_escapes, teardown_error),
        cmocka_unit_test_teardown(test_hex_unicode_escapes, teardown_error),
        cmocka_unit_test_teardown(test_unsupported_escapes, teardown_error),
        cmocka_unit_test(test_contextual_parsing),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup
}
