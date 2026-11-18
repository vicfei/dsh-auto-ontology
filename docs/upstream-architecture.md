<!-- Internal working notes (English, repo-docs policy) -->
# Upstream NVIDIA Auto-Ontology — architecture & functionality (source-level, 2026-11-18)

> Shallow clone via SG relay (direct HTTPS left an empty dir — the false-success
> trap). Baseline: 428 Python files / ~112k LOC in `auto_ontology/` + a full
> Next.js frontend + `mcp/` server + 8-database connector layer + Docker Compose
> stack. Apache-2.0. **This is an enterprise platform; dsh-auto-ontology is a
> stdlib CLI — the comparison is complementary slots, not competitors.**

## 1 · The stack (docker-compose)

postgres (pgvector/pg17) + pgadmin + auto-ontology (API server) + ingestion-service
+ alembic migrations + a full frontend container. Serving: Web UI, REST API, CLI,
and MCP (`mcp/auto_ontology_mcp` with OAuth remote-auth). Everything persists in
Postgres; embeddings in pgvector (`vdb/`).

## 2 · Layer map (by size)

| Layer | Files | What it does |
|---|---|---|
| `retrieval/` | 118 | The product's front door: text_to_sql pipeline (candidate retrieval → SQL agents → execution → follow-up), interactive sessions (clarify, entity_resolution, grounding, **evidence**, kb_coverage, completeness) |
| `server/` | 86 | FastAPI-ish surface: chat, connections, datasources, exploration, ingestion, metadata, owners, custom_analyses, model_interchange |
| `dal/` | 50 | Data access over the catalog store |
| `semantic/` | 39 | The ontology compiler (below) |
| `catalog/` | 38 | Metadata ingest/normalize/extract: SQL parsing (sqlglot), schema registry, query stats, diff, incremental ingest |
| `connectors/` | 33 | ClickHouse, Databricks(+OAuth), DuckDB, HeavyDB, Kyuubi, MySQL, Postgres, … |
| `pii_detection/`, `ingestion_service/`, `infra/` | — | PII scanning during ingest; async ingestion workers; feature flags |

## 3 · The ontology compiler (`semantic/`)

Flat **table-by-table taxonomy pass**: `_WORKERS=3` ThreadPoolExecutor with an
`_OrderedCommitQueue` (commits stay ordered without serializing LLM extraction;
skip semantics documented with the exact incident that motivated them). Per table:
term extraction, attribute descriptions, FK suggestion (`fk_suggester`,
`semantic_fk`, bridge-table handling), distinct-value probing behind a feature
flag, embedding via `SemanticEmbedder`, deterministic passes separated from LLM
passes (`deterministic.py`). One curated `system_prompt.txt`: "You are compiling
a business semantic layer over a relational database… CamelCase Term names…
business language." Output: a governed semantic model (terms, attributes,
relationships) in Postgres.

## 4 · The answer path (`retrieval/`)

`text_to_sql/`: agents for candidates_retrieval, sql_execution, response, and
**sql_unconstructable** (an explicit "cannot construct" exit — their PASS cousin).
`interactive/`: multi-turn sessions — clarify, entity_resolution, kb_coverage,
completeness, followup_merge, **grounding** and **evidence**. The evidence prompt
is instructive: extract formulas/thresholds/definitions from grounded KB entries
into SQL-friendly lines, and — "Never invent a column-like name for a term with
no confirmed mapping." Their anti-hallucination discipline lives in the
**retrieval** path; ours lives in the **construction** path (evidence spans on
every assertion before anything lands). Same instinct, opposite ends.

## 5 · Functionality (README's five pillars, verified in source)

- **Discover** — enterprise ontologies from DB metadata; connect existing
  ontologies/semantic models (`model_interchange`, Apache Ossie portability).
- **Ground** — give agents trusted business meaning; reconcile conflicting
  definitions across systems.
- **Validate** — test a draft with real questions before experts certify;
  generated queries checked against the catalog + the definitions retrieval
  surfaced; SQL and steps returned with every answer.
- **Expose** — Web UI / CLI / API / MCP to any agent harness.
- **Learn** — fold certified corrections and usage back into the ontology
  (owners, custom analyses, review flows in `server/`).
- Benchmarks: **#1 BEAVER, #2 BIRD-Interact** leaderboard badges (agent-analytics
  benchmarks on enterprise stacks).
- `skills/` ships an agent skill for *setting the system up*
  (`nvidia-ontology-setup`, with BENCHMARK.md + troubleshooting) — they target
  agents as operators, not as end users of a zero-infra tool.

## 6 · vs dsh-auto-ontology — the honest table

| Axis | NVIDIA Auto-Ontology | dsh-auto-ontology |
|---|---|---|
| Corpus | enterprise **metadata** (schemas, SQL, query logs) via 8 DB connectors | **documents** (READMEs, docs, any text) |
| Output | governed semantic layer in Postgres (terms/attributes/FKs) | typed TBox+ABox JSON where **every assertion carries its evidence span** |
| Anti-hallucination | at answer time (grounding/evidence prompts, "never invent a column name") | at build time ("no evidence, no assertion"; type guard flags, never drops) |
| Conflicts | reconcile definitions across systems (resolution is the goal) | **record both evidences, never silently resolve** (review is the goal) |
| Incremental | incremental metadata ingest (`catalog/test_incremental_ingest`) | append-only fold; prior evidence never edited |
| Serving | Web UI + REST + CLI + **MCP** | stdlib CLI + skill + **DSH typed-tools** (verified in live sessions) |
| Infra | Docker/Postgres/pgAdmin/pgvector, NVIDIA API key | zero-infra stdlib + any DeepSeek-compatible key |
| Cost surface | platform-scale (workers, embeddings, migrations) | per-call provenance + --max-calls guard |
| Benchmarks | BEAVER #1 / BIRD-Interact #2 | none yet (O4 #15: reproducible evidence spot-check) |

**Positioning confirmed:** they own "agent analytics over governed enterprise
data"; we own "auditable ontologies from the documents you already have." No
collision — and their five pillars give O4 its shape (below).

## 7 · Borrow list for O4 (thinking, not code — Apache-2.0 clean-room anyway)

1. **Certification fold-back (#13) ← their Learn pillar.** Their owners/review
   flows are the model: our `--certify <entity> accept|reject` writes the verdict
   into the ledger; later runs respect it (rejected evidence quotes never
   re-assert from the same doc; accepted entities pinned).
2. **Diff (#14) ← `catalog/diff.py`.** They diff catalogs; we diff ontology run
   layers — what the corpus added between runs, evidence-level.
3. **Honest metric (#15) ← their benchmark posture.** We can't chase BEAVER, but
   their discipline (a named, rerunnable eval) is the bar: a public-corpus
   evidence spot-check anyone can rerun.
4. **"Cannot construct" exit ← `sql_unconstructable`.** Their explicit refusal
   exit validates our no-evidence/no-assertion stance at the answer side; when
   O4 queries grow, keep refusal first-class.
5. **Not borrowed:** the platform stack, connectors, PII scanning, MCP-first
   serving (DSH typed-tools is our native surface), definition reconciliation
   (conflicts stay unresolved by design).

## 8 · Engineering-culture notes worth copying

- Issue-numbered incident comments (the `_OrderedCommitQueue.skip` docstring
  explains the exact cancellation pathology that motivated it) — same culture as
  Tauric's repo.
- Skills shipped **for the setup operator** (with signed `skill.oms.sig`!) — a
  channel idea for us: an `auto-ontology-setup` skill is unnecessary (zero
  infra), but a "feed me your corpus" skill variant is thinkable.
- `AGENTS.md` + `CLAUDE.md` at repo root: the repo is agent-first in
  development, too.
