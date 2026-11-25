# dsh-EvoOntology — a self-evolving ontology layer for DeepSeek Harness

**An evolution engine with evidence on every record: trajectories in, hypothesis-framed
rounds out, nothing publishes without winning an evaluation. Phase 1 powers the
family's own agents; the same engine grows into the full document/data ontology layer.**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![npm](https://img.shields.io/npm/v/dsh-evoontology)](https://www.npmjs.com/package/dsh-evoontology)

> Implements the concept of [ruc-datalab/EvoOntology](https://github.com/ruc-datalab/EvoOntology)
> (1.3k★, MIT, arXiv 2609.15779) natively for DSH — clean-room, zero upstream code,
> not affiliated. [中文文档](README.zh-CN.md)
> Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology) ·
> [dsh-WrenAI](https://github.com/vicfei/dsh-WrenAI)

## Why

Agents re-learn what they already learned. Every session rediscovers the same
tables, the same definitions, the same dead ends — because what an agent learned
lives and dies inside one conversation. The fix is not a bigger context window;
it is a **layer that remembers, and that only changes when the evidence says so**:

- **Trajectories are the corpus.** What agents actually did — decisions, outcomes,
  quotes — is appended to an evidence-linked store, never edited.
- **Evolution is hypothesis-framed and budgeted.** Rounds carry a formal
  hypothesis and a frozen budget; exhaustion marks the run incomplete and needs
  an explicit extension. No silent midnight self-modification.
- **Nothing publishes without winning.** A candidate version only replaces the
  incumbent when it beats it on an evaluation adapter — rerunnable, seeded,
  reported as-is (see our sibling repo's honest 10%).
- **Evidence on every record.** The five-record schema (Term, Mapping, Relation,
  Constraint, Evidence) inherits the family's evidence-linked format: no record
  without a verbatim source span.

## The route (phase 1 = the kernel, phase 3 = the full layer)

| Phase | Ships |
|---|---|
| **E1 · evolution kernel** | trajectory store (append-only, evidence-linked) · threshold triggers (N trajectories / M days) · hypothesis rounds under a frozen budget · evaluation-gate adapter contract · SQLite semantic-layer seed on the README |
| **E2 · family integration** | the family's own agents plug in (verdict ledgers, certification flows, drift alarms) as first proof of generality · npm bundle + typed tools |
| **E3 · semantic layer** | workload collection (questions / same-data history / evidence-grounded generation) · Term→table/column mapping extraction · `browse` answer-time semantics · the full EvoOntology concept, DSH-native |
| **E4 · ecosystem** | bounded connector breadth · visualization · the evidence-linked evolution records as a versioned open format |

Non-goals, stated up front: MCP-first serving (DSH typed tools are the native
surface), chasing eight database connectors, benchmark leaderboard chasing,
and competing with the family's own dsh-WrenAI on Q&A (this engine evolves
layers; WrenAI answers questions through them).

## Status

**Phase E1 complete** — the zero-LLM kernel ships:

```bash
npm i -g dsh-evoontology
evoontology seed --sqlite mydata.db              # Term+Mapping from DDL, zero LLM
evoontology evolve start --hypothesis "..."      # open a budgeted evolution run
evoontology validate .evo/records.jsonl          # evidence-linked format conformance
```

See [ROADMAP](ROADMAP.md) for the full plan (E2 family integration → E3 semantic
layer → E4 ecosystem).

## License

MIT; concept credit to the MIT upstream — zero upstream code used.
