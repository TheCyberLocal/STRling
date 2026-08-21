# Canonical Ruby, PHP, Perl, Lua, and R adapter migration

Status: P17-T07 CP2 verification design and evidence

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
