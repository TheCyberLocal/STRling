namespace STRling.Core

open System

/// STRling Parse Error with position tracking and instructional hints.
/// This error class transforms parse failures into learning opportunities.
type STRlingParseError(message: string, pos: int, text: string, ?hint: string) =
    inherit Exception(STRlingParseError.FormatError(message, pos, text, hint))
    
    /// The error message.
    member _.ErrorMessage = message
    
    /// The character position (0-indexed) where the error occurred.
    member _.Pos = pos
    
    /// The full input text being parsed.
    member _.Text = text
    
    /// An instructional hint explaining how to fix the error.
    member _.Hint = hint
    
    static member private FormatError(message: string, pos: int, text: string, hint: string option) =
        if String.IsNullOrEmpty(text) then
            sprintf "%s at position %d" message pos
        else
            // Find the line containing the error
            let lines = text.Split('\n')
            let mutable currentPos = 0
            let mutable lineNum = 1
            let mutable lineText = ""
            let mutable col = pos
            
            for i = 0 to lines.Length - 1 do
                let line = lines.[i]
                let lineLen = line.Length + 1 // +1 for newline
                if currentPos + lineLen > pos && lineText = "" then
                    lineNum <- i + 1
                    lineText <- line.TrimEnd('\r')
                    col <- pos - currentPos
                currentPos <- currentPos + lineLen
            
            // Error is beyond the last line
            if lineText = "" && lines.Length > 0 then
                lineNum <- lines.Length
                lineText <- lines.[lines.Length - 1]
                col <- lineText.Length
            elif lineText = "" then
                lineText <- text
                col <- pos
            
            // Build the formatted error message
            let parts = ResizeArray<string>()
            parts.Add(sprintf "STRling Parse Error: %s" message)
            parts.Add("")
            parts.Add(sprintf "> %d | %s" lineNum lineText)
            parts.Add(sprintf ">   | %s^" (String.replicate col " "))
            
            match hint with
            | Some h ->
                parts.Add("")
                parts.Add(sprintf "Hint: %s" h)
            | None -> ()
            
            String.concat "\n" parts

/// Hint Engine for generating instructional error hints.
module HintEngine =
    open System.Text.RegularExpressions

    /// Generic fallback hint used when no specific hint pattern matches.
    [<Literal>]
    let GenericHintFallback = "Check the STRling documentation for help with this syntax."

    /// Static hint mappings (pattern -> hint string).
    let private staticHints = [
        ("Unterminated group", "This group was opened with '(' but never closed. Add a matching ')' to close the group.")
        ("Empty character class", "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) \u2014 do not leave them empty. If you meant a literal '[', escape it with '\\['.")
        ("Unterminated character class", "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.")
        ("Unterminated named backref", "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.")
        ("Unterminated group name", "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.")
        ("Unterminated lookahead", "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.")
        ("Unterminated lookbehind", "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.")
        ("Unterminated atomic group", "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.")
        ("Unterminated {m,n}", "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.")
        ("Unterminated {n}", "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.")
        ("Unexpected trailing input", "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.")
        ("Cannot quantify anchor", "Anchors like ^, $, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.")
        ("Backreference to undefined group", "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.")
        ("Duplicate group name", "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().")
        ("Alternation lacks left-hand side", "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.")
        ("Alternation lacks right-hand side", "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.")
        ("Inline modifiers", "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'")
        ("Invalid \\xHH escape", "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').")
        ("Invalid \\uHHHH", "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.")
        ("Unterminated \\x{...}", "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.")
        ("Unterminated \\u{...}", "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.")
        ("Unterminated \\p{...}", "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.")
        ("Expected { after \\p/\\P", "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc.")
        ("Invalid brace quantifier content", "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces \u2014 to match a literal '{', escape it with '\\{'.")
        ("Invalid group name", "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.")
        ("Invalid quantifier range", "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.")
        ("Invalid character range", "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.")
        ("Invalid flag", "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).")
        ("Directive after pattern", "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.")
        ("Malformed directive", "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.")
        ("Empty alternation", "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.")
        ("Expected '<' after \\k", "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.")
        ("Incomplete quantifier", "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.")
        ("Invalid \\UHHHHHHHH escape", "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.")
        ("Unmatched ')'", "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.")
    ]

    /// Dynamic hint for "Unexpected token" errors.
    let private hintUnexpectedToken (msg: string) (source: string) (pos: int) =
        if pos < source.Length then
            let ch = source.[pos]
            if ch = ')' then
                "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern. '\\)'?"
            elif ch = '|' then
                "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'."
            else
                "This character appeared in an unexpected context."
        else
            "This character appeared in an unexpected context."

    /// Dynamic hint for "Unknown escape sequence" errors.
    let private hintUnknownEscape (msg: string) (source: string) (pos: int) =
        let m = Regex.Match(msg, @"Unknown escape sequence \\?(.)")
        if m.Success then
            let ch = m.Groups.[1].Value
            if ch = "z" then
                "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?"
            else
                sprintf "Unknown escape sequence '\\%s'. If you intended a literal '%s', remove the backslash or use a recognized escape." ch ch
        else
            "This is not a recognized escape sequence."

    /// Dynamic hint for "Invalid quantifier" errors.
    let private hintInvalidQuantifier (msg: string) (source: string) (pos: int) =
        let m = Regex.Match(msg, @"Invalid quantifier '(.)'")
        let ch = if m.Success then m.Groups.[1].Value else "*"
        sprintf "The quantifier '%s' must follow an atom (a character or group). Place '%s' after the thing it should quantify, e.g., 'a%s'." ch ch ch

    /// Generate a helpful hint based on the error message and context.
    let getHint (message: string) (source: string) (pos: int) : string option =
        // Check static hints (substring match)
        let staticMatch =
            staticHints
            |> List.tryFind (fun (pattern, _) -> message.Contains(pattern))
        match staticMatch with
        | Some (_, hint) -> Some hint
        | None ->
            // Check dynamic generators
            if message.Contains("Unexpected token") then
                Some (hintUnexpectedToken message source pos)
            elif message.Contains("Unknown escape sequence") then
                Some (hintUnknownEscape message source pos)
            elif message.Contains("Invalid quantifier") then
                Some (hintInvalidQuantifier message source pos)
            else
                None

    /// Get a hint, falling back to the generic hint if none matches.
    let getHintOrFallback (message: string) (source: string) (pos: int) : string =
        match getHint message source pos with
        | Some hint -> hint
        | None -> GenericHintFallback
