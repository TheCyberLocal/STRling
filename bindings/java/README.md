# STRling - Java Binding

Part of the [STRling Project](../..).

## 📦 Installation

```xml
<dependency>
    <groupId>com.thecyberlocal</groupId>
    <artifactId>strling</artifactId>
    <version>1.0.0</version>
</dependency>
```

## 🚀 Usage

```java
import com.strling.core.Parser;
import com.strling.core.Compiler;
import com.strling.emitters.Pcre2Emitter;
import com.strling.core.Nodes.Flags;
import com.strling.core.Nodes.Node;
import com.strling.core.IR.IROp;

// 1. Parse
Parser.ParseResult result = Parser.parse("hello");

// 2. Compile
Compiler compiler = new Compiler();
IROp ir = compiler.compile(result.ast);

// 3. Emit
Pcre2Emitter emitter = new Pcre2Emitter(result.flags);
String regex = emitter.emit(ir);
System.out.println(regex);
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
