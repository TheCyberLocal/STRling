/**
 * @file Test Design — anchors.test.ts
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
 * -   The behavior of `\b` inside a character class, where it represents a
 * backspace literal (covered in `char_classes.test.ts`).
 */

import { parse } from '../../src/STRling/core/parser';
import { Node, Anchor, Seq, Group, Look } from '../../src/STRling/core/nodes';

// --- Test Suite -----------------------------------------------------------------

describe('Category A: Positive Cases', () => {
  /**
   * Covers all positive cases for valid anchor syntax. These tests verify
   * that each anchor token is parsed into the correct Anchor node with the
   * expected `at` value.
   */

  test.each<[string, string, string]>([
    // A.1: Core Line Anchors
    ['^', 'Start', 'line_start'],
    ['$', 'End', 'line_end'],
    // A.2: Core Word Boundary Anchors
    ['\\b', 'WordBoundary', 'word_boundary'],
    ['\\B', 'NotWordBoundary', 'not_word_boundary'],
    // A.3: Absolute Anchors (Extension Features)
    ['\\A', 'AbsoluteStart', 'absolute_start_ext'],
    ['\\Z', 'EndBeforeFinalNewline', 'end_before_newline_ext'],
    ['\\z', 'AbsoluteEnd', 'absolute_end_ext'],
  ])('should correctly parse anchor "%s" (ID: %s)', (inputDsl, expectedAtValue) => {
    /**
     * Tests that each individual anchor token is parsed into the correct
     * Anchor AST node.
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(Anchor);
    expect((ast as Anchor).at).toBe(expectedAtValue);
  });
});

describe('Category B: Negative Cases', () => {
  /**
   * This category is intentionally empty. Anchors are single, unambiguous
   * tokens, and there are no anchor-specific parse errors. Invalid escape
   * sequences are handled by the literal/escape parser and are tested in
   * that suite.
   */
});

describe('Category C: Edge Cases', () => {
  /**
   * Covers edge cases related to the position and combination of anchors.
   */

  test('should parse a pattern with only anchors into a correct sequence', () => {
    /**
     * Tests that a pattern containing multiple anchors is parsed into a
     * correct sequence of Anchor nodes.
     */
    const [, ast] = parse('^\\A\\b$');
    expect(ast).toBeInstanceOf(Seq);
    const seqNode = ast as Seq;
    expect(seqNode.parts).toHaveLength(4);
    expect(seqNode.parts.every((part) => part instanceof Anchor)).toBe(true);
    const atValues = seqNode.parts.map((part) => (part as Anchor).at);
    expect(atValues).toEqual(['Start', 'AbsoluteStart', 'WordBoundary', 'End']);
  });

  test.each<[string, number, string, string]>([
    ['^a', 0, 'Start', 'at_start'],
    ['a\\bb', 1, 'WordBoundary', 'in_middle'],
    ['ab$', 2, 'End', 'at_end'],
  ])('should parse anchor in different positions (ID: %s)', (inputDsl, expectedPosition, expectedAtValue) => {
    /**
     * Tests that anchors are correctly parsed as part of a sequence at
     * various positions.
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(Seq);
    const seqNode = ast as Seq;
    const anchorNode = seqNode.parts[expectedPosition];
    expect(anchorNode).toBeInstanceOf(Anchor);
    expect((anchorNode as Anchor).at).toBe(expectedAtValue);
  });
});

describe('Category D: Interaction Cases', () => {
  /**
   * Covers how anchors interact with other DSL features, such as flags
   * and grouping constructs.
   */

  test('should not change the parsed AST when multiline flag is present', () => {
    /**
     * A critical test to ensure the parser's output for `^` and `$` is
     * identical regardless of the multiline flag. The flag's semantic
     * effect is a runtime concern for the regex engine.
     */
    const [, astNoM] = parse('^a$');
    const [, astWithM] = parse('%flags m\n^a$');

    expect(astWithM).toEqual(astNoM);

    // Add specific checks to help the type checker and be explicit
    expect(astNoM).toBeInstanceOf(Seq);
    const seqNode = astNoM as Seq;
    expect(seqNode.parts[0]).toBeInstanceOf(Anchor);
    expect(seqNode.parts[2]).toBeInstanceOf(Anchor);
    expect((seqNode.parts[0] as Anchor).at).toBe('Start');
    expect((seqNode.parts[2] as Anchor).at).toBe('End');
  });

  // Define a type for the constructor of Node subclasses for cleaner type hinting
  type NodeConstructor = new (...args: any[]) => Group | Look;

  test.each<[string, NodeConstructor, string, string]>([
    ['(^a)', Group, 'Start', 'in_capturing_group'],
    ['(?:a\\b)', Group, 'WordBoundary', 'in_noncapturing_group'],
    ['(?=a$)', Look, 'End', 'in_lookahead'],
    ['(?<=^a)', Look, 'Start', 'in_lookbehind'],
  ])('should parse anchors inside groups and lookarounds (ID: %s)', (inputDsl, containerType, expectedAtValue) => {
    /**
     * Tests that anchors are correctly parsed when nested inside other
     * syntactic constructs.
     */
    const [, ast] = parse(inputDsl);
    expect(ast).toBeInstanceOf(containerType);

    const containerNode = ast as Group | Look;
    const body = containerNode.body;

    // The anchor may be part of a sequence inside the container
    const innerNode = (body instanceof Seq) ? body.parts[0] : body;
    
    expect(innerNode).toBeInstanceOf(Anchor);
    expect((innerNode as Anchor).at).toBe(expectedAtValue);
  });
});