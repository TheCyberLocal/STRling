# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x     | :white_check_mark: |
| < 3.0   | :x:                |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

If you have discovered a security vulnerability in STRling, please report it privately. We strongly prefer reports via **GitHub Security Advisories** to ensure a secure disclosure process.

1.  Go to the [Security tab](https://github.com/TheCyberLocal/STRling/security/advisories/new).
2.  Click on "New Draft Security Advisory".

If you cannot access this feature, please contact the maintainers directly via the email addresses listed in their GitHub profiles before disclosing publicly.

## ⚠️ ReDoS (Regular Expression Denial of Service) Policy

STRling is a **Compiler**. It translates high-level syntax into native regex strings for various engines (PCRE2, Python `re`, JS `RegExp`, etc.). Because of this indirection, triaging security issues requires nuance.

### Is it a STRling Vulnerability?

Please use this guide to determine if the issue belongs to STRling or the target runtime.

#### 🔴 It IS a STRling Vulnerability if:

1.  **Compiler Panic:** The STRling compiler crashes, panics, or throws an unhandled exception while parsing or compiling a pattern. This is a Denial of Service vector for applications that compile user-provided patterns.
2.  **Optimization Failure:** You used a safety feature (e.g., `Atomic Group` or `Possessive Quantifier`), but STRling compiled it into a standard (vulnerable) group in the output regex without warning.
3.  **Semantics Mismatch:** The emitted regex matches strings it shouldn't (or vice versa), creating an injection vulnerability or bypass.

#### ⚪ It is LIKELY an Implementation Detail if:

1.  **Slow Execution:** You wrote a nested pattern (e.g., `(a+)+`), STRling compiled it faithfully to `/(a+)+/`, and it runs slowly in the Python `re` engine. STRling faithfully translated your logic; the vulnerability is in the logic itself.

### Mitigation

STRling provides first-class support for **ReDoS Prevention**. We strongly recommend using these features for user-facing patterns:

-   **Atomic Groups:** `(?>...)` (Discards backtracking info).
-   **Possessive Quantifiers:** `*+`, `++` (Matches without backtracking).
