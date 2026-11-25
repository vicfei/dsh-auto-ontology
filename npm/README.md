# dsh-auto-ontology

**Auto ontology construction with evidence, for DeepSeek Harness** — feed it
documents, get a typed ontology (TBox + ABox) where every entity and relation
carries its source quote. No evidence, no assertion; unknown types are flagged,
never silently dropped.

```bash
npm i -g dsh-auto-ontology
auto-ontology build --docs ~/my-corpus/*.md --domain "internal design docs" --save
```

- Zero-infra: `python3` (stdlib) + a DeepSeek key you already have. No Docker,
  no database — the deliberate opposite of the enterprise-metadata stacks.
- Two-pass pipeline: TBox schema from corpus samples → per-document ABox
  assertions, each with an evidence span.
- Grounding pass: every type and relation claim is judged against its own
  quote; an ungrounded one is flagged (`type_grounding: false`), never dropped.
- Outputs: typed JSON (every assertion + evidence), zero-dep SVG cluster graph,
  markdown digest.
- Register the DSH skill:
  `ln -s "$(npm root -g)/dsh-auto-ontology/skills/dsh-auto-ontology" ~/.dsh/skills/dsh-auto-ontology`

Implements the concept of [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)
(13.3k★, Apache-2.0) natively for DSH — clean-room, zero upstream code, not
affiliated. **Not investment/enterprise advice.**

Full docs: [github.com/vicfei/dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology)
