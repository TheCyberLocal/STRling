# STRling - Python Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
pip install STRling
```

## 🚀 Usage

```python
from STRling.core.parser import parse
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit as emit_pcre2

# 1. Parse
src = "hello"
flags, ast = parse(src)

# 2. Compile
ir_root = Compiler().compile(ast)

# 3. Emit
regex = emit_pcre2(ir_root, flags)
print(f"Regex: {regex}")
```

## 📚 Documentation

See the [API Reference](docs/api_reference.md) for detailed documentation.

## ✨ Features

*   **Clean Syntax**: Write regex in a readable, object-oriented way.
*   **Type Safety**: Catch errors at compile time (where applicable).
*   **Polyglot**: Consistent API across all supported languages.
*   **Standard Features**:
    *   Quantifiers (Greedy, Lazy)
    *   Groups (Capturing, Non-capturing, Named)
    *   Character Classes
    *   Anchors
    *   Lookarounds (Positive/Negative Lookahead/Lookbehind)
