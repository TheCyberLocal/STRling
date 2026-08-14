# Canonical CLI rebase

## Outcome and authority

P16-T01 replaces the repository's Python-specific parser/emitter command path
with one versioned command-line transport over canonical compiler contracts and
the certified Rust kernel. The CLI owns argument decoding, bounded file and
standard-stream I/O, profile resolution, presentation, and exit status. It does
not own syntax parsing, Semantic IR construction, analysis, portability policy,
rewrites, lowering, emission, explanation meaning, or migration meaning.

The compiler contracts under `spec/contracts/1.0`, the Semantic STRling,
regex-compatible, and Simply frontend contracts, the target profiles, and the
semantic explanation, no-match, and conversion contracts remain authoritative.
The CLI contract introduced by this task governs only command selection,
transport envelopes, presentation, and process behavior. It cannot extend the
language or reinterpret a canonical result.

The clean starting and rollback boundary is
`ed3cb1bdee6d033492522d27d6abf807088603fa`. The task begins on
`architecture/v4` after P15 closure. P15 deliberately kept explanations out of
`CompileResult` 1.0 and reserved a reusable transport addition for later work.
P16-T01 may therefore add an independent, additive kernel projection that
returns an unchanged `CompileResult` together with the explanation already
produced by the same stage execution. It may not add an explanation field to
`CompileResult` or rerun low-level stages from the CLI.

## Existing surface inventory

The starting repository contains three distinct command paths:

| Surface                         | Starting behavior                                                                                                                                                                                                         | Disposition                                                                                                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `./strling compile`             | Requires Cargo, delegates request JSON on standard input to `core/cli/strling-kernel.rs`, optionally loads one exact target profile, writes compact `CompileResult` JSON, and uses exits 0, 2, 64, 70, and 74.            | Retain as the canonical raw-request compatibility form and extend through the same Rust binary.                                                                            |
| `./strling simply`              | Delegates a versioned Simply BuilderRequest to the Rust decoder/builder and the sole compiler facade, returning the established adapter response.                                                                         | Retain as an explicit compatibility transport; it is not a second CLI semantic model.                                                                                      |
| `python3 tooling/parse_strl.py` | Reads a positional file or `-`, parses through the historical Python binding, optionally validates the legacy base schema, optionally emits unversioned PCRE2 text, and uses exits 0, 2, and 3 plus uncaught file errors. | Replace with the canonical Rust commands, migrate the owned smoke tests and documentation, then remove the obsolete script. Historical reference runners remain untouched. |

The POSIX root wrapper exposes the canonical compile and Simply routes plus
repository quality/binding operations. The PowerShell wrapper exposes only the
quality/binding operations and therefore lacks product-command parity. The
root public-contract snapshot currently parses command rows only from the
POSIX help source. Neither wrapper reads semantic configuration from the
environment. The Rust transport currently accepts only raw request JSON and
does not expose import, explanation, conversion, human diagnostics, or target
inspection.

The root name `check` is already a repository-quality compatibility alias.
P16-T01 keeps `strling check` with no semantic input flags, and
`strling check <binding|all>`, on that existing path. Canonical source checking
is selected only by an explicit `--input` or `--request` option, which makes
the dispatch deterministic and preserves existing automation.

## Locked command tree

The product command tree is:

```text
strling compile
strling import
strling explain
strling migrate
strling check --input ... | --request ...
strling target list
strling target inspect ...
strling simply
```

`compile` accepts either one strict canonical `CompileRequest` or a source
shorthand from which the CLI constructs that request. `import` selects the
versioned regex-compatible frontend and requests canonical semantics.
`explain` returns the structured semantic explanation and may additionally
return bounded why-no-match evidence for an explicitly supplied subject.
`migrate` converts the completed canonical semantic result to Semantic STRling
or a Simply BuilderRequest through the existing conversion API. `check`
returns or presents the canonical compiler diagnostics. `target list` and
`target inspect` expose only the five authored profiles registered under
`spec/targets/profiles`; they do not probe installed engines. `simply` preserves
the existing builder transport.

The common source shorthand has explicit source, frontend, source-identity,
specification-version, requested-output, diagnostic-severity, partial-semantics,
resource-limit, target-profile, and output-format options. A target profile is
either one bundled exact profile identity/alias or one explicit JSON path. The
CLI computes the immutable profile reference from the parsed profile and places
that reference in the request; it never infers a target from source syntax,
filename, installed runtime, or environment. Canonical contract version 1.0.0
and the currently implemented semantic specification version remain explicit
defaults, and unsupported selections fail rather than downgrade.

`--request` and `--input` are mutually exclusive. Subject text and subject-file
options are mutually exclusive. A command rejects unused or ambiguous options,
duplicate singleton options, an unversioned target name, a target profile whose
identity does not match the request, and output requests that lack target
authority. Source content is always supplied inline to the kernel. A caller may
provide `--source-id`; otherwise the CLI derives a deterministic content-based
opaque identity and retains a file path only as the non-authoritative display
name. Authored Semantic STRling uses authored provenance; regex-compatible
`import` uses imported provenance.

## Canonical execution boundary

Every semantic command has this dependency direction:

```text
CLI arguments and bounded I/O
    -> canonical CompileRequest plus optional exact TargetProfile
    -> one public kernel orchestration call
    -> unchanged CompileResult plus already-computed explanation evidence
    -> optional canonical no-match or semantic-conversion call
    -> versioned CLI JSON or deterministic human rendering
```

The kernel integration may route completed portability plans through the
existing PCRE2, ECMAScript, or Python re lowerer and serializer when
`target_artifact` is requested. This is orchestration of already certified
backends, not new target behavior. Unsupported/unresolved plans produce no
artifact, and a lowerer/serializer correspondence failure remains a typed
kernel failure. CLI and direct-library calls for the same request and profile
must serialize identical `CompileResult` and `TargetArtifact` data.

The additive evidence projection must reuse the exact target-neutral or
target-aware explanation produced during the compiler call. The CLI cannot
call foundational, structural, safety, capability, planning, rewrite,
lowering, or serialization stages individually. Conversion consumes the
completed normalized semantic result and its corresponding explanation.
Bounded no-match consumes the same pair and never includes raw subject text in
its result.

## Versioned output and exit contracts

Machine output is UTF-8, deterministically ordered, compact JSON followed by
one newline. `compile`, `import`, and JSON `check` use the canonical
`CompileResult` 1.0 contract directly. Explanation, migration, and target
inspection use the independently versioned `strling.cli@1.0.0` response suite,
which CP2 will freeze as closed schemas. Those envelopes identify the command
and carry canonical request/result, explanation, conversion, no-match, profile,
or profile-reference values without copying their semantics into CLI-owned
fields. The existing Simply response contract remains unchanged.

JSON mode writes no presentation diagnostics to standard error; a valid failed
`CompileResult` remains data on standard output. Standard error is reserved for
usage, malformed transport, unavailable host prerequisites, internal boundary
failures, and I/O errors. Human mode writes primary material or a success
summary to standard output and renders canonical diagnostics in their existing
order to standard error. Human text is non-normative and must not contradict or
supplement structured evidence.

The stable exit taxonomy is:

| Exit | Meaning                                                                                                                          |
| ---: | -------------------------------------------------------------------------------------------------------------------------------- |
|    0 | Command completed; the canonical compile result succeeded, or the requested inspection/explanation completed truthfully.         |
|    2 | A valid canonical compile/check/migration operation produced a failed or non-exact result for which exact success was requested. |
|   64 | Usage error, malformed UTF-8/JSON contract, invalid option combination, or invalid bounded option.                               |
|   69 | Required local executable or explicitly selected bundled resource is unavailable.                                                |
|   70 | Canonical kernel or post-kernel correspondence invariant failed.                                                                 |
|   74 | Input/output operation failed or a requested output path was unsafe.                                                             |

A broken stdout pipe is treated as successful consumer cancellation and emits
no secondary diagnostic. Other write failures use exit 74. Output-file writes
are permitted only for a fully computed artifact or migration output, refuse
an existing destination, write a same-directory temporary file completely,
and rename it into place. Failed, partial, unsupported, or serialization-error
results never create or truncate the destination.

## Compatibility and retirement rules

`strling compile < request.json`, `strling compile --target-profile PATH`, and
`strling simply` retain their current JSON and exit behavior. The quality
`strling check` compatibility forms remain as described above. POSIX and
PowerShell product command dispatch and help must converge.

The former positional Python CLI input maps to `strling import --input PATH`
or `--input -`. Its `--schema` option is retired because canonical request,
result, semantic, profile, and artifact validation is mandatory and cannot be
selected by an arbitrary legacy schema. Its `--emit pcre2` option is retired
because it omits the required exact engine/profile version; callers must select
an exact PCRE2 profile and request `target_artifact`. Ambiguous legacy option
combinations are rejected, not guessed. The Python CLI file may be removed only
after its Python and TypeScript smoke coverage is replaced by canonical CLI
coverage and documentation examples no longer invoke it.

No product semantic configuration is read from environment variables or a
repository/user config file in this task. Cargo discovery in the root wrappers
and explicit file paths are host transport concerns. Runtime execution of
generated artifacts, package publication, LSP/editor behavior, bindings,
marketplace packaging, and historical-reference cleanup remain outside T01.

## Verification and closure

CP2 freezes the CLI schemas, command/help goldens, canonical request fixtures,
success/failure/malformed cases, stdin/file parity, source provenance,
profile/version selection, exit codes, output safety, broken-pipe behavior,
legacy dispositions, and direct-library parity expectations. CP3 implements
the smallest Rust/root-wrapper changes and focused proof. CP4 runs CLI and
affected binding end-to-end tests, target artifact parity, explanation and
conversion checks, public-contract and generated snapshots, documentation,
architecture/security/governance, migration differential, and Local, Pull
Request, and Full profiles as available.

Closure records every command and response version, compatibility/deprecation
decision, exit status, removed Python plumbing, artifact/result equivalence,
test counts, environment limitation, final commit, and P16-T02 readiness. T01
does not begin LSP diagnostics/hover work.
