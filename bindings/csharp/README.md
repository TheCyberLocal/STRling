# STRling — C# adapter

The C# package is an idiomatic facade over the canonical STRling compiler. It
constructs canonical requests, calls the governed `strling.c-abi` v1 native
library, and returns canonical JSON results. It does not contain a parser,
compiler, target emitter, or regex engine.

> **Migration status:** canonical native adapter implemented and locally
> certified by P17-T05. The retired C# implementation remains
> compatibility evidence, not the compiler boundary.

Semantic STRling is the flagship textual language. Regex-compatible text is an
import/compatibility surface, not Semantic STRling.
STRling 4.0 uses one canonical pipeline for Semantic, Simply, and explicit
compatibility requests.

## Install and load

The `STRling` package targets `net9.0`. Its currently certified package row is
`win-x64`; other RIDs are not implied. Native loading always uses an explicit
absolute path and never searches the current directory, `PATH`, or the network.

```csharp
using System.Text.Json;
using Strling;
using Strling.Native;
using Strling.Simply;

var nativePath = Path.Combine(AppContext.BaseDirectory, "strling_interop.dll");
using var client = NativeClient.Load(nativePath);
var compiler = new Compiler(client);

JsonElement result = compiler.Parse(
    "literal \"hello\"",
    new SourceCompileOptions { SourceId = "src:example" });

Console.WriteLine(result.GetProperty("outcome").GetString());
```

Target artifacts require an exact caller-supplied target profile reference.
The adapter never chooses a default target.

## Simply

The Simply facade records the canonical Simply 1.1 protocol. Compilation also
goes through the native client; `Pattern.ToString()` and `Pattern.Exec()`
intentionally refuse local regex rendering or execution.

```csharp
var projection = JsonSerializer.SerializeToElement(new
{
    requested_outputs = new[] { "semantic" },
    compiler_options = new
    {
        partial_semantics = "forbid",
        diagnostic_policy = new { minimum_severity = "hint" },
    },
});

var pattern = S.Merge(S.Start(), Essential.Email(), S.End());
JsonElement simplyResult = pattern.Compile(client, projection);
```

`Essential` exposes five registered `lexical_shape` helpers across eight exact
variants. These helpers intentionally recognize lexical shapes and may accept
semantically invalid values; they are not semantic validators.

## Errors and lifecycle

`NativeClient` is reentrant, safe for concurrent calls, and `IDisposable`.
Native load, ABI, transport, protocol, and closed-client failures use distinct
stable exception identities. Canonical compiler failures remain canonical
results and diagnostics rather than being rewritten as host semantics.

See the repository [specification](../../spec/README.md) and
[architecture](../../governance/architecture.md) for normative contracts.
