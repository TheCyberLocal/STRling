# Target profiles, portability, and artifacts

## Version-aware profile identity

A target selection is the immutable tuple `profile_id`, `profile_version`,
and SHA-256 of the profile's canonical JSON serialization. The profile document
separately identifies its engine version and, when relevant, its host runtime
version. Profile schema revisions therefore do not pretend to be engine
versions, and engine releases do not force a new compiler-contract version.

Engine versions are tagged as `semver`, `dotted_numeric`, `edition`, or
`opaque`; consumers never compare differently tagged versions by string
guessing. Authored examples cover PCRE2 10.42 and 10.43, ECMAScript 2024, and
Python `re` 3.11. The two PCRE2 profiles prove that the same engine identity can
have materially different versioned capabilities.

These profiles are deliberately enumerated-scope documents. Every listed
capability is authoritative for that profile revision, while an unlisted
capability is `unknown`, never implicitly supported or unsupported. They prove
the representation model without claiming that the complete target matrix has
already been authored.

## Capability and option model

A capability has `available`, `constrained`, or `unavailable` availability.
This is not a timeless Boolean. Constrained capabilities carry typed predicates
such as an upper bound, exact matcher API, or required option. Available and
unavailable entries carry no constraints.

Profile options identify compile-time or runtime settings that affect semantics.
They remain data, not pattern fragments. For example, PCRE2 Unicode property
semantics select `pcre2.utf` and `pcre2.ucp` separately. A caller must pass
those returned options to the engine instead of relying on inline control verbs.

The PCRE2 evidence records the documented 10.43 boundary: earlier versions
support only fixed-length top-level lookbehind alternatives, while 10.43
`pcre2_match` permits bounded variable-length branches. The default
variable-length limit is 255 characters and is caller-selectable. The Python
profile records fixed-length lookbehind and the atomic/possessive constructs
documented for 3.11. The ECMAScript profile cites the 2024 normative RegExp
grammar and matching clauses.

## Portability result

The stable portability vocabulary is exactly:

-   `native`: the selected profile can express the requirement directly;
-   `equivalent_rewrite`: a later planner has selected a semantics-preserving
    structural rewrite; and
-   `unsupported`: no permitted equivalent exists for the selected profile.

There is no degraded or approximate status. If product policy later accepts a
lossy mode, that requires a deliberate contract change rather than reinterpreting
one of these values. Overall status is the least-supported requirement decision,
and decisions are keyed by stable requirement and Semantic IR node identities.

## TargetArtifact

A TargetArtifact is emitted target data, not Semantic IR. It contains:

-   UTF-8 target pattern text and syntax identity;
-   compile/runtime engine options as a separate sorted array;
-   the immutable target-profile reference;
-   `native` or `equivalent_rewrite` artifact status;
-   resolved requirement records;
-   optional generated-to-semantic/source mappings; and
-   emission-phase diagnostics.

An `unsupported` plan cannot have an artifact. Any error diagnostic suppresses
the artifact at the compile-result layer. Generated and source spans use
half-open UTF-8 byte offsets; source maps are attribution only and do not affect
semantic equality.

Artifact serialization is deterministic: options sort by ID/stage, requirements
by requirement ID, source-map entries by generated span, node/source references
are unique and sorted, and diagnostics use canonical diagnostic result order.
The emitted pattern remains byte-for-byte data; options are not folded into it
for convenience.
