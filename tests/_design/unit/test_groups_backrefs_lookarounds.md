# Test Design — `unit/test_groups_backrefs_lookarounds.py`

## Purpose

This test suite validates the parser's handling of all grouping constructs, backreferences, and lookarounds. It ensures that different group types are parsed correctly into their corresponding AST nodes, that backreferences are validated against defined groups, that lookarounds are constructed properly, and that all syntactic errors raise the correct `ParseError`.

## Description

Groups, backreferences, and lookarounds are the primary features for defining structure and context within a pattern.

-   **Groups** `(...)` are used to create sub-patterns, apply quantifiers to sequences, and capture text for later use.
-   **Backreferences** `\1`, `\k<name>` match the exact text previously captured by a group.
-   **Lookarounds** `(?=...)`, `(?<=...)`, etc., are zero-width assertions that check for patterns before or after the current position without consuming characters.

This suite verifies that the parser correctly implements the rich syntax and validation rules for these powerful features.

## Scope

-   **In scope:**

    -   Parsing of all group types: capturing `()`, non-capturing `(?:...)`, named `(?<name>...)`, and atomic `(?>...)`.
    -   Parsing of numeric (`\1`) and named (`\k<name>`) backreferences.
    -   Validation of backreferences (e.g., ensuring no forward references).
    -   Parsing of all four lookaround types: positive/negative lookahead and positive/negative lookbehind.
    -   Error handling for unterminated constructs and invalid backreferences.
    -   The structure of the resulting `nodes.Group`, `nodes.Backref`, and `nodes.Look` AST nodes.

-   **Out of scope:**
    -   Quantification of groups or lookarounds (covered in `test_quantifiers.py`).
    -   Semantic validation of lookbehind contents (e.g., the fixed-length requirement is a post-parse or emitter-level check).
    -   Emitter-specific syntax transformations (e.g., Python's `(?P<name>...)`).

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Group Types**:
    -   Capturing Group: `(a)` → `Group(capturing=True, body=Lit('a'))`.
    -   Non-Capturing Group: `(?:a)` → `Group(capturing=False, body=Lit('a'))`.
    -   Named Capturing Group: `(?<A>a)` → `Group(capturing=True, name='A', body=Lit('a'))`.
    -   Atomic Group (Extension): `(?>a)` → `Group(capturing=False, atomic=True, body=Lit('a'))`.
    -   Nested Groups: `(a(?<b>c))` → Verify correct AST nesting and that capture indices are assigned correctly.
-   **Backreferences**:
    -   Numeric Backreference: `(a)\1` → `Seq(parts=[Group(...), Backref(byIndex=1)])`.
    -   Named Backreference: `(?<A>a)\k<A>` → `Seq(parts=[Group(...), Backref(byName='A')])`.
    -   Multiple/Nested Backreferences: `(?<A>a)(?<B>b)\k<A>\k<B>` → Verify correct name and index resolution.
-   **Lookarounds**:
    -   Positive Lookahead: `a(?=b)` → `Seq(parts=[Lit('a'), Look(dir='Ahead', neg=False)])`.
    -   Negative Lookahead: `a(?!b)` → `Seq(parts=[Lit('a'), Look(dir='Ahead', neg=True)])`.
    -   Positive Lookbehind: `(?<=a)b` → `Seq(parts=[Look(dir='Behind', neg=False), Lit('b')])`.
    -   Negative Lookbehind: `(?<!a)b` → `Seq(parts=[Look(dir='Behind', neg=True), Lit('b')])`.

### Category B — Negative Cases (Parse Errors)

-   **Unterminated Constructs**: Verify that a `ParseError("Unterminated ...")` is raised for:
    -   Unterminated group: `(a`
    -   Unterminated named group: `(?<name>a`
    -   Unterminated lookaround: `(?=a`
-   **Invalid Backreferences (per `parser.py` and `semantics.md`)**:
    -   Forward Reference by Name: `\k<A>(?<A>a)` must raise `ParseError("Backreference to undefined group <A>")`.
    -   Forward Reference by Index: `\2(a)(b)` must raise `ParseError("Backreference to undefined group \\2")`.
    -   Reference to Non-Existent Index: `(a)\2` must raise `ParseError("Backreference to undefined group \\2")`.
-   **Duplicate Group Names**: The behavior for `(?<a>a)(?<a>b)` should be tested. `semantics.md` states emitters must error, but the test should confirm the parser's behavior. The current `parser.py` allows this but a test should formalize this behavior.
-   **Invalid Syntax**: Test that inline modifiers `(?i)` are rejected with `ParseError("Inline modifiers '(?imsx)' are not supported")`.

### Category C — Edge Cases

-   **Empty Groups**: Test parsing of `()`, `(?:)`, `(?<A>)`.
-   **Backreference to Optional Group**: The pattern `(a)?\1` is syntactically valid and should parse correctly. (Its runtime matching behavior is a separate concern).
-   **Complex Nesting**: Test a lookaround inside a group inside another group, e.g., `(a(?=(b)))`.
-   **Backreference to group `\0`**: `\0` is defined as a null byte, not a backreference to the whole match. The test must confirm it parses as `Lit('\x00')`.

### Category D — Cross-Semantics / Interaction

-   **Backreference inside Lookaround**: A backreference should be able to refer to a group defined _before_ the lookaround. Test `(?<A>a)(?=\k<A>)`.
-   **Group inside Lookaround**: A lookaround can contain complex expressions, including groups. Test `(?=(a|b))`.
-   **Free-Spacing Mode (`%flags x`)**: Test that free-spacing and comments work correctly inside groups, but not inside the `<name>` part of a named group. Example: `(?< name > a #comment \n b)`.

### Category E — Nested Groups

-   **Multiple Levels of Nesting**:
    -   Test deeply nested capturing and non-capturing groups.
-   **Named Groups in Nested Structures**:
    -   Test named groups nested within other groups.
-   **Capture Index Assignment**:
    -   Test that capture indices are correctly assigned in nested group structures.
-   **Mixed Group Types**:
    -   Test nesting of different group types (capturing, non-capturing, named, atomic).

### Category F — Lookaround with Complex Content

-   **Lookaround with Alternation**:
    -   Test lookarounds containing alternation patterns.
-   **Lookaround with Quantifiers**:
    -   Test lookarounds containing quantified atoms.
-   **Lookaround with Character Classes**:
    -   Test lookarounds with character class content.
-   **Nested Lookarounds**:
    -   Test lookarounds nested within other lookarounds.

### Category G — Atomic Group Edge Cases

-   **Atomic Group with Alternation**:
    -   Test atomic groups containing alternation.
-   **Atomic Group with Quantifiers**:
    -   Test atomic groups with quantified content.
-   **Nested Atomic Groups**:
    -   Test atomic groups nested within other atomic groups.
-   **Atomic Group Interaction**:
    -   Test atomic groups in combination with other features.

### Category H — Multiple Backreferences

-   **Sequential Backreferences**:
    -   Test patterns with multiple backreferences in sequence.
-   **Backreferences to Multiple Groups**:
    -   Test backreferences referring to different groups.
-   **Named and Numeric Backreferences**:
    -   Test mixing of named and numeric backreference styles.
-   **Backreferences in Complex Patterns**:
    -   Test backreferences within complex nested structures.

### Category I — Groups in Alternation

-   **Groups in Alternation Branches**:
    -   Test groups appearing within alternation branches.
-   **Capturing Groups in Alternation**:
    -   Test that capture indices work correctly across alternation branches.
-   **Named Groups in Alternation**:
    -   Test named groups within alternation patterns.

## Completion Criteria

-   [x] All group syntaxes from `dsl.ebnf` are covered (`Group`, `GroupPrefix`, `GroupSpec`).
-   [x] All backreference syntaxes are covered (`Backreference`).
-   [x] All lookaround syntaxes are covered (`LookSigil`).
-   [x] The AST shape (`nodes.Group`, `nodes.Backref`, `nodes.Look`) is verified for all valid forms.
-   [x] All specified `ParseError` conditions, especially for invalid backreferences, are tested.
-   [x] The critical rule that **forward references are forbidden** is exhaustively tested.
-   [x] The rule that atomic groups are a non-core extension is noted.
-   [x] The behavior of nested groups and their capture index assignment is tested.
-   [x] Multiple levels of group nesting with various group types are validated.
-   [x] Lookarounds with complex content including alternation, quantifiers, and nesting are tested.
-   [x] Atomic group edge cases and interactions are thoroughly covered.
-   [x] Multiple backreference scenarios and combinations are validated.
-   [x] Groups within alternation and their capture behavior are tested.
