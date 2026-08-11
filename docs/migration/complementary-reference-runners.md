# Complementary Historical Reference Runners

## Purpose and authority

This work extends the controlled historical-evidence system from one TypeScript
implementation to independently versioned observational peers. It does not
replace the TypeScript runner or reinterpret any observation already captured
by it.

**Historical reference observations are non-normative evidence. Agreement among
historical implementations does not override the normative specification or
canonical Rust semantics.** One implementation cannot define another
implementation's expected result, and the absence of a runner is not evidence
that a binding agrees with TypeScript.

```text
Normative Specification
        |
        v
Canonical Rust Kernel

Historical TypeScript Runner ----\
Historical Python Runner ---------+--> Migration Evidence
Other justified reference path ---/
```

The later comparison stage, not a reference runner, owns representation
normalization, discrepancy classification, and migration disposition.

## Selection criteria

A reference path is selected only when all of the following are supported by
repository evidence:

1. It contains semantic logic independent of the existing selected runners,
   rather than a generated or thin adapter.
2. It represents behavior that historically shipped or was governed as a
   package implementation.
3. It has meaningful overlap with parser, compiler, emitter, diagnostic, or
   public API surfaces that migration will replace.
4. It can run with deterministic inputs, stable projections, contained
   failures, and a bounded implementation fingerprint.
5. It can reveal migration-relevant behavior that TypeScript evidence cannot.
6. Its additional runtime, dependency, corpus, and maintenance cost is
   proportionate to the distinct evidence it contributes.

Generated and thin bindings are never promoted into artificial independent
authorities. A source translation may contain implementation-specific defects,
but that fact alone does not justify a runner when its historical role,
execution environment, and evidentiary contribution are otherwise duplicative.

## Candidate inventory

The inventory reviewed implementation source, package metadata, tests, shared
fixtures, migration baselines, toolchain requirements, and history for all 17
binding directories plus historical migration tooling.

| Candidate                                                                               | Classification                               | Evidence and decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------------------------------------------------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TypeScript package                                                                      | Independent semantic implementation          | Existing selected runner. Hand-maintained parser, compiler, IR, PCRE2 emitter, diagnostics, package-root API, and Simply API with a locked Node dependency graph. This work preserves its protocol behavior and implementation identity.                                                                                                                                                                                                                                                                                |
| Python package                                                                          | Independent semantic implementation          | **Selected.** Hand-maintained recursive-descent parser, AST/IR compiler, PCRE2 emitter, diagnostics, validator, package root, and Python-specific Simply API. Python tests and history include binding-specific parser, emitter, API, validator, intelligence, and packaging behavior. It executes directly on Python and can expose Python-only return shapes, exception formatting, and omissions.                                                                                                                    |
| C, C++, C#, Dart, F#, Go, Java, Kotlin, Perl, PHP, Ruby, legacy Rust binding, and Swift | Partially independent implementation         | These directories contain translated or separately maintained parser/compiler/emitter code rather than thin FFI wrappers. Repository governance nevertheless identifies the family collectively as duplicated transitional binding compilers, and their conformance suites are predominantly shared-fixture/parity driven. No candidate currently has a documented uniquely important semantic or runtime path that TypeScript plus Python cannot expose at proportionate maintenance cost. Not selected for this task. |
| Lua and R bindings                                                                      | Partially independent implementation         | Both contain runtime-language parser/emitter or Simply logic and are not generated wrappers. Their current governed tests and setup focus on the same PCRE2/shared-fixture surface, with deferred dependency resolution and no demonstrated unique historical semantic path. Not selected. Runtime-engine conformance remains later target/runtime testing rather than legacy authority.                                                                                                                                |
| C compatibility facade and package entrypoints across bindings                          | Thin/generated wrapper                       | These surfaces adapt or re-export their own binding implementation and do not provide an independent semantic authority. Not selected independently from their owning implementation.                                                                                                                                                                                                                                                                                                                                   |
| Rust conformance build output and dependency lock files                                 | Thin/generated wrapper                       | `bindings/rust/build.rs` generates test source from shared fixtures; generated tests and lock files are not semantic implementations. Not selected.                                                                                                                                                                                                                                                                                                                                                                     |
| `tooling/js_to_json_ast` and implementation-derived shared fixtures                     | Runtime-only reference path                  | Historical TypeScript-oracle generation is explicitly retired as authority and retained only as transitional evidence. Its source implementation is already covered by the TypeScript runner, so a second path would duplicate evidence. Not selected.                                                                                                                                                                                                                                                                  |
| Packaged/vendored Python modules under LSP build output                                 | Not useful as independent migration evidence | These are copies or packaging artifacts of Python code, not an independently maintained implementation. The LSP's editor-only island/intelligence behavior is outside the compiler reference surface. Not selected.                                                                                                                                                                                                                                                                                                     |

The rejected classifications do not assert agreement with TypeScript or Python.
They state only that this checkpoint found no proportionate reason to wrap them
as an additional observational peer. A later task may add a narrowly scoped
runtime path if new historical evidence establishes a unique contribution.

## Selected Python surfaces

The Python implementation provides direct parser `parse` and
`parse_to_artifact`, `Compiler.compile` and `compile_with_metadata`, PCRE2
`emit` and `emit_with_diagnostics`, structured parse/compilation errors, and a
Python Simply `Pattern.__str__` pipeline. The package root exports `simply` but
does not export parser/compiler functions. Python has no faithful equivalent of
the TypeScript package-root parse operations, `simply.compileNode`, or
`simply.toRegExp`; the multi-runner contract must report those conceptual
operations as not exposed instead of fabricating adapters.

The Python fingerprint will be limited to `bindings/python/src/STRling/**/*.py`,
`bindings/python/pyproject.toml`, `bindings/python/requirements.txt`, the root
`pytest.ini` that materially configures package tests, and the actual Python
runtime version. There is no Python lock file, so the unhashed environment is
not represented as locked; exact declared dependency specifications are.

## Execution and dependency constraints

The selected Python package declares Python 3.8 or newer and uses setuptools.
Its unpinned `requirements.txt` names build, test, schema, and packaging tools;
the reference operations themselves use only the standard library and package
source. The runner will import the checked-in package through an isolated
process/source path, exclude absolute paths and stacks, and fingerprint the
actual interpreter version. It will not install, modify, or repair the package.

The TypeScript runner continues to build checked-in sources with the existing
locked TypeScript toolchain in a temporary directory. Shared orchestration may
launch both runners, but neither runner may read the other's observations or
define the other's expected output.

## Checkpoint 1 conclusion

Selected runners are the completed historical TypeScript path and the new
historical Python path. No additional runtime or binding runner is justified by
the current inventory. This is an evidentiary selection, not a semantic vote:
legacy consensus is evidence only; disagreement has no built-in disposition;
and missing runner coverage has no implied value.
