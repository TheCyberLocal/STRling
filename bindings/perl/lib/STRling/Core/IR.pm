package STRling::Core::IR;

# ABSTRACT: STRling Intermediate Representation (IR) Node Definitions

=head1 NAME

STRling::Core::IR - Intermediate Representation (IR) Node Definitions

=head1 DESCRIPTION

This module defines the complete set of IR node classes that represent
language-agnostic regex constructs. The IR serves as an intermediate layer
between the parsed AST and the target-specific emitters (e.g., PCRE2).

IR nodes are designed to be:

=over 4

=item * Simple and composable

=item * Easy to serialize (via to_dict methods)

=item * Independent of any specific regex flavor

=item * Optimized for transformation and analysis

=back

Each IR node corresponds to a fundamental regex operation (alternation,
sequencing, character classes, quantification, etc.) and can be serialized
to a dictionary representation for further processing or debugging.

=cut

use strict;
use warnings;

our $VERSION = '3.0.0-alpha';

# ---- Base IR Operation ----

package STRling::Core::IR::IROp {
    use Moo;
    
=head1 CLASSES

=head2 IROp

Base class for all IR operations.

All IR nodes extend this base class and must implement the to_dict() method
for serialization to a dictionary representation.

=head3 METHODS

=over 4

=item to_dict

Serialize the IR node to a dictionary representation.

Returns: The hash reference representation of this IR node.

Raises: dies if not implemented by subclass.

=cut

    sub to_dict {
        die "to_dict() must be implemented by subclass";
    }
    
=back

=cut
}

# ---- IRAlt ----

package STRling::Core::IR::IRAlt {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRAlt

Represents an alternation (OR) operation in the IR.

Matches any one of the provided branches. Equivalent to the | operator
in traditional regex syntax.

=head3 ATTRIBUTES

=over 4

=item branches

ArrayRef of IROp nodes representing the alternative branches.

=back

=cut

    has 'branches' => (
        is       => 'ro',
        required => 1,
        # ArrayRef of IROp - the alternative branches
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            ir       => 'Alt',
            branches => [ map { $_->to_dict() } @{ $self->branches } ]
        };
    }
}

# ---- IRSeq ----

package STRling::Core::IR::IRSeq {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRSeq

Represents a sequence operation in the IR.

Matches all parts in order.

=head3 ATTRIBUTES

=over 4

=item parts

ArrayRef of IROp nodes representing the sequential parts.

=back

=cut

    has 'parts' => (
        is       => 'ro',
        required => 1,
        # ArrayRef of IROp - the sequential parts
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            ir    => 'Seq',
            parts => [ map { $_->to_dict() } @{ $self->parts } ]
        };
    }
}

# ---- IRLit ----

package STRling::Core::IR::IRLit {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRLit

Represents a literal string in the IR.

=head3 ATTRIBUTES

=over 4

=item value

The literal string value.

=back

=cut

    has 'value' => (
        is       => 'ro',
        required => 1,
        # String - the literal value
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            ir    => 'Lit',
            value => $self->value
        };
    }
}

# ---- IRDot ----

package STRling::Core::IR::IRDot {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRDot

Represents the dot (any character) operator in the IR.

=cut

    sub to_dict {
        my ($self) = @_;
        return { ir => 'Dot' };
    }
}

# ---- IRAnchor ----

package STRling::Core::IR::IRAnchor {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRAnchor

Represents an anchor (position assertion) in the IR.

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
            ir => 'Anchor',
            at => $self->at
        };
    }
}

# ---- Character Class Items ----

package STRling::Core::IR::IRClassItem {
    use Moo;
    
=head2 IRClassItem

Base class for character class items.

=cut

    sub to_dict {
        die "to_dict() must be implemented by subclass";
    }
}

package STRling::Core::IR::IRClassRange {
    use Moo;
    extends 'STRling::Core::IR::IRClassItem';
    
=head2 IRClassRange

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
            ir   => 'Range',
            from => $self->from_ch,
            to   => $self->to_ch
        };
    }
}

package STRling::Core::IR::IRClassLiteral {
    use Moo;
    extends 'STRling::Core::IR::IRClassItem';
    
=head2 IRClassLiteral

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
            ir   => 'Char',
            char => $self->ch
        };
    }
}

package STRling::Core::IR::IRClassEscape {
    use Moo;
    extends 'STRling::Core::IR::IRClassItem';
    
=head2 IRClassEscape

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
        my $d = {
            ir   => 'Esc',
            type => $self->type
        };
        if (defined $self->property) {
            $d->{property} = $self->property;
        }
        return $d;
    }
}

# ---- IRCharClass ----

package STRling::Core::IR::IRCharClass {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRCharClass

Represents a character class in the IR.

=head3 ATTRIBUTES

=over 4

=item negated

Boolean indicating if the character class is negated.

=item items

ArrayRef of IRClassItem objects.

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
        # ArrayRef of IRClassItem
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            ir      => 'CharClass',
            negated => $self->negated ? 1 : 0,
            items   => [ map { $_->to_dict() } @{ $self->items } ]
        };
    }
}

# ---- IRQuant ----

package STRling::Core::IR::IRQuant {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRQuant

Represents a quantifier in the IR.

=head3 ATTRIBUTES

=over 4

=item child

The IROp being quantified.

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
        # IROp - the child being quantified
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
            ir    => 'Quant',
            child => $self->child->to_dict(),
            min   => $self->min,
            max   => $self->max,
            mode  => $self->mode
        };
    }
}

# ---- IRGroup ----

package STRling::Core::IR::IRGroup {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRGroup

Represents a group in the IR.

=head3 ATTRIBUTES

=over 4

=item capturing

Boolean indicating if the group is capturing.

=item body

The IROp contained in the group.

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
        # IROp - the group body
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
        my $d = {
            ir        => 'Group',
            capturing => $self->capturing ? 1 : 0,
            body      => $self->body->to_dict()
        };
        if (defined $self->name) {
            $d->{name} = $self->name;
        }
        if (defined $self->atomic) {
            $d->{atomic} = $self->atomic ? 1 : 0;
        }
        return $d;
    }
}

# ---- IRBackref ----

package STRling::Core::IR::IRBackref {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRBackref

Represents a backreference in the IR.

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
        my $d = { ir => 'Backref' };
        if (defined $self->byIndex) {
            $d->{byIndex} = $self->byIndex;
        }
        if (defined $self->byName) {
            $d->{byName} = $self->byName;
        }
        return $d;
    }
}

# ---- IRLook ----

package STRling::Core::IR::IRLook {
    use Moo;
    extends 'STRling::Core::IR::IROp';
    
=head2 IRLook

Represents a lookaround assertion in the IR.

=head3 ATTRIBUTES

=over 4

=item dir

Direction: "Ahead" or "Behind".

=item neg

Boolean indicating if the lookaround is negative.

=item body

The IROp inside the lookaround.

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
        # IROp - lookaround body
    );
    
    sub to_dict {
        my ($self) = @_;
        return {
            ir   => 'Look',
            dir  => $self->dir,
            neg  => $self->neg ? 1 : 0,
            body => $self->body->to_dict()
        };
    }
}

1;

=head1 SEE ALSO

L<STRling::Core::Nodes>

=cut
