# TypeScript and Python Simply Preview adapters

## Status and authority

This document locks the TypeScript and Python Preview adapter boundary for the
ratified [`strling.simply-builder@1.0.0`](../../spec/frontends/simply/1.0/README.md)
protocol. The protocol, canonical contracts, and Rust kernel remain
authoritative. Host classes, method names, transport objects, and exception
presentation are adapter ergonomics and do not define new semantics.

The adapters are Preview. They are additive while the historical TypeScript
and Python `Pattern` APIs remain compatibility evidence. This task does not
promote those legacy private ASTs, compilers, emitters, runtime helpers, or
standard-pattern recipes into Fourth Edition authority.

## One request and one compiler

Both adapters expose immutable builder-owned values and one method for each of
the protocol's 15 operations. They record only the exact versioned
`BuilderRequest`: explicit semantic options, stable step and capture keys,
canonical imports, root identity, and compile projection. They do not parse
regex, normalize a graph, validate semantic meaning, analyze, plan, lower,
serialize a target artifact, execute a regex, or infer a target.

A Rust request replayer inside `core::simply` decodes the same protocol shape
and invokes `SimplyBuilder`. The repository JSON transport exposes that replay
as `strling simply`. Successful transport responses contain the exact canonical
`CompileRequest` and `CompileResult`; construction failures contain ordered
`STRL-SIMPLY-*` code/path records. A failed compile remains a successfully
decoded adapter response whose `CompileResult.outcome` is `failed`.

The CLI owns bounded stdin/stdout and target-profile loading only. It does not
own replay semantics. TypeScript and Python process transports require an
explicit command and optional exact target-profile path; callers may inject an
equivalent transport. No adapter searches PATH, the repository, an environment
variable, or the network to discover semantic behavior.

## Identity, mutation, and errors

Host values contain only an opaque builder token and stable step key. Adapter
methods append protocol data after bounded host-shape checks and freeze or copy
caller-owned collections before retaining them. The Rust replay is the sole
authority for key syntax, duplicate identities, graph ownership, capture
resolution, imports, canonical normalization, and request validation.

Serialization is deterministic: object fields follow protocol order, steps
retain construction order, caller member/value order is preserved, and compile
output order is normalized by Rust. Error translation preserves every canonical
code and JSON path without substituting host prose. Malformed JSON or a
transport failure is a transport error, not a fabricated semantic failure.

## Compatibility boundary

[`simply-preview-adapter-compatibility.json`](../../governance/baselines/simply-preview-adapter-compatibility.json)
enumerates every reachable historical TypeScript and Python Simply operation.
Each is classified as preserved, adapted, intentionally corrected, unsupported
legacy behavior, or unresolved. The inventory distinguishes construction
meaning from historical target strings, runtime objects, capture-repeat guards,
exception prose, and package-private representations.

Adapted operations have a mechanical Preview construction equivalent. The
`max=0` sentinel is intentionally corrected to protocol `null`. Direct
`toString`/`__str__`, local `compileNode`, browser-endpoint wrappers,
`toRegExp`, Python `exec`, private-node constructors, and the five historical
standard-pattern recipes are not Preview semantics. They remain reachable only
through the pre-existing legacy surface and are not used by the Preview path.
No operation is left unresolved at the design checkpoint.

## Certification boundary

Completion requires all 15 operations and all stable failures through the Rust
transport, byte-stable request/response serialization, malformed-input and
transport-negative tests, and cross-language equality for authored fixtures and
fixed seeds. TypeScript, Python, native Rust Simply, and equivalent direct
Semantic IR must produce the same normalized programs and `CompileResult`
values for every supported Preview case.

Historical TypeScript and Python runners remain evidence-only. Their literal,
target-convenience, unsupported-target, and runtime-return observations must be
reviewed against the new route and classified rather than copied. Public API
snapshots must record only intentional additive Preview declarations and the
additive CLI command. Architecture mutations must reject host compilation,
emission, semantic validation, target inference, runtime execution, ambient
discovery, and any second semantic model on Preview paths.

The task closes only after affected binding/Rust tests, repository hardgates,
the reviewed migration differential, Local, Pull Request, and Full profiles
pass as available, and the tree is clean.
