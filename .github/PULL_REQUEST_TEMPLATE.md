## Description

Link the controlling issue, specification, contract, or decision and summarize
the permanent repository outcome. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Change classification

-   [ ] Semantic behavior
-   [ ] Public API
-   [ ] Schema/contract
-   [ ] Diagnostics
-   [ ] Target behavior/profile
-   [ ] Architecture
-   [ ] Generated output
-   [ ] Documentation only
-   [ ] Internal implementation

## Authority and architecture

-   [ ] I identified the controlling ratified specification, versioned contract,
        architecture decision, or explicit compatibility decision.
-   [ ] I did not treat a host binding, reference implementation, generated
        fixture, snapshot, or historical output as semantic authority.
-   [ ] I distinguished host-language adapters from target engines/profiles.
-   [ ] New authoring behavior converges on the canonical semantic path.
-   [ ] I did not introduce a new shadow parser/compiler/planner/emitter outside
        an authorized transitional scope.

If the work is a draft semantic proposal, identify its draft version and confirm
that it makes no implementation-conformance claim.

## Generated and compatibility evidence

-   [ ] I did not hand-edit registered generated outputs.
-   [ ] Any fixture regeneration follows a controlling specification, contract,
        or declared compatibility decision; generation itself is not approval.
-   [ ] I reviewed preserved public surfaces and compatibility evidence affected
        by the change.
-   [ ] Known non-contractual defects were not promoted into requirements.

## Operational package versions

`bindings/python/pyproject.toml` is the current operational package-version
source. It does not version the semantic specification.

-   [ ] If preparing a package release, I changed only the authorized source and
        ran `python3 tooling/sync_versions.py --write`.
-   [ ] I did not infer specification or target-profile compatibility from
        package version numbers.

## Verification

-   [ ] `./strling format --check all`
-   [ ] `./strling hygiene`
-   [ ] `BUNDLER_VERSION=2.4.20 ./strling lint all`
-   [ ] `./strling typecheck all`
-   [ ] `./strling generate --check`
-   [ ] `./strling contracts --check`
-   [ ] `./strling governance`
-   [ ] `BUNDLER_VERSION=2.4.20 ./strling check all`
-   [ ] `BUNDLER_VERSION=2.4.20 ./strling certify all`
-   [ ] Focused tests for every affected binding, target, contract, or tool
-   [ ] Documentation links, structured files, and `git diff --check`

## Checklist

-   [ ] The change stays within its declared task scope.
-   [ ] New and existing required tests pass without new warnings.
-   [ ] Documentation describes permanent capability rather than a temporary
        campaign.
-   [ ] No runtime semantic change is claimed unless explicitly declared and
        versioned.
-   [ ] I reviewed security implications and did not include credentials,
        machine-local state, or unintended generated output.
-   [ ] Suspected vulnerabilities are being handled privately under
        [`SECURITY.md`](../SECURITY.md), not disclosed in this pull request.
