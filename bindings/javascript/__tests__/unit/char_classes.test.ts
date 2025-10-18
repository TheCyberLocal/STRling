/**
 * @file Test Design — char_classes.test.ts
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
 * -   The special syntactic rules for `]`, `-`, `^`, and escapes like `\b`
 * when they appear inside a class.
 * -   Error handling for malformed classes (e.g., unterminated `[` or invalid
 * ranges `[z-a]`).
 * -   The structure of the resulting `nodes.CharClass` AST node and its list
 * of `items`.
 * -   **Out of scope:**
 * -   Quantification of an entire character class (covered in
 * `quantifiers.test.ts`).
 * -   The behavior of character classes within groups or lookarounds.
 * -   Emitter-specific optimizations or translations (covered in
 * `emitter_edges.test.ts`).
 */

import { parse, ParseError } from '../../src/STRling/core/parser';
import {
  CharClass,
  ClassItem,
  ClassLiteral,
  ClassRange,
  ClassEscape,
} from '../../src/STRling/core/nodes';

// --- Test Suite -----------------------------------------------------------------

describe('Category A: Positive Cases', () => {
  /**
   * Covers all positive cases for valid character class syntax.
   */

  test.each<[string, boolean, ClassItem[], string]>([
    // A.1: Basic Classes
    ['[abc]', false, [new ClassLiteral('a'), new ClassLiteral('b'), new ClassLiteral('c')], 'simple_class'],
    ['[^abc]', true, [new ClassLiteral('a'), new ClassLiteral('b'), new ClassLiteral('c')], 'negated_simple_class'],
    // A.2: Ranges
    ['[a-z]', false, [new ClassRange('a', 'z')], 'range_lowercase'],
    ['[A-Za-z0-9]', false, [new ClassRange('A', 'Z'), new ClassRange('a', 'z'), new ClassRange('0', '9')], 'range_alphanum'],
    // A.3: Shorthand Escapes
    ['[\\d\\s\\w]', false, [new ClassEscape('d'), new ClassEscape('s'), new ClassEscape('w')], 'shorthand_positive'],
    ['[\\D\\S\\W]', false, [new ClassEscape('D'), new ClassEscape('S'), new ClassEscape('W')], 'shorthand_negated'],
    // A.4: Unicode Property Escapes
    ['[\\p{L}]', false, [new ClassEscape('p', 'L')], 'unicode_property_short'],
    ['[\\p{Letter}]', false, [new ClassEscape('p', 'Letter')], 'unicode_property_long'],
    ['[\\P{Number}]', false, [new ClassEscape('P', 'Number')], 'unicode_property_negated'],
    ['[\\p{Script=Greek}]', false, [new ClassEscape('p', 'Script=Greek')], 'unicode_property_with_value'],
    // A.5: Special Character Handling
    ['[]a]', false, [new ClassLiteral(']'), new ClassLiteral('a')], 'special_char_bracket_at_start'],
    ['[^]a]', true, [new ClassLiteral(']'), new ClassLiteral('a')], 'special_char_bracket_at_start_negated'],
    ['[-az]', false, [new ClassLiteral('-'), new ClassLiteral('a'), new ClassLiteral('z')], 'special_char_hyphen_at_start'],
    ['[az-]', false, [new ClassLiteral('a'), new ClassLiteral('z'), new ClassLiteral('-')], 'special_char_hyphen_at_end'],
    ['[a^b]', false, [new ClassLiteral('a'), new ClassLiteral('^'), new ClassLiteral('b')], 'special_char_caret_in_middle'],
    ['[\\b]', false, [new ClassLiteral('\\x08')], 'special_char_backspace_escape'],
  ])('should parse valid char class "%s" (ID: %s)', (inputDsl, expectedNegated, expectedItems) => {
    /**
     * Tests that various valid character classes are parsed into the correct
     * CharClass AST node with the expected items.
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(CharClass);
    const ccNode = ast as CharClass;
    expect(ccNode.negated).toBe(expectedNegated);
    expect(ccNode.items).toEqual(expectedItems);
  });
});

describe('Category B: Negative Cases', () => {
  /**
   * Covers all negative cases for malformed character class syntax.
   */

  test.each<[string, string, number, string]>([
    // B.1: Unterminated classes
    ['[abc', 'Unterminated character class', 4, 'unterminated_class'],
    ['[', 'Unterminated character class', 1, 'unterminated_empty_class'],
    ['[^', 'Unterminated character class', 2, 'unterminated_negated_empty_class'],
    // B.2: Malformed Unicode properties
    ['[\\p{L', 'Unterminated \\p{...}', 5, 'unterminated_unicode_property'],
    ['[\\pL]', 'Expected { after \\p/\\P', 3, 'missing_braces_on_unicode_property'],
  ])('should fail to parse "%s" (ID: %s)', (invalidDsl, errorMessagePrefix, errorPosition) => {
    /**
     * Tests that invalid character class syntax raises a ParseError with the
     * correct message and position.
     */
    try {
      parse(invalidDsl);
      // This line should not be reached
      fail(`Expected parse to throw ParseError for input: ${invalidDsl}`);
    } catch (e) {
      expect(e).toBeInstanceOf(ParseError);
      const err = e as ParseError;
      expect(err.message).toContain(errorMessagePrefix);
      expect(err.pos).toBe(errorPosition);
    }
  });
});

describe('Category C: Edge Cases', () => {
  /**
   * Covers edge cases for character class parsing.
   */

  test.each<[string, ClassItem[], string]>([
    ['[a\\-c]', [new ClassLiteral('a'), new ClassLiteral('-'), new ClassLiteral('c')], 'escaped_hyphen_is_literal'],
    ['[\\x41-\\x5A]', [new ClassRange('A', 'Z')], 'range_with_escaped_endpoints'],
    ['[\\n\\t\\d]', [new ClassLiteral('\\n'), new ClassLiteral('\\t'), new ClassEscape('d')], 'class_with_only_escapes'],
  ])('should correctly parse edge case class "%s" (ID: %s)', (inputDsl, expectedItems) => {
    /**
     * Tests unusual but valid character class constructs.
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(CharClass);
    expect((ast as CharClass).items).toEqual(expectedItems);
  });
});

describe('Category D: Interaction Cases', () => {
  /**
   * Covers how character classes interact with other DSL features, specifically
   * the free-spacing mode flag.
   */

  test.each<[string, ClassItem[], string]>([
    ['%flags x\\n[a b]', [new ClassLiteral('a'), new ClassLiteral(' '), new ClassLiteral('b')], 'whitespace_is_literal'],
    ['%flags x\\n[a#b]', [new ClassLiteral('a'), new ClassLiteral('#'), new ClassLiteral('b')], 'comment_char_is_literal'],
  ])('should correctly handle "%s" in free-spacing mode (ID: %s)', (inputDsl, expectedItems) => {
    /**
     * Tests that in free-spacing mode, whitespace and '#' are treated as
     * literal characters inside a class, per the specification.
     *
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(CharClass);
    expect((ast as CharClass).items).toEqual(expectedItems);
  });
});