# No-match explanation 1.0

This directory owns the independently versioned
`strling.no-match-explanation@1.0.0` structured result contract. The schema,
reason taxonomy, verification corpus, and authored examples are authoritative
for this result’s shape and evidence classifications. They do not revise
Semantic IR, semantic explanation model 1.0, matching semantics, target
profiles, target artifacts, or compiler protocol 1.0.

The result separates match outcome from explanation quality. A bounded
canonical evaluation may report `matched`, `no_match`, `unknown`, or
`unavailable`; only a complete no-match result may classify its localized cause
as `proven` or `likely`. Resource exhaustion and missing semantic or target
facts remain `unknown`. Unsupported or unresolved completed target plans remain
`unavailable`.

Subjects are inputs to the producer but are not echoed in result documents.
Results retain a subject SHA-256 digest and bounded length metadata. Finding
locations use half-open UTF-8 byte coordinates.

Validation:

```text
python3 -m tooling.no_match_explanation_contract
```
