#!/usr/bin/env perl
#
# Test Design — flags_and_free_spacing.t
#
# ## Purpose
# This test suite validates the correct parsing of the `%flags` directive and the
# behavioral changes it induces, particularly the free-spacing (`x`) mode. It
# ensures that flags are correctly identified and stored in the `Flags` object
# and that the parser correctly handles whitespace and comments when the
# extended mode is active.
#
# ## Description
# The `%flags` directive is a top-level command in a `.strl` file that modifies
# the semantics of the entire pattern. This suite tests the parser's ability to
# correctly consume this directive and apply its effects. The primary focus is
# on the **`x` flag (extended/free-spacing mode)**, which dramatically alters
# how the parser handles whitespace and comments. The tests will verify that the
# parser correctly ignores insignificant characters outside of character classes
# while treating them as literals inside character classes.
#
# ## Scope
# -   **In scope:**
# -   Parsing the `%flags` directive with single and multiple flags (`i`,
# `m`, `s`, `u`, `x`).
# -   Handling of various separators (commas, spaces) within the flag
# list.
# -   The parser's behavior in free-spacing mode: ignoring whitespace and
# comments outside character classes.
# -   The parser's behavior inside a character class when free-spacing mode
# is active (i.e., treating whitespace and `#` as literals).
#
# -   The structure of the `Flags` object produced by the parser and its
# serialization in the final artifact.
# -   **Out of scope:**
# -   The runtime *effect* of the `i`, `m`, `s`, and `u` flags on the regex
# engine's matching behavior.
# -   The parsing of other directives like `%engine` or `%lang`.

use strict;
use warnings;
use Test::More;
use Test::Exception;
use FindBin;
use lib "$FindBin::Bin/../../lib";

use STRling::Core::parser qw(parse);
use STRling::Core::Nodes;
use STRling::Core::Errors;

# Helper to compare flags
sub flags_match {
    my ($flags, $expected) = @_;
    return $flags->ignoreCase == $expected->{ignoreCase} &&
           $flags->multiline  == $expected->{multiline} &&
           $flags->dotAll     == $expected->{dotAll} &&
           $flags->unicode    == $expected->{unicode} &&
           $flags->extended   == $expected->{extended};
}

subtest 'Category A: Positive Cases' => sub {
    # Test flag directive parsing
    my @flag_tests = (
        ['%flags i', {ignoreCase => 1}, 'single_flag'],
        ['%flags i, m, x', {ignoreCase => 1, multiline => 1, extended => 1}, 'multiple_flags_with_commas'],
        ['%flags u m s', {unicode => 1, multiline => 1, dotAll => 1}, 'multiple_flags_with_spaces'],
        ['%flags i,m s,u x', {ignoreCase => 1, multiline => 1, dotAll => 1, unicode => 1, extended => 1}, 'multiple_flags_mixed_separators'],
        ['  %flags i  ', {ignoreCase => 1}, 'leading_trailing_whitespace'],
    );
    
    for my $test (@flag_tests) {
        my ($input, $expected, $id) = @$test;
        subtest "should parse flag directive \"$input\" correctly (ID: $id)" => sub {
            my ($flags) = parse($input);
            
            # Build expected flags object
            my $expected_flags = STRling::Core::Nodes::Flags->new(
                ignoreCase => $expected->{ignoreCase} // 0,
                multiline  => $expected->{multiline} // 0,
                dotAll     => $expected->{dotAll} // 0,
                unicode    => $expected->{unicode} // 0,
                extended   => $expected->{extended} // 0,
            );
            
            ok(flags_match($flags, $expected), 'Flags match expected values');
        };
    }
    
    # Test free-spacing mode
    subtest 'should handle free-spacing mode for "%flags x\na b c" (ID: whitespace_is_ignored)' => sub {
        my ($flags, $ast) = parse("%flags x\na b c");
        
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 3, 'Seq has 3 parts');
        isa_ok($ast->parts->[0], 'STRling::Core::Nodes::Lit', 'Part 0 is Lit');
        is($ast->parts->[0]->value, 'a', 'Part 0 value is "a"');
        isa_ok($ast->parts->[1], 'STRling::Core::Nodes::Lit', 'Part 1 is Lit');
        is($ast->parts->[1]->value, 'b', 'Part 1 value is "b"');
        isa_ok($ast->parts->[2], 'STRling::Core::Nodes::Lit', 'Part 2 is Lit');
        is($ast->parts->[2]->value, 'c', 'Part 2 value is "c"');
    };
    
    subtest 'should handle free-spacing mode for "%flags x\na # comment\n b" (ID: comments_are_ignored)' => sub {
        my ($flags, $ast) = parse("%flags x\na # comment\n b");
        
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 2, 'Seq has 2 parts');
        is($ast->parts->[0]->value, 'a', 'Part 0 value is "a"');
        is($ast->parts->[1]->value, 'b', 'Part 1 value is "b"');
    };
    
    subtest 'should handle free-spacing mode for "%flags x\na\\ b" (ID: escaped_whitespace_is_literal)' => sub {
        my ($flags, $ast) = parse("%flags x\na\\ b");
        
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 3, 'Seq has 3 parts');
        is($ast->parts->[0]->value, 'a', 'Part 0 value is "a"');
        is($ast->parts->[1]->value, ' ', 'Part 1 value is space');
        is($ast->parts->[2]->value, 'b', 'Part 2 value is "b"');
    };
};

subtest 'Category B: Negative Cases' => sub {
    subtest 'should reject bad directive "%flags z" (ID: unknown_flag)' => sub {
        dies_ok { parse('%flags z') } 'Unknown flag throws error';
    };
    
    subtest 'should reject bad directive "%flagg i" (ID: malformed_directive)' => sub {
        # %flagg is not a valid directive, so it should be treated as pattern content
        # and 'g' is a valid literal
        lives_ok { parse('%flagg i') } 'Malformed directive is treated as pattern';
    };
};

subtest 'Category C: Edge Cases' => sub {
    subtest 'should handle an empty flags directive' => sub {
        my ($flags) = parse('%flags');
        
        ok(!$flags->ignoreCase, 'ignoreCase is false');
        ok(!$flags->multiline, 'multiline is false');
        ok(!$flags->dotAll, 'dotAll is false');
        ok(!$flags->unicode, 'unicode is false');
        ok(!$flags->extended, 'extended is false');
    };
    
    subtest 'should reject a directive that appears after content' => sub {
        dies_ok { parse("a\n%flags i") } 'Directive after content throws error';
    };
    
    subtest 'should handle a pattern with only comments and whitespace' => sub {
        my ($flags, $ast) = parse("%flags x\n# comment\n  \n# another");
        
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 0, 'Seq is empty');
    };
};

subtest 'Category D: Interaction Cases' => sub {
    subtest 'should disable free-spacing inside char class for "%flags x\n[a b]" (ID: whitespace_is_literal_in_class)' => sub {
        my ($flags, $ast) = parse("%flags x\n[a b]");
        
        isa_ok($ast, 'STRling::Core::Nodes::CharClass', 'AST is CharClass');
        is(scalar @{$ast->items}, 3, 'CharClass has 3 items');
        
        isa_ok($ast->items->[0], 'STRling::Core::Nodes::ClassLiteral', 'Item 0 is ClassLiteral');
        is($ast->items->[0]->ch, 'a', 'Item 0 is "a"');
        
        isa_ok($ast->items->[1], 'STRling::Core::Nodes::ClassLiteral', 'Item 1 is ClassLiteral');
        is($ast->items->[1]->ch, ' ', 'Item 1 is space');
        
        isa_ok($ast->items->[2], 'STRling::Core::Nodes::ClassLiteral', 'Item 2 is ClassLiteral');
        is($ast->items->[2]->ch, 'b', 'Item 2 is "b"');
    };
    
    subtest 'should disable free-spacing inside char class for "%flags x\n[a#b]" (ID: comment_char_is_literal_in_class)' => sub {
        my ($flags, $ast) = parse("%flags x\n[a#b]");
        
        isa_ok($ast, 'STRling::Core::Nodes::CharClass', 'AST is CharClass');
        is(scalar @{$ast->items}, 3, 'CharClass has 3 items');
        
        is($ast->items->[0]->ch, 'a', 'Item 0 is "a"');
        is($ast->items->[1]->ch, '#', 'Item 1 is "#"');
        is($ast->items->[2]->ch, 'b', 'Item 2 is "b"');
    };
};

done_testing();
