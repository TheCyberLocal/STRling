# STRling Workflow — Contribution and Pedagogical Diagnostics

> **Scope:** Contributor workflow, PR verification, error-message standards, and
> tooling feedback.

## Instructional errors

Every error should state what failed, explain the constraint, and direct the
next action. Prefer semantic explanations over native engine traces when the
compiler can provide them. Never swallow malformed input into an implicit
fallback.

Existing binding error types and exact `expected_hint` values remain public
compatibility obligations. The TypeScript HintEngine is their transitional
fixture producer, not normative diagnostic authority. New canonical diagnostic
behavior requires a versioned contract and independent cases before
implementation.

Write for a capable developer who may be unfamiliar with compiler and regex
terminology. Define AST, IR, profile, lowering, and emitter when first used.

## Pull requests

Every behavior change requires tests appropriate to its scope. Bug fixes include
a reproducer; refactors preserve existing evidence; semantic changes begin with
the controlling specification or contract.

Before submitting:

```bash
./strling test <binding>
./strling generate --check
./strling contracts --check
./strling governance
BUNDLER_VERSION=2.4.20 ./strling check all
BUNDLER_VERSION=2.4.20 ./strling certify all
```

Certification covers the configured host-language bindings and repository
hardgates. A count of certified bindings is not a count of regex targets.

Do not use the legacy Omega report as a substitute for the canonical `check` and
`certify` aggregates. Historical audit output remains evidence only.

## Commit standards

Use Conventional Commits with a meaningful permanent subject:

-   `feat:` product or governance capability;
-   `fix:` defect correction;
-   `docs:` documentation;
-   `refactor:` behavior-preserving implementation change;
-   `test:` test correction or addition; and
-   `chore:` auxiliary maintenance.

## Task scaffolding

Contained tasks identify exact scope, change classes, controlling authority,
expected files, verification, and compatibility evidence. Provide concrete
entry points and tests without predetermining unratified semantic design.

## Anti-regression rules

-   Do not designate a host binding or generated fixture as semantic authority.
-   Do not bypass specification/contract review for semantic behavior.
-   Do not surface raw target traces when a semantic explanation exists.
-   Do not merge with failed or unavailable enforced hardgates.
-   Preserve exact transitional diagnostics until a contained versioned decision
    authorizes change.
