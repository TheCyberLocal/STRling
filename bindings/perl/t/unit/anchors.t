#!/usr/bin/env perl
#
# Test Design — anchors.t
#
# ## Purpose
# This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
# It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
# with the proper type and that its parsing is unaffected by flags or surrounding
# constructs.

use strict;
use warnings;
use Test::More;
use Test::Exception;
use FindBin;
use lib "$FindBin::Bin/../../lib";

use STRling::Core::parser qw(parse);
use STRling::Core::Nodes;

subtest 'Category A: Positive Cases' => sub {
    my @tests = (
        # Core Line Anchors
        ['^', 'Start', 'line_start'],
        ['$', 'End', 'line_end'],
        # Core Word Boundary Anchors
        ['\\b', 'WordBoundary', 'word_boundary'],
        ['\\B', 'NotWordBoundary', 'not_word_boundary'],
        # Absolute Anchors (Extension Features)
        ['\\A', 'AbsoluteStart', 'absolute_start_ext'],
        ['\\Z', 'EndBeforeFinalNewline', 'end_before_newline_ext'],
    );
    
    for my $test (@tests) {
        my ($input, $expected_at, $id) = @$test;
        subtest "should parse anchor '$input' (ID: $id)" => sub {
            my ($flags, $ast) = parse($input);
            isa_ok($ast, 'STRling::Core::Nodes::Anchor', 'AST is Anchor');
            is($ast->at, $expected_at, "Anchor 'at' value is $expected_at");
        };
    }
};

subtest 'Category B: Negative Cases' => sub {
    # This category is intentionally empty. Anchors are single, unambiguous
    # tokens, and there are no anchor-specific parse errors.
    pass('No anchor-specific parse errors');
};

subtest 'Category C: Edge Cases' => sub {
    subtest 'should parse a pattern with only anchors' => sub {
        my ($flags, $ast) = parse('^\\A\\b$');
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 4, 'Sequence has 4 parts');
        
        for my $part (@{$ast->parts}) {
            isa_ok($part, 'STRling::Core::Nodes::Anchor', 'Part is Anchor');
        }
        
        my @at_values = map { $_->at } @{$ast->parts};
        is_deeply(\@at_values, ['Start', 'AbsoluteStart', 'WordBoundary', 'End'], 
                  'Anchor values are correct');
    };
    
    my @position_tests = (
        ['^a', 0, 'Start', 'at_start'],
        ['a\\bb', 1, 'WordBoundary', 'in_middle'],
        ['ab$', 1, 'End', 'at_end'],
    );
    
    for my $test (@position_tests) {
        my ($input, $pos, $expected_at, $id) = @$test;
        subtest "should parse anchors in different positions (ID: $id)" => sub {
            my ($flags, $ast) = parse($input);
            isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
            my $anchor = $ast->parts->[$pos];
            isa_ok($anchor, 'STRling::Core::Nodes::Anchor', 'Part is Anchor');
            is($anchor->at, $expected_at, "Anchor 'at' value is $expected_at");
        };
    }
};

subtest 'Category D: Interaction Cases' => sub {
    subtest 'should not change the parsed AST when multiline flag is present' => sub {
        my ($flags1, $ast1) = parse('^a$');
        my ($flags2, $ast2) = parse("%flags m\n^a\$");
        
        isa_ok($ast1, 'STRling::Core::Nodes::Seq', 'AST without m flag is Seq');
        isa_ok($ast2, 'STRling::Core::Nodes::Seq', 'AST with m flag is Seq');
        
        # Check structure is same
        is(scalar @{$ast1->parts}, 3, 'AST1 has 3 parts');
        is(scalar @{$ast2->parts}, 3, 'AST2 has 3 parts');
        
        isa_ok($ast1->parts->[0], 'STRling::Core::Nodes::Anchor', 'First part is Anchor');
        is($ast1->parts->[0]->at, 'Start', 'First anchor is Start');
        
        isa_ok($ast1->parts->[2], 'STRling::Core::Nodes::Anchor', 'Third part is Anchor');
        is($ast1->parts->[2]->at, 'End', 'Third anchor is End');
    };
    
    my @group_tests = (
        ['(^a)', 'STRling::Core::Nodes::Group', 'Start', 'in_capturing_group'],
        ['(?:a\\b)', 'STRling::Core::Nodes::Group', 'WordBoundary', 'in_noncapturing_group'],
        ['(?=a$)', 'STRling::Core::Nodes::Look', 'End', 'in_lookahead'],
        ['(?<=^a)', 'STRling::Core::Nodes::Look', 'Start', 'in_lookbehind'],
    );
    
    for my $test (@group_tests) {
        my ($input, $container_type, $expected_at, $id) = @$test;
        subtest "should parse anchors inside groups and lookarounds (ID: $id)" => sub {
            my ($flags, $ast) = parse($input);
            isa_ok($ast, $container_type, "AST is $container_type");
            
            # Find the anchor in the container's body
            my $anchor;
            if (ref($ast->body) eq 'STRling::Core::Nodes::Seq') {
                for my $part (@{$ast->body->parts}) {
                    if (ref($part) eq 'STRling::Core::Nodes::Anchor') {
                        $anchor = $part;
                        last;
                    }
                }
            } elsif (ref($ast->body) eq 'STRling::Core::Nodes::Anchor') {
                $anchor = $ast->body;
            }
            
            ok($anchor, 'Found anchor in container');
            isa_ok($anchor, 'STRling::Core::Nodes::Anchor', 'Found node is Anchor');
            is($anchor->at, $expected_at, "Anchor 'at' value is $expected_at");
        };
    }
};

subtest 'Category E: Anchors in Complex Sequences' => sub {
    subtest 'should parse anchor between quantified atoms' => sub {
        my ($flags, $ast) = parse('a*^b+');
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 3, 'Sequence has 3 parts');
        
        isa_ok($ast->parts->[0], 'STRling::Core::Nodes::Quant', 'Part 0 is Quant');
        isa_ok($ast->parts->[1], 'STRling::Core::Nodes::Anchor', 'Part 1 is Anchor');
        is($ast->parts->[1]->at, 'Start', 'Anchor is Start');
        isa_ok($ast->parts->[2], 'STRling::Core::Nodes::Quant', 'Part 2 is Quant');
    };
    
    subtest 'should parse anchor after quantified group' => sub {
        my ($flags, $ast) = parse('(ab)*$');
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 2, 'Sequence has 2 parts');
        
        isa_ok($ast->parts->[0], 'STRling::Core::Nodes::Quant', 'Part 0 is Quant');
        isa_ok($ast->parts->[1], 'STRling::Core::Nodes::Anchor', 'Part 1 is Anchor');
        is($ast->parts->[1]->at, 'End', 'Anchor is End');
    };
    
    subtest 'should parse multiple anchors of same type' => sub {
        my ($flags, $ast) = parse('^^');
        isa_ok($ast, 'STRling::Core::Nodes::Seq', 'AST is Seq');
        is(scalar @{$ast->parts}, 2, 'Sequence has 2 parts');
        
        isa_ok($ast->parts->[0], 'STRling::Core::Nodes::Anchor', 'Part 0 is Anchor');
        is($ast->parts->[0]->at, 'Start', 'First anchor is Start');
        isa_ok($ast->parts->[1], 'STRling::Core::Nodes::Anchor', 'Part 1 is Anchor');
        is($ast->parts->[1]->at, 'Start', 'Second anchor is Start');
    };
};

subtest 'Category F: Anchors in Alternation' => sub {
    subtest 'should parse anchor in alternation branch' => sub {
        my ($flags, $ast) = parse('^a|b$');
        isa_ok($ast, 'STRling::Core::Nodes::Alt', 'AST is Alt');
        is(scalar @{$ast->branches}, 2, 'Alt has 2 branches');
        
        # First branch: ^a
        my $branch0 = $ast->branches->[0];
        isa_ok($branch0, 'STRling::Core::Nodes::Seq', 'Branch 0 is Seq');
        is(scalar @{$branch0->parts}, 2, 'Branch 0 has 2 parts');
        isa_ok($branch0->parts->[0], 'STRling::Core::Nodes::Anchor', 'Branch 0 part 0 is Anchor');
        is($branch0->parts->[0]->at, 'Start', 'Anchor is Start');
        
        # Second branch: b$
        my $branch1 = $ast->branches->[1];
        isa_ok($branch1, 'STRling::Core::Nodes::Seq', 'Branch 1 is Seq');
        is(scalar @{$branch1->parts}, 2, 'Branch 1 has 2 parts');
        isa_ok($branch1->parts->[1], 'STRling::Core::Nodes::Anchor', 'Branch 1 part 1 is Anchor');
        is($branch1->parts->[1]->at, 'End', 'Anchor is End');
    };
    
    subtest 'should parse anchors in group alternation' => sub {
        my ($flags, $ast) = parse('(^|$)');
        isa_ok($ast, 'STRling::Core::Nodes::Group', 'AST is Group');
        ok($ast->capturing, 'Group is capturing');
        
        isa_ok($ast->body, 'STRling::Core::Nodes::Alt', 'Body is Alt');
        is(scalar @{$ast->body->branches}, 2, 'Alt has 2 branches');
        
        isa_ok($ast->body->branches->[0], 'STRling::Core::Nodes::Anchor', 'Branch 0 is Anchor');
        is($ast->body->branches->[0]->at, 'Start', 'First anchor is Start');
        
        isa_ok($ast->body->branches->[1], 'STRling::Core::Nodes::Anchor', 'Branch 1 is Anchor');
        is($ast->body->branches->[1]->at, 'End', 'Second anchor is End');
    };
};

done_testing();
