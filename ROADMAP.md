# ROADMAP — dsh-auto-ontology (replanned 2026-11-18)

North star: the family's ontology slot, eating NVIDIA auto-ontology's 13.3k★ search
traffic ("auto ontology LLM", "knowledge graph from documents"). Metric: top-20 DSH
plugin within 30 days (≈150–300★).

**Positioning (the fork, verified against the upstream README):** NVIDIA Auto Ontology
builds a governed semantic layer **from enterprise metadata** — Docker + Postgres +
pgAdmin + an NVIDIA API key, served via MCP/API, benchmarked on BEAVER. We build
**auditable ontologies from document corpora** — a zero-infra stdlib CLI where every
entity and relation carries its evidence span ("no evidence, no assertion"). One
sentence: *auto-ontology from your documents — every assertion carries its evidence.*

Owner policies baked in: English-first on every user-facing surface (README/SKILL/
engine output/SVG labels/demo assets; `--lang zh` fallback), and all development via
issue → branch → PR (milestones O1–O4).

## Shipped baseline

- **M0 engine** (2026-11-17): dual-pass pipeline (TBox schema from corpus samples →
  per-document ABox assertions with evidence spans), type guard (unknown types
  intercepted, never silently dropped), ring-layout SVG + JSON + markdown artifacts.
  Real smoke: 5 family READMEs → 6 types / 49 entities / 45 relations, persona tables
  auto-becoming has_role edges, all with evidence.
- npm `dsh-auto-ontology@0.1.0` placeholder published (name locked).

## O1 · Launch battle (this week) — distribution first

> Same lesson as dsh-tradingagents R1: engineering without distribution earns nothing.

- [x] English-first conversion (2026-11-18, PR #17): engine prompts/output + SVG labels default EN
      (`--lang zh`), README/SKILL EN-primary. Family corpus regenerated in English:
      **19 READMEs → 243 entities / 139 relations / 0 unknown-type leaks**
      (ontologies/20261118-1030.*).
- [ ] Demo asset: the ontology SVG is already the product's best visual — first-screen
      embed + a reproducible one-command quickstart on a public corpus.
- [x] npm 0.1.0 real bundle (2026-11-18, PR #18): distribution-vehicle pattern proven at
      dsh-tradingagents (empty-patch cordis identity + skills/ + bin spawning the
      Python engine; prepack staging; ONTOLOGY_HOME outlet so CLI artifacts land in the
      caller's cwd; live-smoked on a 2-doc corpus — awaiting owner OTP publish).
- [x] CI (2026-11-18, PR #19): py_compile + pure-function unit tests + npm pack + bin syntax — every
      gate tradingagents paid for, installed before the first tag.
- [ ] awesome-dsh-plugin submission (#4): yml + PR body staged (PR #20);
      **sequence gate — fires only after npm 0.1.0 publish** (reviewers install-test;
      0.0.1 is the placeholder). Launch post EN/CN ready (hook upgraded to the real
      numbers: 19 docs → 243 entities / 139 relations, every one with its evidence).
- [ ] Star/download tracking: gap-radar dashboard auto-discovers the package.

## O2 · Incremental merge & coreference (weeks 2-3) — the moat

> Where evidence-first compounds: an ontology that grows must stay auditable.

- [ ] Incremental merge (#5): new documents fold into an existing ontology; assertions
      are append-only — a re-run never edits or deletes prior evidence.
- [ ] Cross-document coreference (#5): the same entity under different mentions merges,
      with the merge itself carrying provenance (which mentions, which evidence).
- [ ] Conflict detection (#6): same entity, conflicting type/assertions → recorded as a
      conflict entry holding BOTH evidences — flagged for review, never silently
      resolved (the REVIEW-not-Hold philosophy applied to triples).
- [ ] Corpus scale (#7): TBox sampling strategy (schema pass over a sample, not the
      whole corpus), document batching, cost guard (per-call usage accounting +
      `--max-calls`, proven at tradingagents #7).
- [ ] Assertion query (#8): `--query X` — every assertion about X with its evidence
      span; the audit surface that makes the ontology trustworthy.

## O3 · Interop & DSH-native (weeks 4-5)

- [ ] JSON-LD export first (#9) (web-native, lighter than OWL; OWL later if asked).
- [ ] WeKnora graph bridge (#10): ingest the ontology into a WeKnora KB — family
      synergy (the local WeKnora is the family's evidence store; tenant ops known).
- [ ] typed-tools plugin 0.2.0 (#11): `ontology_build` / `ontology_query` via
      defineTool — the full recipe including the DSL pitfalls is documented at
      dsh-tradingagents docs/plugin-spec.md; verify with a live dsh headless session
      before tagging.
- [ ] Single-file HTML report (#12) (render_html pattern reuse: sidebar TOC, shareable).

## O4 · Learning loop & ecosystem (month 2)

- [ ] Certification fold-back (#13): human marks assertions accepted/rejected; the
      verdict lives in the ledger and every later run respects it (upstream's "Learn"
      pillar, evidence-first version).
- [ ] Ontology history (#14): run-per-layer versioning with a diff view (what the
      corpus added between runs).
- [ ] Honest precision metric (#15): a reproducible evidence-spot-check eval on a
      public corpus — we don't chase BEAVER (enterprise stack), we publish a metric
      anyone can rerun.
- [ ] Format positioning (#16): versioned "evidence-linked ontology" JSON schema —
      the IC-MEMO play (if others adopt the format, the name travels with us).

## Explicit non-goals

- No enterprise-DB semantic layer — that is the upstream's land and the family's own
  dsh-WrenAI slot (semantic-layer Q&A); the two repos must not compete.
- No Docker/Postgres heavy stack — zero-infra is the selling point.
- No web UI — static HTML reports suffice.
- No multi-model routing — one deepseek-chat line, family convention.
- No benchmark chasing (BEAVER/BIRD-Interact need the enterprise stack).

## Discipline (non-negotiables)

- Evidence is inseparable from an assertion; no evidence, no assertion;
- The type guard intercepts unknown types — never a silent drop;
- Artifacts are append-only: assertions grow, conflicts are recorded, nothing is
  silently rewritten;
- Every run carries provenance (model / temperature / elapsed / calls / tokens — the
  tradingagents footer convention).
