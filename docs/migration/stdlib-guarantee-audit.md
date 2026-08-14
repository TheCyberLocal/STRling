# Standard-library guarantee audit

## Authority and scope

This audit applies the ratified validation vocabulary in
[`spec/stdlib/VALIDATION_GUARANTEES.md`](../../spec/stdlib/VALIDATION_GUARANTEES.md)
to the five current Essential helpers: `email`, `url`, `uuid`, `ip`, and
`dateTime`. It records the product decisions that P14-T02 must encode in the
future canonical registry. This task does not create that registry, add a
validator, or change any helper-generated AST or regex.

The audited baseline is repository commit
`82cf9e214b6747a1e831b529c699cda108cf8486`. Seventeen language bindings use
nineteen source/header files, eight public behavior variants, and seventeen binding test files. Every binding
test consumes [`essential_5.json`](../../spec/stdlib/essential_5.json) and
wraps the generated pattern for whole-value matching. The exported patterns
themselves remain composable and unanchored.

## Audit decisions

| Helper     | Current variants                | Assigned guarantee | External reference scope                                                         | Current disposition                                                    | Stronger future claim                                                                     |
| ---------- | ------------------------------- | ------------------ | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `email`    | default                         | `lexical_shape`    | inspired by RFC 5322 section 3.4.1                                               | retain the public helper and narrow its claim                          | use a separate structural or semantic validator; do not strengthen `email()` silently     |
| `url`      | default                         | `lexical_shape`    | inspired by RFC 3986 component spelling                                          | retain the public helper and narrow its claim                          | use a separate parser/validator with an explicit scheme and host policy                   |
| `uuid`     | generic and version 4           | `lexical_shape`    | subset of RFC 9562 textual format; v4 also checks version/variant nibbles        | retain both behaviors and replace the obsolete RFC 4122 citation       | use a separate parsed or generation-aware validator for stronger claims                   |
| `ip`       | IPv4, full-form IPv6, or either | `lexical_shape`    | inspired IPv4 shape; subset-like full IPv6 form within an overall inspired claim | retain compatibility behavior and expose its false positives/negatives | use a separate strict address validator supporting numeric ranges and governed IPv6 forms |
| `dateTime` | default                         | `lexical_shape`    | inspired by RFC 3339 section 5.6                                                 | retain the public helper and narrow its claim                          | use a separate RFC 3339 validator with calendar, clock, offset, and leap-second policy    |

All five guarantees apply under explicit whole-value evaluation. ASCII letter
and hexadecimal ranges are fixed, but `email`, `url`, IPv4, and `dateTime` use
the emitted `\\d` class. Its non-ASCII behavior is target-dependent and no
cross-target Unicode-digit guarantee is made. No helper normalizes input or
produces a parsed value.

No current helper is renamed, deprecated, or retired. That preserves the
public API while correcting the claim. Every future structural or semantic
surface must be additive and separately named; an existing lexical helper
cannot acquire rejection behavior under its current name.

## Exact boundary findings

### `email`

The current pattern accepts one or more ASCII letters, target-engine `\\d`
characters, or `._%+-`, an `@`, one or more ASCII letters, target-engine `\\d`
characters, dots, or hyphens, a dot, and at least two ASCII letters. It does
not enforce RFC 5322 dot-atom placement, domain-label
rules, quoted strings, domain literals, comments, internationalized addresses,
transport syntax, DNS existence, or deliverability. Leading/consecutive dots
and malformed domain-label placement are known accepted non-claims; quoted
local parts and domain literals are known rejected standard forms.

### `url`

The current pattern accepts lowercase `http` or `https`, `://`, an ASCII-letter
or target-engine-`\\d`/dot/hyphen host-like field, an optional `\\d` port, and optional
path, query, and fragment character buckets. It does not parse generic URI
grammar, validate percent-encoding, support user information or IP literals,
apply scheme-specific HTTP requirements, normalize components, resolve DNS, or
check resource existence. Malformed percent escapes are known accepted
non-claims; user-info and bracketed IPv6 URI forms are known rejected RFC 3986
forms.

### `uuid`

The generic form checks the RFC 9562 8-4-4-4-12 hexadecimal text shape. The
version-4 form additionally requires the version nibble `4` and variant nibble
`8`, `9`, `a`, or `b`. Neither form parses 128-bit fields, proves a recognized
semantic version for the generic form, proves random generation, uniqueness,
unguessability, provenance, or authorization. RFC 9562, published May 2024,
obsoletes the historical RFC 4122 citation.

### `ip`

The IPv4 branch accepts exactly four one-to-three-target-engine-`\\d`
components but does not check the required 0-255 range or leading-zero policy. The IPv6 branch accepts
exactly eight one-to-four-digit hexadecimal groups, corresponding only to the
full conventional form in RFC 4291 section 2.2. It rejects compressed and
mixed IPv6 forms. No branch normalizes an address, parses numeric fields, checks
prefixes or zones, or establishes network assignment/reachability.

### `dateTime`

The current pattern accepts the uppercase textual skeleton
`YYYY-MM-DDTHH:MM:SS` using the target engine's `\\d` class, optional fractional seconds, and an optional `Z` or
signed `HH:MM` offset. RFC 3339 requires an offset and imposes calendar, clock,
offset, and leap-second conditions that the helper does not check. Invalid
months, dates, hours, offsets, and missing offsets are known accepted
non-claims; lowercase `t`/`z`, which the RFC 3339 ABNF permits, are known
rejected forms.

## Standards references

-   Email lexical inspiration: [RFC 5322 section 3.4.1](https://www.rfc-editor.org/rfc/rfc5322.html#section-3.4.1), October 2008.
-   URI component inspiration and host forms: [RFC 3986 sections 3 and 3.2.2](https://www.rfc-editor.org/rfc/rfc3986.html#section-3), January 2005.
-   UUID text, variant, and version fields: [RFC 9562 sections 4, 4.1, and 4.2](https://www.rfc-editor.org/rfc/rfc9562.html#section-4), May 2024; RFC 9562 obsoletes RFC 4122.
-   IPv4 address size: [RFC 791](https://www.rfc-editor.org/rfc/rfc791.html), September 1981; dotted-decimal range grammar: [RFC 3986 section 3.2.2](https://www.rfc-editor.org/rfc/rfc3986.html#section-3.2.2).
-   IPv6 text forms: [RFC 4291 section 2.2](https://www.rfc-editor.org/rfc/rfc4291.html#section-2.2), February 2006.
-   Internet timestamps: [RFC 3339 sections 5.6 and 5.7](https://www.rfc-editor.org/rfc/rfc3339.html#section-5.6), July 2002.

References identify the source of selected lexical elements. Only the UUID
text-form decision is a `subset` standards claim. The other four helpers accept
at least one value outside the referenced validity grammar and therefore use
the weaker `inspired` scope.

## Compatibility and handoff

The migration classification for every current helper is
`behavior_preserved_claim_narrowed`: generated ASTs, regex strings, parameters,
defaults, and match outcomes remain unchanged, while prose and editor help stop
presenting lexical patterns as standards validation. The machine-readable audit
and edge corpus are the input to P14-T02. They are not a substitute for its
canonical registry, schema, deterministic fingerprint, generated surfaces, or
target portability certification.
