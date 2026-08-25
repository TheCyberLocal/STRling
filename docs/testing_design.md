# STRling Test Design Standard

[← Back to Developer Hub](index.md)

This standard defines how new STRling behavior is proved. Tests support the
controlling specification and versioned contracts; they do not create semantic
authority by copying the output of an implementation.

## Authoring hierarchy under test

Test user intent through the same hierarchy presented to users:

1. **Semantic STRling** is the flagship textual language.
2. **Simply** is the programmatic semantic-construction surface.
3. **Regex-compatible source** is an explicit import and migration surface.

All three lower to canonical Semantic IR and enter the one Rust compiler
pipeline. A binding-private parser, AST, compiler, diagnostic, or emitter is not
an independent semantic oracle. The executable denominator and comparison
projection are locked by
[`Frontend convergence`](migration/frontend-convergence.md).

## Evidence layers

Use the layers affected by the change. A feature is complete only when every
applicable layer passes.

### 1. Contract and frontend evidence

Syntax, mapping, diagnostics, serialized requests, and profile references need
specification-authored or implementation-independent fixtures at their owning
boundary. These tests should prove:

-   accepted and rejected forms;
-   exact stable diagnostic identity and structured paths;
-   complete mapping into canonical Semantic IR;
-   deterministic parse and format behavior; and
-   schema rejection of unknown, missing, or malformed fields.

For Semantic STRling, use the grammar, mapping, diagnostics, and authored
fixtures under [`spec/frontends/semantic/1.0/`](../spec/frontends/semantic/1.0/).
For Simply, use the closed operation protocol under
[`spec/frontends/simply/1.0/`](../spec/frontends/simply/1.0/). For imports, use
the governed legacy-regex contract under
[`spec/frontends/legacy-regex/1.0/`](../spec/frontends/legacy-regex/1.0/).

### 2. Component and property evidence

Unit tests isolate a bounded implementation responsibility. Property tests
exercise invariants across many generated values. Cover at least:

-   a minimal successful case;
-   a representative composed case;
-   a boundary or malformed case;
-   deterministic repetition; and
-   a controlled mutation that would escape if the test were weak.

Prefer stable codes, paths, semantic facts, and canonical values over private
types or prose fragments. Parser tests may assert spans and recovery behavior;
kernel tests should assert representation-neutral semantics.

### 3. Canonical pipeline and convergence evidence

Integration tests must cross the actual public boundary. Route Semantic source,
native Simply, Preview transports, or source-less IR through `core::compile` or
the deterministic root transport and compare canonical results.

Equivalent intent is compared after alpha-renaming identities and removing only
the locked source/provenance fields listed in the convergence corpus. Semantic
facts, diagnostics, portability decisions, rewrites, and target artifacts stay
observable. A test must fail if any of those meaningful values changes.

When adding a frontend construct or Simply operation, extend the shared corpus
only from the controlling contract and retain its fail-closed completeness
checks. Never generate the expected semantic result from the implementation
being tested.

### 4. Target and runtime certification

An emitted pattern is not proof of behavior. Target claims require an exact
profile and, where execution is claimed, the isolated governed runtime harness.
For every applicable profile, cover:

-   portability classification and capability evidence;
-   deterministic lowering and serialization;
-   positive and negative runtime observations;
-   captures when the intent contains captures; and
-   expected unsupported or indeterminate outcomes.

Compare normalized observations, not target regex spelling. Engine-specific
behavior must be explicitly classified and must not silently weaken a portable
claim.

### 5. Compatibility differential evidence

Historical TypeScript, Python, and other binding implementations may be run as
independent compatibility witnesses. Their fixtures and outputs are
non-normative. Every meaningful difference must use the governed taxonomy:

-   `preserved_behavior`;
-   `intentional_specification_correction`;
-   `unsupported_legacy_behavior`; or
-   `unresolved_discrepancy`.

An unresolved discrepancy blocks certification. Renewing a historical fixture
does not resolve it.

## Designing a test

### Start from the controlling authority

Identify the exact specification section, contract object, profile, or
architecture invariant that owns the behavior. If no authority exists, stop and
ratify it before implementing a new language behavior.

### Choose the owning boundary

Put a test where the failure can be diagnosed without duplicating another
layer:

| Concern                           | Primary evidence                                                           |
| --------------------------------- | -------------------------------------------------------------------------- |
| Semantic grammar and formatting   | `core/tests/semantic_frontend*.rs` and authored frontend fixtures          |
| Simply construction               | `core/tests/simply*.rs` and the Simply contract checker                    |
| Frontend equivalence              | `core/tests/frontend_convergence.rs` and `tooling/frontend_convergence.py` |
| Compile orchestration             | `core/tests/frontend_orchestration.rs`                                     |
| Semantic or safety facts          | focused `core/tests/*analysis*.rs` property/integration tests              |
| Target lowering and serialization | target-specific `core/tests/*lowering*.rs` and `*serialization*.rs`        |
| Runtime behavior                  | exact-engine `core/tests/*runtime_certification.rs`                        |
| Host transport                    | affected binding Preview/adapter suite                                     |
| Historical compatibility          | migration runner and differential corpus                                   |

### Preserve structured failures

Invalid cases should assert the stable diagnostic code, severity, field path,
and relevant source location. Avoid broad exception types or message-substring
checks when the public diagnostic schema can be asserted.

### Keep expected values independent

Good expected values come from a specification fixture, a hand-authored
canonical request/result, or an independent runtime observation. Do not call a
production parser/compiler to manufacture its own golden value.

### Prove the guard

For corpus and policy checks, add at least one controlled negative that removes,
renames, or meaningfully changes required evidence and confirm that validation
fails closed.

## Golden evidence

Use golden files for stable serialized contracts, canonical formatting, or
target artifacts when a readable inline assertion would be worse. A golden
update requires:

1. the controlling behavior declaration;
2. a reviewed diff;
3. independent semantic or runtime evidence; and
4. a reason recorded in the task or commit.

Generated binding fixtures are compatibility evidence unless a specification
explicitly delegates authority to them.

## Test quality

Tests must be deterministic, isolated, and explicit about time, locale,
randomness, profile, runtime, and external inputs. Use fixed seeds for property
tests. Preserve input immutability. Keep assertions focused enough that a
failure identifies the broken contract.

Resource and security limits need boundary cases at, below, and above the
limit. Diagnostic and error paths must not leak source content beyond their
declared contract.

## Verification commands

Run the narrow owning tests first. For frontend work, the usual focused set is:

```bash
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend --locked
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend_properties --locked
cargo test --manifest-path core/internal/Cargo.toml --test frontend_orchestration --locked
cargo test --manifest-path core/internal/Cargo.toml --test frontend_convergence --locked
python3 tooling/frontend_convergence.py --check
python3 -m unittest tooling.tests.test_frontend_convergence
```

Then run the governed profile required by the change:

```bash
./strling profile local
./strling profile pr
```

Use `./strling profile full` for release-candidate certification with the exact
toolchain and runtime inputs described in [`Toolchains`](toolchains.md). A
profile failure cannot be replaced by an ad hoc command that exercises a
different implementation.

## Test charters and review

For cross-layer work, add or update the task's test charter before broad
implementation. Record the denominator, positive and negative cases,
representation exclusions, exact profiles/runtimes, and blocking taxonomy.

During review, ask:

1. Does the test trace to a controlling authority?
2. Is the expected value independent of the implementation under test?
3. Does it exercise the canonical boundary?
4. Are meaningful differences still observable?
5. Are unsupported and unresolved outcomes explicit?
6. Would a controlled semantic mutation make the test fail?

## Related documentation

-   [`Testing workflow`](testing_workflow.md)
-   [`Frontend convergence`](migration/frontend-convergence.md)
-   [`Architecture`](architecture.md)
-   [`Toolchains`](toolchains.md)
