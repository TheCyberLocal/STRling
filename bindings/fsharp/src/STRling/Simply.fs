namespace STRling

open System
open STRling.Core

/// STRling Simply API - Fluent Pattern Builder for F#
///
/// This module provides a fluent, chainable API for building regex patterns
/// using F# idioms including computation expressions.
///
/// Example:
/// ```fsharp
/// let pattern = strling {
///     start
///     capture (digit 3)
///     may (anyOf "-. ")
///     capture (digit 3)
///     may (anyOf "-. ")
///     capture (digit 4)
///     endAnchor
/// }
/// ```
module Simply =

    /// Pattern wrapper that provides fluent API methods.
    type Pattern(node: Node) =

        /// Get the underlying AST node.
        member _.Node = node

        /// Compile the pattern to IR.
        member this.ToIR() = Compiler.compile node

        /// Emit as PCRE2 regex string.
        member this.ToPcre2(?flags: Flags) =
            let ir = this.ToIR()
            Emitters.Pcre2.emit ir flags

        /// Repeat this pattern a specific number of times.
        member this.Repeat(min: int, ?max: int) =
            let maxOpt = max
            Pattern(Quant(node, min, maxOpt, true, false, false))

        /// Make this pattern optional (0 or 1 times).
        member this.Optional() =
            Pattern(Quant(node, 0, Some 1, true, false, false))

        /// Match one or more times (greedy).
        member this.OneOrMore() =
            Pattern(Quant(node, 1, None, true, false, false))

        /// Match zero or more times (greedy).
        member this.ZeroOrMore() =
            Pattern(Quant(node, 0, None, true, false, false))

        /// Make the quantifier lazy.
        member this.Lazy() =
            match node with
            | Quant(target, min, max, _, _, _) ->
                Pattern(Quant(target, min, max, false, true, false))
            | _ -> this

        /// Make the quantifier possessive.
        member this.Possessive() =
            match node with
            | Quant(target, min, max, _, _, _) ->
                Pattern(Quant(target, min, max, false, false, true))
            | _ -> this

        /// Wrap in a capturing group.
        member this.Capture(?name: string) =
            Pattern(Group(true, name, false, node))

        /// Wrap in a non-capturing group.
        member this.Group() =
            Pattern(Group(false, None, false, node))

        /// Wrap in an atomic group.
        member this.Atomic() =
            Pattern(Group(false, None, true, node))

        /// Add a positive lookahead.
        member this.FollowedBy(p: Pattern) =
            Pattern(Seq [node; Lookahead p.Node])

        /// Add a negative lookahead.
        member this.NotFollowedBy(p: Pattern) =
            Pattern(Seq [node; NegativeLookahead p.Node])

    // ========== Static Pattern Builders ==========

    /// Matches the start of a line/string.
    let start = Pattern(Anchor "Start")

    /// Matches the end of a line/string.
    let endAnchor = Pattern(Anchor "End")

    /// Matches a word boundary.
    let wordBoundary = Pattern(Anchor "WordBoundary")

    /// Matches a non-word boundary.
    let nonWordBoundary = Pattern(Anchor "NotWordBoundary")

    /// Matches any single character (except newline by default).
    let any = Pattern(Dot)

    /// Matches a literal string.
    let lit (s: string) = Pattern(Lit s)

    /// Matches any digit (0-9).
    let digit () =
        let node = CharClass(false, [ClassEscape "digit"])
        Pattern(node)

    /// Matches any digit (0-9), repeated.
    let digits (min: int) =
        let node = CharClass(false, [ClassEscape "digit"])
        Pattern(node).Repeat(min)

    /// Matches any non-digit.
    let notDigit () =
        let node = CharClass(false, [ClassEscape "not-digit"])
        Pattern(node)

    /// Matches any word character (alphanumeric + underscore).
    let word () =
        let node = CharClass(false, [ClassEscape "word"])
        Pattern(node)

    /// Matches any word character, repeated.
    let words (min: int) =
        let node = CharClass(false, [ClassEscape "word"])
        Pattern(node).Repeat(min)

    /// Matches any non-word character.
    let notWord () =
        let node = CharClass(false, [ClassEscape "not-word"])
        Pattern(node)

    /// Matches any whitespace character.
    let whitespace () =
        let node = CharClass(false, [ClassEscape "whitespace"])
        Pattern(node)

    /// Matches any non-whitespace character.
    let notWhitespace () =
        let node = CharClass(false, [ClassEscape "not-whitespace"])
        Pattern(node)

    /// Matches any letter (A-Z, a-z).
    let letter () =
        let node = CharClass(false, [ClassRange("A", "Z"); ClassRange("a", "z")])
        Pattern(node)

    /// Matches any letter, repeated.
    let letters (min: int) =
        let node = CharClass(false, [ClassRange("A", "Z"); ClassRange("a", "z")])
        Pattern(node).Repeat(min)

    /// Matches any alphanumeric character.
    let alphaNum () =
        let node = CharClass(false, [ClassRange("A", "Z"); ClassRange("a", "z"); ClassRange("0", "9")])
        Pattern(node)

    /// Matches any character in the given set.
    let anyOf (chars: string) =
        let members = chars |> Seq.map (fun c -> ClassLiteral (string c)) |> List.ofSeq
        Pattern(CharClass(false, members))

    /// Matches any character NOT in the given set.
    let noneOf (chars: string) =
        let members = chars |> Seq.map (fun c -> ClassLiteral (string c)) |> List.ofSeq
        Pattern(CharClass(true, members))

    /// Matches a character range.
    let range (fromCh: char) (toCh: char) =
        Pattern(CharClass(false, [ClassRange(string fromCh, string toCh)]))

    /// Makes a pattern optional (0 or 1 times).
    let may (p: Pattern) = p.Optional()

    /// Matches one or more times.
    let oneOrMore (p: Pattern) = p.OneOrMore()

    /// Matches zero or more times.
    let zeroOrMore (p: Pattern) = p.ZeroOrMore()

    /// Wrap in a capturing group.
    let capture (p: Pattern) = p.Capture()

    /// Wrap in a named capturing group.
    let captureAs (name: string) (p: Pattern) = p.Capture(name)

    /// Wrap in a non-capturing group.
    let group (p: Pattern) = p.Group()

    /// Merge multiple patterns into a sequence.
    let merge (patterns: Pattern list) =
        match patterns with
        | [] -> Pattern(Lit "")
        | [p] -> p
        | ps -> Pattern(Seq (ps |> List.map (fun p -> p.Node)))

    /// Alternate between patterns (OR).
    let either (patterns: Pattern list) =
        match patterns with
        | [] -> Pattern(Lit "")
        | [p] -> p
        | ps -> Pattern(Alt (ps |> List.map (fun p -> p.Node)))

    /// Positive lookahead.
    let lookAhead (p: Pattern) = Pattern(Lookahead p.Node)

    /// Negative lookahead.
    let notLookAhead (p: Pattern) = Pattern(NegativeLookahead p.Node)

    /// Positive lookbehind.
    let lookBehind (p: Pattern) = Pattern(Lookbehind p.Node)

    /// Negative lookbehind.
    let notLookBehind (p: Pattern) = Pattern(NegativeLookbehind p.Node)

    /// Backreference by index.
    let backref (index: int) = Pattern(Backref(Some index, None))

    /// Backreference by name.
    let backrefByName (name: string) = Pattern(Backref(None, Some name))

    // ========== Computation Expression Builder ==========

    /// Builder for the strling computation expression.
    type STRlingBuilder() =
        member _.Yield(p: Pattern) = [p]
        member _.Yield(()) = []

        member _.Combine(a: Pattern list, b: Pattern list) = a @ b
        member _.Delay(f: unit -> Pattern list) = f()
        member _.Zero() = []

        member _.For(items: seq<'a>, body: 'a -> Pattern list) =
            items |> Seq.collect body |> List.ofSeq

        member _.Run(patterns: Pattern list) =
            merge patterns

    /// Computation expression builder for strling patterns.
    let strling = STRlingBuilder()

    // ========================================================================
    // Standard Library — Essential Patterns
    //
    // Canonical, RFC-grounded patterns for the most commonly validated string
    // formats. Each helper composes existing Simply primitives so the compiled
    // output flows through the standard pipeline and no raw regex leaks into
    // the public API.
    // ========================================================================

    let private classOf (items: ClassItem list) (min: int) (maxOpt: int option) =
        let body = CharClass(false, items)
        match min, maxOpt with
        | 1, Some 1 -> Pattern(body)
        | _ -> Pattern(Quant(body, min, maxOpt, true, false, false))

    let private letterItems = [ClassRange("A", "Z"); ClassRange("a", "z")]
    let private digitItems = [ClassEscape "digit"]
    let private hexItems = [ClassRange("A", "F"); ClassRange("a", "f"); ClassRange("0", "9")]

    let private digN min maxOpt = classOf digitItems min maxOpt
    let private hexN min maxOpt = classOf hexItems min maxOpt
    let private lettersN min maxOpt = classOf letterItems min maxOpt

    /// Matches an email address (RFC 5322 addr-spec, basic structure).
    let email () : Pattern =
        let localItems =
            letterItems @ digitItems @
            [ ClassLiteral "."; ClassLiteral "_"; ClassLiteral "%";
              ClassLiteral "+"; ClassLiteral "-" ]
        let domainItems =
            letterItems @ digitItems @
            [ ClassLiteral "."; ClassLiteral "-" ]
        let local = classOf localItems 1 None
        let domain = classOf domainItems 1 None
        let tld = lettersN 2 None
        merge [local; lit "@"; domain; lit "."; tld]

    /// Matches an HTTP or HTTPS URL (RFC 3986 generic syntax).
    let url () : Pattern =
        let urlBaseChars =
            letterItems @ digitItems @
            [ ClassLiteral "/"; ClassLiteral "_"; ClassLiteral "-";
              ClassLiteral "."; ClassLiteral "~"; ClassLiteral "%";
              ClassLiteral "&"; ClassLiteral "="; ClassLiteral ":";
              ClassLiteral "@"; ClassLiteral "!"; ClassLiteral "$";
              ClassLiteral "'"; ClassLiteral "("; ClassLiteral ")";
              ClassLiteral "*"; ClassLiteral "+"; ClassLiteral ",";
              ClassLiteral ";" ]
        let hostItems = letterItems @ digitItems @ [ClassLiteral "."; ClassLiteral "-"]
        let scheme = merge [lit "http"; may (lit "s")]
        let host = classOf hostItems 1 None
        let port = may (merge [lit ":"; digN 1 None])
        let path = may (merge [lit "/"; classOf urlBaseChars 0 None])
        let query = may (merge [lit "?"; classOf (urlBaseChars @ [ClassLiteral "?"]) 0 None])
        let fragment = may (merge [lit "#"; classOf (urlBaseChars @ [ClassLiteral "?"; ClassLiteral "#"]) 0 None])
        merge [scheme; lit "://"; host; port; path; query; fragment]

    /// Matches a UUID (RFC 4122). Pass `version=4` for v4-specific validation.
    let uuid (version: int) : Pattern =
        let dash = lit "-"
        if version = 4 then
            let variantItems =
                [ ClassLiteral "8"; ClassLiteral "9";
                  ClassLiteral "A"; ClassLiteral "B";
                  ClassLiteral "a"; ClassLiteral "b" ]
            let variant = classOf variantItems 1 (Some 1)
            merge [
                hexN 8 (Some 8); dash
                hexN 4 (Some 4); dash
                lit "4"; hexN 3 (Some 3); dash
                variant; hexN 3 (Some 3); dash
                hexN 12 (Some 12)
            ]
        else
            merge [
                hexN 8 (Some 8); dash
                hexN 4 (Some 4); dash
                hexN 4 (Some 4); dash
                hexN 4 (Some 4); dash
                hexN 12 (Some 12)
            ]

    /// Convenience: generic UUID without version validation.
    let uuidAny () = uuid 0

    /// Matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
    let ip (version: int) : Pattern =
        let ipv4 =
            merge [
                digN 1 (Some 3); lit "."
                digN 1 (Some 3); lit "."
                digN 1 (Some 3); lit "."
                digN 1 (Some 3)
            ]
        let ipv6 =
            merge [
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4); lit ":"
                hexN 1 (Some 4)
            ]
        match version with
        | 4 -> ipv4
        | 6 -> ipv6
        | _ -> either [ipv4; ipv6]

    /// Convenience: accepts both IPv4 and IPv6.
    let ipAny () = ip 0

    /// Matches an ISO 8601 / RFC 3339 datetime.
    let dateTime () : Pattern =
        let signItems = [ClassLiteral "+"; ClassLiteral "-"]
        let sign = classOf signItems 1 (Some 1)
        let frac = merge [lit "."; digN 1 None]
        let offset = merge [sign; digN 2 (Some 2); lit ":"; digN 2 (Some 2)]
        merge [
            digN 4 (Some 4); lit "-"; digN 2 (Some 2); lit "-"; digN 2 (Some 2)
            lit "T"
            digN 2 (Some 2); lit ":"; digN 2 (Some 2); lit ":"; digN 2 (Some 2)
            may frac
            may (either [lit "Z"; offset])
        ]


/// Convenience operators for pattern building.
[<AutoOpen>]
module SimplyOperators =

    /// Sequence operator - merge patterns.
    let (++) (p1: Simply.Pattern) (p2: Simply.Pattern) =
        Simply.merge [p1; p2]

    /// Alternation operator.
    let (|||) (p1: Simply.Pattern) (p2: Simply.Pattern) =
        Simply.either [p1; p2]
