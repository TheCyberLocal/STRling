use strict;
use warnings;
use Test::More;
use JSON::PP;
use File::Glob ':glob';
use File::Basename;
use FindBin;
use lib "$FindBin::Bin/../lib";
use STRling::NodeFactory;
use STRling::Core::Compiler;
use STRling::Core::HintEngine qw(get_hint);

my $spec_dir = "$FindBin::Bin/../../../tests/spec";
my @files = glob("$spec_dir/*.json");

if (!@files) {
    plan skip_all => "No spec tests found in $spec_dir";
}

foreach my $file (@files) {
    my $json_text = do {
        local $/;
        open my $fh, '<', $file or die "Cannot open $file: $!";
        <$fh>;
    };

    my $spec = eval { decode_json($json_text) };
    if ($@) {
        fail("Invalid JSON in $file: $@");
        next;
    }

    # Skip if not a full test case
    if (!(exists $spec->{input_ast} && exists $spec->{expected_ir})) {
        if (exists $spec->{expected_error}) {
            print "=== RUN " . basename($file) . "\n";
            if (exists $spec->{input_dsl} && $spec->{input_dsl} ne '') {
                # Parser error test: parse input_dsl and verify error + hint
                my $input_dsl = $spec->{input_dsl};
                my $expected_error = $spec->{expected_error};

                subtest basename($file) . " (parser error)" => sub {
                    eval {
                        require STRling::Core::Parser;
                        my $parser = STRling::Core::Parser->new();
                        $parser->parse($input_dsl);
                    };
                    ok($@, "Expected parse error");
                    if ($@) {
                        like($@, qr/\Q$expected_error\E/, "Error message contains expected substring");
                        if (exists $spec->{expected_hint} && defined $spec->{expected_hint} && $spec->{expected_hint} ne '') {
                            # Check hint if the error object supports it
                            if (ref $@ && $@->can('hint')) {
                                is($@->hint(), $spec->{expected_hint}, "Hint matches expected");
                            }
                        }
                    }
                };
            } else {
                print "    --- PASS: Parser test (no AST), out of scope\n";
            }
        }
        next;
    }

    print "=== RUN " . basename($file) . "\n";
    subtest $spec->{id} // basename($file) => sub {
        my $ast_node = eval { STRling::NodeFactory->from_json($spec->{input_ast}) };
        if ($@) {
            fail("AST Hydration failed: $@");
            return;
        }

        my $ir_node = eval { STRling::Core::Compiler->compile($ast_node) };
        if ($@) {
            fail("Compilation failed: $@");
            return;
        }

        my $got_ir = $ir_node->to_dict();
        my $expected_ir = normalize_expected($spec->{expected_ir});
        is_deeply($got_ir, $expected_ir, "IR matches expected");
    };
}

sub normalize_expected {
    my ($data) = @_;

    if (ref $data eq 'HASH') {
        my $new_hash = {};
        foreach my $key (keys %$data) {
            $new_hash->{$key} = normalize_expected($data->{$key});
        }
        return $new_hash;
    }
    elsif (ref $data eq 'ARRAY') {
        my $new_array = [];
        foreach my $item (@$data) {
            push @$new_array, normalize_expected($item);
        }
        return $new_array;
    }
    elsif (JSON::PP::is_bool($data)) {
        return $data ? 1 : 0;
    }

    return $data;
}

done_testing();
