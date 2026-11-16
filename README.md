# dsh-auto-ontology — auto ontology construction with evidence, for DeepSeek Harness

**Feed it documents; get a typed ontology (TBox + ABox) where every entity and
relation carries its source quote. No evidence, no assertion; unknown types are
flagged, never silently dropped.**
**喂文档，得带类型的本体（TBox+ABox）——每条实体/关系带原文证据。无证据
不落库；未知类型标注拦截，绝不静默丢弃。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![auto-ontology Apache-2.0](https://img.shields.io/badge/upstream-auto--ontology%20Apache--2.0-76b900)](https://github.com/NVIDIA/auto-ontology)

> Implements the concept of [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)
> (13.3k★) natively for DSH, with the family's evidence discipline. Clean-room,
> zero upstream code. Not affiliated. Family: the 12-repo quant stack + [dsh-WrenAI](https://github.com/vicfei/dsh-WrenAI).

## Why (ontology plugins exist — none does LLM auto-construction with evidence)

| | ontology viewers/bridges (catalog) | **dsh-auto-ontology** |
|---|---|---|
| Builds ontologies | no (view/bridge existing) | **two-pass LLM pipeline: TBox schema from corpus, then ABox assertions per doc** |
| Trust | — | **every entity/relation carries an evidence quote**; no-evidence assertions don't land |
| Type safety | — | instances must ∈ TBox; unknown types **flagged, never dropped** |
| Output | files | typed JSON + zero-dep SVG cluster graph + markdown digest |

## Quick start

```bash
git clone https://github.com/vicfei/dsh-auto-ontology && cd dsh-auto-ontology
python3 scripts/build_ontology.py --docs <dir-or-glob> --domain "<描述>" --save
```

Real smoke (2026-11-17): fed **5 of our own family READMEs**, asked for the
"DSH quant-plugin ecosystem" ontology — got **6 entity types / 49 entities /
45 relations**, including `(dsh-ai-hedge-fund) -[inspired_by]-> (ai-hedge-fund)`
with evidence `Inspired by virattt/ai-hedge-fund`, and the persona table parsed
into `has_role` edges. The extractor even kept type discipline: 0 unknown-type
leaks. `ontologies/*.json|svg|md` carry the full graph with evidence.

## Status & roadmap

v0 two-pass engine smoke-tested. [ROADMAP](ROADMAP.md): M1 incremental merge +
cross-doc coreference; M2 OWL/JSON-LD export + WeKnora graph-KB bridge.

## License

MIT; concept credit to Apache-2.0 upstream — zero upstream code used.
