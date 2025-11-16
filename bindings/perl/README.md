# STRling Perl Binding

This directory contains the Perl binding for STRling, a next-generation string pattern DSL and compiler.

## Status

**Current Phase**: Architecture & Core Data Structures (Task 1 - Complete)

The following components have been implemented:
- ✅ Core AST Node definitions (`lib/STRling/Core/Nodes.pm`)
- ✅ Intermediate Representation (IR) nodes (`lib/STRling/Core/IR.pm`)
- ✅ Error handling with instructional diagnostics (`lib/STRling/Core/Errors.pm`)
- ✅ Package distribution configuration (`dist.ini`)

## Directory Structure

```
bindings/perl/
├── dist.ini              # Dist::Zilla distribution configuration
├── lib/                  # Source code
│   ├── STRling.pm       # Main module entry point
│   └── STRling/
│       └── Core/
│           ├── Nodes.pm # AST node definitions
│           ├── IR.pm    # Intermediate representation nodes
│           └── Errors.pm # Error classes
├── t/                    # Tests (to be implemented in Task 2)
└── docs/                 # Documentation
```

## Dependencies

This binding uses modern Perl (5.10+) with the following dependencies:

- **Moo** (≥ 2.005000) - Modern, lightweight object system
- **Type::Tiny** (≥ 2.000000) - Type constraints and validation

## Installation

### For Development

1. Install dependencies:
   ```bash
   cpan Moo Type::Tiny
   ```

2. To use the modules in development:
   ```perl
   use lib '/path/to/STRling/bindings/perl/lib';
   use STRling::Core::Nodes;
   use STRling::Core::IR;
   use STRling::Core::Errors;
   ```

### Using Dist::Zilla (Recommended for Release)

1. Install Dist::Zilla:
   ```bash
   cpan Dist::Zilla
   ```

2. Build the distribution:
   ```bash
   cd bindings/perl
   dzil build
   ```

3. Install:
   ```bash
   dzil install
   ```

## Usage Examples

### Creating AST Nodes

```perl
use STRling::Core::Nodes;

# Create a literal node
my $lit = STRling::Core::Nodes::Lit->new(value => 'hello');

# Create a sequence
my $seq = STRling::Core::Nodes::Seq->new(
    parts => [
        STRling::Core::Nodes::Lit->new(value => 'hello'),
        STRling::Core::Nodes::Lit->new(value => 'world')
    ]
);

# Serialize to dictionary
my $dict = $seq->to_dict();
```

### Creating IR Nodes

```perl
use STRling::Core::IR;

# Create IR literal
my $ir_lit = STRling::Core::IR::IRLit->new(value => 'test');

# Create quantifier
my $quant = STRling::Core::IR::IRQuant->new(
    child => $ir_lit,
    min => 1,
    max => 'Inf',
    mode => 'Greedy'
);
```

### Working with Errors

```perl
use STRling::Core::Errors;

# Create a parse error
my $error = STRling::Core::Errors::STRlingParseError->new(
    message => 'Unexpected token',
    pos => 5,
    text => 'hello world',
    hint => 'Try using proper syntax'
);

# Get formatted error
print $error->to_formatted_string();

# Get LSP diagnostic
my $diagnostic = $error->to_lsp_diagnostic();
```

### Creating Flags

```perl
use STRling::Core::Nodes;

# Create flags from letters
my $flags = STRling::Core::Nodes::Flags->from_letters('ims');

# Or create explicitly
my $flags2 = STRling::Core::Nodes::Flags->new(
    ignoreCase => 1,
    multiline => 1
);
```

## Design Principles

This Perl binding follows the established STRling architecture:

1. **Idiomatic Perl**: Uses modern Perl idioms and best practices
2. **Moo for OOP**: Lightweight, fast object system
3. **Complete Documentation**: POD documentation for all classes and methods
4. **Structural Consistency**: Mirrors Python/JavaScript bindings in structure
5. **Comments Preserved**: All explanatory comments from Python binding retained

## Architecture

The binding is organized into three main components:

### 1. AST Nodes (`STRling::Core::Nodes`)

Represents the Abstract Syntax Tree directly from the parser:
- `Node` - Base class for all AST nodes
- `Alt`, `Seq`, `Lit`, `Dot` - Basic pattern constructs
- `CharClass`, `ClassRange`, `ClassLiteral`, `ClassEscape` - Character classes
- `Quant` - Quantifiers (*, +, ?, {n,m})
- `Group`, `Backref`, `Look` - Grouping and references
- `Anchor` - Position assertions
- `Flags` - Regex modifiers

### 2. IR Nodes (`STRling::Core::IR`)

Intermediate representation for optimization and compilation:
- `IROp` - Base class for all IR operations
- IR equivalents of all AST nodes (e.g., `IRAlt`, `IRSeq`)
- Language-agnostic representation
- Optimized for transformation and analysis

### 3. Errors (`STRling::Core::Errors`)

Rich error handling:
- `STRlingParseError` - Parse errors with position tracking
- Formatted error messages with context
- LSP diagnostic support
- Beginner-friendly hints

## Roadmap

- ✅ **Task 1**: Architecture & Core Data Structures (Current)
- ⏳ **Task 2**: Parser Implementation
- ⏳ **Task 3**: Compiler & IR Generation
- ⏳ **Task 4**: PCRE2 Emitter
- ⏳ **Task 5**: Simply API
- ⏳ **Task 6**: Testing & CI Integration
- ⏳ **Task 7**: Documentation & Examples
- ⏳ **Task 8**: CPAN Release

## Testing

Tests will be implemented in Task 2. The test framework will use Perl's standard `Test::More` module.

```bash
# Run tests (when implemented)
prove -lv t/
```

## Contributing

This binding is part of the STRling project. Please see the main project README for contribution guidelines.

## License

MIT License - Same as the main STRling project.

## See Also

- [Main STRling Repository](https://github.com/TheCyberLocal/STRling)
- [Python Binding](../python/)
- [JavaScript Binding](../javascript/)
- [STRling Specification](../../spec/)
