#!/usr/bin/env perl
#
# Test Design — us_phone.t
#
# ## Purpose
# This test suite validates the STRling::Simply fluent API by building
# a US phone number pattern and verifying that it compiles to the expected
# regex output.
#
# This serves as a verification test for the "Operation Polish (Redux)" initiative,
# ensuring that the Perl binding provides a clean, fluent API that matches
# the Gold Standard (TypeScript/Python) pattern.

use strict;
use warnings;
use Test::More;
use FindBin;
use lib "$FindBin::Bin/../lib";

use STRling::Simply qw(:all);

subtest 'US Phone Pattern - Basic Construction' => sub {
    plan tests => 1;
    
    # Build the pattern using the Simply API
    my $phone = merge(
        start(),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(4)),
        end()
    );
    
    # Verify we got a Pattern object
    isa_ok($phone, 'STRling::Simply::Pattern', 'phone pattern is a Pattern object');
};

subtest 'US Phone Pattern - Compilation' => sub {
    plan tests => 1;
    
    # Build the pattern
    my $phone = merge(
        start(),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(4)),
        end()
    );
    
    # Compile to regex
    my $regex = $phone->compile();
    
    # Expected output: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
    is($regex, '^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$', 'compiled regex matches expected output');
};

subtest 'US Phone Pattern - Regex Matching' => sub {
    plan tests => 6;
    
    # Build the pattern
    my $phone = merge(
        start(),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(4)),
        end()
    );
    
    my $regex = $phone->compile();
    
    # Test valid phone numbers
    like('555-0199', qr/$regex/, 'matches phone with hyphens');
    like('555.0199', qr/$regex/, 'matches phone with dots');
    like('555 0199', qr/$regex/, 'matches phone with spaces');
    like('5550199', qr/$regex/, 'matches phone with no separators');
    
    # Test invalid phone numbers
    unlike('55-0199', qr/^$regex$/, 'rejects phone with too few area code digits');
    unlike('555-019', qr/^$regex$/, 'rejects phone with too few last digits');
};

subtest 'US Phone Pattern - Capture Groups' => sub {
    plan tests => 4;
    
    # Build the pattern
    my $phone = merge(
        start(),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(3)),
        may(any_of("-. ")),
        capture(digit(4)),
        end()
    );
    
    my $regex = $phone->compile();
    
    # Test capture groups
    my $test_number = '555-123-4567';
    if ($test_number =~ /$regex/) {
        is($1, '555', 'first capture group extracts area code');
        is($2, '123', 'second capture group extracts exchange');
        is($3, '4567', 'third capture group extracts subscriber number');
        pass('all capture groups extracted successfully');
    } else {
        fail('pattern did not match test number');
        fail('could not test capture group 1');
        fail('could not test capture group 2');
        fail('could not test capture group 3');
    }
};

subtest 'Simply API - Individual Components' => sub {
    plan tests => 10;
    
    # Test individual functions return Pattern objects
    isa_ok(start(), 'STRling::Simply::Pattern', 'start() returns Pattern');
    isa_ok(end(), 'STRling::Simply::Pattern', 'end() returns Pattern');
    isa_ok(digit(), 'STRling::Simply::Pattern', 'digit() returns Pattern');
    isa_ok(digit(3), 'STRling::Simply::Pattern', 'digit(3) returns Pattern');
    isa_ok(any_of("abc"), 'STRling::Simply::Pattern', 'any_of() returns Pattern');
    isa_ok(lit("hello"), 'STRling::Simply::Pattern', 'lit() returns Pattern');
    
    # Test compilation of individual components
    is(start()->compile(), '^', 'start() compiles to ^');
    is(end()->compile(), '$', 'end() compiles to $');
    is(digit(3)->compile(), '\d{3}', 'digit(3) compiles to \d{3}');
    is(any_of("-. ")->compile(), '[-. ]', 'any_of("-. ") compiles to [-. ]');
};

subtest 'Simply API - Pattern Composition' => sub {
    plan tests => 3;
    
    # Test that patterns can be composed
    my $area_code = digit(3);
    my $separator = may(any_of("-. "));
    my $exchange = digit(3);
    
    my $composed = merge($area_code, $separator, $exchange);
    isa_ok($composed, 'STRling::Simply::Pattern', 'composed pattern is a Pattern object');
    
    my $regex = $composed->compile();
    is($regex, '\d{3}[-. ]?\d{3}', 'composed pattern compiles correctly');
    
    like('555-123', qr/$regex/, 'composed pattern matches correctly');
};

done_testing();
