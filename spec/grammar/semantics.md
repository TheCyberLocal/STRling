# STRling DSL — Semantics

This document explains the **meaning**, behavior, and design choices of the STRling DSL. It serves as the human-readable companion to the canonical EBNF grammar located in `dsl.ebnf`. While the EBNF defines the syntax, this document defines what that syntax _does_.

**Status & Scope**  
This document is **normative** for STRling v3 semantics and maps to TargetArtifact Base Schema **1.0.0** and PCRE2 emitter schema **v1**. Sections marked "Notes" are non-normative clarifications.

## 🧩 Core vs. Extensions

STRling distinguishes between **core features** (supported across all target engines) and **extensions** (engine-specific features that may not be portable).

| Feature Category         | Core Features                                                             | Extensions (Engine-Specific)                        |
| ------------------------ | ------------------------------------------------------------------------- | --------------------------------------------------- |
| **Characters & Escapes** | Literals, `\n`, `\r`, `\t`, `\f`, `\0`, hex & Unicode escapes             | Octal escapes, `\Q...\E` quoting, `\a`, `\e`, `\cX` |
| **Character Classes**    | `[]`, ranges, shorthand (`\d`, `\w`, `\s`), Unicode properties            | POSIX classes (`[[:alpha:]]`), `\R`, `\h`, `\v`     |
| **Quantifiers**          | Greedy & lazy (`*`, `+`, `?`, `{m,n}`, `*?`, etc.)                        | Possessive quantifiers (`*+`, `++`, etc.)           |
| **Groups**               | Capturing `(...)`, named captures `(?<name>...)`, non-capturing `(?:...)` | Atomic `(?>...)`, Recursive patterns                |
| **Anchors**              | `^`, `$`, `\b`, `\B`                                                      | Absolute anchors (`\A`, `\Z`, `\z`)                 |
| **Lookarounds**          | All lookarounds (fixed-length lookbehind)                                 | Variable-length lookbehind                          |
| **Flags**                | Global flags (`%flags i,m,s,u,x`)                                         | Inline modifiers (`(?i)`)                           |

Emitters **MUST error** when encountering non-core features that the target engine cannot support. Emitters **MUST warn** when encountering features that might have different semantics across engines.

---

## ✍️ Literals & Escaping

Literals are the simplest building blocks of a pattern, representing raw characters.

-   **Literal Characters**: Any character that is not a special metacharacter (`. \ | ( ) [ ] { } ^ $ * + ?`) matches itself. For example, the pattern `abc` matches the literal string "abc".

-   **Escaping**: To match a special metacharacter as a literal, you must escape it with a backslash (`\`). For example, `\.` matches a literal period, not "any character".

-   **Control & Whitespace Escapes**: Common non-printing characters can be represented with escapes:

    -   `\n` → Newline
    -   `\r` → Carriage Return
    -   `\t` → Tab

-   **Hex & Unicode Escapes**: Characters can be specified by their code points, which is essential for patterns that must match specific or non-printable characters.

    -   `\xHH` → Character with the given 2-digit hexadecimal code.
    -   `\uHHHH` → Character with the given 4-digit hexadecimal Unicode code point (BMP).
    -   `\UHHHHHHHH` → Character with the given 8-digit hexadecimal Unicode code point.

    These escapes can be used anywhere literals are allowed, including within character classes, where they represent a single character in the set. Support for `\UHHHHHHHH` (full Unicode) varies by engine, and emitters must properly handle this gracefully according to the target engine's capabilities.

-   **Brace Escapes**: STRling accepts `\x{…}` (hex code point) and `\u{…}` where supported; emitters translate to target syntax. In JavaScript, **`\u{…}` requires `u` or `v`** flag and switches to code-point semantics for that escape.

-   **Additional Control Escapes**: Common non-printing characters can be represented with escapes:

    -   `\n` → Newline
    -   `\r` → Carriage Return
    -   `\t` → Tab
    -   `\f` → Form feed
    -   `\v` → Vertical tab

-   **Additional Control Escapes (Extensions)**:

    -   `\a` → Bell (BEL)
    -   `\e` → Escape (ESC)
    -   `\cX` → Control character (X = letter)

    These are not part of ECMAScript; emitters targeting engines without support MUST error or warn.

-   **Octal Escapes Forbidden:** Octal escapes (e.g., `\123`) are **forbidden** due to ambiguity with backreferences.

    -   Only `\0` (null byte) is permitted.
    -   Use hex escapes (`\xHH`) or Unicode escapes (`\uHHHH`) instead.
    -   Emitters **MUST error** on any octal escape except `\0`.

-   **Quoting Blocks**: The syntax `\Q...\E` is **not** part of the core STRling DSL. If present, emitters must either normalize to literal sequences or warn if the target engine lacks support for this feature.

-   **Context-Sensitive Escapes**: Some escapes have different meanings in different contexts:
    -   `\b` outside a character class is a word boundary, but within a character class `[\b]` it represents a backspace character.
    -   `\0` represents a null character (code point 0) but may be treated differently by various engines when used in certain contexts.

> **Note on Code Points vs Code Units**: In JavaScript, without `u/v` flags, regex operates on **UTF-16 code units**; with `u` or `v`, escapes like `\u{1F600}` are interpreted as a single code point. STRling aims for code-point intent; emitters warn when a target can only do code-unit matching.

---

## 🔠 Character Classes

Character classes define a set of characters, any one of which can match at that position in the string.

-   **Basic Sets**: `[abc]` matches a single `a`, `b`, or `c`.
-   **Ranges**: `[a-z]` matches any single lowercase ASCII letter. You can combine ranges, e.g., `[A-Za-z0-9]`.
-   **Negation**: A `^` at the beginning of a class inverts it. `[^0-9]` matches any character that is _not_ a digit.
-   **Shorthand Classes**: For convenience, several shorthand classes are available:

    -   `\d` → A digit. In Unicode mode (`%flags u`), this is equivalent to `\p{Digit}`.
    -   `\w` → A word character. In Unicode mode, this is equivalent to `[\p{L}\p{N}_]`.
    -   `\s` → A whitespace character. In Unicode mode, this includes tabs, spaces, newlines, and various other Unicode space separators.
    -   `\D`, `\W`, `\S` → The negated versions of their lowercase counterparts.

-   **Unicode Property Classes**: For powerful, language-agnostic matching, you can use Unicode properties.

    -   `\p{L}` or `\p{Letter}` → Any Unicode letter.
    -   `\p{Script=Greek}` → Any character from the Greek script.
    -   `\P{...}` → The negated version (e.g., `\P{L}` matches any character that is not a letter).
    -   JavaScript **Unicode property escapes `\p{…}` / `\P{…}` require `u` (or `v`) flag**; otherwise they are invalid. In PCRE2, properties are available and honor UCP when enabled.

-   **PCRE2-Specific Features:** Shorthands like `\R` (any newline), `\h` (horizontal whitespace), `\v` (vertical whitespace), and POSIX classes (e.g., `[[:alpha:]]`) are **not part of the core STRling DSL**.
    -   Emitters **MAY support** them as extensions for PCRE2.
    -   Emitters **MUST warn** when they are used and the target engine lacks support.

> ⚠️ **Note on Engine Compatibility**: The exact set of supported Unicode property names can vary between regex engines. Emitters must validate these properties and surface a warning or error in the `TargetArtifact` if an unsupported property is used.

---

## 🌐 Unicode & Word/Line Semantics

STRling is designed as a Unicode-first DSL, following the principles defined in Unicode Technical Standard #18.

-   **Default Unicode Policy**: Unless otherwise specified, STRling interprets all character classes and escapes with full Unicode semantics:

    -   `\d`, `\s`, `\w`, and `\b` use Unicode properties by default.
    -   Character classes like `[a-z]` still represent their traditional ASCII ranges.

    **Note:** In ECMAScript, `\w` and therefore `\b` remain ASCII-based even with the `u` flag. Use Unicode property escapes (e.g., `\p{L}`) for truly Unicode word semantics; emitters SHOULD warn when users rely on Unicode word boundaries via `\b` in JS.

-   **Normalization Policy**: STRling does **not** perform canonical normalization; matching is by code point sequences. Case-insensitive matching uses Unicode case-folding where available; **no locale-specific rules** (e.g., Turkish İ/i) are applied.

-   **Engine Differences**:

    -   **ECMAScript**: Even with the `u` flag, `\w` is ASCII-only (A-Za-z0-9\_); full Unicode support requires property escapes like `\p{L}` with the `u` flag. This ASCII limitation affects `\b` word boundaries in JavaScript as well.
    -   **PCRE2**: Full Unicode support requires the UCP (Unicode Character Properties) option; otherwise, character shorthands are limited to ASCII. When PCRE2's UCP option is enabled, shorthands like `\w`, `\d`, `\s` use Unicode properties instead of ASCII.
    -   **STRling Policy**: Emitters must use the fullest Unicode support available in the target engine, or issue a warning when dropping down to ASCII-only.

-   **Line Terminator Set**:
    -   In ECMAScript, line terminators include `\n` (LF), `\r` (CR), `\u2028` (Line Separator), and `\u2029` (Paragraph Separator).
    -   With the `s` flag (dotAll), `.` matches all these characters; otherwise, it excludes them.
    -   The `m` flag affects how `^` and `$` treat these line terminators.
    -   PCRE2's newline behavior is configurable, and STRling emitters should document which convention they use.

---

## 📐 Extended / Free-Spacing Mode

When the `x` flag is set (`%flags x`), the pattern is parsed in free-spacing mode:

-   **Outside Character Classes**:

    -   Unescaped whitespace characters are ignored.
    -   The `#` character begins a comment that runs until the end of the line.
    -   This allows patterns to be formatted with indentation and inline documentation.

-   **Inside Character Classes**:

    -   Whitespace and `#` are treated as literal characters to be matched.
    -   To include a literal space in a pattern outside a character class, either escape it (`\ `) or use a hex escape (`\x20`).

-   **Engine Compatibility**:
    -   ECMAScript has no native `x` flag. Emitters may simulate free-spacing by stripping insignificant whitespace/comments at compile time; if exact semantics can't be preserved, emit a warning.
    -   PCRE2's extended mode (`x` flag) serves as the reference semantics for STRling.

```
# Example of free-spacing mode (%flags x):
(?<number>   # Match a number
    [+-]?    # Optional sign
    \d+      # One or more digits
    (\.\d+)? # Optional decimal part
)
```

---

## `.` The Dot Operator

The dot (or period) is a special metacharacter that stands for "any character".

-   **Default Behavior**: By default, `.` matches any single character **except for newline** (`\n`).
-   **With `%flags s` (dotAll)**: When the `s` flag is active, the dot's behavior is modified to match **absolutely any character**, including newlines.
-   **With `%flags u` (Unicode)**: The dot correctly handles Unicode characters, including multi-byte characters and surrogate pairs.

> ⚠️ **Note on Null Bytes**: The dot's behavior with null bytes (`\0`) can vary. In PCRE2, for example, it does match null bytes. STRling semantics consider the null byte a valid character to be matched by the dot.

---

## | Alternation & Operator Precedence

-   **Alternation (`|`)**: The vertical bar acts as an "OR" condition, matching either the entire expression to its left or the entire expression to its right. For example, `cat|dog` matches "cat" or "dog".

-   **Operator Precedence**: The STRling DSL has a clear order of operations:

    1.  **Quantifiers** (`*`, `+`, `?`) bind to the single atom immediately preceding them (e.g., a literal, a group, or a character class).
    2.  **Concatenation** (sequence of atoms) binds tighter than alternation. For example, `abc|def` is interpreted as `(abc)|(def)`, not `ab(c|d)ef`.
    3.  **Alternation** (`|`) has the lowest precedence. To have it apply to only part of a sequence, you must use a group: `ab(?:c|d)ef`.

-   **Evaluation Order**: Matching is **leftmost-first** (a.k.a. "first-match"): among alternatives, the first that can match wins; engines backtrack within the chosen branch only. This is distinct from "leftmost-longest" matching used in some other systems.

---

## 🍽️ Quantifiers & Greediness

Quantifiers specify how many times a preceding token must occur. STRling supports two matching modes and multiple quantifier forms.

### Quantifier Forms

| Syntax  | Meaning                           | Greedy  | Lazy     |
| ------- | --------------------------------- | ------- | -------- |
| `*`     | 0 or more times                   | `*`     | `*?`     |
| `+`     | 1 or more times                   | `+`     | `+?`     |
| `?`     | 0 or 1 time                       | `?`     | `??`     |
| `{n}`   | Exactly n times                   | `{n}`   | `{n}?`   |
| `{n,}`  | At least n times                  | `{n,}`  | `{n,}?`  |
| `{n,m}` | Between n and m times (inclusive) | `{n,m}` | `{n,m}?` |

### Matching Modes

-   **Greedy (Default)**: A greedy quantifier will match as many characters as possible while still allowing the rest of the pattern to match.
-   **Lazy (or Reluctant)**: A lazy quantifier, created by adding a `?` suffix, will match as _few_ characters as possible.

> **Note on Possessive Quantifiers:** Possessive quantifiers (e.g., `a*+`) are **not part of the core STRling DSL**. Use atomic groups (`(?>a*)`) instead for backtracking control.

### Nested Quantifiers

When nested unbounded quantifiers are detected (e.g., `(a+)*`), emitters should emit a **`REDOS_RISK`** warning with information about potential catastrophic backtracking, which can lead to exponential execution time.

### Matching Behavior

STRling follows the "leftmost-first" matching strategy typical of Perl/PCRE-style engines:

-   The engine attempts to match at each position in the string, starting from the left.
-   At each position, it tries alternatives from left to right.
-   The first successful alternative is chosen, and greediness controls backtracking within that alternative.
-   This is different from "leftmost-longest" matching used in some other systems.

---

## 📦 Groups & Capturing

Groups serve two main purposes: to bundle a sequence of tokens together and to capture a portion of the matched string.

-   **Capturing Group `(...)`**: Captures the matched text for backreferences or extraction.

    -   Capture indices are assigned by the order of opening parentheses, from left to right in the pattern, including nested groups.
    -   The first capturing group is at index 1, the second at index 2, and so on.
    -   Group 0 (the whole match) is **not** addressable via backreference in STRling; emitters may expose it at runtime, but **`\0` is not a backref** in the DSL.

-   **Named Capturing Group `(?<name>...)`**: Captures text and allows it to be referenced by name.

    -   Names must be unique within a pattern for portability (even though some engines like PCRE2 permit duplicates).
    -   Names should follow a common subset of identifier rules: start with a letter and contain only letters, digits, and underscores.
    -   Emitters may transform the syntax to the target engine's naming format (e.g., Python's `(?P<name>...)` format).
    -   Emitters MUST error on duplicate names to ensure consistent behavior across engines.

-   **Non-capturing Group `(?:...)`**: Groups tokens without capturing, for efficiency.

-   **Atomic Group `(?>...)`**: A performance optimization that prevents backtracking once the inner expression has matched.

    > ⚠️ **Note on Engine Compatibility**: Atomic groups are only supported by certain regex engines (e.g., PCRE2, Ruby). For unsupported engines, including standard ECMAScript as of ES2025, emitters MUST report this limitation in the `TargetArtifact`'s `errors` or `warnings` array.

---

## 🔗 Backreferences

Backreferences allow you to refer back to the text that was captured by a capturing group earlier in the pattern.

-   **Numeric Backreference (`\1`, `\2`)**: Refers to the Nth capturing group in the pattern, ordered by its opening parenthesis from left to right.

    -   **Example**: `<(\w+)>.*</\1>` matches a simple opening and closing HTML/XML tag pair.

-   **Named Backreference (`\k<name>`)**: Refers to a group by its given name. This is often more readable and maintainable than numeric references.

    -   `\k<name>` is the canonical form in STRling.
    -   Emitters may transform to engine-specific forms (e.g., Python's `(?P=name)` or PCRE2's `\g{name}`).

-   **Behavior**: A backreference matches the exact string that was most recently captured by its corresponding group. If the group did not participate in the match (e.g., it was in an unfollowed branch of an alternation), the backreference will fail to match.

    -   **Example**: In the pattern `(a)|(b)\1`, if the second alternative matches, `\1` will fail because the first group did not participate in the match.

-   **Scope**: Backreferences are only valid if they refer to a group that has already been defined to their left in the pattern. **Forward references are not allowed** and will be treated as a parse-time error, even though some engines might defer this check to runtime.
    -   STRling currently does not support recursive patterns or self-references. Patterns requiring recursion should be flagged by emitters.

---

## 📍 Anchors

Anchors are zero-width assertions that match positions rather than characters.

-   **Line Anchors**:

    -   `^` → Matches the start of the string. If the `%flags m` (multiline) is set, it also matches the position immediately after any line terminator.
    -   `$` → Matches the end of the string. If `%flags m` is set, it also matches the position immediately before any line terminator.

    > ⚠️ **Note on Line Endings**: In multiline mode (`m` flag), the behavior of `^` and `$` with respect to different line endings (e.g., `\r\n` vs. `\n`) may vary across engines. Emitters should adhere to the target engine's specifications, and any deviations should be noted in the `compat` or `warnings` field of the `TargetArtifact`.

-   **Word Boundaries**:

    -   `\b` → A **word boundary**. This is the zero-width position between a word character (`\w`) and a non-word character (`\W`), or at the start/end of the string.
        -   **Example**: `\bcat\b` matches "cat" but not "concatenate".
        -   **Important**: Inside a character class, `[\b]` represents a backspace character, not a word boundary.
    -   `\B` → A **non-word-boundary**. This is any position where `\b` does not match.

-   **Engine-Specific Anchors (Non-Core)**:

    The anchors `\A` (start of string), `\Z` (end of string before final newline), and `\z` (absolute end of string) are **extensions** supported primarily in PCRE2.

    -   Emitters **MUST error** if these are used with engines that do not support them (e.g., ECMAScript).
    -   Prefer core anchors `^` and `$` with appropriate flags for portability.

-   **Newline Handling**:
    -   PCRE2 offers configurable newline conventions that affect the behavior of `^`, `$`, and `.`.
    -   STRling normalizes intent, but emitters enforce engine-specific limits, surfacing warnings via `compat`.
    -   The construct `\R` in PCRE2 matches any Unicode newline sequence but is not standardized across all engines.

---

## 👀 Lookarounds

Lookarounds are zero-width assertions that match based on what comes before or after the current position, without consuming any characters.

-   `(?=...)` → **Positive Lookahead**: Asserts that the following text matches the pattern, but doesn't consume it.

    -   **Example**: `foo(?=bar)` matches "foo" only when followed by "bar".

-   `(?!...)` → **Negative Lookahead**: Asserts that the following text does _not_ match the pattern.

    -   **Example**: `foo(?!bar)` matches "foo" only when NOT followed by "bar".

-   `(?<=...)` → **Positive Lookbehind**: Asserts that the preceding text matches the pattern.

    -   **Example**: `(?<=foo)bar` matches "bar" only when preceded by "foo".
    -   **Fixed-Length Requirement**: In PCRE2 and many engines, lookbehind patterns must be fixed-length. Variable-length lookbehind is not supported.
    -   Emitters must verify **fixed-length** lookbehind by ensuring its AST subtree has a **deterministic length** (no variable quantifiers, no alternations of differing lengths).

-   `(?<!...)` → **Negative Lookbehind**: Asserts that the preceding text does _not_ match the pattern.
    -   **Example**: `(?<!foo)bar` matches "bar" only when NOT preceded by "foo".
    -   **Fixed-Length Requirement**: Like positive lookbehind, the pattern must be fixed-length in PCRE2 and many engines.

> ⚠️ **Note on Engine Compatibility**: ECMAScript supports lookbehind assertions (ES2018+), but still requires fixed length. Emitters must validate lookbehind patterns and issue diagnostics for variable-length lookbehind when targeting engines with this limitation.

---

## 🚩 Directives

Directives are special commands at the beginning of a `.strl` file. While `%flags` is the primary operational directive, others are reserved for tooling and future use.

-   `%flags [i,m,s,u,x]` → Sets the matching behavior for the pattern.
-   `%engine [name]` → (Advisory) Informs tooling of the primary intended target engine (e.g., `pcre2`, `js`).
    -   This directive helps select the appropriate emitter during compilation but does not alter the pattern's semantics.
    -   When the specified engine has limitations incompatible with the pattern, emitters MUST surface these in the `TargetArtifact`.
    -   The directive serves as a hint for tooling to optimize output for the intended target, but the semantics of the pattern itself remain consistent.
-   `%lang [variant]` → (Reserved) Reserved for future use (e.g., dialects or language version tags). The value is an opaque identifier and has no effect on semantics in v3.

> ⚠️ **Note on Unknown Directives**: Any directive not recognized by an emitter should be ignored but result in a warning with code `UNKNOWN_DIRECTIVE`.

> ⚠️ **Inline Modifiers Forbidden:** Inline flags (e.g., `(?i)`, `(?-m)`) are **explicitly disallowed** in STRling patterns.
>
> -   Use the global `%flags` directive instead.
> -   Emitters **MUST error** on encountering inline modifiers.

---

## 🚨 Error Handling & Diagnostics

A key feature of the STRling compiler is its ability to provide rich diagnostics. The semantics for errors and warnings are defined as follows:

-   **Unsupported Constructs**: If a pattern uses a feature that a target emitter does not support (e.g., an unsupported Unicode property), the emitter **must** reject the pattern and include a descriptive error in the `TargetArtifact`. It must not silently fail or produce an incorrect output.
-   **Engine Compatibility**: If a pattern uses a feature that is valid but has known compatibility issues (e.g., variable-length lookbehind for PCRE2), the emitter **must** include a warning in the `TargetArtifact`'s `warnings` array.
-   **Diagnostic Hooks**: The `TargetArtifact` schema includes a top-level `warnings` array. This provides a formal channel for the compiler to communicate non-fatal issues, compatibility notes, or performance suggestions to the end-user or binding.

**Error and Warning Specifications**:

-   **Coordinate System**: All locations in errors and warnings use **UTF-32 code point indices** (not bytes or UTF-16 units) in the source `.strl` file, and include `{start,end}` half-open ranges.
-   **Severity Levels**: `error` (blocks output), `warning` (output proceeds with caveat), `info` (informational note).
-   **Canonical Error Codes**:
    -   `UNSUPPORTED_FEATURE`: The target engine doesn't support a feature used in the pattern.
    -   `ENGINE_INCOMPATIBILITY`: The feature is supported but with different semantics.
    -   `AMBIGUOUS_ESCAPE`: An escape sequence is ambiguous or could be interpreted differently.
    -   `REDOS_RISK`: The pattern may be vulnerable to catastrophic backtracking.
    -   `SYNTAX_ERROR`: The pattern violates the STRling grammar.
    -   `AMBIGUOUS_FLAG_SEMANTICS`: Requesting behavior (like Unicode case-folding) where target only supports a subset.
    -   `UNKNOWN_DIRECTIVE`: A directive that isn't recognized by the emitter.

The `TargetArtifact` may also include a `compat` block that details engine-specific limitations affecting the pattern (e.g., `variableLengthLookbehind: false` for PCRE2).

**Example Error Representation**:

```json
{
    "errors": [
        {
            "code": "UNSUPPORTED_FEATURE",
            "message": "Lookbehind assertions not supported in JavaScript before ES2018",
            "location": { "start": 10, "end": 20 }
        }
    ],
    "warnings": [
        {
            "code": "PERFORMANCE_CONCERN",
            "message": "Nested quantifiers may cause catastrophic backtracking",
            "location": { "start": 5, "end": 15 }
        }
    ],
    "compat": {
        "variableLengthLookbehind": false,
        "unicodeWordBoundary": false
    }
}
```

---

## 📊 Portability Notes

The following table summarizes key feature support across major regex engines:

| Feature                          | PCRE2             | ECMAScript (ES2025)              |
| -------------------------------- | ----------------- | -------------------------------- |
| Lookbehind                       | Fixed-length only | Fixed-length only (ES2018+)      |
| Atomic group `(?> … )`           | ✅                | ❌                               |
| Possessive quantifiers `*+`      | ✅                | ❌                               |
| `\w` Unicode-aware               | ✅ (with UCP)     | ❌ (ASCII; use `\p{…}` with `u`) |
| `\A`, `\Z`, `\z`                 | ✅                | ❌                               |
| Free-spacing `x`                 | ✅                | ❌                               |
| Named captures                   | ✅                | ✅ (ES2018+)                     |
| dotAll `s`                       | ✅                | ✅ (ES2018+)                     |
| Unicode property escapes `\p{…}` | ✅                | ✅ (with `u`/`v`)                |

STRling emitters must respect these limitations and provide appropriate diagnostics when features are used that the target engine doesn't support.

---

## 💡 Examples & Gotchas

This section provides practical examples and highlights common pitfalls.

-   **Matching Paired Tags**:

    ```
    %flags i
    <(?<tag>\w+)>.*?</\k<tag>>
    ```

    -   This uses a named backreference (`\k<tag>`) to find a matching closing tag. It also uses a lazy quantifier (`.*?`) to ensure it only matches until the _first_ closing tag.

-   **Validating an Email Local-Part**: `[A-Za-z0-9._%+-]+`

    -   This character class combines multiple ranges (`A-Z`, `a-z`, `0-9`) and literal characters (`._%+-`) to define the set of allowed characters.

-   **Greedy vs. Lazy Pitfall**: Given the input `<div>one</div><div>two</div>`:

    -   Greedy `<div>.*</div>` will match the entire string from the first `<div>` to the last `</div>`.
    -   Lazy `<div>.*?</div>` will correctly match just `<div>one</div>`.

-   **Word Boundaries and Unicode**: The `\b` anchor depends on `\w`, which is Unicode-aware by default. This means `\b` will correctly identify word boundaries in non-ASCII text, such as `\b你好\b`.

-   **Escaping in Character Classes**: Inside a character class `[...]`, most metacharacters (`*`, `+`, `.`) lose their special meaning and do not need to be escaped. However, `]`, `-`, and `^` (at the start) retain special meaning and may need to be handled carefully (e.g., place `-` at the start or end).

-   **Atomic Groups for Performance**: Consider the difference between these patterns matching against `"aaaab"`:

    ```
    /a+ab/     # Standard greedy matching - will backtrack to match "aaab"
    /(?>a+)ab/ # Atomic group - fails because it consumed all "a"s and won't backtrack
    ```

    Atomic groups are powerful for preventing ReDoS (Regular expression Denial of Service) attacks by eliminating unnecessary backtracking.

-   **Using Atomic Groups Instead of Possessive Quantifiers**:

    ```
    # Instead of possessive quantifiers (not in core DSL):
    # /a*+b/

    # Use atomic groups:
    /(?>a*)b/  # Also fails immediately on "aaab" without backtracking
    ```

-   **Free-Spacing Mode Example**:

    ```
    # Without free-spacing:
    (\d{4})-(\d{2})-(\d{2})

    # With free-spacing (%flags x):
    (
        \d{4}  # year
    ) - (
        \d{2}  # month
    ) - (
        \d{2}  # day
    )
    ```

-   **`\b` in Character Class vs. Outside**:

    ```
    \b word \b  # Matches "word" as a complete word
    [\b]        # Matches a backspace character
    ```

-   **Fixed-Length Lookbehind**:

    ```
    # Valid fixed-length lookbehind:
    (?<=ABC)123  # Matches "123" if preceded by "ABC"

    # Invalid variable-length lookbehind (will cause diagnostic):
    (?<=A+)123   # Variable repetition in lookbehind
    ```

-   **DotAll vs. Multiline**:

    ```
    # With dotAll flag (%flags s):
    a.b   # Matches "a\nb" because . includes newlines

    # With multiline flag (%flags m):
    ^start  # Matches "start" at beginning of string OR after any newline
    end$    # Matches "end" at end of string OR before any newline
    ```

    These flags affect different aspects - `s` changes what `.` matches, while `m` changes where `^` and `$` match.

---

## 📚 Glossary

This section defines key terms used throughout this document and related STRling components:

-   **Atom**: The smallest matchable unit in a pattern (e.g., a literal character, a character class, or a group).
-   **Term**: A sequence of one or more atoms, possibly with quantifiers.
-   **Branch**: An alternation arm (one option in an `|` expression).
-   **Code point**: A Unicode scalar value, the atomic unit of text in Unicode.
-   **Code unit**: A unit of encoding (e.g., 16 bits in UTF-16, 8 bits in UTF-8).
-   **Word character**: A character matched by `\w` (engine-dependent; ASCII in some engines, Unicode in others).
-   **Line terminator**: Characters that separate lines (engine-dependent; typically includes LF, CR, sometimes others).

---

## 📋 Conformance Examples

The following examples demonstrate how STRling patterns are intended to work across different engines:

### Phone Number with Named Captures

```
%flags x
(?<country>\+\d+)?[ -]?   # Optional country code
\(?(?<area>\d{3})\)?      # Area code
[ -]?                     # Optional separator
(?<prefix>\d{3})          # Prefix
[ -]?                     # Optional separator
(?<line>\d{4})            # Line number
```

**Intent**: Match phone numbers with optional country code, handling various separators.
**Notes**: Named captures provide semantic meaning; the `x` flag enables formatting and comments.

### Unicode Letter Matching

```
%flags u
\b\p{L}+\b
```

**Intent**: Match any sequence of Unicode letters as complete words.
**Notes**: Requires `u` flag in JavaScript; PCRE2 needs UCP enabled. The `\b` word boundaries respect Unicode letter properties with the `u` flag.

### Fixed-Length Lookbehind Currency

```
(?<=[$€£¥])[\d,]+\.?\d{0,2}
```

**Intent**: Match amounts after currency symbols, supporting thousands separators and decimal places.
**Notes**: The lookbehind is fixed-length (matches exactly one character); would fail verification if changed to `(?<=[$€£¥]?)` (optional symbol).
