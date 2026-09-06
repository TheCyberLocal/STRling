# Emitted-artifact requirement authority

Status: implementation design and completion record for the bounded pre-4.0
semantic-hardening campaign. This record strengthens requirement accounting; it
does not claim that the remaining cross-engine semantics are equivalent.

## Current pipeline audit

Before this change, normalized Semantic IR was the only source of capability
requirements. Capability evaluation and portability planning correctly ran
before lowering, but each target lowering plan copied only those planned source
requirements. The PCRE2, ECMAScript, and Python `re` serializers then projected
that copied list directly into `TargetArtifact.requirements`.

That pipeline makes the source requirement set an early portability check and,
incorrectly, the final artifact authority. The structured target trees contain
enough information to identify capability-bearing output, but several serializer
forms introduce assertions that have no source-side requirement occurrence.

| Target      | Structured representation  | Source construct                         | Emitted technique                                                 | Requirement missing before this change |
| ----------- | -------------------------- | ---------------------------------------- | ----------------------------------------------------------------- | -------------------------------------- |
| PCRE2       | `Pcre2Operation` tree      | negated set containing an ASCII built-in | negative lookahead followed by a DOTALL wildcard                  | `assertions.lookahead`                 |
| ECMAScript  | `EcmascriptOperation` tree | input end or line end                    | negative or positive lookahead                                    | `assertions.lookahead`                 |
| ECMAScript  | `EcmascriptOperation` tree | line start                               | fixed-length positive lookbehind                                  | `assertions.lookbehind.fixed_length`   |
| ECMAScript  | `EcmascriptOperation` tree | before-final-line-terminator             | positive/negative lookahead plus fixed-length negative lookbehind | both assertion capabilities            |
| ECMAScript  | `EcmascriptOperation` tree | negated set containing a built-in        | negative lookahead followed by an all-input wildcard              | `assertions.lookahead`                 |
| Python `re` | `PythonReOperation` tree   | nonempty negated set                     | negative lookahead followed by a DOTALL wildcard                  | `assertions.lookahead`                 |
| Python `re` | `PythonReOperation` tree   | empty positive set                       | negative lookahead                                                | `assertions.lookahead`                 |

Target serialization, canonical contract validation, the adversarial audit, the
interop/compiler-result projections, and runtime/certification harnesses are
downstream consumers. The adversarial audit exposes the historical omission by
comparing assertion markers in controlled emitted patterns with declared
artifact capabilities; it is evidence, not the extraction implementation.

All 25 V4-H01 `REQUIREMENT_UNSOUNDNESS` findings occur at this source-plan to
artifact projection boundary. The other 121 semantic or target-limit findings
remain lowering/runtime work, and the two structured diagnostic-delivery
findings remain separate.

## Chosen contract

Source requirements describe capabilities inherent in Semantic IR and remain
the input to early capability evaluation and portability planning. Emitted
requirements describe every governed capability used by the structured target
representation, including a capability selected only as a lowering technique.
The final artifact requirement set is the deterministic union of both.

Each target owns a thin exhaustive extractor over its closed target-operation
enum. Purely structural variants are explicitly classified. The three
extractors produce one shared typed requirement vocabulary and use the same
profile evaluator as source requirements. They do not inspect or reparse final
regex text.

Reconciliation preserves every source requirement. An emitted occurrence with
the same semantic node and capability as a source occurrence is already
covered; otherwise it is lowering-introduced, evaluated against the exact
profile revision and fingerprint, and appended in canonical order. Duplicate
introduced node/capability pairs collapse deterministically. Source and
lowering-introduced requirement identities use distinct stable namespaces in
the artifact.

An introduced requirement is accepted only when the common capability evaluator
returns `Supported`, including satisfaction of every typed constraint. Explicit
unavailability, a constraint violation, an unlisted capability, a malformed
profile, or missing evidence stops lowering before serialization and carries a
structured internal failure naming the semantic node, introduced construct,
capability, exact profile, and factual disposition. The existing public
diagnostic-delivery limitation remains owned by the later diagnostic task.

## Completeness and contract identity

The target extractors use exhaustive Rust matches over every operation,
position, assertion, repetition-mode, wildcard, and character-set-member
variant. Adding a variant therefore causes a compile failure until requirement
classification is supplied. Architecture mutation tests also require the
extractors and post-lowering reconciliation call at each target boundary.

`TargetArtifact.requirements` keeps its existing serialized shape. Its ratified
meaning is clarified to be the complete artifact requirement union, rather than
source requirements alone, so no compiler-contract suite version or target
profile revision changes. The changed requirement contents participate in the
artifact's canonical JSON identity and remain uniquely and deterministically
ordered.

## Verification and audit disposition

At clean verified implementation checkpoint
`5a78c9469ed57c10521c0146894ad41d3dd25b5f`, the complete internal kernel
suite and public Rust facade pass, including the dedicated post-lowering,
synthetic restrictive-profile, artifact-identity, and target-AST completeness
tests. Local 1.14.0 passes 36/36 and Pull Request 1.19.0 passes 76/76 with no
failed, waived, unavailable, or incomplete operations.

The regenerated 205-row V4-H01 evidence contains 123 findings. All 25 historical
`REQUIREMENT_UNSOUNDNESS` findings disappear because the introduced capability
is now declared or emission is refused. The remaining 121 semantic and target-
acceptance findings stay assigned to V4-H04; the two diagnostic-delivery defects
stay assigned to V4-H05. Strict audit execution therefore remains intentionally
non-green, with zero unexpected or unaccounted findings.

## Non-goals

This work does not change emitted regex spellings, optimize character-set
lowering, broaden target support, correct wildcard/anchor/word/folding/
backreference behavior, weaken the adversarial corpus, or consume the broader
diagnostic-delivery work.
