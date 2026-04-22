use strict;
use warnings;
use 5.014;
use Test::More;
use FindBin;
use File::Spec;
use JSON::PP;

use lib "$FindBin::Bin/../lib";
use STRling::Core::IR;
use STRling::Core::Diagnostics;
use STRling::Emitters::Pcre2;

# -----------------------------------------------------------------------
# Emitter Edges Conformance — Perl bridge.
#
# Drives the global pathological-AST fixture
# tests/conformance/inputs/emitter_edges/pathological.json through the
# Perl Pcre2 emitter and asserts each Phase 3a safety guard fires:
#   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
#   2. AST Depth Limit Exceeded             — STRlingCompilationError
#   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
#
# `ast_to_ir` mirrors the TypeScript bridge so the test targets the
# emitter without coupling to the parser/compiler stages. Keep it
# minimal — supporting only node types currently appearing in
# pathological.json — so adapter omissions cannot mask emitter bugs by
# silently dropping nodes.
# -----------------------------------------------------------------------

sub find_fixture {
    my $dir = $FindBin::Bin;
    for (1..12) {
        my $marker = File::Spec->catfile($dir, 'toolchain.json');
        if (-f $marker) {
            return File::Spec->catfile(
                $dir, 'tests', 'conformance', 'inputs', 'emitter_edges',
                'pathological.json'
            );
        }
        my $parent = File::Spec->catpath('', File::Spec->catdir($dir, File::Spec->updir), '');
        $parent = File::Spec->canonpath($parent);
        last if $parent eq $dir;
        $dir = $parent;
    }
    die "could not locate workspace root from $FindBin::Bin\n";
}

sub ast_to_ir {
    my ($node) = @_;
    my $type = $node->{type} // '';
    if ($type eq 'Literal') {
        return STRling::Core::IR::IRLit->new(value => "$node->{value}");
    }
    if ($type eq 'Group') {
        return STRling::Core::IR::IRGroup->new(
            capturing => 0,
            body      => ast_to_ir($node->{content}),
        );
    }
    if ($type eq 'Quantifier') {
        my $raw_max = $node->{max};
        my $max = (!defined $raw_max) ? 'Inf' : $raw_max;
        return STRling::Core::IR::IRQuant->new(
            child => ast_to_ir($node->{content}),
            min   => $node->{min} // 0,
            max   => $max,
            mode  => 'Greedy',
        );
    }
    if ($type eq 'Lookbehind') {
        return STRling::Core::IR::IRLook->new(
            dir => 'Behind', neg => 0, body => ast_to_ir($node->{content}),
        );
    }
    if ($type eq 'NegativeLookbehind') {
        return STRling::Core::IR::IRLook->new(
            dir => 'Behind', neg => 1, body => ast_to_ir($node->{content}),
        );
    }
    if ($type eq 'Lookahead') {
        return STRling::Core::IR::IRLook->new(
            dir => 'Ahead', neg => 0, body => ast_to_ir($node->{content}),
        );
    }
    if ($type eq 'NegativeLookahead') {
        return STRling::Core::IR::IRLook->new(
            dir => 'Ahead', neg => 1, body => ast_to_ir($node->{content}),
        );
    }
    die "ast_to_ir: unsupported pathological AST node type \"$type\". "
      . "Extend the adapter when new pathological vectors are added.\n";
}

sub expected_substring {
    my ($prefixed) = @_;
    if ($prefixed =~ /^STRlingCompilationError:\s*(.*)$/s) {
        return $1;
    }
    if ($prefixed =~ /^STRlingWarning[^]]*\]\s*[: ]*(.*)$/s) {
        return $1;
    }
    return $prefixed;
}

my $path = find_fixture();
open(my $fh, '<', $path) or die "open $path: $!";
local $/;
my $raw = <$fh>;
close $fh;
my $doc = JSON::PP->new->utf8->decode($raw);
my $cases = $doc->{tests} // [];
ok(scalar @$cases > 0, 'fixture is non-empty');

for my $tc (@$cases) {
    my $name = $tc->{name} // '<unnamed>';
    my $ir   = ast_to_ir($tc->{ast});
    my $max_depth = $tc->{depth_override_for_test} // 0;

    if (exists $tc->{expected_error}) {
        my $needle = expected_substring("$tc->{expected_error}");
        my $caught;
        eval {
            STRling::Emitters::Pcre2->emit_with_diagnostics($ir, undef, $max_depth);
            1;
        } or do {
            $caught = $@;
        };
        ok(defined $caught, "[$name] expected STRlingCompilationError");
        my $msg = (ref($caught) && $caught->isa('STRling::Core::Diagnostics::STRlingCompilationError'))
            ? $caught->message : "$caught";
        like($msg, qr/\Q$needle\E/, "[$name] message contains needle");
    }
    elsif (exists $tc->{expected_warning}) {
        my $needle = expected_substring("$tc->{expected_warning}");
        my $result = STRling::Emitters::Pcre2->emit_with_diagnostics(
            $ir, undef, $max_depth
        );
        ok(length($result->pattern) > 0,
            "[$name] expected non-empty pattern when only a warning fires");
        my $hit = 0;
        for my $w (@{ $result->warnings }) {
            if ($w->code eq 'REDOS_RISK' && index($w->message, $needle) >= 0) {
                $hit = 1; last;
            }
        }
        ok($hit, "[$name] missing REDOS_RISK warning containing \"$needle\"");
    }
    else {
        fail("[$name] declares neither expected_error nor expected_warning");
    }
}

# Negative controls.
{
    my $r = STRling::Emitters::Pcre2->emit_with_diagnostics(
        STRling::Core::IR::IRLit->new(value => 'abc')
    );
    is($r->pattern, 'abc', 'non-pathological pattern emits unchanged');
    is(scalar @{ $r->warnings }, 0, 'non-pathological emits no warnings');
}
{
    my $deep = STRling::Core::IR::IRGroup->new(
        capturing => 0,
        body => STRling::Core::IR::IRGroup->new(
            capturing => 0,
            body      => STRling::Core::IR::IRLit->new(value => 'ok'),
        ),
    );
    my $r = STRling::Emitters::Pcre2->emit_with_diagnostics($deep, undef, 5);
    is(scalar @{ $r->warnings }, 0, 'depth cap does not fire under limit');
    like($r->pattern, qr/ok/, 'depth-cap-ok pattern contains literal');
}

done_testing();
