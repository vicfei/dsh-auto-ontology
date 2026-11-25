# dsh-auto-ontology

**Auto ontology construction with evidence, for DeepSeek Harness** — feed it
documents, get a typed ontology (TBox + ABox) where every entity and relation
carries its source quote. No evidence, no assertion; unknown types are flagged,
never silently dropped.

```bash
npm i -g dsh-auto-ontology
auto-ontology build --docs ~/my-corpus/*.md --domain "internal design docs" --save
auto-ontology build --kb <weknora-kb-id> --domain "..." --save   # from a WeKnora knowledge base
```

- Zero-infra: `python3` (stdlib) + a DeepSeek key you already have. No Docker,
  no database — the deliberate opposite of the enterprise-metadata stacks.
- Two-pass pipeline: TBox schema from corpus samples → per-document ABox
  assertions, each with an evidence span.
- Chunk-level evidence: `build --kb` reads a WeKnora knowledge base's parsed
  chunks (needs `WEKNORA_URL` / `WEKNORA_API_KEY`; `--limit N` to bound it) and
  puts the `chunk_id` on every evidence — each assertion resolves back into
  the base.
- Grounding pass: every type and relation claim is judged against its own
  quote; an ungrounded one is flagged (`type_grounding: false`), never dropped.
- Outputs: typed JSON (every assertion + evidence), zero-dep SVG cluster graph,
  markdown digest.
- `auto-ontology export x.json`: the artifact as an event stream
  (`ao-trajectory/0.1`, newline JSON) — what dsh-EvoOntology's adapter consumes.
- `auto-ontology apply --proposals run.proposals.json --actor agent:<name>`:
  a judge-grounded re-typing comes back as a certification, never as an edit.
- Register the DSH skill:
  `ln -s "$(npm root -g)/dsh-auto-ontology/skills/dsh-auto-ontology" ~/.dsh/skills/dsh-auto-ontology`

Implements the concept of [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)
(13.3k★, Apache-2.0) natively for DSH — clean-room, zero upstream code, not
affiliated. **Not investment/enterprise advice.**

Full docs: [github.com/vicfei/dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology)
