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

## Trajectory stream — `ao-trajectory/0.1`

An artifact is a *state*: what is asserted now. A consumer that evolves a layer
— dsh-EvoOntology's adapter is the first — needs *what happened*: which claims
were made, which quote came with each, what the judge said, what a human or an
agent decided. `auto-ontology export` turns an artifact into that stream. It
reads the artifact and calls no model.

**Contract (normative).**

1. **Encoding** — newline JSON (NDJSON), UTF-8, one event per line, nothing
   else. `auto-ontology export a.json b.json` concatenates the streams in the
   order given, with `seq` running on across them.
2. **Envelope (every line)** — required: `schema` (exactly `ao-trajectory/0.1`),
   `id`, `seq` (the line's position, from 0), `kind`, `at` (ISO-8601, or
   `null` when the artifact does not record the time), `agent` (who did the
   work), `summary` (one line, human-readable), `domain`,
   `artifact {built_at, source, model, judge}`, and `endorsed` — `true`,
   `false` or `null`.
3. **Kinds**, in this order within one artifact:
   - `build` — the run that wrote the artifact: `provenance`, `stats`,
     `tbox {entity_types, relation_types}`.
   - `fold` — one per `merge_log` entry: `merge` (the entry without its alias
     list) and `alias_merges [{canonical, alias}]`.
   - `assertion` — **one per evidence quote**, the append-only unit: `claim`,
     `subject` (`{name, type}` for an entity, `{subject, predicate, object}`
     for a relation), `evidence {quote, doc}`, `verdict` (`grounded` |
     `ungrounded` | `null` = never judged), `by`, and `reason` on an
     ungrounded quote.
   - `certification` — `claim`, `subject {name, type}`, `evidence` (the
     strongest quote, as the verdict cites it), `verdict` (`accept` | `reject`),
     `by` (the actor), `note`.
   - `conflict` — `subject {name, types: {type → evidence}}`: both sides, as
     kept.
   - `unknown_type` — `claim`, `subject {name, type}`, `evidence`: the type
     guard's catch.
   - `ungrounded_clash` — `subject {name, existing_type, asserted_type}`,
     `evidence`.
4. **`endorsed`** — `true`: a quote the judge grounded, or an accepted
   certification. `false`: a quote the judge rejected, or a rejected
   certification. `null`: never judged, or a kind that asserts nothing (build,
   fold, conflict, unknown type, clash).
5. **`id`** — `aot_` + the first 16 hex digits of the SHA-1 over the event's
   kind and what it says (for an `assertion`: claim, evidence, verdict, by) —
   never its position, its file name or the artifact it was read from. The
   same quote judged the same way in two artifacts is one event. **A consumer
   that replays a stream MUST key on `id`**: that is what makes a replay add
   nothing.
6. **Determinism** — the same artifact exports to the same events in the same
   order; nothing depends on the clock.
7. **What the artifact does not know** — when one quote was folded (`at` is
   `null` on an `assertion`) and which judge model judged it (`by` is `judge`;
   the `build` event names the judge of its own run, and only when a grounding
   pass ran).

`validate_format.py` does not check streams. CI checks the exporter against
the committed artifact: same bytes twice, ids independent of file names, one
event per quote, verdicts and certification actors carried.

## Validation

`python3 scripts/validate_format.py ontologies/*.json` (or
`auto-ontology validate <files>` via the npm bin) — pure stdlib checks of the
normative clauses above; CI validates every committed artifact.
