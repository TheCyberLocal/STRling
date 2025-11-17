# STRling for Swift

[![Swift Version](https://img.shields.io/badge/Swift-5.9+-orange.svg)](https://swift.org)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20iOS%20%7C%20tvOS%20%7C%20watchOS-lightgrey.svg)](https://swift.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

STRling is a next-generation production-grade syntax designed as a user interface for writing powerful regular expressions (RegEx) with an object-oriented approach and instructional error handling.

## 🚀 Quick Start

This Swift binding provides a native, type-safe interface to the STRling pattern language.

### Requirements

- Swift 5.9 or later
- macOS 10.15+, iOS 13+, tvOS 13+, watchOS 6+

### Installation

#### Swift Package Manager

Add STRling to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/TheCyberLocal/STRling.git", branch: "main")
]
```

Then add it to your target dependencies:

```swift
targets: [
    .target(
        name: "YourTarget",
        dependencies: ["STRling"])
]
```

## 📚 Documentation

For complete documentation on the STRling pattern language, visit the [main documentation hub](../../docs/index.md).

## 🏗️ Architecture

The Swift binding follows Swift best practices and idioms:

- **Value Semantics**: Core data structures use `struct` for efficiency and safety
- **Type Safety**: Leverages Swift's powerful type system with `enum`s and associated values
- **Error Protocol**: Errors conform to Swift's native `Error` protocol
- **Modern Swift**: Uses modern Swift features (5.9+) for clean, idiomatic code

### Core Components

The Swift binding is organized into the following modules:

- **Core/Nodes.swift**: AST node definitions using Swift enums with associated values
- **Core/IR.swift**: Intermediate representation for language-agnostic regex constructs
- **Core/Errors.swift**: Rich error types with position tracking and instructional hints

## 🧪 Development Status

**Current Status**: Alpha (v3.0.0-alpha)

Task 1 (Architecture & Core Data Structures) is complete. The following components are available:

- ✅ Package structure and build system (Swift Package Manager)
- ✅ Core AST node definitions
- ✅ IR node definitions
- ✅ Error handling with instructional messages

Coming in future tasks:

- ⏳ Parser implementation (Task 2)
- ⏳ Compiler and validator (Task 2)
- ⏳ PCRE2 emitter (Task 2)
- ⏳ Comprehensive test suite (Task 2)
- ⏳ CI/CD integration (Task 3)

## 🛠️ Building

```bash
cd bindings/swift
swift build
```

## 🧪 Testing

```bash
cd bindings/swift
swift test
```

## 📄 License

MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🔗 Links

- [Main Project Repository](https://github.com/TheCyberLocal/STRling)
- [Documentation](../../docs/index.md)
- [Python Binding](../python/README.md)
- [JavaScript Binding](../javascript/README.md)

## 🤝 Contributing

Contributions are welcome! Please see the [contributing guidelines](../../docs/CONTRIBUTING.md) for more information.
