# STRling C++ API Documentation

## Overview

This documentation covers the C++ API for STRling, a next-generation production-grade syntax for writing powerful regular expressions.

## Core Data Structures

### AST Nodes (Abstract Syntax Tree)

Located in `include/strling/core/nodes.hpp`, these classes represent the parsed structure of STRling patterns:

#### Flags
Container for regex flags/modifiers (ignoreCase, multiline, dotAll, unicode, extended).

#### Node Classes

- **Alt**: Alternation (OR operation) - represents choice between branches
- **Seq**: Sequence (concatenation) - represents sequential matching
- **Lit**: Literal string node
- **Dot**: Wildcard character node (matches any character)
- **Anchor**: Position anchors (Start, End, WordBoundary, etc.)
- **CharClass**: Character class with items (ranges, literals, escapes)
- **Quant**: Quantifier (*, +, ?, {n,m})
- **Group**: Grouping with optional capturing
- **Backref**: Backreference to capturing groups
- **Look**: Lookahead/lookbehind assertions

#### Character Class Items

- **ClassRange**: Character range (e.g., a-z)
- **ClassLiteral**: Single literal character
- **ClassEscape**: Escape sequences (\d, \w, \s, \p{...})

### IR Nodes (Intermediate Representation)

Located in `include/strling/core/ir.hpp`, these classes represent language-agnostic regex constructs:

#### IR Operations

- **IRAlt**: Alternation operation
- **IRSeq**: Sequence operation
- **IRLit**: Literal string
- **IRDot**: Wildcard character
- **IRAnchor**: Position anchor
- **IRCharClass**: Character class with items
- **IRQuant**: Quantifier
- **IRGroup**: Grouping operation
- **IRBackref**: Backreference
- **IRLook**: Lookaround assertion

#### IR Character Class Items

- **IRClassRange**: Character range
- **IRClassLiteral**: Single character
- **IRClassEscape**: Escape sequence

### Error Handling

Located in `include/strling/core/strling_parse_error.hpp`:

#### STRlingParseError

Rich parse error class with:
- Position tracking
- Context-aware error messages
- Beginner-friendly hints
- LSP diagnostic format support

**Methods:**
- `getMessage()`: Get the error message
- `getPos()`: Get the error position
- `getText()`: Get the input text
- `getHint()`: Get the hint (if any)
- `toFormattedString()`: Get formatted error with context
- `toLspDiagnostic()`: Convert to LSP diagnostic format

## Building and Installation

See the main [README.md](../README.md) for build instructions.

## Examples (Coming in Task 2)

Parser and Compiler implementations will be added in Task 2.

## Contributing

See the main [Developer Documentation](../../../docs/index.md) for contribution guidelines.
