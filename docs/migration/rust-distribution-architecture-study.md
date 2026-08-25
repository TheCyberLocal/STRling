# Rust distribution architecture decision study

Status: recommendation complete; implementation requires Program Owner
authorization.

Decision scope: P18-T05 CP4 Rust packaging blocker only. This record does not
select a Fourth Edition package version, change a support tier, authorize a
registry claim, or authorize publication.

Study source: clean `architecture/v4` commit
`3ffcc5d77f3a1fe21176a693fa14075a7744ae7c`.

## Decision

Recommend **one distributable `strling` crate containing the canonical
implementation through a curated crate root**.

The publishable package should compile the existing authoritative `core/src`
files directly. It must not copy, generate, vendor, or fork those semantic
sources. The curated crate root exposes only the P17-T02 Rust facade while
compiler stages remain private. The existing `core/Cargo.toml` package may
remain `publish = false` as an internal build package for the canonical CLI,
interop, fuzz, and performance tooling; both manifests compile the same source
files, not two semantic implementations.

This is better for STRling over the long term than publishing
`strling-kernel`. It keeps one consumer artifact, one registry coordinate, one
public SemVer surface, and one SBOM/provenance subject. It also prevents the
current internal kernel module tree from becoming an addressable crates.io API.
The tradeoff is a deliberate package-layout and governance change: the public
crate needs a package root capable of including `core/src` and its governed
JSON inputs, plus a curated crate root whose module inventory is checked
against the canonical implementation.

Model A, `strling -> strling-kernel`, is Cargo-valid and remains a viable
fallback. It is not recommended because Cargo has no workspace-private public
visibility: facade-required kernel items, and any stage APIs needed by the
internal CLI or performance harness, become callable through a permanent
public registry coordinate. It also adds an immutable package, ordered
publication, a second artifact/SBOM/provenance subject, and a second version
relationship before P20 has ratified package policy.

There is no technical basis to demote or remove Rust from the release graph.
Both tested package models work; support-policy reconsideration therefore
remains out of scope.

### P18-T05 implementation authorization and layout correction

The Program Owner subsequently authorized Model B as the permanent Rust
distribution architecture. The repository-root `Cargo.toml` is the sole
publishable `strling` package and compiles `core/src/lib_public.rs` plus the
same canonical module files directly. The prior binding-local manifest, lock,
and forwarding crate root are retired. No `strling-kernel` registry package is
created.

Permanent implementation exposed one Cargo package-boundary fact that the
disposable prototype did not model: retaining `core/Cargo.toml` makes `core` a
nested package, so Cargo excludes `core/src` from the root package even when
the root manifest names those files in `include`. The unpublished internal
manifest and lock therefore move to `core/internal/`; their targets continue
to compile the exact `core/src` files and remain `publish = false`. This
supersedes this study's earlier statement that the internal manifest could
remain at `core/Cargo.toml`; it does not change the selected architecture or
create another semantic implementation.

The permanent package contains 70 intentional files and excludes the
unpublished internal crate root. Rust 1.75 `cargo package --locked` passes;
two clean package builds are byte-identical at SHA-256
`f8331474fab31453d59b2d54a441655b94d5b922ada652b8dd8c6f0904c247b6`;
and fresh Windows and Ubuntu x86_64 consumers produce `3.0.0 Succeeded` from
the packaged source without a dependency on the repository checkout. The
`3.0.0` value is the already-governed operational manifest value, not a
selection of the Fourth Edition public release version. P20-T01/T02 retain
authority over the next public version, compatibility policy, support tier,
and publication pipeline ratification.

## 1. Current blocker

The canonical facade manifest declares only a local dependency:

```toml
[dependencies]
strling-kernel = { path = "../../core" }
```

The dependency package is named `strling-kernel`, version `0.1.0`, and declares
`publish = false`. With Rust/Cargo 1.75.0, the unchanged repository fails
closed:

```text
error: all dependencies must have a version specified when packaging.
dependency `strling-kernel` does not specify a version
Note: The packaged dependency will use the version from crates.io,
the `path` specification will be removed from the dependency declaration.
```

This is documented Cargo behavior, not a repository-specific heuristic. A
path-only dependency cannot be published. A dependency with both `path` and
`version` uses the path locally, but the packaged manifest retains the registry
version requirement and removes the path. See Cargo's
[dependency specification](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies)
and [`cargo package`](https://doc.rust-lang.org/cargo/commands/cargo-package.html)
documentation.

The official crates.io API establishes the external state:

-   [`strling`](https://crates.io/api/v1/crates/strling) has one unyanked,
    immutable `3.0.0` release, checksum
    `07301bd0fbf1d1e2be25bd14e856e375b59b2fed1726170799e28b8efb7f869e`,
    created 2026-04-19 and licensed MIT.
-   The official
    [owner record](https://crates.io/api/v1/crates/strling/owners) identifies
    `TheCyberLocal` / Timothy Macfarlane, so the existing name is controlled by
    the current project owner.
-   The historical
    [3.0.0 dependency graph](https://crates.io/api/v1/crates/strling/3.0.0/dependencies)
    uses `clap`, `glob`, `regex`, `serde`, `serde_json`, and `thiserror`, plus
    development dependencies. It is not the Fourth Edition graph.
-   [`strling-kernel`](https://crates.io/api/v1/crates/strling-kernel) returned
    HTTP 404 during this study. Absence is not a reservation or ownership
    guarantee.

Cargo does not allow an existing crate version to be overwritten. Publication
and owner management are separate registry operations; dependencies must
already be available to the registry before a dependent crate can be
published. These constraints are documented in Cargo's
[publishing guide](https://doc.rust-lang.org/cargo/reference/publishing.html)
and [`cargo owner`](https://doc.rust-lang.org/cargo/commands/cargo-owner.html)
reference.

## 2. Architectural constraints

The study treated the following as non-negotiable:

-   `core/src` remains the only semantic implementation and the Rust reference
    kernel.
-   `strling` remains the ergonomic consumer facade defined by P17-T02.
-   Public behavior remains the governed request/result, diagnostic,
    target/profile, artifact, Simply, and public-contract surface.
-   Compiler stages and internal module topology do not become accidental
    stable API.
-   No packaged crate depends on a repository-relative path after extraction.
-   Every registry artifact must have exact checksum, SBOM, provenance,
    license, and clean-rebuild evidence.
-   This study cannot decide public versions, support tiers, compatibility
    promises, or publication policy assigned to P20-T01/T02.

Cargo package membership is controlled by the package root and explicit
`include`/`exclude` rules, not merely by workspace membership. The applicable
rules are in the
[manifest reference](https://doc.rust-lang.org/cargo/reference/manifest.html#the-exclude-and-include-fields)
and [workspace reference](https://doc.rust-lang.org/cargo/reference/workspaces.html).

## 3. Candidate designs

### Model A — facade plus versioned implementation dependency

```text
consumer -> strling -> strling-kernel -> serde / serde_json / sha2
```

`strling-kernel` becomes a registry package. `strling` uses a path-plus-version
dependency in the repository and a registry-only version in its normalized
package manifest. A clean consumer names only `strling`.

Cargo requires no special facade API metadata beyond a valid package manifest
and a public library interface sufficient for the dependent facade to compile.
crates.io expects the normal package metadata, including name, version,
description, license, repository/homepage, and readme. The package should use an
explicit `include` list.

The technical coupling choices are:

-   An exact kernel requirement is the fail-closed choice for an implementation
    dependency because it accepts only a certified facade/kernel pair.
-   A compatible range is technically valid Cargo, but it creates a SemVer
    compatibility promise for the kernel API. That promise is policy and must
    be ratified by P20-T01 before use.
-   The kernel must be published and visible in the registry index before the
    facade can be published. A local registry can prove resolution but cannot
    remove that production ordering requirement.

The current internal kernel surface complicates this model. The canonical CLI,
interop bridge, fuzz targets, and performance runner consume modules beyond the
curated Rust facade. Cargo provides no visibility that is public to selected
workspace dependents but private to all other consumers. `#[doc(hidden)]`
reduces documentation exposure; it does not make a public item private or keep
third parties from depending on it.

### Model B — one distributable crate over the canonical source tree

```text
consumer -> strling -> serde / serde_json / sha2
                       |
                       +-- compiles canonical core/src directly
```

The consumer crate and canonical implementation are one distributable Cargo
package, but the public facade and internal stages remain different Rust module
boundaries. This is not a duplicate implementation.

The validated repository-layout mechanism is:

1.  a publishable package root that contains `core/src` and the governed JSON
    inputs under Cargo's package root;
2.  a curated crate root beside `core/src/lib.rs`, so ordinary Rust module
    resolution compiles the exact canonical files without copying or rewriting
    them;
3.  explicit package `include` entries for the curated root, canonical Rust
    sources, exact governed JSON inputs, facade tests/examples, readme, and
    license;
4.  private compiler-stage modules and the seven intended public facade
    modules;
5.  the existing unpublished internal `core/Cargo.toml` retained for internal
    CLI/performance consumers until a later deliberate consolidation.

A repository-root Cargo manifest is the smallest known package root that can
include the existing `core`, `spec`, `tests`, and facade evidence without
copying them or using paths outside the packaged archive. The permanent
implementation may choose an equivalent root only if it proves the same
properties. Cargo's documented
[dependency renaming](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#renaming-dependencies-in-cargotoml)
remains available if an internal workspace consumer later needs a different
local dependency key; it was not required by the prototype.

### Model C — remove or demote Rust

Rust could be made source-only, non-publishable, Preview, or Legacy only through
a support-policy decision. That would change the frozen release denominator and
does not follow from technical evidence: Models A and B both produced valid,
usable packages. Model C is therefore rejected in this study and remains solely
a P20-T01 policy alternative if the Program Owner later chooses to reconsider
Rust for independent reasons.

## 4. Disposable prototype configurations

All prototypes were under ignored `.tmp` paths, used temporary prerelease
versions, and were removed after evidence capture. No registry upload occurred.

### Model A configuration

The implementation package used:

```toml
[package]
name = "strling-kernel"
version = "0.0.0-p18t05.1"
edition = "2021"
rust-version = "1.70"
license = "Apache-2.0"
description = "Canonical STRling compiler implementation dependency"
include = ["src/**/*.rs", "assets/**/*.json", "README.md", "LICENSE"]
autobins = false
autoexamples = false
autotests = false
autobenches = false

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
sha2 = "0.10"
```

The facade used:

```toml
[package]
name = "strling"
version = "0.0.0-p18t05.1"
edition = "2021"
rust-version = "1.70"
license = "Apache-2.0"
include = ["src/**/*.rs", "assets/**/*.json", "tests/**/*.rs",
           "examples/**/*.rs", "README.md", "LICENSE"]

[dependencies]
strling-kernel = { path = "../kernel", version = "=0.0.0-p18t05.1" }
```

The kernel prototype made compiler stages private and exposed only the seven
modules and root items required by the facade, marked `#[doc(hidden)]`. Its
self-contained assets were exact byte copies of twelve governed repository
JSON files. The facade included six exact governed JSON inputs. A disposable
Cargo local registry contained the kernel and third-party lock graph; the
facade was packaged against that registry, and a separate consumer resolved
only `strling = "=0.0.0-p18t05.1"`.

The normalized packaged facade manifest removed `path` and retained only:

```toml
[dependencies.strling-kernel]
version = "=0.0.0-p18t05.1"
```

### Model B configuration

Two controls were run. The first placed the canonical files under one
disposable crate directory. The stronger control reproduced the intended
repository layout using byte-identical disposable copies of the tracked files:

```toml
[package]
name = "strling"
version = "0.0.0-p18t05.2"
edition = "2021"
rust-version = "1.70"
license = "Apache-2.0"
include = [
  "core/src/lib_public.rs",
  "core/src/**/*.rs",
  "spec/**/*.json",
  "tests/conformance/*.json",
  "bindings/rust/tests/facade.rs",
  "bindings/rust/examples/*.rs",
  "README.md",
  "LICENSE",
]

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
sha2 = "0.10"

[lib]
name = "strling"
path = "core/src/lib_public.rs"
```

The disposable copies had experiment authority only; the permanent mechanism
would point at the tracked `core/src` files directly. `lib_public.rs` declared
the same canonical modules from the same directory. Compiler stages were
private. Only `contract`, `diagnostics`, `semantic`,
`simply`, `source`, `stdlib`, and `target`, plus the existing root facade
reexports and functions, were public. The test and example targets continued
to use the P17 facade evidence.

An attempted control with a crate root outside `core/src` failed because Rust
nested-module resolution changed (`diagnostic_generation::quality`,
`portability_planning::equivalence`, and similar children resolved beside the
alternate root). That failed layout is rejected as fragile. Moving the curated
root beside the canonical modules fixed resolution without modifying a
semantic source file.

## 5. Package, install, smoke, and API results

| Evidence                           | Model A                                                                                                                                              | Model B                                                            |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `cargo package --locked --offline` | Passed for kernel and facade                                                                                                                         | Passed                                                             |
| Packaged files                     | Kernel 61; facade 15                                                                                                                                 | Same-source layout 70                                              |
| Compressed artifact size           | Kernel 246,916 bytes; facade 13,991 bytes                                                                                                            | 254,124 bytes                                                      |
| SHA-256                            | Kernel `3e1fd4a2a6f34c06e989af86c336bb1db32c002f9c9ad14faa5cdc55418959c7`; facade `f81f05e2b61d80c1cc866f335c089e587b62c7d4219afefe1c9f04ddc392b68e` | `2fcc1584cdb8b8db775b86bf7824f1ae8100d4b2e0692555510172be1c751156` |
| Facade tests                       | 6/6 passed                                                                                                                                           | 6/6 passed; 20/20 included core tests also passed                  |
| Fresh Windows consumer             | `0.0.0-p18t05.1 Succeeded`                                                                                                                           | `0.0.0-p18t05.2 Succeeded`                                         |
| Fresh Linux consumer               | Same result under Ubuntu x86_64, Rust 1.75                                                                                                           | Same result under Ubuntu x86_64, Rust 1.75                         |
| Repository-relative consumer path  | None                                                                                                                                                 | None                                                               |
| Simply + canonical compile smoke   | Passed                                                                                                                                               | Passed                                                             |

The Linux runs used WSL only as a packaging/build compatibility host. They are
not performance evidence and do not change the P18-T04 WSL disposition.

Archive inspection found only the explicit Cargo manifests/lock where
applicable, canonical Rust sources, exact governed JSON inputs, facade
tests/examples, readme, and license. There were no target outputs, local
registry files, repository metadata, credentials, or unrelated binding files.

For Model A, the current source-signature extractor produced 19 symbols; the
only difference from the governed facade snapshot was the temporary kernel path
coordinate. The facade source itself was byte-identical. A negative consumer
could not access `strling::compiler_pipeline`; it also could not name the
transitive `strling_kernel` crate without declaring it directly.

For Model B, Rustdoc listed exactly the seven intended modules, existing root
facade reexports, `compile`, `compile_with_evidence`, `check`, `version`, and
`VERSION`. It did not list `compiler_pipeline` or a `kernel` module. A negative
consumer received Rust privacy errors for those paths. The current governed
extractor is source-shape-specific to `pub use strling_kernel::...`; Model B
therefore requires an extractor update that records the same logical facade
through `crate::...`, not an API expansion or a silent snapshot rewrite.

## 6. SBOM, provenance, dependency, license, and reproducibility

The prototypes used Cargo.lock-backed local-registry resolution and
CycloneDX's official Rust generator for graph inspection. P18-T05's permanent
producer remains authoritative for the required SPDX 2.3 artifact SBOM.

| Evidence                         | Model A                                  | Model B                                 |
| -------------------------------- | ---------------------------------------- | --------------------------------------- |
| CycloneDX                        | 1.5 JSON                                 | 1.5 JSON                                |
| Components / dependency rows     | 22 / 23                                  | 21 / 22                                 |
| First-party graph                | `strling -> strling-kernel`              | `strling` only                          |
| External components              | Same exact 20 packages                   | Same exact 20 packages                  |
| First-party license              | Both Apache-2.0                          | Apache-2.0                              |
| Missing component license fields | 0                                        | 0                                       |
| Clean archive rebuild            | Three identical copies of each A archive | Two identical same-source-layout copies |

Model A SBOM SHA-256 was
`eb85b42e67b42fd798ceca44b1cccd2e7cd70bae01c2eb0cd1e98d056031c837`.
The initial Model B SBOM was
`04907555efb6c134e2167640008e532b45a64c3da261636629615c40e828e44e`;
the stronger same-source layout produced
`546ee256b60e96c62320f95df25c3f3e1f15d7d30197a84564c13cf060daf61e`.
CycloneDX 0.5.9 warned that `version_check` uses the historical non-SPDX slash
form `MIT/Apache-2.0`. The governed P18 exact license evidence, not that parser,
remains license authority; the resolved graph introduced no new third-party
package or license.

All packaged canonical/spec/conformance JSON inputs matched their repository
sources byte-for-byte. The Rust 1.75 toolchain was authenticated as:

-   Cargo `1.75.0 (1d8b05cdd 2023-11-20)`, executable SHA-256
    `7f2357adb9b7dca9f7b6e9eb9a0e0a0b4e7e516c19f34d3a348b298701692c80`;
-   rustc `1.75.0 (82e1608df 2023-12-21)`, executable SHA-256
    `9e7863a6ea57c70e875d25c5818e0f836bd8da60b07f64a578298f0064144626`.

The existing P18 in-toto Statement v1 / SLSA Provenance v1 producer was applied
to the prototype subjects. It bound source commit, build command, current
release-manifest fingerprint, toolchain versions and executable hashes, input
tree hashes, and artifact hashes. Statement fingerprints were:

-   Model A kernel:
    `6084a8fba00c992e8b7d3ceea5cfd0d2b322b07c222594dee22b66adadb320b5`;
-   Model A facade:
    `8206acc05b380731b8b0ec9824ce5b5cdc62388dd170799709381d5ba840eb32`;
-   Model B same-source layout:
    `3b4a84959c123ae92681455e00081ba11a90785a2f25e1f63f26e068905c5bcd`.

These prototype statements have study authority only. Model A would require
the permanent release denominator to add a second independently checksummed,
SBOM-described, and provenance-bound crate. Model B fits the existing single
Rust artifact subject.

## 7. Decision matrix

| Criterion                   | Model A: facade + kernel                                                                          | Model B: one same-source crate                                                  | Model C: demote/remove                                            |
| --------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| One semantic implementation | Preserved                                                                                         | Preserved directly from `core/src`                                              | Avoids distribution but does not improve implementation authority |
| Fourth Edition alignment    | Directly matches P17's dependency arrow                                                           | Preserves P17's curated-facade intent while changing the Cargo package boundary | Conflicts with the retained Rust release surface                  |
| Accidental public API       | Higher: a permanent kernel coordinate and facade-required public items are externally addressable | Lowest: stages remain crate-private                                             | None only because the package is absent                           |
| Rust consumer ergonomics    | Normal; consumer names only `strling`                                                             | Normal and simpler; consumer names only `strling`                               | Poor or unavailable                                               |
| Cargo/crates.io correctness | Proven                                                                                            | Proven                                                                          | Not a publishable design                                          |
| Dependency clarity          | Explicit implementation edge                                                                      | One package; internal boundary is source/module governance                      | Removes useful evidence rather than resolving it                  |
| Release ordering/coupling   | Kernel first, facade second; exact pair recommended                                               | One artifact; no first-party publish ordering                                   | Support-policy dependent                                          |
| Kernel evolvability         | Constrained by immutable public kernel versions and possible direct users                         | Internal modules evolve without a second public coordinate                      | Not applicable                                                    |
| Facade stability            | Curated facade remains                                                                            | Curated facade remains and is the only registry API                             | Surface withdrawn or reclassified                                 |
| SBOM/provenance             | Clear but two first-party components and subjects                                                 | Clearest: one component and subject                                             | Release denominator must change                                   |
| Reproducibility             | Byte-for-byte proven                                                                              | Byte-for-byte proven                                                            | No artifact to prove                                              |
| Cross-platform              | Windows and Linux consumer smoke passed                                                           | Windows and Linux consumer smoke passed                                         | No consumer path                                                  |
| Installation complexity     | Cargo resolves one transitive first-party crate                                                   | Smallest graph                                                                  | Higher user burden or unavailable                                 |
| Supply-chain surface        | Extra crate name, owner boundary, OIDC configuration, artifact, and immutable version             | Existing crate name and one artifact                                            | Smaller only by dropping promised capability                      |
| Maintenance burden          | Package/API/version/pipeline coupling plus internal-API exposure management                       | Curated crate-root/module-inventory governance; no semantic copies              | Documentation/support migration burden                            |
| P17 compatibility           | Exact package dependency mechanism                                                                | Same facade/authority intent, different package mechanism                       | Reverses retained-surface outcome                                 |
| Policy deferred to P20      | Kernel and facade version relationship, kernel support meaning, plus next `strling` version       | Next `strling` version and normal package support/compatibility only            | Entire Rust support disposition                                   |
| Historical 3.0.0 migration  | New facade version required; kernel is a new immutable coordinate                                 | New facade version required; no new coordinate                                  | Requires explicit withdrawal/reclassification                     |

## 8. Recommended architecture

Select Model B: **one public `strling` crate that compiles the canonical
implementation directly through a curated crate root**.

This is the only tested model that simultaneously:

-   keeps `strling` as the normal ergonomic facade;
-   keeps `core/src` as the sole semantic authority;
-   prevents internal kernel stages from becoming a public registry API;
-   preserves current internal kernel consumers without forcing their APIs
    into the public crate;
-   fits the existing one-artifact Rust checksum/SBOM/provenance denominator;
-   avoids a new public package name, owner boundary, publication order, and
    pre-P20 version relationship.

P17's durable intent was a curated facade over canonical behavior, not a second
semantic implementation. Model B preserves that intent at the Rust module and
crate-root boundary. It supersedes only the provisional path-dependency
packaging mechanism that P17 explicitly deferred to a later release decision.

## 9. Rejected alternatives

-   **Path-only kernel dependency:** Cargo rejects it for packaging.
-   **Change only the facade version:** does not create a registry-resolvable
    kernel.
-   **Publish the current broad kernel unchanged:** makes internal stage modules
    an externally addressable registry API and expands supply-chain scope.
-   **Use `#[doc(hidden)]` as privacy:** documentation hiding is not Rust
    visibility or a compatibility barrier.
-   **Copy/generate kernel sources into `bindings/rust`:** creates drift and a
    second implementation artifact; rejected.
-   **Assemble/rewrite source trees during release:** makes the published source
    differ from reviewed authority and weakens reproducibility; rejected.
-   **Reference files outside the Cargo package root:** cannot produce a
    standalone registry package; rejected.
-   **Use a curated crate root outside `core/src` with per-module `#[path]`:**
    empirically broke nested-module resolution; rejected as fragile.
-   **Demote/remove Rust:** no technical evidence supports it because two valid
    package architectures exist.

## 10. Minimal authorized implementation to unblock P18-T05

If the Program Owner authorizes the recommendation, P18-T05 should make only
these architecture-preserving changes before resuming CP4:

1.  Add one publishable `strling` Cargo package root whose explicit include set
    contains the canonical Rust sources and exact governed JSON inputs.
2.  Add one curated, semantic-free crate root beside `core/src/lib.rs`; it must
    compile the same source modules and expose only the governed Rust facade.
3.  Keep `core/Cargo.toml` unpublished for internal CLI, interop, fuzz, and
    performance consumers. Do not copy or generate semantic sources.
4.  Move or point the existing Rust facade tests/examples at the new public
    package without changing their behavior.
5.  Update the Rust architecture hardgate and public-contract extractor to
    enforce same-source compilation, exact public modules, private stage
    modules, and no restored binding-owned implementation.
6.  Package exact source/spec/conformance inputs through Cargo's include list;
    reject missing, extra, or hash-drifted inputs.
7.  Update the P18 Rust release manifest/build root and workflow handoff for one
    `.crate`; keep byte-for-byte reproducibility, SPDX 2.3, in-toto/SLSA,
    checksum, OIDC, and no-publication requirements unchanged.
8.  Run `cargo package --locked`, archive inspection, isolated consumer smoke,
    public-contract negatives, dependency/license checks, two clean rebuilds,
    and the complete CP4 Full/Release dry-run.

The implementation may temporarily mirror the currently governed package
version solely so dry-run packaging has a manifest value. It must not claim
that historical `3.0.0` can be republished or select the next public version.

## 11. Decisions deferred to P20-T01/T02

P20-T01 must ratify:

-   the next public `strling` version, which must differ from immutable 3.0.0;
-   package/core/spec/protocol version relationships;
-   SemVer compatibility promises and support tiers;
-   the Supported/Preview/Legacy Rust inventory;
-   migration messaging from the unrelated historical 3.0.0 graph;
-   minimum supported Rust policy if it changes from the governed floor.

P20-T02 must rebuild the final manifest and publication pipeline around those
decisions, including final artifact names, registry metadata, trusted
publishing configuration, release ordering, and consumer documentation.

Model B technically forces only one relationship: one published `strling`
version identifies one exact packaged source/toolchain/input/artifact subject.
It does not force the package version to equal the compiler, specification,
protocol, or target-profile version. Those remain policy.

If Model A is selected instead, P20-T01 must additionally decide the public
meaning and support status of `strling-kernel`, facade/kernel version coupling,
whether exact or compatible dependency requirements are promised, and how
direct kernel consumers are treated.

## 12. Risks and carry-forward

-   A second curated crate root can drift in module declarations even though it
    shares semantic files. The implementation must add a fail-closed module
    inventory check and public-contract negatives.
-   A repository-root Cargo manifest introduces a new default Cargo entrypoint
    alongside existing root package-manager files. Commands and workspace
    expectations must be explicit and tested.
-   The package include list becomes security/provenance authority and must be
    generated or checked from exact governed inputs, not maintained by archive
    inspection alone.
-   Cargo library dependency ranges describe what consumers may resolve later;
    the P18 artifact SBOM describes the exact producer resolution. P20 must
    decide dependency-range policy without weakening P18's producer evidence.
-   The `strling` 3.0.0 owner is authenticated, but the next version remains an
    irreversible registry decision and is not authorized here.
-   No production publication path, credential, crate ownership mutation, or
    registry upload was exercised.

## Authorization required

To implement this recommendation and resume P18-T05 CP4, the Program Owner must
authorize the permanent **single same-source `strling` crate architecture**,
including the publishable package root, curated crate root, corresponding P17
architecture-hardgate/public-contract updates, and one-artifact P18 release
manifest/workflow changes described above.

That authorization need not and should not select a public version, change a
support tier, publish a crate, claim a new registry name, or consume P20's
versioning/publication-policy authority.
