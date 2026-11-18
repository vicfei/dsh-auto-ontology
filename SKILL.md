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
```

Outputs land in `ontologies/` (typed JSON + SVG + md digest).

## Discipline

- Every assertion must carry its evidence quote — strip none, trust nothing
  without one; report flagged unknown types instead of hiding them.
- TBox comes from the corpus, not from the model's prior — say so.
- Rebuilds produce new timestamped artifacts; never edit ontologies in place.
