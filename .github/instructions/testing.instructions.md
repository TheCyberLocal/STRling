# STRling Testing — Specification, Compatibility, and Verification

> **Scope:** Conformance cases, compatibility fixtures, cross-binding parity,
> diagnostics evidence, and certification.

## Authority-aware testing

Semantic work follows:

1. ratified specification or reviewed draft/contract;
2. independently reviewable conformance cases;
3. implementation; and
4. certification.

Tests demonstrate behavior but do not create semantic authority. A generated
expectation cannot approve the implementation that produced it.

## Specification-authored conformance

A conformance case is normative only when a ratified specification delegates an
exact example set to it and project review accepts it. New canonical conformance
material must trace to the controlling specification or contract independently
of compiler output.

## Current shared fixtures

`tests/spec/*.json` are implementation-derived compatibility evidence. The
TypeScript binding remains their transitional producer through:

```bash
cd bindings/typescript
npm run build:specs
```

The fixture schema governs shape, including required diagnostic fields. It does
not make generated AST, IR, codegen, error, or hint values normative.

All current bindings must continue matching preserved fixtures unless a
contained, declared semantic/diagnostic/schema/target decision authorizes a
change. Cross-binding equality is a migration constraint, not proof of
specification correctness.

## Test categories

-   **Unit:** isolated component behavior.
-   **Semantic verification:** meaning and invariant checks.
-   **Specification conformance:** independently authored cases delegated by
    normative sources.
-   **Compatibility parity:** current cross-binding fixture and regression
    evidence.
-   **End to end:** authoring input through target artifact and, where
    applicable, target runtime behavior.
-   **Target conformance:** profile-specific lowering and engine behavior.

Engine-specific cases must name the target/profile scope. A host-language name
must not be used as a target identity unless it names an actual runtime profile.

## Transitional fixture changes

When contained work must update TypeScript-derived fixtures:

1. identify the higher-authority specification, contract, or explicit
   compatibility decision;
2. declare every affected semantic, diagnostic, schema, target, and generated
   surface;
3. modify the transitional producer;
4. regenerate rather than hand-edit outputs;
5. review the diff against the controlling decision; and
6. run affected binding parity plus canonical hardgates.

Regeneration alone never authorizes expected behavior.

## Verification commands

```bash
./strling test <binding>
./strling generate --check
./strling contracts --check
./strling governance
BUNDLER_VERSION=2.4.20 ./strling check all
BUNDLER_VERSION=2.4.20 ./strling certify all
```

The certification aggregate covers the configured host bindings. Its binding
count is not a count of regex targets.

## Diagnostics

Existing `expected_hint` values and duplicated hint engines remain compatibility
evidence. Until a canonical diagnostic contract and engine exist, preserve exact
public outcomes, but do not designate the TypeScript HintEngine as semantic
authority.

## Anti-regression rules

-   Do not skip required conformance or parity tests.
-   Do not hand-edit registered generated outputs.
-   Do not treat snapshots, goldens, or multiple agreeing implementations as
    normative without delegated specification authority.
-   Do not add semantic behavior to one binding without a declared controlling
    decision and migration plan.
-   Do not hide target-specific divergence; report it through target planning
    and profile-scoped evidence.
