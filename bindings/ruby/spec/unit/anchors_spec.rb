# frozen_string_literal: true

# Test Design — anchors_spec.rb
#
# ## Purpose
# This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
# It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
# with the proper type and that its parsing is unaffected by flags or surrounding
# constructs.
#
# ## Description
# Anchors are zero-width assertions that do not consume characters but instead
# match a specific **position** within the input string, such as the start of a
# line or a boundary between a word and a space. This suite tests the parser's
# ability to correctly identify all supported core and extension anchors and
# produce the corresponding `nodes.Anchor` AST object.
#
# ## Scope
# -   **In scope:**
#     -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
#         (`\b`, `\B`).
#     -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
#     -   The structure and `at` value of the resulting `nodes.Anchor` AST node.
#     -   How anchors are parsed when placed at the start, middle, or end of a sequence.
#     -   Ensuring the parser's output for `^` and `$` is consistent regardless
#         of the multiline (`m`) flag's presence.
# -   **Out of scope:**
#     -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
#         active (this is an emitter/engine concern).
#     -   Quantification of anchors.
#     -   The behavior of `\b` inside a character class, where it represents a
#         backspace literal (covered in `char_classes_spec.rb`).

require 'spec_helper'
require 'strling'

RSpec.describe 'Anchor Parsing' do
  # Helper to parse and get AST
  def parse(input)
    Strling::Core.parse(input)
  end

  describe 'Category A: Positive Cases' do
    # Covers all positive cases for valid anchor syntax. These tests verify
    # that each anchor token is parsed into the correct Anchor node with the
    # expected `at` value.

    [
      # A.1: Core Line Anchors
      ['^', 'Start', 'line_start'],
      ['$', 'End', 'line_end'],
      # A.2: Core Word Boundary Anchors
      ['\\b', 'WordBoundary', 'word_boundary'],
      ['\\B', 'NotWordBoundary', 'not_word_boundary'],
      # A.3: Absolute Anchors (Extension Features)
      ['\\A', 'AbsoluteStart', 'absolute_start_ext'],
      ['\\Z', 'EndBeforeFinalNewline', 'end_before_newline_ext']
    ].each do |input_dsl, expected_at_value, id|
      it "should parse anchor '#{input_dsl}' (ID: #{id})" do
        # Tests that each individual anchor token is parsed into the correct
        # Anchor AST node.
        _flags, ast = parse(input_dsl)
        expect(ast).to be_a(Strling::Core::Anchor)
        expect(ast.at).to eq(expected_at_value)
      end
    end
  end

  describe 'Category B: Negative Cases' do
    # This category is intentionally empty. Anchors are single, unambiguous
    # tokens, and there are no anchor-specific parse errors. Invalid escape
    # sequences are handled by the literal/escape parser and are tested in
    # that suite.
  end

  describe 'Category C: Edge Cases' do
    # Covers edge cases related to the position and combination of anchors.

    it 'should parse a pattern with only anchors' do
      # Tests that a pattern containing multiple anchors is parsed into a
      # correct sequence of Anchor nodes.
      _flags, ast = parse('^\A\\b$')
      expect(ast).to be_a(Strling::Core::Seq)
      seq_node = ast

      expect(seq_node.parts).to have_attributes(length: 4)
      expect(seq_node.parts.all? { |part| part.is_a?(Strling::Core::Anchor) }).to be true
      at_values = seq_node.parts.map(&:at)
      expect(at_values).to eq(['Start', 'AbsoluteStart', 'WordBoundary', 'End'])
    end

    [
      ['^a', 0, 'Start', 'at_start'],
      ['a\\bb', 1, 'WordBoundary', 'in_middle'],
      ['ab$', 1, 'End', 'at_end']
    ].each do |input_dsl, expected_position, expected_at_value, id|
      it "should parse anchors in different positions (ID: #{id})" do
        # Tests that anchors are correctly parsed as part of a sequence at
        # various positions.
        _flags, ast = parse(input_dsl)
        expect(ast).to be_a(Strling::Core::Seq)
        seq_node = ast
        anchor_node = seq_node.parts[expected_position]
        expect(anchor_node).to be_a(Strling::Core::Anchor)
        expect(anchor_node.at).to eq(expected_at_value)
      end
    end
  end

  describe 'Category D: Interaction Cases' do
    # Covers how anchors interact with other DSL features, such as flags
    # and grouping constructs.

    it 'should not change the parsed AST when multiline flag is present' do
      # A critical test to ensure the parser's output for `^` and `$` is
      # identical regardless of the multiline flag. The flag's semantic
      # effect is a runtime concern for the regex engine.
      _flags, ast_no_m = parse('^a$')
      _flags, ast_with_m = parse("%flags m\n^a$")

      expect(ast_with_m.to_dict).to eq(ast_no_m.to_dict)

      # Add specific checks to be explicit
      expect(ast_no_m).to be_a(Strling::Core::Seq)
      seq_node = ast_no_m
      expect(seq_node.parts[0]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[2]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[0].at).to eq('Start')
      expect(seq_node.parts[2].at).to eq('End')
    end

    [
      ['(^a)', Strling::Core::Group, 'Start', 'in_capturing_group'],
      ['(?:a\\b)', Strling::Core::Group, 'WordBoundary', 'in_noncapturing_group'],
      ['(?=a$)', Strling::Core::Look, 'End', 'in_lookahead'],
      ['(?<=^a)', Strling::Core::Look, 'Start', 'in_lookbehind']
    ].each do |input_dsl, container_type, expected_at_value, id|
      it "should parse anchors inside groups and lookarounds (ID: #{id})" do
        # Tests that anchors are correctly parsed when nested inside other
        # syntactic constructs.
        _flags, ast = parse(input_dsl)
        expect(ast).to be_a(container_type)

        container_node = ast

        # The anchor may be part of a sequence inside the container, find it
        anchor_node = nil
        if container_node.body.is_a?(Strling::Core::Seq)
          # Find the anchor in the sequence
          container_node.body.parts.each do |part|
            if part.is_a?(Strling::Core::Anchor)
              anchor_node = part
              break
            end
          end
        elsif container_node.body.is_a?(Strling::Core::Anchor)
          # Direct anchor
          anchor_node = container_node.body
        end

        expect(anchor_node).not_to be_nil, "No anchor found in sequence: #{container_node.body}"
        expect(anchor_node).to be_a(Strling::Core::Anchor)
        expect(anchor_node.at).to eq(expected_at_value)
      end
    end
  end

  describe 'Category E: Anchors in Complex Sequences' do
    # Tests for anchors in complex sequences with quantified atoms.

    it 'should parse anchor between quantified atoms' do
      # Tests anchor between quantified atoms: a*^b+
      # The ^ anchor appears between two quantified literals.
      _flags, ast = parse('a*^b+')
      expect(ast).to be_a(Strling::Core::Seq)
      seq_node = ast
      expect(seq_node.parts).to have_attributes(length: 3)
      expect(seq_node.parts[0]).to be_a(Strling::Core::Quant)
      expect(seq_node.parts[1]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[1].at).to eq('Start')
      expect(seq_node.parts[2]).to be_a(Strling::Core::Quant)
    end

    it 'should parse anchor after quantified group' do
      # Tests anchor after quantified group: (ab)*$
      _flags, ast = parse('(ab)*$')
      expect(ast).to be_a(Strling::Core::Seq)
      seq_node = ast
      expect(seq_node.parts).to have_attributes(length: 2)
      expect(seq_node.parts[0]).to be_a(Strling::Core::Quant)
      expect(seq_node.parts[1]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[1].at).to eq('End')
    end

    it 'should parse multiple anchors of same type' do
      # Tests multiple same anchors: ^^
      # Edge case: semantically redundant but syntactically valid.
      _flags, ast = parse('^^')
      expect(ast).to be_a(Strling::Core::Seq)
      seq_node = ast
      expect(seq_node.parts).to have_attributes(length: 2)
      expect(seq_node.parts[0]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[0].at).to eq('Start')
      expect(seq_node.parts[1]).to be_a(Strling::Core::Anchor)
      expect(seq_node.parts[1].at).to eq('Start')
    end
  end

  describe 'Category F: Anchors in Alternation' do
    # Tests for anchors used in alternation patterns.

    it 'should parse anchor in alternation branch' do
      # Tests anchor in one branch of alternation: ^a|b$
      # Parses as (^a)|(b$).
      _flags, ast = parse('^a|b$')
      expect(ast).to be_a(Strling::Core::Alt)
      alt_node = ast
      expect(alt_node.branches).to have_attributes(length: 2)

      # First branch: ^a
      branch0 = alt_node.branches[0]
      expect(branch0).to be_a(Strling::Core::Seq)
      expect(branch0.parts).to have_attributes(length: 2)
      expect(branch0.parts[0]).to be_a(Strling::Core::Anchor)
      expect(branch0.parts[0].at).to eq('Start')
      expect(branch0.parts[1]).to be_a(Strling::Core::Lit)

      # Second branch: b$
      branch1 = alt_node.branches[1]
      expect(branch1).to be_a(Strling::Core::Seq)
      expect(branch1.parts).to have_attributes(length: 2)
      expect(branch1.parts[0]).to be_a(Strling::Core::Lit)
      expect(branch1.parts[1]).to be_a(Strling::Core::Anchor)
      expect(branch1.parts[1].at).to eq('End')
    end
  end

  describe 'Category G: Anchors with Quantifiers' do
    # Tests confirming that anchors themselves cannot be quantified.

    it 'should raise error for anchor quantified directly (^*)' do
      # Tests that ^* raises an error (cannot quantify anchor).
      expect { parse('^*') }.to raise_error(Strling::Core::STRlingParseError, /Cannot quantify anchor/)
    end

    it 'should raise error for end anchor followed by quantifier ($+)' do
      # Tests $+ raises an error (cannot quantify anchor).
      expect { parse('$+') }.to raise_error(Strling::Core::STRlingParseError, /Cannot quantify anchor/)
    end
  end
end
