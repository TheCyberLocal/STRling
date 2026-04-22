package STRling::Emitters::Pcre2;

use strict;
use warnings;
use 5.014;
use Moo;
use Scalar::Util qw(blessed);

use STRling::Core::IR;
use STRling::Core::Diagnostics;

=head1 NAME

STRling::Emitters::Pcre2 — IR → PCRE2 pattern emitter (Phase 3a guards)

=head1 DESCRIPTION

Pure-function emitter that translates the canonical STRling IR into a
PCRE2-compatible regex string. Implements the cross-binding Phase 3a
safety guards:

=over 4

=item * Variable-Length Lookbehind Rejection (C<VLB_NOT_SUPPORTED>)

=item * AST Depth Limit (C<MAX_DEPTH>)

=item * Catastrophic Backtracking Warning (C<REDOS_RISK>)

=back

=cut

# Default upper bound on IR nesting depth before the emitter aborts.
# Mirrors the SSOT in the TypeScript reference.
use constant DEFAULT_MAX_DEPTH => 250;

my $REDOS_MESSAGE =
    'The pattern contains overlapping alternations or nested unbounded '
  . 'quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking '
  . 'and exponential CPU spikes. Consider using possessive quantifiers '
  . '(++ or *+) or atomic groups to guarantee execution safety.';

has '_depth'         => (is => 'rw', default => sub { 0 });
has '_max_depth'     => (is => 'rw', default => sub { DEFAULT_MAX_DEPTH });
has '_in_lookbehind' => (is => 'rw', default => sub { 0 });
has '_warnings'      => (is => 'rw', default => sub { [] });

# --- Public API ---------------------------------------------------------

sub emit {
    my ($class_or_self, $ir, $flags) = @_;
    return $class_or_self->emit_with_diagnostics($ir, $flags)->pattern;
}

sub emit_with_diagnostics {
    my ($class_or_self, $ir, $flags, $max_depth) = @_;
    my $self = blessed($class_or_self) ? $class_or_self : $class_or_self->new;
    $self->_depth(0);
    $self->_max_depth(($max_depth && $max_depth > 0) ? $max_depth : DEFAULT_MAX_DEPTH);
    $self->_in_lookbehind(0);
    $self->_warnings([]);
    my $pattern = $self->_emit_node($ir);
    return STRling::Core::Diagnostics::CompileResult->new(
        pattern  => $pattern,
        warnings => $self->_warnings,
    );
}

# --- Phase 3a safety predicates ----------------------------------------

sub _is_unbounded_quant {
    my ($q) = @_;
    my $m = $q->max;
    return !defined($m) || (defined($m) && "$m" eq 'Inf');
}

sub _is_variable_length_quant {
    my ($q) = @_;
    return 1 if _is_unbounded_quant($q);
    return $q->max ne $q->min;
}

sub _is_fixed_length_body {
    my ($node) = @_;
    return 1 unless blessed($node);
    if ($node->isa('STRling::Core::IR::IRQuant')) {
        return (!_is_variable_length_quant($node)) && _is_fixed_length_body($node->child);
    }
    if ($node->isa('STRling::Core::IR::IRSeq')) {
        for my $p (@{ $node->parts }) {
            return 0 unless _is_fixed_length_body($p);
        }
        return 1;
    }
    if ($node->isa('STRling::Core::IR::IRAlt')) {
        for my $b (@{ $node->branches }) {
            return 0 unless _is_fixed_length_body($b);
        }
        return 1;
    }
    if ($node->isa('STRling::Core::IR::IRGroup')) {
        return _is_fixed_length_body($node->body);
    }
    if ($node->isa('STRling::Core::IR::IRLook')) {
        return 1;  # zero-width
    }
    return 1;
}

sub _has_nested_unbounded_quant {
    my ($child) = @_;
    return 0 unless blessed($child);
    if ($child->isa('STRling::Core::IR::IRQuant')) {
        return _is_unbounded_quant($child);
    }
    if ($child->isa('STRling::Core::IR::IRGroup')) {
        return _has_nested_unbounded_quant($child->body);
    }
    if ($child->isa('STRling::Core::IR::IRSeq')) {
        my @p = @{ $child->parts };
        return @p == 1 && _has_nested_unbounded_quant($p[0]);
    }
    if ($child->isa('STRling::Core::IR::IRAlt')) {
        for my $b (@{ $child->branches }) {
            return 1 if _has_nested_unbounded_quant($b);
        }
        return 0;
    }
    return 0;
}

sub _push_redos_warning {
    my ($self) = @_;
    for my $w (@{ $self->_warnings }) {
        return if $w->code eq 'REDOS_RISK';
    }
    push @{ $self->_warnings }, STRling::Core::Diagnostics::STRlingWarning->new(
        code    => 'REDOS_RISK',
        message => $REDOS_MESSAGE,
    );
}

# --- Dispatch -----------------------------------------------------------

my %LITERAL_SPECIAL = map { $_ => 1 } split //, '[\\]^$.|?*+(){}';

sub _escape_literal {
    my ($s) = @_;
    my $out = '';
    for my $ch (split //, $s) {
        $out .= '\\' if $LITERAL_SPECIAL{$ch};
        $out .= $ch;
    }
    return $out;
}

sub _emit_node {
    my ($self, $node) = @_;
    $self->_depth($self->_depth + 1);
    if ($self->_depth > $self->_max_depth) {
        my $limit = $self->_max_depth;
        $self->_depth($self->_depth - 1);
        die STRling::Core::Diagnostics::STRlingCompilationError->new(
            message => "Maximum AST depth exceeded (limit: $limit). "
              . 'This pattern is too deeply nested and risks host stack '
              . 'exhaustion during emission. Refactor the pattern to reduce '
              . 'nesting, or flatten capturing groups where possible.',
            code => 'MAX_DEPTH',
        );
    }
    my $result;
    my $ok = eval {
        $result = $self->_dispatch($node);
        1;
    };
    my $err = $@;
    $self->_depth($self->_depth - 1);
    if (!$ok) { die $err; }
    return $result;
}

sub _dispatch {
    my ($self, $node) = @_;
    die "emit: undef IR node\n" unless blessed($node);

    if    ($node->isa('STRling::Core::IR::IRLit'))   { return _escape_literal($node->value) }
    elsif ($node->isa('STRling::Core::IR::IRDot'))   { return '.' }
    elsif ($node->isa('STRling::Core::IR::IRSeq'))   {
        return join '', map { $self->_emit_node($_) } @{ $node->parts };
    }
    elsif ($node->isa('STRling::Core::IR::IRAlt'))   {
        return join '|', map { $self->_emit_node($_) } @{ $node->branches };
    }
    elsif ($node->isa('STRling::Core::IR::IRGroup')) {
        my $body = $self->_emit_node($node->body);
        if ($node->atomic)        { return "(?>$body)" }
        if (defined $node->name)  { return '(?<' . $node->name . '>' . $body . ')' }
        if ($node->capturing)     { return "($body)" }
        return "(?:$body)";
    }
    elsif ($node->isa('STRling::Core::IR::IRQuant')) {
        # ReDoS guard: only flag when the *outer* quantifier is itself
        # unbounded. A bounded outer like `(a+){0,3}` cannot produce
        # exponential backtracking on its own.
        if (_is_unbounded_quant($node) && _has_nested_unbounded_quant($node->child)) {
            $self->_push_redos_warning;
        }
        my $child_str = $self->_emit_node($node->child);
        # Conservatively wrap multi-char or composite children.
        my $needs_paren =
              $node->child->isa('STRling::Core::IR::IRSeq')
           || $node->child->isa('STRling::Core::IR::IRAlt')
           || $node->child->isa('STRling::Core::IR::IRQuant')
           || ($node->child->isa('STRling::Core::IR::IRLit')
                 && length($child_str) > 1
                 && substr($child_str, 0, 1) ne '\\');
        $child_str = "(?:$child_str)" if $needs_paren;

        my $min  = $node->min;
        my $maxv = $node->max;
        my $unbounded = _is_unbounded_quant($node);
        my $suffix;
        if ($unbounded) {
            if    ($min == 0) { $suffix = '*' }
            elsif ($min == 1) { $suffix = '+' }
            else              { $suffix = "{$min,}" }
        }
        elsif ($min == 0 && $maxv == 1) { $suffix = '?' }
        elsif ($min == $maxv)           { $suffix = "{$min}" }
        else                            { $suffix = "{$min,$maxv}" }

        my $mode = $node->mode || 'Greedy';
        $suffix .= '?' if $mode eq 'Lazy';
        $suffix .= '+' if $mode eq 'Possessive';

        return $child_str . $suffix;
    }
    elsif ($node->isa('STRling::Core::IR::IRLook')) {
        # Variable-length lookbehind guard: PCRE2 mandates a fixed-width
        # lookbehind body. Detect the violation here so the user sees a
        # Signpost-pattern error rather than an opaque PCRE2 compile
        # failure leaking from the runtime.
        if ($node->dir eq 'Behind' && !_is_fixed_length_body($node->body)) {
            die STRling::Core::Diagnostics::STRlingCompilationError->new(
                message =>
                    'PCRE2 does not support variable-length lookbehinds. The '
                  . 'lookbehind body contains a quantifier that makes its '
                  . 'length unpredictable. Rewrite the assertion using a '
                  . 'fixed-length range (e.g. `{1,8}` instead of `+`), or '
                  . 'restructure the pattern using a Lookahead, or extract '
                  . 'the quantified portion outside the assertion.',
                code => 'VLB_NOT_SUPPORTED',
            );
        }
        my $was = $self->_in_lookbehind;
        $self->_in_lookbehind(1) if $node->dir eq 'Behind';
        my $body = $self->_emit_node($node->body);
        $self->_in_lookbehind($was);
        if ($node->dir eq 'Ahead') {
            return $node->neg ? "(?!$body)" : "(?=$body)";
        }
        return $node->neg ? "(?<!$body)" : "(?<=$body)";
    }
    die 'Unknown IR node: ' . ref($node) . "\n";
}

1;
