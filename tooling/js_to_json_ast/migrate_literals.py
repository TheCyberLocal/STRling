import os

fixtures_dir = "tooling/js_to_json_ast/fixtures"
os.makedirs(fixtures_dir, exist_ok=True)

patterns = {
    # Literals - Category A
    "plain_literal_letter.pattern": "a",
    "plain_literal_underscore.pattern": "_",
    "identity_escape_dot.pattern": "\\.",
    "identity_escape_paren.pattern": "\\(",
    "identity_escape_star.pattern": "\\*",
    "identity_escape_backslash.pattern": "\\\\",
    "control_escape_newline.pattern": "\\n",
    "control_escape_tab.pattern": "\\t",
    "control_escape_carriage_return.pattern": "\\r",
    "control_escape_form_feed.pattern": "\\f",
    "control_escape_vertical_tab.pattern": "\\v",
    "hex_escape_fixed.pattern": "\\x41",
    "hex_escape_fixed_case.pattern": "\\x4a",
    "hex_escape_brace.pattern": "\\x{41}",
    "hex_escape_brace_non_bmp.pattern": "\\x{1F600}",
    "unicode_escape_fixed.pattern": "\\u0041",
    "unicode_escape_brace_bmp.pattern": "\\u{41}",
    "unicode_escape_brace_non_bmp.pattern": "\\u{1f600}",
    "unicode_escape_fixed_supplementary.pattern": "\\U0001F600",
    "null_byte_escape.pattern": "\\0",
    # Literals - Category B
    "unterminated_hex_brace.pattern": '%expect_error "Unterminated \\x{...}"\n\\x{12',
    "invalid_hex_char_short.pattern": '%expect_error "Invalid \\xHH escape"\n\\xG',
    "unterminated_unicode_brace.pattern": '%expect_error "Unterminated \\u{...}"\n\\u{1F60',
    "incomplete_unicode_fixed.pattern": '%expect_error "Invalid \\uHHHH escape"\n\\u123',
    "incomplete_unicode_supplementary.pattern": '%expect_error "Invalid \\UHHHHHHHH escape"\n\\U1234567',
    "stray_closing_paren.pattern": "%expect_error \"Unmatched ')'\"\n)",
    "stray_pipe.pattern": '%expect_error "Alternation lacks left-hand side"\n|',
    "forbidden_octal_escape.pattern": '%expect_error "Backreference to undefined group"\n\\123',
    # Literals - Category C
    "max_unicode_value.pattern": "\\u{10FFFF}",
    "zero_value_hex_brace.pattern": "\\x{0}",
    "empty_hex_brace.pattern": "\\x{}",
    "escaped_null_byte.pattern": "\\\\0",
    # Literals - Category D
    "free_spacing_literals.pattern": "%flags x\n a b #comment\n c",
    "free_spacing_escaped_space.pattern": "%flags x\n a \\\\ b ",
    # Literals - Category E
    "sequence_plain_literals.pattern": "abc",
    "sequence_escaped_metachars.pattern": "a\\*b\\+c",
    "sequence_only_escapes.pattern": "\\n\\t\\r",
    "sequence_mixed_escapes.pattern": "\\x41\\u0042\\n",
    # Literals - Category F
    "literal_after_control.pattern": "\\na",
    "literal_after_hex.pattern": "\\x41b",
    "escape_after_escape.pattern": "\\n\\t",
    "identity_escape_after_literal.pattern": "a\\*",
    # Literals - Category G
    "double_backslash.pattern": "\\\\",
    "quadruple_backslash.pattern": "\\\\\\\\",
    "backslash_before_literal.pattern": "\\\\a",
    # Literals - Category H
    "hex_escape_min.pattern": "\\x00",
    "hex_escape_max.pattern": "\\xFF",
    "unicode_escape_bmp_boundary.pattern": "\\uFFFF",
    "unicode_escape_supplementary.pattern": "\\U00010000",
    # Literals - Category I
    "backref_single_digit_error.pattern": '%expect_error "Backreference to undefined group"\n\\1',
    "backref_two_digit_group.pattern": "(a)\\12",
    "backref_three_digit_error.pattern": '%expect_error "Backreference to undefined group"\n\\123',
    # Literals - Category J
    "literal_between_quantifiers.pattern": "a*Xb+",
    "literal_in_alternation.pattern": "a|b|c",
    "escaped_literal_in_group.pattern": "(\\*)",
    # Flags - Category A
    "single_flag.pattern": "%flags i",
    "multiple_flags_with_commas.pattern": "%flags i, m, x",
    "multiple_flags_with_spaces.pattern": "%flags u m s",
    "multiple_flags_mixed_separators.pattern": "%flags i,m s,u x",
    "leading_trailing_whitespace.pattern": "  %flags i  ",
    "whitespace_is_ignored.pattern": "%flags x\na b c",
    "comments_are_ignored.pattern": "%flags x\na # comment\n b",
    "escaped_whitespace_is_literal.pattern": "%flags x\na\\\\ b",
    # Flags - Category B
    "unknown_flag.pattern": "%expect_error \"Invalid flag 'z'\"\n%flags z",
    "malformed_directive.pattern": '%expect_error "Malformed directive"\n%flagg i',
    # Flags - Category C
    "empty_flags_directive.pattern": "%flags",
    "directive_after_content.pattern": '%expect_error "Directive after pattern"\na\n%flags i',
    "pattern_only_comments.pattern": "%flags x\n# comment\n  \n# another",
    # Flags - Category D
    "whitespace_is_literal_in_class.pattern": "%flags x\n[a b]",
    "comment_char_is_literal_in_class.pattern": "%flags x\n[a#b]",
}

for filename, content in patterns.items():
    filepath = os.path.join(fixtures_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created {filepath}")
