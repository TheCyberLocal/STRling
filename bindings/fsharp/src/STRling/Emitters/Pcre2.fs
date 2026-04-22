namespace STRling.Emitters

open System
open System.Text
open STRling
open STRling.Core

/// PCRE2 Emitter - IR to PCRE2 Pattern String
/// This module implements the emitter that transforms STRling's Intermediate
/// Representation (IR) into PCRE2-compatible regex pattern strings.
module Pcre2 =
    
    /// Characters that need escaping in PCRE2 patterns.
    let private metaChars = set ['.'; '^'; '$'; '|'; '('; ')'; '?'; '*'; '+'; '{'; '}'; '['; ']'; '\\']
    
    /// Escape PCRE2 metacharacters in literal strings.
    let escapeLiteral (s: string) : string =
        let sb = StringBuilder()
        for i = 0 to s.Length - 1 do
            let ch = s.[i]
            if metaChars.Contains(ch) then
                sb.Append('\\').Append(ch) |> ignore
            else
                sb.Append(ch) |> ignore
        sb.ToString()
    
    /// Escape a character for use inside [...] per PCRE2 rules.
    let escapeClassChar (ch: char) : string =
        match ch with
        | '\\' -> "\\\\"
        | ']' -> "\\]"
        | '[' -> "\\["
        | '-' -> "\\-"
        | '^' -> "\\^"
        | '\n' -> "\\n"
        | '\r' -> "\\r"
        | '\t' -> "\\t"
        | '\f' -> "\\f"
        | '\u000B' -> "\\v"
        | c when int c < 32 || (int c >= 127 && int c <= 159) ->
            sprintf "\\x%02x" (int c)
        | c -> string c
    
    /// Emit a PCRE2 character class.
    let private emitClass (negated: bool) (items: IRClassItem list) : string =
        match items with
        | [IRClassEscape (k, prop)] ->
            match k, negated, prop with
            | "d", true, _ -> "\\D"
            | "w", true, _ -> "\\W"
            | "s", true, _ -> "\\S"
            | "d", false, _ -> "\\d"
            | "w", false, _ -> "\\w"
            | "s", false, _ -> "\\s"
            | "D", true, _ -> "\\d"
            | "W", true, _ -> "\\w"
            | "S", true, _ -> "\\s"
            | "D", false, _ -> "\\D"
            | "W", false, _ -> "\\W"
            | "S", false, _ -> "\\S"
            | ("p" | "P"), _, Some propVal ->
                let isUpperP = (k = "P")
                let useUpperP = negated <> isUpperP
                let useK = if useUpperP then "P" else "p"
                sprintf "\\%s{%s}" useK propVal
            | _ ->
                "[" + (if negated then "^" else "") + "\\" + k + "]"
        | _ ->
            let parts = StringBuilder()
            for item in items do
                match item with
                | IRClassLiteral c ->
                    parts.Append(escapeClassChar (c.[0])) |> ignore
                | IRClassRange (f, t) ->
                    parts.Append(escapeClassChar (f.[0])).Append('-').Append(escapeClassChar (t.[0])) |> ignore
                | IRClassEscape (typ, propOpt) ->
                    match typ, propOpt with
                    | "d", _ -> parts.Append("\\d") |> ignore
                    | "D", _ -> parts.Append("\\D") |> ignore
                    | "w", _ -> parts.Append("\\w") |> ignore
                    | "W", _ -> parts.Append("\\W") |> ignore
                    | "s", _ -> parts.Append("\\s") |> ignore
                    | "S", _ -> parts.Append("\\S") |> ignore
                    | ("p" | "P"), Some prop ->
                        parts.Append('\\').Append(typ).Append('{').Append(prop).Append('}') |> ignore
                    | _, _ ->
                        parts.Append('\\').Append(typ) |> ignore
            "[" + (if negated then "^" else "") + parts.ToString() + "]"
    
    /// Emit *, +, ?, {m}, {m,}, {m,n} plus optional lazy/possessive suffix.
    let private emitQuantSuffix (minv: int) (maxv: string) (mode: string) : string =
        let q =
            match minv, maxv with
            | 0, "Inf" -> "*"
            | 1, "Inf" -> "+"
            | 0, "1" -> "?"
            | n, m when m <> "Inf" && string n = m -> sprintf "{%d}" n
            | n, "Inf" -> sprintf "{%d,}" n
            | n, m -> sprintf "{%d,%s}" n m
        match mode with
        | "Lazy" -> q + "?"
        | "Possessive" -> q + "+"
        | _ -> q
    
    /// Return true if 'child' needs a non-capturing group when quantifying.
    let private needsGroupForQuant (child: IROp) : bool =
        match child with
        | IRCharClass _ -> false
        | IRDot -> false
        | IRGroup _ -> false
        | IRBackref _ -> false
        | IRAnchor _ -> false
        | IRLit v ->
            if v.Length = 2 && v.[0] = '\\' then false
            else v.Length > 1
        | IRAlt _ -> true
        | IRLook _ -> true
        | IRSeq parts -> parts.Length > 1
        | IRQuant _ -> true
    
    /// Generate opening for group based on type.
    let private emitGroupOpen (capturing: bool) (name: string option) (atomic: bool) : string =
        if atomic then "(?>"
        elif capturing then
            match name with
            | Some n -> sprintf "(?<%s>" n
            | None -> "("
        else "(?:"
    
    /// Default upper bound on AST/IR nesting depth before the emitter
    /// aborts. Mirrors the SSOT in the TypeScript reference.
    let DEFAULT_MAX_DEPTH = 250

    let private REDOS_MESSAGE =
        "The pattern contains overlapping alternations or nested unbounded "
        + "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
        + "and exponential CPU spikes. Consider using possessive quantifiers "
        + "(++ or *+) or atomic groups to guarantee execution safety."

    /// Mutable per-emit context threaded through `emitNode` so the depth,
    /// lookbehind, and warning-collection guards can fire without
    /// polluting the public API.
    type private EmitContext =
        { mutable Depth: int
          MaxDepth: int
          mutable InLookbehind: bool
          Warnings: ResizeArray<STRlingWarning> }

    let private newContext (maxDepth: int) : EmitContext =
        { Depth = 0
          MaxDepth = if maxDepth > 0 then maxDepth else DEFAULT_MAX_DEPTH
          InLookbehind = false
          Warnings = ResizeArray<STRlingWarning>() }

    /// True iff a quantifier has an unbounded upper bound.
    let private isUnboundedQuant (max: string) : bool = max = "Inf"

    /// True iff a quantifier matches a variable number of characters.
    let private isVariableLengthQuant (minv: int) (maxv: string) : bool =
        // Maxv is either an int rendered as a string or the sentinel "Inf".
        maxv <> string minv

    /// Mirror of `_isFixedLengthBody` in the TS SSOT. Returns `true` when
    /// `node` consumes a fixed number of characters and is therefore safe
    /// inside a PCRE2 lookbehind.
    let rec private isFixedLengthBody (node: IROp) : bool =
        match node with
        | IRQuant (child, minv, maxv, _) ->
            (not (isVariableLengthQuant minv maxv)) && isFixedLengthBody child
        | IRSeq parts -> parts |> List.forall isFixedLengthBody
        | IRAlt branches -> branches |> List.forall isFixedLengthBody
        | IRGroup (_, body, _, _) -> isFixedLengthBody body
        | IRLook _ -> true
        | _ -> true

    /// Mirror of `_hasNestedUnboundedQuant` in the TS SSOT. Detects an
    /// unbounded quantifier reachable from `child` via single-child
    /// wrappers or any branch of an Alt.
    let rec private hasNestedUnboundedQuant (child: IROp) : bool =
        match child with
        | IRQuant (_, _, maxv, _) -> isUnboundedQuant maxv
        | IRGroup (_, body, _, _) -> hasNestedUnboundedQuant body
        | IRSeq parts when parts.Length = 1 -> hasNestedUnboundedQuant parts.[0]
        | IRAlt branches -> branches |> List.exists hasNestedUnboundedQuant
        | _ -> false

    /// Append a single REDOS_RISK warning, deduplicated per pass.
    let private pushReDoSWarning (ctx: EmitContext) =
        let already =
            ctx.Warnings
            |> Seq.exists (fun w -> w.Code = "REDOS_RISK")
        if not already then
            ctx.Warnings.Add({ Code = "REDOS_RISK"; Message = REDOS_MESSAGE })

    /// Emit a single IR node to PCRE2 syntax.
    let rec private emitNode (parentKind: string) (node: IROp) (ctx: EmitContext) : string =
        ctx.Depth <- ctx.Depth + 1
        try
            if ctx.Depth > ctx.MaxDepth then
                let msg =
                    sprintf
                        "Maximum AST depth exceeded (limit: %d). This pattern is too deeply nested and risks host stack exhaustion during emission. Refactor the pattern to reduce nesting, or flatten capturing groups where possible."
                        ctx.MaxDepth
                raise (STRlingCompilationError(msg, "MAX_DEPTH"))
            match node with
            | IRLit v -> escapeLiteral v
            | IRDot -> "."
            | IRAnchor at ->
                match at with
                | "Start" -> "^"
                | "End" -> "$"
                | "WordBoundary" -> "\\b"
                | "NotWordBoundary" -> "\\B"
                | "NonWordBoundary" -> "\\B"
                | "AbsoluteStart" -> "\\A"
                | "EndBeforeFinalNewline" -> "\\Z"
                | "AbsoluteEnd" -> "\\z"
                | _ -> ""
            | IRBackref (byIndex, byName) ->
                match byName with
                | Some n -> sprintf "\\k<%s>" n
                | None ->
                    match byIndex with
                    | Some i -> "\\" + string i
                    | None -> ""
            | IRCharClass (negated, items) -> emitClass negated items
            | IRSeq parts -> parts |> List.map (fun p -> emitNode "Seq" p ctx) |> String.concat ""
            | IRAlt branches ->
                let body = branches |> List.map (fun b -> emitNode "Alt" b ctx) |> String.concat "|"
                if parentKind = "Seq" || parentKind = "Quant" then "(?:" + body + ")"
                else body
            | IRQuant (child, minv, maxv, mode) ->
                // ReDoS guard: only flag when the *outer* quantifier is
                // itself unbounded (e.g. `(a+)+`). A bounded outer like
                // `(a+){0,3}` cannot produce exponential backtracking on
                // its own.
                if isUnboundedQuant maxv && hasNestedUnboundedQuant child then
                    pushReDoSWarning ctx
                let childStr = emitNode "Quant" child ctx
                let grouped =
                    match child with
                    | IRGroup _ -> childStr
                    | _ when needsGroupForQuant child -> "(?:" + childStr + ")"
                    | _ -> childStr
                grouped + emitQuantSuffix minv maxv mode
            | IRGroup (capturing, body, name, atomic) ->
                emitGroupOpen capturing name atomic + emitNode "Group" body ctx + ")"
            | IRLook (dir, neg, body) ->
                // Variable-length lookbehind guard: PCRE2 mandates a
                // fixed-width lookbehind body. Detect the violation here
                // so the user sees a Signpost-pattern error rather than
                // an opaque PCRE2 compile failure leaking from the runtime.
                if dir = "Behind" && not (isFixedLengthBody body) then
                    let msg =
                        "PCRE2 does not support variable-length lookbehinds. "
                        + "The lookbehind body contains a quantifier that makes "
                        + "its length unpredictable. Rewrite the assertion using "
                        + "a fixed-length range (e.g. `{1,8}` instead of `+`), "
                        + "or restructure the pattern using a Lookahead, or "
                        + "extract the quantified portion outside the assertion."
                    raise (STRlingCompilationError(msg, "VLB_NOT_SUPPORTED"))
                let wasInLb = ctx.InLookbehind
                if dir = "Behind" then ctx.InLookbehind <- true
                try
                    let op =
                        match dir, neg with
                        | "Ahead", false -> "?="
                        | "Ahead", true -> "?!"
                        | "Behind", false -> "?<="
                        | "Behind", true -> "?<!"
                        | _, _ -> "?="
                    "(" + op + emitNode "Look" body ctx + ")"
                finally
                    ctx.InLookbehind <- wasInLb
        finally
            ctx.Depth <- ctx.Depth - 1
    
    /// Build the inline prefix form expected by tests, e.g. "(?imx)".
    let private emitPrefixFromFlags (flags: Flags) : string =
        let sb = StringBuilder()
        if flags.IgnoreCase then sb.Append('i') |> ignore
        if flags.Multiline then sb.Append('m') |> ignore
        if flags.DotAll then sb.Append('s') |> ignore
        if flags.Unicode then sb.Append('u') |> ignore
        if flags.Extended then sb.Append('x') |> ignore
        if sb.Length > 0 then sprintf "(?%s)" (sb.ToString())
        else ""
    
    /// Emit a PCRE2 pattern string from IR.
    let emit (irRoot: IROp) (flags: Flags option) : string =
        let prefix = 
            match flags with
            | Some f -> emitPrefixFromFlags f
            | None -> ""
        let ctx = newContext 0
        let body = emitNode "" irRoot ctx
        prefix + body

    /// Emit a PCRE2 pattern string from IR and surface any non-fatal
    /// diagnostics collected during emission. Pass `maxDepth <= 0` to
    /// use `DEFAULT_MAX_DEPTH`.
    let emitWithDiagnostics (irRoot: IROp) (flags: Flags option) (maxDepth: int) : CompileResult =
        let prefix =
            match flags with
            | Some f -> emitPrefixFromFlags f
            | None -> ""
        let ctx = newContext maxDepth
        let body = emitNode "" irRoot ctx
        { Pattern = prefix + body
          Warnings = ctx.Warnings |> List.ofSeq }
    
    /// Emit a PCRE2 pattern string from IR without flags.
    let emitNoFlags (irRoot: IROp) : string =
        emit irRoot None
