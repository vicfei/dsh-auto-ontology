# Evidence-Linked Ontology — format v0.2

An open artifact format for LLM-built ontologies where **evidence is first-class**:
no assertion exists without its verbatim source quote. If another tool adopts it,
assertions stay auditable across implementations. Versioned: v0.1 is the
dsh-auto-ontology v2 engine shape; **v0.2 adds build-time grounding verdicts** and
is backward-compatible — every v0.2 addition is optional, a v0.1 artifact is a
valid v0.2 artifact.

## Contract (normative)

1. **Top level** — required keys: `domain` (string), `built_at` (ISO-8601),
   `tbox` `{entity_types: [{name, desc?}], relation_types: [...]}`,
   `abox` `{entities: [...], relations: [...]}`, `stats` (object),
   `provenance` (object; SHOULD carry model/temperature/elapsed_s/calls/
   tokens_in/tokens_out). Optional: `conflicts`, `flagged_unknown_types`,
   `merge_log`, `certifications`; since v0.2 `flagged_ungrounded`.
2. **Entity** — required: `name` (string), `type` (∈ tbox.entity_types names),
   `evidences`: non-empty array of `{quote: string, doc: string}` where `quote`
   is a verbatim span from the source document. Optional: `aliases` (array),
   `docs` (array of source doc names), and since v0.2 `type_grounding` (boolean).
3. **Relation** — required: `subject`, `predicate`, `object` (strings; endpoints
   SHOULD be entity names), `evidences` as above. Optional since v0.2:
   `grounding` (boolean).
4. **Evidence (v0.2)** — `{quote, doc}` plus optional `grounded` (boolean): the
   build's verdict on whether THIS quote grounds the claim it is attached to;
   and `reason` (string): why it does not, present on ungrounded evidences.
   A build that ran a grounding pass sets `grounded` on every quote it judged.
5. **Grounding flag (v0.2)** — derived from the evidences: `true` when some
   evidence is grounded; `false` when every evidence is judged and none is
   grounded; **absent when nothing was judged**. A quote grounds a claim iff a
   careful reader who sees only the quote, the TBox type definition and the
   source document's name would conclude the claim. A flagged assertion
   **stays in the ABox** — queryable, certifiable, never dropped: the flag is
   the whole point. `evidences[0]` SHOULD be the strongest quote the assertion
   carries (a grounded one whenever it has any).
6. **Ungrounded type clashes (v0.2)** — `flagged_ungrounded: [{entity,
   existing_type, asserted_type, evidence}]`: a different type asserted for an
   existing name with a quote that does not ground it. Kept and flagged; it is
   not a conflict. It becomes one (clause 7) only when a grounded quote says so.
7. **Conflicts** — `{entity, types: {typeA: evidence, typeB: evidence}}`: both
   sides' evidence MUST be preserved; a conflict is never silently resolved.
8. **Certifications** — keyed by name-match key: `{name, type, verdict:
   accept|reject, at, note?, evidence}`; a verdict that travels with the
   artifact; later folds respect it. Optional since v0.2: `actor` (string)
   naming who issued it — an agent applying a verdict MUST say so.
9. **Append-only discipline** (process rule): a merge never edits or drops prior
   evidence; removals happen only via certification and are recorded. A later
   fold never rewrites an earlier evidence's verdict.
10. **Legacy v1** artifacts (single `evidence` string) are readable but not
   valid — convert by folding into a v2 build.

## Validation

`python3 scripts/validate_format.py ontologies/*.json` (or
`auto-ontology validate <files>` via the npm bin) — pure stdlib checks of the
normative clauses above; CI validates every committed artifact.
