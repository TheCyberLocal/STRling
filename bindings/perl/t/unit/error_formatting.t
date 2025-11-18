#!/usr/bin/env perl
#
# Test Design — error_formatting.t
#
# ## Purpose
# Tests formatting of `STRlingParseError` and the behavior of the hint engine.
# Ensures formatted errors include source context, caret positioning, and
# that the hint engine returns contextual guidance where appropriate.

use strict;
use warnings;
use Test::More;
use FindBin;
use lib "$FindBin::Bin/../../lib";

use STRling::Core::Errors;
use STRling::Core::HintEngine qw(get_hint);

subtest 'Intelligent Error Handling Gap Coverage' => sub {
    subtest 'STRlingParseError' => sub {
        subtest 'simple error without text' => sub {
            my $err = STRling::Core::Errors::STRlingParseError->new(
                message => 'Test error',
                pos     => 5
            );
            my $str = "$err";  # Stringify via overload
            like($str, qr/Test error at position 5/, 'Error message includes position');
        };
        
        subtest 'error with text and hint' => sub {
            my $text = '(a|b))';
            my $err = STRling::Core::Errors::STRlingParseError->new(
                message => "Unmatched ')'",
                pos     => 5,
                text    => $text,
                hint    => "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
            );
            my $formatted = $err->to_formatted_string();
            
            # Check that it contains the expected parts
            like($formatted, qr/STRling Parse Error: Unmatched '\)'/, 'Contains error type');
            like($formatted, qr/> 1 \| \(a\|b\)\)/, 'Contains source line');
            like($formatted, qr/\^/, 'Contains caret indicator');
            like($formatted, qr/Hint:/, 'Contains hint marker');
            like($formatted, qr/does not have a matching opening '\('/, 'Contains hint text');
        };
        
        subtest 'error position indicator' => sub {
            my $text = 'abc def';
            my $err = STRling::Core::Errors::STRlingParseError->new(
                message => 'Error at d',
                pos     => 4,
                text    => $text
            );
            my $formatted = $err->to_formatted_string();
            
            # The caret should be under 'd' (position 4)
            my @lines = split /\n/, $formatted;
            my $found = 0;
            for my $line (@lines) {
                if ($line =~ /^>   \| (.*)$/) {
                    # Count spaces before ^
                    my $caret_line = $1;
                    my $spaces_before_caret = length($caret_line) - length($caret_line =~ s/^ +//r);
                    is($spaces_before_caret, 4, 'Caret is at position 4');
                    $found = 1;
                    last;
                }
            }
            ok($found, 'Found caret line');
        };
        
        subtest 'multiline error' => sub {
            my $text = "abc\ndef\nghi";
            my $err = STRling::Core::Errors::STRlingParseError->new(
                message => 'Error on line 2',
                pos     => 5,
                text    => $text
            );
            my $formatted = $err->to_formatted_string();
            
            # Should show line 2
            like($formatted, qr/> 2 \| def/, 'Shows correct line number');
        };
        
        subtest 'toFormattedString method' => sub {
            my $err = STRling::Core::Errors::STRlingParseError->new(
                message => 'Test',
                pos     => 0,
                text    => 'abc'
            );
            is($err->to_formatted_string(), "$err", 'to_formatted_string equals stringify');
        };
    };
    
    subtest 'HintEngine' => sub {
        subtest 'unterminated group hint' => sub {
            my $hint = get_hint('Unterminated group', '(abc', 4);
            ok(defined $hint, 'Hint is defined');
            like($hint, qr/opened with '\('/,  "Contains 'opened with'");
            like($hint, qr/Add a matching '\)'/, "Contains 'Add a matching'");
        };
        
        subtest 'unterminated character class hint' => sub {
            my $hint = get_hint('Unterminated character class', '[abc', 4);
            ok(defined $hint, 'Hint is defined');
            like($hint, qr/opened with '\['/,  "Contains 'opened with'");
            like($hint, qr/Add a matching '\]'/, "Contains 'Add a matching'");
        };
        
        subtest 'unexpected token hint - closing paren' => sub {
            my $hint = get_hint('Unexpected token', 'abc)', 3);
            ok(defined $hint, 'Hint is defined');
            like($hint, qr/does not have a matching opening '\('/, 'Contains matching hint');
            like($hint, qr/escape it with/, 'Contains escape hint');
        };
        
        subtest 'cannot quantify anchor hint' => sub {
            my $hint = get_hint('Cannot quantify anchor', '^*', 1);
            ok(defined $hint, 'Hint is defined');
            like($hint, qr/Anchors/, 'Contains Anchors');
            like($hint, qr/match positions/, 'Contains match positions');
            like($hint, qr/cannot be quantified/, 'Contains cannot be quantified');
        };
        
        subtest 'inline modifiers hint' => sub {
            my $hint = get_hint(
                'Inline modifiers `(?imsx)` are not supported',
                '(?i)abc',
                1
            );
            ok(defined $hint, 'Hint is defined');
            like($hint, qr/%flags/, 'Contains %flags');
            like($hint, qr/directive/, 'Contains directive');
        };
        
        subtest 'no hint for unknown error' => sub {
            my $hint = get_hint('Some unknown error message', 'abc', 0);
            ok(!defined $hint, 'No hint for unknown error');
        };
    };
};

done_testing();
