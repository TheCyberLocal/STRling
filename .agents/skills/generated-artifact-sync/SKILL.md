---
name: generated-artifact-sync
description: Resolve and safely synchronize STRling generated artifacts from changed source paths using governance/generated-artifacts.json. Use when a change may affect tracked fixtures, contract snapshots, version projections, runtime evidence, stdlib projections, or another registered generated family, or when reviewing a generated-output diff.
---

# Synchronize generated artifacts

1. Inspect Git status and preserve staged, unstaged, and concurrent work. Accept
   explicit repository-relative changed-source paths; if none are supplied,
   derive candidates from the requested change or a read-only diff and state
   that assumption.
2. Read `governance/generated-artifacts.json`. Match candidate paths against
   each family's `authoritative_sources` and `generator_inputs`, respecting its
   repository-relative globs. Do not substitute a remembered mapping.
3. Report every affected family with its authority, generator inputs, outputs,
   transition/enforcement state, generator command, and verification command.
   Distinguish an authoritative-source match from a generator-input match.
4. Before writing, confirm the user requested synchronization and inspect
   existing output changes. Preserve unrelated modifications. If only analysis
   was requested, return the map and commands without running a generator.
5. For an authorized write, run only the registry's exact generator for the
   affected family. Reuse its existing repository script; do not reimplement
   generation in the skill. Avoid networked, full-profile, release, or unrelated
   generators unless the registry and task explicitly require them.
6. Review the output diff and run the registry's exact verification command.
   Then run the smallest affected component test or generated-artifact check.
   Escalate through the root validation ladder only when scope requires it.
7. If the generator or verification command is absent, ambiguous, unsafe, or
   marked transitional, stop and report the gap. Never invent a command or
   treat reproducible output as semantic approval.
8. Summarize the matched families, commands run, outputs changed, verification
   results, skipped tiers, and remaining gaps. Never stage, commit, push,
   publish, or rewrite history automatically.
