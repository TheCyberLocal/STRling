# Semantic STRling frontend contracts

Semantic STRling is the flagship textual authoring language. Its current
ratified source contract is [`1.0/`](1.0/) with frontend identity
`strling.semantic`, dialect version `1.0.0`, and exact in-source edition
selector `semantic strling 1.0;`.

The contract is specification-first: it defines syntax, formatting, source
diagnostics, and deterministic mapping to canonical Semantic IR before parser
or formatter implementation. It never selects a target or embeds target regex.
