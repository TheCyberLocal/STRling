# STRling Specification Versioning

## Specification identity

The normative language specification is named **STRling Semantic
Specification**. A ratified release is identified by:

-   the specification name;
-   a `MAJOR.MINOR` specification version;
-   ratified status; and
-   the immutable repository revision or tag containing its complete normative
    file set and delegated conformance cases.

The semantic specification version is independent of compiler, package,
binding, schema, and target-profile release versions.

## Version format and compatibility

Ratified versions use two non-negative decimal integers without leading zeroes:
`MAJOR.MINOR`, for example `1.0` or `1.2`. A patch component is deliberately
omitted.

**MAJOR** changes when a normative semantic change is incompatible. Examples
include changing the meaning of a previously valid construct, rejecting a
previously valid program without a prior compatible transition, or changing a
normative contract so existing conforming consumers cannot continue unchanged.

**MINOR** changes for backward-compatible semantic or contract additions. A
later minor version in the same major line must preserve the meaning of every
program conforming to an earlier minor version, except for behavior already
reserved or explicitly undefined by that earlier version.

Editorial corrections do not change the specification version when they do not
change normative meaning. They must be recorded as errata and remain traceable
to the exact repository revision. A correction that changes an implementer's
required behavior is semantic, even if described as a clarification, and
requires a minor or major version according to compatibility impact.

## Draft versions

Unratified work uses `MAJOR.MINOR-draft.N` labels, where `N` is a positive
integer review iteration. A draft label is not a specification version,
provides no compatibility guarantee, and must not satisfy a normative
conformance claim.

Draft material lives under `spec/drafts/<major>.<minor>/`. Ratification:

1. resolves open normative questions;
2. identifies the complete normative file set and any delegated conformance
   cases;
3. records compatibility impact;
4. receives project ratification under the Engineering Constitution;
5. freezes an immutable source revision or tag; and
6. publishes the material under `spec/versions/<major>.<minor>/` or an
   equivalent immutable versioned location.

Removing the draft suffix is an explicit ratification action, never an automatic
consequence of implementation or package release.

## Compiler and package versions

Compiler releases use their own release version. Each compiler release must
declare the exact ratified specification version or versions it implements.
Neither equal-looking numbers nor “latest” imply conformance.

A compiler may support multiple specification versions. Selection and fallback
must be explicit and deterministic; silently compiling input under a different
semantic specification version is not allowed.

Host-language packages and adapters may release on independent schedules. Their
versions describe package compatibility, not semantic authority. A package must
identify the compiler capability and specification support it exposes.

## Target profiles

Target profiles are versioned independently because target-engine behavior
changes across engine editions, runtime versions, options, and environments.
Every ratified target profile must declare the semantic specification versions
with which it is compatible.

A compiler result must ultimately be traceable to the selected specification
version and target-profile identity/version. The exact profile schema and result
fields are intentionally deferred to canonical contract design.

A target-profile revision cannot redefine STRling semantics. It may refine
target facts, support decisions, required diagnostics, or lowering choices
within the controlling specification. If a proposed target decision would
change semantic meaning, the semantic specification versioning rules apply.

## Contracts, schemas, and conformance cases

A formal schema or contract is normative only when its own version, scope, and
normative designation are explicit. File naming, directory placement, or use by
an implementation is insufficient.

Specification-authored conformance cases are normative only when a ratified
specification delegates an exact question or example set to them. Generated
fixtures, implementation snapshots, and historical goldens remain
non-normative compatibility evidence unless independently reviewed, accepted,
and designated through that delegation.

Changes to a separately versioned contract follow that contract's compatibility
policy and must also trigger a semantic specification version change if they
alter normative STRling meaning.

## Initial transition

The certified baseline's `unversioned-transitional` label remains the accurate
identity of the historical formal-specification bundle. It is not `0.x`, `v3`,
or `1.0` by implication.

The upcoming semantic architecture uses `1.0-draft.N` working labels. No
ratified `1.0` specification exists until the ratification requirements above
are satisfied, and current implementations retain only their separately
recorded compatibility and contract claims.
