# STRling Developer Documentation Hub

This is the **central landing page** for all STRling technical documentation. Use this hub to navigate to architecture, testing standards, contribution guidelines, and formal specifications.

## Navigation

### [← Back to Project Overview](../README.md)

Return to the main STRling project overview for a high-level introduction and feature highlights.

---

## Core Documentation

### [Architectural Principles](architecture.md)

Learn about STRling's foundational design decisions, including the `parse → compile (IR) → emit` pipeline, the Iron Law of Emitters, and grammar-semantics alignment.

### Testing Documentation

STRling's testing system is organized into three specialized guides:

#### [Test Environment Setup](testing_setup.md)

Copy-pasteable commands for setting up your local test environment for Python and JavaScript bindings.

#### [Test Design Standard](testing_design.md)

The technical, normative standard for writing new tests: the 3-Test Standard, Combinatorial E2E Testing, and Golden Pattern Testing.

#### [Testing Philosophy & Workflow](testing_workflow.md)

High-level testing principles, the Iron Law of test parity, and contribution workflow requirements.

### [Contribution & Documentation Guidelines](guidelines.md)

The definitive rulebook for contributing to STRling. Covers the DRY principle, docstring standards, tone of voice, and contribution workflows.

### [Formal Language Specification (Links)](spec_links.md)

A curated index linking to the formal grammar (EBNF), semantics, and JSON schemas that define the STRling DSL.

---

## Related Documentation

- **[Specification Hub](../spec/README.md)**: Formal language specification (grammar, semantics, schemas)
- **[Test Suite Guide](../tests/README.md)**: Test directory structure and quick reference
- **[Python Binding Quick Start](../bindings/python/README.md)**: Installation and usage for Python
- **[JavaScript Binding Quick Start](../bindings/javascript/README.md)**: Installation and usage for JavaScript
