# Evidence-Linked Ontology — format v0.3

An open artifact format for LLM-built ontologies where **evidence is first-class**:
no assertion exists without its verbatim source quote. If another tool adopts it,
assertions stay auditable across implementations. Versioned: v0.1 is the
dsh-auto-ontology v2 engine shape; **v0.2 adds build-time grounding verdicts**;
**v0.3 records where a quote was read (`chunk_id`) and names the judge behind an
applied re-typing (`judge`)**. Backward-compatible — every addition is optional,
and an artifact valid under an earlier version is valid under this one.

## Contract (normative)

1. **Top level** — required keys: `domain` (string), `built_at` (ISO-8601),
   `tbox` `{entity_types: [{name, desc?}], relation_types: [...]}`,
   `abox` `{entities: [...], relations: [...]}`, `stats` (object),
   `provenance` (object; SHOULD carry model/temperature/elapsed_s/calls/
   tokens_in/tokens_out). Optional: `conflicts`, `flagged_unknown_types`,
   `merge_log`, `certifications`; since v0.2 `flagged_ungrounded`; since v0.3,
   on a build that read a knowledge base, `provenance.kb` — `{id, limit,
   skipped_documents, documents, chunks}` (*Building from a knowledge base*).
2. **Entity** — required: `name` (string), `type` (∈ tbox.entity_types names),
   `evidences`: non-empty array of evidence objects (clause 4) whose `quote`
   is a verbatim span from the source document. Optional: `aliases` (array),
   `docs` (array of source doc names), and since v0.2 `type_grounding`
   (boolean).
3. **Relation** — required: `subject`, `predicate`, `object` (strings; endpoints
   SHOULD be entity names), `evidences` as above. Optional since v0.2:
   `grounding` (boolean).
4. **Evidence** — `{quote, doc}` plus optional fields:
   - `grounded` (boolean, v0.2): the build's verdict on whether THIS quote
     grounds the claim it is attached to. A build that ran a grounding pass
     sets `grounded` on every quote it judged.
   - `reason` (string): why the quote does not ground the claim — present on an
     ungrounded evidence. Since v0.3 it may also stand on a **grounded**
     evidence, and only beside `judge`.
   - `judge` (string, v0.3): the model whose grounded verdict paid for the
     claim. Written only by `apply --proposals` (below), on the quote it
     brought — never by a build.
   - `chunk_id` (string, v0.3): the WeKnora chunk the quote was read from. On
     every evidence a knowledge-base build writes; a file build never writes
     one.

   `judge` and `reason` never stand without `grounded`.
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
   existing name with a quote that does not ground it (the evidence is as in
   clause 4). Kept and flagged; it is not a conflict. It becomes one (clause 7)
   only when a grounded quote says so.
7. **Conflicts** — `{entity, types: {typeA: evidence, typeB: evidence}}`: both
   sides' evidence MUST be preserved (each as in clause 4); a conflict is never
   silently resolved.
8. **Certifications** — keyed by name-match key: `{name, type, verdict:
   accept|reject, at, note?, evidence}`; a verdict that travels with the
   artifact; later folds respect it. Optional since v0.2: `actor` (string)
   naming who issued it — an agent applying a verdict MUST say so. A reject
   written by `apply --proposals` (below) carries two more optional fields:
   `retyped_to {type, quote, doc, judge, run?, reason?, chunk_id?}` — the typing
   the name was moved to and the judge-grounded quote that paid for it, with
   its chunk when the source was a knowledge base — and, when the name had been
   re-typed before, `also_rejects` (array of type names): the typings rejected
   earlier, which later folds keep suppressing. One certification per name: a
   later verdict on the same name replaces the earlier one.
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
   - `build` — the run that wrote the artifact: `provenance` (with its `kb`
     block when it read a knowledge base), `stats`,
     `tbox {entity_types, relation_types, entity_type_descs,
     relation_type_descs}` — the type definitions ride along, so a consumer
     can judge or propose against them without opening the artifact.
   - `fold` — one per `merge_log` entry: `merge` (the entry without its alias
     list) and `alias_merges [{canonical, alias}]`.
   - `assertion` — **one per evidence quote**, the append-only unit: `claim`,
     `subject` (`{name, type}` for an entity, `{subject, predicate, object}`
     for a relation), `evidence {quote, doc, chunk_id?}`, `verdict` (`grounded`
     | `ungrounded` | `null` = never judged), `by`, and `reason` on an
     ungrounded quote or beside a named judge.
   - `certification` — `claim`, `subject {name, type}`, `evidence` (the
     strongest quote, as the verdict cites it — with its `chunk_id` when it has
     one), `verdict` (`accept` | `reject`), `by` (the actor), `note`, and
     `retyped_to` / `also_rejects` when the verdict re-typed the name.
   - `conflict` — `subject {name, types: {type → evidence}}`: both sides, as
     kept, each with its `chunk_id` when it has one.
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
   nothing. Who judged is part of what an assertion says: a re-typing exported
   before v0.3 (`by: judge`) and again under v0.3 (`by: judge:<model>`) is two
   events, and a store holding both shows that quote twice.
6. **Determinism** — the same artifact exports to the same events in the same
   order; nothing depends on the clock.
7. **What the artifact does not know** — when one quote was folded (`at` is
   `null` on an `assertion`) and, for a quote judged inside a build, which judge
   model judged it (`by` is `judge`; the `build` event names the judge of its
   own run, and only when a grounding pass ran). An evidence that names its
   judge (v0.3) exports `by: judge:<model>`.

`validate_format.py` does not check streams. CI checks the exporter against
the committed artifact: same bytes twice, ids independent of file names, one
event per quote, verdicts and certification actors carried.

### The trip back — `apply --proposals`

A consumer that proposes a re-typing (dsh-EvoOntology's adapter is the first)
writes a proposals file and hands it back: `{run_id?, judge_model?, proposals:
[{name, from_type, to_type, quote, doc, why, grounded, judge_reason?,
chunk_id?}]}` — the chunk the quote was read from, when the layer was built
from a knowledge base.
`auto-ontology apply --proposals FILE --actor agent:<name> [--from x.json]`
turns each applied proposal into a new certification and a new assertion —
never an edit of an old one. `--actor` is required and MUST start with
`agent`: this path applies a machine's proposals, a person's verdict is
`--certify`.

1. **Only `grounded: true` is applied.** A quote no judge grounded re-types
   nothing; it is counted and skipped.
2. **A stale proposal is reported, not forced.** Stale: the name is gone from
   the artifact, or is typed something other than `from_type` since the stream
   was exported.
3. **`to_type` must be in the artifact's TBox** — the type guard holds on the
   way back too.
4. **A person's verdict is not overwritten.** When the certification in force
   on the name was not issued by an `agent:` actor, the name is not touched.
5. **What is written.** A `reject` certification on the OLD typing — actor, a
   note naming the judge, the strongest quote, `retyped_to` — and a new
   assertion of the new type whose first evidence is the judge-grounded quote,
   carrying the judge's name (`judge`), its reason (`judge_reason`), and the
   chunk id when the proposal names one. A proposal that names no judge leaves
   the quote without `judge` and without a reason. The name's other quotes
   follow **unjudged** — their verdicts were about the old claim; their chunk
   ids stay. Aliases, docs and every relation the name endpoints, with its
   evidences and verdicts, are carried over unchanged.
6. **Replay adds nothing.** After one apply every proposal is stale against
   the new artifact, and nothing is written.
7. **A name re-typed twice keeps rejecting its first typing** — the second
   certification lists it in `also_rejects`, so the next fold does not let it
   back in as a conflict.
8. **The stream tells both halves.** Re-exported, the artifact carries the
   rejected certification (endorsed `false`) and the new assertion (endorsed
   `true`) — the latter with `by: judge:<model>` and the judge's reason. The
   old typing's assertion events are in the earlier export, not the new one —
   a consumer keeps both.

## Building from a knowledge base — `build --kb`

A WeKnora knowledge base is a corpus whose documents are already parsed and
cut into chunks. `auto-ontology build --kb <id>` — or the typed tool with `kb`
— reads one directly, and makes every assertion addressable inside the base.

- **One chunk is one document**, read whole. (A file build reads a document's
  first 6,000 characters.)
- **The reading order is fixed**: documents by title, a document's chunks by
  index. `--limit N` reads the first N chunks of that order and stops there,
  even in the middle of a document — it saves model calls, not API reads (the
  chunk list of the document it stops in is still fetched whole).
- **Only a document whose parse completed is read.** The others are counted
  in `provenance.kb.skipped_documents` by status — a document still parsing
  has nothing to quote yet. Only text chunks are read: a generated summary is
  not a source; a disabled or blank chunk is skipped.
- **Every evidence carries `chunk_id`** — on entities, relations, conflicts,
  the type guard's catches and the ungrounded clashes alike, in the artifact
  and in the stream. `doc` stays the document's title, the name a person knows
  the source by; `--query` prints both.
- **The schema pass samples documents**, not chunks: each sampled document is
  represented by its opening as chunked.
- **The verbatim gate is unchanged**: a quote is checked against the text of
  its own chunk. A span taken from anywhere else — the prompt's label line
  included — fails the gate and stays as an ungrounded evidence.

A consumer resolves a chunk id with `GET /api/v1/chunks/by-id/{id}` and
should find the quote inside that chunk's content. The build reads
`WEKNORA_URL` and `WEKNORA_API_KEY` from the environment (and sends
`WEKNORA_TENANT_ID` as the tenant header when set) and never writes to the
base. The typed tool reads 40 chunks unless given `limit`.

**Not yet**: dsh-EvoOntology's projection keeps a quote's `chunk_id` on its
Terms, but its proposals do not carry one back — a re-typing that began in a
knowledge base returns without its chunk id until that adapter changes.

## Validation

`python3 scripts/validate_format.py ontologies/*.json` (or
`auto-ontology validate <files>` via the npm bin) — pure stdlib checks of
the normative clauses above; CI validates every committed artifact. v0.3
checks the new fields: `chunk_id` and `judge`, when present, are non-empty
strings; neither `judge` nor `reason` stands without `grounded`; a grounded
evidence carries a reason only beside a judge.
