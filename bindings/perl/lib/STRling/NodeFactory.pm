package STRling::NodeFactory;

use strict;
use warnings;
use STRling::Core::Nodes;

sub from_json {
    my ($class, $json, $is_class_member) = @_;
    
    return undef unless defined $json;
    
    my $type = $json->{type};
    die "Unknown node type: " . ($type // 'undef') unless defined $type;

    if ($type eq 'Alternation') {
        return STRling::Core::Nodes::Alt->new(
            branches => [ map { $class->from_json($_) } @{ $json->{expressions} // $json->{alternatives} } ]
        );
    }
    elsif ($type eq 'Sequence') {
        my $parts = $json->{parts} // $json->{elements};
        if (@$parts == 1) {
            return $class->from_json($parts->[0]);
        }
        return STRling::Core::Nodes::Seq->new(
            parts => [ map { $class->from_json($_) } @$parts ]
        );
    }
    elsif ($type eq 'Literal') {
        if ($is_class_member) {
             return STRling::Core::Nodes::ClassLiteral->new(
                ch => $json->{value}
            );
        }
        return STRling::Core::Nodes::Lit->new(
            value => $json->{value}
        );
    }
    elsif ($type eq 'Dot') {
        return STRling::Core::Nodes::Dot->new();
    }
    elsif ($type eq 'Anchor') {
        my $at = $json->{at};
        $at = 'NotWordBoundary' if $at eq 'NonWordBoundary';
        return STRling::Core::Nodes::Anchor->new(
            at => $at
        );
    }
    elsif ($type eq 'CharacterClass') {
        return STRling::Core::Nodes::CharClass->new(
            negated => $json->{negated} ? 1 : 0,
            items   => [ map { $class->from_json($_, 1) } @{ $json->{members} } ]
        );
    }
    elsif ($type eq 'Range') {
        return STRling::Core::Nodes::ClassRange->new(
            from_ch => $json->{from},
            to_ch   => $json->{to}
        );
    }
    elsif ($type eq 'Quantifier') {
        my $mode = 'Greedy';
        if ($json->{lazy}) { $mode = 'Lazy'; }
        elsif ($json->{possessive}) { $mode = 'Possessive'; }
        
        my $max = $json->{max};
        $max = 'Inf' unless defined $max;

        return STRling::Core::Nodes::Quant->new(
            child => $class->from_json($json->{target} // $json->{expression}),
            min   => $json->{min},
            max   => $max,
            mode  => $mode
        );
    }
    elsif ($type eq 'Group') {
        return STRling::Core::Nodes::Group->new(
            capturing => $json->{capturing} ? 1 : 0,
            body      => $class->from_json($json->{expression} // $json->{body}),
            name      => $json->{name} || undef,
            atomic    => $json->{atomic} ? 1 : undef
        );
    }
    elsif ($type eq 'Backreference') {
        return STRling::Core::Nodes::Backref->new(
            byIndex => $json->{index} || undef,
            byName  => $json->{name} || undef
        );
    }
    elsif ($type eq 'Escape') {
        my $kind = $json->{kind};
        my $esc_type;
        if ($kind eq 'digit') { $esc_type = 'd'; }
        elsif ($kind eq 'word') { $esc_type = 'w'; }
        elsif ($kind eq 'space') { $esc_type = 's'; }
        elsif ($kind eq 'not-digit') { $esc_type = 'D'; }
        elsif ($kind eq 'not-word') { $esc_type = 'W'; }
        elsif ($kind eq 'not-space') { $esc_type = 'S'; }
        else { die "Unknown escape kind: $kind"; }
        
        return STRling::Core::Nodes::ClassEscape->new(
            type => $esc_type
        );
    }
    elsif ($type eq 'UnicodeProperty') {
        return STRling::Core::Nodes::ClassEscape->new(
            type     => $json->{negated} ? 'P' : 'p',
            property => $json->{value}
        );
    }
    elsif ($type eq 'Lookahead') {
        return STRling::Core::Nodes::Look->new(
            dir  => 'Ahead',
            neg  => 0,
            body => $class->from_json($json->{body} // $json->{expression})
        );
    }
    elsif ($type eq 'NegativeLookahead') {
        return STRling::Core::Nodes::Look->new(
            dir  => 'Ahead',
            neg  => 1,
            body => $class->from_json($json->{body} // $json->{expression})
        );
    }
    elsif ($type eq 'Lookbehind') {
        return STRling::Core::Nodes::Look->new(
            dir  => 'Behind',
            neg  => 0,
            body => $class->from_json($json->{body} // $json->{expression})
        );
    }
    elsif ($type eq 'NegativeLookbehind') {
        return STRling::Core::Nodes::Look->new(
            dir  => 'Behind',
            neg  => 1,
            body => $class->from_json($json->{body} // $json->{expression})
        );
    }
    
    die "Unsupported node type: $type";
}

1;
