# Formal Language Specification (Links)

[← Back to Developer Hub](index.md)

This document provides a **curated index** of all formal specification artifacts that define the STRling Domain-Specific Language (DSL). These are the authoritative sources for syntax and semantics.

---

## Overview

STRling's specification consists of multiple interconnected artifacts, each serving a specific purpose. Together, they form a complete, normative definition of the language.

For detailed information about the specification structure and principles, see the [Specification Hub](../spec/README.md).

---

## Grammar

The formal grammar defines the **syntax** of the STRling DSL using Extended Backus-Naur Form (EBNF).

### [Complete EBNF Grammar](../spec/grammar/dsl.ebnf)

This is the canonical definition of what constitutes a valid STRling pattern. All parsers must conform to this grammar.

**What you'll find:**
- Production rules for all STRling constructs
- Terminal and non-terminal definitions
- Operator precedence and associativity
- Lexical structure (tokens, whitespace, comments)

---

## Semantics

The semantics document defines the **meaning and behavior** of all STRling constructs.

### [Semantics Specification](../spec/grammar/semantics.md)

This is the canonical definition of what parsed STRling constructs mean and how they should behave across different regex engines.

**What you'll find:**
- Behavioral contracts for every language feature
- Portability rules across regex engines (PCRE2, ECMAScript, etc.)
- Core features vs. extension features
- Emitter requirements and conformance criteria
- Examples demonstrating expected behavior

---

## JSON Schemas

JSON schemas define the structure of intermediate representations and target artifacts.

### [Base Schema](../spec/schema/base.schema.json)

Defines the core schema for STRling's Intermediate Representation (IR).

**What you'll find:**
- IR node type definitions
- Required and optional fields for each node type
- Validation rules for IR structures
- Type constraints and enumerations

### [PCRE2 v1 Schema](../spec/schema/pcre2.v1.schema.json)

Defines the target artifact schema for the PCRE2 emitter.

**What you'll find:**
- Output format specification for PCRE2 patterns
- Metadata fields and their constraints
- Version compatibility information
- Extension points for PCRE2-specific features

---

## Feature Registry

The feature registry tracks all STRling features and their implementation status.

### [Feature Registry](../spec/features.json)

A comprehensive, machine-readable list of all language features with metadata.

**What you'll find:**
- Complete feature inventory
- Implementation status (planned, in-progress, complete)
- Target engine support matrix
- Feature categorization (core, extension, experimental)
- Version information for when features were introduced

---

## Specification Principles

### Grammar and Semantics Alignment

The EBNF grammar and semantics document are **both normative** and must evolve in lockstep:

- **Grammar** defines _what is parsable_ (syntax)
- **Semantics** defines _what parsed constructs mean_ (behavior)

For complete details, see the Grammar and Semantics Alignment principle in the Architectural Principles document (accessible via the Developer Hub).

### Any New Feature Must Include

1. EBNF grammar update in `spec/grammar/dsl.ebnf`
2. Semantics update in `spec/grammar/semantics.md`
3. Impact assessment on schemas in `spec/schema/`
4. Feature registry update in `spec/features.json`

---

## Using the Specification

### For Language Designers

When adding or modifying features:
1. Update the EBNF grammar with new syntax rules
2. Update the semantics document with behavioral definitions
3. Update or add JSON schemas if the change affects IR or artifacts
4. Update the feature registry to track the new feature

### For Emitter Implementers

Emitter implementations must conform to:
- The syntax rules defined in the grammar
- The behavioral contracts defined in the semantics
- The schema constraints defined in the JSON schemas

See the Iron Law of Emitters section in the Architectural Principles document (accessible via the Developer Hub) for emitter design principles.

### For Binding Developers

When implementing STRling bindings:
- Parse according to the grammar specification
- Implement behavior according to the semantics specification
- Generate output that conforms to the target schema
- Validate against the feature registry for completeness

---

## Related Documentation

- **[Developer Hub](index.md)**: Return to the central documentation hub for architecture, guidelines, and more
- **[Specification Hub](../spec/README.md)**: Detailed specification overview
