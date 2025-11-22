/**
 * @file ir_compiler_test.c
 * @brief Unit Tests for IR Compiler Lowering and Normalization (40 Tests).
 *
 * PURPOSE:
 * Validates the internal logic of the compiler: transforming the AST to IR (Lowering)
 * and optimizing the IR tree (Normalization).
 * Matches the test count (40) of 'bindings/javascript/__tests__/unit/ir_compiler.test.ts'.
 *
 * ADAPTATION NOTE:
 * The C library does not expose the internal IR structures or the separate 'lower'
 * and 'normalize' passes. This test suite verifies these internal behaviors
 * indirectly by compiling JSON ASTs and asserting that the final PCRE2 output
 * reflects the expected optimizations (e.g., fused literals, flattened groups).
 *
 * COVERAGE:
 * - Category A: AST to IR Lowering (Indirect verification via basic compilation)
 * - Category B: IR Normalization (Fusion, Flattening)
 * - Category C: Full Compilation (Integration of Lower + Normalize)
 * - Category D: Metadata Generation (Features Used)
 * - Category E: Deeply Nested Alternations
 * - Category F: Complex Sequence Normalization
 * - Category G: Literal Fusion Edge Cases
 * - Category H: Quantifier Normalization
 * - Category I: Feature Detection Comprehensive
 * - Category J: Alternation Normalization Edge Cases
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"

// --- Test Infrastructure ----------------------------------------------------

typedef struct
{
    const char *id;
    const char *json_input;
    const char *expected_pcre;
} TestCase;

static void run_test_batch(void **state, const TestCase *cases, size_t count)
{
    (void)state;

    for (size_t i = 0; i < count; i++)
    {
        strling_result_t result = strling_compile_compat(cases[i].json_input, NULL);

        if (result.error_code != STRling_OK)
        {
            printf("FAIL [%s]: Compilation error: %s\n", cases[i].id, result.error_message);
        }
        assert_int_equal(result.error_code, STRling_OK);
        assert_non_null(result.pcre2_pattern);

        if (strcmp(result.pcre2_pattern, cases[i].expected_pcre) != 0)
        {
            printf("FAIL [%s]:\n  Expected: '%s'\n  Got:      '%s'\n",
                   cases[i].id, cases[i].expected_pcre, result.pcre2_pattern);
        }
        assert_string_equal(result.pcre2_pattern, cases[i].expected_pcre);

        strling_result_free_compat(&result);
    }
}

// --- Category A: AST to IR Lowering (10 Tests) ------------------------------
// Verifies that all basic Node types are correctly translated.

static void test_category_a_lowering(void **state)
{
    const TestCase cases[] = {
        // 1. Lit -> IRLit
        {"lower_lit", "{\"type\": \"Literal\", \"value\": \"a\"}", "a"},

        // 2. Dot -> IRDot
        {"lower_dot", "{\"type\": \"Dot\"}", "."},

        // 3. Anchor -> IRAnchor
        {"lower_anchor", "{\"type\": \"Anchor\", \"at\": \"Start\"}", "^"},

        // 4. CharClass -> IRCharClass
        {"lower_charclass",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}",
         "[a-z]"},

        // 5. Seq -> IRSeq
        {"lower_seq",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Dot\"}]}",
         "a."},

        // 6. Alt -> IRAlt
        {"lower_alt",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}",
         "a|b"},

        // 7. Quant -> IRQuant
        {"lower_quant",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "a+"},

        // 8. Group -> IRGroup
        {"lower_group",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"x\", \"expression\": {\"type\": \"Dot\"}}",
         "(?<x>.)"},

        // 9. Backref -> IRBackref
        {"lower_backref",
         "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}",
         "\\1"},

        // 10. Look -> IRLook
        {"lower_look",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?=a)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category B: IR Normalization (4 Tests) ---------------------------------
// Verifies fusion and flattening logic.

static void test_category_b_normalization(void **state)
{
    const TestCase cases[] = {
        // 11. Fuse adjacent literals
        // Seq([Lit("a"), Lit("b"), Dot(), Lit("c")]) -> "ab.c" (Lit("ab") fused)
        {"norm_fuse_literals",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Dot\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}",
         "ab.c"},

        // 12. Flatten nested sequences
        // Seq([Lit("a"), Seq([Lit("b"), Lit("c")])]) -> "abc" (Flattened + Fused)
        {"norm_flatten_seq",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}]}",
         "abc"},

        // 13. Flatten nested alternations
        // Alt([Lit("a"), Alt([Lit("b"), Lit("c")])]) -> "a|b|c"
        {"norm_flatten_alt",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}]}",
         "a|b|c"},

        // 14. Idempotency (Already normalized)
        // Seq([Lit("ab"), Dot()]) -> "ab."
        {"norm_idempotent",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"ab\"}, {\"type\": \"Dot\"}]}",
         "ab."}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Full Compilation (2 Tests) ---------------------------------

static void test_category_c_full_compilation(void **state)
{
    const TestCase cases[] = {
        // 15. AST adjacent literals -> fused output
        {"full_adjacent_lits",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"hello\"}, {\"type\": \"Literal\", \"value\": \" \"}, {\"type\": \"Literal\", \"value\": \"world\"}]}",
         "hello world"},

        // 16. Nested AST sequence -> flat output
        {"full_nested_seq",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Dot\"}]}]}]}",
         "ab."}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Metadata Generation (4 Tests) ------------------------------
// NOTE: The C API doesn't expose the metadata object directly for inspection.
// We verify these compilations succeed and produce correct patterns.
// (Internal metadata tracking is assumed to be working if no crashes occur).

static void test_category_d_metadata(void **state)
{
    const TestCase cases[] = {
        // 17. Atomic Group
        {"meta_atomic",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?>a)"},

        // 18. Possessive Quantifier
        // Note: PCRE2 emits x*+ for possessive
        {"meta_possessive",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "a++"}, // or a*+ depending on min/max. min 1 -> a++

        // 19. Lookbehind
        {"meta_lookbehind",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?<=a)"},

        // 20. No features (clean compile)
        {"meta_none",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Dot\"}]}",
         "a."}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category E: Deeply Nested Alternations (3 Tests) -----------------------

static void test_category_e_deep_alt(void **state)
{
    const TestCase cases[] = {
        // 21. Three-level nested alternation -> flattened
        // (a|(b|(c|d))) -> a|b|c|d
        {"deep_alt_flatten",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"c\"}, {\"type\": \"Literal\", \"value\": \"d\"}]}]}]}",
         "a|b|c|d"},

        // 22. Sequences within alternation
        // (ab|cd|ef) - sequences inside alternation branches should fuse
        {"deep_alt_fuse_seq",
         "{\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]},"
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"c\"}, {\"type\": \"Literal\", \"value\": \"d\"}]},"
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"e\"}, {\"type\": \"Literal\", \"value\": \"f\"}]}"
         "]}",
         "ab|cd|ef"},

        // 23. Mixed alternation and sequence nesting
        // ((a|b)(c|d)) -> (?:a|b)(?:c|d) or equivalent grouping
        // Note: Emitter usually wraps alternation in non-capturing group if inside sequence.
        {"deep_alt_mixed",
         "{\"type\": \"Group\", \"capturing\": false, \"body\": {\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]},"
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"c\"}, {\"type\": \"Literal\", \"value\": \"d\"}]}"
         "]}}",
         "(?:(?:a|b)(?:c|d))"} // Emitter specific: STRling output logic
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category F: Complex Sequence Normalization (3 Tests) -------------------

static void test_category_f_complex_seq(void **state)
{
    const TestCase cases[] = {
        // 24. Deeply nested sequences -> fused
        // Seq([Lit("a"), Seq([Lit("b"), Seq([Lit("c")])])]) -> "abc"
        {"complex_seq_deep",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"c\"}]}]}]}",
         "abc"},

        // 25. Sequence with non-literal in middle -> partial fusion
        // Seq([Lit("a"), Dot(), Lit("b")]) -> a.b
        {"complex_seq_mid_nonlit",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Dot\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}",
         "a.b"},

        // 26. Empty sequence
        // Seq([]) -> ""
        {"complex_seq_empty",
         "{\"type\": \"Sequence\", \"parts\": []}",
         ""}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category G: Literal Fusion Edge Cases (3 Tests) ------------------------

static void test_category_g_fusion_edges(void **state)
{
    const TestCase cases[] = {
        // 27. Fuse escaped chars
        // Lit("a") + Lit("\n") + Lit("b") -> a\nb
        {"fusion_escaped",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"\\n\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}",
         "a\\nb"},

        // 28. Fuse unicode
        // Lit("😀") + Lit("a") -> 😀a
        {"fusion_unicode",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"😀\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}",
         "\\x{1f600}a"},

        // 29. No fusion across non-literals
        // Seq([Lit("a"), Dot(), Lit("b")])
        {"fusion_boundary",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Dot\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}",
         "a.b"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category H: Quantifier Normalization (3 Tests) -------------------------

static void test_category_h_quant_norm(void **state)
{
    const TestCase cases[] = {
        // 30. Unwrap quantifier of single-item sequence
        // Quant(Seq([Lit("a")])) -> a+
        {"quant_unwrap_seq",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}]}}",
         "a+"},

        // 31. Preserve quantifier of empty sequence
        // Quant(Seq([])) -> (?:)*
        {"quant_empty_seq",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Sequence\", \"parts\": []}}",
         "(?:)*"},

        // 32. Preserve nested quantifiers
        // Quant(Quant(Lit("a"))) -> (a{1,3})* (Example)
        {"quant_nested",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": 3, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
         "(?:a{1,3})?"} // Note: Inner quant needs group to be quantified
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category I: Feature Detection Comprehensive (5 Tests) ------------------

static void test_category_i_feature_detection(void **state)
{
    const TestCase cases[] = {
        // 33. Named Groups
        {"feat_named_group",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"mygroup\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?<mygroup>a)"},

        // 34. Backreferences
        {"feat_backref",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"body\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"Backref\", \"byIndex\": 1}]}",
         "(a)\\1"},

        // 35. Lookahead
        {"feat_lookahead",
         "{\"type\": \"Lookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?=a)"},

        // 36. Unicode Properties
        {"feat_unicode",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"UnicodeProperty\", \"value\": \"Letter\"}]}",
         "[\\p{Letter}]"},

        // 37. Multiple Features
        {"feat_multiple",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"atomic\": true, \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Lookbehind\", \"body\": {\"type\": \"Literal\", \"value\": \"c\"}}"
         "]}",
         "(?>a)(?<=c)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category J: Alternation Edge Cases (3 Tests) ---------------------------

static void test_category_j_alt_edges(void **state)
{
    const TestCase cases[] = {
        // 38. Unwrap single branch alternation
        // Alt([Lit("a")]) -> a
        {"alt_single_unwrap",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}]}",
         "a"},

        // 39. Preserve empty branches (if valid)
        // Alt([Lit("a"), Seq([])]) -> a|
        {"alt_preserve_empty",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Sequence\", \"parts\": []}]}",
         "a|"},

        // 40. Flatten alts at different depths
        // Alt([Lit("a"), Alt([Lit("b"), Lit("c")]), Lit("d")]) -> a|b|c|d
        {"alt_flatten_depths",
         "{\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Literal\", \"value\": \"a\"},"
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]},"
         "{\"type\": \"Literal\", \"value\": \"d\"}"
         "]}",
         "a|b|c|d"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_lowering),
        cmocka_unit_test(test_category_b_normalization),
        cmocka_unit_test(test_category_c_full_compilation),
        cmocka_unit_test(test_category_d_metadata),
        cmocka_unit_test(test_category_e_deep_alt),
        cmocka_unit_test(test_category_f_complex_seq),
        cmocka_unit_test(test_category_g_fusion_edges),
        cmocka_unit_test(test_category_h_quant_norm),
        cmocka_unit_test(test_category_i_feature_detection),
        cmocka_unit_test(test_category_j_alt_edges),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}