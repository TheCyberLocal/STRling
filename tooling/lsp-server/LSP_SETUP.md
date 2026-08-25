# STRling LSP setup

The supported VS Code path is the platform-targeted VSIX described in
`README.md`. Direct source-tree launch remains useful for editor integration
development, but it is not an alternate semantic implementation.

## Prerequisites

-   Python 3.11 or newer for the LSP transport;
-   Cargo and Rust for the canonical kernel/editor processes;
-   Node and the locked `tooling/lsp-server/package-lock.json` dependencies only
    when building the VS Code client or package.

The server has no external Python package dependencies. Do not install the
STRling Python binding or download `pygls`/`lsprotocol` to run it.

## Source-tree server

Build the two canonical processes from the repository root:

```text
cargo build --manifest-path core/internal/Cargo.toml --locked \
  --bin strling-kernel --bin strling-editor-core
```

Then launch the authored server over stdio:

```text
python tooling/lsp-server/server/server.py --stdio
```

Source-tree discovery uses the built core executables and repository-governed
Simply, standard-library, and island-boundary resources. You may instead set
`STRLING_KERNEL`, `STRLING_EDITOR_CORE`, `STRLING_SIMPLY_PROTOCOL_PATH`,
`STRLING_STDLIB_REGISTRY_PATH`, and `STRLING_ISLAND_BOUNDARIES_PATH` to explicit
paths. Missing canonical inputs are fatal; there is no binding fallback.

## VS Code package

```text
npm ci --ignore-scripts --no-audit --no-fund --prefix tooling/lsp-server
python tooling/lsp-server/package_extension.py package --target auto
code --install-extension tooling/lsp-server/vscode-strling-1.0.0-<target>.vsix
```

Replace `<target>` with the native target reported by the package command. The
extension discovers Python 3.11+ automatically unless
`strling.languageServer.command` is configured.

## Generic LSP clients

Configure the client to start this command from the repository root:

```text
python /absolute/path/to/strling/tooling/lsp-server/server/server.py --stdio
```

Use `strling` for native `.strl` documents. Host-language island support is
available for the governed C, C++, C#, Dart, F#, Go, Java, JavaScript, Kotlin,
Lua, Perl, PHP, Python, R, Ruby, Rust, Swift, and TypeScript routes when the
client forwards the corresponding LSP language ID.

Example Neovim configuration:

```lua
local configs = require('lspconfig.configs')
local lspconfig = require('lspconfig')

configs.strling = configs.strling or {
  default_config = {
    cmd = {
      'python3',
      '/absolute/path/to/strling/tooling/lsp-server/server/server.py',
      '--stdio',
    },
    filetypes = {'strling'},
    root_dir = lspconfig.util.root_pattern('.git'),
  },
}
lspconfig.strling.setup({})
```

## Verification

Run the source and package checks from the repository root:

```text
python -m pytest tooling/lsp-server/tests -q -p no:cacheprovider
python tooling/lsp-server/package_extension.py certify --target auto
```

Package certification requires a clean Git tree and performs no marketplace
publication or real-user installation.

## Troubleshooting

-   If activation reports a missing Python runtime, install Python 3.11+ or set
    `strling.languageServer.command` to an explicit executable.
-   If source-tree launch cannot find the kernel/editor executables, build both
    Cargo bins or set their environment paths explicitly.
-   If a packaged resource or process is missing or has the wrong hash, rebuild
    from a clean checkout; do not copy binding code into the payload.
-   Set `strling.trace.server` to `messages` or `verbose` for LSP transport logs.
