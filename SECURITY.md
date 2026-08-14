# STRling security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use a private
[GitHub Security Advisory](https://github.com/strling-lang/strling/security/advisories/new)
or email [strlinglang@gmail.com](mailto:strlinglang@gmail.com) if private
reporting is unavailable.

Include the affected revision, package or component, source frontend, target
profile, reproduction conditions, expected security boundary, observed impact,
and any known mitigation. Do not send live credentials or unnecessarily
sensitive personal data.

## Supported state

STRling is undergoing an active pre-release architecture and compatibility
migration. There is no single repository-wide version support table. Security
fixes target the current maintained default branch and affected published
packages according to their actual release state. A package version does not by
itself establish semantic-specification or target-profile support.

## Project security boundaries

Security-relevant STRling defects can include:

- compiler, parser, analyzer, formatter, CLI, language-server, or adapter
  behavior that crosses an established trust or resource boundary;
- incorrect lowering or emission that creates an injection, validation bypass,
  or material semantic mismatch;
- false safety, portability, validation, or compatibility claims presented with
  stronger guarantees than their controlling contract and evidence support;
- package, dependency, release, workflow, generated-artifact, or provenance
  integrity failures; and
- exposed credentials or unsafe handling of untrusted source, schemas,
  artifacts, diagnostics, or workspace content.

Generated regular expressions execute in target runtimes with their own
versioned semantics and resource behavior. A slow or unsafe target expression
is not automatically a compiler vulnerability, and a successful compilation is
not a universal ReDoS proof. Reports should identify the requested intent,
target profile, emitted artifact, runtime, and input so maintainers can separate
compiler behavior from target-runtime behavior.

The engineering security baseline and enforced repository controls are
documented in [`governance/security.md`](governance/security.md). This policy
defines public disclosure and triage; it does not redefine those engineering
contracts.
