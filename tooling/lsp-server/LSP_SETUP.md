# STRling LSP Setup Guide

## Overview

This guide explains how to set up the STRling Language Server Protocol (LSP) for real-time diagnostics in your code editor.

## Prerequisites

-   Python 3.8 or higher
-   pip (Python package manager)
-   A compatible code editor (VS Code, Neovim, Sublime Text, etc.)

## Installation

### 1. Install STRling Python Package

```bash
# From the repository root
cd bindings/python
pip install -e .
```

### 2. Install LSP Server Dependencies

```bash
cd tooling/lsp-server
pip install -r requirements.txt
npm install
npm run assemble
```

This will install:

-   `pygls` - Python Generic Language Server implementation
-   `lsprotocol` - LSP protocol types

### 3. Verify Installation

Test the parser CLI (which now wraps the unified intelligence core):

```bash
# Parse from stdin (exit 2 + JSON error envelope on failure)
echo "(abc" | python3 tooling/parse_strl.py -

# Parse a file
python3 tooling/parse_strl.py path/to/file.strl
```

Test the LSP server imports:

```bash
cd tooling/lsp-server
python3 -c "from server.server import server; print('LSP Server ready!')"
```

## Editor Configuration

### Visual Studio Code

#### Option 1: Using Generic LSP Client Extension

1. Install the "Generic Language Server" extension
2. Create or edit `.vscode/settings.json` in your workspace:

```json
{
    "genericLanguageServer.languageConfigs": {
        "strling": {
            "command": "python3",
            "args": [
                "/absolute/path/to/STRling/tooling/lsp-server/server/server.py",
                "--stdio"
            ],
            "filetypes": ["strl", "strling"]
        }
    }
}
```

#### Option 2: Bundled STRling Extension

Build and install the repository's bundled extension:

```bash
cd tooling/lsp-server
npm install
npm run install:local
```

The local install step synchronizes the packaged extension into the active
VS Code server profile under `~/.vscode-server/extensions/`, fixes ownership,
and clears the cached VSIX metadata that can hide the new payload in WSL.

### Neovim (with nvim-lspconfig)

Add to your Neovim configuration:

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Define STRling LSP
if not configs.strling then
  configs.strling = {
    default_config = {
      cmd = {
                'python3',
                '/absolute/path/to/STRling/tooling/lsp-server/server/server.py',
        '--stdio'
      },
      filetypes = {'strl', 'strling'},
      root_dir = lspconfig.util.root_pattern('.git', 'pyproject.toml'),
      settings = {},
    },
  }
end

lspconfig.strling.setup{}
```

### Sublime Text (with LSP package)

1. Install the "LSP" package via Package Control
2. Add to your LSP settings (`Preferences > Package Settings > LSP > Settings`):

```json
{
    "clients": {
        "strling": {
            "enabled": true,
            "command": [
                "python3",
                "/absolute/path/to/STRling/tooling/lsp-server/server/server.py",
                "--stdio"
            ],
            "selector": "source.strling",
            "schemes": ["file"]
        }
    }
}
```

## File Extensions

The LSP server will automatically activate for files with these extensions:

-   `.strl` - Recommended
-   `.strling` - Alternative

You may need to configure your editor to recognize these file types.

## Features

### Current (MVP)

-   ✅ **Real-time Diagnostics**: Instant error detection as you type
-   ✅ **Instructional Hints**: Beginner-friendly error messages
-   ✅ **Position Tracking**: Accurate error location (line/column)
-   ✅ **Multi-line Support**: Handles patterns spanning multiple lines
-   ✅ **Rich Error Context**: Shows error line with caret indicator

### Planned Features

-   🔨 Code completion for STRling syntax
-   🔨 Hover documentation
-   🔨 Go to definition for named groups
-   🔨 Symbol highlighting
-   🔨 Quick fixes and refactoring
-   🔨 Pattern snippets

## Diagnostic Severity Levels

The LSP server uses standard LSP severity levels:

| Level       | Value | Description                         |
| ----------- | ----- | ----------------------------------- |
| Error       | 1     | Parse failures, syntax errors       |
| Warning     | 2     | Deprecated features, best practices |
| Information | 3     | Informational messages              |
| Hint        | 4     | Optimization suggestions            |

Currently, all diagnostics are reported as **Error** level.

## Troubleshooting

### LSP Server Not Starting

**Problem**: Editor shows "LSP server failed to start"

**Solutions**:

1. Verify Python is in your PATH: `python3 --version`
2. Check the server imports correctly:
    ```bash
    cd tooling/lsp-server
    python3 -c "from server.server import server; print('OK')"
    ```
3. Check editor logs for detailed error messages

### No Diagnostics Appearing

**Problem**: File opens but no errors are shown for invalid patterns

**Solutions**:

1. Verify file extension is `.strl` or `.strling`
2. Check the parser CLI works:
    ```bash
    echo "(abc" | python3 tooling/parse_strl.py -
    ```
3. Check editor LSP logs (usually in Output panel)

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'STRling'`

**Solutions**:

1. Rebuild the hermetic payload so `dist/server/libs` is repopulated:
    ```bash
    cd tooling/lsp-server
    npm run package
    ```
2. For direct source-tree runs, verify the binding imports:
   `python3 -c "import sys; sys.path.insert(0, 'bindings/python/src'); import STRling; print('OK')"`

### Diagnostics Too Slow

**Problem**: Diagnostics appear with significant delay

**Solutions**:

1. The LSP debounces text changes by 50 ms; very complex patterns may exceed that.
2. Consider breaking large patterns into smaller components.
3. Check if your system is under high load.

## Testing

Run the test suite to verify everything is working:

```bash
# Test island extractor + LSP integration (uses the in-process intelligence core)
cd tooling/lsp-server
python3 -m pytest tests/test_island_extractor.py tests/test_lsp_server.py -v

# Test LSP diagnostic conversion
cd ../../bindings/python
python -m pytest tests/unit/test_lsp_diagnostics.py -v

# Test LSP server
cd ../../tooling/lsp-server
python3 -m pytest tests/test_lsp_server.py -v
```

All tests should pass.

## Example Workflow

1. Create a STRling pattern file: `touch pattern.strl`
2. Open it in your editor (VS Code, Neovim, etc.)
3. Start typing a pattern:
    ```
    (hello world
    ```
4. The LSP server will immediately show an error:

    ```
    Unterminated group

    Hint: This group was opened with '(' but never closed.
    Add a matching ')' to close the group.
    ```

5. Fix the error by adding the closing parenthesis:
    ```
    (hello world)
    ```
6. The error clears automatically!

## Architecture

```
┌─────────────────┐
│   Code Editor   │
│   (VS Code)     │
└────────┬────────┘
         │ LSP Protocol
         │ (JSON-RPC)
         ▼
┌─────────────────┐
│   LSP Server    │
│   (server.py)   │
└────────┬────────┘
         │ In-process Python call
         ▼
┌─────────────────────┐
│ Intelligence Core   │
│ (STRling.core.      │
│  intelligence)      │
└────────┬───────────┘
         │ Python API
         ▼
┌─────────────────┐
│  STRling Parser │
│   (parser.py)   │
└─────────────────┘
```

This architecture ensures:

-   One single source of truth for diagnostics (shared with `tooling/parse_strl.py`)
-   **Binding-agnostic** design
-   Future compatibility with Rust core
-   Clear separation of concerns
-   Easy to test and maintain

## Performance

-   **Startup Time**: < 1 second
-   **Diagnostic Latency**: < 100ms for typical patterns (in-process, no subprocess hop)
-   **Memory Usage**: ~50MB base + pattern size

## Security

-   The LSP server runs locally - no network requests
-   Pattern files are only read, never modified
-   No external dependencies beyond Python standard library + pygls
-   Subprocess execution is restricted to the STRling CLI

## Contributing

To contribute to the LSP server:

1. Follow the main project contributing guidelines
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass before submitting PR

## License

MIT License - See the root LICENSE file for details.

## Support

For issues or questions:

-   GitHub Issues: https://github.com/strling-lang/strling/issues
-   Documentation: https://github.com/strling-lang/strling/tree/main/docs
