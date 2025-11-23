# STRling - C Binding

Part of the [STRling Project](../..).

## 📦 Installation

```bash
# Clone and build
make
```

## 🚀 Usage

```c
#include "strling.h"
#include <stdio.h>

int main() {
    // Currently supports compiling JSON AST to PCRE2
    const char* json_ast = "{\"type\": \"Literal\", \"value\": \"hello\"}";
    STRlingResult* result = strling_compile(json_ast, NULL);
    
    if (result->pattern) {
        printf("Regex: %s\n", result->pattern);
    }
    
    strling_result_free_ptr(result);
    return 0;
}
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
