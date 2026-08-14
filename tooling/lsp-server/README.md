# STRling Language Server And VS Code Extension

This directory is the single source of truth for the STRling editor integration
stack: the hand-authored Python language server, the VS Code client, and the
hermetic build pipeline that assembles a disposable extension payload under
`dist/`.

## Source Layout

-   `server/server.py` is the canonical Python entrypoint for the language server.
-   `server/canonical_core.py` is the bounded process adapter and exact
    `CompileResult`/LSP position projector used by diagnostics and hover.
-   `server/canonical_intelligence.py` validates bounded canonical editor
    evidence for completion, navigation, formatting, tokens, and certified
    rewrites.
-   `server/island_extractor.py` is the governed, fail-closed host-source
    coordinate adapter; the top-level `island_extractor.py` only re-exports it.
-   `client/extension.ts` launches the bundled server with an explicit `cwd` and
    `PYTHONPATH`, and auto-detects `python3` or `python` when the user has not
    configured a command override.
-   `package.json`, `language-configuration.json`, and this `README.md` are the
    metadata templates copied into `dist/`.
-   `assemble.sh` is the authoritative assembly pipeline. `build_extension.sh`
    remains only as a compatibility wrapper.

The assembly step copies the authored `package.json` into `dist/` as-is so the
packaged manifest already points `main` at `./out/extension.js`, keeps the
repository metadata in a string form for Marketplace validation, and relies on
`.vscodeignore` for VSIX payload selection. It also refuses to package if
`strling-icon.png` is not a 128x128 PNG.

## Hermetic Build Pipeline

Build the extension from this directory:

```bash
cd tooling/lsp-server
npm install
npm run assemble
npm run package
```

Each build starts from an empty `dist/` folder and then:

1. Copies extension metadata into `dist/` without rewriting the manifest.
2. Copies `server/server.py` and `server/island_extractor.py` into `dist/server/`.
3. Vendors `pygls`, `lsprotocol`, and the local `bindings/python` package into
   `dist/server/libs/`.
4. Bundles `client/extension.ts` into `dist/out/extension.js` with `esbuild`.
5. Packages only the runtime payload from `dist/` into `dist/vscode-strling.vsix`.

The resulting VSIX is hermetic with respect to Python modules: the packaged
server resolves `pygls`, `lsprotocol`, and `STRling` from `server/libs/`
without requiring global `pip` installs.

## Runtime Behavior

The Python bootstrap at the top of `server/server.py` inserts `libs/` at
`sys.path[0]` before importing transport and canonical adapter modules. On
import failure it emits a forensic stderr report that includes:

-   the resolved server path
-   the expected vendor directory
-   the current working directory
-   the `PYTHONPATH` environment value
-   the full `sys.path` matrix

In source-tree runs, the same bootstrap also falls back to the local shim
packages under `tooling/lsp-server/` so tests can execute without building a
VSIX first.

The authored server does not import the Python binding. Diagnostics and hover
execute the canonical `strling-kernel` process and consume its immutable
`CompileResult`.
Set `STRLING_KERNEL` to an explicit executable when needed; source-tree runs
also discover a built debug or release kernel. Regex-compatible islands use the
canonical `import` route, while Semantic STRling documents use `compile`.
Compiler diagnostics retain their canonical code, severity, message, order,
and UTF-8 byte span. The adapter projects spans into the negotiated UTF-8,
UTF-16, or UTF-32 LSP coordinate system; UTF-16 remains the default.

Hover is a deterministic view over the current cached canonical result. It
selects the narrowest containing Semantic IR node and renders only evidence
present in that result. It does not guess helpers or compile an independent
PCRE2 preview. Source is limited to 1 MiB, diagnostics and host islands to 256,
and each compiler request to five seconds. Document versions, content,
position encoding, and exact target profile are cache inputs; superseded work
is cancelled and stale completions are discarded.

The complete canonical bridge, governed registry, and kernel executable are not
yet copied by the VSIX assembly pipeline. Shipping that complete authored set
and removing obsolete vendored compatibility payload is assigned to P16-T05. A
missing kernel or registry is therefore a reported service limitation, never a
reason to fall back to Python semantics or permissive host extraction.

Island routing operates in two modes:

-   Host-language mode scans known boundary calls such as `s.parse(...)`,
    `simply.parse(...)`, and `STRling.parse(...)`, then projects diagnostics back
    into the original TypeScript/JavaScript/Python/Rust/Java document.
-   Native `.strl` mode bypasses host extraction and compiles the document as a
    regex-compatible source. Native `*.semantic.strling` documents use the
    Semantic frontend and are the only formatting surface.

Only current native Semantic documents can expose certified
`STRL-QUALITY-0002` exact-once wrapper rewrites, and only through
`refactor.rewrite`. `STRL-SAFETY-0003`, regex-compatible sources, host islands,
stale diagnostics, processed escapes, interpolation, and ambiguous host values
remain non-actionable.

## Local Installation

## Local Development

Do not edit `dist/` directly. Treat it as a disposable build artifact.

During local development, change files under `tooling/lsp-server/` and then
rebuild the generated extension payload with:

```bash
cd tooling/lsp-server
npm run assemble
```

Use `npm run package` when you need a VSIX, and only inspect `dist/` to verify
the assembled payload.

## Local Installation

Install the generated VSIX into VS Code with:

```bash
cd tooling/lsp-server
npm run install:local
```

The install script copies the packaged payload into the active user's
versioned `~/.vscode-server/extensions/strling-lang.vscode-strling-<version>`
directory, repairs ownership to match the home directory, and clears the VSIX
cache so WSL sessions see the fresh extension without relying on `code --force`.

After installation, open a TypeScript, JavaScript, Python, Rust, Java, or
`.strl`-associated document and check the Output panel entry named
`STRling Language Server`.

## Verification

Useful checks while iterating:

```bash
cd tooling/lsp-server
python3 -m pytest tests -q
npm run assemble
npm run package
npm run install:local
python3 dist/server/server.py --help
```

P16-T04 code-action, formatting, and island tests are included in the standard
suite; generated `dist/**` remains outside authored source work.

For direct source-tree setup outside the packaged VS Code flow, see
`LSP_SETUP.md`.
