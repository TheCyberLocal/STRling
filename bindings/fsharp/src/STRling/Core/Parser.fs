namespace STRling.Core

open System
open System.Text.RegularExpressions
open STRling

/// Recursive descent parser for the STRling DSL.
/// Parses pattern syntax into Abstract Syntax Tree (AST) nodes.
module Parser =

    /// Control escape character mappings.
    let private controlEscapes =
        dict [
            'n', "\n"
            'r', "\r"
            't', "\t"
            'f', "\f"
            'v', "\u000B"
        ]

    /// Internal cursor for tracking position within the input text.
    type private Cursor(text: string, startPos: int, extendedMode: bool, inClass: int) =
        let mutable i = startPos
        let mutable inClassCount = inClass

        member _.Text = text
        member _.I with get() = i and set(v) = i <- v
        member _.ExtendedMode = extendedMode
        member _.InClass with get() = inClassCount and set(v) = inClassCount <- v

        member _.Eof() = i >= text.Length

        member _.Peek(?n: int) =
            let offset = defaultArg n 0
            let j = i + offset
            if j >= text.Length then '\000' else text.[j]

        member this.Take() =
            if this.Eof() then '\000'
            else
                let ch = text.[i]
                i <- i + 1
                ch

        member this.Match(s: string) =
            if i + s.Length <= text.Length && text.Substring(i, s.Length) = s then
                i <- i + s.Length
                true
            else
                false

        member this.SkipWsAndComments() =
            if not extendedMode || inClassCount > 0 then ()
            else
                let mutable cont = true
                while cont && not (this.Eof()) do
                    let ch = this.Peek()
                    if " \t\r\n".Contains(ch) then
                        i <- i + 1
                    elif ch = '#' then
                        while not (this.Eof()) && not ("\r\n".Contains(this.Peek())) do
                            i <- i + 1
                    else
                        cont <- false

    /// Result of parsing directives from the input.
    type private DirectiveResult = {
        Flags: Flags
        Pattern: string
    }

    /// Parse directives (like %flags) from the pattern.
    let private parseDirectives (text: string) : DirectiveResult =
        let mutable flags = Flags.defaultFlags
        let lines = text.Split('\n')
        let patternLines = ResizeArray<string>()
        let mutable inPattern = false
        let mutable lineNum = 0

        for rawLine in lines do
            lineNum <- lineNum + 1
            let line = rawLine.TrimEnd('\r')
            let stripped = line.Trim()

            if not inPattern && (stripped = "" || stripped.StartsWith("#")) then
                ()
            elif stripped.StartsWith("%") then
                if inPattern then
                    let pos = lines |> Seq.take (lineNum - 1) |> Seq.sumBy (fun l -> l.Length + 1)
                    let hint = HintEngine.getHint "Directive after pattern" text pos
                    raise (STRlingParseError("Directive after pattern", pos + line.IndexOf("%"), text, ?hint = hint))

                if not (stripped.StartsWith("%flags")) then
                    let pos = lines |> Seq.take (lineNum - 1) |> Seq.sumBy (fun l -> l.Length + 1)
                    let hint = HintEngine.getHint "Malformed directive" text pos
                    raise (STRlingParseError("Malformed directive", pos + line.IndexOf("%"), text, ?hint = hint))

                let idx = line.IndexOf("%flags")
                let after = line.Substring(idx + "%flags".Length)
                let allowed = " ,\t[]imsuxIMSUX"

                let mutable j = 0
                while j < after.Length && allowed.Contains(after.[j]) do
                    j <- j + 1

                let flagsToken = after.Substring(0, j)
                let remainder = if j < after.Length then after.Substring(j) else ""

                let mutable letters = ""
                for ch in flagsToken do
                    if Char.IsLetter(ch) then
                        letters <- letters + string (Char.ToLower(ch))

                let validFlags = "imsux"
                for ch in letters do
                    if not (validFlags.Contains(ch)) then
                        let pos = lines |> Seq.take (lineNum - 1) |> Seq.sumBy (fun l -> l.Length + 1)
                        let hint = HintEngine.getHint (sprintf "Invalid flag '%c'" ch) text (pos + idx)
                        raise (STRlingParseError(sprintf "Invalid flag '%c'" ch, pos + idx, text, ?hint = hint))

                if letters.Length > 0 then
                    flags <- Flags.fromLetters letters
                else
                    let trimmed = remainder.TrimStart()
                    if trimmed.Length > 0 then
                        let ch = trimmed.[0]
                        let pos = lines |> Seq.take (lineNum - 1) |> Seq.sumBy (fun l -> l.Length + 1)
                        let hint = HintEngine.getHint (sprintf "Invalid flag '%c'" ch) text (pos + idx)
                        raise (STRlingParseError(sprintf "Invalid flag '%c'" ch, pos + idx, text, ?hint = hint))

                let remTrimmed = remainder.TrimStart()
                if remTrimmed.Length > 0 then
                    patternLines.Add(remainder)
                    inPattern <- true

            elif line.Contains("%flags") then
                let pos = lines |> Seq.take (lineNum - 1) |> Seq.sumBy (fun l -> l.Length + 1)
                let hint = HintEngine.getHint "Directive after pattern" text pos
                raise (STRlingParseError("Directive after pattern", pos + line.IndexOf("%flags"), text, ?hint = hint))
            else
                inPattern <- true
                patternLines.Add(line)

        { Flags = flags; Pattern = String.concat "\n" patternLines }

    /// Parse a STRling pattern string into flags and AST.
    let parse (text: string) : Flags * Node =
        let dirResult = parseDirectives text
        let src = dirResult.Pattern
        let flags = dirResult.Flags
        let cur = Cursor(src, 0, flags.Extended, 0)
        let mutable capCount = 0
        let capNames = System.Collections.Generic.HashSet<string>()

        let raiseError msg pos =
            let hint = HintEngine.getHint msg src pos
            raise (STRlingParseError(msg, pos, src, ?hint = hint))

        let isHexDigit (c: char) =
            (c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f')

        let rec parsePattern () =
            cur.SkipWsAndComments()
            if cur.Eof() then Seq []
            else
                let node = parseAlt()
                cur.SkipWsAndComments()
                if not (cur.Eof()) then
                    if cur.Peek() = ')' then
                        raiseError "Unmatched ')'" cur.I
                    raiseError "Unexpected trailing input" cur.I
                node

        and parseAlt () =
            cur.SkipWsAndComments()

            // Check for stray pipe at start
            if cur.Peek() = '|' then
                raiseError "Alternation lacks left-hand side" cur.I

            let branches = ResizeArray<Node>()
            branches.Add(parseSeq())

            while cur.Peek() = '|' do
                cur.Take() |> ignore
                cur.SkipWsAndComments()

                // Check for empty alternation
                if cur.Peek() = '|' || cur.Eof() || cur.Peek() = ')' then
                    raiseError "Empty alternation" cur.I

                branches.Add(parseSeq())

            if branches.Count = 1 then branches.[0]
            else Alt (List.ofSeq branches)

        and parseSeq () =
            let parts = ResizeArray<Node>()
            let mutable prevHadFailedQuant = false

            let mutable cont = true
            while cont && not (cur.Eof()) do
                cur.SkipWsAndComments()
                let ch = cur.Peek()

                if ch <> '\000' && "*+?{".Contains(ch) && parts.Count = 0 then
                    if ch = '{' then
                        // Check brace content
                        let mutable j = cur.I + 1
                        let mutable look = ""
                        while j < cur.Text.Length && cur.Text.[j] <> '}' do
                            look <- look + string cur.Text.[j]
                            j <- j + 1
                        if j < cur.Text.Length && look.Length > 0 then
                            if Regex.IsMatch(look, @"^\d+(,\d*)?$") then
                                raiseError (sprintf "Invalid quantifier '%c'" ch) cur.I
                            else
                                raiseError "Brace quantifier: Invalid brace quantifier content" cur.I
                        elif j >= cur.Text.Length then
                            raiseError "Incomplete quantifier" cur.I
                        else
                            raiseError (sprintf "Invalid quantifier '%c'" ch) cur.I
                    else
                        raiseError (sprintf "Invalid quantifier '%c'" ch) cur.I

                if ch = '|' || ch = ')' || ch = '\000' then
                    cont <- false
                else
                    let atom = parseAtom()
                    let (quantified, hadFailedQuant) = parseQuantIfAny atom

                    let mutable shouldCoalesce = false
                    match quantified, (if parts.Count > 0 then Some parts.[parts.Count - 1] else None) with
                    | Lit currentVal, Some (Lit lastVal) when not cur.ExtendedMode && not prevHadFailedQuant && not (currentVal.Contains("\n")) && not (lastVal.Contains("\n")) ->
                        shouldCoalesce <- true
                        parts.[parts.Count - 1] <- Lit (lastVal + currentVal)
                    | _ -> ()

                    if not shouldCoalesce then
                        parts.Add(quantified)

                    prevHadFailedQuant <- hadFailedQuant

            if parts.Count = 0 then Lit ""
            elif parts.Count = 1 then parts.[0]
            else Seq (List.ofSeq parts)

        and parseAtom () =
            cur.SkipWsAndComments()
            let ch = cur.Peek()

            match ch with
            | '^' ->
                cur.Take() |> ignore
                Anchor "Start"
            | '$' ->
                cur.Take() |> ignore
                Anchor "End"
            | '.' ->
                cur.Take() |> ignore
                Dot
            | '\\' ->
                parseEscapeAtom()
            | '(' ->
                parseGroupOrLook()
            | '[' ->
                parseCharClass()
            | ')' | ']' | '|' | '*' | '+' | '?' | '{' ->
                raiseError (sprintf "Unexpected token '%c'" ch) cur.I
                Lit ""
            | _ ->
                takeLiteralChar()

        and parseEscapeAtom () =
            let startPos = cur.I
            cur.Take() |> ignore // consume backslash

            if cur.Eof() then
                raiseError "Unexpected end of pattern after '\\'" startPos

            let ch = cur.Peek()

            // Anchors
            match ch with
            | 'b' -> cur.Take() |> ignore; Anchor "WordBoundary"
            | 'B' -> cur.Take() |> ignore; Anchor "NotWordBoundary"
            | 'A' -> cur.Take() |> ignore; Anchor "AbsoluteStart"
            | 'Z' -> cur.Take() |> ignore; Anchor "EndBeforeFinalNewline"

            // Shorthand classes
            | 'd' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "digit"])
            | 'D' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "not-digit"])
            | 'w' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "word"])
            | 'W' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "not-word"])
            | 's' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "whitespace"])
            | 'S' -> cur.Take() |> ignore; CharClass (false, [ClassEscape "not-whitespace"])

            // Control escapes
            | 'n' -> cur.Take() |> ignore; Lit controlEscapes.['n']
            | 'r' -> cur.Take() |> ignore; Lit controlEscapes.['r']
            | 't' -> cur.Take() |> ignore; Lit controlEscapes.['t']
            | 'f' -> cur.Take() |> ignore; Lit controlEscapes.['f']
            | 'v' -> cur.Take() |> ignore; Lit controlEscapes.['v']

            // Unicode property
            | 'p' | 'P' ->
                let neg = ch = 'P'
                cur.Take() |> ignore
                if cur.Peek() <> '{' then
                    raiseError "Expected { after \\p/\\P" startPos
                cur.Take() |> ignore // consume {
                let mutable prop = ""
                while not (cur.Eof()) && cur.Peek() <> '}' do
                    prop <- prop + string (cur.Take())
                if cur.Eof() then
                    raiseError "Unterminated \\p{...}" startPos
                cur.Take() |> ignore // consume }
                let mutable propName = None
                let mutable propValue = prop
                if prop.Contains("=") then
                    let parts = prop.Split([|'='|], 2)
                    propName <- Some parts.[0]
                    propValue <- parts.[1]
                CharClass (false, [ClassUnicodeProperty(propName, propValue, neg)])

            // Hex escape
            | 'x' ->
                cur.Take() |> ignore
                if cur.Peek() = '{' then
                    cur.Take() |> ignore
                    let mutable hex = ""
                    while not (cur.Eof()) && cur.Peek() <> '}' do
                        hex <- hex + string (cur.Take())
                    if cur.Eof() then
                        raiseError "Unterminated \\x{...}" startPos
                    cur.Take() |> ignore
                    let cp = Convert.ToInt32((if hex.Length > 0 then hex else "0"), 16)
                    Lit (Char.ConvertFromUtf32(cp))
                else
                    let mutable hex = ""
                    for _ in 0..1 do
                        let h = cur.Peek()
                        if not (isHexDigit h) then
                            raiseError "Invalid \\xHH escape" startPos
                        hex <- hex + string (cur.Take())
                    let cp = Convert.ToInt32(hex, 16)
                    Lit (string (char cp))

            // Unicode escape \u
            | 'u' ->
                cur.Take() |> ignore
                if cur.Peek() = '{' then
                    cur.Take() |> ignore
                    let mutable hex = ""
                    while not (cur.Eof()) && cur.Peek() <> '}' do
                        hex <- hex + string (cur.Take())
                    if cur.Eof() then
                        raiseError "Unterminated \\u{...}" startPos
                    cur.Take() |> ignore
                    let cp = Convert.ToInt32((if hex.Length > 0 then hex else "0"), 16)
                    Lit (Char.ConvertFromUtf32(cp))
                else
                    let mutable hex = ""
                    for _ in 0..3 do
                        let h = cur.Peek()
                        if not (isHexDigit h) then
                            raiseError "Invalid \\uHHHH escape" startPos
                        hex <- hex + string (cur.Take())
                    let cp = Convert.ToInt32(hex, 16)
                    Lit (Char.ConvertFromUtf32(cp))

            // Unicode escape \U (8 hex digits)
            | 'U' ->
                cur.Take() |> ignore
                let mutable hex = ""
                for _ in 0..7 do
                    let h = cur.Peek()
                    if not (isHexDigit h) then
                        raiseError "Invalid \\UHHHHHHHH escape" startPos
                    hex <- hex + string (cur.Take())
                let cp = Convert.ToInt32(hex, 16)
                Lit (Char.ConvertFromUtf32(cp))

            // Numeric backreference
            | c when c >= '1' && c <= '9' ->
                let mutable numStr = string (cur.Take())
                while cur.Peek() >= '0' && cur.Peek() <= '9' do
                    numStr <- numStr + string (cur.Take())
                let num = int numStr
                if num > capCount then
                    raiseError (sprintf "Backreference to undefined group \\%d" num) startPos
                Backref (Some num, None)

            // Forbidden octal
            | '0' ->
                raiseError "Forbidden octal escape" startPos
                Lit ""

            // Named backreference
            | 'k' ->
                cur.Take() |> ignore
                if cur.Peek() <> '<' then
                    raiseError "Expected '<' after \\k" startPos
                cur.Take() |> ignore // consume <
                let mutable name = ""
                while not (cur.Eof()) && cur.Peek() <> '>' do
                    name <- name + string (cur.Take())
                if cur.Eof() then
                    raiseError "Unterminated named backref" startPos
                cur.Take() |> ignore // consume >
                if not (capNames.Contains(name)) then
                    raiseError (sprintf "Backreference to undefined group <%s>" name) startPos
                Backref (None, Some name)

            // Meta escapes
            | c when "^$.*+?()[]{}|\\/".Contains(c) ->
                cur.Take() |> ignore
                Lit (string c)

            // Unknown escape - alphanumeric is error
            | c when Char.IsLetterOrDigit(c) ->
                raiseError (sprintf "Unknown escape sequence \\%c" c) startPos
                Lit ""

            | c ->
                cur.Take() |> ignore
                Lit (string c)

        and parseGroupOrLook () =
            let startPos = cur.I
            cur.Take() |> ignore
            cur.SkipWsAndComments()

            if cur.Peek() = '?' then
                cur.Take() |> ignore
                let next = cur.Peek()

                match next with
                | ':' ->
                    cur.Take() |> ignore
                    let body = parseAlt()
                    if cur.Peek() <> ')' then raiseError "Unterminated group" cur.I
                    cur.Take() |> ignore
                    Group (false, None, false, body)
                | '=' ->
                    cur.Take() |> ignore
                    let body = parseAlt()
                    if cur.Peek() <> ')' then raiseError "Unterminated lookahead" cur.I
                    cur.Take() |> ignore
                    Lookahead body
                | '!' ->
                    cur.Take() |> ignore
                    let body = parseAlt()
                    if cur.Peek() <> ')' then raiseError "Unterminated lookahead" cur.I
                    cur.Take() |> ignore
                    NegativeLookahead body
                | '<' ->
                    cur.Take() |> ignore
                    let afterAngle = cur.Peek()
                    if afterAngle = '=' then
                        cur.Take() |> ignore
                        let body = parseAlt()
                        if cur.Peek() <> ')' then raiseError "Unterminated lookbehind" cur.I
                        cur.Take() |> ignore
                        Lookbehind body
                    elif afterAngle = '!' then
                        cur.Take() |> ignore
                        let body = parseAlt()
                        if cur.Peek() <> ')' then raiseError "Unterminated lookbehind" cur.I
                        cur.Take() |> ignore
                        NegativeLookbehind body
                    else
                        // Named group
                        let mutable name = ""
                        while not (cur.Eof()) && cur.Peek() <> '>' do
                            name <- name + string (cur.Take())
                        if cur.Eof() then
                            raiseError "Unterminated group name" cur.I
                        cur.Take() |> ignore // consume >

                        // Validate group name
                        if name.Length = 0 || (not (Char.IsLetter(name.[0])) && name.[0] <> '_') then
                            raiseError (sprintf "Invalid group name '%s'" name) startPos
                        for k in 1..name.Length-1 do
                            if not (Char.IsLetterOrDigit(name.[k])) && name.[k] <> '_' then
                                raiseError (sprintf "Invalid group name '%s'" name) startPos

                        if capNames.Contains(name) then
                            raiseError (sprintf "Duplicate group name '%s'" name) startPos
                        capNames.Add(name) |> ignore
                        capCount <- capCount + 1

                        let body = parseAlt()
                        if cur.Peek() <> ')' then raiseError "Unterminated group" cur.I
                        cur.Take() |> ignore
                        Group (true, Some name, false, body)
                | '>' ->
                    cur.Take() |> ignore
                    let body = parseAlt()
                    if cur.Peek() <> ')' then raiseError "Unterminated atomic group" cur.I
                    cur.Take() |> ignore
                    Group (false, None, true, body)
                | _ ->
                    // Check for inline modifiers
                    let save = cur.I
                    let mutable scan = ""
                    let mutable sj = save
                    while sj < cur.Text.Length && "imsux".Contains(cur.Text.[sj]) do
                        scan <- scan + string cur.Text.[sj]
                        sj <- sj + 1
                    if scan.Length > 0 && sj < cur.Text.Length && cur.Text.[sj] = ')' then
                        raiseError (sprintf "Inline modifiers like (?%s...) are not supported" scan) startPos

                    raiseError (sprintf "Unknown group modifier: ?%c" next) (cur.I - 1)
                    Lit ""
            else
                // Capturing group
                capCount <- capCount + 1
                let body = parseAlt()
                if cur.Peek() <> ')' then raiseError "Unterminated group" cur.I
                cur.Take() |> ignore
                Group (true, None, false, body)

        and parseCharClass () =
            let startPos = cur.I
            cur.Take() |> ignore
            cur.InClass <- cur.InClass + 1

            let negated =
                if cur.Peek() = '^' then
                    cur.Take() |> ignore
                    true
                else
                    false

            // Empty class: [] or [^]
            if cur.Peek() = ']' then
                cur.InClass <- cur.InClass - 1
                raiseError "Unterminated character class" cur.I

            let items = ResizeArray<ClassItem>()

            while not (cur.Eof()) && cur.Peek() <> ']' do
                let item = parseClassItem()

                // Check for range
                if cur.Peek() = '-' && cur.Peek(1) <> ']' && not (cur.Eof()) then
                    match item with
                    | ClassLiteral fromCh ->
                        cur.Take() |> ignore // consume -
                        if cur.Eof() || cur.Peek() = ']' then
                            items.Add(item)
                            items.Add(ClassLiteral "-")
                        else
                            let toItem = parseClassItem()
                            match toItem with
                            | ClassLiteral toCh ->
                                if String.Compare(toCh, fromCh, StringComparison.Ordinal) < 0 then
                                    cur.InClass <- cur.InClass - 1
                                    raiseError "Invalid character range" startPos
                                items.Add(ClassRange(fromCh, toCh))
                            | _ ->
                                items.Add(item)
                                items.Add(ClassLiteral "-")
                                items.Add(toItem)
                    | _ ->
                        items.Add(item)
                else
                    items.Add(item)

            if cur.Eof() then
                cur.InClass <- cur.InClass - 1
                raiseError "Unterminated character class" cur.I

            cur.Take() |> ignore // consume ]
            cur.InClass <- cur.InClass - 1

            CharClass (negated, List.ofSeq items)

        and parseClassItem () =
            let ch = cur.Peek()

            if ch = '\\' then
                let startPos = cur.I
                cur.Take() |> ignore

                if cur.Eof() then
                    raiseError "Unexpected end of pattern after '\\'" startPos

                let escCh = cur.Peek()

                match escCh with
                | 'd' -> cur.Take() |> ignore; ClassEscape "digit"
                | 'D' -> cur.Take() |> ignore; ClassEscape "not-digit"
                | 'w' -> cur.Take() |> ignore; ClassEscape "word"
                | 'W' -> cur.Take() |> ignore; ClassEscape "not-word"
                | 's' -> cur.Take() |> ignore; ClassEscape "whitespace"
                | 'S' -> cur.Take() |> ignore; ClassEscape "not-whitespace"
                | 'n' -> cur.Take() |> ignore; ClassLiteral "\n"
                | 'r' -> cur.Take() |> ignore; ClassLiteral "\r"
                | 't' -> cur.Take() |> ignore; ClassLiteral "\t"
                | 'f' -> cur.Take() |> ignore; ClassLiteral "\f"
                | 'v' -> cur.Take() |> ignore; ClassLiteral "\u000B"

                // Unicode property
                | 'p' | 'P' ->
                    let neg = escCh = 'P'
                    cur.Take() |> ignore
                    if cur.Peek() <> '{' then
                        cur.InClass <- cur.InClass - 1
                        raiseError "Expected { after \\p/\\P" startPos
                    cur.Take() |> ignore
                    let mutable prop = ""
                    while not (cur.Eof()) && cur.Peek() <> '}' do
                        prop <- prop + string (cur.Take())
                    if cur.Eof() then
                        cur.InClass <- cur.InClass - 1
                        raiseError "Unterminated \\p{...}" startPos
                    cur.Take() |> ignore
                    let mutable propName = None
                    let mutable propValue = prop
                    if prop.Contains("=") then
                        let parts = prop.Split([|'='|], 2)
                        propName <- Some parts.[0]
                        propValue <- parts.[1]
                    ClassUnicodeProperty(propName, propValue, neg)

                // Hex escape
                | 'x' ->
                    cur.Take() |> ignore
                    if cur.Peek() = '{' then
                        cur.Take() |> ignore
                        let mutable hex = ""
                        while not (cur.Eof()) && cur.Peek() <> '}' do
                            hex <- hex + string (cur.Take())
                        if cur.Eof() then
                            cur.InClass <- cur.InClass - 1
                            raiseError "Unterminated \\x{...}" startPos
                        cur.Take() |> ignore
                        let cp = Convert.ToInt32((if hex.Length > 0 then hex else "0"), 16)
                        ClassLiteral (Char.ConvertFromUtf32(cp))
                    else
                        let mutable hex = ""
                        for _ in 0..1 do
                            let h = cur.Peek()
                            if not (isHexDigit h) then
                                cur.InClass <- cur.InClass - 1
                                raiseError "Invalid \\xHH escape" startPos
                            hex <- hex + string (cur.Take())
                        let cp = Convert.ToInt32(hex, 16)
                        ClassLiteral (string (char cp))

                // Unicode escape \u
                | 'u' ->
                    cur.Take() |> ignore
                    if cur.Peek() = '{' then
                        cur.Take() |> ignore
                        let mutable hex = ""
                        while not (cur.Eof()) && cur.Peek() <> '}' do
                            hex <- hex + string (cur.Take())
                        if cur.Eof() then
                            cur.InClass <- cur.InClass - 1
                            raiseError "Unterminated \\u{...}" startPos
                        cur.Take() |> ignore
                        let cp = Convert.ToInt32((if hex.Length > 0 then hex else "0"), 16)
                        ClassLiteral (Char.ConvertFromUtf32(cp))
                    else
                        let mutable hex = ""
                        for _ in 0..3 do
                            let h = cur.Peek()
                            if not (isHexDigit h) then
                                cur.InClass <- cur.InClass - 1
                                raiseError "Invalid \\uHHHH escape" startPos
                            hex <- hex + string (cur.Take())
                        let cp = Convert.ToInt32(hex, 16)
                        ClassLiteral (Char.ConvertFromUtf32(cp))

                // Forbidden octal
                | '0' ->
                    cur.InClass <- cur.InClass - 1
                    raiseError "Forbidden octal escape" startPos
                    ClassLiteral ""

                // Meta escapes in class
                | c when "^$.*+?()[]{}|\\/\\-".Contains(c) ->
                    cur.Take() |> ignore
                    ClassLiteral (string c)

                // Unknown escape
                | c when Char.IsLetterOrDigit(c) ->
                    cur.InClass <- cur.InClass - 1
                    raiseError (sprintf "Unknown escape sequence \\%c" c) startPos
                    ClassLiteral ""

                | c ->
                    cur.Take() |> ignore
                    ClassLiteral (string c)
            else
                cur.Take() |> ignore
                ClassLiteral (string ch)

        and parseQuantIfAny (child: Node) : Node * bool =
            cur.SkipWsAndComments()
            let ch = cur.Peek()

            match child with
            | Anchor _ when ch <> '\000' && "*+?{".Contains(ch) ->
                raiseError "Cannot quantify anchor" cur.I
                (child, false)
            | Anchor _ ->
                (child, false)
            | _ ->
                let mutable min = 0
                let mutable max = None
                let mutable greedy = true
                let mutable lazy_ = false
                let mutable possessive = false
                let mutable matched = true

                match ch with
                | '*' ->
                    cur.Take() |> ignore
                    min <- 0
                    max <- None
                | '+' ->
                    cur.Take() |> ignore
                    min <- 1
                    max <- None
                | '?' ->
                    cur.Take() |> ignore
                    min <- 0
                    max <- Some 1
                | '{' ->
                    let result = parseBraceQuant()
                    match result with
                    | Some (minVal, maxVal) ->
                        min <- minVal
                        max <- maxVal
                    | None ->
                        matched <- false
                | _ ->
                    matched <- false

                if not matched then
                    (child, false)
                else
                    if cur.Peek() = '?' then
                        cur.Take() |> ignore
                        greedy <- false
                        lazy_ <- true
                    elif cur.Peek() = '+' then
                        cur.Take() |> ignore
                        greedy <- false
                        possessive <- true

                    (Quant (child, min, max, greedy, lazy_, possessive), true)

        and parseBraceQuant () =
            let startPos = cur.I
            cur.Take() |> ignore // consume {

            // Read content until }
            let contentStart = cur.I
            let mutable content = ""
            while not (cur.Eof()) && cur.Peek() <> '}' do
                content <- content + string (cur.Take())

            if cur.Eof() then
                raiseError "Incomplete quantifier" startPos
                None
            else
                cur.Take() |> ignore // consume }

                if content.Length = 0 then
                    raiseError "Brace quantifier: Invalid brace quantifier content" startPos
                    None
                elif not (Regex.IsMatch(content, @"^\d+(,\d*)?$")) then
                    raiseError "Brace quantifier: Invalid brace quantifier content" startPos
                    None
                else
                    let commaIdx = content.IndexOf(',')
                    if commaIdx = -1 then
                        let v = int content
                        Some (v, Some v)
                    else
                        let minVal = int (content.Substring(0, commaIdx))
                        let maxVal =
                            if commaIdx + 1 < content.Length then Some (int (content.Substring(commaIdx + 1)))
                            else None

                        match maxVal with
                        | Some mv when mv < minVal ->
                            raiseError "Invalid quantifier range" startPos
                            None
                        | _ ->
                            Some (minVal, maxVal)

        and takeLiteralChar () =
            let ch = cur.Take()
            Lit (string ch)

        // Execute parsing
        let ast = parsePattern()
        (flags, ast)
