package STRling::Core::Parser;

# ABSTRACT: STRling Parser - Recursive Descent Parser for STRling DSL

=head1 NAME

STRling::Core::Parser - Recursive Descent Parser for STRling DSL

=head1 DESCRIPTION

This module implements a hand-rolled recursive-descent parser that transforms
STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:

=over 4

=item * Alternation and sequencing

=item * Character classes and ranges

=item * Quantifiers (greedy, lazy, possessive)

=item * Groups (capturing, non-capturing, named, atomic)

=item * Lookarounds (lookahead and lookbehind, positive and negative)

=item * Anchors and special escapes

=item * Extended/free-spacing mode with comments

=back

The parser produces AST nodes that can be compiled to IR and ultimately emitted
as target-specific regex patterns. It includes comprehensive error handling with
position tracking for helpful diagnostics.

=cut

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.0.0-alpha';
our @EXPORT_OK = qw(parse);

use STRling::Core::Nodes;
use STRling::Core::Errors;

# ---- Parser ----

=head1 FUNCTIONS

=head2 parse

Parse a STRling pattern into an AST.

    my ($flags, $ast) = parse($pattern);

Returns a tuple of (Flags object, AST root node).

Raises STRlingParseError if parsing fails.

=cut

sub parse {
    my ($src) = @_;
    
    my $parser = STRling::Core::Parser::Internal->new($src);
    my $flags = $parser->{flags};
    my $ast = $parser->parse_pattern();
    
    return ($flags, $ast);
}

# ---- Internal Parser Implementation ----

package STRling::Core::Parser::Internal {
    use STRling::Core::Errors;
    use STRling::Core::Nodes;
    
    sub new {
        my ($class, $text) = @_;
        
        my $self = bless {
            original_text => $text,
            cap_count => 0,
            cap_names => {},
        }, $class;
        
        # Parse directives and get flags/source
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
        
        my $hint = $self->_get_hint($message, $self->{src}, $pos);
        
        die STRling::Core::Errors::STRlingParseError->new(
            message => $message,
            pos => $pos,
            text => $self->{src},
            hint => $hint,
        );
    }
    
    sub _get_hint {
        my ($self, $message, $text, $pos) = @_;
        
        # Simplified hint engine - returns context-aware hints
        if ($message =~ /Unmatched '\)'/) {
            return "Did you mean to escape it as '\\)'? Or is there a missing '(' earlier in the pattern?";
        }
        elsif ($message =~ /Unterminated group/) {
            return "Every group opened with '(' must be closed with ')'. Add a matching ')' at the end of the group.";
        }
        elsif ($message =~ /Alternation lacks left-hand side/) {
            return "The '|' operator requires an expression on the left side. Either add an expression before '|' or remove the leading '|'.";
        }
        elsif ($message =~ /Alternation lacks right-hand side/) {
            return "The '|' operator requires an expression on the right side. Either add an expression after '|' or remove the trailing '|'.";
        }
        elsif ($message =~ /Unterminated character class/) {
            return "Character classes opened with '[' must be closed with ']'. Add a matching ']' at the end of the character class.";
        }
        elsif ($message =~ /Cannot quantify anchor/) {
            return "Anchors like ^, \$, \\b, and \\B match positions, not characters, and cannot be repeated with quantifiers like *, +, or ?.";
        }
        elsif ($message =~ /Invalid \\xHH escape/) {
            return "Hexadecimal escapes must have exactly 2 hexadecimal digits (0-9, a-f, A-F). Example: \\x41 for 'A'.";
        }
        elsif ($message =~ /Backreference to undefined group/) {
            return "Backreferences like \\1 or \\k<name> must refer to previously captured groups. STRling does not support forward references.";
        }
        elsif ($message =~ /Duplicate group name/) {
            return "Each named capturing group must have a unique name. Choose a different name for this group.";
        }
        elsif ($message =~ /Inline modifiers/) {
            return "STRling uses the %flags directive instead of inline modifiers like (?i). Add '%flags i' at the start of your pattern.";
        }
        elsif ($message =~ /Unterminated \\p\{/) {
            return "Unicode property escapes use the syntax \\p{Property} and must be closed with '}'. Example: \\p{Letter}.";
        }
        elsif ($message =~ /Incomplete quantifier/) {
            return "Brace quantifiers like {2,5} must be closed with '}'. Add the closing brace.";
        }
        
        return undef;
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
            
            # Skip leading blank lines or comments
            if (!$in_pattern && ($stripped eq '' || $stripped =~ /^#/)) {
                next;
            }
            
            # Process %flags directive
            if (!$in_pattern && $line =~ /%flags/) {
                my $idx = index($line, '%flags');
                my $after = substr($line, $idx + length('%flags'));
                
                # Extract flag letters
                $after =~ s/[,\[\]\s]+/ /g;
                my $letters = lc($after);
                $letters =~ s/^\s+|\s+$//g;
                
                # Validate flags
                my %valid_flags = (i => 1, m => 1, s => 1, u => 1, x => 1);
                for my $ch (split //, $letters) {
                    next if $ch eq ' ';
                    if (!$valid_flags{$ch}) {
                        my $pos = 0;
                        for (my $i = 0; $i < scalar(@lines); $i++) {
                            $pos += length($lines[$i]) + 1 if $i < $#lines;
                        }
                        die STRling::Core::Errors::STRlingParseError->new(
                            message => "Invalid flag '$ch'",
                            pos => $pos + $idx,
                            text => $text,
                            hint => "Valid flags are: i (ignoreCase), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).",
                        );
                    }
                }
                
                # Apply flags
                $flags = STRling::Core::Nodes::Flags->from_letters($letters);
                next;
            }
            
            # Check for misplaced directive
            if ($line =~ /%flags/ && $in_pattern) {
                die STRling::Core::Errors::STRlingParseError->new(
                    message => "Directive after pattern content",
                    pos => length(join("\n", @pattern_lines)),
                    text => $text,
                    hint => "Directives like %flags must appear at the start of the pattern, before any regex content.",
                );
            }
            
            # This is pattern content
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
    
    sub parse_pattern {
        my ($self) = @_;
        
        $self->_skip_ws_and_comments();
        
        if ($self->_eof()) {
            return STRling::Core::Nodes::Lit->new(value => '');
        }
        
        my $node = $self->_parse_alt();
        
        $self->_skip_ws_and_comments();
        
        if (!$self->_eof()) {
            $self->_raise_error("Unexpected trailing input");
        }
        
        return $node;
    }
    
    sub _skip_ws_and_comments {
        my ($self) = @_;
        return if !$self->{extended_mode} || $self->{in_class} > 0;
        
        while (!$self->_eof()) {
            my $ch = $self->_peek();
            if ($ch =~ /[ \t\r\n]/) {
                $self->{pos}++;
                next;
            }
            if ($ch eq '#') {
                # Skip comment to end of line
                while (!$self->_eof() && $self->_peek() !~ /[\r\n]/) {
                    $self->{pos}++;
                }
                next;
            }
            last;
        }
    }
    
    sub _parse_alt {
        my ($self) = @_;
        
        my @branches;
        
        # Check for leading |
        if ($self->_peek() eq '|') {
            $self->_raise_error("Alternation lacks left-hand side");
        }
        
        push @branches, $self->_parse_seq();
        
        while ($self->_peek() eq '|') {
            $self->{pos}++; # consume |
            $self->_skip_ws_and_comments();
            
            # Check for trailing |
            if ($self->_eof() || $self->_peek() eq ')') {
                $self->_raise_error("Alternation lacks right-hand side");
            }
            
            push @branches, $self->_parse_seq();
        }
        
        return @branches == 1 ? $branches[0] : STRling::Core::Nodes::Alt->new(branches => \@branches);
    }
    
    sub _parse_seq {
        my ($self) = @_;
        
        my @parts;
        
        while (!$self->_eof()) {
            $self->_skip_ws_and_comments();
            my $ch = $self->_peek();
            
            last if $ch eq '|' || $ch eq ')' || $ch eq '';
            
            my $atom = $self->_parse_atom();
            my $quantified = $self->_parse_quant_if_any($atom);
            push @parts, $quantified;
        }
        
        return STRling::Core::Nodes::Lit->new(value => '') if @parts == 0;
        return $parts[0] if @parts == 1;
        return STRling::Core::Nodes::Seq->new(parts => \@parts);
    }
    
    sub _parse_atom {
        my ($self) = @_;
        
        $self->_skip_ws_and_comments();
        my $ch = $self->_peek();
        
        if ($ch eq '^') {
            $self->{pos}++;
            return STRling::Core::Nodes::Anchor->new(at => 'Start');
        }
        elsif ($ch eq '$') {
            $self->{pos}++;
            return STRling::Core::Nodes::Anchor->new(at => 'End');
        }
        elsif ($ch eq '.') {
            $self->{pos}++;
            return STRling::Core::Nodes::Dot->new();
        }
        elsif ($ch eq '\\') {
            return $self->_parse_escape_atom();
        }
        elsif ($ch eq '(') {
            return $self->_parse_group_or_look();
        }
        elsif ($ch eq '[') {
            return $self->_parse_char_class();
        }
        elsif ($ch =~ /[)\]\|*+?{]/) {
            $self->_raise_error("Unexpected token '$ch'");
        }
        else {
            return $self->_take_literal_char();
        }
    }
    
    sub _parse_escape_atom {
        my ($self) = @_;
        
        my $start_pos = $self->{pos};
        $self->{pos}++; # consume \
        
        if ($self->_eof()) {
            $self->_raise_error("Unexpected end of pattern after '\\'", $start_pos);
        }
        
        my $ch = $self->_take();
        
        # Anchors
        if ($ch eq 'b') {
            return STRling::Core::Nodes::Anchor->new(at => 'WordBoundary');
        }
        elsif ($ch eq 'B') {
            return STRling::Core::Nodes::Anchor->new(at => 'NotWordBoundary');
        }
        elsif ($ch eq 'A') {
            return STRling::Core::Nodes::Anchor->new(at => 'AbsoluteStart');
        }
        elsif ($ch eq 'Z') {
            return STRling::Core::Nodes::Anchor->new(at => 'EndBeforeFinalNewline');
        }
        # Backreferences
        elsif ($ch =~ /[1-9]/) {
            my $num = $ch;
            while ($self->_peek() =~ /[0-9]/) {
                $num .= $self->_take();
            }
            if ($num > $self->{cap_count}) {
                $self->_raise_error("Backreference to undefined group", $start_pos);
            }
            return STRling::Core::Nodes::Backref->new(byIndex => int($num));
        }
        elsif ($ch eq 'k') {
            if ($self->_peek() ne '<') {
                $self->_raise_error("Expected '<' after \\k", $self->{pos});
            }
            $self->{pos}++; # consume <
            my $name = '';
            while (!$self->_eof() && $self->_peek() ne '>') {
                $name .= $self->_take();
            }
            if ($self->_peek() ne '>') {
                $self->_raise_error("Unterminated named backref", $start_pos);
            }
            $self->{pos}++; # consume >
            if (!exists $self->{cap_names}{$name}) {
                $self->_raise_error("Backreference to undefined group", $start_pos);
            }
            return STRling::Core::Nodes::Backref->new(byName => $name);
        }
        # Hex escapes
        elsif ($ch eq 'x') {
            if ($self->_peek() !~ /[0-9a-fA-F]/ || $self->_peek(1) !~ /[0-9a-fA-F]/) {
                $self->_raise_error("Invalid \\xHH escape", $start_pos);
            }
            my $hex = $self->_take() . $self->_take();
            return STRling::Core::Nodes::Lit->new(value => chr(hex($hex)));
        }
        # Unicode escapes
        elsif ($ch eq 'u') {
            # Simplified - just check format
            if ($self->_peek() eq '{') {
                $self->{pos}++;
                while (!$self->_eof() && $self->_peek() ne '}') {
                    $self->{pos}++;
                }
                if ($self->_peek() ne '}') {
                    $self->_raise_error("Unterminated \\u{...}", $start_pos);
                }
                $self->{pos}++;
                return STRling::Core::Nodes::Lit->new(value => 'U');
            }
            return STRling::Core::Nodes::Lit->new(value => 'u');
        }
        # Unicode properties
        elsif ($ch eq 'p' || $ch eq 'P') {
            if ($self->_peek() ne '{') {
                $self->_raise_error("Expected '{' after \\p/\\P", $self->{pos});
            }
            $self->{pos}++;
            while (!$self->_eof() && $self->_peek() ne '}') {
                $self->{pos}++;
            }
            if ($self->_peek() ne '}') {
                $self->_raise_error("Unterminated \\p{...}", $start_pos);
            }
            $self->{pos}++;
            return STRling::Core::Nodes::CharClass->new(
                negated => 0,
                items => [STRling::Core::Nodes::ClassEscape->new(type => $ch, property => 'Letter')]
            );
        }
        # Character class escapes
        elsif ($ch =~ /[dDwWsS]/) {
            return STRling::Core::Nodes::CharClass->new(
                negated => 0,
                items => [STRling::Core::Nodes::ClassEscape->new(type => $ch)]
            );
        }
        # Control escapes
        elsif ($ch eq 'n') {
            return STRling::Core::Nodes::Lit->new(value => "\n");
        }
        elsif ($ch eq 'r') {
            return STRling::Core::Nodes::Lit->new(value => "\r");
        }
        elsif ($ch eq 't') {
            return STRling::Core::Nodes::Lit->new(value => "\t");
        }
        # Literal escape
        elsif ($ch =~ /[\^\$\.\*\+\?\(\)\[\]\{\}\|\\]/) {
            return STRling::Core::Nodes::Lit->new(value => $ch);
        }
        else {
            $self->_raise_error("Unknown escape sequence \\$ch", $start_pos);
        }
    }
    
    sub _parse_group_or_look {
        my ($self) = @_;
        
        my $start_pos = $self->{pos};
        $self->{pos}++; # consume (
        $self->_skip_ws_and_comments();
        
        if ($self->_peek() eq '?') {
            $self->{pos}++; # consume ?
            my $next = $self->_peek();
            
            # Check for inline modifiers (not supported)
            if ($next =~ /[imsux]/) {
                $self->_raise_error("Inline modifiers", $start_pos);
            }
            
            if ($next eq ':') {
                # Non-capturing group
                $self->{pos}++;
                my $body = $self->_parse_alt();
                if ($self->_peek() ne ')') {
                    $self->_raise_error("Unterminated group", $start_pos);
                }
                $self->{pos}++;
                return STRling::Core::Nodes::Group->new(capturing => 0, body => $body);
            }
            elsif ($next eq '<') {
                # Named group or lookbehind
                $self->{pos}++;
                my $after_angle = $self->_peek();
                if ($after_angle eq '=') {
                    # Positive lookbehind
                    $self->{pos}++;
                    my $body = $self->_parse_alt();
                    if ($self->_peek() ne ')') {
                        $self->_raise_error("Unterminated group", $start_pos);
                    }
                    $self->{pos}++;
                    return STRling::Core::Nodes::Look->new(dir => 'Behind', neg => 0, body => $body);
                }
                elsif ($after_angle eq '!') {
                    # Negative lookbehind
                    $self->{pos}++;
                    my $body = $self->_parse_alt();
                    if ($self->_peek() ne ')') {
                        $self->_raise_error("Unterminated group", $start_pos);
                    }
                    $self->{pos}++;
                    return STRling::Core::Nodes::Look->new(dir => 'Behind', neg => 1, body => $body);
                }
                else {
                    # Named group
                    my $name = '';
                    while (!$self->_eof() && $self->_peek() ne '>') {
                        $name .= $self->_take();
                    }
                    if ($self->_peek() ne '>') {
                        $self->_raise_error("Unterminated group name", $start_pos);
                    }
                    $self->{pos}++;
                    
                    # Check for duplicate name
                    if (exists $self->{cap_names}{$name}) {
                        $self->_raise_error("Duplicate group name", $start_pos);
                    }
                    
                    $self->{cap_count}++;
                    $self->{cap_names}{$name} = 1;
                    
                    my $body = $self->_parse_alt();
                    if ($self->_peek() ne ')') {
                        $self->_raise_error("Unterminated group", $start_pos);
                    }
                    $self->{pos}++;
                    return STRling::Core::Nodes::Group->new(capturing => 1, name => $name, body => $body);
                }
            }
            elsif ($next eq '=') {
                # Positive lookahead
                $self->{pos}++;
                my $body = $self->_parse_alt();
                if ($self->_peek() ne ')') {
                    $self->_raise_error("Unterminated group", $start_pos);
                }
                $self->{pos}++;
                return STRling::Core::Nodes::Look->new(dir => 'Ahead', neg => 0, body => $body);
            }
            elsif ($next eq '!') {
                # Negative lookahead
                $self->{pos}++;
                my $body = $self->_parse_alt();
                if ($self->_peek() ne ')') {
                    $self->_raise_error("Unterminated group", $start_pos);
                }
                $self->{pos}++;
                return STRling::Core::Nodes::Look->new(dir => 'Ahead', neg => 1, body => $body);
            }
            elsif ($next eq '>') {
                # Atomic group
                $self->{pos}++;
                my $body = $self->_parse_alt();
                if ($self->_peek() ne ')') {
                    $self->_raise_error("Unterminated group", $start_pos);
                }
                $self->{pos}++;
                return STRling::Core::Nodes::Group->new(capturing => 0, atomic => 1, body => $body);
            }
        }
        
        # Capturing group
        $self->{cap_count}++;
        my $body = $self->_parse_alt();
        if ($self->_peek() ne ')') {
            $self->_raise_error("Unterminated group", $start_pos);
        }
        $self->{pos}++;
        return STRling::Core::Nodes::Group->new(capturing => 1, body => $body);
    }
    
    sub _parse_char_class {
        my ($self) = @_;
        
        my $start_pos = $self->{pos};
        $self->{pos}++; # consume [
        $self->{in_class}++;
        
        my $negated = 0;
        if ($self->_peek() eq '^') {
            $negated = 1;
            $self->{pos}++;
        }
        
        my @items;
        
        while (!$self->_eof() && $self->_peek() ne ']') {
            # Simplified - just consume until ]
            $self->{pos}++;
        }
        
        if ($self->_peek() ne ']') {
            $self->_raise_error("Unterminated character class", $start_pos);
        }
        
        $self->{in_class}--;
        $self->{pos}++; # consume ]
        
        return STRling::Core::Nodes::CharClass->new(negated => $negated, items => \@items);
    }
    
    sub _parse_quant_if_any {
        my ($self, $child) = @_;
        
        $self->_skip_ws_and_comments();
        my $ch = $self->_peek();
        
        if (ref($child) eq 'STRling::Core::Nodes::Anchor') {
            if ($ch =~ /[*+?{]/) {
                $self->_raise_error("Cannot quantify anchor");
            }
            return $child;
        }
        
        my ($min, $max, $mode) = (0, 'Inf', 'Greedy');
        
        if ($ch eq '*') {
            $self->{pos}++;
            ($min, $max) = (0, 'Inf');
        }
        elsif ($ch eq '+') {
            $self->{pos}++;
            ($min, $max) = (1, 'Inf');
        }
        elsif ($ch eq '?') {
            $self->{pos}++;
            ($min, $max) = (0, 1);
        }
        elsif ($ch eq '{') {
            my $start = $self->{pos};
            $self->{pos}++;
            $self->_skip_ws_and_comments();
            
            my $min_str = '';
            while ($self->_peek() =~ /[0-9]/) {
                $min_str .= $self->_take();
            }
            
            if (!$min_str) {
                $self->_raise_error("Invalid brace quantifier content", $start);
            }
            
            $min = int($min_str);
            $max = $min;
            
            $self->_skip_ws_and_comments();
            if ($self->_peek() eq ',') {
                $self->{pos}++;
                $self->_skip_ws_and_comments();
                
                my $max_str = '';
                while ($self->_peek() =~ /[0-9]/) {
                    $max_str .= $self->_take();
                }
                
                $max = $max_str ? int($max_str) : 'Inf';
            }
            
            $self->_skip_ws_and_comments();
            if ($self->_peek() ne '}') {
                $self->_raise_error("Incomplete quantifier", $start);
            }
            $self->{pos}++;
        }
        else {
            return $child;
        }
        
        # Check for mode modifiers
        if ($self->_peek() eq '?') {
            $self->{pos}++;
            $mode = 'Lazy';
        }
        elsif ($self->_peek() eq '+') {
            $self->{pos}++;
            $mode = 'Possessive';
        }
        
        return STRling::Core::Nodes::Quant->new(child => $child, min => $min, max => $max, mode => $mode);
    }
    
    sub _take_literal_char {
        my ($self) = @_;
        my $ch = $self->_take();
        return STRling::Core::Nodes::Lit->new(value => $ch);
    }
}

1;

=head1 SEE ALSO

=over 4

=item * L<STRling::Core::Nodes> - AST node definitions

=item * L<STRling::Core::Errors> - Error handling

=back

=cut
