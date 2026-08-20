# Canonical C# and F# .NET adapter migration

Status: P17-T05 CP3 minimal implementation and local proof

Starting commit: 352d7c2547a58f692a709e464b458bf83103b09c

## Objective

Replace the C# and F# package-local compilers with two idiomatic facades over
one shared .NET/native boundary. The .NET packages may own request
construction, canonical JSON projection, native loading, lifecycle, host
errors, package metadata, and Simply ergonomics. They may not parse, normalize,
analyze, validate, plan, lower, emit, or reinterpret STRling semantics.

## Starting state

The clean architecture/v4 starting tree contains 50 tracked C#/F# entries with
fingerprint
sha256:82633270ef02d21d267724a90dac9a92134cbd51eb811fffb31c2007a75d947f.
Thirty-two production C#/F# sources contain 4,462 lines; seventeen test sources
contain 1,070 lines and 45 static Fact annotations.

Eighteen product paths contain the closed local semantic implementation
footprint: C# parser/compiler/AST/IR/hint/emitter/Simply/helper routes and the
parallel F# parser/compiler/AST/IR/hint/emitter/Simply routes. Those paths
contain 4,080 lines and fingerprint to
sha256:fa3a2ab366719e9e4e93d5f7b0f4ca1fd502bf3521447cfd000d5c7f9fa7f7df.
They are compatibility evidence, not semantic authority, and may be retired
only after CP2 freezes their exact source and behavior.

The host exposes .NET SDK 9.0.302 under the governed >=9.0,<10.0 range. On the
starting tree, the historical C# suite passes 625 tests and the historical F#
compiler suite passes 616 tests on net9.0 with zero failures or skips. The
second F# project already references the C# package, but Api.fs is not included
in its project. It produces an assembly with zero exported types and its tests
fail to compile. That incomplete wrapper is not treated as a passing facade.

The starting reflection inventory exposes 48 C# exported types and 54
historical F# exported types. CP2 replaces the transitional inventory with a
checked-in isolated Release extractor. Its normalized task-start snapshots
contain 487 C# symbols across 48 types and one assembly and 479 F# symbols
across 54 types and both task-start product assemblies.

## Shared interop decision

The C# STRling assembly is the sole .NET interop substrate. It will use the
built-in NativeLibrary load/export APIs and fixed unmanaged delegates to the
existing strling.c-abi version 1 symbols. This avoids a third package, a second
F# native layer, generated Rust layout, JNI-style glue, subprocesses, sockets,
downloads, PATH discovery, and any dependency on internal Rust modules.

The F# package is the STRling.FSharp assembly and depends on the C# STRling
package. It may project canonical responses into F# records and discriminated
unions and provide F# Simply builders, but it cannot load the native library
independently or interpret canonical Semantic IR. The historical F# STRling
assembly conflicts by name with the C# STRling assembly and is therefore the
retirement source, not the shared substrate. The currently incomplete
STRling.FSharp project becomes the single F# product assembly after CP2 freezes
both historical public surfaces.

## Native and lifecycle contract

-   NativeClient loads a caller-supplied absolute path. Exact packaged
    runtimes/<rid>/native discovery may be enabled only for an actually packaged
    and certified RID; there is no network, current-directory, PATH, or ambient
    name search.
-   The declared mapping is win-x64, linux-x64, osx-x64, and osx-arm64 to the four
    strling.c-abi certification targets. A RID is not supported merely because a
    name is mapped.
-   This Windows host may certify only win-x64 unless matching external evidence
    exists with unchanged inputs. No Linux or macOS claim is inferred.
-   The client resolves the ABI-version, execute, and free symbols from the same
    library handle; verifies ABI version 1 before execution; enforces the 10 MiB
    request and 32 MiB response ceilings; uses strict UTF-8 and strict JSON; and
    frees every owned response through the same descriptor and library.
-   NativeClient is immutable, reentrant, safe for concurrent calls, and
    IDisposable. Calls after disposal fail as host lifecycle errors. The package
    does not promise deterministic OS unload timing, finalizer-only correctness,
    cancellation of an in-flight native call, or recovery from process-level
    allocation termination.
-   Native load, symbol, ABI, disposed-client, marshaling, UTF-8, size, and
    transport failures are stable host errors. Canonical completed or rejected
    protocol responses, diagnostics, and paths remain canonical values and are
    not rewritten as host semantics.

## Public compatibility contract

Package IDs STRling and STRling.FSharp, version 3.0.0, net9.0, and the Strling,
Strling.Simply, STRling, and STRling.FSharp namespace families remain the
starting compatibility obligations.

The final public break is intentional:

-   binding-owned Core AST/IR, parser/compiler, emitter, hint, warning, and target
    semantics are retired;
-   root parse/compile conveniences return canonical contract data rather than
    binding-private AST or regex strings;
-   target artifacts require an exact caller-supplied profile and reference;
-   targetless Pattern.Compile and F# compile/ToPcre2 behavior cannot continue as
    implicit PCRE2 execution and must be explicitly deprecated/refused or
    replaced by client-and-profile operations;
-   C# may expose classes/records and exceptions for host failures; F# may expose
    records, options, and discriminated unions over the same canonical response;
-   existing Simply and Essential names are preserved where they can construct
    the canonical Simply protocol without local semantic interpretation.

The five standard helpers remain lexical_shape conveniences across eight
variants, 117 edge records, and zero semantic validators. Neither adapter may
strengthen those helpers into semantic validation.

## Package and verification boundary

Production code uses only the .NET base class library plus the internal
STRling-to-STRling.FSharp package dependency. Test-only xUnit, test SDK, runner,
and coverage dependencies remain separately governed. CP2 must freeze the
exact NuGet graph, licenses, source/public/package denominator, and historical
behavior before any dependency or product-source change.

## Frozen CP2 evidence

The registered .NET evidence manifest fingerprints to
sha256:0cc397456a771e2171594218f78f66086a4fa3bc2913963dab8794337e2906db.
It freezes 72 cases across twelve families, eleven runners, four canonical
operations, the dotnet/C#/F# component denominator, and SDK 9.0.120, 9.0.200,
and 9.0.302. Every installed SDK passes the unchanged 625-case C# suite and
616-case historical F# suite with zero failures or skips. The incomplete F#
wrapper remains recorded as debt rather than being reclassified as passing.

The authenticated baseline fingerprints to
sha256:12034b0723bec7154da0eecf3f93b6e4e608fc488674ec43363a0703367574f2.
It embeds all 50 task-start files as hash-checked historical evidence and
separately locks 26 public/build inputs and all 18 semantic-copy paths. Nine
mutation tests reject count, identity, runner, observation, path, content, and
fingerprint substitution. The evidence bundle is certification input only and
cannot enter product or package graphs.

CP3 may implement only the frozen boundary and may remove the eighteen
semantic-copy paths only after local replacement proof. CP4 owns native
lifecycle and concurrency execution, pack/install and clean consumer proof,
live dependency risk, migration differential, final SDK/TFM/RID execution,
public/generated contracts, governance, security, and Local/Pull Request/Full
profiles. No NuGet publication, branch push, release, support-tier change, or
other binding migration is authorized.

## CP3 implementation and local proof

The final C# product now owns one built-in `NativeLibrary` client over the
three `strling.c-abi` v1 symbols. It validates ABI version 1 before execution,
uses length-delimited strict UTF-8 and strict JSON, enforces the 10 MiB request
and 32 MiB response ceilings, releases every owned response through the same
library handle, and serializes disposal against in-flight calls. Stable host
errors remain distinct from canonical failed compile results.

The final F# product is the `STRling.FSharp` assembly and has exactly one
project reference to the C# `STRling` product. Its records, options, module
functions, and compile-outcome union project canonical JSON; it owns no native
load, Semantic IR interpretation, target selection, diagnostic synthesis, or
regex execution route.

All eighteen frozen semantic-copy paths are absent. C# and F# Simply surfaces
record Simply 1.1 protocol operations, and their Essential helpers are
generated from registry fingerprint
`sha256:3539cc50744c492ee617f9c836c83e040ad3af2f32dd8fe3b1e329c5b14bc719`.
They expose five `lexical_shape` identities and eight exact variants without
claiming semantic validation.

Focused Release suites pass 9 C# and 4 F# tests. Three clean native parity runs
execute `describe`, source compile, and Simply compile through both facades and
produce identical normalized results with fingerprint
`sha256:d95c5b12a4b50c231be5dccff11454f7b4160f7e5a939c3f532296d2b5da1b31`.
Only `win-x64` is certified locally; other RID mappings remain unclaimed.
Isolated public extraction now records 128 C# and 92 F# replacement symbols.
