---
applyTo: "tests/spec/*.json,governance/contracts/snapshots/*.json,spec/stdlib/essential_5.json,spec/stdlib/registry.json,tests/conformance/evidence/**,bindings/swift/Tests/STRlingConformanceTests/Resources/*.json,bindings/c/tests/fixtures/*.json,bindings/c/tests/unit/converted_from_js.c"
---

# Generated-artifact guidance

Do not edit a matching artifact until you have located its family in
[governance/generated-artifacts.json](../../governance/generated-artifacts.json).
Change the registered authoritative source or generator input, use the exact
registered generator, review the output diff, and run the registered
verification. If a family has no generator or verification command, stop and
report the transition gap; do not invent one. Generated output is never
semantic authority merely because it is tracked or reproducible.
