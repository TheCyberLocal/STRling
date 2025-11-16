package STRling::Core::parser;

# ABSTRACT: STRling Parser - Recursive Descent Parser for STRling DSL

=head1 NAME

STRling::Core::parser - Recursive Descent Parser for STRling DSL

=head1 DESCRIPTION

This module implements a hand-rolled recursive-descent parser that transforms
STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
  - Alternation and sequencing
  - Character classes and ranges
  - Quantifiers (greedy, lazy, possessive)
  - Groups (capturing, non-capturing, named, atomic)
  - Lookarounds (lookahead and lookbehind, positive and negative)
  - Anchors and special escapes
  - Extended/free-spacing mode with comments

The parser produces AST nodes (defined in nodes.pm) that can be compiled
to IR and ultimately emitted as target-specific regex patterns. It includes
comprehensive error handling with position tracking for helpful diagnostics.

=cut

use strict;
use warnings;

our $VERSION = '3.0.0-alpha';

use Exporter 'import';
our @EXPORT_OK = qw(parse parse_to_artifact);

use STRling::Core::Nodes;
use STRling::Core::Errors;
use STRling::Core::HintEngine qw(get_hint);

# ---------------- Lexer helpers ----------------

package STRling::Core::parser::Cursor {
    use Moo;
    
    has 'text' => (
        is => 'rw',
        default => sub { '' },
    );
    
    has 'i' => (
        is => 'rw',
        default => sub { 0 },
    );
    
    has 'extended_mode' => (
        is => 'rw',
        default => sub { 0 },
    );
    
    has 'in_class' => (
        is => 'rw',
        default => sub { 0 },
    );
    
    sub eof {
        my ($self) = @_;
        return $self->i >= length($self->text);
    }
    
    sub peek {
        my ($self, $n) = @_;
        $n //= 0;
        my $j = $self->i + $n;
        return '' if $j >= length($self->text);
        return substr($self->text, $j, 1);
    }
    
    sub take {
        my ($self) = @_;
        return '' if $self->eof();
        my $ch = substr($self->text, $self->i, 1);
        $self->i($self->i + 1);
        return $ch;
    }
    
    sub match {
        my ($self, $s) = @_;
        my $len = length($s);
        if (substr($self->text, $self->i, $len) eq $s) {
            $self->i($self->i + $len);
            return 1;
        }
        return 0;
    }
    
    sub skip_ws_and_comments {
        my ($self) = @_;
        return if !$self->extended_mode || $self->in_class > 0;
        
        # In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
        while (!$self->eof()) {
            my $ch = $self->peek();
            if ($ch =~ /[ \t\r\n]/) {
                $self->i($self->i + 1);
                next;
            }
            if ($ch eq '#') {
                # skip comment to end of line
                while (!$self->eof() && $self->peek() !~ /[\r\n]/) {
                    $self->i($self->i + 1);
                }
                next;
            }
            last;
        }
    }
}

# ---------------- Parser ----------------

package STRling::Core::parser::Parser {
    use Moo;
    
    has '_original_text' => (
        is => 'ro',
        required => 1,
    );
    
    has 'flags' => (
        is => 'rw',
    );
    
    has 'src' => (
        is => 'rw',
    );
    
    has 'cur' => (
        is => 'rw',
    );
    
    has '_cap_count' => (
        is => 'rw',
        default => sub { 0 },
    );
    
    has '_cap_names' => (
        is => 'rw',
        default => sub { {} },
    );
    
    has 'CONTROL_ESCAPES' => (
        is => 'ro',
        default => sub {
            {
                'n' => "\n",
                'r' => "\r",
                't' => "\t",
                'f' => "\f",
                'v' => "\x{0b}",
            }
        },
    );
    
    sub BUILD {
        my ($self) = @_;
        
        # Extract directives first
        my ($flags, $src) = $self->_parse_directives($self->_original_text);
        $self->flags($flags);
        $self->src($src);
        $self->cur(STRling::Core::parser::Cursor->new(
            text => $src,
            i => 0,
            extended_mode => $flags->extended,
            in_class => 0,
        ));
    }
    
    sub _raise_error {
        my ($self, $message, $pos) = @_;
        
        # Raise a STRlingParseError with an instructional hint
        my $hint = STRling::Core::HintEngine::get_hint($message, $self->src, $pos);
        die STRling::Core::Errors::STRlingParseError->new(
            message => $message,
            pos     => $pos,
            text    => $self->src,
            hint    => $hint,
        );
    }
    
    # -- Directives --
    
    sub _parse_directives {
        my ($self, $text) = @_;
        
        my $flags = STRling::Core::Nodes::Flags->new();
        my @lines = split /(\r?\n)/, $text, -1;
        my @pattern_lines;
        my $in_pattern = 0;
        my $line_num = 0;
        
        for (my $i = 0; $i < @lines; $i += 2) {
            my $line = $lines[$i];
            my $eol = $lines[$i + 1] || '';
            $line_num++;
            
            my $stripped = $line;
            $stripped =~ s/^\s+|\s+$//g;
            
            # Skip leading blank lines or comments
            if (!$in_pattern && ($stripped eq '' || $stripped =~ /^#/)) {
                next;
            }
            
            # Process directives only before pattern content
            if (!$in_pattern && $stripped =~ /^%flags/) {
                my $idx = index($line, '%flags');
                my $after = substr($line, $idx + length('%flags'));
                
                # Scan the remainder to separate the flags token from any
                # inline pattern content
                my $j = 0;
                while ($j < length($after) && $after =~ /^.{$j}[ ,\t\[\]imsuxIMSUX]/) {
                    $j++;
                }
                
                my $flags_token = substr($after, 0, $j);
                my $remainder = substr($after, $j);
                
                # Normalize separators and whitespace to single spaces
                my $letters = $flags_token;
                $letters =~ s/[,\[\]\s]+/ /g;
                $letters =~ s/^\s+|\s+$//g;
                $letters = lc($letters);
                
                my %valid_flags = map { $_ => 1 } qw(i m s u x);
                
                # If no valid flag letters were found but something remains on
                # the same line, treat the first non-space char as an
                # invalid-flag error
                $letters =~ s/ //g;
                if ($letters eq '') {
                    $remainder =~ s/^\s+//;
                    if ($remainder ne '') {
                        my $ch = substr($remainder, 0, 1);
                        my $leading_ws = length($after) - length($after =~ s/^\s+//r) - length($remainder);
                        my $pos_before = 0;
                        for (my $k = 0; $k < $line_num - 1; $k++) {
                            $pos_before += length($lines[$k * 2]) + length($lines[$k * 2 + 1] || '');
                        }
                        my $pos = $pos_before + $idx + $j + $leading_ws;
                        my $hint = STRling::Core::HintEngine::get_hint("Invalid flag '$ch'", $text, $pos);
                        die STRling::Core::Errors::STRlingParseError->new(
                            message => "Invalid flag '$ch'",
                            pos     => $pos,
                            text    => $text,
                            hint    => $hint,
                        );
                    }
                } else {
                    # Validate and accept the flags we found
                    for my $ch (split //, $letters) {
                        if ($ch && !$valid_flags{$ch}) {
                            my $pos_before = 0;
                            for (my $k = 0; $k < $line_num - 1; $k++) {
                                $pos_before += length($lines[$k * 2]) + length($lines[$k * 2 + 1] || '');
                            }
                            my $pos = $pos_before + $idx;
                            my $hint = STRling::Core::HintEngine::get_hint("Invalid flag '$ch'", $text, $pos);
                            die STRling::Core::Errors::STRlingParseError->new(
                                message => "Invalid flag '$ch'",
                                pos     => $pos,
                                text    => $text,
                                hint    => $hint,
                            );
                        }
                    }
                    $flags = STRling::Core::Nodes::Flags->from_letters($letters);
                    
                    # If remainder contains pattern content on the same line,
                    # treat it as the start of the pattern
                    $remainder =~ s/^\s+//;
                    if ($remainder ne '') {
                        $in_pattern = 1;
                        push @pattern_lines, $remainder . $eol;
                    }
                }
                next;
            }
            
            if (!$in_pattern && $stripped =~ /^%/) {
                next;
            }
            
            # This is pattern content
            # Check if %flags appears anywhere in this line (would be misplaced)
            if (index($line, '%flags') >= 0) {
                my $pos_before = 0;
                for (my $k = 0; $k < $line_num - 1; $k++) {
                    $pos_before += length($lines[$k * 2]) + length($lines[$k * 2 + 1] || '');
                }
                my $pos = $pos_before + index($line, '%flags');
                my $hint = STRling::Core::HintEngine::get_hint("Directive after pattern content", $text, $pos);
                die STRling::Core::Errors::STRlingParseError->new(
                    message => "Directive after pattern content",
                    pos     => $pos,
                    text    => $text,
                    hint    => $hint,
                );
            }
            
            # All other lines are pattern content
            $in_pattern = 1;
            push @pattern_lines, $line . $eol;
        }
        
        # Join all pattern lines
        my $pattern = join('', @pattern_lines);
        
        return ($flags, $pattern);
    }
    
    sub parse {
        my ($self) = @_;
        
        # Parse the entire STRling pattern into an AST
        my $node = $self->parse_alt();
        $self->cur->skip_ws_and_comments();
        
        if (!$self->cur->eof()) {
            # If there's an unmatched closing parenthesis at top-level
            if ($self->cur->peek() eq ')') {
                die STRling::Core::Errors::STRlingParseError->new(
                    message => "Unmatched ')'",
                    pos     => $self->cur->i,
                    text    => $self->src,
                    hint    => "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?",
                );
            }
            if ($self->cur->peek() eq '|') {
                # Alternation must have a right-hand side
                $self->_raise_error("Alternation lacks right-hand side", $self->cur->i);
            } else {
                $self->_raise_error("Unexpected trailing input", $self->cur->i);
            }
        }
        
        return $node;
    }
    
    # alt := seq ('|' seq)+ | seq
    sub parse_alt {
        my ($self) = @_;
        
        # Check if the pattern starts with a pipe (no left-hand side)
        $self->cur->skip_ws_and_comments();
        if ($self->cur->peek() eq '|') {
            $self->_raise_error("Alternation lacks left-hand side", $self->cur->i);
        }
        
        my @branches = ($self->parse_seq());
        $self->cur->skip_ws_and_comments();
        
        while ($self->cur->peek() eq '|') {
            my $pipe_pos = $self->cur->i;
            $self->cur->take();
            $self->cur->skip_ws_and_comments();
            
            # Check if the pipe is followed by end-of-input (no right-hand side)
            if ($self->cur->peek() eq '') {
                $self->_raise_error("Alternation lacks right-hand side", $pipe_pos);
            }
            
            # Check if the pipe is followed by another pipe (empty branch)
            if ($self->cur->peek() eq '|') {
                $self->_raise_error("Empty alternation branch", $pipe_pos);
            }
            
            push @branches, $self->parse_seq();
            $self->cur->skip_ws_and_comments();
        }
        
        if (@branches == 1) {
            return $branches[0];
        }
        
        return STRling::Core::Nodes::Alt->new(branches => \@branches);
    }
    
    # seq := { term }
    sub parse_seq {
        my ($self) = @_;
        
        my @parts;
        my $prev_had_failed_quant = 0;
        
        while (1) {
            $self->cur->skip_ws_and_comments();
            my $ch = $self->cur->peek();
            
            # Invalid quantifier at start of sequence/group (no previous atom)
            if ($ch ne '' && $ch =~ /[*+?{]/ && @parts == 0) {
                $self->_raise_error("Invalid quantifier '$ch'", $self->cur->i);
            }
            
            # Stop parsing sequence if we hit end, closing paren, or alternation pipe
            last if $ch eq '' || $ch =~ /[)|]/;
            
            # Parse the fundamental unit (literal, class, group, escape, etc.)
            my $atom = $self->parse_atom();
            
            # Parse any quantifier (*, +, ?, {m,n}) that might follow the atom
            my ($quantified_atom, $had_failed_quant_parse) = $self->parse_quant_if_any($atom);
            
            # Coalesce adjacent Lit nodes
            my $should_coalesce = (
                ref($quantified_atom) eq 'STRling::Core::Nodes::Lit'
                && @parts > 0
                && ref($parts[-1]) eq 'STRling::Core::Nodes::Lit'
                && !$self->cur->extended_mode
                && !$prev_had_failed_quant
            );
            
            if ($should_coalesce) {
                $parts[-1] = STRling::Core::Nodes::Lit->new(
                    value => $parts[-1]->value . $quantified_atom->value
                );
            } else {
                push @parts, $quantified_atom;
            }
            
            $prev_had_failed_quant = $had_failed_quant_parse;
        }
        
        # If the sequence ended up being just one atom, return it directly
        if (@parts == 1) {
            return $parts[0];
        }
        
        # Otherwise, return a Sequence node containing all parts
        return STRling::Core::Nodes::Seq->new(parts => \@parts);
    }
    
    sub parse_quant_if_any {
        my ($self, $child) = @_;
        
        my $cur = $self->cur;
        my $ch = $cur->peek();
        
        my ($min_val, $max_val, $mode) = (undef, undef, 'Greedy');
        my $had_failed_quant_parse = 0;
        
        if ($ch eq '*') {
            ($min_val, $max_val) = (0, 'Inf');
            $cur->take();
        } elsif ($ch eq '+') {
            ($min_val, $max_val) = (1, 'Inf');
            $cur->take();
        } elsif ($ch eq '?') {
            ($min_val, $max_val) = (0, 1);
            $cur->take();
        } elsif ($ch eq '{') {
            my $save = $cur->i;
            my ($m, $n, $parsed_mode) = $self->parse_brace_quant();
            if (defined $m) {
                ($min_val, $max_val, $mode) = ($m, $n, $parsed_mode);
            } else {
                $had_failed_quant_parse = 1;
                $cur->i($save);  # Backtrack
            }
        }
        
        # If we didn't parse a quantifier, we're done
        if (!defined $min_val) {
            return ($child, $had_failed_quant_parse);
        }
        
        # Semantic validation: Cannot quantify anchors
        if (ref($child) eq 'STRling::Core::Nodes::Anchor') {
            $self->_raise_error("Cannot quantify anchor", $cur->i);
        }
        
        # Now check for lazy/possessive modifiers
        my $nxt = $cur->peek();
        if ($nxt eq '?') {
            $mode = 'Lazy';
            $cur->take();
        } elsif ($nxt eq '+') {
            $mode = 'Possessive';
            $cur->take();
        }
        
        return (
            STRling::Core::Nodes::Quant->new(
                child => $child,
                min   => $min_val,
                max   => $max_val,
                mode  => $mode,
            ),
            $had_failed_quant_parse
        );
    }
    
    sub parse_brace_quant {
        my ($self) = @_;
        
        my $cur = $self->cur;
        return (undef, undef, 'Greedy') unless $cur->match('{');
        
        my $quant_start = $cur->i - 1;
        my $m = $self->_read_int_optional();
        
        if (!defined $m) {
            # No leading digits - check if this looks like invalid content
            my $j = 0;
            my $content = '';
            while (1) {
                my $ch = $cur->peek($j);
                last if $ch eq '' || $ch eq '}' || $ch =~ /[\r\n]/;
                $content .= $ch;
                $j++;
            }
            
            if ($cur->peek($j) eq '}') {
                # If content has chars other than digits or commas, reject
                if ($content =~ /[^0-9,]/) {
                    $self->_raise_error(
                        "Brace quantifier: Invalid brace quantifier content",
                        $quant_start
                    );
                }
            }
            
            # Otherwise, it's not a quantifier - treat as literal and backtrack
            return (undef, undef, 'Greedy');
        }
        
        # We have at least one digit
        if ($cur->peek() eq ',') {
            $cur->take();
            my $n = $self->_read_int_optional();
            
            if (!defined $n) {
                # {m,} format
                if ($cur->match('}')) {
                    return ($m, 'Inf', 'Greedy');
                } else {
                    $self->_raise_error("Incomplete quantifier", $cur->i);
                }
            } else {
                # {m,n} format
                if ($cur->match('}')) {
                    if ($m > $n) {
                        $self->_raise_error("Invalid quantifier range", $quant_start);
                    }
                    return ($m, $n, 'Greedy');
                } else {
                    $self->_raise_error("Incomplete quantifier", $cur->i);
                }
            }
        } else {
            # {n} format
            if ($cur->match('}')) {
                return ($m, $m, 'Greedy');
            } else {
                $self->_raise_error("Incomplete quantifier", $cur->i);
            }
        }
    }
    
    sub _read_int_optional {
        my ($self) = @_;
        
        my $cur = $self->cur;
        my $num = '';
        
        while ($cur->peek() =~ /[0-9]/) {
            $num .= $cur->take();
        }
        
        return undef if $num eq '';
        return int($num);
    }
    
    sub parse_atom {
        my ($self) = @_;
        
        my $cur = $self->cur;
        my $ch = $cur->peek();
        
        # Anchors
        if ($ch eq '^') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'Start');
        }
        if ($ch eq '$') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'End');
        }
        
        # Dot
        if ($ch eq '.') {
            $cur->take();
            return STRling::Core::Nodes::Dot->new();
        }
        
        # Character class
        if ($ch eq '[') {
            return $self->parse_char_class();
        }
        
        # Group or lookaround
        if ($ch eq '(') {
            return $self->parse_group_or_look();
        }
        
        # Escape sequence
        if ($ch eq '\\') {
            return $self->parse_escape_atom();
        }
        
        # Regular literal
        $cur->take();
        return STRling::Core::Nodes::Lit->new(value => $ch);
    }
    
    sub parse_escape_atom {
        my ($self) = @_;
        
        my $cur = $self->cur;
        $cur->take();  # consume backslash
        
        my $ch = $cur->peek();
        if ($ch eq '') {
            $self->_raise_error("Unexpected end of pattern after backslash", $cur->i);
        }
        
        # Anchors
        if ($ch eq 'b') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'WordBoundary');
        }
        if ($ch eq 'B') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'NotWordBoundary');
        }
        if ($ch eq 'A') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'AbsoluteStart');
        }
        if ($ch eq 'Z') {
            $cur->take();
            return STRling::Core::Nodes::Anchor->new(at => 'EndBeforeFinalNewline');
        }
        
        # Backreferences
        if ($ch =~ /[1-9]/) {
            my $num = '';
            while ($cur->peek() =~ /[0-9]/) {
                $num .= $cur->take();
            }
            my $n = int($num);
            if ($n > $self->_cap_count) {
                $self->_raise_error("Backreference to undefined group", $cur->i - length($num));
            }
            return STRling::Core::Nodes::Backref->new(index => $n);
        }
        
        # Named backreference
        if ($ch eq 'k') {
            $cur->take();
            if ($cur->peek() ne '<') {
                $self->_raise_error("Expected '<' after \\k", $cur->i);
            }
            $cur->take();
            my $name = '';
            while ($cur->peek() ne '>' && !$cur->eof()) {
                $name .= $cur->take();
            }
            if ($cur->peek() ne '>') {
                $self->_raise_error("Unterminated named backref", $cur->i);
            }
            $cur->take();
            return STRling::Core::Nodes::Backref->new(name => $name);
        }
        
        # Character classes
        if ($ch eq 'd') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 1,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'digit')],
            );
        }
        if ($ch eq 'D') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 0,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'digit')],
            );
        }
        if ($ch eq 'w') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 1,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'word')],
            );
        }
        if ($ch eq 'W') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 0,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'word')],
            );
        }
        if ($ch eq 's') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 1,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'space')],
            );
        }
        if ($ch eq 'S') {
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => 0,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => 'space')],
            );
        }
        
        # Control escapes
        if (exists $self->CONTROL_ESCAPES->{$ch}) {
            $cur->take();
            return STRling::Core::Nodes::Lit->new(value => $self->CONTROL_ESCAPES->{$ch});
        }
        
        # Hex escape
        if ($ch eq 'x') {
            $cur->take();
            my $hex = '';
            if ($cur->peek() eq '{') {
                $cur->take();
                while ($cur->peek() =~ /[0-9a-fA-F]/) {
                    $hex .= $cur->take();
                }
                if ($cur->peek() ne '}') {
                    $self->_raise_error("Unterminated \\x{...}", $cur->i);
                }
                $cur->take();
            } else {
                for (1..2) {
                    if ($cur->peek() =~ /[0-9a-fA-F]/) {
                        $hex .= $cur->take();
                    } else {
                        $self->_raise_error("Invalid \\xHH escape", $cur->i);
                    }
                }
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        
        # Unicode escape
        if ($ch eq 'u') {
            $cur->take();
            my $hex = '';
            if ($cur->peek() eq '{') {
                $cur->take();
                while ($cur->peek() =~ /[0-9a-fA-F]/) {
                    $hex .= $cur->take();
                }
                if ($cur->peek() ne '}') {
                    $self->_raise_error("Unterminated \\u{...}", $cur->i);
                }
                $cur->take();
            } else {
                for (1..4) {
                    if ($cur->peek() =~ /[0-9a-fA-F]/) {
                        $hex .= $cur->take();
                    } else {
                        $self->_raise_error("Invalid \\uHHHH", $cur->i);
                    }
                }
            }
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        
        # Unicode property
        if ($ch eq 'p' || $ch eq 'P') {
            my $negative = ($ch eq 'P');
            $cur->take();
            if ($cur->peek() ne '{') {
                $self->_raise_error("Expected { after \\p/\\P", $cur->i);
            }
            $cur->take();
            my $prop = '';
            while ($cur->peek() ne '}' && !$cur->eof()) {
                $prop .= $cur->take();
            }
            if ($cur->peek() ne '}') {
                $self->_raise_error("Unterminated \\p{...}", $cur->i);
            }
            $cur->take();
            return STRling::Core::Nodes::CharClass->new(
                positive => !$negative,
                items    => [STRling::Core::Nodes::ClassEscape->new(kind => "unicode_$prop")],
            );
        }
        
        # Unknown escape - check if it's a known character
        if ($ch =~ /[z]/) {
            $self->_raise_error("Unknown escape sequence \\$ch", $cur->i - 1);
        }
        
        # Identity escape - literal character
        $cur->take();
        return STRling::Core::Nodes::Lit->new(value => $ch);
    }
    
    sub parse_char_class {
        my ($self) = @_;
        
        my $cur = $self->cur;
        $cur->take();  # consume '['
        
        my $positive = 1;
        if ($cur->peek() eq '^') {
            $positive = 0;
            $cur->take();
        }
        
        my @items;
        $cur->in_class($cur->in_class + 1);
        
        while (!$cur->eof() && $cur->peek() ne ']') {
            my $ch = $cur->peek();
            
            # Escape sequence in character class
            if ($ch eq '\\') {
                $cur->take();
                my $esc_ch = $cur->peek();
                
                # Unicode property
                if ($esc_ch eq 'p' || $esc_ch eq 'P') {
                    my $negative = ($esc_ch eq 'P');
                    $cur->take();
                    if ($cur->peek() ne '{') {
                        $self->_raise_error("Expected { after \\p/\\P", $cur->i);
                    }
                    $cur->take();
                    my $prop = '';
                    while ($cur->peek() ne '}' && !$cur->eof()) {
                        $prop .= $cur->take();
                    }
                    if ($cur->peek() ne '}') {
                        $self->_raise_error("Unterminated \\p{...}", $cur->i);
                    }
                    $cur->take();
                    push @items, STRling::Core::Nodes::ClassEscape->new(kind => "unicode_$prop");
                } else {
                    $cur->take();
                    push @items, STRling::Core::Nodes::ClassLiteral->new(ch => $esc_ch);
                }
            } else {
                $cur->take();
                push @items, STRling::Core::Nodes::ClassLiteral->new(ch => $ch);
            }
        }
        
        if ($cur->peek() ne ']') {
            $self->_raise_error("Unterminated character class", $cur->i);
        }
        $cur->take();
        $cur->in_class($cur->in_class - 1);
        
        return STRling::Core::Nodes::CharClass->new(
            positive => $positive,
            items    => \@items,
        );
    }
    
    sub parse_group_or_look {
        my ($self) = @_;
        
        my $cur = $self->cur;
        $cur->take();  # consume '('
        
        # Check for special group types
        if ($cur->peek() eq '?') {
            $cur->take();
            my $next = $cur->peek();
            
            # Non-capturing group
            if ($next eq ':') {
                $cur->take();
                my $body = $self->parse_alt();
                if (!$cur->match(')')) {
                    $self->_raise_error("Unterminated group", $cur->i);
                }
                return STRling::Core::Nodes::Group->new(
                    capturing => 0,
                    body      => $body,
                );
            }
            
            # Named group
            if ($next eq '<') {
                $cur->take();
                # Check for lookbehind first
                my $lookahead_ch = $cur->peek();
                if ($lookahead_ch eq '=') {
                    # Positive lookbehind
                    $cur->take();
                    my $body = $self->parse_alt();
                    if (!$cur->match(')')) {
                        $self->_raise_error("Unterminated lookbehind", $cur->i);
                    }
                    return STRling::Core::Nodes::Look->new(
                        direction => 'Behind',
                        negative  => 0,
                        body      => $body,
                    );
                } elsif ($lookahead_ch eq '!') {
                    # Negative lookbehind
                    $cur->take();
                    my $body = $self->parse_alt();
                    if (!$cur->match(')')) {
                        $self->_raise_error("Unterminated lookbehind", $cur->i);
                    }
                    return STRling::Core::Nodes::Look->new(
                        direction => 'Behind',
                        negative  => 1,
                        body      => $body,
                    );
                }
                
                # Named capturing group
                my $name = '';
                while ($cur->peek() ne '>' && !$cur->eof()) {
                    $name .= $cur->take();
                }
                if ($cur->peek() ne '>') {
                    $self->_raise_error("Unterminated group name", $cur->i);
                }
                $cur->take();
                
                # Check for duplicate names
                if (exists $self->_cap_names->{$name}) {
                    $self->_raise_error("Duplicate group name", $cur->i);
                }
                $self->_cap_names->{$name} = 1;
                $self->_cap_count($self->_cap_count + 1);
                
                my $body = $self->parse_alt();
                if (!$cur->match(')')) {
                    $self->_raise_error("Unterminated group", $cur->i);
                }
                return STRling::Core::Nodes::Group->new(
                    capturing => 1,
                    name      => $name,
                    body      => $body,
                );
            }
            
            # Atomic group
            if ($next eq '>') {
                $cur->take();
                my $body = $self->parse_alt();
                if (!$cur->match(')')) {
                    $self->_raise_error("Unterminated atomic group", $cur->i);
                }
                return STRling::Core::Nodes::Group->new(
                    capturing => 0,
                    atomic    => 1,
                    body      => $body,
                );
            }
            
            # Positive lookahead
            if ($next eq '=') {
                $cur->take();
                my $body = $self->parse_alt();
                if (!$cur->match(')')) {
                    $self->_raise_error("Unterminated lookahead", $cur->i);
                }
                return STRling::Core::Nodes::Look->new(
                    direction => 'Ahead',
                    negative  => 0,
                    body      => $body,
                );
            }
            
            # Negative lookahead
            if ($next eq '!') {
                $cur->take();
                my $body = $self->parse_alt();
                if (!$cur->match(')')) {
                    $self->_raise_error("Unterminated lookahead", $cur->i);
                }
                return STRling::Core::Nodes::Look->new(
                    direction => 'Ahead',
                    negative  => 1,
                    body      => $body,
                );
            }
            
            # Inline modifiers (not supported)
            if ($next =~ /[imsx]/) {
                $self->_raise_error("Inline modifiers `(?imsx)` are not supported", $cur->i - 1);
            }
        }
        
        # Capturing group
        $self->_cap_count($self->_cap_count + 1);
        my $body = $self->parse_alt();
        if (!$cur->match(')')) {
            $self->_raise_error("Unterminated group", $cur->i);
        }
        return STRling::Core::Nodes::Group->new(
            capturing => 1,
            body      => $body,
        );
    }
}

# ---------------- Public API ----------------

sub parse {
    my ($src) = @_;
    
    my $p = STRling::Core::parser::Parser->new(_original_text => $src);
    return ($p->flags, $p->parse());
}

sub parse_to_artifact {
    my ($src) = @_;
    
    my ($flags, $root) = parse($src);
    
    return {
        version  => '1.0.0',
        flags    => $flags->to_dict(),
        root     => $root->to_dict(),
        warnings => [],
        errors   => [],
    };
}

=head1 FUNCTIONS

=head2 parse

Parse a STRling pattern string into an AST.

    my ($flags, $ast) = parse($pattern);

Returns a tuple of (Flags object, AST root node).

=head2 parse_to_artifact

Parse a STRling pattern and return a complete artifact hashref.

    my $artifact = parse_to_artifact($pattern);

Returns a hashref with version, flags, root, warnings, and errors.

=head1 SEE ALSO

L<STRling::Core::Nodes>, L<STRling::Core::Errors>

=cut

1;
