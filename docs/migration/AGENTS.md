# Migration-record agent guidance

Status: transitional

Canonical migration authority: [README.md](README.md), [ledger.md](ledger.md),
and task records under `records/`, subordinate to permanent governance and
versioned specifications.

Owner: STRling Program Owner.

Introduced because: the active architecture migration retains historical
implementations, compatibility evidence, and sequenced verification records
while canonical contracts and the reference kernel converge.

Removal trigger: the migration ledger is closed and remaining transitional
allowances have been retired or moved to durable canonical policy.

Review trigger: every architecture-migration task closure, profile/release
certification change, or ratification that satisfies a recorded transition.

Migration records are control and evidence, not product or semantic authority.
Keep temporary task IDs, sequencing, and checkpoint detail in this subtree.
Do not leak them into permanent source comments, product documentation,
generated output, release notes, or commit subjects. Preserve historical
records; add explicit completion, correction, or supersession evidence rather
than rewriting their meaning.
