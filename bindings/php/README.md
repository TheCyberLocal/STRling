# STRling - PHP Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
composer require strling/strling
```

## 🚀 Usage

```php
use STRling\Core\NodeFactory;
use STRling\Compiler;

$ast = NodeFactory::fromArray($input_ast);
$compiler = new Compiler();
$ir = $compiler->compile($ast);
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
