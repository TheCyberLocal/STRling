# STRling Architecture Terminology

## Status

This is the canonical vocabulary for product, specification, and architecture
work. Definitions assign responsibility without fixing fields, protocols,
module boundaries, or implementation language. Versioned specifications may
define additional terms within their scope but must not silently conflict with
this reference.

## Terms

**STRling**
:   The portable regex-intent compiler platform defined in
    [`product.md`](product.md).

**Semantic STRling**
:   The flagship semantic authoring language and abstraction. It expresses
    pattern intent independently of target regex spelling. Its future textual
    syntax is not the current regex-shaped grammar by default.

**Simply**
:   A family of idiomatic, first-class semantic authoring APIs for host
    languages. Simply lowers to the canonical semantic representation and does
    not define independent semantics.

**regex frontend**
:   The low-level source frontend that accepts STRling's existing
    regex-compatible notation. It supports compatibility, migration, and import
    use cases without defining the semantic ceiling of STRling.

**regex importer**
:   A frontend responsibility that accepts regex-shaped external input and
    translates recognized intent into the canonical semantic path. The current
    regex frontend is the first such capability; broader dialect coverage is
    future work.

**source dialect**
:   A named, versioned input syntax accepted by a frontend. Source dialects are
    distinct from target regex output dialects.

**semantic representation**
:   The canonical, target-independent expression of pattern intent on which
    analysis and planning operate. Its exact data contract is intentionally
    deferred.

**Semantic IR**
:   A future versioned compiler representation derived from semantic input and
    suitable for downstream analysis or planning. The term does not ratify the
    current shallow per-binding IRs or prescribe a separate physical structure.

**semantic analysis**
:   Target-independent validation and reasoning about meaning, including
    diagnostics and safety properties that can be determined before target
    selection or lowering.

**portability planner**
:   The compiler responsibility that compares semantic requirements with a
    selected target profile and chooses native support, a
    semantics-preserving rewrite, or an unsupported result.

**target**
:   The requested compilation destination, identified through a target profile;
    it is not a host programming language.

**target engine**
:   The regex implementation or runtime semantics for which STRling emits an
    artifact, such as PCRE2, ECMAScript, or Python `re`.

**target profile**
:   A versioned description of relevant target-engine semantics and
    capabilities. Its exact schema and version-selection rules remain later
    contract work.

**lowering**
:   The deliberate transformation of analyzed semantic intent into a
    target-specific plan consistent with a selected target profile.

**emitter**
:   The deterministic serializer of an already selected target-specific plan.
    An emitter does not invent semantic or portability policy.

**TargetArtifact**
:   A versioned compiler result for a selected target, including emitted target
    material and traceable diagnostics or explanatory metadata as its future
    contract defines. This term does not ratify existing schema fields as the
    final contract.

**binding**
:   The distributed STRling package or integration surface for a host-language
    ecosystem. Existing bindings may still contain transitional compiler logic.

**adapter**
:   The target-architecture portion of a binding that converts idiomatic host
    inputs and outputs to and from the canonical compiler interface without
    reimplementing STRling semantics.

**specification**
:   A ratified, versioned normative definition of STRling behavior within a
    declared scope. Drafts and explanatory documents are not specifications
    merely because they live under `spec/`.

**conformance case**
:   An independently reviewable example authored from the specification or a
    normative contract. It is normative only where the specification explicitly
    delegates an exact case to it and the case is accepted through ratification.

**compatibility evidence**
:   Historical behavior, tests, fixtures, binding outputs, or release
    observations retained to inform migration and compatibility decisions.
    Agreement across implementations does not make evidence normative.

**reference implementation**
:   The designated canonical compiler implementation that demonstrates and
    tests conformance to the normative specification. Implementation-only
    behavior remains implementation behavior until formally accepted.
