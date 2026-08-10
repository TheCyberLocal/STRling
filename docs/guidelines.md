# Contribution & Documentation Guidelines

[← Back to Developer Hub](index.md)

## Authority

Contributors follow the
[`Engineering Constitution`](../governance/ENGINEERING_CONSTITUTION.md) and
[`authority hierarchy`](../governance/authority.md). A ratified specification
or expressly normative versioned contract defines behavior. Reference
implementations, tests, generated fixtures, and tutorials do not.

TypeScript is transitional compatibility evidence, not the logic source of
truth. `bindings/python/pyproject.toml` is the current operational source for
package-version synchronization only.

## Change workflow

1. Declare task scope and every affected semantic, public API, schema,
   diagnostic, target, architecture, and generated surface.
2. Identify the controlling specification, contract, architecture decision, or
   explicit compatibility decision.
3. Add independent conformance or regression evidence.
4. Implement without creating a new semantic authority.
5. Run focused tests and canonical hardgates.
6. Record preserved behavior, transitions, and readiness.

Generated files are changed through their registered producers. A generated
diff is evidence to review, not approval.

## Verification

Before review, run the operations required by the active task, including:

```bash
./strling format --check all
./strling hygiene
BUNDLER_VERSION=2.4.20 ./strling lint all
./strling typecheck all
./strling generate --check
./strling contracts --check
./strling governance
BUNDLER_VERSION=2.4.20 ./strling check all
BUNDLER_VERSION=2.4.20 ./strling certify all
```

The aggregates cover host bindings and repository hardgates. Host-binding count
does not represent regex-target support.

## Commit standards

Use meaningful Conventional Commit subjects such as `feat:`, `fix:`, `docs:`,
`refactor:`, `test:`, or `chore:`. Permanent artifacts and commit subjects
describe the capability, not a temporary campaign.

## Documentation

`docs/index.md` is the contributor hub. Product, authority, architecture,
terminology, and specification entry documents should be linked rather than
reinterpreted.

Write for a capable developer unfamiliar with compiler theory. Define terms on
first use, distinguish source dialects from target output, distinguish host
adapters from target engines, and label historical/transitional material.

Documentation explains normative sources; it cannot create behavior. Correct a
conflict or mark it historical/transitional.

## Task scaffolding and tooling feedback

A contained task provides exact scope, controlling authority, expected files,
verification, and compatibility evidence without predetermining unratified
design.

Tool failures should state the failure, explain the constraint, and direct the
next action. Prefer semantic explanations to raw engine traces when available.
