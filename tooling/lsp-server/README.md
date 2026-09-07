# STRling Language Server and VS Code Extension

This directory owns the authored STRling editor adapters and the deterministic,
platform-targeted VS Code package pipeline. It does not own language semantics.
The packaged `strling-kernel` and `strling-editor-core` Rust executables remain
the only semantic engines; the Python server and TypeScript client are transport,
projection, and editor-lifecycle adapters.

## Source layout

-   `server/server.py` is the language-server entrypoint.
-   `server/canonical_core.py` projects canonical compile results into LSP
    diagnostics and hover.
-   `server/canonical_intelligence.py` validates canonical editor evidence for
    completion, navigation, symbols, tokens, actions, and formatting.
-   `server/island_extractor.py` is the governed host-source coordinate adapter.
-   `client/extension.ts` and `client/runtime.ts` activate the client, discover
    Python 3.11+, and bind the packaged processes and resources by absolute path.
-   `package_contract.json` is the closed package, target, runtime, content, and
    reproducibility contract.
-   `syntaxes/semantic-strling.tmLanguage.json` provides static Semantic STRling
    highlighting before the language server is ready.
-   `package_extension.py` is the cross-platform assembler, packager, validator,
    and clean-checkout certification command.
-   `assemble.sh` and `build_extension.sh` are compatibility wrappers around the
    Python generator.

`dist/`, `build/`, and `*.vsix` are disposable ignored outputs. Do not edit or
commit them.

## Package targets

The package contract declares four native artifacts:

| Target         | Rust host                  | CI runner        |
| -------------- | -------------------------- | ---------------- |
| `linux-x64`    | `x86_64-unknown-linux-gnu` | `ubuntu-latest`  |
| `win32-x64`    | `x86_64-pc-windows-msvc`   | `windows-latest` |
| `darwin-x64`   | `x86_64-apple-darwin`      | `macos-15-intel` |
| `darwin-arm64` | `aarch64-apple-darwin`     | `macos-latest`   |

The builder rejects undeclared targets and target/host mismatches. It does not
cross-compile a VSIX while claiming native runtime proof.

## Build and certify

Install the lockfile-governed Node build tools once, then use the package
generator without network access:

```text
npm ci --ignore-scripts --no-audit --no-fund --prefix tooling/lsp-server
python tooling/lsp-server/package_extension.py assemble --target auto
python tooling/lsp-server/package_extension.py package --target auto
```

Equivalent repository commands are available through `./strling build lsp` and
the Full/Release package-certification profile operation.

Certification requires a clean Git tree. It builds two independent payloads,
compares every payload byte, compares normalized VSIX entries, launches both
canonical Rust processes, exercises all ten advertised LSP features over stdio,
and performs isolated install, upgrade, and uninstall checks:

```text
python tooling/lsp-server/package_extension.py certify --target auto
```

CI retains the exact certified artifact and JSON evidence with:

```text
python tooling/lsp-server/package_extension.py certify \
  --target auto \
  --output artifacts/vscode-strling-1.0.0-<target>.vsix \
  --evidence artifacts/lsp-package-<target>.json
```

Certification never publishes to a marketplace and never writes into a real
VS Code profile or user home.

## Packaged runtime

The closed payload contains 21 files:

-   extension metadata, icon, license, language configuration, and bundled client;
-   the four authored Python server modules and bounded local
    `pygls`/`lsprotocol`-compatible transport subset;
-   the Simply protocol, standard-library registry, and island-boundary registry;
-   native `strling-kernel` and `strling-editor-core` executables; and
-   `strling-package-manifest.json`, containing input, content, payload, and
    manifest SHA-256 fingerprints.

The payload contains no STRling language binding, shadow parser/compiler,
external Python package, test corpus, source map, or package-manager tree.
Runtime execution is offline after the explicit build dependency install.

The extension requires a Python 3.11+ interpreter to host the LSP transport.
It probes `python3`/`python` on POSIX and `python`/`py -3` on Windows unless
`strling.languageServer.command` is configured. A missing or too-old interpreter
produces an explicit activation error; it never triggers a semantic fallback.

## Editor surface

The extension registers `.strling` as the primary Semantic STRling source
extension and retains `.strl` as the explicit regex-compatible legacy route.
Both receive static highlighting before LSP initialization; the server selects
the Semantic frontend only for `.strling` and never infers it from file content.
It also
activates on the 20 governed host-editor language IDs needed to find embedded
STRling islands without claiming those language registrations.

The packaged evidence exercises diagnostics, hover, completion, definition,
references, document symbols, semantic tokens, code actions, formatting, and
embedded-island projection. Semantic documents alone expose the certified
formatter and exact rewrite actions. Regex-compatible helpers and islands retain
their declared lexical or compatibility behavior; packaging does not strengthen
their guarantees.

## Local installation

Build a VSIX and install it through the editor CLI you intentionally selected:

```text
python tooling/lsp-server/package_extension.py package --target auto
code --install-extension tooling/lsp-server/vscode-strling-1.0.0-<target>.vsix
```

There is no repository script that mutates `~/.vscode*`, repairs user ownership,
or clears editor caches. Lifecycle certification uses only an isolated temporary
extension root.

## Development checks

```text
python -m pytest tooling/lsp-server/tests -q -p no:cacheprovider
./strling format-check lsp
./strling lint lsp
./strling typecheck lsp
git diff --check
```

See `LSP_SETUP.md` for direct source-tree editor configuration and
`docs/migration/lsp-packaging-certification.md` for the migration evidence and
known platform dispositions.
