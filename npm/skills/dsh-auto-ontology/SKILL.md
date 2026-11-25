---
name: dsh-auto-ontology
description: Auto ontology construction for DeepSeek Harness — two-pass LLM pipeline (TBox schema from corpus, ABox assertions per document) with an evidence quote on every entity/relation and a type guard against silent drops. English-first, --lang zh for Chinese.
---

Use this skill when asked to turn a document corpus into a knowledge graph /
ontology ("extract a knowledge graph from these docs", "build an ontology").
**Evidence is the contract** — no assertion lands without its source quote, and
unknown types are flagged, never silently dropped.

## Run

`auto-ontology` must be on PATH (`npm i -g dsh-auto-ontology`).

```bash
auto-ontology build --docs <dir-or-glob> --domain "<description>" --save   # typed JSON + SVG cluster graph + md digest
auto-ontology build --docs '*.md' --domain "..." --lang zh                # Chinese prompts/artifacts
auto-ontology export ontologies/x.json > trajectory.ndjson                  # the artifact as an event stream
```

Requires `python3` (stdlib only) and a `DEEPSEEK_API_KEY` in `~/.bashrc`.
Artifacts land in `./ontologies/` (relative to where you invoke); the SVG is
the shareable overview, the JSON carries every assertion with its evidence span.

## Discipline

- Every entity/relation must carry `evidence` = a verbatim quote (up to 200
  chars — the sentence that STATES the claim, not one that merely mentions the
  name); the engine rejects no-evidence assertions.
- Grounding is judged at build time: a quote that does not support its claim
  gets one re-grounding attempt and is then flagged (`type_grounding: false` on
  entities, `grounding: false` on relations) — kept, queryable, certifiable,
  never dropped. `--no-ground` skips the judge; `--judge-model` picks it.
- Report ungrounded assertions as ungrounded — `--query X` marks each ✓ or ⚠.
- Instance types must come from the extracted TBox; unknown types are recorded
  in `flagged_unknown_types`, never silently dropped.
- Artifacts are append-only in spirit: a new run writes new files; it never
  edits a prior ontology.
- `auto-ontology export` is the artifact as events (`ao-trajectory/0.1`, one
  JSON event per line: every quote with the judge's verdict, every
  certification, merges, conflicts). Use it when another tool — dsh-EvoOntology
  first — needs what happened, not just the current state.
- `auto-ontology apply --proposals <run>.proposals.json --actor agent:<name>`
  applies a judge-grounded re-typing as a certification on the old typing plus
  a new assertion — never as an edit. Only a proposal a judge grounded is
  applied; a person's verdict on the name stops it; a replay writes nothing.
