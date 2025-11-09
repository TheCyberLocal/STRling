# STRling Formal Specification

This directory contains the **formal specification** for the STRling Domain-Specific Language (DSL). The specification is the authoritative source of truth for syntax and semantics.

## Specification Components

### 1. Grammar

The formal grammar defines the syntax of the STRling DSL using Extended Backus-Naur Form (EBNF):

- **[Grammar Specification](./grammar/dsl.ebnf)**: Complete EBNF definition of STRling syntax

### 2. Semantics

The semantics document defines the meaning and behavior of all STRling constructs:

- **[Semantics Specification](./grammar/semantics.md)**: Normative behavioral specification, portability rules, and emitter requirements

### 3. JSON Schemas

JSON schemas define the structure of intermediate representations and target artifacts:

- **[Base Schema](./schema/base.schema.json)**: Core schema definitions for STRling IR
- **[PCRE2 v1 Schema](./schema/pcre2.v1.schema.json)**: Target artifact schema for PCRE2 emitter

### 4. Feature Registry

The feature registry tracks all STRling features and their implementation status:

- **[Feature Registry](./features.json)**: Comprehensive list of features with metadata

## Specification Principles

### Grammar and Semantics Alignment

The **EBNF grammar** and **semantics document** are both normative and must evolve together:

- **Grammar** defines _what is parsable_ (syntax)
- **Semantics** defines _what parsed constructs mean_ (behavior)

Any new feature must include updates to both grammar and semantics. See the [Documentation Hub](../docs/README.md#architectural-principles) for details on this principle.

### Versioning

The specification is versioned as a cohesive unit. Changes to any component (grammar, semantics, or schemas) constitute a specification version change.

## Using This Specification

### For Language Designers

When adding or modifying features:

1. Update the [EBNF grammar](./grammar/dsl.ebnf) with new syntax rules
2. Update the [semantics document](./grammar/semantics.md) with behavioral definitions
3. Update or add JSON schemas if the change affects the IR or target artifacts
4. Update the [feature registry](./features.json) to track the new feature

### For Emitter Implementers

Emitter implementations must conform to:

- The **syntax rules** defined in the [grammar](./grammar/dsl.ebnf)
- The **behavioral contracts** defined in the [semantics](./grammar/semantics.md)
- The **schema constraints** defined in [schema files](./schema/)

See the [Iron Law of Emitters](../docs/README.md#architectural-principles) in the Documentation Hub for emitter design principles.

### For Binding Developers

When implementing STRling bindings:

- Parse according to the [grammar specification](./grammar/dsl.ebnf)
- Implement behavior according to the [semantics specification](./grammar/semantics.md)
- Generate output that conforms to the target [schema](./schema/)
- Validate against the [feature registry](./features.json) for completeness

## Related Documentation

- **[Documentation Hub](../docs/README.md)**: Architecture, philosophy, and contribution guides
- **[Test Suite Guide](../tests/README.md)**: Testing strategy and directory structure
- **[Documentation Guidelines](../docs/DOCUMENTATION_GUIDELINES.md)**: Standards for all documentation
