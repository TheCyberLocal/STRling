# Regex-compatible frontend specifications

This directory contains versioned contracts for STRling's historical
regex-shaped source notation. The notation is a compatibility and import
frontend. It is not the Semantic STRling authoring language and does not define
the semantic or target capability ceiling of the product.

The current contract is
[`legacy-regex/1.0`](legacy-regex/1.0/README.md). Its stable frontend identity is
`strling.regex-compat`, and its dialect version is `1.0.0`.

Each version owns only:

-   source encoding, layout, directives, and syntax;
-   frontend context rules and resource limits;
-   stable frontend diagnostic identities and UTF-8 byte locations; and
-   specification-authored positive and negative fixtures.

Accepted syntax must lower structurally to canonical Semantic IR. A frontend
contract cannot define Semantic IR meaning, select a target, assert target
support, or authorize opaque target-regex passthrough.
