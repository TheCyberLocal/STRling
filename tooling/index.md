# tooling/ — Index of maintenance & test utilities

This file catalogs the scripts, helpers, and subdirectories under `tooling/` and gives quick guidance on what each item does and how to run or inspect it.

If you add or change tooling, please update this index so maintainers and CI contributors can find the right helpers quickly.

---

## Quick links

-   Audit & reporting: `audit_conformance.py`, `audit_precision.py`, `audit_hints.py`, `audit_bindings.sh`
-   Release helpers: `sync_versions.py`, `check_version_exists.py`
-   Migration & fixture tooling: `migrate_tests.py`, `strip_migrated_tests.py`, `js_to_json_ast/`
-   LSP & editor tooling: `lsp-server/`
-   Utilities & reports: `parse_strl.py`, `generate_final_report.py`, `generate_c_asts.sh`
-   Tests & logs: `tests/`, `test_logs/`, `TEST_REPORT.md`

---

## Scripts and tools (alphabetical)

-   `audit_bindings.sh` — Shell wrapper to run test commands across language bindings and collect logs into `audit_logs/`. Useful for cross-binding checks and CI auditing.

-   `audit_conformance.py` — Run conformance coverage checks across bindings by comparing executed test fixtures against canonical JSON AST fixtures. Produces a report of missing coverage and exits non-zero on failures.

-   `audit_hints.py` — Small interactive helper that runs the Python parser against a pattern and prints instructional hints from `STRlingParseError`. Useful when debugging parser errors and improving error messages.

-   `audit_precision.py` — Compares binding test counts against the spec baseline and generates a human-readable precision/coverage report to help triage gaps.

-   `check_version_exists.py` — Release helper to detect whether a particular package version already exists on registries (npm, PyPI, crates.io, NuGet, RubyGems, Pub.Dev, LuaRocks). Use during release automation to avoid publishing duplicates.

-   `generate_c_asts.sh` — Helper script that builds/produces C AST artifacts from parser outputs. Used by C/C++ integration tasks and tests which rely on JSON AST artifacts.

-   `generate_final_report.py` — Build a final aggregated report by reading `TEST_REPORT.md` and writing a timestamped artifact under `reports/` or repository root.

-   `migrate_tests.py` — Extract test patterns and cases from JavaScript/TypeScript tests and write them into fixtures that the `js_to_json_ast` pipeline can consume.

-   `parse_strl.py` — Command-line parsing/validation tool for STRling DSL files. Can emit JSON ASTs or run emitters to produce a target regex. Handy for local parsing, debugging, and scripting.

-   `strip_migrated_tests.py` — Cleanup helper that removes migrated `test.each` / manual tests from JS/TS files after their cases have been converted to fixtures.

-   `sync_versions.py` — Single source-of-truth version synchronization utility. Reads the canonical version (Python/pyproject or other) and updates language binding manifests (Cargo.toml, package.json, pom.xml, etc.). Supports dry-run and write modes.

-   `sync_versions.py.bak` — Backup copy of the version sync script retained for historical/debugging reference.

---

## Subdirectories and larger tooling areas

-   `js_to_json_ast/` — JS→JSON AST generator and fixtures pipeline. Use this to extract patterns from JS tests (`extract_patterns_from_js_tests.js`), generate JSON AST artifacts (`generate_json_ast.js`), verify parity with the C emitter (`verify_js_c_parity.js`), and to manage the large fixtures corpus in `js_to_json_ast/fixtures/`.

    -   See `tooling/js_to_json_ast/README.md` for full generator workflows and environment setup (requires building the TypeScript binding).

-   `lsp-server/` — Language Server Protocol implementation and docs. Provides an LSP server that wraps the CLI diagnostics (`server.py`), examples demonstrating valid/invalid `.strl` files, vendored support libs, and README/setup docs.

    -   Key files: `server.py`, `LSP_SETUP.md`, `IMPLEMENTATION_SUMMARY.md`, `README.md`.

-   `scripts/` — Miscellaneous helper scripts for environment verification and CI maintenance tasks. Example: `scripts/verify_ecosystem.py`.

-   `tests/` — Unit tests for tooling scripts (pytest). Includes tests such as `test_sync_versions.py`, `test_audit_conformance.py`.

-   `test_logs/` — Directory containing archive logs created by tooling audit runs (e.g., `audit_bindings_rerun.log`). Inspect here when diagnosing cross-binding audit failures.

-   `__pycache__/` — Auto-generated Python bytecode cache. Not a source artifact; safe to ignore.

---

## How to use these tools (quick examples)

-   Run a cross-binding audit (bash):

```bash
./tooling/audit_bindings.sh
```

-   Generate JSON AST artifacts from fixtures (JS/TS binding required):

```bash
cd tooling/js_to_json_ast
# build typescript binding, then
node ./generate_json_ast.js fixtures/ out/
```

-   Start the LSP server (recommended to create a Python venv and install `tooling/lsp-server/requirements.txt`):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r tooling/lsp-server/requirements.txt
python tooling/lsp-server/server.py --stdio
```

---

## Maintenance notes

-   Keep this file updated whenever you add or remove tooling files. Prefer short, actionable descriptions (one line + 1–2 sentence summary).
-   Do not include auto-generated caches like `__pycache__/` or temporary build artifacts.
-   If you add major new tooling, add a short example showing how to run it and a link to a README if available.

---

If you want, I can also add a short pointer to this index in the root `README.md` or `docs/` to make it more discoverable — would you like me to do that next?

## Tooling Index

This document catalogs the main helper scripts and tools under the `tooling/` directory. It is intended as a quick-reference for contributors and maintainers so you can find audit scripts, migration tools, generation pipelines and editor integrations quickly.

If you need more detail on any item below, open its README or the script header for usage examples.

---

## Quick highlights

-   Audit & reports: `audit_conformance.py`, `audit_precision.py`, `audit_bindings.sh`, `TEST_REPORT.md` ✅
-   AST / fixture generation: `js_to_json_ast/`, `generate_c_asts.sh` 🔧
-   Migration helpers: `migrate_tests.py`, `strip_migrated_tests.py` 🔁
-   Release helpers: `sync_versions.py`, `check_version_exists.py` 📦
-   Editor tooling: `lsp-server/` (LSP server and examples) 🧑‍💻
-   Misc: `parse_strl.py`, `scripts/verify_ecosystem.py` 📝

---

## Audits & reports

-   `tooling/audit_conformance.py` — Conformance audit runner that verifies language bindings exercise the shared JSON AST specs. Run with:

    ```bash
    python3 tooling/audit_conformance.py
    ```

-   `tooling/audit_precision.py` — Compares numeric counts of conformance tests across bindings and flags mismatches.

    ```bash
    python3 tooling/audit_precision.py
    ```

-   `tooling/audit_bindings.sh` — Shell script to run build/test across each binding and write per-binding logs under `tooling/test_logs/`.

    ```bash
    bash tooling/audit_bindings.sh
    ```

-   `tooling/TEST_REPORT.md` — Generated global test report summarising conformance across bindings. Used for human review and CI reporting.

---

## Generators & migration helpers

-   `tooling/js_to_json_ast/` — The JS → JSON AST generator pipeline. It contains generator scripts and a large set of test fixtures used to create the canonical JSON AST files consumed by other bindings. See `tooling/js_to_json_ast/README.md` for full instructions. Example invocation:

    ```bash
    node tooling/js_to_json_ast/generate_json_ast.js
    ```

-   `tooling/generate_c_asts.sh` — Convenience script which builds the JS binding and runs the AST generator to produce C-compatible JSON fixtures.

    ```bash
    bash tooling/generate_c_asts.sh
    ```

-   `tooling/migrate_tests.py` — Helper to migrate tests (e.g., converting TypeScript manual tests into fixtures).

    ```bash
    python3 tooling/migrate_tests.py path/to/testfile.ts output_dir/
    ```

-   `tooling/strip_migrated_tests.py` — Remove migration-specific scaffolding (e.g. `manual()` wrappers) from TypeScript tests during migration workflows.

    ```bash
    python3 tooling/strip_migrated_tests.py path/to/testfile.ts
    ```

Note: `tooling/js_to_json_ast/fixtures/` contains many fixture files (pattern sources). The index intentionally groups these rather than listing each file individually.

---

## LSP (editor) tooling

-   `tooling/lsp-server/` — The Python LSP implementation used for editor integration (live diagnostics, hints). Key files:

    -   `tooling/lsp-server/README.md` — setup and integration notes
    -   `tooling/lsp-server/server.py` — main entrypoint for running the LSP server

    Typical usage:

    ```bash
    pip install -r tooling/lsp-server/requirements.txt
    python tooling/lsp-server/server.py --stdio
    ```

    The folder contains examples under `tooling/lsp-server/examples/` which are helpful when testing editor behavior.

---

## Release & automation helpers

-   `tooling/sync_versions.py` — Maintainer tool to synchronize versions across language bindings (Python `pyproject.toml` is the canonical source-of-truth). Useful for release automation and CI.

    ```bash
    python3 tooling/sync_versions.py --help
    ```

-   `tooling/check_version_exists.py` — Verifies whether a package version exists on various registries (PyPI, npm, crates.io, etc.). Example:

    ```bash
    python3 tooling/check_version_exists.py --registry pypi --package strling --version 1.2.3
    ```

---

## CLI helpers & miscellaneous

-   `tooling/parse_strl.py` — CLI wrapper around the STRling parser / emitter. Can parse `.strl` files or read from stdin and emit target regexes.

    ```bash
    python3 tooling/parse_strl.py my_pattern.strl
    echo 'pattern' | python3 tooling/parse_strl.py - --emit pcre2
    ```

-   `tooling/scripts/verify_ecosystem.py` — Small shim script used by CI/test harnesses.

---

## Tests & logs

-   `tooling/tests/` — Unit tests covering tooling scripts (run with pytest):

    ```bash
    pytest tooling/tests
    ```

-   `tooling/test_logs/` — Persisted test-run status files and logs created by audit scripts (helpful when debugging binding CI failures).

---

## Contributing notes

If you add or change tooling scripts, please:

1. Add or update a brief header docstring / README for the script so its usage is clear.
2. Add or update tests under `tooling/tests/` with an accompanying test case.
3. When adding large generated fixture sets (e.g. under `js_to_json_ast/fixtures/`), prefer to document their purpose in the parent README rather than listing every file in this index.

For general contribution guidance, see `CONTRIBUTING.md` at the repo root.

---

If you'd like the index to list every fixture file separately (the `js_to_json_ast/fixtures/` folder contains many hundreds of files), I can expand the index into a full exhaustive listing in a follow-up change — otherwise this compact grouping keeps the index maintainable and readable.
