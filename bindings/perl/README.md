# STRling - Perl Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
cpanm STRling
```

## 🚀 Usage

```perl
use STRling::NodeFactory;
use STRling::Core::Compiler;

my $ast_node = STRling::NodeFactory->from_json($input_ast);
my $ir_node = STRling::Core::Compiler->compile($ast_node);
```

## 📚 Documentation

See the [API Reference](docs/api_reference.md) for detailed documentation.

## ✨ Features

-   **Clean Syntax**: Write regex in a readable, object-oriented way.
-   **Type Safety**: Catch errors at compile time (where applicable).
-   **Polyglot**: Consistent API across all supported languages.
-   **Standard Features**:
    -   Quantifiers (Greedy, Lazy)
    -   Groups (Capturing, Non-capturing, Named)
    -   Character Classes
    -   Anchors
    -   Lookarounds (Positive/Negative Lookahead/Lookbehind)
