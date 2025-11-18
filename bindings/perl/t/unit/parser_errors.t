#!/usr/bin/env perl
use strict;
use warnings;
use Test::More;

# Test Parser Error Messages - Comprehensive Validation of Rich Error Output
#
# This test suite validates that the parser produces rich, instructional error
# messages in the "Visionary State" format with:
#   - Context line showing the error location
#   - Caret (^) pointing to the exact position
#   - Helpful hints explaining how to fix the error
#
# These tests intentionally pass invalid syntax to ensure the error messages
# are helpful and educational.

use lib 'lib';
use STRling::Core::Parser qw(parse);
use STRling::Core::Errors;

# Rich Error Formatting
subtest 'Rich Error Formatting' => sub {
    subtest 'unmatched closing paren shows visionary format' => sub {
        eval { parse('(a|b))') };
        ok($@, 'throws error');
        
        if (my $err = $@) {
            isa_ok($err, 'STRling::Core::Errors::STRlingParseError');
            my $formatted = "$err";
            
            like($formatted, qr/STRling Parse Error:/, 'contains error header');
            like($formatted, qr/Unmatched '\)'/, 'contains error message');
            like($formatted, qr/> 1 \| \(a\|b\)\)/, 'contains context line');
            like($formatted, qr/\^/, 'contains caret pointer');
            like($formatted, qr/Hint:/, 'contains hint section');
            like($formatted, qr/Did you mean to escape it/, 'contains helpful hint');
        }
    };
    
    subtest 'unterminated group shows helpful hint' => sub {
        eval { parse('(abc') };
        if (my $err = $@) {
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/opened with '\('/, 'hint mentions opening paren');
            like($err->hint, qr/Add a matching '\)'/, 'hint suggests adding closing paren');
        }
    };
    
    subtest 'error on second line shows correct line number' => sub {
        my $pattern = "abc\n(def";
        eval { parse($pattern) };
        if (my $err = $@) {
            my $formatted = "$err";
            like($formatted, qr/> 2 \|/, 'shows line 2');
            like($formatted, qr/\(def/, 'shows context from line 2');
        }
    };
    
    subtest 'caret points to exact position' => sub {
        eval { parse('abc)') };
        if (my $err = $@) {
            my $formatted = "$err";
            my @lines = split /\n/, $formatted;
            
            for my $line (@lines) {
                if ($line =~ /^>   \|/) {
                    my $caret_line = substr($line, 6);
                    $caret_line =~ s/^\s+//;
                    is($caret_line, '^', 'caret is properly placed');
                    
                    # Count spaces before caret
                    my $spaces = length($line) - length($line =~ s/^>   \|\s*//r) - 1;
                    is($spaces, 3, 'caret points to position 3');
                }
            }
        }
    };
};

# Specific Error Hints
subtest 'Specific Error Hints' => sub {
    subtest 'alternation no lhs hint' => sub {
        eval { parse('|abc') };
        if (my $err = $@) {
            like($err->message, qr/Alternation lacks left-hand side/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/expression on the left side/, 'helpful hint about lhs');
        }
    };
    
    subtest 'alternation no rhs hint' => sub {
        eval { parse('abc|') };
        if (my $err = $@) {
            like($err->message, qr/Alternation lacks right-hand side/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/expression on the right side/, 'helpful hint about rhs');
        }
    };
    
    subtest 'unterminated char class hint' => sub {
        eval { parse('[abc') };
        if (my $err = $@) {
            like($err->message, qr/Unterminated character class/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/opened with '\['/, 'hint mentions opening bracket');
            like($err->hint, qr/Add a matching '\]'/, 'hint suggests adding closing bracket');
        }
    };
    
    subtest 'cannot quantify anchor hint' => sub {
        eval { parse('^*') };
        if (my $err = $@) {
            like($err->message, qr/Cannot quantify anchor/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/Anchors/, 'hint mentions anchors');
            like($err->hint, qr/match positions/, 'hint explains anchor behavior');
        }
    };
    
    subtest 'invalid hex escape hint' => sub {
        eval { parse('\xGG') };
        if (my $err = $@) {
            like($err->message, qr/Invalid \\xHH escape/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/hexadecimal digits/, 'hint explains hex requirement');
        }
    };
    
    subtest 'undefined backref hint' => sub {
        eval { parse('\1abc') };
        if (my $err = $@) {
            like($err->message, qr/Backreference to undefined group/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/previously captured groups/, 'hint explains group requirement');
            like($err->hint, qr/forward references/, 'hint mentions forward references');
        }
    };
    
    subtest 'duplicate group name hint' => sub {
        eval { parse('(?<name>a)(?<name>b)') };
        if (my $err = $@) {
            like($err->message, qr/Duplicate group name/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/unique name/, 'hint explains uniqueness requirement');
        }
    };
    
    subtest 'inline modifiers hint' => sub {
        eval { parse('(?i)abc') };
        if (my $err = $@) {
            like($err->message, qr/Inline modifiers/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/%flags/, 'hint mentions %flags directive');
            like($err->hint, qr/directive/, 'hint explains directive usage');
        }
    };
    
    subtest 'unterminated unicode property hint' => sub {
        eval { parse('[\p{Letter') };
        if (my $err = $@) {
            like($err->message, qr/Unterminated \\p\{\.\.\.}/, 'correct error message');
            ok(defined $err->hint, 'error has hint');
            like($err->hint, qr/syntax \\p\{Property}/, 'hint shows correct syntax');
        }
    };
};

# Complex Error Scenarios
subtest 'Complex Error Scenarios' => sub {
    subtest 'nested groups error shows outermost' => sub {
        eval { parse('((abc') };
        if (my $err = $@) {
            like($err->message, qr/Unterminated group/, 'correct error message');
        }
    };
    
    subtest 'error in alternation branch' => sub {
        eval { parse('a|(b') };
        if (my $err = $@) {
            like($err->message, qr/Unterminated group/, 'correct error message');
            is($err->pos, 4, 'position points to end where ) is expected');
        }
    };
    
    subtest 'error with free spacing mode' => sub {
        my $pattern = "%flags x\n(abc\n  def";
        eval { parse($pattern) };
        if (my $err = $@) {
            ok(defined $err->hint, 'error has hint in free spacing mode');
        }
    };
    
    subtest 'error position accuracy' => sub {
        eval { parse('abc{2,') };
        if (my $err = $@) {
            like($err->message, qr/Incomplete quantifier/, 'correct error message');
            is($err->pos, 6, 'position points to end where } is expected');
        }
    };
};

# Error Backward Compatibility
subtest 'Error Backward Compatibility' => sub {
    subtest 'error has message attribute' => sub {
        eval { parse('(') };
        if (my $err = $@) {
            ok(defined $err->message, 'error has message attribute');
            is($err->message, 'Unterminated group', 'correct message');
        }
    };
    
    subtest 'error has pos attribute' => sub {
        eval { parse('abc)') };
        if (my $err = $@) {
            ok(defined $err->pos, 'error has pos attribute');
            is($err->pos, 3, 'correct position');
        }
    };
    
    subtest 'error string contains position' => sub {
        eval { parse(')') };
        if (my $err = $@) {
            my $formatted = "$err";
            like($formatted, qr/>/, 'contains line markers');
            like($formatted, qr/\^/, 'contains caret pointer');
        }
    };
};

done_testing();
