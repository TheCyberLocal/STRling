# STRling Kotlin Binding

This directory contains the Kotlin binding for STRling, a human-readable regex language.

## Structure

```
bindings/kotlin/
├── build.gradle.kts          # Gradle build configuration
├── settings.gradle.kts        # Gradle settings
├── src/
│   ├── main/kotlin/strling/
│   │   ├── STRling.kt         # Main public API
│   │   └── core/
│   │       ├── Nodes.kt       # AST node definitions
│   │       ├── IR.kt          # Intermediate representation
│   │       └── Errors.kt      # Error classes
│   └── test/kotlin/strling/
│       └── STRlingTest.kt     # Test suite
└── docs/                      # Documentation
```

## Building

```bash
gradle build
```

## Testing

```bash
gradle test
```

## Architecture

The Kotlin binding follows these design principles:

- **Sealed Classes**: Used for polymorphic node hierarchies (Node, IROp, ClassItem, IRClassItem)
- **Data Classes**: Used for all concrete node types to provide automatic `equals()`, `hashCode()`, `toString()`, and `copy()`
- **Idiomatic Kotlin**: Leverages Kotlin's type system and language features for clean, safe code
- **Documentation**: All public APIs are documented with KDoc comments

## Core Components

### Nodes.kt
Defines the Abstract Syntax Tree (AST) node classes that represent the parsed structure of STRling patterns.

### IR.kt
Defines the Intermediate Representation (IR) node classes that serve as a language-agnostic representation between the AST and target regex emitters.

### Errors.kt
Provides rich error handling with position tracking and instructional hints for better developer experience.

## Development Status

This is the initial architecture setup. The following components are planned for future releases:
- Parser
- Compiler
- Validator
- Target emitters (PCRE2, etc.)
