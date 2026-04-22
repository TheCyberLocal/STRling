# STRling Language Server And VS Code Extension

This directory is the single source of truth for the STRling editor integration
stack: the hand-authored Python language server, the VS Code client, and the
hermetic build pipeline that assembles a disposable extension payload under
`dist/`.

## Source Layout

- `server/server.py` is the canonical Python entrypoint for the language server.
- `server/island_extractor.py` is the compatibility shim for island extraction.
- `client/extension.ts` launches the bundled server with an explicit `cwd` and
  `PYTHONPATH`, and auto-detects `python3` or `python` when the user has not
  configured a command override.
- `package.json`, `language-configuration.json`, and this `README.md` are the
  metadata templates copied into `dist/`.
- `assemble.sh` is the authoritative assembly pipeline. `build_extension.sh`
  remains only as a compatibility wrapper.

## Hermetic Build Pipeline

Build the extension from this directory:

```bash
cd tooling/lsp-server
npm install
npm run assemble
npm run package
```

Each build starts from an empty `dist/` folder and then:

1. Copies extension metadata into `dist/`.
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
`sys.path[0]` before importing transport or STRling modules. On import failure
it emits a forensic stderr report that includes:

- the resolved server path
- the expected vendor directory
- the current working directory
- the `PYTHONPATH` environment value
- the full `sys.path` matrix

In source-tree runs, the same bootstrap also falls back to the local shim
packages under `tooling/lsp-server/` so tests can execute without building a
VSIX first.

Island extraction now operates in two modes:

- Host-language mode scans known boundary calls such as `s.parse(...)`,
  `simply.parse(...)`, and `STRling.parse(...)`, then projects diagnostics back
  into the original TypeScript/JavaScript/Python/Rust/Java document.
- Pure `.strl` mode bypasses boundary regexes and treats each source line as a
  standalone STRling island so unterminated constructs stay clamped to the line
  being edited instead of bleeding to the file EOF.

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
python3 -m pytest tests/test_lsp_server.py -v
npm run assemble
npm run package
npm run install:local
python3 dist/server/server.py --help
```

For direct source-tree setup outside the packaged VS Code flow, see
`LSP_SETUP.md`.
