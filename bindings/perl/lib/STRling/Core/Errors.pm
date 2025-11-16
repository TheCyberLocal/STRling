package STRling::Core::Errors;

# ABSTRACT: STRling Error Classes - Rich Error Handling for Instructional Diagnostics

=head1 NAME

STRling::Core::Errors - Rich Error Handling for Instructional Diagnostics

=head1 DESCRIPTION

This module provides enhanced error classes that deliver context-aware,
instructional error messages. The STRlingParseError class stores detailed
information about syntax errors including position, context, and beginner-friendly
hints for resolution.

=cut

use strict;
use warnings;
use Moo;
use overload '""' => \&to_formatted_string, fallback => 1;

our $VERSION = '3.0.0-alpha';

=head1 CLASSES

=head2 STRlingParseError

Rich parse error with position tracking and instructional hints.

This error class transforms parse failures into learning opportunities by
providing:

=over 4

=item * The specific error message

=item * The exact position where the error occurred

=item * The full line of text containing the error

=item * A beginner-friendly hint explaining how to fix the issue

=back

=head3 ATTRIBUTES

=over 4

=item message

A concise description of what went wrong.

=item pos

The character position (0-indexed) where the error occurred.

=item text

The full input text being parsed.

=item hint

An instructional hint explaining how to fix the error (optional).

=back

=cut

has 'message' => (
    is       => 'ro',
    required => 1,
    # A concise description of what went wrong
);

has 'pos' => (
    is       => 'ro',
    required => 1,
    # The character position (0-indexed) where the error occurred
);

has 'text' => (
    is      => 'ro',
    default => sub { '' },
    # The full input text being parsed
);

has 'hint' => (
    is => 'ro',
    # An instructional hint explaining how to fix the error
);

=head3 METHODS

=over 4

=item _format_error

Format the error in the visionary state format.

Returns a formatted error message with context and hints.

=cut

sub _format_error {
    my ($self) = @_;
    
    my $message = $self->message;
    my $pos     = $self->pos;
    my $text    = $self->text;
    my $hint    = $self->hint;
    
    # Fallback to simple format if no text provided
    if (!$text) {
        return "$message at position $pos";
    }
    
    # Find the line containing the error
    my @lines = split /\n/, $text, -1;
    my $current_pos = 0;
    my $line_num = 1;
    my $line_text = '';
    my $col = $pos;
    
    for my $i (0 .. $#lines) {
        my $line = $lines[$i];
        my $line_len = length($line) + 1; # +1 for newline
        
        if ($current_pos + $line_len > $pos) {
            $line_num = $i + 1;
            $line_text = $line;
            $col = $pos - $current_pos;
            last;
        }
        $current_pos += $line_len;
    }
    
    # Error is beyond the last line
    if (!$line_text) {
        if (@lines) {
            $line_num = scalar(@lines);
            $line_text = $lines[-1];
            $col = length($line_text);
        } else {
            $line_text = $text;
            $col = $pos;
        }
    }
    
    # Build the formatted error message
    my @parts = ("STRling Parse Error: $message", "");
    push @parts, "> $line_num | $line_text";
    push @parts, ">   | " . (' ' x $col) . '^';
    
    if ($hint) {
        push @parts, "";
        push @parts, "Hint: $hint";
    }
    
    return join("\n", @parts);
}

=item to_formatted_string

Backwards/JS-friendly alias for getting the formatted error string.

Returns the formatted error message (same as stringification).

=cut

sub to_formatted_string {
    my ($self) = @_;
    return $self->_format_error();
}

=item to_lsp_diagnostic

Convert the error to LSP Diagnostic format.

Returns a hashref compatible with the Language Server Protocol
Diagnostic specification, which can be serialized to JSON for
communication with LSP clients.

Returns:

=over 4

=item * range: The line/column range where the error occurred

=item * severity: Error severity (1 = Error)

=item * message: The error message with hint if available

=item * source: "STRling"

=item * code: A normalized error code derived from the message

=back

=cut

sub to_lsp_diagnostic {
    my ($self) = @_;
    
    my $message = $self->message;
    my $pos     = $self->pos;
    my $text    = $self->text;
    my $hint    = $self->hint;
    
    # Find the line and column containing the error
    my @lines = $text ? split(/\n/, $text, -1) : ();
    my $current_pos = 0;
    my $line_num = 0; # 0-indexed for LSP
    my $col = $pos;
    
    for my $i (0 .. $#lines) {
        my $line = $lines[$i];
        my $line_len = length($line) + 1; # +1 for newline
        
        if ($current_pos + $line_len > $pos) {
            $line_num = $i;
            $col = $pos - $current_pos;
            last;
        }
        $current_pos += $line_len;
    }
    
    # Error is beyond the last line
    if (!@lines || $current_pos <= $pos) {
        if (@lines) {
            $line_num = $#lines;
            $col = length($lines[-1]);
        } else {
            $line_num = 0;
            $col = $pos;
        }
    }
    
    # Build the diagnostic message
    my $diagnostic_message = $message;
    if ($hint) {
        $diagnostic_message .= "\n\nHint: $hint";
    }
    
    # Create error code from message (normalize to snake_case)
    my $error_code = lc($message);
    $error_code =~ s/[\s'"()\[\]{}\\\/]/_/g;
    $error_code =~ s/_+/_/g;
    $error_code =~ s/^_|_$//g;
    
    return {
        range => {
            start => { line => $line_num, character => $col },
            end   => { line => $line_num, character => $col + 1 }
        },
        severity => 1, # 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
        message  => $diagnostic_message,
        source   => "STRling",
        code     => $error_code
    };
}

=back

=cut

1;
