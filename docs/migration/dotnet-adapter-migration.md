# Canonical C# and F# .NET adapter migration

Status: P17-T05 CP1 scope and contract lock

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

Public extraction is transitional: the current C# assembly exposes 48 exported
types and 564 declared public members; the historical F# compiler assembly
exposes 54 exported types and 481 declared public members. No checked-in C# or
F# public snapshot exists. CP2 must pin normalized extraction for both final
package assemblies before implementation.

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

- NativeClient loads a caller-supplied absolute path. Exact packaged
  runtimes/<rid>/native discovery may be enabled only for an actually packaged
  and certified RID; there is no network, current-directory, PATH, or ambient
  name search.
- The declared mapping is win-x64, linux-x64, osx-x64, and osx-arm64 to the four
  strling.c-abi certification targets. A RID is not supported merely because a
  name is mapped.
- This Windows host may certify only win-x64 unless matching external evidence
  exists with unchanged inputs. No Linux or macOS claim is inferred.
- The client resolves the ABI-version, execute, and free symbols from the same
  library handle; verifies ABI version 1 before execution; enforces the 10 MiB
  request and 32 MiB response ceilings; uses strict UTF-8 and strict JSON; and
  frees every owned response through the same descriptor and library.
- NativeClient is immutable, reentrant, safe for concurrent calls, and
  IDisposable. Calls after disposal fail as host lifecycle errors. The package
  does not promise deterministic OS unload timing, finalizer-only correctness,
  cancellation of an in-flight native call, or recovery from process-level
  allocation termination.
- Native load, symbol, ABI, disposed-client, marshaling, UTF-8, size, and
  transport failures are stable host errors. Canonical completed or rejected
  protocol responses, diagnostics, and paths remain canonical values and are
  not rewritten as host semantics.

## Public compatibility contract

Package IDs STRling and STRling.FSharp, version 3.0.0, net9.0, and the Strling,
Strling.Simply, STRling, and STRling.FSharp namespace families remain the
starting compatibility obligations.

The final public break is intentional:

- binding-owned Core AST/IR, parser/compiler, emitter, hint, warning, and target
  semantics are retired;
- root parse/compile conveniences return canonical contract data rather than
  binding-private AST or regex strings;
- target artifacts require an exact caller-supplied profile and reference;
- targetless Pattern.Compile and F# compile/ToPcre2 behavior cannot continue as
  implicit PCRE2 execution and must be explicitly deprecated/refused or
  replaced by client-and-profile operations;
- C# may expose classes/records and exceptions for host failures; F# may expose
  records, options, and discriminated unions over the same canonical response;
- existing Simply and Essential names are preserved where they can construct
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

CP3 may implement only the frozen boundary and may remove the eighteen
semantic-copy paths only after local replacement proof. CP4 owns the SDK/TFM/RID
matrix, native lifecycle and concurrency execution, pack/install and clean
consumer proof, live dependency risk, migration differential, public/generated
contracts, governance, security, and Local/Pull Request/Full profiles. No
NuGet publication, branch push, release, support-tier change, or other binding
migration is authorized.
