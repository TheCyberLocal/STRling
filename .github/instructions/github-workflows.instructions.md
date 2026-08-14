---
applyTo: ".github/workflows/**"
---

# GitHub workflow guidance

Treat [toolchain.json](../../toolchain.json) and
[governance/certification-profiles.md](../../governance/certification-profiles.md)
as validation-profile authority. Workflows should invoke or verify canonical
operations instead of defining a competing command catalog. Preserve the
offline guarantees of `local` and `pull-request`, least privilege, pinned
dependencies, and explicit authorization for networked or release operations.
Run security/content workflow validation and the smallest relevant profile
before broader certification.
