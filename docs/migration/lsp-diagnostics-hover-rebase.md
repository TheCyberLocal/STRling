# Canonical LSP diagnostics and hover rebase

## Outcome and authority

P16-T02 moves editor diagnostics and hover from the transitional Python-binding
intelligence layer to the canonical compiler interface completed by P16-T01.
The language server remains an adapter. It may own document synchronization,
bounded process transport, caching, cancellation, LSP presentation, and
host-language coordinate projection, but it may not parse STRling, infer
semantic facts, classify diagnostics, choose target support, or compile a
preview independently.

The canonical compiler contracts under `spec/contracts/1.0`, the Semantic
STRling and regex-compatible frontend contracts, and the Rust kernel remain
authoritative. The canonical CLI is the versioned process boundary available
to the Python LSP. For an identical source, frontend, compiler options, and
target profile, the LSP must publish the same diagnostic code, severity,
message, order, and canonical source span returned by the CLI/library result.
LSP ranges are deterministic projections of those spans, not replacement
diagnostic authority.

The clean starting and rollback boundary is
`823bad395b831504bc65dd2a2ebdaae3dd807c40` on `architecture/v4`. P16-T01
removed `tooling/parse_strl.py`; this task must not revive it or introduce a
new Python semantic facade.

## Starting-state inventory

The authored server entrypoint is `tooling/lsp-server/server/server.py`.
`assemble.sh` copies that file and `server/island_extractor.py` into the
generated extension payload. The root-level `tooling/lsp-server/server.py` is
not the packaged entrypoint and is not a second implementation target.

At the starting boundary, the authored server imports
`STRling.core.intelligence` directly. Diagnostics call `analyze_content`, map
its legacy dictionaries to LSP objects, project them through cached islands,
and then clamp every diagnostic to its starting line. Hover queries binding
registry documentation and otherwise invokes a binding PCRE2 emitter to show a
live compiled preview. Those paths are semantic dependencies and heuristics,
not canonical compiler projections.

Document changes are debounced by a 50 ms `threading.Timer`. The current code
does not retain the document version used for a computation, cannot cancel an
in-flight compiler operation, can publish an older result after a newer edit,
does not bound compiler duration, and has no close handler. Island and
diagnostic caches can therefore outlive the document snapshot that produced
them. The local protocol shim likewise lacks `didClose` support.

Existing island extraction and host projection remain selected compatibility
capabilities, but authoritative island grammar work is assigned to P16-T04.
Completion, navigation, semantic tokens, and code actions are implemented by
legacy intelligence today and are assigned to P16-T03 or P16-T04. P16-T02 may
keep those features operational while changing shared cache plumbing, but it
must not redesign or certify them.

## Locked compiler boundary

Each editor source unit is compiled through the canonical `strling-kernel`
process transport. Semantic STRling documents use `compile` and frontend
`strling.semantic`; compatibility-pattern documents and extracted host islands
use `import` and frontend `strling.regex-compat`. The request asks explicitly
for semantic and analysis results and carries the bounded diagnostic policy.
An exact target profile is included only when editor configuration supplies
one; target evidence is never inferred from a filename, installed engine, or
host language.

The bridge accepts the exact UTF-8 source on standard input, parses the one
JSON `CompileResult`, and retains that immutable result with the snapshot that
produced it. Exit 0 and exit 2 both carry valid result data. Usage, unavailable
executable, malformed transport, timeout, I/O, and internal failures are
service failures and must be logged separately; the LSP must not fabricate a
canonical diagnostic to disguise them.

Source-tree discovery may use an explicit injected command for tests, a
configured executable, an already-built repository kernel, or the root
canonical wrapper. Final extension packaging and distribution of that
executable belong to P16-T05. Absence of a packaged kernel before T05 is a
recorded deployment limitation, never permission to fall back to Python
semantics.

One architecture rule will enforce that the authored diagnostics/hover server
and its new bridge cannot import the STRling Python binding. The existing
transitional rule may retain only files whose completion, navigation, tokens,
code actions, or island work is explicitly deferred to T03/T04; it may no
longer describe the diagnostics/hover server as an allowed semantic client.

## Diagnostic projection contract

Canonical source spans are half-open UTF-8 byte offsets into the exact source
bytes. The LSP projection first validates `source_id`, coordinate system, and
bounds, then maps each endpoint by decoding the exact prefix. The server uses
the client/server position encoding selected for the session. UTF-16 is the
LSP-compatible default and VS Code path; UTF-8 and UTF-32 mapping are supported
where negotiation exposes them. Invalid mid-scalar offsets or spans for a
different source are isolated as bridge failures rather than rounded.

For native documents, the projected range is the canonical span. For embedded
islands, the canonical span is first mapped into the virtual document and then
projected through the island mirror into the host snapshot. Empty and
multi-line spans remain empty and multi-line respectively. The old
single-line clamp is removed because it changes compiler evidence. A canonical
diagnostic without a primary location receives the required zero-length LSP
range at the document start, while its canonical payload remains available in
`Diagnostic.data`.

Severity maps only by the closed canonical names `error`, `warning`, `info`,
and `hint`. Code, message, occurrence order, and compiler ordering are retained
exactly. Advice, fixes, category, phase, severity basis, and related locations
may be projected as LSP metadata where the protocol supports them, but the
adapter cannot promote, suppress, rewrite, or reclassify a diagnostic.

## Hover contract

Hover reads only the cached canonical result for the exact current snapshot.
It selects the narrowest Semantic IR node whose canonical origin span contains
the requested source position; ties are resolved deterministically by source
span, tree depth, and canonical traversal order. The returned hover range is
that node's projected canonical span.

The Markdown payload has a fixed section order and includes only evidence
present in the result: canonical construct kind and explicit parameters,
capture identity/name, foundational or structural facts, safety evidence,
exact-profile portability status, and an authoritative documentation reference
when the selected node/result carries enough identity to justify it. Missing,
partial, unsupported, unresolved, stale, or source-less evidence is omitted or
reported with its canonical status. The server does not infer a helper from a
word under the cursor and does not emit a PCRE2 preview merely because a
pattern happens to compile.

No hover compilation is initiated independently of snapshot validation. A
hover with no current canonical result, no containing canonical node, or only
failed/unsupported evidence returns `None`. This keeps hover deterministic and
prevents it from becoming a second semantic execution path.

## Snapshot, cancellation, and cache contract

The server retains an immutable per-URI snapshot containing URI, document
version, exact text, content identity, position encoding, and a monotonically
increasing generation. Open, full-content change, save, target/profile change,
and close all invalidate prior work according to that identity.

Pending debounce timers and in-flight compiler processes are registered per
URI. A newer generation cancels the pending timer and terminates the older
process. Every completion compares URI, version, content identity, profile
identity, and generation under the cache lock before storing results or
publishing diagnostics. A stale completion is discarded silently. Close
cancels work, removes islands/results/diagnostics/snapshot state, and publishes
an empty diagnostic list.

Compiler input, diagnostic count, number of island computations, and process
duration have explicit limits. Timeouts and process failures affect only the
owning snapshot and cannot crash the transport loop or poison a later cache
entry. Cache hits reuse immutable canonical results only when every semantic
input is identical; caching never changes request options or result order.

## Compatibility and task boundary

P16-T02 preserves the selected outcomes of diagnostics, hover availability,
rapid-edit responsiveness, embedded-source projection, and server recovery.
Where a legacy diagnostic differs from the canonical compiler, the canonical
result wins and the disposition is recorded in the migration differential.
The legacy one-line clamp, synthetic internal-error diagnostics, binding
registry word guesses, and live binding PCRE2 preview are intentionally
retired because they contradict the new evidence boundary.

This task does not:

- change Semantic STRling, regex-compatible, Semantic IR, analysis, diagnostic,
  target, or standard-library semantics;
- implement completion, definition/navigation, document symbols, semantic
  tokens, formatting redesign, code actions, or authoritative island grammars;
- add or change a binding public API;
- finalize VSIX packaging, marketplace metadata, kernel distribution, or
  extension installation; or
- edit generated `tooling/lsp-server/dist/**` output directly.

## Verification and closure

CP2 freezes canonical CLI/library/LSP parity fixtures, deterministic hover
goldens, all major Semantic IR node kinds, malformed and partial sources,
Unicode/multibyte offsets, UTF-8/UTF-16/UTF-32 position cases, native and host
projection, open/change/save/close, rapid edits, cancellation, stale results,
profile changes, bounded failures, missing kernel behavior, and recovery.

CP3 implements the smallest bridge, diagnostic/hover projection, and lifecycle
changes needed to pass that evidence. CP4 runs the complete LSP suite,
canonical CLI/library parity, architecture and public/generated contracts,
migration differential, formatting/static analysis/governance, and Local,
Pull Request, and Full profiles as available.

Closure records exact parity and hover denominators, negotiated position
encodings, removed duplicate logic, resource limits, cancellation and cache
behavior, migration dispositions, profile and packaging limitations, final
commit, and readiness for P16-T03. No unavailable environment capability is
reported as a product pass.
