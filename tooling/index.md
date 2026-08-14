# tooling/ — Index of maintenance & test utilities

This file catalogs the scripts, helpers, and subdirectories under `tooling/` and gives quick guidance on what each item does and how to run or inspect it.

If you add or change tooling, please update this index so maintainers and CI contributors can find the right helpers quickly.

---

## Quick links

-   Audit & reporting: `audit_precision.py`, `audit_hints.py`, `audit_omega.py`, `audit_hint_parity.py`
-   Release helpers: `sync_versions.py`, `check_version_exists.py`
-   Fixture tooling: `js_to_json_ast/`
-   Historical evidence: legacy_reference/
-   Governance hardgates: `baseline.py`, `public_contracts.py`, `contract_declarations.py`, `architecture_fitness.py`, `generated_artifacts.py`, `governance.py`, `sync_fixture_projection.py`
-   LSP & editor tooling: `lsp-server/`
-   Utilities: `generate_c_asts.sh`
-   CLI: root `strling` wrapper and canonical Rust `strling-kernel` transport
-   Tests & logs: `tests/`, `test_logs/`

---

## Scripts and tools (alphabetical)

-   `audit_hints.py` — **Interactive Parser Debugger** for testing STRling parse error messages. Runs the Python parser against a pattern and prints the fully formatted `STRlingParseError` with instructional hints. This is a **developer-facing utility** for debugging parser errors and improving error message quality — not part of CI.

    ```bash
    # Test an invalid pattern to see error hints
    python3 tooling/audit_hints.py "[a-"
    python3 tooling/audit_hints.py "(?<name"
    python3 tooling/audit_hints.py "a{3,1}"   # invalid quantifier range
    ```

-   `audit_hint_parity.py` — **Cross-Binding Hint Parity Auditor**. Statically analyzes all binding hint engine source files and reports which of the 38 canonical error-pattern keys (from the TypeScript reference) are present or missing. Exits with code 0 for full parity, 1 for drift.

    ```bash
    python3 tooling/audit_hint_parity.py
    ```

-   `audit_omega.py` — The unified Final Certification harness. Runs the global audit and generates `docs/generated/FINAL_AUDIT_REPORT.md`.

-   `audit_precision.py` — **Ad-Hoc Analysis (Dormant)** — Compares binding test counts against the spec baseline and generates a human-readable precision/coverage report (`docs/reports/coverage_precision.md`). This tool is for **manual developer use only** and is **not part of CI/CD**. It requires all binding toolchains to be installed locally; missing toolchains will report errors or timeouts.

    ```bash
    # Run locally to check coverage across bindings
    python3 tooling/audit_precision.py
    ```

    **Note:** This tool may report 0 or errors for bindings you don't have installed — that's expected for local development environments.

-   `check_version_exists.py` — Release helper to detect whether a particular package version already exists on registries (npm, PyPI, crates.io, NuGet, RubyGems, Pub.Dev, LuaRocks). Use during release automation to avoid publishing duplicates.

-   `contract_declarations.py` — Compares governed snapshots with the active task's Git base and requires compatible, additive, breaking, or intentional-correction declarations naming exact surface identifiers.

-   `architecture_fitness.py` — Performs language-aware import, JSON Schema reference, generated-authority, transition, and new semantic-island checks for `governance.py`.
-   `baseline.py` — Validates the frozen certified migration-baseline registry, Git identities and ancestry, governed path-set fingerprints, and cross-record evidence consistency. Exposed as `./strling baseline --check [--json]` and enforced by `check` and `certify`.

-   `generate_c_asts.sh` — Helper script that builds/produces C AST artifacts from parser outputs. Used by C/C++ integration tasks and tests which rely on JSON AST artifacts.
-   `legacy_reference/` - **Controlled Historical Reference Runners**. Builds
    governed TypeScript sources into a temporary directory or imports the
    checked-in Python package directly, invokes runner-owned historical
    parser/compiler/emitter/public API surfaces without changing them, and emits
    canonical JSON observations. Shared orchestration certifies independently
    versioned runners without comparing or classifying their outputs. It is
    migration tooling only; its output is non-normative and cannot define
    compiler or target behavior.

    -   python3 tooling/legacy_reference/launch.py --request request.json
    -   python3 tooling/legacy_reference/launch.py --runner python --certify
    -   python3 tooling/legacy_reference/launch.py --corpus
    -   python3 tooling/legacy_reference/launch.py --certify
    -   python3 tooling/legacy_reference/launch.py --cross-certify
    -   ./strling legacy-reference --check

-   `generated_artifacts.py` — Validates the generated-artifact registry and either regenerates governed outputs or certifies exact committed reproduction without mutating the working tree. Exposed as `./strling generate [--check]`.

-   `governance.py` — Validates the active contained-task diff, change declarations, registered generated-output changes, and active architecture fitness rules. Exposed as `./strling governance`.

-   `public_contracts.py` — Extracts, writes, and checks deterministic public API, package-entrypoint, CLI, and stable-schema compatibility snapshots. Exposed as `./strling contracts [--check]`.

-   `strling` — The root CLI utility. Its product commands (`compile`, `import`, `explain`, `migrate`, semantic `check`, `target`, and `simply`) dispatch to the canonical Rust kernel transport; its engineering commands orchestrate repository setup, verification, generation, and certification.

-   `sync_versions.py` — Single source-of-truth version synchronization utility. Reads the canonical version (Python/pyproject or other) and updates language binding manifests (Cargo.toml, package.json, pom.xml, etc.). Supports dry-run and write modes.

-   `sync_fixture_projection.py` — Reproduces or checks the governed Swift compatibility-fixture projection from the authoritative C fixture corpus.

---

## Subdirectories and larger tooling areas

-   `js_to_json_ast/` — JS→JSON AST generator and fixtures pipeline. Use this to extract patterns from JS tests (`extract_patterns_from_js_tests.js`), generate JSON AST artifacts (`generate_json_ast.js`), verify parity with the C emitter (`verify_js_c_parity.js`), and to manage the large fixtures corpus in `js_to_json_ast/fixtures/`.

    -   See `tooling/js_to_json_ast/README.md` for full generator workflows and environment setup (requires building the TypeScript binding).

-   `lsp-server/` — Unified source-of-truth for the Python LSP server and the VS Code extension packaging pipeline. The hand-authored sources live here (`server/server.py`, `server/island_extractor.py`, `client/extension.ts`), while `assemble.sh` assembles a disposable `dist/` folder containing the vendored Python runtime and packaged VSIX payload.

    -   Key files: `server/server.py`, `client/extension.ts`, `assemble.sh`, `README.md`, `LSP_SETUP.md`.

-   `scripts/` — Miscellaneous helper scripts for environment verification and CI maintenance tasks. Example: `scripts/verify_ecosystem.py`.

-   `tests/` — Unit tests for tooling scripts (pytest). Includes tests such as `test_sync_versions.py`.

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

-   Build the VS Code extension from the unified LSP source tree:

```bash
cd tooling/lsp-server
npm install
npm run package
```

-   Start the Python LSP server directly (development path):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r tooling/lsp-server/requirements.txt
python tooling/lsp-server/server/server.py --stdio
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

-   Audit & reports: `audit_precision.py`, `audit_omega.py` ✅
-   AST / fixture generation: `js_to_json_ast/`, `generate_c_asts.sh` 🔧
-   Release helpers: `sync_versions.py`, `check_version_exists.py` 📦
-   Editor tooling: `lsp-server/` (LSP server and examples) 🧑‍💻
-   CLI: `strling` 🧰
-   Canonical product transport: `core/cli/strling-kernel.rs` 📝

---

## Audits & reports

### CI Pipeline Tool

-   `tooling/audit_omega.py` — **CI Gate** — Unified final certification audit runner. Generates `docs/generated/FINAL_AUDIT_REPORT.md`. This is the authoritative audit tool used in CI/CD pipelines.

    ```bash
    python3 tooling/audit_omega.py
    ```

### Developer-Facing Utilities (Manual Use Only)

The following tools are for **local development and debugging** — they are **not part of the CI/CD gate**.

-   `tooling/audit_hints.py` — **Interactive Parser Debugger** — Tests invalid patterns and displays formatted `STRlingParseError` messages with instructional hints. Use this when improving error messages or debugging parser behavior.

    ```bash
    python3 tooling/audit_hints.py "[a-"      # unclosed character class
    python3 tooling/audit_hints.py "(?<name"  # incomplete named group
    python3 tooling/audit_hints.py "\\k<x"    # invalid backreference
    ```

-   `tooling/audit_precision.py` — **Ad-Hoc Coverage Analysis (Dormant)** — Compares numeric counts of conformance tests across all 17 bindings and flags mismatches. Requires local toolchain installations for each binding; uninstalled bindings will report errors/timeouts.

    ```bash
    python3 tooling/audit_precision.py
    ```

    Output: `docs/reports/coverage_precision.md`

-   `tooling/TEST_REPORT.md` — Generated global test report summarising conformance across bindings. Used for human review and CI reporting.

---

## Generators & fixtures

-   `tooling/js_to_json_ast/` — The JS → JSON AST generator pipeline. It contains generator scripts and a large set of test fixtures used to create the canonical JSON AST files consumed by other bindings. See `tooling/js_to_json_ast/README.md` for full instructions. Example invocation:

    ```bash
    node tooling/js_to_json_ast/generate_json_ast.js
    ```

-   `tooling/generate_c_asts.sh` — Convenience script which builds the JS binding and runs the AST generator to produce C-compatible JSON fixtures.

    ```bash
    bash tooling/generate_c_asts.sh
    ```

Note: `tooling/js_to_json_ast/fixtures/` contains many fixture files (pattern sources). The index intentionally groups these rather than listing each file individually.

Note: `tooling/js_to_json_ast/fixtures/` contains many fixture files (pattern sources). The index intentionally groups these rather than listing each file individually.

---

## LSP (editor) tooling

-   `tooling/lsp-server/` — The Python LSP implementation used for editor integration (live diagnostics, hints). Key files:

    -   `tooling/lsp-server/README.md` — setup and integration notes
    -   `tooling/lsp-server/server/server.py` — main entrypoint for running the LSP server

    Typical usage:

    ```bash
    pip install -r tooling/lsp-server/requirements.txt
    python tooling/lsp-server/server/server.py --stdio
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

-   `strling` — Routes canonical product commands to the Rust kernel and orchestrates setup, build, test, generation, governance, and certification across the repository.

    ```bash
    ./strling import --input pattern.regex --target pcre2-10.43 --output target_artifact
    ./strling check --input pattern.semantic.strling --format human
    ./strling target list --format json
    ```

    The retired `tooling/parse_strl.py` path is not a compatibility oracle. Use
    `import` for regex-compatible source and explicit target profiles for
    artifacts; canonical contract validation is mandatory.

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
