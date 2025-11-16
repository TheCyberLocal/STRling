# STRling Java Binding Documentation

This directory contains documentation for the STRling Java binding.

## Project Structure

```
bindings/java/
├── docs/                  # Documentation
├── pom.xml               # Maven project configuration
└── src/
    ├── main/
    │   └── java/
    │       └── com/
    │           └── strling/
    │               ├── Strling.java              # Main public class
    │               └── core/
    │                   ├── Nodes.java            # AST node definitions
    │                   ├── IR.java               # IR node definitions
    │                   └── STRlingParseError.java # Error handling
    └── test/
        └── java/
            └── com/
                └── strling/          # JUnit test directory
```

## Architecture

The Java binding follows the same architectural pattern as the Python and JavaScript bindings:

### Core Data Structures

1. **Nodes.java** - Abstract Syntax Tree (AST) node definitions
   - Represents the parsed structure of STRling patterns
   - Direct output of the parser
   - Includes: `Flags`, `Node`, `Alt`, `Seq`, `Lit`, `Dot`, `Anchor`, `CharClass`, `Quant`, `Group`, `Backref`, `Look`

2. **IR.java** - Intermediate Representation (IR) node definitions
   - Language-agnostic regex constructs
   - Intermediate layer between AST and target-specific emitters
   - Includes: `IROp`, `IRAlt`, `IRSeq`, `IRLit`, `IRDot`, `IRAnchor`, `IRCharClass`, `IRQuant`, `IRGroup`, `IRBackref`, `IRLook`

3. **STRlingParseError.java** - Rich error handling
   - Context-aware, instructional error messages
   - Position tracking with line and column information
   - LSP diagnostic support for IDE integration

## Building

```bash
# Compile the project
mvn compile

# Run tests (when available)
mvn test

# Create a JAR
mvn package

# Clean build artifacts
mvn clean
```

## Requirements

- Java 11 or higher
- Apache Maven 3.6.0 or higher

## Maven Coordinates

```xml
<dependency>
    <groupId>com.thecyberlocal</groupId>
    <artifactId>strling</artifactId>
    <version>3.0.0-alpha</version>
</dependency>
```

## License

MIT License - see the main project README for details.
