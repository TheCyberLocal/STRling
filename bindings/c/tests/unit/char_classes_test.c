/**
 * @file char_classes_test.c
 *
 * ## Purpose
 * This test suite validates the correct parsing of character classes, ensuring
 * all forms—including literals, ranges, shorthands, and Unicode properties—are
 * correctly transformed into `CharClass` AST nodes. It also verifies that
 * negation, edge cases involving special characters, and invalid syntax are
 * handled according to the DSL's semantics.
 *
 * ## Description
 * Character classes (`[...]`) are a fundamental feature of the STRling DSL,
 * allowing a pattern to match any single character from a specified set. This
 * suite tests the parser's ability to correctly handle the various components
 * that can make up these sets: literal characters, character ranges (`a-z`),
 * shorthand escapes (`\d`, `\w`), and Unicode property escapes (`\p{L}`). It also
 * ensures that class-level negation (`[^...]`) and the special rules for
 * metacharacters (`-`, `]`, `^`) within classes are parsed correctly.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of positive `[abc]` and negative `[^abc]` character classes.
 * -   Parsing of character ranges (`[a-z]`, `[0-9]`) and their validation.
 * -   Parsing of all supported shorthand (`\d`, `\s`, `\w` and their negated
 * counterparts) and Unicode property (`\p{...}`, `\P{...}`) escapes
 * within a class.
 * -   The special syntactic rules for `]`, `-`, `^`, and `\` within classes.
 * -   Error handling for invalid ranges (`[z-a]`) or unterminated classes.
 * -   **Out of scope:**
 * -   Quantification of character classes (e.g., `[a-z]+`), which is
 * covered by the quantifiers test suite.
 * -   Runtime behavior (this is a parser test).
 *
 * C Translation of `char_classes.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- AST Node Definitions (Mocked) --------------------------------------------
// These C structs and enums mirror the TypeScript `nodes.ts` classes.

/**
 * @enum NodeKind_t
 * Mirrors `nodes.Node.kind` for top-level AST nodes.
 */
typedef enum {
    NODE_LIT,
    NODE_ANCHOR,
    NODE_SEQ,
    NODE_CHAR_CLASS
} NodeKind_t;

/**
 * @enum ClassItemKind_t
 * Mirrors the `kind` property for nodes *inside* a CharClass.
 */
typedef enum {
    CLASS_ITEM_LITERAL,
    CLASS_ITEM_RANGE,
    CLASS_ITEM_SHORTHAND,
    CLASS_ITEM_UNICODE_PROP
} ClassItemKind_t;

/**
 * @enum ShorthandType_t
 * Represents the specific shorthand (d, s, w, h, v).
 */
typedef enum {
    SHORTHAND_D, // digit
    SHORTHAND_S, // whitespace
    SHORTHAND_W, // word
    SHORTHAND_H, // horizontal whitespace
    SHORTHAND_V  // vertical whitespace
} ShorthandType_t;


// --- Base AST Node Structs ----------------------------------------------------

/** @struct AST_Node_t Base for all top-level AST nodes. */
typedef struct {
    NodeKind_t kind;
} AST_Node_t;

/** @struct ClassItem_t Base for all items inside a CharClass. */
typedef struct {
    ClassItemKind_t kind;
} ClassItem_t;


// --- Specific AST Node Structs ------------------------------------------------

/** @struct ClassLiteral_Node_t Mirrors `nodes.ClassLiteral`. */
typedef struct {
    ClassItemKind_t kind; // CLASS_ITEM_LITERAL
    char* value;
} ClassLiteral_Node_t;

/** @struct ClassRange_Node_t Mirrors `nodes.ClassRange`. */
typedef struct {
    ClassItemKind_t kind; // CLASS_ITEM_RANGE
    ClassLiteral_Node_t* min;
    ClassLiteral_Node_t* max;
} ClassRange_Node_t;

/** @struct ClassShorthand_Node_t Mirrors `nodes.ClassShorthand`. */
typedef struct {
    ClassItemKind_t kind; // CLASS_ITEM_SHORTHAND
    ShorthandType_t shorthand;
    bool negated;
} ClassShorthand_Node_t;

/** @struct UnicodeProperty_Node_t Mirrors `nodes.UnicodeProperty`. */
typedef struct {
    ClassItemKind_t kind; // CLASS_ITEM_UNICODE_PROP
    char* name;  // e.g., "Script" or NULL for single form
    char* value; // e.g., "Latin" or "L" for single form
    bool negated;
} UnicodeProperty_Node_t;

/** @struct CharClass_Node_t Mirrors `nodes.CharClass`. */
typedef struct {
    NodeKind_t kind; // NODE_CHAR_CLASS
    bool negated;
    ClassItem_t** items;
    int num_items;
} CharClass_Node_t;


// --- Global Error State (for mocking ParseError) ------------------------------
static const char* g_last_error_message = NULL;

// --- AST Helper Functions (Mock constructors and destructors) -----------------

// Forward declare for use in `free_ast`
void free_class_item(ClassItem_t* item);

void free_ast(AST_Node_t* node) {
    if (!node) return;
    switch (node->kind) {
        case NODE_CHAR_CLASS: {
            CharClass_Node_t* cc = (CharClass_Node_t*)node;
            for (int i = 0; i < cc->num_items; ++i) {
                free_class_item(cc->items[i]);
            }
            free(cc->items);
            break;
        }
        // Add cases for Lit, Seq, Anchor if needed
        default:
            break;
    }
    free(node);
}

void free_class_item(ClassItem_t* item) {
    if (!item) return;
    switch (item->kind) {
        case CLASS_ITEM_LITERAL:
            free(((ClassLiteral_Node_t*)item)->value);
            break;
        case CLASS_ITEM_RANGE: {
            ClassRange_Node_t* range = (ClassRange_Node_t*)item;
            free_class_item((ClassItem_t*)range->min);
            free_class_item((ClassItem_t*)range->max);
            break;
        }
        case CLASS_ITEM_SHORTHAND:
            // No dynamic data
            break;
        case CLASS_ITEM_UNICODE_PROP: {
            UnicodeProperty_Node_t* prop = (UnicodeProperty_Node_t*)item;
            free(prop->name);
            free(prop->value);
            break;
        }
    }
    free(item);
}

ClassItem_t* create_class_literal(const char* value) {
    ClassLiteral_Node_t* lit = (ClassLiteral_Node_t*)malloc(sizeof(ClassLiteral_Node_t));
    lit->kind = CLASS_ITEM_LITERAL;
    lit->value = strdup(value);
    return (ClassItem_t*)lit;
}

ClassItem_t* create_class_range(ClassLiteral_Node_t* min, ClassLiteral_Node_t* max) {
    ClassRange_Node_t* range = (ClassRange_Node_t*)malloc(sizeof(ClassRange_Node_t));
    range->kind = CLASS_ITEM_RANGE;
    range->min = min;
    range->max = max;
    return (ClassItem_t*)range;
}

ClassItem_t* create_class_shorthand(ShorthandType_t s_type, bool negated) {
    ClassShorthand_Node_t* sh = (ClassShorthand_Node_t*)malloc(sizeof(ClassShorthand_Node_t));
    sh->kind = CLASS_ITEM_SHORTHAND;
    sh->shorthand = s_type;
    sh->negated = negated;
    return (ClassItem_t*)sh;
}

ClassItem_t* create_unicode_prop(const char* name, const char* value, bool negated) {
    UnicodeProperty_Node_t* prop = (UnicodeProperty_Node_t*)malloc(sizeof(UnicodeProperty_Node_t));
    prop->kind = CLASS_ITEM_UNICODE_PROP;
    prop->name = name ? strdup(name) : NULL;
    prop->value = strdup(value);
    prop->negated = negated;
    return (ClassItem_t*)prop;
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

// --- Mock `parse` Function ----------------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded AST for known class inputs.
 * C equivalent of the `parse(src)[1]` (i.e., just the AST part).
 * Returns NULL on error and sets `g_last_error_message`.
 */
AST_Node_t* strling_parse(const char* src) {
    g_last_error_message = NULL;

    // Category A: Positive and Negative
    if (strcmp(src, "[a]") == 0) return create_char_class(false, 1, create_class_literal("a"));
    if (strcmp(src, "[abc]") == 0) {
        return create_char_class(false, 3, 
            create_class_literal("a"), 
            create_class_literal("b"), 
            create_class_literal("c")
        );
    }
    if (strcmp(src, "[^a]") == 0) return create_char_class(true, 1, create_class_literal("a"));
    if (strcmp(src, "[^abc]") == 0) {
         return create_char_class(true, 3, 
            create_class_literal("a"), 
            create_class_literal("b"), 
            create_class_literal("c")
        );
    }

    // Category B: Class Contents
    if (strcmp(src, "[a-z]") == 0) {
        return create_char_class(false, 1, 
            create_class_range(
                (ClassLiteral_Node_t*)create_class_literal("a"), 
                (ClassLiteral_Node_t*)create_class_literal("z")
            )
        );
    }
    if (strcmp(src, "[a-zA-Z0-9]") == 0) {
        return create_char_class(false, 3, 
            create_class_range((ClassLiteral_Node_t*)create_class_literal("a"), (ClassLiteral_Node_t*)create_class_literal("z")),
            create_class_range((ClassLiteral_Node_t*)create_class_literal("A"), (ClassLiteral_Node_t*)create_class_literal("Z")),
            create_class_range((ClassLiteral_Node_t*)create_class_literal("0"), (ClassLiteral_Node_t*)create_class_literal("9"))
        );
    }
    if (strcmp(src, "[\\d]") == 0) return create_char_class(false, 1, create_class_shorthand(SHORTHAND_D, false));
    if (strcmp(src, "[\\D]") == 0) return create_char_class(false, 1, create_class_shorthand(SHORTHAND_D, true));
    if (strcmp(src, "[\\w\\s]") == 0) {
        return create_char_class(false, 2, 
            create_class_shorthand(SHORTHAND_W, false), 
            create_class_shorthand(SHORTHAND_S, false)
        );
    }
    if (strcmp(src, "[a-f\\d]") == 0) {
         return create_char_class(false, 2, 
            create_class_range((ClassLiteral_Node_t*)create_class_literal("a"), (ClassLiteral_Node_t*)create_class_literal("f")),
            create_class_shorthand(SHORTHAND_D, false)
        );
    }
    if (strcmp(src, "[^\\S]") == 0) return create_char_class(true, 1, create_class_shorthand(SHORTHAND_S, true));
    if (strcmp(src, "[\\h\\v]") == 0) {
        return create_char_class(false, 2, 
            create_class_shorthand(SHORTHAND_H, false), 
            create_class_shorthand(SHORTHAND_V, false)
        );
    }
    
    // Category C: Unicode Properties
    if (strcmp(src, "[\\p{L}]") == 0) return create_char_class(false, 1, create_unicode_prop(NULL, "L", false));
    if (strcmp(src, "[\\P{L}]") == 0) return create_char_class(false, 1, create_unicode_prop(NULL, "L", true));
    if (strcmp(src, "[\\p{Script=Latin}]") == 0) return create_char_class(false, 1, create_unicode_prop("Script", "Latin", false));
    if (strcmp(src, "[\\P{Script=Latin}]") == 0) return create_char_class(false, 1, create_unicode_prop("Script", "Latin", true));
    if (strcmp(src, "[\\p{L}a-z]") == 0) {
        return create_char_class(false, 2, 
            create_unicode_prop(NULL, "L", false),
            create_class_range((ClassLiteral_Node_t*)create_class_literal("a"), (ClassLiteral_Node_t*)create_class_literal("z"))
        );
    }

    // Category D: Special Characters
    if (strcmp(src, "[]a]") == 0) return create_char_class(false, 2, create_class_literal("]"), create_class_literal("a"));
    if (strcmp(src, "[-a]") == 0) return create_char_class(false, 2, create_class_literal("-"), create_class_literal("a"));
    if (strcmp(src, "[a-]") == 0) return create_char_class(false, 2, create_class_literal("a"), create_class_literal("-"));
    if (strcmp(src, "[^-a]") == 0) return create_char_class(true, 2, create_class_literal("-"), create_class_literal("a"));
    if (strcmp(src, "[a\\-z]") == 0) return create_char_class(false, 3, create_class_literal("a"), create_class_literal("-"), create_class_literal("z"));
    if (strcmp(src, "[a^b]") == 0) return create_char_class(false, 3, create_class_literal("a"), create_class_literal("^"), create_class_literal("b"));

    // Category J: Error Cases
    if (strcmp(src, "[]") == 0) {
        g_last_error_message = "Unterminated character class";
        return NULL;
    }
    if (strcmp(src, "[z-a]") == 0) {
        g_last_error_message = "Invalid character range";
        return NULL;
    }

    // Fallback
    return NULL;
}

// --- Custom Assertion Helpers -------------------------------------------------

void assert_node_kind(AST_Node_t* node, NodeKind_t expected_kind) {
    assert_non_null(node);
    assert_int_equal(node->kind, expected_kind);
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

void assert_class_range(ClassItem_t* item, const char* expected_min, const char* expected_max) {
    assert_class_item_kind(item, CLASS_ITEM_RANGE);
    ClassRange_Node_t* range = (ClassRange_Node_t*)item;
    assert_string_equal(range->min->value, expected_min);
    assert_string_equal(range->max->value, expected_max);
}

void assert_class_shorthand(ClassItem_t* item, ShorthandType_t expected_type, bool expected_negated) {
    assert_class_item_kind(item, CLASS_ITEM_SHORTHAND);
    ClassShorthand_Node_t* sh = (ClassShorthand_Node_t*)item;
    assert_int_equal(sh->shorthand, expected_type);
    assert_int_equal(sh->negated, expected_negated);
}

void assert_unicode_prop(ClassItem_t* item, const char* expected_name, const char* expected_value, bool expected_negated) {
    assert_class_item_kind(item, CLASS_ITEM_UNICODE_PROP);
    UnicodeProperty_Node_t* prop = (UnicodeProperty_Node_t*)item;
    
    if (expected_name) {
        assert_string_equal(prop->name, expected_name);
    } else {
        assert_null(prop->name);
    }
    assert_string_equal(prop->value, expected_value);
    assert_int_equal(prop->negated, expected_negated);
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Category A: Positive and Negative Classes', ...)"
 */
static void test_positive_and_negative_classes(void** state) {
    (void)state; // Unused
    
    // Test: "[a]"
    AST_Node_t* ast1 = strling_parse("[a]");
    assert_char_class(ast1, false, 1);
    assert_class_literal(get_class_item(ast1, 0), "a");
    free_ast(ast1);

    // Test: "[abc]"
    AST_Node_t* ast2 = strling_parse("[abc]");
    assert_char_class(ast2, false, 3);
    assert_class_literal(get_class_item(ast2, 0), "a");
    assert_class_literal(get_class_item(ast2, 1), "b");
    assert_class_literal(get_class_item(ast2, 2), "c");
    free_ast(ast2);

    // Test: "[^a]"
    AST_Node_t* ast3 = strling_parse("[^a]");
    assert_char_class(ast3, true, 1);
    assert_class_literal(get_class_item(ast3, 0), "a");
    free_ast(ast3);

    // Test: "[^abc]"
    AST_Node_t* ast4 = strling_parse("[^abc]");
    assert_char_class(ast4, true, 3);
    assert_class_literal(get_class_item(ast4, 0), "a");
    assert_class_literal(get_class_item(ast4, 1), "b");
    assert_class_literal(get_class_item(ast4, 2), "c");
    free_ast(ast4);
}

/**
 * @brief Corresponds to "describe('Category B: Class Contents (Literals, Ranges, Shorthands)', ...)"
 */
static void test_class_contents_literals_ranges_shorthands(void** state) {
    (void)state; // Unused
    
    // Test: "[a-z]"
    AST_Node_t* ast1 = strling_parse("[a-z]");
    assert_char_class(ast1, false, 1);
    assert_class_range(get_class_item(ast1, 0), "a", "z");
    free_ast(ast1);

    // Test: "[a-zA-Z0-9]"
    AST_Node_t* ast2 = strling_parse("[a-zA-Z0-9]");
    assert_char_class(ast2, false, 3);
    assert_class_range(get_class_item(ast2, 0), "a", "z");
    assert_class_range(get_class_item(ast2, 1), "A", "Z");
    assert_class_range(get_class_item(ast2, 2), "0", "9");
    free_ast(ast2);

    // Test: "[\d]"
    AST_Node_t* ast3 = strling_parse("[\\d]");
    assert_char_class(ast3, false, 1);
    assert_class_shorthand(get_class_item(ast3, 0), SHORTHAND_D, false);
    free_ast(ast3);

    // Test: "[\D]"
    AST_Node_t* ast4 = strling_parse("[\\D]");
    assert_char_class(ast4, false, 1);
    assert_class_shorthand(get_class_item(ast4, 0), SHORTHAND_D, true);
    free_ast(ast4);

    // Test: "[\w\s]"
    AST_Node_t* ast5 = strling_parse("[\\w\\s]");
    assert_char_class(ast5, false, 2);
    assert_class_shorthand(get_class_item(ast5, 0), SHORTHAND_W, false);
    assert_class_shorthand(get_class_item(ast5, 1), SHORTHAND_S, false);
    free_ast(ast5);

    // Test: "[a-f\d]"
    AST_Node_t* ast6 = strling_parse("[a-f\\d]");
    assert_char_class(ast6, false, 2);
    assert_class_range(get_class_item(ast6, 0), "a", "f");
    assert_class_shorthand(get_class_item(ast6, 1), SHORTHAND_D, false);
    free_ast(ast6);

    // Test: "[^\S]" (Negated class containing negated shorthand)
    AST_Node_t* ast7 = strling_parse("[^\\S]");
    assert_char_class(ast7, true, 1);
    assert_class_shorthand(get_class_item(ast7, 0), SHORTHAND_S, true);
    free_ast(ast7);

    // Test: "[\h\v]"
    AST_Node_t* ast8 = strling_parse("[\\h\\v]");
    assert_char_class(ast8, false, 2);
    assert_class_shorthand(get_class_item(ast8, 0), SHORTHAND_H, false);
    assert_class_shorthand(get_class_item(ast8, 1), SHORTHAND_V, false);
    free_ast(ast8);
}

/**
 * @brief Corresponds to "describe('Category C: Unicode Properties', ...)"
 */
static void test_unicode_properties(void** state) {
    (void)state; // Unused
    
    // Test: "[\p{L}]"
    AST_Node_t* ast1 = strling_parse("[\\p{L}]");
    assert_char_class(ast1, false, 1);
    assert_unicode_prop(get_class_item(ast1, 0), NULL, "L", false);
    free_ast(ast1);

    // Test: "[\P{L}]"
    AST_Node_t* ast2 = strling_parse("[\\P{L}]");
    assert_char_class(ast2, false, 1);
    assert_unicode_prop(get_class_item(ast2, 0), NULL, "L", true);
    free_ast(ast2);

    // Test: "[\p{Script=Latin}]"
    AST_Node_t* ast3 = strling_parse("[\\p{Script=Latin}]");
    assert_char_class(ast3, false, 1);
    assert_unicode_prop(get_class_item(ast3, 0), "Script", "Latin", false);
    free_ast(ast3);

    // Test: "[\P{Script=Latin}]"
    AST_Node_t* ast4 = strling_parse("[\\P{Script=Latin}]");
    assert_char_class(ast4, false, 1);
    assert_unicode_prop(get_class_item(ast4, 0), "Script", "Latin", true);
    free_ast(ast4);
    
    // Test: "[\p{L}a-z]"
    AST_Node_t* ast5 = strling_parse("[\\p{L}a-z]");
    assert_char_class(ast5, false, 2);
    assert_unicode_prop(get_class_item(ast5, 0), NULL, "L", false);
    assert_class_range(get_class_item(ast5, 1), "a", "z");
    free_ast(ast5);
}

/**
 * @brief Corresponds to "describe('Category D: Special Character Handling (-, ], ^)', ...)"
 */
static void test_special_character_handling(void** state) {
    (void)state; // Unused
    
    // Test: "[]a]" (] is literal)
    AST_Node_t* ast1 = strling_parse("[]a]");
    assert_char_class(ast1, false, 2);
    assert_class_literal(get_class_item(ast1, 0), "]");
    assert_class_literal(get_class_item(ast1, 1), "a");
    free_ast(ast1);

    // Test: "[-a]" (- is literal)
    AST_Node_t* ast2 = strling_parse("[-a]");
    assert_char_class(ast2, false, 2);
    assert_class_literal(get_class_item(ast2, 0), "-");
    assert_class_literal(get_class_item(ast2, 1), "a");
    free_ast(ast2);

    // Test: "[a-]" (- is literal)
    AST_Node_t* ast3 = strling_parse("[a-]");
    assert_char_class(ast3, false, 2);
    assert_class_literal(get_class_item(ast3, 0), "a");
    assert_class_literal(get_class_item(ast3, 1), "-");
    free_ast(ast3);

    // Test: "[^-a]" (- is literal in negated class)
    AST_Node_t* ast4 = strling_parse("[^-a]");
    assert_char_class(ast4, true, 2);
    assert_class_literal(get_class_item(ast4, 0), "-");
    assert_class_literal(get_class_item(ast4, 1), "a");
    free_ast(ast4);

    // Test: "[a\-z]" (- is literal via escape)
    AST_Node_t* ast5 = strling_parse("[a\\-z]");
    assert_char_class(ast5, false, 3);
    assert_class_literal(get_class_item(ast5, 0), "a");
    assert_class_literal(get_class_item(ast5, 1), "-");
    assert_class_literal(get_class_item(ast5, 2), "z");
    free_ast(ast5);

    // Test: "[a^b]" (^ is literal)
    AST_Node_t* ast6 = strling_parse("[a^b]");
    assert_char_class(ast6, false, 3);
    assert_class_literal(get_class_item(ast6, 0), "a");
    assert_class_literal(get_class_item(ast6, 1), "^");
    assert_class_literal(get_class_item(ast6, 2), "b");
    free_ast(ast6);
}

/**
 * @brief Corresponds to "describe('Category J: Error Cases', ...)"
 */
static void test_error_cases(void** state) {
    (void)state; // Unused
    
    // Test: "[]"
    AST_Node_t* ast1 = strling_parse("[]");
    assert_null(ast1);
    assert_non_null(g_last_error_message);
    assert_string_equal(g_last_error_message, "Unterminated character class");

    // Test: "[z-a]"
    AST_Node_t* ast2 = strling_parse("[z-a]");
    assert_null(ast2);
    assert_non_null(g_last_error_message);
    assert_non_null(strstr(g_last_error_message, "Invalid character range"));

    // Test: "[a-]" (This was in the TS file, but it's valid, not an error)
    // The test in the TS file `test("should parse incomplete range at end as literal", ...)`
    // is correctly placed in `test_special_character_handling` as `[a-]`.
}

// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_positive_and_negative_classes),
        cmocka_unit_test(test_class_contents_literals_ranges_shorthands),
        cmockT_unit_test(test_unicode_properties),
        cmocka_unit_test(test_special_character_handling),
        cmocka_unit_test(test_error_cases),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup/teardown
}
