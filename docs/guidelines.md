# Contribution & Documentation Guidelines

[← Back to Developer Hub](index.md)

This is the **definitive rulebook** for contributing to STRling. It defines the DRY principle, docstring standards, tone of voice, and contribution workflows that all contributors must follow.

---

## Core Principles

### 1. Don't Repeat Yourself (DRY)

**Never duplicate significant bodies of text across multiple files.**

- Use hyperlinks to reference detailed information in other documents
- Each concept should have a single source of truth
- When tempted to copy/paste, create a link instead

**Examples:**
- ✅ Good: "See the [3-Test Standard](testing_design.md#the-3-test-standard) for details on our testing approach."
- ❌ Bad: Copying the entire 3-Test Standard explanation into multiple files

### 2. Single Responsibility

Each file (code or documentation) must have a clearly defined scope:

- Each module solves one problem
- Each document covers one topic
- Dependencies are explicit and minimal
- Changes to one component don't cascade unnecessarily

### 3. Hyperlinks Over Duplication

Use hyperlinks extensively to create an interconnected system:

- Link to the authoritative source when referencing concepts
- Use relative paths for internal links (e.g., `../spec/grammar/dsl.ebnf`)
- Ensure links are descriptive (e.g., "formal grammar specification" not "click here")

---

## Writing Standards

### Tone and Voice

- **Be clear and concise**: Prefer short sentences and simple language
- **Be authoritative**: Use declarative statements, not tentative language
  - ✅ "The emitter must return a string"
  - ❌ "The emitter should probably return a string"
- **Be helpful**: Anticipate reader questions and address them proactively
- **Be consistent**: Use the same terminology throughout all documents

### Formatting

#### Headers

- Use sentence case for headers (e.g., "Getting started" not "Getting Started")
- Maintain a clear hierarchy: H1 → H2 → H3
- Avoid skipping header levels

#### Lists

- Use bullet points for unordered lists
- Use numbered lists for sequential steps
- Keep list items parallel in structure

#### Code Examples

- Always include language identifiers in code blocks (```python, ```javascript, etc.)
- Provide complete, runnable examples when possible
- Include comments for complex logic
- Show both Python and JavaScript examples when documenting cross-binding features

#### Links

- Use descriptive link text that makes sense out of context
- Use relative paths for internal links
- Verify all links are working before committing

---

## Docstrings and Code Comments

### Python Docstrings

Use Google-style docstrings with complete type information and examples.

**Example:**
```python
def compile_pattern(pattern: str, flags: int = 0) -> Pattern:
    """Compile a STRling pattern to a regex Pattern object.

    Args:
        pattern: The STRling pattern string to compile
        flags: Optional regex flags to apply

    Returns:
        A compiled regex Pattern object

    Raises:
        SyntaxError: If the pattern is invalid

    Example:
        >>> pattern = compile_pattern("digit(3)")
        >>> pattern.match("123")
        <Match object>
    """
    pass
```

### JavaScript Documentation

Use JSDoc format with type annotations and examples.

**Example:**
```javascript
/**
 * Compile a STRling pattern to a RegExp object.
 *
 * @param {string} pattern - The STRling pattern string to compile
 * @param {string} flags - Optional regex flags to apply
 * @returns {RegExp} A compiled RegExp object
 * @throws {SyntaxError} If the pattern is invalid
 *
 * @example
 * const pattern = compilePattern("digit(3)");
 * pattern.test("123"); // true
 */
function compilePattern(pattern, flags = "") {
    // Implementation
}
```

### Code Comments

- Use comments to explain **why**, not **what**
- Document non-obvious decisions or workarounds
- Keep comments up-to-date with code changes
- Remove outdated or redundant comments

---

## Code Standards

### Follow Existing Patterns

- Match the style and structure of existing code
- Use the same naming conventions
- Respect established architectural patterns
- Maintain consistency with the codebase

### Write Tests First

Follow the test-driven development workflow:

1. Write a failing test that describes the desired behavior
2. Implement the minimal code to make the test pass
3. Refactor while keeping tests green
4. Ensure all three test types pass (unit, E2E, conformance)

See the [Testing Philosophy & Workflow](testing_workflow.md) for complete testing requirements.

### Keep Changes Minimal

- Make the smallest change that solves the problem
- Don't refactor unrelated code
- Don't add unnecessary features
- Each commit should have a single, clear purpose

### Document as You Go

- Update documentation in the same commit as code changes
- Keep docstrings synchronized with implementation
- Update relevant guides when changing architecture
- Add examples for new features

---

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
   - Ensure tests follow the [3-Test Standard](testing_design.md#the-3-test-standard)
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

---

## Pull Request Process

### Before Submitting

1. **Create a branch** from `main`
2. **Make changes** following the development workflow
3. **Run all tests** and ensure they pass
4. **Update documentation** to reflect changes
5. **Review your own changes** for quality and completeness

### Submitting the PR

1. **Write a clear title** that summarizes the change
2. **Provide a detailed description** including:
   - What problem does this solve?
   - What approach did you take?
   - What tests were added/modified?
   - What documentation was updated?
3. **Link to related issues** if applicable
4. **Request review** from appropriate reviewers

### During Review

1. **Respond to feedback** promptly and professionally
2. **Make requested changes** in new commits
3. **Explain your reasoning** when you disagree with feedback
4. **Update the PR description** if scope changes

### Before Merge

1. **Squash commits** if requested (maintains clean history)
2. **Ensure all CI checks pass**
3. **Verify documentation is complete**
4. **Thank reviewers** for their time and feedback

---

## Review Criteria

Pull requests are evaluated on:

- **Correctness**: Does it solve the stated problem?
- **Completeness**: Does it follow the full development workflow?
- **Testing**: Does it meet the [3-Test Standard](testing_design.md#the-3-test-standard)?
- **Documentation**: Are docs updated and accurate?
- **Code quality**: Is it clear, maintainable, and minimal?
- **Specification alignment**: Does it comply with grammar and semantics?

---

## Version Control and Maintenance

### Commit Messages

Write clear, descriptive commit messages:

- Use the imperative mood ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- Provide details in the body if needed
- Reference issue numbers when applicable

**Good examples:**
- `Add support for Unicode character classes`
- `Fix off-by-one error in quantifier parsing`
- `Update Python binding documentation`

**Bad examples:**
- `changes`
- `fix stuff`
- `WIP`

### Updating Documentation

When making code changes that affect documentation:

1. Update the relevant documentation files in the same commit
2. Check for broken links after moving or renaming files
3. Update cross-references if scope or structure changes
4. Run spell-check before committing

### Review Checklist

Before submitting documentation changes, verify:

- [ ] No content is duplicated across files
- [ ] All internal links use relative paths and are working
- [ ] Cross-references point to the authoritative source
- [ ] Tone and formatting follow these guidelines
- [ ] Code examples are complete and tested
- [ ] Spelling and grammar are correct

---

## Getting Help

- **Questions about architecture?** See [Architectural Principles](architecture.md)
- **Questions about testing?** See [Test Design Standard](testing_design.md), [Test Setup Guide](testing_setup.md), or [Testing Philosophy & Workflow](testing_workflow.md)
- **Questions about the specification?** See [Formal Language Specification](spec_links.md)
- **Questions about usage?** See the binding READMEs ([Python](../bindings/python/README.md) | [JavaScript](../bindings/javascript/README.md))

---

## Enforcement

These guidelines are **mandatory** for all contributions to STRling:

- Pull requests will be reviewed against these standards
- Violations of the DRY principle will be rejected
- Missing or broken hyperlinks must be fixed before merging
- Inconsistent tone or formatting should be corrected during review
- Code without appropriate tests will not be merged
