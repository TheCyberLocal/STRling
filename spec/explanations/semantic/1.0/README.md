# Semantic explanation model 1.0

This directory owns the independently versioned `1.0.0` structured semantic
explanation contract. The schema and authored JSON examples are authoritative
for explanation data shape. They do not revise Semantic IR, CompileResult 1.0,
diagnostic meaning, target profiles, or the STRling Semantic Specification.

The model has two rendering-ready data forms in one document:

-   `concise` is a bounded program summary; and
-   the remaining collections are the detailed entity graph.

Every detailed entity declares whether its evidence is a `semantic_fact`,
`target_plan`, `diagnostic_advice`, or `uncertainty`. Target-neutral entities
remain unchanged when a target projection is added. Unknown evidence is always
represented explicitly.

The checked text files under `../generated/` are non-normative views generated
from the authored structured example. They cannot override the JSON model.

Validation:

```text
python3 -m tooling.explanation_contract
python3 -m tooling.explanation_fixtures --check
```
