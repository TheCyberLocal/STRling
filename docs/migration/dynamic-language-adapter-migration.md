# Canonical Ruby, PHP, Perl, Lua, and R adapter migration

Status: Complete — READY WITH RECORDED CARRY-FORWARD

Starting commit: 4504a35fdff420c5461beaedeeea6a2f184d2c5d

## Objective

Replace five package-local compilers with thin, idiomatic adapters over the
versioned native interop boundary. If an ecosystem cannot sustain a safe,
testable adapter, preserve its history as compatibility evidence and recommend
an explicit Legacy or unsupported disposition instead of retaining an
independent compiler.

The adapters may own request construction, canonical JSON projection, native
loading, allocation and release, lifecycle, host errors, package metadata, and
Simply ergonomics. They may not parse, normalize, analyze, validate, plan,
lower, emit, or reinterpret STRling semantics.

## Starting state

The clean `architecture/v4` starting tree contains 157 tracked Ruby, PHP, Perl,
Lua, and R entries with fingerprint
`sha256:1ba12f0e78fe407c7fdae5ee8839d4c9fb4dd625fe6399a015ce7fbe5c22b1b1`.
Its 86 production language sources contain 15,310 lines and fingerprint to
`sha256:f038f043704bfb5f4d50e2ee1d4ea24b88040cccab947f7156a1daf1fd3abdd2`.
Thirty-nine test sources contain 4,825 lines and fingerprint to
`sha256:2a0c9927b75b897fb308b94c263fc634e55ccd5fe2009823ad5d01ba29a6c286`.

Eighty-three product sources form the closed candidate semantic-copy footprint:
thirteen Ruby, forty-three PHP, twelve Perl, seven Lua, and eight R sources.
They contain 15,200 lines and fingerprint to
`sha256:6b4db0f70e7c32c535d25620d1f9969f15323c760b1fcfa739828251051798cd`.
CP2 must authenticate their exact task-start content and freeze executable
compatibility evidence before any semantic copy is removed.

Only R currently has an enforced public snapshot, containing 37 exports and S3
methods. Ruby, PHP, Perl, and Lua remain transitional public-contract rows with
no checked-in snapshot. The Windows host has none of the five runtime/package
toolchains. The existing native Linux verification clone has Perl 5.38.2 and
`prove`; Ruby, PHP, Lua, R, and their package tools are absent. These are exact
starting availability facts, not pass/fail rows and not support claims.

Package identities and declared ranges remain compatibility inputs: Ruby gem
`strling` requires Ruby `>=3.0,<4.0`; Composer package `strling/strling`
requires PHP `>=8.2,<9.0`; Perl distribution `STRling` declares Perl
`>=5.10,<6.0`; the Lua rock template declares Lua `>=5.1,<5.5`; and R package
`strling` has no governed runtime range. Version literals, the template-only Lua
release identity, unconstrained Lua/Perl/R dependency resolution, and the R
package's historical MIT metadata are frozen starting evidence, not silently
corrected by CP1.

## Support-disposition boundary

Permanent consumer-facing Supported, Preview, and Legacy policy is ordered for
ratification in P20-T01 after adapter certification. P17-T07 therefore records a
provisional migration disposition, not a permanent publication promise. All
five ecosystems begin as retained candidates for Preview-level certification.
An adapter earns that retained disposition only by passing its applicable
public, runtime, lifecycle, package, conformance, architecture, and security
gates on an explicitly executed platform/toolchain. Failure to meet that bar
produces an evidence-backed Legacy or unsupported recommendation for P17-T08
and P20-T01; it never preserves a local compiler as a workaround.

No support-tier ratification, package publication, release, tag, upload, or
branch push is part of this task.

## Bridge decisions

All retained adapters consume `strling.c-abi` version 1 through a caller-supplied
absolute library path and the canonical JSON protocol.

-   Ruby uses the standard-library `Fiddle` dynamic-loader interface. It adds no
    runtime gem dependency and exposes an explicit closeable client.
-   PHP uses the PHP FFI extension under the declared PHP 8.2 range. The
    extension and its enabled configuration are explicit prerequisites; there
    is no fallback when FFI is disabled.
-   Perl uses `FFI::Platypus` as the smallest sustainable native binding over
    the existing CPAN distribution model. Its exact resolved dependency and
    license graph must be frozen and certified before retention.
-   Standard Lua has no portable built-in FFI, so the package uses a minimal C
    module compiled against each executed Lua ABI. The module owns only native
    loading and bounded byte transport; the Lua facade owns JSON projection.
-   R uses a registered native `.Call` routine in the package shared library.
    The C layer performs only loading and bounded byte transport; R owns
    request/result projection. R's runtime range must be made exact before an
    executed retention claim.

These are five ecosystem transports over one ABI, not five native semantic
implementations. Ambient library-name search, current-directory probing,
network download, subprocess or socket transport, copied Rust layout, and
direct access to internal Rust modules are forbidden.

## Transport and lifecycle contract

-   Every client verifies ABI major version 1 before execution, enforces the
    10 MiB request and 32 MiB response ceilings, uses strict UTF-8 and strict
    JSON, and releases every owned response through the matching free symbol.
-   Empty, relative, missing, wrong-architecture, wrong-ABI, missing-symbol,
    closed-client, encoding, size, allocation, transport, and native-status
    failures remain stable host errors. Canonical completed or rejected
    protocol responses and diagnostics remain canonical values.
-   Ruby, PHP, and Perl provide idempotent close and serialize close against
    in-flight calls while allowing declared reentrant execution. Lua and R
    provide idempotent close within their host interpreter model and make no
    cross-thread host-API claim.
-   Deterministic operating-system unload timing, cancellation of an in-flight
    native call, process-level allocation recovery, and unexecuted platform or
    runtime versions are not promised.

## Public and semantic compatibility

The final adapter replacement is intentionally breaking. Binding-owned AST,
IR, parser, compiler, emitter, validator, hint, warning, diagnostic-synthesis,
and implicit target semantics are retirement candidates. Canonical operations
accept or construct versioned request envelopes and return canonical JSON data.
Target artifact operations require an exact target profile or reference;
targetless regex conveniences cannot silently preserve local execution.

Ruby exceptions/data, PHP exceptions/arrays, Perl exceptions/hash references,
Lua errors/tables, and R conditions/lists are host projections only. Simply and
Essential names may remain only as canonical protocol recipes without local
regex rendering or semantic validation.

The standard library remains five `lexical_shape` helpers across eight variants
and 117 edge records with zero semantic validators. No adapter may strengthen
lexical acceptance into semantic correctness.

## Checkpoint boundary

CP2 freezes the exact task-start source, public/package inputs, dependency
metadata, all 83 semantic-copy sources, compatibility cases, toolchain
availability, and platform rows before deletion. CP3 implements only the locked
transports, facades, public extractors, and generated helper projections. CP4
owns live toolchain/native execution, resource and concurrency certification,
clean package consumers, dependency risk/licenses, migration differential,
public/generated contracts, governance, and Local/Pull Request/Full profiles.

No product implementation changes in CP1. No canonical semantic, frontend,
target-profile, standard-library guarantee, interop ABI, package version,
permanent support-tier, publication, or unrelated binding change is authorized.

## CP3 implementation state

The five provisional retention candidates now use only the locked bridges:
Ruby/Fiddle, PHP/FFI, Perl/FFI::Platypus, a minimal Lua C module, and registered
R `.Call` routines. All 83 authenticated semantic-copy paths are absent. Each
facade constructs versioned compile or Simply requests, exposes the five
generated lexical helpers, requires a caller-selected absolute library path,
checks ABI version 1, bounds request and response bytes, rejects malformed or
duplicate-property JSON, releases the same descriptor, and has no alternate
compiler route.

The shared live harness now compiles seven strict C11 probes: canonical Unicode
transport, ABI mismatch, oversized response, duplicate JSON properties,
malformed response UTF-8, response-release failure, and a delayed concurrency
fixture. The probes reject malformed request UTF-8, track outstanding ownership
per calling thread so reentrant calls are not serialized by the fixture, and
return the same multibyte value to every host suite. Ruby exercises a shared
client across four concurrent workers. Release failure remains observable after
the descriptor has been zeroed.

On each of three executions, every host suite writes its actual `describe`,
`compile`, `target_profile.inspect`, and `simply.compile` values to an isolated
evidence directory. The runner rejects missing or extra operations, value drift,
cross-binding disagreement, and cross-run nondeterminism before fingerprinting
the observed result. It does not substitute a predeclared expected fingerprint
for host output.

Lua, Perl, and R public snapshots reproduce through non-executing extractors.
Ruby Ripper and PHP `token_get_all` extractors are implemented but require the
missing host tools before their snapshots can be materialized. The exact
declared/locked release graph fingerprints to
`sha256:108fb25f2cea46f5861db72dfefbbb68339f6645291e9a8fd20d47a9907a413c`;
it contains no packaged native payload and no semantic runtime package. Live
advisory/license evidence remains a CP4 requirement rather than an inferred
pass.

The previously recorded local non-toolchain profile passes 183 tests. After
transport hardening, its directly affected evidence, architecture, runtime,
public-contract, package, stdlib, and version suites remain green. Existing
Git-for-Windows Perl 5.38.2 and the cached network-disabled Linux conformance
image both pass the 15-case no-probe adapter suite. The cached image also
compiles the Unicode and release-failure probes with strict C11 warnings and
executes their exact status, value, and descriptor-zeroing checks. Its nine
tool-independent evidence mutations pass; the tenth exact-output test is
accurately unavailable there because that historical image has no Node or
governed Prettier.

Ruby/PHP snapshots, five-host syntax/build/test, Lua/R C compilation against
their real headers, Composer lock regeneration, clean consumers, and live
dependency risk remain unexecuted because P17-T07 toolchain and dependency
retrieval has not been authorized. Existing Windows, WSL, and cached
network-disabled images do not contain the required hosts and dependencies.
The shared runtime runner reports exact unavailability at Ruby. CP3 therefore
remains open and no retention or support claim has been promoted.

## Verification baseline

The registered `dynamic-language-adapter-migration-baseline` family freezes the
task-start denominator before any compiler copy is removed. Its authenticated
bundle contains all 157 tracked starting files, all 83 candidate semantic-copy
sources, and 28 public, build, package, dependency, and lock inputs. The exact
baseline fingerprints to
`sha256:e033b8a9db923b443449f2366e07121780c9f17b25228ef4cd0c2789575274b5`.

The closed matrix contains 129 cases across thirteen families: architecture
deletion, canonical parity, compatibility refusal, compatibility success,
historical preservation, lifecycle/concurrency, marshaling/error, package
installation, platform/toolchain, public API, Simply/stdlib, support
disposition, and Unicode/resource behavior. The contract fingerprints to
`sha256:fd7b8a81a6d3111e023c65e86690de63658442dd514f9be6906f42e309c8d719`
and the generated evidence fingerprints to
`sha256:ff02fceb857ed2966bd61068d9dc499f8a84781e7bd578e0ed8911515509a987`.

Ten mutation tests prove that case removal or substitution, starting
observation promotion, support-disposition promotion, semantic-path
substitution, historical-source mutation, non-exact materialization, and schema
shrinkage fail closed. The five absent Windows toolchains and the Linux
Perl-only observation remain frozen facts rather than inferred failures. The
five provisional Preview-candidate rows remain evidence dispositions rather
than permanent support claims.

CP3 public extraction is non-executing and ecosystem-aware: Ruby uses Ripper,
PHP uses `token_get_all`, Perl uses parser-backed export/prototype extraction,
Lua uses a task-owned parser over the bounded facade grammar, and R retains its
enforced parser-backed snapshot. Extractors describe host API shape only; they
cannot load product code or become semantic authorities. Generated Simply and
standard-library surfaces remain projections of the canonical registries.

## CP4 certification and final disposition

CP4 supersedes the earlier CP3 availability paragraph without rewriting its
historical observation. The exact committed implementation at
`cdd7691d080bb8ccf8ff61de88e8751b4b1afce9` has tree
`6184da555e590f78114bcb7b30f5df11a9097634`, identical to the reviewed and
certified 225-path Linux tree. Ruby 3.2.3, PHP 8.3.6, Perl 5.38.2, Lua 5.4.6,
and R 4.3.3 execute all five adapters on Linux x86_64. Three runs cover four
canonical operations and seven hostile transport probes per host with result
fingerprint
`sha256:591e370cd156f1d2abb2f1e1229fc8b41f04bf0031a9f87ae2bd0663e5ccfa4b`.
All 83 authenticated semantic-copy paths remain absent.

The final task-local disposition retains all five ecosystems as evidence-backed
Preview candidates: Ruby over Fiddle, PHP over FFI, Perl over FFI::Platypus,
Lua through its semantic-free C module, and R through registered `.Call`
routines. This is not permanent consumer-facing tier ratification; P20-T01
retains that authority. Each adapter requires a caller-supplied absolute native
library path, verifies ABI version 1 before execution, preserves canonical
responses, releases owned results, and offers no local semantic or fallback
route. Historical binding-owned AST, IR, parser, compiler, emitter, validator,
hint, diagnostic-synthesis, and targetless-regex APIs are intentionally removed.

Ruby, PHP, Perl, Lua, and R public snapshots reproduce without unclassified API
drift. Authorized Python and TypeScript snapshot changes and the affected .NET,
JVM, Go, Dart, and Swift evidence changes are fingerprint/reference-only.
Five standard-library projections reproduce from the unchanged registry, whose
contract remains five `lexical_shape` helpers, eight variants, 117 edge records,
and zero semantic validators. The release graph fingerprints to
`sha256:46f2921854bcad5ff96ff2d4594abaacc23ba12f49a26bba1a7a2ee8a94be258`.

The clean post-commit profile artifacts record:

-   Local: 22 passed, 5 failed, 6 unavailable; fingerprint
    `5d43464abe608370dfdec07acc72a01fb5aa3e4ade2cff510d3ee0c7d7e7b8f4`.
-   Pull Request: 31 passed, 8 failed, 31 unavailable; fingerprint
    `ee98e7619d8967aaece2da53c67627657aa26ec4a886263ec2a18a6fe978c09a`.
-   Full: 43 passed, 13 failed, 56 unavailable; fingerprint
    `88623c585ab3b863296e7aa032283d28a90fb165632f53ee71eb0f665c893034`.

Every applicable T07 row passes, including shared runtime and release-graph
certification, Perl/PHP/Ruby lint, Perl/R/Ruby builds, and all five host tests.
The nonzero aggregates retain exact non-T07 public/generated, interop,
TypeScript/Python, LSP, dependency-risk, unavailable-toolchain, and
platform-sensitive differential results; none is converted into a T07 pass.

Live Composer audit reports no advisories, Bundler reports no vulnerabilities
against ruby-advisory-db commit
`2faad0ccdfa19c7c57f965b90af99dd774eb0085`, and the direct Perl dependencies
FFI::Platypus 2.11 and JSON::PP 4.16 report no CPAN advisories. PHP and Ruby
resolved licenses are permitted. Governed Composer, Bundler, CPAN, LuaRocks,
and R vulnerability/license rows remain explicitly unavailable where the
repository has no authoritative scanner; supplementary evidence does not
reclassify them.

The Windows three-run migration differential covers 44 observations with zero
mismatches and zero blocking unresolved replacements at
`sha256:a625055f60e2eda0b37ee785d68eabcbbc94dab2fca272bd0a4ff54ad87636ab`.
Linux cannot reproduce the platform-sensitive historical source fingerprint,
so that row remains an environment limitation rather than a false pass.

No T07-owned work remains. Carry-forward is limited to unexecuted platforms,
architectures, and runtime versions; unavailable governed ecosystem scanners;
permanent P20-T01 support policy; repository-wide non-T07 profile debt; and
publication or push, neither of which was authorized. P17-T08 may now assemble
the zero-duplicated-semantics evidence matrix from this checkpoint.
