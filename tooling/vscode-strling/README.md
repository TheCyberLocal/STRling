# vscode-strling

Reference VS Code client for the STRling Language Server.

## What it does

- Spawns `tooling/lsp-server/server.py` over stdio.
- Activates on native `.strl` files and registers for `.ts/.tsx/.js/.jsx`, `.py`, `.rs`, and `.java` host files.
- Forwards diagnostics + hovers from the Island Grammar bridge.
- Leaves host-language syntax highlighting untouched (the host LSPs remain
  authoritative).

## Local development

```bash
cd tooling/vscode-strling
npm install
npm run compile
# Press F5 in VS Code to launch an Extension Development Host.
```

## Building the `.vsix` (beta distribution)

The extension ships a pre-wired `vsce package` script. From the
`tooling/vscode-strling` directory:

```bash
npm install                # one-time
npm run package            # produces vscode-strling.vsix
```

To install the resulting bundle locally for beta testing:

```bash
code --install-extension ./vscode-strling.vsix
```

Or, inside VS Code: open the **Extensions** view, click the `…` overflow
menu, choose **Install from VSIX…** and pick the generated file. Beta
testers should also ensure `python3` (or whichever interpreter the
`strling.languageServer.command` setting points at) has the `STRling`
package importable — typically by running `pip install -e bindings/python`
from the repository root.

For pre-release marketplace channels, use `npm run package:pre-release`
(adds the `--pre-release` flag). `npm run publish` requires a Personal
Access Token with marketplace publishing rights and is reserved for the
release maintainers.

## Configuration

| Setting                          | Default                     | Purpose                               |
| -------------------------------- | --------------------------- | ------------------------------------- |
| `strling.languageServer.command` | `python`                    | Executable used to launch the server. |
| `strling.languageServer.args`    | bundled `server.py --stdio` | Arguments passed to the command.      |
| `strling.trace.server`           | `off`                       | LSP message tracing.                  |

## Definition of Done verification

1. Open a `.ts` file containing `s.parse("(abc")` — a red squiggly appears
   under the malformed pattern.
2. Open a `.py` file containing `s.parse("Email()")` and hover over `Email`
   inside the literal — STRling docs render in the hover popup.
3. Native TypeScript / Python highlighting and diagnostics from the host
   language servers continue to work unmodified.
