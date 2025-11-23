# STRling - Ruby Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
gem install strling
```

## 🚀 Usage

```ruby
require 'strling/nodes'
require 'strling/ir'

ast = Strling::Nodes::NodeFactory.from_json(input_ast)
ir = Strling::IR::Compiler.compile(ast)
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
