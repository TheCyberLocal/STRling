# STRling Documentation Hub

This is the **central source of truth** for STRling's architecture, development philosophy, and contribution guidelines. This document provides the foundation for understanding how STRling is designed, built, and maintained.

## Table of Contents

- [Architectural Principles](#architectural-principles)
- [Testing Philosophy](#testing-philosophy)
- [Development Workflow](#development-workflow)
- [Contributing Guidelines](#contributing-guidelines)
- [Documentation Standards](#documentation-standards)

## Architectural Principles

STRling's architecture is governed by foundational principles that ensure consistency, reliability, and maintainability across the entire project.

### The Iron Law of Emitters

**Principle**: Every emitter must implement a predictable, testable interface with no side effects.

Emitters are the core abstraction that translate STRling's internal representation into serialized outputs (text, JSON, regex patterns). To ensure consistency and prevent duplicated logic, all emitters must adhere to the "Iron Law":

**Requirements:**

1. **Single, well-documented interface** with:
   - Concise initialization API (config + dependencies)
   - Single render/emit method accepting a canonical internal model
   - No side effects (emitters return strings/bytes or write to provided streams)
   - Deterministic output for a given model + config

2. **Shared concerns** (format helpers, validation, escaping) live in `core/` or `emitters/utils/` — not duplicated in each emitter

**Benefits:**

- New output formats are easier to add and review
- Testing is simplified: call render with a model → assert string/bytes
- Performance-sensitive emitters may provide streaming helpers without breaking the deterministic contract

**Example Structure:**

```python
class PCRE2Emitter:
    def __init__(self, config: EmitterConfig):
        self.config = config
    
    def emit(self, model: IRModel) -> str:
        # Deterministic transformation
        return self._render(model)
```

### Grammar and Semantics Alignment

**Principle**: The EBNF grammar and semantics specification are both normative and must evolve in lockstep.

STRling defines both a formal grammar (`spec/grammar/dsl.ebnf`) and normative semantics (`spec/grammar/semantics.md`). For STRling to remain portable and testable across multiple regex engines (PCRE2, ECMAScript, etc.), both must be kept synchronized.

**The Contract:**

- **EBNF Grammar** is the canonical definition of **syntax** (what is parsable)
- **Semantics Document** is the canonical definition of **behavior** (what parsed constructs mean)
- Both artifacts are versioned together and are equally authoritative

**Feature Categorization:**

- **Core features**: Portable across all supported regex engines
- **Extension features**: Engine-specific, clearly documented as such

**Any new feature must include:**

1. EBNF grammar update in `spec/grammar/dsl.ebnf`
2. Semantics update in `spec/grammar/semantics.md` (including portability rules)
3. Impact assessment on target artifact schemas in `spec/schema/`

**Benefits:**

- ✅ Eliminates drift between grammar and semantics
- ✅ Ensures every feature is backed by both parse rules and behavioral contracts
- ✅ Provides clear validation criteria for emitters and bindings
- ⚠️ Requires coordination when evolving the DSL (must touch multiple files)

See the [Specification Hub](../spec/README.md) for the complete formal specification.

### Separation of Concerns

STRling maintains a clear separation between:

- **Specification** (`spec/`): Formal grammar, semantics, and schemas
- **Core** (`core/`): Language-agnostic compiler and IR
- **Emitters** (`emitters/`): Target-specific code generators
- **Bindings** (`bindings/`): Language-specific APIs and convenience wrappers
- **Tests** (`tests/`): Validation and verification

This separation ensures:
- Changes to one component don't cascade unnecessarily
- Each component can be understood independently
- Testing can be targeted and efficient

## Testing Philosophy

STRling employs a **spec-driven, test-driven development workflow**: **specifications → tests → features**.

### The 3-Test Standard

Every feature must pass three types of tests before being considered complete:

#### 1. Unit Tests

**Purpose**: Validate individual components in isolation

- Test single functions, classes, or modules
- Mock dependencies to isolate the unit under test
- Fast execution (milliseconds)
- Located in `bindings/{language}/tests/unit/`

**Example**: Testing the `digit(n)` function parses correctly and generates expected IR

#### 2. End-to-End (E2E) Tests

**Purpose**: Validate complete workflows from user input to final output

- Test the entire compilation pipeline
- Use real dependencies (no mocking)
- Verify actual regex engine behavior
- Located in `bindings/{language}/tests/e2e/`

**Example**: Full pattern compilation, matching against test strings, extracting named groups

#### 3. Conformance Tests

**Purpose**: Ensure consistent behavior across multiple regex engines

- Run identical STRling patterns against multiple backends (PCRE2, ECMAScript, etc.)
- Assert matching behavior is identical across all engines
- Detect engine-specific quirks or incompatibilities
- Located in `tests/conformance/`

**Example**: Verify that character class `[a-z]` behaves identically in PCRE2 and JavaScript

### Combinatorial Testing

For features with multiple configuration options or edge cases:

- Generate test cases covering all meaningful combinations
- Use property-based testing where appropriate
- Document the combinatorial matrix in test design documents

### Golden Pattern Testing

For complex patterns or emitter outputs:

- Maintain "golden" reference outputs
- Compare actual output against golden files
- Version control golden files for regression detection
- Update golden files deliberately when behavior changes

### Test-Driven Development Workflow

Every feature follows this structured workflow:

1. **Specification** (`spec/`): Define syntax in EBNF and behavior in semantics
2. **Test Design** (`tests/_design/`): Create Test Charter documenting scope and test cases
3. **Test Implementation**: Write failing tests in appropriate test suites
4. **Feature Implementation**: Write minimal code to pass tests
5. **Verification**: Ensure code coverage and mutation testing pass
6. **Refinement**: Refactor for clarity and performance

See the [Test Suite Guide](../tests/README.md) for directory structure and execution details.

## Development Workflow

### Adding a New Feature

1. **Propose** the feature with use cases and examples
2. **Update specification**:
   - Add syntax rules to `spec/grammar/dsl.ebnf`
   - Add semantics to `spec/grammar/semantics.md`
   - Update schemas in `spec/schema/` if needed
3. **Design tests**:
   - Create Test Charter in `tests/_design/`
   - Define unit, E2E, and conformance test cases
4. **Implement tests**:
   - Write failing tests in appropriate test directories
   - Ensure tests follow the 3-Test Standard
5. **Implement feature**:
   - Update core compiler/IR as needed
   - Update emitters to handle new construct
   - Update bindings to expose new functionality
6. **Verify**:
   - All tests pass
   - Code coverage meets standards
   - Mutation testing shows tests are effective
7. **Document**:
   - Update binding READMEs with examples
   - Update feature registry in `spec/features.json`
8. **Review and merge**

### Fixing a Bug

1. **Reproduce** the bug with a failing test
2. **Diagnose** the root cause
3. **Fix** with minimal code changes
4. **Verify** the test now passes
5. **Check** that no other tests broke
6. **Document** if the fix changes expected behavior

### Refactoring

1. **Ensure** full test coverage exists
2. **Make changes** while keeping tests green
3. **Verify** no behavioral changes occurred
4. **Update documentation** if structure changed

## Contributing Guidelines

### Before You Start

1. Read this documentation hub thoroughly
2. Review the [Documentation Guidelines](./DOCUMENTATION_GUIDELINES.md)
3. Familiarize yourself with the [formal specification](../spec/README.md)
4. Set up your development environment

### Code Standards

- **Follow existing patterns**: Match the style and structure of existing code
- **Write tests first**: Follow the test-driven workflow
- **Keep changes minimal**: Make the smallest change that solves the problem
- **Document as you go**: Update docs in the same commit as code changes

### Pull Request Process

1. **Create a branch** from `main`
2. **Make changes** following the development workflow
3. **Run all tests** and ensure they pass
4. **Update documentation** to reflect changes
5. **Submit PR** with clear description of changes and rationale
6. **Respond to feedback** from reviewers
7. **Squash commits** if requested before merge

### Review Criteria

Pull requests are evaluated on:

- **Correctness**: Does it solve the stated problem?
- **Completeness**: Does it follow the full development workflow?
- **Testing**: Does it meet the 3-Test Standard?
- **Documentation**: Are docs updated and accurate?
- **Code quality**: Is it clear, maintainable, and minimal?
- **Specification alignment**: Does it comply with grammar and semantics?

## Documentation Standards

All documentation in this project must follow the [Documentation Guidelines](./DOCUMENTATION_GUIDELINES.md).

### Key Principles

- **DRY (Don't Repeat Yourself)**: Use hyperlinks instead of duplicating content
- **Single Responsibility**: Each document has a clearly defined scope
- **Interconnected**: Extensive use of cross-references
- **Authoritative**: Clear, declarative language
- **Maintained**: Updated in sync with code changes

### Documentation Structure

STRling's documentation is organized into five interconnected pillars:

1. **[Specification Hub](../spec/README.md)**: Formal language specification (grammar, semantics, schemas)
2. **Documentation Hub** (this file): Architecture, philosophy, and contribution guides
3. **[Test Suite Guide](../tests/README.md)**: Test directory structure and quick reference
4. **Binding READMEs**: User-facing installation and usage guides
   - [Python binding](../bindings/python/README.md)
   - [JavaScript binding](../bindings/javascript/README.md)
5. **[Documentation Guidelines](./DOCUMENTATION_GUIDELINES.md)**: Standards for all documentation

Each pillar has a specific scope to prevent overlap and duplication.

## Getting Help

- **Questions about the specification?** See the [Specification Hub](../spec/README.md)
- **Questions about testing?** See the [Test Suite Guide](../tests/README.md)
- **Questions about documentation?** See the [Documentation Guidelines](./DOCUMENTATION_GUIDELINES.md)
- **Questions about usage?** See the binding READMEs ([Python](../bindings/python/README.md) | [JavaScript](../bindings/javascript/README.md))

## Project Status and Roadmap

For the latest project status, feature roadmap, and known issues, see the main [project README](../README.md) and the [GitHub Issues](https://github.com/TheCyberLocal/STRling/issues).

## License and Contributing

STRling is open source. For licensing information and contribution guidelines, see the repository root.
