-- STRling Hint Engine - Context-Aware Error Hints
--
-- This module provides intelligent, beginner-friendly hints for common syntax errors.
-- The hint engine maps specific error types and contexts to instructional messages
-- that help users understand and fix their mistakes.

local HintEngine = {}

--- Generic fallback hint used when no specific hint pattern matches.
HintEngine.GENERIC_HINT_FALLBACK = "Check the STRling documentation for help with this syntax."

-- Static hint strings (no dynamic generation needed)
local STATIC_HINTS = {
    ["Unterminated group"] = "This group was opened with '(' but never closed. Add a matching ')' to close the group.",
    ["Empty character class"] = "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['.",
    ["Unterminated character class"] = "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.",
    ["Unterminated named backref"] = "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.",
    ["Unterminated group name"] = "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.",
    ["Unterminated lookahead"] = "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.",
    ["Unterminated lookbehind"] = "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.",
    ["Unterminated atomic group"] = "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.",
    ["Unterminated {m,n}"] = "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.",
    ["Unterminated {n}"] = "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.",
    ["Unexpected trailing input"] = "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.",
    ["Cannot quantify anchor"] = "Anchors like ^, $, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.",
    ["Backreference to undefined group"] = "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.",
    ["Duplicate group name"] = "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().",
    ["Alternation lacks left-hand side"] = "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.",
    ["Alternation lacks right-hand side"] = "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.",
    ["Inline modifiers"] = "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'",
    ["Invalid \\xHH escape"] = "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').",
    ["Invalid \\uHHHH"] = "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.",
    ["Unterminated \\x{...}"] = "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.",
    ["Unterminated \\u{...}"] = "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.",
    ["Unterminated \\p{...}"] = "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.",
    ["Expected { after \\p/\\P"] = "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc.",
    ["Invalid brace quantifier content"] = "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.",
    ["Invalid group name"] = "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.",
    ["Invalid quantifier range"] = "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.",
    ["Invalid character range"] = "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.",
    ["Invalid flag"] = "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).",
    ["Directive after pattern"] = "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.",
    ["Malformed directive"] = "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.",
    ["Empty alternation"] = "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.",
    ["Expected '<' after \\k"] = "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.",
    ["Incomplete quantifier"] = "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.",
    ["Invalid \\UHHHHHHHH escape"] = "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.",
    ["Unmatched ')'"] = "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.",
}

-- Dynamic hint generators for patterns that need context
local function hint_unexpected_token(msg, text, pos)
    if pos and text and pos <= #text then
        local char = text:sub(pos, pos)
        if char == ")" then
            return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern. '\\)'?"
        elseif char == "|" then
            return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'."
        end
    end
    return "This character appeared in an unexpected context."
end

local function hint_unknown_escape(msg, text, pos)
    local ch = msg:match("Unknown escape sequence \\?(.)")
    if ch then
        if ch == "z" then
            return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?"
        end
        return "Unknown escape sequence '\\" .. ch .. "'. If you intended a literal '" .. ch .. "', remove the backslash or use a recognized escape."
    end
    return "This is not a recognized escape sequence."
end

local function hint_invalid_quantifier(msg, text, pos)
    local ch = msg:match("Invalid quantifier '(.)'")
    if not ch then ch = "*" end
    return "The quantifier '" .. ch .. "' must follow an atom (a character or group). Place '" .. ch .. "' after the thing it should quantify, e.g., 'a" .. ch .. "'."
end

-- Ordered patterns for matching (more specific first)
local DYNAMIC_PATTERNS = {
    { pattern = "Unexpected token", generator = hint_unexpected_token },
    { pattern = "Unknown escape sequence", generator = hint_unknown_escape },
    { pattern = "Invalid quantifier", generator = hint_invalid_quantifier },
}

--- Get a hint for the given error.
-- @param error_message string The error message from the parser
-- @param text string The full input text being parsed
-- @param pos number The position where the error occurred
-- @return string|nil A helpful hint, or nil if no hint is available
function HintEngine.get_hint(error_message, text, pos)
    if not error_message then return nil end

    -- Check static hints first (exact substring match)
    for pattern, hint in pairs(STATIC_HINTS) do
        if error_message:find(pattern, 1, true) then
            return hint
        end
    end

    -- Check dynamic generators
    for _, entry in ipairs(DYNAMIC_PATTERNS) do
        if error_message:find(entry.pattern, 1, true) then
            return entry.generator(error_message, text, pos)
        end
    end

    return nil
end

--- Get a hint, falling back to the generic hint if none matches.
-- @param error_message string The error message from the parser
-- @param text string The full input text being parsed
-- @param pos number The position where the error occurred
-- @return string A helpful hint (never nil)
function HintEngine.get_hint_or_fallback(error_message, text, pos)
    return HintEngine.get_hint(error_message, text, pos) or HintEngine.GENERIC_HINT_FALLBACK
end

return HintEngine
