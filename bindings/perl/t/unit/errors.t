#!/usr/bin/env perl
#
# Test Design — errors.t
#
# ## Purpose
# This test suite serves as the single source of truth for defining and
# validating the error-handling contract of the entire STRling pipeline. It
# ensures that invalid inputs are rejected predictably and that diagnostics are
# stable, accurate, and helpful across all stages—from the parser to the CLI.
#
# ## Description
# This suite defines the expected behavior for all invalid, malformed, or
# unsupported inputs. It verifies that errors are raised at the correct stage
# (e.g., `ParseError`), contain a clear, human-readable message, and provide an
# accurate source location. A key invariant tested is the "first error wins"
# policy: for an input with multiple issues, only the error at the earliest
# position is reported.
#
# ## Scope
# -   **In scope:**
# -   `ParseError` exceptions raised by the parser for syntactic and lexical
# issues.
# -   `ValidationError` (or equivalent semantic errors) raised for
# syntactically valid but semantically incorrect patterns.
#
# -   Asserting error messages for a stable, recognizable substring and the
# correctness of the error's reported position.
#
# -   **Out of scope:**
# -   Correct handling of **valid** inputs (covered in other test suites).
#
# -   The exact, full wording of error messages (tests assert substrings).

use strict;
use warnings;
use Test::More;
use Test::Exception;
use FindBin;
use lib "$FindBin::Bin/../../lib";

use STRling::Core::parser qw(parse);
use STRling::Core::Errors;

subtest 'Grouping & Lookaround Errors' => sub {
    my @tests = (
        ['(abc', 'Unterminated group', 4, 'unterminated_group'],
        ['(?<nameabc)', 'Unterminated group name', 11, 'unterminated_named_group'],
        ['(?=abc', 'Unterminated lookahead', 6, 'unterminated_lookahead'],
        ['(?<=abc', 'Unterminated lookbehind', 7, 'unterminated_lookbehind'],
        ['(?i)abc', 'Inline modifiers', 1, 'unsupported_inline_modifier'],
    );
    
    for my $test (@tests) {
        my ($invalid_dsl, $error_prefix, $error_pos, $id) = @$test;
        subtest "should fail for \"$invalid_dsl\" (ID: $id)" => sub {
            dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
            
            eval { parse($invalid_dsl) };
            my $err = $@;
            isa_ok($err, 'STRling::Core::Errors::STRlingParseError', 'Error type');
            like($err->message, qr/\Q$error_prefix\E/, 'Error message contains expected prefix');
            is($err->pos, $error_pos, 'Error position is correct');
        };
    }
};

subtest 'Backreference & Naming Errors' => sub {
    my @tests = (
        ['\\k<later>(?<later>a)', 'Backreference to undefined group', 0, 'forward_reference_by_name'],
        ['\\2(a)(b)', 'Backreference to undefined group', 0, 'forward_reference_by_index'],
        ['(a)\\2', 'Backreference to undefined group', 3, 'nonexistent_reference_by_index'],
        ['\\k<', 'Unterminated named backref', 0, 'unterminated_named_backref'],
    );
    
    for my $test (@tests) {
        my ($invalid_dsl, $error_prefix, $error_pos, $id) = @$test;
        subtest "should fail for \"$invalid_dsl\" (ID: $id)" => sub {
            dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
            
            eval { parse($invalid_dsl) };
            my $err = $@;
            isa_ok($err, 'STRling::Core::Errors::STRlingParseError', 'Error type');
            like($err->message, qr/\Q$error_prefix\E/, 'Error message contains expected prefix');
            is($err->pos, $error_pos, 'Error position is correct');
        };
    }
    
    subtest 'duplicate group name raises error' => sub {
        dies_ok { parse('(?<name>a)(?<name>b)') } 'ParseError is thrown';
        
        eval { parse('(?<name>a)(?<name>b)') };
        like($@->message, qr/Duplicate group name/, 'Error message contains "Duplicate group name"');
    };
};

subtest 'Character Class Errors' => sub {
    my @tests = (
        ['[abc', 'Unterminated character class', 4, 'unterminated_class'],
        ['[\\p{L', 'Unterminated \\p{...}', 1, 'unterminated_unicode_property'],
        ['[\\pL]', 'Expected { after \\p/\\P', 1, 'missing_braces_on_unicode_property'],
    );
    
    for my $test (@tests) {
        my ($invalid_dsl, $error_prefix, $error_pos, $id) = @$test;
        subtest "should fail for \"$invalid_dsl\" (ID: $id)" => sub {
            dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
            
            eval { parse($invalid_dsl) };
            my $err = $@;
            isa_ok($err, 'STRling::Core::Errors::STRlingParseError', 'Error type');
            like($err->message, qr/\Q$error_prefix\E/, 'Error message contains expected prefix');
            is($err->pos, $error_pos, 'Error position is correct');
        };
    }
};

subtest 'Escape & Codepoint Errors' => sub {
    my @tests = (
        ['\\xG1', 'Invalid \\xHH escape', 0, 'invalid_hex_digit'],
        ['\\u12Z4', 'Invalid \\uHHHH', 0, 'invalid_unicode_digit'],
        ['\\x{', 'Unterminated \\x{...}', 0, 'unterminated_hex_brace_empty'],
        ['\\x{FFFF', 'Unterminated \\x{...}', 0, 'unterminated_hex_brace_with_digits'],
    );
    
    for my $test (@tests) {
        my ($invalid_dsl, $error_prefix, $error_pos, $id) = @$test;
        subtest "should fail for \"$invalid_dsl\" (ID: $id)" => sub {
            dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
            
            eval { parse($invalid_dsl) };
            my $err = $@;
            isa_ok($err, 'STRling::Core::Errors::STRlingParseError', 'Error type');
            like($err->message, qr/\Q$error_prefix\E/, 'Error message contains expected prefix');
            is($err->pos, $error_pos, 'Error position is correct');
        };
    }
};

subtest 'Quantifier Errors' => sub {
    subtest 'unterminated brace quantifier raises error' => sub {
        my $invalid_dsl = 'a{2,5';
        dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
        
        eval { parse($invalid_dsl) };
        my $err = $@;
        is($err->message, 'Incomplete quantifier', 'Error message is correct');
        is($err->pos, 5, 'Error position is correct');
    };
    
    subtest 'quantifying a non-quantifiable atom raises error' => sub {
        dies_ok { parse('^*') } 'ParseError is thrown';
        
        eval { parse('^*') };
        like($@->message, qr/Cannot quantify anchor/, 'Error message contains "Cannot quantify anchor"');
    };
};

subtest 'Invariant: First Error Wins' => sub {
    subtest 'first of multiple errors is reported' => sub {
        my $invalid_dsl = '[a|b(';
        dies_ok { parse($invalid_dsl) } 'ParseError is thrown';
        
        eval { parse($invalid_dsl) };
        my $err = $@;
        like($err->message, qr/Unterminated character class/, 'Error message contains "Unterminated character class"');
        is($err->pos, 5, 'Error position is correct');
    };
};

done_testing();
