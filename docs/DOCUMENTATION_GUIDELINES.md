# Documentation Guidelines

This document defines the **non-negotiable standards** for all documentation in the STRling project. These guidelines ensure consistency, maintainability, and clarity across all documentation artifacts.

## Core Principles

### 1. Don't Repeat Yourself (DRY)

**Never duplicate significant bodies of text across multiple files.**

- Use hyperlinks to reference detailed information in other documents
- Each concept should have a single source of truth
- When tempted to copy/paste, create a link instead

**Examples:**
- ✅ Good: "See the [3-Test Standard](./README.md#testing-philosophy) for details on our testing approach."
- ❌ Bad: Copying the entire 3-Test Standard explanation into multiple files

### 2. Single Responsibility

Each documentation file must have a clearly defined scope:

- **Specification Hub** (`spec/README.md`): Links to formal language specifications
- **Documentation Hub** (`docs/README.md`): Architecture, philosophy, and contribution guides
- **Test Suite Guide** (`tests/README.md`): Test directory structure and quick reference
- **Binding READMEs**: Installation and usage examples for end users
- **Documentation Guidelines** (this file): Documentation standards and rules

### 3. Hyperlinks Over Duplication

Use hyperlinks extensively to create an interconnected documentation system:

- Link to the authoritative source when referencing concepts
- Use relative paths for internal links (e.g., `../spec/grammar/dsl.ebnf`)
- Ensure links are descriptive (e.g., "formal grammar specification" not "click here")

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

### Document Structure

Every documentation file should include:

1. **Title** (H1): Clear, descriptive title
2. **Purpose statement**: Brief explanation of the document's scope
3. **Body content**: Main content organized with clear headers
4. **Cross-references**: Links to related documentation

## Docstrings and Code Comments

### Python Docstrings

- Use Google-style docstrings
- Include parameter types and return types
- Provide examples for complex functions

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

- Use JSDoc format
- Include type annotations
- Provide examples for complex functions

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

## Version Control and Maintenance

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

## Examples of Good Documentation Structure

### Using Hyperlinks Effectively

**Instead of this:**
```markdown
## Testing Strategy

STRling uses a 3-Test Standard:
1. Unit tests validate individual components
2. E2E tests validate complete workflows
3. Conformance tests ensure cross-engine compatibility

[Explanation of each test type repeated across multiple files...]
```

**Do this:**
```markdown
## Testing Strategy

STRling uses a comprehensive [3-Test Standard](../docs/README.md#testing-philosophy) 
that ensures quality through unit tests, E2E tests, and conformance tests.
```

### Defining Scope Clearly

Each document should start with a clear scope statement:

```markdown
# STRling Test Suite

This guide explains the directory layout and test execution philosophy 
for developers working in the `tests/` directory. For the comprehensive 
testing philosophy and standards, see the [Documentation Hub](../docs/README.md).
```

## Enforcement

These guidelines are **mandatory** for all documentation in the STRling project:

- Pull requests with documentation changes will be reviewed against these standards
- Violations of the DRY principle (duplicated content) will be rejected
- Missing or broken hyperlinks must be fixed before merging
- Inconsistent tone or formatting should be corrected during review
