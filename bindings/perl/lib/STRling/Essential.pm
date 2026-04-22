package STRling::Essential;

# ABSTRACT: STRling Essential — canonical, RFC-grounded patterns.

=head1 NAME

STRling::Essential - Canonical patterns for the most commonly validated
string formats.

=head1 DESCRIPTION

Each helper composes existing primitives so the compiled output flows
through the standard pipeline and no raw regex leaks into the public API.

=cut

use strict;
use warnings;
use STRling::Core::Nodes;
use STRling::Simply;

our $VERSION = '3.0.0';

use Exporter 'import';
our @EXPORT_OK = qw(email url uuid ip date_time);
our %EXPORT_TAGS = (all => \@EXPORT_OK);

sub _letter_items {
    return [
        STRling::Core::Nodes::ClassRange->new(from_ch => 'A', to_ch => 'Z'),
        STRling::Core::Nodes::ClassRange->new(from_ch => 'a', to_ch => 'z'),
    ];
}

sub _digit_items {
    return [STRling::Core::Nodes::ClassEscape->new(type => 'd')];
}

sub _hex_items {
    return [
        STRling::Core::Nodes::ClassRange->new(from_ch => 'A', to_ch => 'F'),
        STRling::Core::Nodes::ClassRange->new(from_ch => 'a', to_ch => 'f'),
        STRling::Core::Nodes::ClassRange->new(from_ch => '0', to_ch => '9'),
    ];
}

sub _chars_items {
    my ($s) = @_;
    return [ map { STRling::Core::Nodes::ClassLiteral->new(ch => $_) } split(//, $s) ];
}

sub _class_of {
    my ($items, $min, $max) = @_;
    my $cc = STRling::Core::Nodes::CharClass->new(negated => 0, items => $items);
    my $node;
    if (defined $max && $min == 1 && $max == 1) {
        $node = $cc;
    } else {
        my $max_val = defined $max ? $max : 'Inf';
        $node = STRling::Core::Nodes::Quant->new(
            child => $cc, min => $min, max => $max_val, mode => 'Greedy'
        );
    }
    return STRling::Simply::Pattern->_new(node => $node, named_groups => []);
}

sub _dig_n  { my ($mn, $mx) = @_; _class_of(_digit_items(), $mn, $mx); }
sub _hex_n  { my ($mn, $mx) = @_; _class_of(_hex_items(),   $mn, $mx); }
sub _lett_n { my ($mn, $mx) = @_; _class_of(_letter_items(),$mn, $mx); }

sub _lit {
    my ($s) = @_;
    return STRling::Simply::Pattern->_new(
        node => STRling::Core::Nodes::Lit->new(value => $s),
        named_groups => [],
    );
}

sub _opt {
    my ($pat) = @_;
    my $grouped = STRling::Core::Nodes::Group->new(
        capturing => 0, body => $pat->{node}, name => undef,
    );
    my $q = STRling::Core::Nodes::Quant->new(
        child => $grouped, min => 0, max => 1, mode => 'Greedy',
    );
    return STRling::Simply::Pattern->_new(node => $q, named_groups => []);
}

sub _alt {
    my (@branches) = @_;
    my @nodes = map { $_->{node} } @branches;
    return STRling::Simply::Pattern->_new(
        node => STRling::Core::Nodes::Alt->new(branches => \@nodes),
        named_groups => [],
    );
}

sub _seq { return STRling::Simply::merge(@_); }

# Matches an email address (RFC 5322 addr-spec, basic structure).
sub email {
    my $local  = _class_of([@{_letter_items()}, @{_digit_items()}, @{_chars_items('._%+-')}], 1, undef);
    my $domain = _class_of([@{_letter_items()}, @{_digit_items()}, @{_chars_items('.-')}],    1, undef);
    my $tld    = _lett_n(2, undef);
    return _seq($local, _lit('@'), $domain, _lit('.'), $tld);
}

# Matches an HTTP or HTTPS URL (RFC 3986 generic syntax).
sub url {
    my @base     = (@{_letter_items()}, @{_digit_items()}, @{_chars_items("/_-.~%&=:@!\$'()*+,;")});
    my @with_q   = (@base, @{_chars_items('?')});
    my @with_frag= (@with_q, @{_chars_items('#')});

    my $scheme   = _seq(_lit('http'), _opt(_lit('s')));
    my $host     = _class_of([@{_letter_items()}, @{_digit_items()}, @{_chars_items('.-')}], 1, undef);
    my $port     = _opt(_seq(_lit(':'), _dig_n(1, undef)));
    my $path     = _opt(_seq(_lit('/'), _class_of([@base],     0, undef)));
    my $query    = _opt(_seq(_lit('?'), _class_of([@with_q],   0, undef)));
    my $fragment = _opt(_seq(_lit('#'), _class_of([@with_frag],0, undef)));
    return _seq($scheme, _lit('://'), $host, $port, $path, $query, $fragment);
}

# Matches a UUID (RFC 4122). Pass version=4 for v4-specific validation.
sub uuid {
    my ($version) = @_;
    $version //= 0;
    if ($version == 4) {
        my $variant = _class_of(_chars_items('89ABab'), 1, 1);
        return _seq(
            _hex_n(8, 8),  _lit('-'),
            _hex_n(4, 4),  _lit('-'),
            _lit('4'), _hex_n(3, 3), _lit('-'),
            $variant, _hex_n(3, 3), _lit('-'),
            _hex_n(12, 12),
        );
    }
    return _seq(
        _hex_n(8, 8),  _lit('-'),
        _hex_n(4, 4),  _lit('-'),
        _hex_n(4, 4),  _lit('-'),
        _hex_n(4, 4),  _lit('-'),
        _hex_n(12, 12),
    );
}

# Matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
sub ip {
    my ($version) = @_;
    $version //= 0;
    my $ipv4 = sub {
        _seq(
            _dig_n(1, 3), _lit('.'),
            _dig_n(1, 3), _lit('.'),
            _dig_n(1, 3), _lit('.'),
            _dig_n(1, 3),
        );
    };
    my $ipv6 = sub {
        _seq(
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4), _lit(':'),
            _hex_n(1, 4),
        );
    };
    return $ipv4->() if $version == 4;
    return $ipv6->() if $version == 6;
    return _alt($ipv4->(), $ipv6->());
}

# Matches an ISO 8601 / RFC 3339 datetime.
sub date_time {
    my $sign   = _class_of(_chars_items('+-'), 1, 1);
    my $frac   = _seq(_lit('.'), _dig_n(1, undef));
    my $offset = _seq($sign, _dig_n(2, 2), _lit(':'), _dig_n(2, 2));
    return _seq(
        _dig_n(4, 4), _lit('-'), _dig_n(2, 2), _lit('-'), _dig_n(2, 2),
        _lit('T'),
        _dig_n(2, 2), _lit(':'), _dig_n(2, 2), _lit(':'), _dig_n(2, 2),
        _opt($frac),
        _opt(_alt(_lit('Z'), $offset)),
    );
}

1;
