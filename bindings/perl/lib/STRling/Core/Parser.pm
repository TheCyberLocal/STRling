package STRling::Core::Parser;

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.0.0';
our @EXPORT_OK = qw(parse);

use STRling::Core::Nodes;
use STRling::Core::Errors;
use STRling::Core::HintEngine qw(get_hint);

sub new {
    my ($class) = @_;
    return bless {}, $class;
}

sub parse {
    my ($self_or_src, $src_arg) = @_;
    my $src;
    if (ref $self_or_src) {
        # Called as method: $parser->parse($input)
        $src = $src_arg;
    } else {
        # Called as function: parse($input)
        $src = $self_or_src;
    }
    my $parser = STRling::Core::Parser::Internal->new($src);
    my $flags = $parser->{flags};
    my $ast = $parser->parse_pattern();
    return ($flags, $ast);
}

package STRling::Core::Parser::Internal {
    use STRling::Core::Errors;
    use STRling::Core::Nodes;
    use STRling::Core::HintEngine qw(get_hint);

    sub new {
        my ($class, $text) = @_;
        my $self = bless {
            original_text => $text,
            cap_count => 0,
            cap_names => {},
        }, $class;

        my ($flags, $src) = $self->_parse_directives($text);
        $self->{flags} = $flags;
        $self->{src} = $src;
        $self->{pos} = 0;
        $self->{extended_mode} = $flags->extended;
        $self->{in_class} = 0;
        return $self;
    }

    sub _raise_error {
        my ($self, $message, $pos) = @_;
        $pos //= $self->{pos};
        my $hint = get_hint($message, $self->{src}, $pos);
        die STRling::Core::Errors::STRlingParseError->new(
            message => $message, pos => $pos,
            text => $self->{src}, hint => $hint,
        );
    }

    sub _raise_error_with_text {
        my ($self, $message, $pos, $text) = @_;
        my $hint = get_hint($message, $text, $pos);
        die STRling::Core::Errors::STRlingParseError->new(
            message => $message, pos => $pos,
            text => $text, hint => $hint,
        );
    }

    sub _parse_directives {
        my ($self, $text) = @_;
        my $flags = STRling::Core::Nodes::Flags->new();
        my @lines = split /\n/, $text, -1;
        my @pattern_lines;
        my $in_pattern = 0;

        for my $line (@lines) {
            my $stripped = $line;
            $stripped =~ s/^\s+|\s+$//g;

            next if !$in_pattern && ($stripped eq '' || $stripped =~ /^#/);

            if ($stripped =~ /^%/) {
                if ($in_pattern) {
                    $self->_raise_error_with_text('Directive after pattern', 0, $text);
                }
                unless ($stripped =~ /^%flags/) {
                    $self->_raise_error_with_text('Malformed directive', 0, $text);
                }

                my $idx = index($line, '%flags');
                my $after = substr($line, $idx + 6);
                my %valid = (i => 1, m => 1, s => 1, u => 1, x => 1);
                my $allowed_re = qr/^[ ,\t\[\]imsuxIMSUX]/;

                my $j = 0;
                for my $k (0 .. length($after) - 1) {
                    my $c = substr($after, $k, 1);
                    if ($c =~ $allowed_re) { $j = $k + 1; }
                    else { last; }
                }

                my $flags_token = substr($after, 0, $j);
                my $remainder = substr($after, $j);
                (my $letters = $flags_token) =~ s/[^a-zA-Z]//g;
                $letters = lc($letters);

                for my $ch (split //, $letters) {
                    unless ($valid{$ch}) {
                        $self->_raise_error_with_text("Invalid flag '$ch'", 0, $text);
                    }
                }

                if ($letters ne '') {
                    $flags = STRling::Core::Nodes::Flags->from_letters($letters);
                } elsif ($remainder =~ /\S/) {
                    my ($ch) = $remainder =~ /(\S)/;
                    $self->_raise_error_with_text("Invalid flag '$ch'", 0, $text);
                }

                if (defined $remainder && $remainder =~ /\S/) {
                    push @pattern_lines, $remainder;
                    $in_pattern = 1;
                }
                next;
            }

            if ($line =~ /%flags/) {
                $self->_raise_error_with_text('Directive after pattern', 0, $text);
            }

            $in_pattern = 1;
            push @pattern_lines, $line;
        }

        my $pattern = join("\n", @pattern_lines);
        return ($flags, $pattern);
    }

    sub _eof {
        my ($self) = @_;
        return $self->{pos} >= length($self->{src});
    }

    sub _peek {
        my ($self, $n) = @_;
        $n //= 0;
        my $j = $self->{pos} + $n;
        return '' if $j >= length($self->{src});
        return substr($self->{src}, $j, 1);
    }

    sub _take {
        my ($self) = @_;
        return '' if $self->_eof();
        my $ch = substr($self->{src}, $self->{pos}, 1);
        $self->{pos}++;
        return $ch;
    }

    sub _match_str {
        my ($self, $s) = @_;
        if (substr($self->{src}, $self->{pos}, length($s)) eq $s) {
            $self->{pos} += length($s);
            return 1;
        }
        return 0;
    }

    sub _skip_ws_and_comments {
        my ($self) = @_;
        return if !$self->{extended_mode} || $self->{in_class} > 0;
        while (!$self->_eof()) {
            my $ch = $self->_peek();
            if ($ch =~ /[ \t\r\n]/) { $self->{pos}++; next; }
            if ($ch eq '#') {
                while (!$self->_eof() && $self->_peek() !~ /[\r\n]/) { $self->{pos}++; }
                next;
            }
            last;
        }
    }

    sub parse_pattern {
        my ($self) = @_;
        $self->_skip_ws_and_comments();
        if ($self->_eof()) {
            return STRling::Core::Nodes::Lit->new(value => '');
        }
        my $node = $self->_parse_alt();
        $self->_skip_ws_and_comments();
        if (!$self->_eof()) {
            if ($self->_peek() eq ')') {
                $self->_raise_error("Unmatched ')'");
            }
            $self->_raise_error("Unexpected trailing input");
        }
        return $node;
    }

    sub _parse_alt {
        my ($self) = @_;
        $self->_skip_ws_and_comments();

        if ($self->_peek() eq '|') {
            $self->_raise_error('Alternation lacks left-hand side');
        }

        my @branches = ($self->_parse_seq());
        $self->_skip_ws_and_comments();

        while ($self->_peek() eq '|') {
            my $pipe_pos = $self->{pos};
            $self->_take();
            $self->_skip_ws_and_comments();

            if ($self->_eof()) {
                $self->_raise_error('Alternation lacks right-hand side', $pipe_pos);
            }
            if ($self->_peek() eq '|') {
                $self->_raise_error('Empty alternation', $pipe_pos);
            }
            if ($self->_peek() eq ')') {
                $self->_raise_error('Alternation lacks right-hand side', $pipe_pos);
            }

            push @branches, $self->_parse_seq();
            $self->_skip_ws_and_comments();
        }

        return @branches == 1 ? $branches[0] : STRling::Core::Nodes::Alt->new(branches => \@branches);
    }

    sub _parse_seq {
        my ($self) = @_;
        my @parts;

        while (1) {
            $self->_skip_ws_and_comments();
            my $ch = $self->_peek();
            last if $ch eq '' || $ch eq '|' || $ch eq ')';

            my $atom = $self->_parse_atom();
            $self->_skip_ws_and_comments();
            my $quantified = $self->_parse_quant_if_any($atom);
            push @parts, $quantified;
        }

        return STRling::Core::Nodes::Lit->new(value => '') if @parts == 0;
        return $parts[0] if @parts == 1;
        return STRling::Core::Nodes::Seq->new(parts => \@parts);
    }

    sub _parse_atom {
        my ($self) = @_;
        my $ch = $self->_peek();
        $self->_raise_error('Unexpected end of input') if $ch eq '';

        if ($ch eq '.') { $self->_take(); return STRling::Core::Nodes::Dot->new(); }
        if ($ch eq '^') { $self->_take(); return STRling::Core::Nodes::Anchor->new(at => 'Start'); }
        if ($ch eq '$') { $self->_take(); return STRling::Core::Nodes::Anchor->new(at => 'End'); }
        if ($ch eq '(') { return $self->_parse_group(); }
        if ($ch eq '[') { return $self->_parse_char_class(); }
        if ($ch eq '\\') { return $self->_parse_escape(); }
        if ($ch =~ /[*+?]/) { $self->_raise_error("Invalid quantifier '$ch'"); }
        if ($ch eq '{') {
            my $save = $self->{pos};
            my $look = '';
            my $j = $self->{pos} + 1;
            while ($j < length($self->{src}) && substr($self->{src}, $j, 1) ne '}') {
                $look .= substr($self->{src}, $j, 1);
                $j++;
            }
            if ($j < length($self->{src}) && $look ne '' && $look !~ /^\d+(,\d*)?$/) {
                $self->_raise_error('Brace quantifier: Invalid brace quantifier content', $save);
            }
            $self->_raise_error("Invalid quantifier '$ch'");
        }

        return $self->_take_literal();
    }

    sub _take_literal {
        my ($self) = @_;
        my $ch = $self->_take();
        return STRling::Core::Nodes::Lit->new(value => $ch);
    }

    sub _parse_escape {
        my ($self) = @_;
        my $start_pos = $self->{pos};
        $self->_take(); # consume backslash
        $self->_raise_error('Incomplete escape sequence', $start_pos) if $self->_eof();

        my $ch = $self->_take();

        if ($ch eq 'b') { return STRling::Core::Nodes::Anchor->new(at => 'WordBoundary'); }
        if ($ch eq 'B') { return STRling::Core::Nodes::Anchor->new(at => 'NotWordBoundary'); }
        if ($ch eq 'A') { return STRling::Core::Nodes::Anchor->new(at => 'AbsoluteStart'); }
        if ($ch eq 'Z') { return STRling::Core::Nodes::Anchor->new(at => 'EndBeforeFinalNewline'); }
        # NOTE: lowercase \z is intentionally NOT an anchor

        if ($ch =~ /[dDwWsS]/) {
            return STRling::Core::Nodes::CharClass->new(
                negated => 0,
                items => [STRling::Core::Nodes::ClassEscape->new(type => $ch)],
            );
        }

        if ($ch eq 'n') { return STRling::Core::Nodes::Lit->new(value => "\n"); }
        if ($ch eq 'r') { return STRling::Core::Nodes::Lit->new(value => "\r"); }
        if ($ch eq 't') { return STRling::Core::Nodes::Lit->new(value => "\t"); }
        if ($ch eq 'f') { return STRling::Core::Nodes::Lit->new(value => "\f"); }
        if ($ch eq 'v') { return STRling::Core::Nodes::Lit->new(value => "\x0B"); }

        if ($ch eq '0') {
            if ($self->_peek() =~ /[0-9]/) {
                $self->_raise_error("Forbidden octal escape \\0" . $self->_peek(), $start_pos);
            }
            return STRling::Core::Nodes::Lit->new(value => "\x00");
        }

        if ($ch =~ /[1-9]/) {
            my $num_str = $ch;
            while ($self->_peek() =~ /[0-9]/) { $num_str .= $self->_take(); }
            my $num = int($num_str);
            if ($num > $self->{cap_count}) {
                $self->_raise_error("Backreference to undefined group \\$num", $start_pos);
            }
            return STRling::Core::Nodes::Backref->new(byIndex => $num);
        }

        if ($ch eq 'k') {
            if ($self->_peek() ne '<') {
                $self->_raise_error("Expected '<' after \\k", $self->{pos});
            }
            $self->_take(); # consume <
            my $name = '';
            while (!$self->_eof() && $self->_peek() ne '>') {
                $name .= $self->_take();
            }
            if ($self->_eof()) {
                $self->_raise_error('Unterminated named backref', $self->{pos});
            }
            $self->_take(); # consume >
            if (!exists $self->{cap_names}{$name}) {
                $self->_raise_error("Backreference to undefined group <$name>", $start_pos);
            }
            return STRling::Core::Nodes::Backref->new(byName => $name);
        }

        if ($ch eq 'x') { return $self->_parse_hex_escape($start_pos); }
        if ($ch eq 'u') { return $self->_parse_unicode_escape('u', $start_pos); }
        if ($ch eq 'U') { return $self->_parse_unicode_escape('U', $start_pos); }

        if ($ch eq 'p' || $ch eq 'P') {
            if ($self->_peek() ne '{') {
                $self->_raise_error("Expected { after \\p/\\P", $start_pos);
            }
            $self->_take(); # consume {
            my $prop = '';
            while (!$self->_eof() && $self->_peek() ne '}') { $prop .= $self->_take(); }
            if ($self->_eof()) { $self->_raise_error("Unterminated \\p{...}", $start_pos); }
            $self->_take(); # consume }
            return STRling::Core::Nodes::CharClass->new(
                negated => 0,
                items => [STRling::Core::Nodes::ClassEscape->new(type => $ch, property => $prop)],
            );
        }

        if ($ch =~ /[a-zA-Z0-9]/) {
            $self->_raise_error("Unknown escape sequence \\$ch", $start_pos);
        }
        return STRling::Core::Nodes::Lit->new(value => $ch);
    }

    sub _parse_hex_escape {
        my ($self, $start_pos) = @_;
        if ($self->_peek() eq '{') {
            $self->_take();
            my $hex = '';
            while ($self->_peek() =~ /[0-9a-fA-F]/) { $hex .= $self->_take(); }
            unless ($self->_match_str('}')) {
                $self->_raise_error("Unterminated \\x{...}", $start_pos);
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        my $hex = '';
        for (1..2) { $hex .= $self->_take() unless $self->_eof(); }
        if (length($hex) != 2 || $hex !~ /^[0-9a-fA-F]{2}$/) {
            $self->_raise_error("Invalid \\xHH escape", $start_pos);
        }
        return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
    }

    sub _parse_unicode_escape {
        my ($self, $tp, $start_pos) = @_;
        if ($tp eq 'u' && $self->_peek() eq '{') {
            $self->_take();
            my $hex = '';
            while ($self->_peek() =~ /[0-9a-fA-F]/) { $hex .= $self->_take(); }
            unless ($self->_match_str('}')) {
                $self->_raise_error("Unterminated \\u{...}", $start_pos);
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        if ($tp eq 'u') {
            my $hex = '';
            for (1..4) { $hex .= $self->_take() unless $self->_eof(); }
            if (length($hex) != 4 || $hex !~ /^[0-9a-fA-F]{4}$/) {
                $self->_raise_error("Invalid \\uHHHH escape", $start_pos);
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        if ($tp eq 'U') {
            my $hex = '';
            for (1..8) { $hex .= $self->_take() unless $self->_eof(); }
            if (length($hex) != 8 || $hex !~ /^[0-9a-fA-F]{8}$/) {
                $self->_raise_error("Invalid \\UHHHHHHHH escape", $start_pos);
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        $self->_raise_error('Invalid unicode escape', $start_pos);
    }

    sub _parse_group {
        my ($self) = @_;
        my $start_pos = $self->{pos};
        $self->_take(); # consume (

        if ($self->_peek() eq '?') {
            $self->_take();
            my $next = $self->_peek();

            if ($next eq ':') {
                $self->_take();
                my $body = $self->_parse_alt();
                $self->_expect_char(')', 'Unterminated group');
                return STRling::Core::Nodes::Group->new(capturing => 0, body => $body);
            }
            if ($next eq '=') {
                $self->_take();
                my $body = $self->_parse_alt();
                $self->_expect_char(')', 'Unterminated lookahead');
                return STRling::Core::Nodes::Look->new(dir => 'Ahead', neg => 0, body => $body);
            }
            if ($next eq '!') {
                $self->_take();
                my $body = $self->_parse_alt();
                $self->_expect_char(')', 'Unterminated lookahead');
                return STRling::Core::Nodes::Look->new(dir => 'Ahead', neg => 1, body => $body);
            }
            if ($next eq '<') {
                $self->_take();
                if ($self->_peek() eq '=') {
                    $self->_take();
                    my $body = $self->_parse_alt();
                    $self->_expect_char(')', 'Unterminated lookbehind');
                    return STRling::Core::Nodes::Look->new(dir => 'Behind', neg => 0, body => $body);
                }
                if ($self->_peek() eq '!') {
                    $self->_take();
                    my $body = $self->_parse_alt();
                    $self->_expect_char(')', 'Unterminated lookbehind');
                    return STRling::Core::Nodes::Look->new(dir => 'Behind', neg => 1, body => $body);
                }
                # Named group
                my $name = '';
                while (!$self->_eof() && $self->_peek() ne '>') {
                    $name .= $self->_take();
                }
                if ($self->_eof()) {
                    $self->_raise_error('Unterminated group name', $self->{pos});
                }
                $self->_take(); # consume >
                if ($name !~ /^[a-zA-Z_][a-zA-Z0-9_]*$/) {
                    $self->_raise_error("Invalid group name '$name'", $start_pos);
                }
                if (exists $self->{cap_names}{$name}) {
                    $self->_raise_error("Duplicate group name '$name'", $start_pos);
                }
                $self->{cap_names}{$name} = 1;
                $self->{cap_count}++;
                my $body = $self->_parse_alt();
                $self->_expect_char(')', 'Unterminated group');
                return STRling::Core::Nodes::Group->new(capturing => 1, name => $name, body => $body);
            }
            if ($next eq '>') {
                $self->_take();
                my $body = $self->_parse_alt();
                $self->_expect_char(')', 'Unterminated atomic group');
                return STRling::Core::Nodes::Group->new(capturing => 0, atomic => 1, body => $body);
            }

            # Check for inline modifiers like (?i), (?im)
            my $save = $self->{pos};
            my $scan = '';
            my $j = $save;
            while ($j < length($self->{src}) && substr($self->{src}, $j, 1) =~ /[imsux]/) {
                $scan .= substr($self->{src}, $j, 1);
                $j++;
            }
            if ($scan ne '' && $j < length($self->{src}) && substr($self->{src}, $j, 1) eq ')') {
                $self->_raise_error("Inline modifiers like (?${scan}...) are not supported", $start_pos);
            }
            $self->_raise_error("Unknown group modifier: ?$next", $self->{pos} - 1);
        }

        # Capturing group
        $self->{cap_count}++;
        my $body = $self->_parse_alt();
        $self->_expect_char(')', 'Unterminated group');
        return STRling::Core::Nodes::Group->new(capturing => 1, body => $body);
    }

    sub _parse_char_class {
        my ($self) = @_;
        my $start_pos = $self->{pos};
        $self->_take(); # consume [
        $self->{in_class}++;

        my $negated = 0;
        if ($self->_peek() eq '^') {
            $negated = 1;
            $self->_take();
        }

        # Empty/unterminated char class: [] or [^]
        if ($self->_peek() eq ']') {
            $self->{in_class}--;
            $self->_raise_error('Unterminated character class', $start_pos);
        }

        my @items;

        while (1) {
            if ($self->_eof()) {
                $self->{in_class}--;
                $self->_raise_error('Unterminated character class', $start_pos);
            }
            last if $self->_peek() eq ']';

            my $item = $self->_parse_class_item();

            # Check for range
            if ($self->_peek() eq '-' && $self->_peek(1) ne ']' && !$self->_eof()) {
                if (ref($item) eq 'STRling::Core::Nodes::ClassLiteral') {
                    my $from_ch = $item->ch;
                    $self->_take(); # consume -
                    if ($self->_eof() || $self->_peek() eq ']') {
                        push @items, $item;
                        push @items, STRling::Core::Nodes::ClassLiteral->new(ch => '-');
                        next;
                    }
                    my $to_item = $self->_parse_class_item();
                    if (ref($to_item) eq 'STRling::Core::Nodes::ClassLiteral') {
                        my $to_ch = $to_item->ch;
                        if ($to_ch lt $from_ch) {
                            $self->{in_class}--;
                            $self->_raise_error('Invalid character range', $start_pos);
                        }
                        push @items, STRling::Core::Nodes::ClassRange->new(from_ch => $from_ch, to_ch => $to_ch);
                        next;
                    } else {
                        push @items, $item;
                        push @items, STRling::Core::Nodes::ClassLiteral->new(ch => '-');
                        push @items, $to_item;
                        next;
                    }
                }
            }

            push @items, $item;
        }

        $self->_take(); # consume ]
        $self->{in_class}--;
        return STRling::Core::Nodes::CharClass->new(negated => $negated, items => \@items);
    }

    sub _parse_class_item {
        my ($self) = @_;
        if ($self->_peek() eq '\\') {
            my $start_pos = $self->{pos};
            $self->_take();
            $self->_raise_error('Incomplete escape sequence', $start_pos) if $self->_eof();
            my $ch = $self->_take();

            if ($ch =~ /[dDwWsS]/) {
                return STRling::Core::Nodes::ClassEscape->new(type => $ch);
            }
            if ($ch eq 'b') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\b"); }
            if ($ch eq '0') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\x00"); }
            if ($ch eq 'n') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\n"); }
            if ($ch eq 'r') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\r"); }
            if ($ch eq 't') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\t"); }
            if ($ch eq 'f') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\f"); }
            if ($ch eq 'v') { return STRling::Core::Nodes::ClassLiteral->new(ch => "\x0B"); }
            if ($ch eq 'x') {
                if ($self->_peek() eq '{') {
                    $self->_take();
                    my $hex = '';
                    while ($self->_peek() =~ /[0-9a-fA-F]/) { $hex .= $self->_take(); }
                    unless ($self->_match_str('}')) {
                        $self->_raise_error("Unterminated \\x{...}", $start_pos);
                    }
                    return STRling::Core::Nodes::ClassLiteral->new(ch => chr(hex($hex)));
                }
                my $hex = '';
                for (1..2) { $hex .= $self->_take() unless $self->_eof(); }
                if (length($hex) != 2 || $hex !~ /^[0-9a-fA-F]{2}$/) {
                    $self->_raise_error("Invalid \\xHH escape", $start_pos);
                }
                return STRling::Core::Nodes::ClassLiteral->new(ch => chr(hex($hex)));
            }
            if ($ch eq 'u') {
                if ($self->_peek() eq '{') {
                    $self->_take();
                    my $hex = '';
                    while ($self->_peek() =~ /[0-9a-fA-F]/) { $hex .= $self->_take(); }
                    unless ($self->_match_str('}')) {
                        $self->_raise_error("Unterminated \\u{...}", $start_pos);
                    }
                    return STRling::Core::Nodes::ClassLiteral->new(ch => chr(hex($hex)));
                }
                my $hex = '';
                for (1..4) { $hex .= $self->_take() unless $self->_eof(); }
                if (length($hex) != 4 || $hex !~ /^[0-9a-fA-F]{4}$/) {
                    $self->_raise_error("Invalid \\uHHHH escape", $start_pos);
                }
                return STRling::Core::Nodes::ClassLiteral->new(ch => chr(hex($hex)));
            }
            if ($ch eq 'p' || $ch eq 'P') {
                if ($self->_peek() ne '{') {
                    $self->_raise_error("Expected { after \\p/\\P", $start_pos);
                }
                $self->_take();
                my $prop = '';
                while (!$self->_eof() && $self->_peek() ne '}') { $prop .= $self->_take(); }
                if ($self->_eof()) { $self->_raise_error("Unterminated \\p{...}", $start_pos); }
                $self->_take();
                return STRling::Core::Nodes::ClassEscape->new(type => $ch, property => $prop);
            }
            if ($ch =~ /[a-zA-Z0-9]/) {
                $self->_raise_error("Unknown escape sequence \\$ch", $start_pos);
            }
            return STRling::Core::Nodes::ClassLiteral->new(ch => $ch);
        }
        return STRling::Core::Nodes::ClassLiteral->new(ch => $self->_take());
    }

    sub _parse_quant_if_any {
        my ($self, $child) = @_;
        $self->_skip_ws_and_comments();
        my $ch = $self->_peek();
        return $child if $ch eq '' || $ch !~ /[*+?{]/;

        my $start_pos = $self->{pos};
        my ($min, $max);

        if ($ch eq '*') { $self->_take(); $min = 0; $max = 'Inf'; }
        elsif ($ch eq '+') { $self->_take(); $min = 1; $max = 'Inf'; }
        elsif ($ch eq '?') { $self->_take(); $min = 0; $max = 1; }
        elsif ($ch eq '{') {
            my $save = $self->{pos};
            $self->_take();

            # Look ahead for invalid brace content
            my $look = '';
            my $j = $self->{pos};
            while ($j < length($self->{src}) && substr($self->{src}, $j, 1) ne '}') {
                $look .= substr($self->{src}, $j, 1);
                $j++;
            }
            if ($j < length($self->{src}) && $look ne '' && $look !~ /^\d+(,\d*)?$/) {
                $self->_raise_error('Brace quantifier: Invalid brace quantifier content', $save);
            }

            my $min_str = '';
            while ($self->_peek() =~ /\d/) { $min_str .= $self->_take(); }
            if ($min_str eq '') {
                $self->_raise_error('Expected number in quantifier', $self->{pos});
            }
            $min = int($min_str);

            if ($self->_match_str(',')) {
                my $max_str = '';
                while ($self->_peek() =~ /\d/) { $max_str .= $self->_take(); }
                $max = $max_str eq '' ? 'Inf' : int($max_str);
            } else {
                $max = $min;
            }

            unless ($self->_match_str('}')) {
                $self->_raise_error('Incomplete quantifier', $self->{pos});
            }

            if ($max ne 'Inf' && $min > $max) {
                $self->_raise_error('Invalid quantifier range', $save);
            }
        }
        else { return $child; }

        # Cannot quantify anchor
        if (ref($child) eq 'STRling::Core::Nodes::Anchor') {
            $self->_raise_error('Cannot quantify anchor', $start_pos);
        }

        my $mode = 'Greedy';
        if ($self->_peek() eq '?') { $self->_take(); $mode = 'Lazy'; }
        elsif ($self->_peek() eq '+') { $self->_take(); $mode = 'Possessive'; }

        return STRling::Core::Nodes::Quant->new(child => $child, min => $min, max => $max, mode => $mode);
    }

    sub _expect_char {
        my ($self, $expected, $error_msg) = @_;
        my $ch = $self->_take();
        unless ($ch eq $expected) {
            $self->_raise_error($error_msg, $self->{pos} - ($ch eq '' ? 0 : 1));
        }
    }
}

1;
