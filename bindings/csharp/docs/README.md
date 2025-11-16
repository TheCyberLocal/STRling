# STRling C# Binding

This directory contains the C# binding for STRling, a high-level regex DSL compiler.

## Project Structure

```
bindings/csharp/
├── STRling.sln                    # Solution file
├── src/STRling/                   # Main library project
│   ├── STRling.csproj            # Project file
│   ├── Strling.cs                # Main public API (Parser, Compiler stubs)
│   └── Core/                      # Core data structures
│       ├── Nodes.cs              # AST node definitions
│       ├── IR.cs                 # IR node definitions
│       └── STRlingParseError.cs  # Error handling
├── test/STRling.Tests/           # Test project
│   └── STRling.Tests.csproj      # Test project file
└── docs/                          # Documentation
```

## Building

```bash
dotnet build
```

## Testing

```bash
dotnet test
```

## Status

**Phase 1 (Complete):**
- ✅ Project structure and scaffolding
- ✅ Core data structures (Nodes, IR, Errors)

**Phase 2 (Planned):**
- Parser implementation
- Compiler implementation
- Unit tests

**Phase 3 (Planned):**
- CI/CD integration
- NuGet packaging
