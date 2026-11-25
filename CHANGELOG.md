# Changelog

## 0.3.0 (2026-11-25)

Everything since 0.2.2 (which shipped on launch day, 2026-11-18): the honest
grounding pass, the trajectory contract that dsh-EvoOntology consumes, and
builds from a WeKnora knowledge base. Format v0.1 and v0.2 artifacts remain
valid v0.3 artifacts.

### Build from a knowledge base — `--kb` (O5.2, #56)

- `auto-ontology build --kb <id> [--limit N]` reads a WeKnora base's parsed
  chunks as the corpus: one chunk is one document, read whole, in a fixed
  reading order; only documents whose parse completed are read (the rest are
  counted in `provenance.kb.skipped_documents`); `--limit` (≥ 1) reads the
  first N chunks and may stop inside a document. Read-only against the base;
  needs `WEKNORA_URL` / `WEKNORA_API_KEY` (+ tenant header when the key needs
  one).
- **Every evidence carries the `chunk_id` it was read from** — entities,
  relations, conflicts, the type guard's catches, ungrounded clashes,
  certifications and `retyped_to` alike, in the artifact and in the stream. A
  consumer resolves it with `GET /api/v1/chunks/by-id/{id}`. The verbatim gate
  checks a quote against its own chunk; the prompt's label line does not pass
  it.
- Typed tool: `ontology_build` takes `kb` + `limit` (default 40 — a whole base
  can run for an hour; timeout 30 min) and throws when neither or both of
  `docs`/`kb` is given.
- Measured on a real base (23 public READMEs, 369 chunks): 248 evidence
  records, **248 of 248 resolved by the WeKnora API and by Postgres SQL**, 0
  failed (`eval/kb-round/`). The same documents built from files make a larger,
  better-grounded ontology on a different TBox — when you have the files,
  build from the files.

### Format v0.3 — the judge's name on its quotes

- An externally judged evidence carries `judge` (and `reason` beside it); the
  exported assertion reads `by: "judge:<model>"` instead of `by: "judge"`.
- A named judge changes an assertion's event id; a re-issued certification
  gets a new id. A consumer keeps earlier exports — a store holding both shows
  the quote twice, which is the record, not a bug.
- `docs/FORMAT.md` rewritten for v0.3, including the `--kb` contract and the
  trip-back rules; `validate_format.py` enforces the new checks.

### Trajectory in and out (O5.1)

- `auto-ontology export --trajectory` — the append-only event stream
  (`ao-trajectory/0.1`: build, fold, assertion, certification, conflict),
  documented in FORMAT.md as the contract dsh-EvoOntology's adapter reads.
- `auto-ontology apply run.proposals.json --actor agent:<name>` — a
  judge-grounded re-typing applied as a certification on the old typing
  (`retyped_to` with judge, reason, run) plus a new assertion whose first
  evidence is that quote. Never an edit; a person's verdict on the name stops
  it; a replay writes nothing. One certification per name — a re-typing
  reject lists the typings it replaces in `also_rejects`.
- Closed live with dsh-EvoOntology: one Term re-typed (`OAR`, `dsh_plugin` →
  `upstream_project`) on the quote the build had judged against the wrong
  type; three attempts, the qualifiers measured (`eval/live-round/`).

### Grounding pass and honest eval (O5.0, closes #35)

- One judge call per quote; the verbatim check is the only mechanical reject;
  ungrounded assertions are flagged, never dropped. Strict-judge precision on
  the frozen 19-README corpus: **25% → 67%** (deepseek-chat), **9% → 50%**
  (deepseek-reasoner). Tables, rows, blind audit and judge stability in
  `eval/`.
- `eval --adversarial`: 28 labelled cases (18 must-reject, 10 must-accept),
  gold checked in CI.
- Merge keeps the TBox definitions the base artifact carried (#55) — merged
  types used to come back with a blank description.

### CI

- Committed artifacts (now including every ontology artifact under `eval/`)
  must conform to the format; SVG geometry checks; the full engine contract
  suite runs on every push.

## 0.2.2 (2026-11-18)

Launch-day fix: subcommand names leaked into the engine args (#39).

## 0.2.1 (2026-11-18)

Launch-day fixes.

## 0.2.0 (2026-11-18)

Typed tools: `ontology_build`, `ontology_query`, `ontology_export` (#11).

## 0.1.0 (2026-11-18)

First real bundle: the stdlib engine behind `auto-ontology`, the skill, the
build pipeline (#2).

## 0.0.1 (2026-11-17)

Name reservation.
