# STRling LSP Setup Guide

## Overview

This guide explains how to set up the STRling Language Server Protocol (LSP) for real-time diagnostics in your code editor.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A compatible code editor (VS Code, Neovim, Sublime Text, etc.)

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
```

This will install:
- `pygls` - Python Generic Language Server implementation
- `lsprotocol` - LSP protocol types

### 3. Verify Installation

Test the CLI server:

```bash
# Test with stdin
echo "(abc" | python -m STRling.cli_server --diagnostics-stdin

# Test with a file
python -m STRling.cli_server --diagnostics path/to/file.strl
```

Test the LSP server imports:

```bash
cd tooling/lsp-server
python -c "from server import server; print('LSP Server ready!')"
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
      "command": "python",
      "args": [
        "/absolute/path/to/STRling/tooling/lsp-server/server.py",
        "--stdio"
      ],
      "filetypes": ["strl", "strling"]
    }
  }
}
```

#### Option 2: Custom Extension (Future Work)

A dedicated VS Code extension is planned for future development.

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
        'python',
        '/absolute/path/to/STRling/tooling/lsp-server/server.py',
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
        "python",
        "/absolute/path/to/STRling/tooling/lsp-server/server.py",
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
- `.strl` - Recommended
- `.strling` - Alternative

You may need to configure your editor to recognize these file types.

## Features

### Current (MVP)

- ✅ **Real-time Diagnostics**: Instant error detection as you type
- ✅ **Instructional Hints**: Beginner-friendly error messages
- ✅ **Position Tracking**: Accurate error location (line/column)
- ✅ **Multi-line Support**: Handles patterns spanning multiple lines
- ✅ **Rich Error Context**: Shows error line with caret indicator

### Planned Features

- 🔨 Code completion for STRling syntax
- 🔨 Hover documentation
- 🔨 Go to definition for named groups
- 🔨 Symbol highlighting
- 🔨 Quick fixes and refactoring
- 🔨 Pattern snippets

## Diagnostic Severity Levels

The LSP server uses standard LSP severity levels:

| Level | Value | Description |
|-------|-------|-------------|
| Error | 1 | Parse failures, syntax errors |
| Warning | 2 | Deprecated features, best practices |
| Information | 3 | Informational messages |
| Hint | 4 | Optimization suggestions |

Currently, all diagnostics are reported as **Error** level.

## Troubleshooting

### LSP Server Not Starting

**Problem**: Editor shows "LSP server failed to start"

**Solutions**:
1. Verify Python is in your PATH: `python --version`
2. Check the server imports correctly:
   ```bash
   cd tooling/lsp-server
   python -c "from server import server; print('OK')"
   ```
3. Check editor logs for detailed error messages

### No Diagnostics Appearing

**Problem**: File opens but no errors are shown for invalid patterns

**Solutions**:
1. Verify file extension is `.strl` or `.strling`
2. Check the CLI server works:
   ```bash
   echo "(abc" | python -m STRling.cli_server --diagnostics-stdin
   ```
3. Check editor LSP logs (usually in Output panel)

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'STRling'`

**Solutions**:
1. Reinstall STRling in editable mode:
   ```bash
   cd bindings/python
   pip install -e .
   ```
2. Verify installation: `python -c "import STRling; print('OK')"`

### Diagnostics Too Slow

**Problem**: Diagnostics appear with significant delay

**Solutions**:
1. The CLI server has a 5-second timeout - very complex patterns may timeout
2. Consider breaking large patterns into smaller components
3. Check if your system is under high load

## Testing

Run the test suite to verify everything is working:

```bash
# Test CLI server
cd tooling/lsp-server
python -m pytest tests/test_cli_server.py -v

# Test LSP diagnostic conversion
cd ../../bindings/python
python -m pytest tests/unit/test_lsp_diagnostics.py -v

# Test LSP server
cd ../../tooling/lsp-server
python -m pytest tests/test_lsp_server.py -v
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
         │ CLI/JSON
         │ (subprocess)
         ▼
┌─────────────────┐
│   CLI Server    │
│ (cli_server.py) │
└────────┬────────┘
         │ Python API
         │
         ▼
┌─────────────────┐
│  STRling Parser │
│   (parser.py)   │
└─────────────────┘
```

This architecture ensures:
- **Binding-agnostic** design
- Future compatibility with Rust core
- Clear separation of concerns
- Easy to test and maintain

## Performance

- **Startup Time**: < 1 second
- **Diagnostic Latency**: < 100ms for typical patterns
- **Memory Usage**: ~50MB base + pattern size
- **Timeout**: 5 seconds for complex patterns

## Security

- The LSP server runs locally - no network requests
- Pattern files are only read, never modified
- No external dependencies beyond Python standard library + pygls
- Subprocess execution is restricted to the STRling CLI

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
- GitHub Issues: https://github.com/TheCyberLocal/STRling/issues
- Documentation: https://github.com/TheCyberLocal/STRling/tree/main/docs
