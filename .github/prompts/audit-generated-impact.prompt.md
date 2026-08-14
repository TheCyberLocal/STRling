---
description: "Map changed source paths to registered generated artifacts and required checks"
argument-hint: "<changed-source-path> [additional paths...]"
---

# Audit generated impact

Treat the invocation arguments as repository-relative changed-source paths.
Read `/AGENTS.md` and `governance/generated-artifacts.json`; do not rely on a
remembered artifact list.

For each path, match both `authoritative_sources` and `generator_inputs`,
including repository glob semantics. Report:

1. every affected artifact family and why it matched;
2. a source → generator → output → verification map;
3. missing synchronization, ambiguous ownership, or transition gaps;
4. the exact smallest checks required.

Distinguish authoritative sources from current generator inputs. Do not edit,
generate, stage, commit, or publish unless the user separately authorizes that
action.
