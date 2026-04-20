# STRling AI Orchestration Matrix

STRling is a polyglot regex DSL compiler with 17 language bindings. To maintain the hermetic context and architectural integrity of the STRling engine, you MUST load the specific instruction sets based on the active objective:

- **For API Design & Fluent Interfaces:** Load `instructions/philosophy.instructions.md`
- **For AST, Parsing, or Core Logic:** Load `instructions/architecture.instructions.md`
- **For Validation & Parity Checks:** Load `instructions/testing.instructions.md`
- **For Documentation, Inline Comments, & Pedagogy:** Load `instructions/documentation.instructions.md`
- **For PRs & Error Handling:** Load `instructions/workflow.instructions.md`

Do not execute implementation tasks without ingesting the appropriate bounded context.

---

## Routing Rules

The following rules determine which instruction file(s) to load. When a task spans multiple domains, load all applicable files.

### Philosophy (`instructions/philosophy.instructions.md`)

Load this context when the task involves:

- Designing, extending, or renaming public API methods
- Working on the Simply API or any fluent builder interface
- Reviewing user-facing naming conventions
- Evaluating whether a feature exposes raw regex to users

### Architecture (`instructions/architecture.instructions.md`)

Load this context when the task involves:

- Modifying the parser, compiler, or any emitter
- Changing AST or IR node structures
- Adding a new language binding or target engine
- Updating the grammar (`dsl.ebnf`) or semantics specification
- Working with version management or the TypeScript reference implementation

### Testing (`instructions/testing.instructions.md`)

Load this context when the task involves:

- Writing or debugging conformance, unit, semantic, or E2E tests
- Regenerating or validating golden master fixtures
- Investigating cross-binding parity failures
- Running the Omega Audit or interpreting its output

### Documentation (`instructions/documentation.instructions.md`)

Load this context when the task involves:

- Writing or updating files under `docs/`
- Adding or standardizing docstrings, JSDoc, XML docs, or rustdoc comments
- Adding module-level pedagogy headers or inline architectural comments
- Evaluating whether code changes require synchronous documentation updates

### Workflow (`instructions/workflow.instructions.md`)

Load this context when the task involves:

- Preparing a Pull Request or responding to review feedback
- Writing or improving error messages and parser hints
- Creating contributor-facing Issues or task scaffolding
- Modifying CLI tooling output or audit feedback messages

---

## Quick Reference

| Resource                 | Path                             |
| ------------------------ | -------------------------------- |
| Reference Implementation | `bindings/typescript/`           |
| Golden Master Fixtures   | `tests/spec/*.json`              |
| Grammar                  | `spec/grammar/dsl.ebnf`          |
| Semantics                | `spec/grammar/semantics.md`      |
| Documentation Hub        | `docs/index.md`                  |
| Omega Audit              | `tooling/audit_omega.py`         |
| Version SSOT             | `bindings/python/pyproject.toml` |
| Version Sync             | `tooling/sync_versions.py`       |

> All instruction file paths above are relative to `.github/`.
