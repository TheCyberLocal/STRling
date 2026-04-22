# STRling Language Server

A Language Server Protocol (LSP) implementation for STRling, providing real-time diagnostics and intelligent error handling in code editors.

## Overview

This LSP server acts as a **delivery mechanism** for STRling's "Intelligent Error Handling" engine, translating rich `STRlingParseError` objects into real-time, instructional feedback within code editors like VS Code.

## Architecture

The LSP server consumes the unified Python language-intelligence core in-process — there is no longer a separate CLI subprocess shadow:

```
Editor (VS Code) ←→ LSP Server ───→ Intelligence Core ───→ Parser
                    (server.py)      (STRling.core.intelligence)   (STRling.core.parser)
```

### Key Components

1. **LSP Server** (`server.py`): Handles LSP protocol communication with editors and owns Island-Grammar dispatch.
   The local `pygls` shim now provides the actual stdio/TCP transport loop, so the server stays alive long enough to receive initialize/didOpen/didChange messages.
2. **Intelligence Core** (`../../bindings/python/src/STRling/core/intelligence.py`): The single facade that produces diagnostics and exposes island extraction. The `tooling/parse_strl.py` CLI wraps the same module so editor diagnostics and CLI diagnostics never drift.
3. **Parser** (`../../bindings/python/src/STRling/core/parser.py`): Core parsing logic, surfaced through `STRling.core.intelligence.analyze_content`.

This separation ensures:

- A single source of truth for diagnostics across the LSP and CLI surfaces.
- Future compatibility with the Rust core implementation.
- Multi-language binding support and clear separation of concerns.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

```bash
# From the tooling/lsp-server directory
pip install -r requirements.txt

# Install STRling Python bindings in development mode
cd ../../bindings/python
pip install -e .
```

## Usage

### Standalone Server

Start the LSP server:

```bash
# Using stdio (default)
python server.py --stdio

# Using TCP
python server.py --tcp --host 127.0.0.1 --port 2087
```

### VS Code Integration

Create or update `.vscode/settings.json` in your project:

```json
{
    "strling.languageServer.enabled": true,
    "strling.languageServer.command": "python",
    "strling.languageServer.args": [
        "/path/to/STRling/tooling/lsp-server/server.py",
        "--stdio"
    ]
}
```

## Features

### ✅ Implemented (MVP)

- **Real-time Diagnostics**: Instant error detection as you type
- **Instructional Hints**: Beginner-friendly error messages with fix suggestions
- **Position Tracking**: Accurate error location with line/column info
- **Multi-line Support**: Handles patterns spanning multiple lines

### 🚧 Planned Features

- Code completion and suggestions
- Hover documentation
- Go to definition for named groups
- Symbol highlighting
- Quick fixes and refactoring

## JSON Communication Contract

The CLI server emits JSON diagnostics in LSP-compatible format:

```json
{
    "success": false,
    "diagnostics": [
        {
            "range": {
                "start": { "line": 0, "character": 4 },
                "end": { "line": 0, "character": 5 }
            },
            "severity": 1,
            "message": "Unterminated group\n\nHint: This group was opened with '(' but never closed.",
            "source": "STRling",
            "code": "unterminated_group"
        }
    ],
    "version": "1.0.0"
}
```

### Severity Levels

- `1` = Error (parse failures, syntax errors)
- `2` = Warning (deprecated features, best practices)
- `3` = Information (informational messages)
- `4` = Hint (optimization suggestions)

## Testing

See the `tests/` directory for functional tests.

```bash
# Run LSP server tests
python -m pytest tests/
```

## Development

### Adding New Features

1. Extend the intelligence core (`STRling.core.intelligence`) to expose new diagnostics
2. Update the LSP server (`server.py`) to handle new LSP capabilities
3. Add tests to validate the new functionality
4. Update documentation

### Debugging

Enable logging in VS Code:

```json
{
    "strling.trace.server": "verbose"
}
```

Check the Output panel → "STRling Language Server" for logs.

## License

MIT License - See the root LICENSE file for details.

## Contributing

Contributions are welcome! Please see the main project CONTRIBUTING guidelines.
