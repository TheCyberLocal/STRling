package STRling::Simply;

# ABSTRACT: Fluent API for building STRling patterns

=head1 NAME

STRling::Simply - Fluent API for building STRling patterns

=head1 SYNOPSIS

    use STRling::Simply qw(:all);
    
    # Build a US phone number pattern
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
    # Returns: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$

=head1 DESCRIPTION

STRling::Simply provides a fluent, functional API for constructing regex patterns
in Perl. Instead of manually creating AST nodes with C<STRling::Core::Nodes>,
you can use simple, composable functions that return blessed Pattern objects.

This module follows the Gold Standard set by the TypeScript and Python bindings,
using snake_case naming conventions for Perl while maintaining functional parity.

=cut

use strict;
use warnings;
use STRling::Core::Nodes;
use STRling::Core::Compiler;

our $VERSION = '3.0.0-alpha';

use Exporter 'import';
our @EXPORT_OK = qw(
    merge capture may group
    any_of
    digit start end
    lit
);
our %EXPORT_TAGS = (
    all => \@EXPORT_OK,
);

# Private helper function to validate named groups uniqueness
sub _validate_named_groups {
    my ($function_name, @patterns) = @_;
    
    my %named_group_counts;
    for my $pattern (@patterns) {
        for my $group_name (@{$pattern->{named_groups}}) {
            $named_group_counts{$group_name}++;
        }
    }
    
    my @duplicates = grep { $named_group_counts{$_} > 1 } keys %named_group_counts;
    if (@duplicates) {
        my $dup_info = join(", ", map { "$_: $named_group_counts{$_}" } @duplicates);
        die "$function_name: Named groups must be unique. Duplicate named groups found: $dup_info\n";
    }
    
    # Return all named groups for caller to use
    my @all_named_groups;
    for my $p (@patterns) {
        push @all_named_groups, @{$p->{named_groups}};
    }
    return @all_named_groups;
}

=head1 FUNCTIONS

=head2 Constructors

=head3 merge(@patterns)

Concatenates the provided patterns into a single sequential pattern.

    my $pattern = merge(digit(3), lit('-'), digit(4));
    # Matches: 123-4567

Parameters:
  - @patterns: One or more Pattern objects or strings to concatenate

Returns:
  - A new Pattern object representing the concatenated sequence

=cut

sub merge {
    my (@patterns) = @_;
    
    my @clean_patterns;
    for my $p (@patterns) {
        if (!ref($p)) {
            # Plain string, convert to literal
            $p = lit($p);
        }
        die "merge: all parameters must be Pattern objects or strings"
            unless ref($p) eq 'STRling::Simply::Pattern';
        push @clean_patterns, $p;
    }
    
    # Validate named groups and get combined list
    my @all_named_groups = _validate_named_groups('merge', @clean_patterns);
    
    my @child_nodes = map { $_->{node} } @clean_patterns;
    
    # If only one pattern, no need to wrap in Seq
    if (@child_nodes == 1) {
        return $clean_patterns[0];
    }
    
    my $node = STRling::Core::Nodes::Seq->new(parts => \@child_nodes);
    
    return STRling::Simply::Pattern->_new(
        node => $node,
        named_groups => \@all_named_groups,
    );
}

=head3 capture(@patterns)

Creates a numbered capture group for extracting matched content by index.

    my $pattern = capture(digit(3));
    # In regex: (\d{3})

Parameters:
  - @patterns: One or more patterns to be captured

Returns:
  - A new Pattern object representing the numbered capture group

=cut

sub capture {
    my (@patterns) = @_;
    
    my @clean_patterns;
    for my $p (@patterns) {
        if (!ref($p)) {
            $p = lit($p);
        }
        die "capture: all parameters must be Pattern objects or strings"
            unless ref($p) eq 'STRling::Simply::Pattern';
        push @clean_patterns, $p;
    }
    
    # Validate named groups and get combined list
    my @all_named_groups = _validate_named_groups('capture', @clean_patterns);
    
    my $body_node;
    if (@clean_patterns == 1) {
        $body_node = $clean_patterns[0]->{node};
    } else {
        my @child_nodes = map { $_->{node} } @clean_patterns;
        $body_node = STRling::Core::Nodes::Seq->new(parts => \@child_nodes);
    }
    
    my $node = STRling::Core::Nodes::Group->new(
        capturing => 1,
        body => $body_node,
        name => undef,
    );
    
    return STRling::Simply::Pattern->_new(
        node => $node,
        named_groups => \@all_named_groups,
        numbered_group => 1,
    );
}

=head3 may(@patterns)

Makes the provided patterns optional (matches 0 or 1 times).

    my $pattern = may(lit('-'));
    # In regex: -?

Parameters:
  - @patterns: One or more patterns to be optionally matched

Returns:
  - A new Pattern object representing the optional pattern(s)

=cut

sub may {
    my (@patterns) = @_;
    
    my @clean_patterns;
    for my $p (@patterns) {
        if (!ref($p)) {
            $p = lit($p);
        }
        die "may: all parameters must be Pattern objects or strings"
            unless ref($p) eq 'STRling::Simply::Pattern';
        push @clean_patterns, $p;
    }
    
    # Validate named groups and get combined list
    my @all_named_groups = _validate_named_groups('may', @clean_patterns);
    
    my $body_node;
    if (@clean_patterns == 1) {
        $body_node = $clean_patterns[0]->{node};
    } else {
        my @child_nodes = map { $_->{node} } @clean_patterns;
        $body_node = STRling::Core::Nodes::Seq->new(parts => \@child_nodes);
    }
    
    my $node = STRling::Core::Nodes::Quant->new(
        child => $body_node,
        min => 0,
        max => 1,
        mode => 'Greedy',
    );
    
    return STRling::Simply::Pattern->_new(
        node => $node,
        named_groups => \@all_named_groups,
    );
}

=head3 group($name, @patterns)

Creates a named capture group that can be referenced by name.

    my $pattern = group('area_code', digit(3));
    # In regex: (?<area_code>\d{3})

Parameters:
  - $name: The unique name for the group
  - @patterns: One or more patterns to be captured

Returns:
  - A new Pattern object representing the named capture group

=cut

sub group {
    my ($name, @patterns) = @_;
    
    die "group: first parameter must be a string name"
        unless defined $name && !ref($name);
    
    my @clean_patterns;
    for my $p (@patterns) {
        if (!ref($p)) {
            $p = lit($p);
        }
        die "group: all parameters must be Pattern objects or strings"
            unless ref($p) eq 'STRling::Simply::Pattern';
        push @clean_patterns, $p;
    }
    
    # Validate named groups and get combined list
    my @all_named_groups = _validate_named_groups('group', @clean_patterns);
    push @all_named_groups, $name;
    
    my $body_node;
    if (@clean_patterns == 1) {
        $body_node = $clean_patterns[0]->{node};
    } else {
        my @child_nodes = map { $_->{node} } @clean_patterns;
        $body_node = STRling::Core::Nodes::Seq->new(parts => \@child_nodes);
    }
    
    my $node = STRling::Core::Nodes::Group->new(
        capturing => 1,
        body => $body_node,
        name => $name,
    );
    
    return STRling::Simply::Pattern->_new(
        node => $node,
        named_groups => \@all_named_groups,
    );
}

=head2 Character Sets

=head3 any_of($chars)

Matches any one of the provided characters.

    my $pattern = any_of("-. ");
    # Matches any of: - . or space
    # In regex: [-. ]

Parameters:
  - $chars: A string containing the characters to match

Returns:
  - A new Pattern object representing the character class

=cut

sub any_of {
    my ($chars) = @_;
    
    die "any_of: parameter must be a string"
        unless defined $chars && !ref($chars);
    
    # Build character class items from the string
    my @items;
    for my $ch (split //, $chars) {
        push @items, STRling::Core::Nodes::ClassLiteral->new(ch => $ch);
    }
    
    my $node = STRling::Core::Nodes::CharClass->new(
        negated => 0,
        items => \@items,
    );
    
    return STRling::Simply::Pattern->_new(node => $node);
}

=head2 Static Patterns

=head3 digit($min, $max)

Matches digit characters.

    my $pattern = digit(3);      # Matches exactly 3 digits
    my $pattern = digit(3, 5);   # Matches 3-5 digits
    my $pattern = digit();       # Matches 1 digit

Parameters:
  - $min: Minimum number of digits (optional, defaults to 1)
  - $max: Maximum number of digits (optional, defaults to $min)

Returns:
  - A new Pattern object representing the digit pattern

=cut

sub digit {
    my ($min_rep, $max_rep) = @_;
    
    my $node = STRling::Core::Nodes::CharClass->new(
        negated => 0,
        items => [ STRling::Core::Nodes::ClassEscape->new(type => 'd') ],
    );
    
    my $pattern = STRling::Simply::Pattern->_new(node => $node);
    
    if (defined $min_rep) {
        return $pattern->rep($min_rep, $max_rep);
    }
    
    return $pattern;
}

=head3 start()

Matches the start of a line.

    my $pattern = start();
    # In regex: ^

Returns:
  - A new Pattern object representing the start anchor

=cut

sub start {
    my $node = STRling::Core::Nodes::Anchor->new(at => 'Start');
    return STRling::Simply::Pattern->_new(node => $node);
}

=head3 end()

Matches the end of a line.

    my $pattern = end();
    # In regex: $

Returns:
  - A new Pattern object representing the end anchor

=cut

sub end {
    my $node = STRling::Core::Nodes::Anchor->new(at => 'End');
    return STRling::Simply::Pattern->_new(node => $node);
}

=head2 Utilities

=head3 lit($text)

Creates a literal pattern from a string.

    my $pattern = lit('hello');
    # Matches the literal text: hello

Parameters:
  - $text: The text to match literally

Returns:
  - A new Pattern object representing the literal text

=cut

sub lit {
    my ($text) = @_;
    
    die "lit: parameter must be a string"
        unless defined $text && !ref($text);
    
    my $node = STRling::Core::Nodes::Lit->new(value => $text);
    return STRling::Simply::Pattern->_new(node => $node);
}

=head1 PATTERN CLASS

The Pattern class is the core object returned by all Simply API functions.
It provides methods for compiling patterns to regex strings.

=cut

package STRling::Simply::Pattern;

use strict;
use warnings;
use STRling::Core::Compiler;

sub _new {
    my ($class, %args) = @_;
    
    my $self = {
        node => $args{node},
        named_groups => $args{named_groups} || [],
        numbered_group => $args{numbered_group} || 0,
    };
    
    return bless $self, $class;
}

=head2 compile()

Compiles the pattern to a PCRE2-compatible regex string.

    my $regex = $pattern->compile();

Returns:
  - A string containing the compiled regex pattern

=cut

sub compile {
    my ($self) = @_;
    
    # Use the compiler to convert AST to IR, then emit to PCRE2
    my $ir = STRling::Core::Compiler->compile($self->{node});
    
    # For now, we'll use a simple stringification
    # In the future, this should call an emitter
    return $self->_emit_pcre2($ir);
}

=head2 rep($min, $max)

Applies a repetition quantifier to the pattern.

    my $pattern = digit()->rep(3);      # Exactly 3 digits: \d{3}
    my $pattern = digit()->rep(3, 5);   # 3-5 digits: \d{3,5}
    my $pattern = digit()->rep(3, 0);   # 3 or more digits: \d{3,}

Parameters:
  - $min: Minimum repetitions (required)
  - $max: Maximum repetitions (optional)
          - If omitted: matches exactly $min times
          - If 0: matches $min or more times (unlimited)
          - Otherwise: matches between $min and $max times

Returns:
  - A new Pattern object with the repetition applied

Note:
  - Named groups cannot be repeated as they must be unique.
  - Numbered (captured) groups created with C<capture()> only accept exact counts.
    For example, C<capture(digit(3))->rep(4)> creates 4 separate capture groups,
    not a quantified single group. Using C<rep($min, $max)> with different values
    on a captured group will result in an error.

=cut

sub rep {
    my ($self, $min_rep, $max_rep) = @_;
    
    die "rep: minimum repetition must be specified"
        unless defined $min_rep;
    
    # Named groups cannot be repeated (they must be unique)
    if (@{$self->{named_groups}}) {
        die "rep: Named groups cannot be repeated as they must be unique\n";
    }
    
    # Handle numbered groups specially
    if ($self->{numbered_group}) {
        if (defined $max_rep) {
            die "rep: numbered (captured) groups take only exact count, not a range\n";
        }
        # Duplicate the node exactly $min_rep times
        my @children = ($self->{node}) x $min_rep;
        my $new_node = STRling::Core::Nodes::Seq->new(parts => \@children);
        return STRling::Simply::Pattern->_new(
            node => $new_node,
            named_groups => $self->{named_groups},
        );
    }
    
    # Regular quantifier
    my $q_max = defined $max_rep ? ($max_rep == 0 ? 'Inf' : $max_rep) : $min_rep;
    
    my $new_node = STRling::Core::Nodes::Quant->new(
        child => $self->{node},
        min => $min_rep,
        max => $q_max,
        mode => 'Greedy',
    );
    
    return STRling::Simply::Pattern->_new(
        node => $new_node,
        named_groups => $self->{named_groups},
    );
}

# Simple PCRE2 emitter (basic implementation)
sub _emit_pcre2 {
    my ($self, $ir) = @_;
    
    my $type = ref($ir);
    
    if ($type eq 'STRling::Core::IR::IRLit') {
        # Escape special regex characters
        my $value = $ir->value;
        $value =~ s/([\[\](){}.*+?^$|\\])/\\$1/g;
        return $value;
    }
    elsif ($type eq 'STRling::Core::IR::IRSeq') {
        return join('', map { $self->_emit_pcre2($_) } @{$ir->parts});
    }
    elsif ($type eq 'STRling::Core::IR::IRCharClass') {
        # Optimization: if single escape and not negated, emit directly without brackets
        # This ensures parity with TypeScript which emits \d instead of [\d]
        if (!$ir->negated && scalar(@{$ir->items}) == 1) {
            my $item = $ir->items->[0];
            if (ref($item) eq 'STRling::Core::IR::IRClassEscape') {
                return '\\' . $item->type;
            }
        }

        my $result = '[';
        $result .= '^' if $ir->negated;
        
        for my $item (@{$ir->items}) {
            my $item_type = ref($item);
            if ($item_type eq 'STRling::Core::IR::IRClassLiteral') {
                my $ch = $item->ch;
                # Escape special chars within character class
                # Place - at end to avoid creating a range
                $ch =~ s/([\[\]\\^}])/\\$1/g;
                $ch =~ s/-/\\-/g;
                $result .= $ch;
            }
            elsif ($item_type eq 'STRling::Core::IR::IRClassRange') {
                $result .= $item->from_ch . '-' . $item->to_ch;
            }
            elsif ($item_type eq 'STRling::Core::IR::IRClassEscape') {
                $result .= '\\' . $item->type;
            }
        }
        
        $result .= ']';
        return $result;
    }
    elsif ($type eq 'STRling::Core::IR::IRQuant') {
        my $child = $self->_emit_pcre2($ir->child);
        my $min = $ir->min;
        my $max = $ir->max;
        
        if ($min == 0 && $max == 1) {
            return $child . '?';
        }
        elsif ($min == 0 && $max eq 'Inf') {
            return $child . '*';
        }
        elsif ($min == 1 && $max eq 'Inf') {
            return $child . '+';
        }
        elsif ($min == $max) {
            return $child . '{' . $min . '}';
        }
        elsif ($max eq 'Inf') {
            return $child . '{' . $min . ',}';
        }
        else {
            return $child . '{' . $min . ',' . $max . '}';
        }
    }
    elsif ($type eq 'STRling::Core::IR::IRGroup') {
        my $body = $self->_emit_pcre2($ir->body);
        
        if ($ir->capturing) {
            if (defined $ir->name) {
                return '(?<' . $ir->name . '>' . $body . ')';
            }
            return '(' . $body . ')';
        }
        return '(?:' . $body . ')';
    }
    elsif ($type eq 'STRling::Core::IR::IRAnchor') {
        my $at = $ir->at;
        return '^' if $at eq 'Start';
        return '$' if $at eq 'End';
        return '\\b' if $at eq 'WordBoundary';
        return '\\B' if $at eq 'NotWordBoundary';
        return '\\A' if $at eq 'AbsoluteStart';
        return '\\Z' if $at eq 'EndBeforeFinalNewline';
        return '\\z' if $at eq 'AbsoluteEnd';
    }
    elsif ($type eq 'STRling::Core::IR::IRAlt') {
        return join('|', map { $self->_emit_pcre2($_) } @{$ir->branches});
    }
    
    die "Unknown IR node type: $type\n";
}

1;

=head1 SEE ALSO

L<STRling>, L<STRling::Core::Nodes>, L<STRling::Core::Compiler>

=head1 AUTHOR

TheCyberLocal

=head1 LICENSE

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut
