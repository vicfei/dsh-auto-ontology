<!-- Internal working notes (English, repo-docs policy) -->
# EvoOntology (ruc-datalab) — analysis (source-level, 2026-11-18)

> Shallow clone via SG relay. 25 py files / ~4.6k LOC + plugins + benchmarks.
> **1,258★ in ~2 months** (created 2026-09-15), MIT, arXiv 2609.15779, Renmin
> University DataLab. Bilingual README/USAGE (EN primary + zh-CN — same language
> policy as ours). This is the closest neighbor our O2/O4 design space has, and
> its traction validates the category.

## What it is

"A self-evolving ontology layer for data agents" over heterogeneous tables,
files, and databases — i.e. the **semantic-layer slot** (WrenAI /
NVIDIA-auto-ontology territory: agent-data grounding), not our document-corpus
slot. The novelty is the **evolution loop**: the ontology keeps adapting from
recorded execution trajectories under controlled, budgeted, evaluation-gated
rounds. Ships as MCP server + Codex & Claude Code plugins.

## Architecture

- **Ontology store** (`ontology/`): five record types — Term, Mapping,
  Relation, Constraint, and **Evidence as a first-class record** that other
  records reference by id. Convergent evolution with our format: same
  constitution ("no assertion without evidence"), different implementation
  (their evidence = separate records + id refs; ours = verbatim span inline on
  every assertion — ours stays human-readable in one place, theirs normalizes
  cross-record reuse).
- **Trajectory store** (`trajectory/`): append-only per-task execution records
  under `trajectories/<task_id>.json` — the workload is the corpus, and the
  evidence for change is grounded in what agents actually did.
- **EvolutionTrigger** (`trigger/`): batched, threshold-based — evolve after N
  new trajectories or M days; state in `state.json`. Cheap and predictable.
- **EvolutionSession** (`evolution/`): the disciplined core. Runs carry
  `parent_version` lineage, canonical version names (`ontology_vN`), **formal
  hypotheses per round**, candidate versions, a **frozen round budget**
  (exhaustion marks the run incomplete; extension requires explicit user
  confirmation), atomic JSON writes, resume support.
- **Adapter contract** (`evolution/adapter.py`): evolution is **gated by
  evaluation** — an adapter runs one benchmark (bird / insightbench / ddr_10k)
  against a candidate semantic version and returns comparable results; the
  session never touches benchmark internals.
- **Runtime** (`runtime/`): MCP server + workflow tools; plugins for Codex and
  Claude Code; `validate.py`, `visualization/`, `workspace.py` complete the
  product surface.

## vs dsh-auto-ontology

| Axis | EvoOntology | dsh-auto-ontology |
|---|---|---|
| Corpus | execution trajectories over tables/files/DBs | documents |
| Evidence | first-class record, id-referenced (workload-grounded) | inline verbatim span per assertion (document-grounded) |
| Change governance | hypothesis + rounds + frozen budget + **evaluation-gated** auto-evolution | human certification fold-back (append-only; rejected stays rejected) |
| Versioning | `ontology_vN` lineage with parent pointers | run-per-layer artifacts + `--diff` |
| Serving | MCP + Codex/Claude Code plugins | DSH typed-tools + CLI + skill (MCP is a non-goal for now) |
| Cost control | frozen evolution budget | per-call usage accounting + `--max-calls` |
| Rigor | arXiv paper + three benchmarks | honest rerunnable eval (10% reported as-is) |

No slot collision: they evolve a semantic layer over live data estates; we
build auditable ontologies from the documents people already have. Their
traction (1.3k★/2mo + paper) is category validation — good for our
awesome-dsh pitch.

## Borrow list

1. **Evolution rounds as formal hypotheses with a frozen budget** — the most
   disciplined auto-evolution design we have read; if dsh-auto-ontology ever
   grows auto-refinement (e.g., #35's type-grounding tightening as an
   evolution loop), it should be hypothesis-framed, budgeted, and resumable
   exactly like this.
2. **Evaluation-gated change** — no candidate version publishes without
   beating the incumbent on an adapter. Direct reinforcement of our #35 path:
   prompt-tightening must prove itself on the eval before shipping, and the
   eval IS our adapter.
3. **Threshold triggers** — evolve on N new documents (not every run); a
   cheap, predictable answer to "when does the ontology update".
4. Not borrowed: MCP-first serving (DSH typed-tools is our native surface);
   trajectory-as-corpus (different problem); record-normalized evidence
   (inline spans are our readability bet).

## Engineering-culture notes

Atomic JSON writes everywhere; protocol-typed adapters (runtime_checkable);
run schemas versioned (`RUN_SCHEMA_VERSION = 1`); bilingual docs with EN
primary — the academic-product hybrid done right.
