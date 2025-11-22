const { parse } = require("./bindings/javascript/dist/STRling/core/parser");

const cases = [
    { name: "unknown_flag", input: "%flags z" },
    { name: "malformed_directive", input: "%flagg i" },
    { name: "directive_after_content", input: "a\n%flags i" },
    { name: "unterminated_hex_brace", input: "\\x{12" },
    { name: "invalid_hex_char_short", input: "\\xG" },
    { name: "unterminated_unicode_brace", input: "\\u{1F60" },
    { name: "incomplete_unicode_fixed", input: "\\u123" },
    { name: "incomplete_unicode_supplementary", input: "\\U1234567" },
    { name: "stray_closing_paren", input: ")" },
    { name: "stray_pipe", input: "|" },
    { name: "forbidden_octal_escape", input: "\\123" },
    { name: "backref_single_digit_error", input: "\\1" },
];

cases.forEach(({ name, input }) => {
    try {
        parse(input);
        console.log(`${name}: No error`);
    } catch (e) {
        console.log(`${name}: ${e.message}`);
    }
});
