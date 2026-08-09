# Dev Donor Capability Inventory

## Comparison identity

-   Donor: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
-   Governed comparison commit:
    `4abc8ec71b4466a13be19fb0b6435c7a6a6b6b13`
-   Merge base: `d41b0b73fea6c62f7bb32473f190cf4c8c9f14bc`
-   Relationship: zero donor-only commits; governed branch 36 commits ahead
-   Authoritative inventory: [`donor-inventory.json`](donor-inventory.json)

The governed branch contains the complete donor ancestry. Accordingly,
`absent-from-governed` is not used: the inventory distinguishes unchanged
donor-origin assets, behavior-neutrally modified assets, superseded approaches,
and development artifacts already removed by hygiene work. The comparison
reviewed all 16 commits in `main..dev`, the 259-file donor delta, the complete
`dev..governed` delta, and implementation/test context for every highlighted
subsystem.

## Disposition summary

| Disposition | Count | Most significant capabilities                                                                                                              |
| ----------- | ----: | ------------------------------------------------------------------------------------------------------------------------------------------ |
| preserve    |     6 | Conformance schema, Essential source data, pathological emitter inputs, VS Code client/configuration                                       |
| port        |     8 | Structured diagnostic contracts, consolidated Python intelligence, island extraction, diagnostics, hover, tokens, navigation, code actions |
| rewrite     |     7 | Hint engines, duplicated compilers, safety planning, Essential helpers, packaging, LSP semantic coupling, diagnostic production            |
| retire      |     3 | TypeScript oracle/parity tooling, vendored LSP transport, legacy audit certification                                                       |
| evidence    |     4 | Binding edge tests, diagnostic/parser regressions, shared fixtures, emitter audits                                                         |
| discard     |     1 | One capability family covering temporary, binary, packaged, cache, and scratch artifacts                                                   |

## Preserve

-   `conformance-fixture-schema` — keep the governed structured contract while
    replacing TypeScript-oracle wording through separately versioned work.
-   `essential-standard-library-definition` — retain registry, AST data,
    citations, and examples as product-definition input; ratify authority and
    exact semantics before reuse.
-   `emitter-pathological-input-corpus` — retain adversarial source inputs and
    review outcomes against target-profile contracts.
-   `vscode-language-client` — retain the thin editor client, language
    configuration, and branding; redirect it to the canonical service.
-   `engineering-contribution-guidance` — retain only guidance consistent with
    the Engineering Constitution and authority hierarchy.
-   `lua-pcre2-runtime-setup` — retain the binding runtime setup concern and add
    platform/setup smoke evidence.

## Port

-   `structured-diagnostic-result-contracts` — consolidate codes, ranges,
    severity, warnings, result payloads, and serialization into versioned
    contracts while keeping idiomatic host mappings.
-   `python-intelligence-consolidation` — transfer useful analysis, preview,
    token, registry, symbol, navigation, and formatting algorithms behind the
    canonical compiler/tooling interface.
-   `embedded-language-island-extraction` — transfer the boundary spec,
    scanners, virtual documents, and bidirectional coordinate mapping as an
    authoring frontend.
-   `lsp-diagnostics` — retain projection, clamping, caching, and debouncing;
    replace diagnostic production with canonical results.
-   `lsp-hover-completion` — retain the editor experience after stdlib registry
    authority and protocol behavior are specified and tested.
-   `lsp-semantic-tokens` — retain the feature after token legend,
    delta-encoding, and embedded projection receive a versioned contract and
    tests.
-   `lsp-navigation-formatting` — retain symbols, definitions, and source edits
    through canonical symbol/format contracts.
-   `lsp-code-actions` — retain diagnostic-driven edits after ReDoS rewrite
    safety is specified and proven.

## Rewrite

-   `duplicated-binding-hint-engines` — one canonical diagnostic engine must
    replace static TypeScript string parity across 17 bindings.
-   `duplicated-binding-compilers` — accepted behavior remains evidence, but
    independent parsers, compilers, validators, IRs, and emitters conflict with
    the single semantic authority.
-   `emitter-safety-planning` — move lookbehind, depth, and ReDoS decisions into
    semantic analysis and target planning rather than duplicated serialization.
-   `essential-binding-helpers` — keep idiomatic APIs while deriving meaning
    from one versioned stdlib definition.
-   `extension-assembly-installation` — replace mutable ownership/cache repair
    with reproducible packaging and installed-artifact smoke tests.
-   `lsp-python-semantic-coupling` — preserve LSP behavior while routing all
    semantics through the canonical interface.
-   `duplicated-diagnostic-implementations` — retain host exception conversion,
    but centralize codes, ranges, ordering, severity, and warnings.

## Retire

-   `typescript-oracle-parity-tooling` — TypeScript output may remain temporary
    differential evidence but cannot author semantic expectations.
-   `vendored-lsp-transport` — replace copied pygls/lsprotocol modules with
    pinned, provenance-tracked dependencies or a deliberately owned protocol
    layer.
-   `legacy-audit-certification` — deterministic structured certification
    supersedes environment-count, wall-clock, and stdout assumptions.

## Preserve as evidence only

-   `per-binding-emitter-edge-tests`;
-   `diagnostic-parser-regressions`;
-   `implementation-derived-shared-fixtures`; and
-   `emitter-hardening-audits`.

These remain high-value differential material. They do not become future
implementation or semantic authority merely because current bindings pass them.

## Discard

`temporary-generated-development-artifacts` groups the donor `.new` source
copies, compiled C and inspection binaries, packaged VSIX, Ruby status cache,
scratch island-boundary file, and audit status file. The governed branch already
removed all nine paths. None is a product capability or preservation obligation.

## Highest-value carry-forward

The first product/specification architecture work should explicitly account for:

1. structured diagnostics and result contracts;
2. the accepted semantic and pathological input evidence needed for differential
   migration;
3. the standard-library product decision represented by Essential source data;
4. island extraction and the editor feature set as authoring/tooling consumers;
5. target planning and safety requirements currently scattered across emitters;
   and
6. the boundary between canonical semantics and thin binding/editor adapters.
