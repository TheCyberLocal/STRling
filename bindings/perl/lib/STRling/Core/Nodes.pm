package STRling::Core::Nodes;

# ABSTRACT: STRling AST Node Definitions

=head1 NAME

STRling::Core::Nodes - STRling AST Node Definitions

=head1 DESCRIPTION

This module defines the complete set of Abstract Syntax Tree (AST) node classes
that represent the parsed structure of STRling patterns. The AST is the direct
output of the parser and represents the syntactic structure of the pattern before
optimization and lowering to IR.

AST nodes are designed to:

=over 4

=item * Closely mirror the source pattern syntax

=item * Be easily serializable to the Base TargetArtifact schema

=item * Provide a clean separation between parsing and compilation

=item * Support multiple target regex flavors through the compilation pipeline

=back

Each AST node type corresponds to a syntactic construct in the STRling DSL
(alternation, sequencing, character classes, anchors, etc.) and can be
serialized to a dictionary representation for debugging or storage.

=cut

use strict;
use warnings;

our $VERSION = '3.0.0-alpha';

# ---- Flags container ----

package STRling::Core::Nodes::Flags {
    use Moo;
    
=head1 CLASSES

=head2 Flags

Container for regex flags/modifiers.

Flags control the behavior of pattern matching (case sensitivity, multiline
mode, etc.). This class encapsulates all standard regex flags.

=head3 ATTRIBUTES

=over 4

=item ignoreCase

Boolean flag for case-insensitive matching.

=item multiline

Boolean flag for multiline mode.

=item dotAll

Boolean flag for dot matching newlines.

=item unicode

Boolean flag for unicode mode.

=item extended

Boolean flag for extended/verbose mode.

=back

=cut

    has 'ignoreCase' => (
        is      => 'ro',
        default => sub { 0 },
        # Boolean - case-insensitive matching
    );
    
    has 'multiline' => (
        is      => 'ro',
        default => sub { 0 },
        # Boolean - multiline mode
    );
    
    has 'dotAll' => (
        is      => 'ro',
        default => sub { 0 },
        # Boolean - dot matches newlines
    );
    
    has 'unicode' => (
        is      => 'ro',
        default => sub { 0 },
        # Boolean - unicode mode
    );
    
    has 'extended' => (
        is      => 'ro',
        default => sub { 0 },
        # Boolean - extended/verbose mode
    );
    
=head3 METHODS

=over 4

=item to_dict

Serialize the flags to a hash reference.

=cut

    sub to_dict {
        my ($self) = @_;
        return {
            ignoreCase => $self->ignoreCase ? 1 : 0,
            multiline  => $self->multiline ? 1 : 0,
            dotAll     => $self->dotAll ? 1 : 0,
            unicode    => $self->unicode ? 1 : 0,
            extended   => $self->extended ? 1 : 0,
        };
    }
    
=item from_letters

Create a Flags object from a string of flag letters.

    my $flags = STRling::Core::Nodes::Flags->from_letters('ims');

Supported letters: i (ignoreCase), m (multiline), s (dotAll), u (unicode), x (extended)

=cut

    sub from_letters {
        my ($class, $letters) = @_;
        
        # Remove commas and spaces
        $letters =~ s/[, ]//g;
        
        my %flag_map = (
            i => 'ignoreCase',
            m => 'multiline',
            s => 'dotAll',
            u => 'unicode',
            x => 'extended',
        );
        
        my %attrs;
        foreach my $ch (split //, $letters) {
            if (exists $flag_map{$ch}) {
                $attrs{$flag_map{$ch}} = 1;
            }
            # Unknown flags are ignored at parser stage; may be warned later
        }
        
        return $class->new(%attrs);
    }
    
=back

=cut
}

# ---- Base node ----

package STRling::Core::Nodes::Node {
    use Moo;
    
=head2 Node

Base class for all AST nodes.

All concrete node types extend this base class.

=head3 METHODS

=over 4

=item to_dict

Serialize the node to a hash reference.

Must be implemented by subclasses.

=cut

    sub to_dict {
        die "to_dict() must be implemented by subclass";
    }
    
=back

=cut
}

# ---- Concrete nodes matching Base Schema ----

package STRling::Core::Nodes::Alt {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Alt

Represents an alternation (OR) node.

=head3 ATTRIBUTES

=over 4

=item branches

ArrayRef of Node objects representing the alternative branches.

=back

=cut

    has 'branches' => (
        is       => 'ro',
        required => 1,
        # ArrayRef of Node - alternative branches
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind     => 'Alt',
            branches => [ map { $_->to_dict() } @{ $self->branches } ]
        };
    }
}

package STRling::Core::Nodes::Seq {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Seq

Represents a sequence node.

=head3 ATTRIBUTES

=over 4

=item parts

ArrayRef of Node objects representing the sequential parts.

=back

=cut

    has 'parts' => (
        is       => 'ro',
        required => 1,
        # ArrayRef of Node - sequential parts
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind  => 'Seq',
            parts => [ map { $_->to_dict() } @{ $self->parts } ]
        };
    }
}

package STRling::Core::Nodes::Lit {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Lit

Represents a literal string node.

=head3 ATTRIBUTES

=over 4

=item value

The literal string value.

=back

=cut

    has 'value' => (
        is       => 'ro',
        required => 1,
        # String - literal value
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind  => 'Lit',
            value => $self->value
        };
    }
}

package STRling::Core::Nodes::Dot {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Dot

Represents the dot (any character) node.

=cut

    sub to_dict {
        my ($self) = @_;
        return { kind => 'Dot' };
    }
}

package STRling::Core::Nodes::Anchor {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Anchor

Represents an anchor (position assertion) node.

=head3 ATTRIBUTES

=over 4

=item at

The anchor type: "Start", "End", "WordBoundary", "NotWordBoundary", or Absolute* variants.

=back

=cut

    has 'at' => (
        is       => 'ro',
        required => 1,
        # String - anchor type
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind => 'Anchor',
            at   => $self->at
        };
    }
}

# --- CharClass --

package STRling::Core::Nodes::ClassItem {
    use Moo;
    
=head2 ClassItem

Base class for character class items.

=cut

    sub to_dict {
        die "to_dict() must be implemented by subclass";
    }
}

package STRling::Core::Nodes::ClassRange {
    use Moo;
    extends 'STRling::Core::Nodes::ClassItem';
    
=head2 ClassRange

Represents a character range in a character class (e.g., a-z).

=head3 ATTRIBUTES

=over 4

=item from_ch

The starting character of the range.

=item to_ch

The ending character of the range.

=back

=cut

    has 'from_ch' => (
        is       => 'ro',
        required => 1,
        # String - start character
    );
    
    has 'to_ch' => (
        is       => 'ro',
        required => 1,
        # String - end character
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind => 'Range',
            from => $self->from_ch,
            to   => $self->to_ch
        };
    }
}

package STRling::Core::Nodes::ClassLiteral {
    use Moo;
    extends 'STRling::Core::Nodes::ClassItem';
    
=head2 ClassLiteral

Represents a literal character in a character class.

=head3 ATTRIBUTES

=over 4

=item ch

The literal character.

=back

=cut

    has 'ch' => (
        is       => 'ro',
        required => 1,
        # String - the character
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind => 'Char',
            char => $self->ch
        };
    }
}

package STRling::Core::Nodes::ClassEscape {
    use Moo;
    extends 'STRling::Core::Nodes::ClassItem';
    
=head2 ClassEscape

Represents an escape sequence in a character class (e.g., \d, \w, \p{Lu}).

=head3 ATTRIBUTES

=over 4

=item type

The escape type: d, D, w, W, s, S, p, P.

=item property

Unicode property name (for \p and \P types).

=back

=cut

    has 'type' => (
        is       => 'ro',
        required => 1,
        # String - escape type
    );
    
    has 'property' => (
        is => 'ro',
        # String - optional unicode property
    );
    
    sub to_dict {
        my ($self) = @_;
        my $data = {
            kind => 'Esc',
            type => $self->type
        };
        if ($self->type =~ /^[pP]$/ && defined $self->property) {
            $data->{property} = $self->property;
        }
        return $data;
    }
}

package STRling::Core::Nodes::CharClass {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 CharClass

Represents a character class node.

=head3 ATTRIBUTES

=over 4

=item negated

Boolean indicating if the character class is negated.

=item items

ArrayRef of ClassItem objects.

=back

=cut

    has 'negated' => (
        is       => 'ro',
        required => 1,
        # Boolean - whether negated
    );
    
    has 'items' => (
        is       => 'ro',
        required => 1,
        # ArrayRef of ClassItem
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind    => 'CharClass',
            negated => $self->negated ? 1 : 0,
            items   => [ map { $_->to_dict() } @{ $self->items } ]
        };
    }
}

package STRling::Core::Nodes::Quant {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Quant

Represents a quantifier node.

=head3 ATTRIBUTES

=over 4

=item child

The Node being quantified.

=item min

Minimum number of repetitions.

=item max

Maximum number of repetitions (integer or "Inf" for unbounded).

=item mode

Quantifier mode: "Greedy", "Lazy", or "Possessive".

=back

=cut

    has 'child' => (
        is       => 'ro',
        required => 1,
        # Node - the child being quantified
    );
    
    has 'min' => (
        is       => 'ro',
        required => 1,
        # Integer - minimum repetitions
    );
    
    has 'max' => (
        is       => 'ro',
        required => 1,
        # Integer or "Inf" - maximum repetitions
    );
    
    has 'mode' => (
        is       => 'ro',
        required => 1,
        # String - Greedy|Lazy|Possessive
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind  => 'Quant',
            child => $self->child->to_dict(),
            min   => $self->min,
            max   => $self->max,
            mode  => $self->mode
        };
    }
}

package STRling::Core::Nodes::Group {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Group

Represents a group node.

=head3 ATTRIBUTES

=over 4

=item capturing

Boolean indicating if the group is capturing.

=item body

The Node contained in the group.

=item name

Optional group name (for named capturing groups).

=item atomic

Optional boolean indicating if the group is atomic.

=back

=cut

    has 'capturing' => (
        is       => 'ro',
        required => 1,
        # Boolean - whether capturing
    );
    
    has 'body' => (
        is       => 'ro',
        required => 1,
        # Node - the group body
    );
    
    has 'name' => (
        is => 'ro',
        # Optional String - group name
    );
    
    has 'atomic' => (
        is => 'ro',
        # Optional Boolean - atomic group
    );
    
    sub to_dict {
        my ($self) = @_;
        my $data = {
            kind      => 'Group',
            capturing => $self->capturing ? 1 : 0,
            body      => $self->body->to_dict()
        };
        if (defined $self->name) {
            $data->{name} = $self->name;
        }
        if (defined $self->atomic) {
            $data->{atomic} = $self->atomic ? 1 : 0;
        }
        return $data;
    }
}

package STRling::Core::Nodes::Backref {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Backref

Represents a backreference node.

=head3 ATTRIBUTES

=over 4

=item byIndex

Optional integer index for numeric backreferences.

=item byName

Optional string name for named backreferences.

=back

=cut

    has 'byIndex' => (
        is => 'ro',
        # Optional Integer - backreference by index
    );
    
    has 'byName' => (
        is => 'ro',
        # Optional String - backreference by name
    );
    
    sub to_dict {
        my ($self) = @_;
        my $data = { kind => 'Backref' };
        if (defined $self->byIndex) {
            $data->{byIndex} = $self->byIndex;
        }
        if (defined $self->byName) {
            $data->{byName} = $self->byName;
        }
        return $data;
    }
}

package STRling::Core::Nodes::Look {
    use Moo;
    extends 'STRling::Core::Nodes::Node';
    
=head2 Look

Represents a lookaround assertion node.

=head3 ATTRIBUTES

=over 4

=item dir

Direction: "Ahead" or "Behind".

=item neg

Boolean indicating if the lookaround is negative.

=item body

The Node inside the lookaround.

=back

=cut

    has 'dir' => (
        is       => 'ro',
        required => 1,
        # String - Ahead|Behind
    );
    
    has 'neg' => (
        is       => 'ro',
        required => 1,
        # Boolean - whether negative
    );
    
    has 'body' => (
        is       => 'ro',
        required => 1,
        # Node - lookaround body
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            kind => 'Look',
            dir  => $self->dir,
            neg  => $self->neg ? 1 : 0,
            body => $self->body->to_dict()
        };
    }
}

1;

=head1 SEE ALSO

L<STRling::Core::IR>

=cut
