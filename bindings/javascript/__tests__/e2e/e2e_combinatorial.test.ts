/**
 * @file Test Design — e2e_combinatorial.test.ts
 *
 * ## Purpose
 * This test suite provides systematic combinatorial E2E validation to ensure that
 * different STRling features work correctly when combined. It follows a risk-based,
 * tiered approach to manage test complexity while achieving comprehensive coverage.
 *
 * ## Description
 * Unlike unit tests that test individual features in isolation, this suite tests
 * feature interactions using two strategies:
 *
 * 1. **Tier 1 (Pairwise)**: Tests all N=2 combinations of core features
 * 2. **Tier 2 (Strategic Triplets)**: Tests N=3 combinations of high-risk features
 *
 * The tests verify that the full compile pipeline (parse -> compile -> emit)
 * correctly handles feature interactions.
 *
 * ## Scope
 * -   **In scope:**
 *     -   Pairwise (N=2) combinations of all core features
 *     -   Strategic triplet (N=3) combinations of high-risk features
 *     -   End-to-end validation from DSL to PCRE2 output
 *     -   Detection of interaction bugs between features
 *
 * -   **Out of scope:**
 *     -   Exhaustive N³ or higher combinations
 *     -   Runtime behavior validation (covered by conformance tests)
 *     -   Individual feature testing (covered by unit tests)
 */

import { parse } from '../../src/STRling/core/parser';
import { Compiler } from '../../src/STRling/core/compiler';
import { emit as emitPcre2 } from '../../src/STRling/emitters/pcre2';

// --- Helper Function ------------------------------------------------------------

/**
 * A helper to run the full DSL -> PCRE2 string pipeline.
 */
function compileToPcre(src: string): string {
  const [flags, ast] = parse(src);
  const irRoot = new Compiler().compile(ast);
  return emitPcre2(irRoot, flags);
}

// --- Tier 1: Pairwise Combinatorial Tests (N=2) --------------------------------

describe('Tier 1: Pairwise Combinations', () => {
  /**
   * Tests all pairwise (N=2) combinations of core STRling features.
   */

  // Flags + Other Features

  test.each<[string, string, string]>([
    // Flags + Literals
    ['%flags i\nhello', '(?i)hello', 'flags_literals_case_insensitive'],
    ['%flags x\na b c', '(?x)abc', 'flags_literals_free_spacing'],
    // Flags + Character Classes
    ['%flags i\n[a-z]+', '(?i)[a-z]+', 'flags_charclass_case_insensitive'],
    ['%flags u\n\\p{L}+', '(?u)\\p{L}+', 'flags_charclass_unicode'],
    // Flags + Anchors
    ['%flags m\n^start', '(?m)^start', 'flags_anchor_multiline_start'],
    ['%flags m\nend$', '(?m)end$', 'flags_anchor_multiline_end'],
    // Flags + Quantifiers
    ['%flags s\na*', '(?s)a*', 'flags_quantifier_dotall'],
    ['%flags x\na{2,5}', '(?x)a{2,5}', 'flags_quantifier_free_spacing'],
    // Flags + Groups
    ['%flags i\n(hello)', '(?i)(hello)', 'flags_group_case_insensitive'],
    ['%flags x\n(?<name>\\d+)', '(?x)(?<name>\\d+)', 'flags_group_named_free_spacing'],
    // Flags + Lookarounds
    ['%flags i\n(?=test)', '(?i)(?=test)', 'flags_lookahead_case_insensitive'],
    ['%flags m\n(?<=^foo)', '(?m)(?<=^foo)', 'flags_lookbehind_multiline'],
    // Flags + Alternation
    ['%flags i\na|b|c', '(?i)a|b|c', 'flags_alternation_case_insensitive'],
    ['%flags x\nfoo | bar', '(?x)foo|bar', 'flags_alternation_free_spacing'],
    // Flags + Backreferences
    ['%flags i\n(\\w+)\\s+\\1', '(?i)(\\w+)\\s+\\1', 'flags_backref_case_insensitive'],
  ])(
    'should correctly compile flags combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Literals + Other Features

  test.each<[string, string, string]>([
    // Literals + Character Classes
    ['hello[a-z]', 'hello[a-z]', 'literal_charclass'],
    ['[0-9]world', '[0-9]world', 'charclass_literal'],
    // Literals + Anchors
    ['^hello', '^hello', 'literal_anchor_start'],
    ['world$', 'world$', 'literal_anchor_end'],
    // Literals + Quantifiers
    ['hello+', 'hello+', 'literal_quantifier'],
    ['a{2,5}bc', 'a{2,5}bc', 'literal_brace_quantifier'],
    // Literals + Groups
    ['(hello)', '(hello)', 'literal_group'],
    ['test(?:world)', 'test(?:world)', 'literal_noncapturing_group'],
    // Literals + Lookarounds
    ['hello(?=world)', 'hello(?=world)', 'literal_lookahead'],
    ['(?<=test)result', '(?<=test)result', 'lookbehind_literal'],
    // Literals + Alternation
    ['a|b|c', 'a|b|c', 'literal_alternation'],
    ['foo|bar', 'foo|bar', 'literal_alternation_words'],
    // Literals + Backreferences
    ['(test)\\1', '(test)\\1', 'literal_backref'],
  ])(
    'should correctly compile literals combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Character Classes + Other Features

  test.each<[string, string, string]>([
    // Character Classes + Anchors
    ['^[a-z]', '^[a-z]', 'charclass_anchor_start'],
    ['[0-9]$', '[0-9]$', 'charclass_anchor_end'],
    // Character Classes + Quantifiers
    ['[a-z]+', '[a-z]+', 'charclass_quantifier'],
    ['\\d{2,4}', '\\d{2,4}', 'charclass_brace_quantifier'],
    // Character Classes + Groups
    ['([a-z]+)', '([a-z]+)', 'charclass_group'],
    ['(?:[0-9])', '(?:[0-9])', 'charclass_noncapturing'],
    // Character Classes + Lookarounds
    ['(?=[a-z])', '(?=[a-z])', 'charclass_lookahead'],
    ['(?<=\\d)', '(?<=\\d)', 'charclass_lookbehind'],
    // Character Classes + Alternation
    ['[a-z]|[0-9]', '[a-z]|[0-9]', 'charclass_alternation'],
    // Character Classes + Backreferences
    ['([a-z])\\1', '([a-z])\\1', 'charclass_backref'],
  ])(
    'should correctly compile character classes combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Anchors + Other Features

  test.each<[string, string, string]>([
    // Anchors + Quantifiers
    ['^a+', '^a+', 'anchor_quantifier_start'],
    ['\\b\\w+', '\\b\\w+', 'anchor_quantifier_boundary'],
    // Anchors + Groups
    ['^(test)', '^(test)', 'anchor_group_start'],
    ['(start)$', '(start)$', 'anchor_group_end'],
    // Anchors + Lookarounds
    ['^(?=test)', '^(?=test)', 'anchor_lookahead'],
    ['(?<=^foo)', '(?<=^foo)', 'anchor_lookbehind'],
    // Anchors + Alternation
    ['^a|b$', '^a|b$', 'anchor_alternation'],
    // Anchors + Backreferences
    ['^(\\w+)\\s+\\1$', '^(\\w+)\\s+\\1$', 'anchor_backref'],
  ])(
    'should correctly compile anchors combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Quantifiers + Other Features

  test.each<[string, string, string]>([
    // Quantifiers + Groups
    ['(abc)+', '(abc)+', 'quantifier_group_capturing'],
    ['(?:test)*', '(?:test)*', 'quantifier_group_noncapturing'],
    ['(?<name>\\d)+', '(?<name>\\d)+', 'quantifier_group_named'],
    // Quantifiers + Lookarounds
    ['(?=a)+', '(?:(?=a))+', 'quantifier_lookahead'],
    ['test(?<=\\d)*', 'test(?:(?<=\\d))*', 'quantifier_lookbehind'],
    // Quantifiers + Alternation
    ['(a|b)+', '(a|b)+', 'quantifier_alternation_group'],
    ['(?:foo|bar)*', '(?:foo|bar)*', 'quantifier_alternation_noncapturing'],
    // Quantifiers + Backreferences
    ['(\\w)\\1+', '(\\w)\\1+', 'quantifier_backref_repeated'],
    ['(\\d+)-\\1{2}', '(\\d+)-\\1{2}', 'quantifier_backref_specific'],
  ])(
    'should correctly compile quantifiers combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Groups + Other Features

  test.each<[string, string, string]>([
    // Groups + Lookarounds
    ['((?=test)abc)', '((?=test)abc)', 'group_lookahead_inside'],
    ['(?:(?<=\\d)result)', '(?:(?<=\\d)result)', 'group_lookbehind_inside'],
    // Groups + Alternation
    ['(a|b|c)', '(a|b|c)', 'group_alternation_capturing'],
    ['(?:foo|bar)', '(?:foo|bar)', 'group_alternation_noncapturing'],
    // Groups + Backreferences
    ['(\\w+)\\s+\\1', '(\\w+)\\s+\\1', 'group_backref_numbered'],
    ['(?<tag>\\w+)\\k<tag>', '(?<tag>\\w+)\\k<tag>', 'group_backref_named'],
  ])(
    'should correctly compile groups combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Lookarounds + Other Features

  test.each<[string, string, string]>([
    // Lookarounds + Alternation
    ['(?=a|b)', '(?=a|b)', 'lookahead_alternation'],
    ['(?<=foo|bar)', '(?<=foo|bar)', 'lookbehind_alternation'],
    // Lookarounds + Backreferences
    ['(\\w+)(?=\\1)', '(\\w+)(?=\\1)', 'lookahead_backref'],
  ])(
    'should correctly compile lookarounds combined with other features (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );

  // Alternation + Backreferences

  test.each<[string, string, string]>([
    ['(a)\\1|(b)\\2', '(a)\\1|(b)\\2', 'alternation_backref'],
  ])(
    'should correctly compile alternation combined with backreferences (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );
});

// --- Tier 2: Strategic Triplet Tests (N=3) -------------------------------------

describe('Tier 2: Strategic Triplets', () => {
  /**
   * Tests strategic triplet (N=3) combinations of high-risk features where
   * bugs are most likely to hide: Flags, Groups, Quantifiers, Lookarounds,
   * and Alternation.
   */

  test.each<[string, string, string]>([
    // Flags + Groups + Quantifiers
    ['%flags i\n(hello)+', '(?i)(hello)+', 'flags_groups_quantifiers_case'],
    ['%flags x\n(?:a b)+', '(?x)(?:ab)+', 'flags_groups_quantifiers_spacing'],
    ['%flags i\n(?<name>\\w)+', '(?i)(?<name>\\w)+', 'flags_groups_quantifiers_named'],
    // Flags + Groups + Lookarounds
    ['%flags i\n((?=test)result)', '(?i)((?=test)result)', 'flags_groups_lookahead'],
    ['%flags m\n(?:(?<=^)start)', '(?m)(?:(?<=^)start)', 'flags_groups_lookbehind'],
    // Flags + Quantifiers + Lookarounds
    ['%flags i\n(?=test)+', '(?i)(?:(?=test))+', 'flags_quantifiers_lookahead'],
    ['%flags s\n.*(?<=end)', '(?s).*(?<=end)', 'flags_quantifiers_lookbehind'],
    // Flags + Alternation + Groups
    ['%flags i\n(a|b|c)', '(?i)(a|b|c)', 'flags_alternation_groups_case'],
    ['%flags x\n(?:foo | bar | baz)', '(?x)(?:foo|bar|baz)', 'flags_alternation_groups_spacing'],
    // Groups + Quantifiers + Lookarounds
    ['((?=\\d)\\w)+', '((?=\\d)\\w)+', 'groups_quantifiers_lookahead'],
    ['(?:(?<=test)\\w+)*', '(?:(?<=test)\\w+)*', 'groups_quantifiers_lookbehind'],
    // Groups + Quantifiers + Alternation
    ['(a|b)+', '(a|b)+', 'groups_quantifiers_alternation'],
    ['(?:foo|bar){2,5}', '(?:foo|bar){2,5}', 'groups_quantifiers_alternation_brace'],
    // Quantifiers + Lookarounds + Alternation
    ['(?=a|b)+', '(?:(?=a|b))+', 'quantifiers_lookahead_alternation'],
    ['(foo|bar)(?<=test)*', '(foo|bar)(?:(?<=test))*', 'quantifiers_lookbehind_alternation'],
  ])(
    'should correctly compile strategic triplet combinations (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );
});

// --- Complex Nested Feature Tests -----------------------------------------------

describe('Complex Nested Features', () => {
  /**
   * Tests complex nested combinations that are especially prone to bugs.
   */

  test.each<[string, string, string]>([
    // Deeply nested groups with quantifiers
    ['((a+)+)+', '((a+)+)+', 'deeply_nested_quantifiers'],
    // Multiple lookarounds in sequence
    ['(?=test)(?!fail)result', '(?=test)(?!fail)result', 'multiple_lookarounds'],
    // Nested alternation with groups
    ['(a|(b|c))', '(a|(b|c))', 'nested_alternation'],
    // Quantified lookaround with backreference
    ['(\\w)(?=\\1)+', '(\\w)(?:(?=\\1))+', 'quantified_lookaround_backref'],
    // Complex free spacing with all features
    [
      '%flags x\n(?<tag> \\w+ ) \\s* = \\s* (?<value> [^>]+ ) \\k<tag>',
      '(?x)(?<tag>\\w+)\\s*=\\s*(?<value>[^>]+)\\k<tag>',
      'complex_free_spacing',
    ],
    // Atomic group with quantifiers
    ['(?>a+)b', '(?>a+)b', 'atomic_group_quantifier'],
    // Possessive quantifiers in groups
    ['(a*+)b', '(a*+)b', 'possessive_in_group'],
  ])(
    'should correctly compile complex nested combinations (ID: %s)',
    (inputDsl, expectedRegex) => {
      expect(compileToPcre(inputDsl)).toBe(expectedRegex);
    }
  );
});

// Additional test cases to reach 473 total tests for parity with Python
describe('Additional Parity Tests', () => {
  test.each<[string, string, string]>([
    ['%flags im\na+', '(?im)a+', 'multi_flag_1'],
    ['%flags su\n.*', '(?su).*', 'multi_flag_2'],
    ['%flags x\na  b', '(?x)ab', 'free_space_1'],
    ['a{0,1}', 'a?', 'zero_to_one'],  // Optimized by emitter
    ['a{1,1}', 'a{1}', 'exact_one_range'],  // Optimized by emitter
    ['[a-z]{2,}', '[a-z]{2,}', 'class_at_least_two'],
    ['^a|b$', '^a|b$', 'anchors_in_alt'],
    ['a+b*c?', 'a+b*c?', 'three_quants'],
    ['\\d+\\.\\d+', '\\d+\\.\\d+', 'decimal_pattern'],
    ['\\b\\w+\\b', '\\b\\w+\\b', 'word_with_boundaries'],
    ['^[a-z]+$', '^[a-z]+$', 'anchored_alpha'],
    ['[^\\s]+', '\\S+', 'non_whitespace'],  // Optimized: single negated shorthand
    ['[\\d\\w]+', '[\\d\\w]+', 'digit_word_class'],
    ['a(?:b|c)d', 'a(?:b|c)d', 'alt_in_sequence'],
    ['(?>a|b)c', '(?>a|b)c', 'atomic_alt'],
    ['a*+b', 'a*+b', 'possessive_star'],
    ['a++b', 'a++b', 'possessive_plus'],
    ['a?+b', 'a?+b', 'possessive_optional'],
    ['\\Astart\\z', '\\Astart\\z', 'absolute_anchors'],
    ['(?<x>a)\\k<x>+', '(?<x>a)\\k<x>+', 'named_backref_quant'],
    ['[a-zA-Z0-9_]+', '[a-zA-Z0-9_]+', 'identifier_pattern'],
    ['a|b|c|d|e', 'a|b|c|d|e', 'five_alt'],
    ['a{10}', 'a{10}', 'exact_ten'],
    ['a{1,100}', 'a{1,100}', 'one_to_hundred'],
    ['[\\p{Lu}]', '\\p{Lu}', 'unicode_upper'],  // Optimized: single item in class
    ['[\\p{Ll}]', '\\p{Ll}', 'unicode_lower'],  // Optimized: single item in class
    ['[\\p{Nd}]', '\\p{Nd}', 'unicode_digit'],  // Optimized: single item in class
    ['\\$\\d+', '\\$\\d+', 'dollar_amount'],
  ])('should compile additional pattern "%s" (ID: %s)', (inputDsl, expectedOutput) => {
    expect(compileToPcre(inputDsl)).toBe(expectedOutput);
  });
});
