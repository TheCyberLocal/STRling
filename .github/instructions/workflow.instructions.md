# STRling Workflow — Contributor Process and Pedagogical Error Handling

> **Scope:** This file governs contributor workflow, PR requirements, error-message standards, and tooling feedback. It does NOT cover pipeline architecture, fluent API philosophy, or test fixture strategy.

---

## Error Handling: The Signpost Pattern

STRling mandates **Instructional Error Engineering**. Every error state — whether from the parser, a CLI tool, or an audit script — must act as a **signpost** that teaches the user what went wrong and how to fix it.

### The Failure Contract

Every error message must satisfy three requirements:

1. **State the Failure:** Clearly identify _what_ failed (e.g., "Invalid quantifier range: min exceeds max").
2. **Explain the Constraint:** Briefly explain _why_ it matters (e.g., "Quantifier ranges require min ≤ max to produce a valid match interval").
3. **Direct the Action:** Explicitly tell the user what to do next (e.g., "Swap the values so the smaller number comes first: `a{2,5}` instead of `a{5,2}`").

### Non-Negotiable Rules

- **Never dump native regex engine traces** when STRling can provide a semantic explanation instead. Users should see `"Expected a digit quantifier"` not `"Invalid token \\d{n} at position 4"`.
- **Use `STRlingParseError`** (or the binding's equivalent) with instructional messages explaining what's wrong AND how to fix it.
- **Hint Engine conformance:** Error fixtures include an `expected_hint` field. All bindings must produce hints that match the TypeScript HintEngine's output exactly.
- **No silent failures.** If a pattern is malformed, the error must be raised — not swallowed into a default or fallback.

---

## The "Junior First" Voice

All user-facing output — error messages, documentation, CLI feedback — must be written for a **junior developer who is smart but unfamiliar with compiler theory or regex internals**.

- Define technical terms (AST, IR, Emitter) on first use.
- Prefer plain language over jargon.
- Explain _why_ a decision was made, not just _what_ it is.

---

## PR Requirements

### All PRs Must Include Tests

No exceptions.

- **New features:** Unit tests (3-Test Standard minimum), E2E tests, conformance tests if portable.
- **Bug fixes:** A test that reproduces the bug (fails before the fix, passes after).
- **Refactoring:** Verification that all existing tests still pass. New tests if coverage gaps are discovered.

### Mandatory Certification

All Pull Requests **must** pass the **Omega Audit** (`python3 tooling/audit_omega.py`) returning `🟢 CERTIFIED` status for all 17 bindings before merge.

The audit validates:

- Directory structure and file naming conventions
- Test conformance pass rates across all bindings
- Zero test skips
- Zero warnings in build/test output
- Semantic verification (duplicate capture groups, invalid ranges)

### Before Submitting

```bash
# Run tests for modified bindings
./strling test <lang>

# Run full certification
python3 tooling/audit_omega.py
```

Look for `🟢 CERTIFIED` for **all 17 bindings** before requesting review.

---

## Commit Standards

STRling enforces **Conventional Commits**:

- `feat:` A new feature
- `fix:` A bug fix
- `docs:` Documentation-only changes
- `chore:` Build process or auxiliary tooling changes
- `refactor:` Code changes that neither fix a bug nor add a feature
- `test:` Adding or correcting tests

---

## The "Fill-in-the-Blank" Imperative

When creating tasks (Issues) for contributors, provide the **scaffolding** — not just the description:

1. **Target Vector:** Exact file path(s) where changes must occur.
2. **The Container:** The class or function signature.
3. **The Logic Gap:** A specific comment block indicating where the contributor's logic goes.
4. **The Verification:** A pre-written test case they can run to verify their work.

> _A task is only ready for a junior developer if the question is "How do I write this logic?" and not "Where does this file go?"_

---

## Anti-Regression Rules

- **Do not** surface raw regex engine stack traces in user-facing output when a semantic `STRlingParseError` is available.
- **Do not** merge a PR without `🟢 CERTIFIED` status from the Omega Audit.
- **Do not** bypass the Signpost Pattern. Errors that say "invalid input" without explaining why or what to do next are unacceptable.
- **Do not** write error messages that require regex knowledge to interpret.
- **No Octal Escapes:** `\0` (null byte) only. All other octal patterns are forbidden per `spec/grammar/semantics.md`.
