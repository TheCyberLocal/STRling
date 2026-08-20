# STRling — F# adapter

The `STRling.FSharp` package is an idiomatic F# projection over the shared C#
`STRling` adapter and the canonical native compiler. It does not own another
native transport, parser, compiler, Semantic IR interpretation, target emitter,
or regex engine.

> **Migration status:** canonical native adapter implemented and locally
> certified by P17-T05. The retired F# implementation remains
> compatibility evidence, not the compiler boundary.

Semantic STRling is the flagship textual language. Regex-compatible text is an
import/compatibility surface, not Semantic STRling.
STRling 4.0 uses one canonical pipeline for Semantic, Simply, and explicit
compatibility requests.

## Install and load

The package targets `net9.0`, depends on `STRling 3.0.0` and pinned
`FSharp.Core 9.0.300`, and currently certifies only the `win-x64` native row.
Loading requires an explicit absolute native path.

```fsharp
open System
open System.IO
open STRling.FSharp

let nativePath = Path.Combine(AppContext.BaseDirectory, "strling_interop.dll")

use client = Api.loadClient nativePath
let compiler = Api.createCompiler client
let options = { Api.defaultOptions () with SourceId = "src:example" }

match Api.parse compiler "literal \"hello\"" (Some options) with
| Succeeded result
| Failed result -> printfn "%s" (result.GetProperty("outcome").GetString())
```

The `CompileOutcome` union projects the canonical result outcome. Diagnostics,
artifacts, paths, spans, and other canonical values remain `JsonElement` data;
the facade does not reinterpret them. Target artifacts require an exact
caller-supplied profile and reference.

## Simply and standard helpers

The F# facade exposes the same canonical Simply builder types from the shared
C# package plus generated `Essential` helper functions. Five registered
helpers produce eight exact `lexical_shape` variants. Lexical-shape acceptance
is intentionally distinct from semantic validity; these helpers are not
semantic validators.

## Errors and lifecycle

The shared `NativeClient` is reentrant and disposable. Native load, ABI,
transport, protocol, and closed-client failures retain the stable C# adapter
exception identities. The F# layer adds projections only and cannot create a
second native route or host-owned compiler behavior.

See the repository [specification](../../spec/README.md) and
[architecture](../../governance/architecture.md) for normative contracts.
