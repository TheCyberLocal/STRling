use strict;
use warnings;
use Test::More;
use JSON::PP;
use File::Glob ':glob';
use FindBin;
use lib "$FindBin::Bin/../lib";
use STRling::NodeFactory;
use STRling::Core::Compiler;

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
    next unless exists $spec->{input_ast} && exists $spec->{expected_ir};
    
    subtest $spec->{id} => sub {
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
