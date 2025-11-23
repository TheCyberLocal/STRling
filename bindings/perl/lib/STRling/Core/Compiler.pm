package STRling::Core::Compiler;

use strict;
use warnings;
use STRling::Core::IR;
use Scalar::Util qw(blessed);

sub compile {
    my ($class, $node) = @_;
    
    return undef unless defined $node;
    
    my $type = blessed($node);
    die "Not a blessed object" unless $type;

    if ($node->isa('STRling::Core::Nodes::Alt')) {
        return STRling::Core::IR::IRAlt->new(
            branches => [ map { $class->compile($_) } @{ $node->branches } ]
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Seq')) {
        my @compiled_parts = map { $class->compile($_) } @{ $node->parts };
        my @optimized_parts;
        
        foreach my $part (@compiled_parts) {
            if (@optimized_parts && 
                $optimized_parts[-1]->isa('STRling::Core::IR::IRLit') && 
                $part->isa('STRling::Core::IR::IRLit')) {
                
                my $prev = pop @optimized_parts;
                push @optimized_parts, STRling::Core::IR::IRLit->new(
                    value => $prev->value . $part->value
                );
            } else {
                push @optimized_parts, $part;
            }
        }
        
        if (@optimized_parts == 1) {
            return $optimized_parts[0];
        }

        return STRling::Core::IR::IRSeq->new(
            parts => \@optimized_parts
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Lit')) {
        return STRling::Core::IR::IRLit->new(
            value => $node->value
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Dot')) {
        return STRling::Core::IR::IRDot->new();
    }
    elsif ($node->isa('STRling::Core::Nodes::Anchor')) {
        return STRling::Core::IR::IRAnchor->new(
            at => $node->at
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::CharClass')) {
        return STRling::Core::IR::IRCharClass->new(
            negated => $node->negated,
            items   => [ map { $class->compile_class_item($_) } @{ $node->items } ]
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Quant')) {
        return STRling::Core::IR::IRQuant->new(
            child => $class->compile($node->child),
            min   => $node->min,
            max   => $node->max,
            mode  => $node->mode
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Group')) {
        return STRling::Core::IR::IRGroup->new(
            capturing => $node->capturing,
            body      => $class->compile($node->body),
            name      => $node->name,
            atomic    => $node->atomic
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Backref')) {
        return STRling::Core::IR::IRBackref->new(
            byIndex => $node->byIndex,
            byName  => $node->byName
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::Look')) {
        return STRling::Core::IR::IRLook->new(
            dir  => $node->dir,
            neg  => $node->neg,
            body => $class->compile($node->body)
        );
    }
    
    die "Unsupported node type for compilation: $type";
}

sub compile_class_item {
    my ($class, $node) = @_;
    
    if ($node->isa('STRling::Core::Nodes::ClassRange')) {
        return STRling::Core::IR::IRClassRange->new(
            from_ch => $node->from_ch,
            to_ch   => $node->to_ch
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::ClassLiteral')) {
        return STRling::Core::IR::IRClassLiteral->new(
            ch => $node->ch
        );
    }
    elsif ($node->isa('STRling::Core::Nodes::ClassEscape')) {
        return STRling::Core::IR::IRClassEscape->new(
            type     => $node->type,
            property => $node->property
        );
    }
    
    die "Unsupported class item type: " . blessed($node);
}

1;
