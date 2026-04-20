package STRling::Core::HintEngine;

# ABSTRACT: STRling Hint Engine - Context-Aware Error Hints

=head1 NAME

STRling::Core::HintEngine - Context-Aware Error Hints

=head1 DESCRIPTION

This module provides intelligent, beginner-friendly hints for common syntax errors.
The hint engine maps specific error types and contexts to instructional messages
that help users understand and fix their mistakes.

=cut

use strict;
use warnings;
use utf8;

our $VERSION = '3.0.0';

use Exporter 'import';
our @EXPORT_OK = qw(get_hint);

# Global hint engine mapping (error pattern => hint generator sub)
# NOTE: More specific patterns must come before more general ones
my %HINT_GENERATORS = (
    'Invalid brace quantifier content' => \&_hint_invalid_brace_quant_content,
    'Empty character class' => \&_hint_empty_character_class,
    'Unterminated group' => \&_hint_unterminated_group,
    'Unterminated character class' => \&_hint_unterminated_char_class,
    'Unterminated named backref' => \&_hint_unterminated_named_backref,
    'Unterminated group name' => \&_hint_unterminated_group_name,
    'Unterminated lookahead' => \&_hint_unterminated_lookahead,
    'Unterminated lookbehind' => \&_hint_unterminated_lookbehind,
    'Unterminated atomic group' => \&_hint_unterminated_atomic_group,
    'Unterminated {m,n}' => \&_hint_unterminated_brace_quant,
    'Unterminated {n}' => \&_hint_unterminated_brace_quant,
    'Invalid quantifier range' => \&_hint_invalid_quantifier_range,  # More specific, comes first
    'Invalid quantifier' => \&_hint_invalid_quantifier,  # More general, comes second
    'Invalid character range' => \&_hint_invalid_character_range,
    'Invalid flag' => \&_hint_invalid_flag,
    'Directive after pattern' => \&_hint_directive_after_pattern,
    'Unknown escape sequence' => \&_hint_unknown_escape,
    'Unexpected token' => \&_hint_unexpected_token,
    'Unexpected trailing input' => \&_hint_unexpected_trailing,
    'Cannot quantify anchor' => \&_hint_cannot_quantify_anchor,
    'Backreference to undefined group' => \&_hint_undefined_backref,
    'Duplicate group name' => \&_hint_duplicate_group_name,
    'Invalid group name' => \&_hint_invalid_group_name,
    'Empty alternation' => \&_hint_empty_alternation,
    'Alternation lacks left-hand side' => \&_hint_alternation_no_lhs,
    'Alternation lacks right-hand side' => \&_hint_alternation_no_rhs,
    'Expected \'<\' after \\k' => \&_hint_incomplete_named_backref,
    'Inline modifiers' => \&_hint_inline_modifiers,
    'Invalid \\xHH escape' => \&_hint_invalid_hex,
    'Invalid \\uHHHH' => \&_hint_invalid_unicode,
    'Unterminated \\x{...}' => \&_hint_unterminated_hex_brace,
    'Unterminated \\u{...}' => \&_hint_unterminated_unicode_brace,
    'Unterminated \\p{...}' => \&_hint_unterminated_unicode_property,
    'Expected { after \\p/\\P' => \&_hint_unicode_property_missing_brace,
    'Malformed directive' => \&_hint_malformed_directive,
    'Incomplete quantifier' => \&_hint_incomplete_quantifier,
    'Invalid \\UHHHHHHHH escape' => \&_hint_invalid_unicode_long,
    'Unmatched \')\'' => \&_hint_unmatched_close_paren,
);

=head1 FUNCTIONS

=head2 get_hint

Get a hint for the given error.

This is a convenience function that uses the global hint engine mapping.

Parameters:
    $error_message - The error message from the parser
    $text - The full input text being parsed
    $pos - The position where the error occurred

Returns:
    A helpful hint string, or undef if no hint is available

=cut

sub get_hint {
    my ($error_message, $text, $pos) = @_;
    
    # Try to match error message to a hint generator
    # Sort by length descending so more specific patterns match first
    for my $pattern (sort { length($b) <=> length($a) } keys %HINT_GENERATORS) {
        if (index($error_message, $pattern) >= 0) {
            my $generator = $HINT_GENERATORS{$pattern};
            return $generator->($error_message, $text, $pos);
        }
    }
    
    # No specific hint available
    return undef;
}

# Hint generators for specific error types

sub _hint_unterminated_group {
    return "This group was opened with '(' but never closed. " .
           "Add a matching ')' to close the group.";
}

sub _hint_unterminated_char_class {
    return "This character class was opened with '[' but never closed. " .
           "Add a matching ']' to close the character class.";
}

sub _hint_unterminated_named_backref {
    return "Named backreferences use the syntax \\k<name>. " .
           "Make sure to close the '<name>' with '>'.";
}

sub _hint_unterminated_group_name {
    return "Named groups use the syntax (?<name>...). " .
           "Make sure to close the '<name>' with '>' before the group content.";
}

sub _hint_unterminated_lookahead {
    return "This lookahead was opened with '(?=' or '(?!' but never closed. " .
           "Add a matching ')' to close the lookahead.";
}

sub _hint_unterminated_lookbehind {
    return "This lookbehind was opened with '(?<=' or '(?<!' but never closed. " .
           "Add a matching ')' to close the lookbehind.";
}

sub _hint_unterminated_atomic_group {
    return "This atomic group was opened with '(?>' but never closed. " .
           "Add a matching ')' to close the atomic group.";
}

sub _hint_unterminated_brace_quant {
    return "Brace quantifiers use the syntax {m,n} or {n}. " .
           "Make sure to close the quantifier with '}'.";
}

sub _hint_invalid_brace_quant_content {
    return "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. " .
           "Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.";
}

sub _hint_empty_character_class {
    return "Empty character class '[]' detected. " .
           "Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. " .
           "If you meant a literal '[', escape it with '\\['.";
}

sub _hint_invalid_quantifier_range {
    return "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). " .
           "For example, use '{2,5}' or '{2,2}', not '{5,2}'.";
}

sub _hint_invalid_quantifier {
    my ($msg, $text, $pos) = @_;
    my $quant = '*';
    if ($msg =~ /'([*+?{])'/) {
        $quant = $1;
    }
    return "The quantifier '$quant' must follow an atom (a character or group). " .
           "Place '$quant' after the thing it should quantify, e.g., 'a$quant'.";
}

sub _hint_invalid_character_range {
    return "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. " .
           "Reversed ranges like '[z-a]' are invalid.";
}

sub _hint_invalid_flag {
    return "Unknown flag. Valid flags are: " .
           "i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";
}

sub _hint_directive_after_pattern {
    return "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). " .
           "Move the directive to the top of the input on its own line.";
}

sub _hint_unknown_escape {
    my ($msg, $text, $pos) = @_;
    if ($msg =~ /\\(.)/) {
        my $ch = $1;
        if ($ch eq 'z') {
            return "'\\z' is not a recognized escape sequence. " .
                   "Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
        }
        return "Unknown escape sequence '\\$ch'. If you intended a literal '$ch', " .
               "remove the backslash or use a recognized escape.";
    }
    return "This is not a recognized escape sequence.";
}

sub _hint_unexpected_token {
    my ($msg, $text, $pos) = @_;
    # Try to identify the unexpected character
    if ($pos < length($text)) {
        my $char = substr($text, $pos, 1);
        if ($char eq ')') {
            return "This ')' character does not have a matching opening '('. " .
                   "Did you mean to escape it with '\\)'?";
        } elsif ($char eq '|') {
            return "The alternation operator '|' requires expressions on both sides. " .
                   "Use 'a|b' to match either 'a' or 'b'.";
        }
    }
    return "This character appeared in an unexpected context.";
}

sub _hint_unexpected_trailing {
    return "There is unexpected content after the pattern ended. " .
           "Check for unmatched parentheses or extra characters.";
}

sub _hint_cannot_quantify_anchor {
    return "Anchors like ^, \$, \\b, \\B match positions, not characters, " .
           "so they cannot be quantified with *, +, ?, or {}.";
}

sub _hint_undefined_backref {
    return "Backreferences refer to previously captured groups. " .
           "Make sure the group is defined before referencing it. " .
           "STRling does not support forward references.";
}

sub _hint_duplicate_group_name {
    return "Each named group must have a unique name. " .
           "Use different names for different groups, or use unnamed groups ().";
}

sub _hint_invalid_group_name {
    return "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. " .
           "Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";
}

sub _hint_empty_alternation {
    return "One of the alternation branches is empty. Remove the empty branch or provide an expression, " .
           "e.g., 'a|b' instead of 'a||b'.";
}

sub _hint_alternation_no_lhs {
    return "The alternation operator '|' requires an expression on the left side. " .
           "Use 'a|b' to match either 'a' or 'b'.";
}

sub _hint_alternation_no_rhs {
    return "The alternation operator '|' requires an expression on the right side. " .
           "Use 'a|b' to match either 'a' or 'b'.";
}

sub _hint_incomplete_named_backref {
    return "Named backreferences use the syntax \\k<name>. " .
           "Make sure to close the '<name>' with '>'.";
}

sub _hint_inline_modifiers {
    return "STRling does not support inline modifiers like (?i) for case-insensitivity. " .
           "Instead, use the %flags directive at the start of your pattern: '%flags i'";
}

sub _hint_invalid_hex {
    return "Hex escapes must use valid hexadecimal digits (0-9, A-F). " .
           "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";
}

sub _hint_invalid_unicode {
    return "Unicode escapes must use valid hexadecimal digits (0-9, A-F). " .
           "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.";
}

sub _hint_unterminated_hex_brace {
    return "Variable-length hex escapes use the syntax \\x{...}. " .
           "Make sure to close the escape with '}'.";
}

sub _hint_unterminated_unicode_brace {
    return "Variable-length unicode escapes use the syntax \\u{...}. " .
           "Make sure to close the escape with '}'.";
}

sub _hint_unterminated_unicode_property {
    return "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. " .
           "Make sure to close the property name with '}'.";
}

sub _hint_unicode_property_missing_brace {
    return "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. " .
           "Use \\p{L} for letters, \\p{N} for numbers, etc.";
}

sub _hint_malformed_directive {
    return "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, " .
           "for example '%flags i' on a line by itself.";
}

sub _hint_incomplete_quantifier {
    return "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. " .
           "Make sure to close the quantifier with '}' and provide valid numbers.";
}

sub _hint_invalid_unicode_long {
    return "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). " .
           "Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.";
}

sub _hint_unmatched_close_paren {
    return "This ')' does not have a matching opening '('. " .
           "Remove the extra ')' or add an opening '(' earlier in the pattern.";
}

=head1 SEE ALSO

L<STRling::Core::Errors>

=cut

1;
