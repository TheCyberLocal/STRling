# STRling - Dart Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
dart pub add strling
```

## 🚀 Usage

```dart
import 'package:strling/strling.dart';

// Assuming inputAst is a Map<String, dynamic>
final node = Node.fromJson(inputAst);
final ir = node.toIR();
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
