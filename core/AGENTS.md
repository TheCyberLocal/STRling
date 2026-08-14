# Core agent guidance

`core/` is the Rust reference kernel for canonical parsing, normalization,
Semantic IR, analysis, planning, lowering, emission, and runtime projections.
It implements the contracts under `../spec/`; reference behavior is not
independently normative.

Start with [README.md](README.md), then
[../governance/architecture.md](../governance/architecture.md) and the relevant
versioned contract. Keep host-binding APIs, target runtime execution, and
compatibility projections outside the kernel unless the architecture assigns
that responsibility here.

For iteration, run the narrow Cargo test or check that exercises the changed
module. Before handoff, use `./strling test core` from the repository root and
the root validation ladder when the change crosses contracts, targets, or
public surfaces. Check `../governance/generated-artifacts.json` before changing
core inputs that feed registered evidence or snapshots.
