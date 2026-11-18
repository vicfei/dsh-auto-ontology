# Evidence-Linked Ontology — format v0.1

An open artifact format for LLM-built ontologies where **evidence is first-class**:
no assertion exists without its verbatim source quote. If another tool adopts it,
assertions stay auditable across implementations. Versioned; v0.1 is the
dsh-auto-ontology v2 engine shape.

## Contract (normative)

1. **Top level** — required keys: `domain` (string), `built_at` (ISO-8601),
   `tbox` `{entity_types: [{name, desc?}], relation_types: [...]}`,
   `abox` `{entities: [...], relations: [...]}`, `stats` (object),
   `provenance` (object; SHOULD carry model/temperature/elapsed_s/calls/
   tokens_in/tokens_out). Optional: `conflicts`, `flagged_unknown_types`,
   `merge_log`, `certifications`.
2. **Entity** — required: `name` (string), `type` (∈ tbox.entity_types names),
   `evidences`: non-empty array of `{quote: string, doc: string}` where `quote`
   is a verbatim span from the source document. Optional: `aliases` (array),
   `docs` (array of source doc names).
3. **Relation** — required: `subject`, `predicate`, `object` (strings; endpoints
   SHOULD be entity names), `evidences` as above.
4. **Conflicts** — `{entity, types: {typeA: evidence, typeB: evidence}}`: both
   sides' evidence MUST be preserved; a conflict is never silently resolved.
5. **Certifications** — keyed by name-match key: `{name, type, verdict:
   accept|reject, at, note?, evidence}`; a human verdict that travels with the
   artifact; later folds respect it.
6. **Append-only discipline** (process rule): a merge never edits or drops prior
   evidence; removals happen only via certification and are recorded.
7. **Legacy v1** artifacts (single `evidence` string) are readable but not
   valid v0.1 — convert by folding into a v2 build.

## Validation

`python3 scripts/validate_format.py ontologies/*.json` (or
`auto-ontology validate <files>` via the npm bin) — pure stdlib checks of the
normative clauses above; CI validates every committed artifact.
