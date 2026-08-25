# STRling Testing Workflow

[← Back to Developer Hub](index.md)

This workflow turns a declared behavior change into reviewable evidence without
creating a second semantic implementation.

## The canonical rule

The Rust kernel owns semantic execution. Semantic STRling, Simply, source-less
Semantic IR, and regex-compatible imports enter that one pipeline. No binding
implementation, generated fixture, target regex spelling, or runtime wrapper is
the reference semantics.

Use the authoring hierarchy consistently:

1. **Semantic STRling** for flagship textual intent;
2. **Simply** for programmatic semantic construction; and
3. **regex-compatible source** only for explicit import or migration evidence.

The shared
[`frontend-convergence corpus`](migration/frontend-convergence.md) proves that
equivalent intent reaches the same representation-neutral canonical result.

## 1. Classify the change

Before editing code, identify every affected boundary:

-   specification grammar, mapping, or diagnostic;
-   serialized contract or schema;
-   Semantic or Simply frontend;
-   canonical semantic/safety behavior;
-   portability, rewrite, lowering, or serialization;
-   target runtime behavior;
-   host adapter or transport;
-   historical compatibility; and
-   documentation or public examples.

Also name the exact target profiles and runtimes required for the claim. A
change that does not affect a boundary should not rewrite its evidence.

## 2. Confirm authority and starting state

Read the controlling specification, contracts, architecture decisions, task
record, and preceding certified commit. Confirm the worktree state before
making changes.

If behavior has no controlling authority, ratify it first. Tests may reveal a
gap, but passing implementation output cannot fill a specification gap.

## 3. Write independent evidence

Add the narrowest evidence that would fail for the intended missing or broken
behavior:

-   authored positive and negative frontend fixtures;
-   exact schema/contract cases;
-   hand-authored Semantic or Simply requests;
-   component and fixed-seed property tests;
-   canonical pipeline integration cases;
-   exact-profile target/runtime observations; or
-   classified historical differential cases.

Do not generate expected Semantic IR, diagnostics, or artifacts by calling the
production path that the test is meant to validate.

For a new frontend construct or Simply operation, extend completeness evidence
fail-closed. The corpus must continue to cover every ratified mapping,
operation, and supported legacy construct family.

## 4. Implement at the owning boundary

Make the smallest coherent implementation change:

-   frontend syntax and formatting stay bounded to frontend modules;
-   Simply remains a construction layer over the host-neutral protocol;
-   semantic behavior belongs in the canonical kernel;
-   target differences enter through explicit capability profiles;
-   adapters serialize requests and preserve canonical results/errors; and
-   historical runners remain isolated, non-normative witnesses.

Do not duplicate canonical semantics in a binding to make an adapter test pass.

## 5. Run focused verification

Start with the directly affected suites. For Semantic/frontend work:

```bash
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend --locked
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend_properties --locked
cargo test --manifest-path core/internal/Cargo.toml --test frontend_orchestration --locked
cargo test --manifest-path core/internal/Cargo.toml --test frontend_convergence --locked
python3 tooling/semantic_strling_contract.py
python3 tooling/frontend_convergence.py --check
python3 -m unittest tooling.tests.test_frontend_convergence
```

For Simply or a host adapter, add the owning Rust Simply suites and the affected
Preview/adapter suite. For target behavior, add the corresponding capability,
lowering, serialization, and exact-runtime certification tests.

Always finish the focused pass with formatting and patch checks:

```bash
./strling format repository
./strling format repository --check
git diff --check
```

## 6. Compare the right values

Frontend equivalence compares normalized Semantic IR, semantic/safety facts,
structured diagnostics, portability decisions, rewrites, and target artifacts.
Only the locked identity and source/provenance fields may be excluded.

Target conformance compares runtime observations under exact profiles. Regex
text alone is insufficient because two spellings may be equivalent and one
spelling may behave differently across engines.

Historical comparisons use the governed taxonomy:

-   `preserved_behavior`;
-   `intentional_specification_correction`;
-   `unsupported_legacy_behavior`; or
-   `unresolved_discrepancy`.

`unresolved_discrepancy` is blocking. Updating a fixture or broadening a
normalization rule is not a resolution.

## 7. Run governed profiles

After focused checks pass, run the profiles required by the task:

```bash
./strling profile local
./strling profile pr
```

Release-candidate work also runs:

```bash
./strling profile full
```

The Full profile requires the exact toolchains and runtime binaries recorded in
[`Toolchains`](toolchains.md). Preserve its structured result; do not substitute
a nearby local version or a hand-selected subset.

Run the governed migration differential when canonical or compatibility-facing
behavior changes. Repeat it as required by the task to demonstrate deterministic
classification.

## 8. Review and commit

Before each checkpoint commit:

1. inspect the complete diff and untracked-file set;
2. confirm the task record lists every changed path;
3. verify no generated output or local cache is accidentally included;
4. record exact commands, counts, profiles, fingerprints, and dispositions;
5. run governance and documentation integrity checks; and
6. use a domain-oriented commit subject.

Prefer progressive commits for contract/design, implementation/evidence,
documentation, and final certification. A task closes only after its clean-state
verification and evidence synchronization are complete.

## Host adapter contributions

Host APIs may use idiomatic types and names, but equivalent operations must
serialize the same versioned request and preserve canonical results and errors.
Test the adapter's construction, serialization, transport, deserialization, and
error mapping. Run another host suite only when that host is affected; language
symmetry is proved by the shared protocol and convergence corpus, not by copying
tests into every binding.

Historical binding-local parsers, compilers, ASTs, emitters, and generated
fixtures are compatibility evidence during migration. Their output must never
renew a canonical golden automatically.

## Diagnostics and LSP changes

Changes that affect diagnostics require evidence at every affected boundary:

-   the originating parser, frontend, kernel, or adapter;
-   canonical diagnostic normalization and serialization;
-   source span/path preservation; and
-   LSP conversion and an editor-facing functional test when the LSP surface is
    affected.

Assert stable code, severity, structured path, related locations, and safe
message content. Avoid depending only on exception class or prose substrings.

## Test maintenance

Keep tests deterministic and isolated. Fix the controlling implementation or
contract when a test fails; do not disable the test, loosen normalization, or
renew expected output without classifying the change. Remove obsolete evidence
only with an explicit preservation or retirement decision.

Shared helpers may reduce setup duplication, but they must not compute both the
actual and expected semantic result. Keep fixed seeds, exact profiles, and
runtime identities visible in the test or its governed fixture.

## Review checklist

-   The behavior traces to a controlling authority.
-   Semantic STRling remains the flagship textual example.
-   Simply is presented as programmatic construction.
-   Regex-compatible source is labeled import/compatibility.
-   The canonical Rust pipeline remains the only semantic implementation.
-   Expected values are independent of the production path under test.
-   Structured diagnostics and meaningful semantic differences remain visible.
-   Target claims use exact profiles and governed runtimes.
-   Compatibility differences are classified with no unresolved entry.
-   Focused tests, required profiles, governance, documentation, and clean-state
    checks pass.

## Related documentation

-   [`Test design standard`](testing_design.md)
-   [`Frontend convergence`](migration/frontend-convergence.md)
-   [`Architecture`](architecture.md)
-   [`Toolchains`](toolchains.md)
