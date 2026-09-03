# Engineering Authority

## Purpose

This document defines precedence when STRling artifacts disagree. It governs
engineering interpretation but creates no language syntax or semantics. An
artifact is normative only when the project has explicitly assigned that status
for a version and scope; location, age, implementation use, or apparent
completeness is insufficient.

The specification version and ratification policy is
[`spec/VERSIONING.md`](../spec/VERSIONING.md).
Product version, support, compatibility, and release authority is
[`governance/release-policy.json`](release-policy.json), with a generated
human-readable projection in
[`docs/release-policy.md`](../docs/release-policy.md).

## Precedence

From highest to lowest authority:

1. **Ratified versioned specification.** Language grammar and semantics
   expressly designated normative for an identified specification version.
2. **Normative versioned formal contracts and schemas.** Ratified public API,
   diagnostic, interoperability, serialization, target-profile, and related
   contracts for their declared versions and scopes.
3. **Delegated specification-authored conformance cases.** Independently
   reviewable cases derived from higher-level normative sources, accepted
   through project review, and normative only where a ratified specification
   delegates an exact question or example set to them.
4. **Ratified architectural decisions.** Accepted decisions governing semantic
   interpretation, system structure, or engineering constraints within their
   declared scope.
5. **Canonical reference implementation.** The designated semantic compiler,
   once established, as evidence of how higher-level rules are implemented.
6. **Implementation-specific tests.** Unit, integration, regression, snapshot,
   and golden tests local to an implementation or adapter.
7. **Compatibility and historical evidence.** Previously observed output,
   released behavior, binding agreement, historical tests, and preserved
   migration evidence.
8. **General documentation and examples.** Tutorials, guides, examples, and
   explanatory prose not expressly ratified as a higher-level artifact.

Lower levels remain valuable evidence. They can reveal ambiguity, regression,
or an error in a higher level, but they MUST NOT silently redefine it. A
conflict MUST be resolved by conforming the lower-level artifact or by
explicitly reviewing, ratifying, and versioning a change to the controlling
higher-level artifact.

## Reference implementation

The canonical compiler implements the normative specification and
contracts. It MUST NOT silently extend them. A behavior present only in the
implementation is implementation behavior until the project formally accepts it
through the controlling specification or contract process. The implementation
language does not change this rule.

## Generated and compatibility evidence

Generated output inherits neither authority nor acceptance merely because it is
checked in. A generator and its output MUST trace to the specification,
contract, or accepted conformance case they project. Output derived from an
implementation remains implementation evidence.

Existing binding behavior, historical tests, generated fixtures, and legacy
outputs MAY provide important compatibility evidence. Agreement among multiple
implementations does not make behavior normative. Preservation during migration
is an engineering constraint, not elevation above this hierarchy.

Operational sources of truth, such as a version field used by release tooling,
have authority only for their stated operational value. They do not acquire
semantic authority.

## Documentation

Tutorials, examples, binding guides, and general explanatory prose explain
normative behavior. They do not create new behavior. When documentation
conflicts with a normative source, the documentation MUST be corrected or
explicitly marked historical/transitional.

## Current specification state

There is currently no ratified STRling Semantic Specification version. The
frozen baseline accurately records the earlier formal-specification bundle as
`unversioned-transitional`. The Fourth Edition canonical compiler and adapters
implement the current versioned contracts, but implementation agreement and
retained historical fixtures remain non-normative evidence and cannot ratify
the draft specification or supersede existing versioned contracts.

Current versioned schemas retain authority only for their expressly declared
contract scopes. Product release `4.0.0`, semantic specification
`1.0-draft.1`, schema/protocol versions, target-profile revisions, target
engine versions, and certification-profile versions are separate identities.
