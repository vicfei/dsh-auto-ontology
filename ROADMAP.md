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

- [x] Incremental merge + coreference (#5, 2026-11-18 PR #22): one fold store shared by
      fresh builds and `--merge`; append-only verified live (20 evidences → 30, zero lost);
      conservative coref clusters certain mentions (same type only), records aliases and
      unions evidence, re-points relation endpoints to canonical names.
- [x] Conflict detection (#6, PR #22): same name under a different TYPE → conflict entry
      holding BOTH evidences, flagged for review, never silently resolved; a real one
      surfaced in the live merge test.
- [x] Corpus scale (#7, PR #22): `--sample N` bounds the TBox schema pass; per-call usage
      accounting + `--max-calls`; every artifact carries provenance (model/temp/elapsed/
      calls/tokens).
- [x] Assertion query (#8, PR #22): `--query X` (name/alias/endpoint) with every evidence
      span; pure semantics unit-tested in CI (v1+v2 artifact shapes accepted).

## O3 · Interop & DSH-native (weeks 4-5)

- [x] JSON-LD export (2026-11-18, PR #24): typed entity nodes + reified relation
      statements, evidence first-class (@list), stable urn:dshao: namespace;
      unit-tested in CI; live export verified.
- [x] WeKnora graph bridge (2026-11-18, PR #28): each entity becomes an
      evidence-first manual-knowledge doc (quotes + source docs + its relations);
      deliberately never creates a KB (the ingest-scoped key is correctly refused
      by the server — verified live; a KB is a person's choice); requires --kb;
      pure builder CI-tested; live ingest awaits the first owner-designated KB.
- [x] typed-tools plugin 0.2.0 (2026-11-18, PR #27): ontology_build / ontology_query
      via defineTool (family recipe, DSL pitfalls honored); contract-tested,
      installed into a live headless profile, and **live-session verified** — the
      dsh agent called ontology_build on a 2-doc corpus and quoted evidence spans
      (12 entities / 11 relations / 4 calls artifact). Publish via owner OTP.
- [x] Single-file HTML digest (2026-11-18, PR #25): stats+provenance header,
      conflicts table (both evidences), entities by type, relations with quotes;
      family render_html (sidebar TOC); digest + render CI-tested.

## O4 · Learning loop & ecosystem (month 2)

- [x] Certification fold-back (2026-11-18, PR #31): --certify NAME --verdict
      accept|reject [--note]; the verdict travels WITH the artifact (timestamp, note,
      original evidence for audit); rejected (name,type) suppressed in every later
      fold (counted, never re-asserted; a different type re-enters as a new
      assertion). Upstream's Learn pillar, evidence-first version.
- [x] Ontology history (2026-11-18, PR #32/#33): --diff OLD NEW at evidence
      granularity — additions, removals WITH causes (a certification rejection names
      its note), evidence growth, aliases, new conflicts. (One CI lesson on the way:
      certify mutates in place — diff needs two distinct artifacts.)
- [x] Honest precision metric (2026-11-18, PR #34): 'auto-ontology eval' — seeded
      strict judge, rerunnable by anyone, v1/v2 shapes. First honest numbers:
      **10% (2/20) on both artifacts** — most quotes mention the entity but do not
      support its TYPE claim (relations with exact quotes pass). Diagnosis: type
      assertions are the weak evidence axis; tightening is tracked as #35. The
      metric ships as-is — it exists to make this visible, not to be gamed.
- [x] Format positioning (2026-11-18, PR #36/#37): evidence-linked ontology v0.1
      (docs/FORMAT.md) + stdlib validator ('auto-ontology validate') + CI enforcement
      on committed artifacts. Enforcement had teeth on day one: the legacy v1
      artifacts failed, replaced by the first conforming v2 family build
      (88 entities / 121 relations / 4 organic conflicts, 21 calls 55s). The
      showcase set is now tracked in-git (the awesome submission's icon URL had
      been a 404 — found and fixed).

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

## O5 · Quality vindication & the family pipeline (2026-11-25 → 12-15) — CURRENT

→ full plan: [docs/plan-O5.md](docs/plan-O5.md). Driven by four post-O4 facts:
adoption outran quality (999 dl/wk family #3 vs 10% type-assertion precision
#35); the evoontology E2 bridge contract names our certifications as its
trajectory source; the family channel works (uigen merged); spec-as-product
stays gated on adoption.

- [x] O5.0 type-grounding quality (2026-11-25) — one judge call per quote,
      verbatim as the only mechanical reject, flag never drop; honest
      before/after on the same frozen corpus (19 public READMEs):
      25% → 67% (deepseek-chat), 9% → 50% (deepseek-reasoner), tables and
      rows in `eval/` (closes #35)
- [ ] O5.1 `export --trajectory` (FORMAT.md contract) + one live two-repo
      evolution round with dsh-evoontology E2
- [ ] O5.2 chunk-level evidence on WeKnora KBs (queryable provenance)
- [x] O5.3 adversarial set (2026-11-25) — `eval --adversarial`, 28 labelled
      cases (18 must-reject, 10 must-accept), gold checked in CI
- [ ] O5.3 stretch: second-corpus eval (non-family)
- [ ] O5.4 release train 0.3.0 (owner terminal publish)
