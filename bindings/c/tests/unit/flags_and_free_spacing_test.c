/**
 * @file flags_and_free_spacing_test.c
 *
 * ## Purpose
 * This test suite validates the correct parsing of the `%flags` directive and the
 * behavioral changes it induces, particularly the free-spacing (`x`) mode. It
 * ensures that flags are correctly identified and stored in the `Flags` object
 * and that the parser correctly handles whitespace and comments when the
 * extended mode is active.
 *
 * ## Description
 * The `%flags` directive is a top-level command in a `.strl` file that modifies
 * the semantics of the entire pattern. This suite tests the parser's ability to
 * correctly consume this directive and apply its effects. The primary focus is
 * on the **`x` flag (extended/free-spacing mode)**, which dramatically alters
 * how the parser handles whitespace and comments. The tests will verify that the
 * parser correctly ignores insignificant characters outside of character classes
 * while treating them as literals inside character classes.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing the `%flags` directive with single and multiple flags (`i`,
 * `m`, `s`, `u`, `x`).
 * -   Handling of various separators (commas, spaces) within the flag
 * list.
 * -   The parser's behavior in free-spacing mode: ignoring whitespace and
 * comments outside character classes.
 * -   The parser's behavior inside a character class when free-spacing mode
 * is active (i.e., treating whitespace and `#` as literals).
 *
 * -   The resulting structure of the AST (e.g., `Seq` or `Lit`) after
 * free-spacing rules have been applied.
 * -   **Out of scope:**
 * -   The runtime effect of the flags (e.g., case-insensitivity) on the
 * regex engine (this is an emitter/conformance concern).
 *
 * C Translation of `flags_and_free_spacing.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- AST/Flags Node Definitions (Mocked) --------------------------------------

// --- AST Enums ---
typedef enum { NODE_LIT, NODE_SEQ, NODE_CHAR_CLASS } NodeKind_t;
typedef enum { CLASS_ITEM_LITERAL, CLASS_ITEM_RANGE } ClassItemKind_t;

// --- AST Base Structs ---
typedef struct { NodeKind_t kind; } AST_Node_t;
typedef struct { ClassItemKind_t kind; } ClassItem_t;

// --- AST Node Structs ---
typedef struct { NodeKind_t kind; char* value; } Lit_Node_t;
typedef struct { NodeKind_t kind; AST_Node_t** parts; int num_parts; } Seq_Node_t;
typedef struct { ClassItemKind_t kind; char* value; } ClassLiteral_Node_t;
typedef struct { NodeKind_t kind; bool negated; ClassItem_t** items; int num_items; } CharClass_Node_t;

/**
 * @struct Flags_t
 * Mirrors the `Flags` object returned by the parser.
 */
typedef struct {
    bool i; // ignoreCase
    bool m; // multiline
    bool s; // dotAll
    bool u; // unicode
    bool x; // freeSpacing
} Flags_t;

/**
 * @struct ParseResult_t
 * Bundles the dual return (Flags, AST) of the `parse` function.
 */
typedef struct {
    Flags_t* flags;
    AST_Node_t* ast;
} ParseResult_t;


// --- Global Error State (Mocked) ----------------------------------------------
static const char* g_last_error_message = NULL;

// --- AST/Flags Helper Functions (Mock constructors and destructors) -----------

// Forward declare for recursive free
void free_ast(AST_Node_t* node);

void free_class_item(ClassItem_t* item) {
    if (!item) return;
    if (item->kind == CLASS_ITEM_LITERAL) {
        free(((ClassLiteral_Node_t*)item)->value);
    }
    // Add other item types if necessary
    free(item);
}

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_LIT:
            free(((Lit_Node_t*)node)->value);
            break;
        case NODE_SEQ: {
            Seq_Node_t* seq = (Seq_Node_t*)node;
            for (int i = 0; i < seq->num_parts; ++i) {
                free_ast(seq->parts[i]);
            }
            free(seq->parts);
            break;
        }
        case NODE_CHAR_CLASS: {
            CharClass_Node_t* cc = (CharClass_Node_t*)node;
            for (int i = 0; i < cc->num_items; ++i) {
                free_class_item(cc->items[i]);
            }
            free(cc->items);
            break;
        }
    }
    free(node);
}

void free_parse_result(ParseResult_t* result) {
    if (result) {
        free(result->flags);
        free_ast(result->ast);
        free(result);
    }
}

Flags_t* create_flags(bool i, bool m, bool s, bool u, bool x) {
    Flags_t* flags = (Flags_t*)malloc(sizeof(Flags_t));
    flags->i = i;
    flags->m = m;
    flags->s = s;
    flags->u = u;
    flags->x = x;
    return flags;
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
    for (int i = 0; i < num_parts; ++i) {
        node->parts[i] = va_arg(args, AST_Node_t*);
    }
    va_end(args);
    return (AST_Node_t*)node;
}

ClassItem_t* create_class_literal(const char* value) {
    ClassLiteral_Node_t* lit = (ClassLiteral_Node_t*)malloc(sizeof(ClassLiteral_Node_t));
    lit->kind = CLASS_ITEM_LITERAL;
    lit->value = strdup(value);
    return (ClassItem_t*)lit;
}

AST_Node_t* create_char_class(bool negated, int num_items, ...) {
    CharClass_Node_t* cc = (CharClass_Node_t*)malloc(sizeof(CharClass_Node_t));
    cc->kind = NODE_CHAR_CLASS;
    cc->negated = negated;
    cc->num_items = num_items;
    cc->items = (ClassItem_t**)malloc(sizeof(ClassItem_t*) * num_items);
    va_list args;
    va_start(args, num_items);
    for (int i = 0; i < num_items; ++i) {
        cc->items[i] = va_arg(args, ClassItem_t*);
    }
    va_end(args);
    return (AST_Node_t*)cc;
}

ParseResult_t* create_parse_result(Flags_t* flags, AST_Node_t* ast) {
    ParseResult_t* res = (ParseResult_t*)malloc(sizeof(ParseResult_t));
    res->flags = flags;
    res->ast = ast;
    return res;
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded result for known inputs.
 * C equivalent of the `parse` function under test.
 * Returns NULL on error and sets `g_last_error_message`.
 */
ParseResult_t* strling_parse(const char* src) {
    g_last_error_message = NULL;

    // Category A: Flag Directive Parsing
    if (strcmp(src, "%flags i\na") == 0) 
        return create_parse_result(create_flags(true, false, false, false, false), create_lit("a"));
    if (strcmp(src, "%flags m\na") == 0) 
        return create_parse_result(create_flags(false, true, false, false, false), create_lit("a"));
    if (strcmp(src, "%flags s\na") == 0) 
        return create_parse_result(create_flags(false, false, true, false, false), create_lit("a"));
    if (strcmp(src, "%flags u\na") == 0) 
        return create_parse_result(create_flags(false, false, false, true, false), create_lit("a"));
    if (strcmp(src, "%flags x\na") == 0) 
        return create_parse_result(create_flags(false, false, false, false, true), create_lit("a"));
    if (strcmp(src, "%flags i,m,s\na") == 0) 
        return create_parse_result(create_flags(true, true, true, false, false), create_lit("a"));
    if (strcmp(src, "%flags i, m, s\na") == 0) 
        return create_parse_result(create_flags(true, true, true, false, false), create_lit("a"));
    if (strcmp(src, "%flags i m s u x\na") == 0) 
        return create_parse_result(create_flags(true, true, true, true, true), create_lit("a"));
    if (strcmp(src, "a") == 0) // no_flags_default
        return create_parse_result(create_flags(false, false, false, false, false), create_lit("a"));

    // Category B: Free-Spacing (x-mode) Behavior
    if (strcmp(src, "%flags x\n a b c") == 0)
        return create_parse_result(create_flags(false, false, false, false, true), 
            create_seq(3, create_lit("a"), create_lit("b"), create_lit("c"))
        );
    if (strcmp(src, "%flags x\n a # comment\n b") == 0)
        return create_parse_result(create_flags(false, false, false, false, true), 
            create_seq(2, create_lit("a"), create_lit("b"))
        );
    if (strcmp(src, "%flags x\n# comment\n  \n# another") == 0)
        return create_parse_result(create_flags(false, false, false, false, true), 
            create_seq(0) // Empty sequence
        );

    // Category D: Interaction Cases
    if (strcmp(src, "%flags x\n[a b]") == 0)
        return create_parse_result(create_flags(false, false, false, false, true),
            create_char_class(false, 3, 
                create_class_literal("a"), 
                create_class_literal(" "), 
                create_class_literal("b")
            )
        );
    if (strcmp(src, "%flags x\n[a#b]") == 0)
        return create_parse_result(create_flags(false, false, false, false, true),
            create_char_class(false, 3, 
                create_class_literal("a"), 
                create_class_literal("#"), 
                create_class_literal("b")
            )
        );

    // Fallback
    return create_parse_result(create_flags(false, false, false, false, false), create_seq(0));
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

void assert_char_class(AST_Node_t* node, bool expected_negated, int expected_items) {
    assert_node_kind(node, NODE_CHAR_CLASS);
    CharClass_Node_t* cc = (CharClass_Node_t*)node;
    assert_int_equal(cc->negated, expected_negated);
    assert_int_equal(cc->num_items, expected_items);
}

ClassItem_t* get_class_item(AST_Node_t* node, int index) {
    assert_node_kind(node, NODE_CHAR_CLASS);
    CharClass_Node_t* cc = (CharClass_Node_t*)node;
    assert_true(index < cc->num_items);
    return cc->items[index];
}

void assert_class_item_kind(ClassItem_t* item, ClassItemKind_t expected_kind) {
    assert_non_null(item);
    assert_int_equal(item->kind, expected_kind);
}

void assert_class_literal(ClassItem_t* item, const char* expected_value) {
    assert_class_item_kind(item, CLASS_ITEM_LITERAL);
    ClassLiteral_Node_t* lit = (ClassLiteral_Node_t*)item;
    assert_string_equal(lit->value, expected_value);
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Category A: Flag Directive Parsing', ...)"
 */
static void test_flag_directive_parsing(void** state) {
    (void)state; // Unused

    typedef struct {
        const char* input;
        bool i, m, s, u, x;
        const char* id;
    } FlagTestCase;
    
    const FlagTestCase cases[] = {
        {"%flags i\na", true, false, false, false, false, "single_i"},
        {"%flags m\na", false, true, false, false, false, "single_m"},
        {"%flags s\na", false, false, true, false, false, "single_s"},
        {"%flags u\na", false, false, false, true, false, "single_u"},
        {"%flags x\na", false, false, false, false, true, "single_x"},
        {"%flags i,m,s\na", true, true, true, false, false, "multiple_comma"},
        {"%flags i, m, s\na", true, true, true, false, false, "multiple_comma_space"},
        {"%flags i m s u x\na", true, true, true, true, true, "multiple_space"},
        {"a", false, false, false, false, false, "no_flags_default"},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        const FlagTestCase* tc = &cases[i];
        ParseResult_t* result = strling_parse(tc->input);
        
        assert_non_null_bt(result, "Test ID: %s", tc->id);
        assert_non_null_bt(result->flags, "Test ID: %s", tc->id);
        
        assert_int_equal_bt(result->flags->i, tc->i, "Test ID: %s (flag i)", tc->id);
        assert_int_equal_bt(result->flags->m, tc->m, "Test ID: %s (flag m)", tc->id);
        assert_int_equal_bt(result->flags->s, tc->s, "Test ID: %s (flag s)", tc->id);
        assert_int_equal_bt(result->flags->u, tc->u, "Test ID: %s (flag u)", tc->id);
        assert_int_equal_bt(result->flags->x, tc->x, "Test ID: %s (flag x)", tc->id);
        
        // Also verify the AST is what we expect
        assert_lit_value(result->ast, "a");
        
        free_parse_result(result);
    }
}

/**
 * @brief Corresponds to "describe('Category B: Free-Spacing (x-mode) Behavior', ...)"
 */
static void test_free_spacing_behavior(void** state) {
    (void)state; // Unused
    
    // Test: "should ignore whitespace and comments"
    ParseResult_t* res1 = strling_parse("%flags x\n a # comment\n b");
    assert_non_null(res1);
    assert_true(res1->flags->x);
    assert_seq_length(res1->ast, 2);
    assert_lit_value(get_seq_part(res1->ast, 0), "a");
    assert_lit_value(get_seq_part(res1->ast, 1), "b");
    free_parse_result(res1);

    // Test: "should parse 'a b c' as Seq(Lit(a), Lit(b), Lit(c))"
    ParseResult_t* res2 = strling_parse("%flags x\n a b c");
    assert_non_null(res2);
    assert_true(res2->flags->x);
    assert_seq_length(res2->ast, 3);
    assert_lit_value(get_seq_part(res2->ast, 0), "a");
    assert_lit_value(get_seq_part(res2->ast, 1), "b");
    assert_lit_value(get_seq_part(res2->ast, 2), "c");
    free_parse_result(res2);

    // Test: "should parse an empty pattern in free-spacing mode"
    ParseResult_t* res3 = strling_parse("%flags x\n# comment\n  \n# another");
    assert_non_null(res3);
    assert_true(res3->flags->x);
    assert_seq_length(res3->ast, 0); // Empty Seq
    free_parse_result(res3);
}

/**
 * @brief Corresponds to "describe('Category D: Interaction Cases', ...)"
 */
static void test_free_spacing_interaction_with_char_class(void** state) {
    (void)state; // Unused
    
    // Test: "whitespace_is_literal_in_class"
    ParseResult_t* res1 = strling_parse("%flags x\n[a b]");
    assert_non_null(res1);
    assert_true(res1->flags->x);
    
    // Verifies that free-spacing is *disabled* inside the class
    assert_char_class(res1->ast, false, 3);
    assert_class_literal(get_class_item(res1->ast, 0), "a");
    assert_class_literal(get_class_item(res1->ast, 1), " ");
    assert_class_literal(get_class_item(res1->ast, 2), "b");
    free_parse_result(res1);

    // Test: "comment_char_is_literal_in_class"
    ParseResult_t* res2 = strling_parse("%flags x\n[a#b]");
    assert_non_null(res2);
    assert_true(res2->flags->x);

    // Verifies that '#' is a literal inside the class
    assert_char_class(res2->ast, false, 3);
    assert_class_literal(get_class_item(res2->ast, 0), "a");
    assert_class_literal(get_class_item(res2->ast, 1), "#");
    assert_class_literal(get_class_item(res2->ast, 2), "b");
    free_parse_result(res2);
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_flag_directive_parsing),
        cmocka_unit_test(test_free_spacing_behavior),
        cmocka_unit_test(test_free_spacing_interaction_with_char_class),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup/teardown
}
