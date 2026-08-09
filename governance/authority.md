# Engineering Authority

## Purpose

This document defines precedence when STRling artifacts disagree. It governs
engineering interpretation but creates no language syntax or semantics. An
artifact is normative only when the project has explicitly assigned it that
status; location or age alone is insufficient.

## Precedence

From highest to lowest authority:

1. **Normative specification.** Ratified, versioned language grammar and
   semantics expressly marked normative.
2. **Versioned public contracts and schemas.** Ratified public API, diagnostic,
   interoperability, serialization, and target-profile contracts for their
   declared versions and scopes.
3. **Accepted specification-authored conformance cases.** Independently
   reviewable cases derived from higher-level specifications or contracts and
   accepted through project review, not merely generated from an implementation.
4. **Ratified architectural decisions.** Accepted decisions governing system
   structure and engineering constraints, within their declared scope.
5. **Canonical reference implementation.** The designated semantic compiler,
   once established, as evidence of how higher-level rules are implemented.
6. **Implementation-specific tests.** Unit, integration, regression, snapshot,
   and golden tests local to an implementation or adapter.
7. **Historical behavior.** Previously observed output, compatibility evidence,
   released behavior, and historical test results.
8. **General documentation and examples.** Tutorials, guides, examples, and
   explanatory prose not expressly ratified as a higher-level artifact.

Lower levels remain valuable evidence. They can reveal ambiguity, regression,
or an error in a higher level, but they MUST NOT silently redefine it. A conflict
MUST be resolved by conforming the lower-level artifact or by explicitly
reviewing and versioning a change to the controlling higher-level artifact.

Generated output inherits neither authority nor acceptance merely because it is
checked in. A generator and its output MUST trace to the specification, contract,
or accepted conformance case they project.

Operational sources of truth, such as a version field used by release tooling,
have authority only for their stated operational value. They do not acquire
semantic authority.

## Transitional repository state

The current repository does not fully satisfy this hierarchy or the target
architecture. In particular, existing documents that call TypeScript behavior,
TypeScript tests, or implementation-generated fixtures normative describe a
transitional workflow. Those artifacts remain useful conformance evidence, but
they cannot supersede the normative specification or versioned contracts.

Duplicated binding behavior and historical fixtures MUST be preserved unless a
contained change explicitly authorizes a behavior change. Preservation during
migration is an engineering constraint, not elevation of that behavior above
the authority hierarchy.
