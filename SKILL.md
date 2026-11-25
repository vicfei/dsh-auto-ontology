---
name: dsh-auto-ontology
description: Auto ontology construction for DeepSeek Harness — two-pass LLM pipeline (TBox schema from corpus, ABox assertions per document) with evidence quotes on every entity/relation and type-guard against silent drops.
---

Use this skill when asked to turn a document corpus into a knowledge graph /
ontology ("extract a knowledge graph from these docs", "build an ontology").
Evidence is the contract. Output defaults to English; `--lang zh` switches prompts
and artifacts to Chinese (env `ONTOLOGY_LANG`).

## Run

```bash
KIT=<this-directory>
python3 $KIT/scripts/build_ontology.py --docs <dir-or-glob> --domain "<description>" --save
python3 $KIT/scripts/build_ontology.py --kb <weknora-kb-id> --domain "<description>" --save [--limit N]   # chunk-level evidence
python3 $KIT/scripts/build_ontology.py --proposals <run>.proposals.json --actor agent:<name>   # a judge's re-typing, applied
```

Outputs land in `ontologies/` (typed JSON + SVG + md digest).

## Discipline

- Every assertion must carry its evidence quote — strip none, trust nothing
  without one; report flagged unknown types instead of hiding them.
- From a WeKnora knowledge base (`--kb`, needs `WEKNORA_URL` /
  `WEKNORA_API_KEY`): one chunk is one document, and every evidence carries
  the `chunk_id` it was read from — never drop it when you quote an assertion
  back, it is how the claim resolves into the base.
- Grounding is judged at build time: a quote that does not support its claim
  gets one re-grounding attempt and is then flagged (`type_grounding: false` /
  `grounding: false`) — kept, queryable, certifiable, never dropped.
  `--no-ground` skips the judge, `--judge-model` picks it; an agent applying a
  certification verdict names itself with `--actor`.
- A re-typing proposed by a model (dsh-EvoOntology's adapter writes
  `runs/<run>.proposals.json`) is applied only when a judge grounded its
  quote, and lands as a certification on the old typing plus a new assertion —
  never as an edit. A person's verdict on the name stops it; `--actor` must
  start with `agent`.
- TBox comes from the corpus, not from the model's prior — say so.
- Rebuilds produce new timestamped artifacts; never edit ontologies in place.
