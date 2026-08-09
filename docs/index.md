# STRling Developer Documentation Hub

[← Back to Project Overview](../README.md)

This is the **central landing page** for all STRling technical documentation. Use this hub to navigate to architecture, testing standards, contribution guidelines, and formal specifications.

---

## Documentation Index

### Core Concepts

- **[Architectural Principles](architecture.md)**: The `parse → compile → emit` pipeline and Iron Law of Emitters.
- **[Project Architecture & Strategy](project_architecture_strategy.md)**: The durable binding SSOT rules, diagnostics flow, and release strategy model.
- **[Formal Language Specification (Links)](spec_links.md)**: Index of grammar, semantics, and schemas.

### Guides & Tutorials

- **[Your First Contribution](tutorial/first_contribution.md)**: The "Zip Code" tutorial for new contributors.
- **[Test Environment Setup](testing_setup.md)**: The "Golden Path" setup guide using `./strling`.
- **[Testing Philosophy & Workflow](testing_workflow.md)**: Principles of Test Parity and contribution workflow.
- **[Test Design Standard](testing_design.md)**: The 3-Test Standard and Golden Pattern Testing.
- **[Toolchains and Quality Commands](toolchains.md)**: Deterministic runtime policy, root quality interface, capability states, and JSON results.
- **[Releasing STRling](releasing.md)**: Release process and Omega Certification.
- **[CI/CD Pipeline Setup](ci_cd_setup.md)**: GitHub Actions configuration and deployment.
- **[Contribution & Documentation Guidelines](guidelines.md)**: Standards for code and documentation.

### Tooling & Utilities

STRling provides a unified CLI and certification suite to streamline development.

- **`./strling`**: The canonical setup, build, test, quality, environment-validation, and certification interface shared by developers and CI.
- **`tooling/audit_omega.py`**: The unified Final Certification harness. Must return 100% Green before any release.
