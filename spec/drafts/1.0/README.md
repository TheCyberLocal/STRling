# STRling Semantic Specification 1.0 Draft

## Status

**Unratified and non-normative.** This directory is the working home for the
future STRling Semantic Specification 1.0. Its current contents establish scope
only; they define no language constructs or canonical data-contract fields.

The working label is `1.0-draft.1`. It must not be used to claim conformance by
the current compiler, bindings, Simply APIs, regex frontend, schemas, or target
emitters.

## Intended scope

The 1.0 specification is expected to define semantic pattern intent and the
normative behavior needed for deterministic analysis, portability planning,
target-aware lowering, explanation, and target artifacts.

The next contained architecture task is expected to design independently
reviewable contracts for:

-   the canonical source model;
-   Semantic IR;
-   diagnostics;
-   compiler request and result;
-   target profile; and
-   target artifact.

This scaffold does not prejudge their fields, serialization formats, or process
boundaries.

## Inputs, not authority

The current regex frontend, Simply APIs, binding behavior, historical tests,
shared fixtures, current AST/IR structures, target schemas, and donor assets are
design and compatibility inputs. They do not become 1.0 semantics merely by
being copied or agreed upon by several implementations.

Ratification follows [`../../VERSIONING.md`](../../VERSIONING.md). Until then,
the controlling permanent decisions are the
[`product architecture`](../../../governance/product.md),
[`architecture invariants`](../../../governance/architecture.md), and
[`engineering authority hierarchy`](../../../governance/authority.md).
