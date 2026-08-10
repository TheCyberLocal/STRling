# STRling Engineering Constitution

## Status and scope

This constitution is normative for STRling engineering. It governs how the
project defines, implements, verifies, and releases behavior; it does not itself
define STRling language semantics. The artifact precedence in
[`authority.md`](authority.md) resolves conflicting project guidance. The
ratified [product definition](product.md), [architecture invariants](architecture.md),
and [canonical terminology](terminology.md) define permanent conceptual
responsibilities without defining semantic data-contract fields. The
[specification versioning policy](../spec/VERSIONING.md) governs draft and
ratified semantic specifications.

## Permanent rules

### Specification sovereignty

Normative specifications and explicitly versioned public contracts MUST define
STRling behavior. An implementation, generated fixture, historical test result,
documentation example, or reference implementation MUST NOT silently supersede
them. Implementations provide evidence of conformance; existence alone does not
make behavior normative.

### Single semantic authority

The target architecture MUST contain one canonical implementation of parsing,
normalization, semantic analysis, portability planning, target lowering, and
emission semantics. Host-language adapters MAY provide idiomatic APIs,
serialization, interoperability, packaging, error conversion, and runtime
integration, but MUST NOT remain independent semantic compilers.

Current duplicated semantic implementations are transitional. They MUST NOT be
described as satisfying this invariant until migration and certification prove
that they depend on the canonical compiler authority.

### Determinism and portability

Given identical semantic input, compiler version, specification version, target
profile, and compiler options, compilation MUST produce deterministic semantic
results, diagnostics, and target artifacts. Any permitted nondeterministic
metadata MUST be explicitly specified and isolated from semantic results.

Target-dependent behavior MUST have an explicit outcome: native support,
semantics-preserving lowering or rewrite, or unsupported behavior. A degraded
mode MAY exist only when deliberately requested and documented by a versioned
contract. Unsupported behavior MUST NOT silently degrade.

### Contract-first semantic development

Semantic work MUST progress from contract or specification, to independently
reviewable conformance evidence, to implementation, and then certification. An
implementation MUST NOT generate expected behavior and thereby make its own
output the specification.

### Enforceable boundaries

Architecture boundaries MUST be expressible as machine-verifiable dependency
rules. Fitness gates SHOULD tighten progressively as transitional code is
replaced. A gate MUST NOT falsely certify a boundary that the repository has not
yet attained. The target dependency model is defined in
[`architecture.md`](architecture.md).

### Generated artifacts

Generated artifacts are non-normative. They MAY implement, project, or render a
normative contract, but the generated output MUST NOT become the source of
semantic truth. Changes to expected generated output MUST be justified by the
governing specification or contract.

### Governed exceptions

Warnings, suppressions, and architecture or quality exceptions MUST be governed
debt, not unmanaged background noise. Every accepted exception MUST identify
its rule, scope, rationale, and retirement or expiration condition. Exceptions
MUST be removed when that condition is met.

### Reproducible certification and release verification

Certification MUST operate from a known repository state with explicit
toolchains and dependencies. It MUST NOT rely on unrecorded developer-machine
state.

A package-upload command does not by itself constitute a successful release.
Every supported released package MUST be independently installable and
smoke-tested from its actual public distribution channel before the release is
certified successful.

### Meaningful permanent vocabulary

Permanent artifacts MUST describe the engineering capability, rule,
architecture, or behavior they contain. Temporary campaign identifiers MUST NOT
appear in source comments, docstrings, TODO or FIXME comments, test names,
product documentation, architecture terminology, changelogs, release notes,
generated output, or permanent commit subjects.

Migration-control records MAY contain neutral sequencing metadata for
traceability, but implementation artifacts MUST remain understandable without
knowledge of a migration campaign.
