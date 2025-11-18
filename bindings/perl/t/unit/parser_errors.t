#!/usr/bin/env perl
#
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

use strict;
use warnings;
use Test::More;
use Test::Exception;
use FindBin;
use lib "$FindBin::Bin/../../lib";

use STRling::Core::parser qw(parse);
use STRling::Core::Errors;

subtest 'Rich Error Formatting' => sub {
    subtest 'unmatched closing paren shows visionary format' => sub {
        dies_ok { parse('(a|b))') } 'parse throws on unmatched )';
        
        eval { parse('(a|b))') };
        my $err = $@;
        isa_ok($err, 'STRling::Core::Errors::STRlingParseError');
        
        my $formatted = "$err";
        
        # Check all components of visionary format
        like($formatted, qr/STRling Parse Error:/, 'Contains error header');
        like($formatted, qr/Unmatched '\)'/, 'Contains error message');
        like($formatted, qr/> 1 \| \(a\|b\)\)/, 'Contains source line');
        like($formatted, qr/\^/, 'Contains caret indicator');
        like($formatted, qr/Hint:/, 'Contains hint marker');
        like($formatted, qr/Did you mean to escape it/, 'Contains escape hint');
    };
    
    subtest 'unterminated group shows helpful hint' => sub {
        eval { parse('(abc') };
        my $err = $@;
        isa_ok($err, 'STRling::Core::Errors::STRlingParseError');
        
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/opened with '\('/, "Contains 'opened with'");
        like($err->hint, qr/Add a matching '\)'/, "Contains 'Add a matching'");
    };
    
    subtest 'error on second line shows correct line number' => sub {
        my $pattern = "abc\n(def";
        eval { parse($pattern) };
        my $err = $@;
        
        my $formatted = "$err";
        like($formatted, qr/> 2 \|/, 'Shows line 2');
        like($formatted, qr/\(def/, 'Contains error line content');
    };
    
    subtest 'caret points to exact position' => sub {
        eval { parse('abc)') };
        my $err = $@;
        
        my $formatted = "$err";
        my @lines = split /\n/, $formatted;
        
        # Find the line with the caret
        my $found = 0;
        for my $line (@lines) {
            if ($line =~ /^>   \| (.*)$/) {
                my $caret_line = $1;
                # Caret should be at position 3 (under ')')
                is($caret_line =~ s/\s//gr, '^', 'Caret is the only character');
                my $spaces = length($caret_line) - length($caret_line =~ s/^ +//r);
                is($spaces, 3, 'Caret is at position 3');
                $found = 1;
                last;
            }
        }
        ok($found, 'Found caret line');
    };
};

subtest 'Specific Error Hints' => sub {
    subtest 'alternation no lhs hint' => sub {
        eval { parse('|abc') };
        my $err = $@;
        
        like($err->message, qr/Alternation lacks left-hand side/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/expression on the left side/, 'Contains left side hint');
    };
    
    subtest 'alternation no rhs hint' => sub {
        eval { parse('abc|') };
        my $err = $@;
        
        like($err->message, qr/Alternation lacks right-hand side/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/expression on the right side/, 'Contains right side hint');
    };
    
    subtest 'unterminated char class hint' => sub {
        eval { parse('[abc') };
        my $err = $@;
        
        like($err->message, qr/Unterminated character class/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/opened with '\['/, "Contains 'opened with'");
        like($err->hint, qr/Add a matching '\]'/, "Contains 'Add a matching'");
    };
    
    subtest 'cannot quantify anchor hint' => sub {
        eval { parse('^*') };
        my $err = $@;
        
        like($err->message, qr/Cannot quantify anchor/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/Anchors/, 'Contains Anchors');
        like($err->hint, qr/match positions/, 'Contains match positions');
    };
    
    subtest 'invalid hex escape hint' => sub {
        eval { parse('\\xGG') };
        my $err = $@;
        
        like($err->message, qr/Invalid \\xHH escape/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/hexadecimal digits/, 'Contains hexadecimal hint');
    };
    
    subtest 'undefined backref hint' => sub {
        eval { parse('\\1abc') };
        my $err = $@;
        
        like($err->message, qr/Backreference to undefined group/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/previously captured groups/, 'Contains captured groups hint');
        like($err->hint, qr/forward references/, 'Contains forward references hint');
    };
    
    subtest 'duplicate group name hint' => sub {
        eval { parse('(?<name>a)(?<name>b)') };
        my $err = $@;
        
        like($err->message, qr/Duplicate group name/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/unique name/, 'Contains unique name hint');
    };
    
    subtest 'inline modifiers hint' => sub {
        eval { parse('(?i)abc') };
        my $err = $@;
        
        like($err->message, qr/Inline modifiers/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/%flags/, 'Contains %flags');
        like($err->hint, qr/directive/, 'Contains directive');
    };
    
    subtest 'unterminated unicode property hint' => sub {
        eval { parse('[\\p{Letter') };
        my $err = $@;
        
        like($err->message, qr/Unterminated \\p\{\.\.\.}/, 'Error message correct');
        ok(defined $err->hint, 'Hint is defined');
        like($err->hint, qr/syntax \\p\{Property}/, 'Contains property syntax hint');
    };
};

subtest 'Complex Error Scenarios' => sub {
    subtest 'nested groups error shows outermost' => sub {
        eval { parse('((abc') };
        my $err = $@;
        
        like($err->message, qr/Unterminated group/, 'Error message correct');
    };
    
    subtest 'error in alternation branch' => sub {
        eval { parse('a|(b') };
        my $err = $@;
        
        like($err->message, qr/Unterminated group/, 'Error message correct');
        # Position should point to the end where ')' is expected
        is($err->pos, 4, 'Error position is correct');
    };
    
    subtest 'error with free spacing mode' => sub {
        my $pattern = "%flags x\n(abc\n  def";
        eval { parse($pattern) };
        my $err = $@;
        
        ok(defined $err->hint, 'Hint is defined for free spacing mode error');
    };
    
    subtest 'error position accuracy' => sub {
        eval { parse('abc{2,') };
        my $err = $@;
        
        like($err->message, qr/Incomplete quantifier/, 'Error message correct');
        # Position should be at the end where '}' is expected
        is($err->pos, 6, 'Error position is correct');
    };
};

subtest 'Error Backward Compatibility' => sub {
    subtest 'error has message attribute' => sub {
        eval { parse('(') };
        my $err = $@;
        
        ok(defined $err->message, 'Error has message attribute');
        is($err->message, 'Unterminated group', 'Message is correct');
    };
    
    subtest 'error has pos attribute' => sub {
        eval { parse('abc)') };
        my $err = $@;
        
        ok(defined $err->pos, 'Error has pos attribute');
        is($err->pos, 3, 'Position is correct');
    };
    
    subtest 'error string contains position' => sub {
        eval { parse(')') };
        my $err = $@;
        
        my $formatted = "$err";
        # Should contain position information in the formatted output
        like($formatted, qr/>/, 'Contains line markers');
        like($formatted, qr/\^/, 'Contains caret pointer');
    };
};

done_testing();
