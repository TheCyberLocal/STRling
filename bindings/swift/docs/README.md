# Swift Binding Documentation

## Overview

The STRling Swift binding provides a native, type-safe interface to the STRling pattern language. It follows Swift best practices and idioms to provide a clean, modern API.

## Architecture

### Core Data Structures

The Swift binding uses modern Swift features to provide a safe and efficient implementation:

#### AST Nodes (Nodes.swift)

The Abstract Syntax Tree (AST) nodes use Swift's powerful enum system with associated values for type-safe pattern matching:

```swift
public indirect enum Node {
    case alt(Alt)
    case seq(Seq)
    case lit(Lit)
    case dot(Dot)
    case anchor(Anchor)
    case charClass(CharClass)
    case quant(Quant)
    case group(Group)
    case backref(Backref)
    case look(Look)
}
```

Each case has an associated struct that holds the specific data for that node type. This approach provides:

- Type safety: The compiler ensures correct usage
- Pattern matching: Easy traversal and transformation
- Value semantics: Efficient copying and immutability

#### IR Nodes (IR.swift)

The Intermediate Representation (IR) follows the same pattern:

```swift
public indirect enum IROp {
    case alt(IRAlt)
    case seq(IRSeq)
    case lit(IRLit)
    // ... etc
}
```

IR nodes are language-agnostic and serve as an intermediate layer between the AST and target-specific emitters.

#### Error Handling (Errors.swift)

Error handling uses Swift's native `Error` protocol:

```swift
public struct STRlingParseError: Error {
    public let message: String
    public let pos: Int
    public let text: String
    public let hint: String?
}
```

This provides:

- Native Swift error handling with `do-catch`
- Rich error messages with position tracking
- Instructional hints for learning

## Design Principles

### 1. Type Safety

The Swift binding leverages the type system to prevent errors at compile time:

- Enums with associated values for polymorphic types
- Strong typing for all parameters
- Optional types for nullable values

### 2. Value Semantics

Most data structures use `struct` rather than `class`:

- Automatic copying prevents accidental mutation
- Thread-safe by default
- Efficient memory usage

### 3. Idiomatic Swift

The code follows Swift naming conventions and best practices:

- camelCase for properties and methods
- PascalCase for types
- Descriptive names
- Comprehensive documentation comments

### 4. Access Control

The binding uses appropriate access control:

- `public` for the public API
- `internal` (default) for implementation details
- `fileprivate` where appropriate

## Usage Examples

### Working with AST Nodes

```swift
// Create a literal node
let lit = Lit(value: "hello")
let node = Node.lit(lit)

// Pattern matching
switch node {
case .lit(let literal):
    print("Literal: \(literal.value)")
case .seq(let sequence):
    print("Sequence with \(sequence.parts.count) parts")
default:
    print("Other node type")
}

// Serialize to dictionary
let dict = node.toDict()
```

### Working with Errors

```swift
do {
    // Some parsing operation that might fail
    throw STRlingParseError(
        message: "Unexpected character",
        pos: 5,
        text: "hello world",
        hint: "Expected a digit here"
    )
} catch let error as STRlingParseError {
    print(error.localizedDescription)
    // Prints formatted error with context and hint
}
```

## Future Development

The following components will be added in future tasks:

- Parser (Task 2)
- Compiler (Task 2)
- Validator (Task 2)
- Emitters (Task 2)
- Comprehensive test suite (Task 2)

## Contributing

When contributing to the Swift binding:

1. Follow Swift naming conventions
2. Add comprehensive documentation comments
3. Write unit tests for new functionality
4. Ensure all tests pass before submitting

## Additional Resources

- [Swift Language Guide](https://docs.swift.org/swift-book/)
- [Swift API Design Guidelines](https://swift.org/documentation/api-design-guidelines/)
- [Main STRling Documentation](../../../docs/index.md)
