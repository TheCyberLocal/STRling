# Public Contract Compatibility Policy

## Purpose and authority

Public snapshots are compatibility baselines. They detect and describe changes
to externally meaningful structure; they do not define STRling syntax,
semantics, diagnostics, or target behavior. Normative specification text and
versioned contracts retain their authority under `authority.md`.

`public-surfaces.json` inventories every active binding and the stable
compiler-facing schemas currently present in the repository. A surface is
`planned` only while its deterministic extractor and controlled failure tests
are being established, `enforced` when the canonical contracts check can
reproduce it, or `transitional` when reliable structural extraction is bounded
by a recorded gap and retirement condition.

## Detection and approval

Extraction compares the current source surface with a normalized checked-in
snapshot. Check mode never rewrites snapshots. A stale or missing enforced
snapshot and every extraction failure are detection failures regardless of a
change declaration.

After exact reproduction succeeds, the current snapshot is compared with the
snapshot at the active task's recorded Git base. This second comparison
classifies intentional drift and validates the declaration for the exact
surface identifier. Updating a snapshot therefore records detected structure;
it does not approve the change by itself.

## Compatibility classes

-   `unchanged`: normalized public structure is identical.
-   `compatible`: only non-constraining contract metadata or another explicitly
    ignored compatibility detail changed; no consumer-visible symbol or
    accepted data shape narrowed.
-   `additive`: a public symbol, optional property, schema alternative, or enum
    value was added without narrowing an existing contract.
-   `breaking`: a symbol was removed, a signature changed, a required property
    was added, an accepted schema alternative was removed, constraints were
    tightened, or public structure changed in another consumer-breaking way.
-   `intentional-correction`: a separately justified correction to a contract
    whose compatibility effect is still detected and reported. This label never
    suppresses a breaking result by itself.

API declaration comparison is deliberately conservative: additions are
additive, while removals and signature replacements are breaking. Schema
comparison recognizes optional property and alternative additions, required
property changes, enum expansion/contraction, property removal, constraint
tightening, and non-contract descriptive metadata. It is a structural
compatibility check, not a theorem prover for every JSON Schema assertion.

## Monotonic enforcement

An enforced surface cannot be removed from the registry or downgraded to a
transition as an incidental edit. Such a change requires a breaking
architecture declaration naming that surface and evidence explaining the
replacement or bounded exception. New extractor coverage may move only
`transitional -> planned -> enforced`; an enforced architecture rule follows
the corresponding `transitional -> enforced` path.
