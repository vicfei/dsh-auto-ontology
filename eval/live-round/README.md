# live-round — one evolution round across two repositories (O5.1)

Measured on 2026-11-25 (times are CST), models at temperature 0. Reports are
stored as written.

**The result.** An ontology built and certified in dsh-auto-ontology was
exported as a trajectory stream, imported by dsh-EvoOntology, which proposed a
re-typing, had it judged, published a new layer, and sent the proposal back;
dsh-auto-ontology applied it as a new certification and assertion, and the
stream of that was imported again: **the loop closed across the two
repositories.** One Term was re-typed — `OAR`, from `dsh_plugin` to
`upstream_project`, on the very quote the build had judged against the wrong
type. The other twelve proposals were judged ungrounded and changed nothing.

**Read the qualifiers before quoting a number.** The round took three attempts;
its two seed certifications and its budget extension were issued by the agent
that ran it, not by a person; and the round-1 judge rows were overwritten by
round 2. All of it is below.

## The repositories at the time of the round

| | |
|---|---|
| dsh-auto-ontology | `main` 2f5e4d9 (`apply --proposals` #53 and the TBox-definition fix #55 merged). The 19:38 re-apply ran on the format-v0.3 working tree of this branch |
| dsh-EvoOntology | branch `feat/e2-auto-ontology-adapter` at a55286c, with fixes uncommitted at the time; all of them are in 218ee6c and the account of the round in that repository's README (ad2c16e, PR #27) |
| corpus | family corpus v2: the 19 frozen public READMEs of `eval/before-after/corpus/` plus 4 more public ones. The same 23 repositories as `eval/kb-round/`, with `dsh-auto-ontology` and `dsh-evoontology` at an earlier HEAD |
| models | build and build-time judge `deepseek-chat`; proposer `deepseek-chat`; evolution judge `deepseek-reasoner` |

## The round, in order

| time | step | record |
|---|---|---|
| 17:15–17:18 | 19-document build: 109 entities / 166 relations | `../ontologies/20261125-1718.*` |
| 18:26 | first merge of the 4 new documents — 46 calls, 25 entity types of which **12 without a definition** (the TBox defect of #55). Discarded | `artifacts/discarded-first-merge-20261125-1826.json` |
| 18:32 | merge again on the fixed engine: 129 entities / 178 relations, 22 types, all defined, 53 calls · 29 s | `build/merge-run.log` |
| 18:34:42 | certification **accept**: `turn/end is a harness_event` | `build/certs.log` |
| 18:34:44 | certification **reject**: `ontology_build is a harness_service` — the name and its relation leave the ABox: 128 / 177. This is the round's input | `artifacts/20261125-183444-certified.json` |
| 18:36:46 | `export --trajectory`: 374 events — 1 build · 1 fold · 370 assertion · 2 certification | `stream/round1.ndjson` |
| 18:36:46–18:36:53 | **attempt 1**, run `20261125-183646`: import +374; projection Constraint 1 · Relation 177 · Term 128; proposer 47 calls — 8 proposals, 39 malformed; the adapter crashed printing a malformed proposal (`KeyError: 'from_type'`) before any judge ran. Run closed `aborted` | `evoontology/adapt-round1.log`, `…-183646.json` |
| 18:41:49–18:41:59 | **attempt 2**, run `20261125-184149`, round 1: 10 proposals (37 malformed dropped); judge 0 grounded · 10 not. Candidate 2.9627 against incumbent 2.9627 — **lost**, nothing published | `evoontology/adapt-round2.log` |
| 18:47:50 | the same stream again: refused — "an unchanged stream gets no second run on its own" | `evoontology/adapt-round3.log` (a) |
| 18:48:11 | the run extended from 1 to 2 rounds, **by `agent:shanghai-window`** | (b′), the run file's `extensions` |
| 18:48:11–18:48:24 | **round 2**: 13 proposals · 34 null · 0 malformed (the proposer's prompt had been fixed in the working tree); judge **1 grounded · 12 not**. Candidate 2.9693 against 2.9627 — **won**, published as `layer_v1` | (c′), `…-184149.proposals.json`, `…-184149.judge/` |
| 18:48:44 | **the trip back**: `apply --proposals` re-typed 1 entity, skipped 12 as not grounded | `build/apply.log` |
| 18:52 | `export --trajectory`: 375 events; import into dsh-EvoOntology +2 (373 already present, 376 in the store); Constraint 2 · Relation 177 · Term 128; verdicts 208 grounded · 96 ungrounded; gate **2.9681** | `build/export-round2.log`, `build/import-round2.log`, `stream/round2-v02-engine.ndjson` |

### The one proposal that was grounded

The build had typed `OAR` as `dsh_plugin` on a quote from `dsh-evidence-plugin`
and judged that typing ungrounded ("Quote mentions OAR as an adapter/session,
not a plugin for DeepSeek Harness"). The proposer offered `upstream_project`
on the same quote; the evolution judge grounded it ("Quote names OAR as Open
Agent Runtime with GitHub link and an adapter integrating it"). That is the
run's hypothesis exactly — a quote judged against the wrong type states one of
the TBox's own types — on a sample of one.

`apply --proposals` wrote it as a certification on the old typing with
`retyped_to` (judge, reason, run) and a new assertion whose only evidence is
that quote, now `grounded: true`:

```json
"retyped_to": {"type": "upstream_project", "doc": "dsh-evidence-plugin",
               "judge": "deepseek-reasoner", "run": "20261125-184149",
               "reason": "Quote names OAR as Open Agent Runtime with GitHub link and an adapter integrating it."}
```

## Two scores for the won round — 2.9693 and 2.9681

The run file records the candidate at **2.9693**. That candidate was built
without the constraint a re-typing's certification adds, so the layer it
published scored one record above what the trip back really projects:
importing the trip-back stream reads **2.9681**. dsh-EvoOntology fixed its
candidate in 218ee6c (the published layer now equals the trip-back
projection, and its CI checks it). Under the fixed construction the round
still wins, 2.9681 against 2.9627; the published `layer_v1` itself was not
regenerated. Both numbers are kept.

## The same round under format v0.3 (`build/v0.3/`)

v0.3 names the judge on an externally judged quote (`judge` on the evidence,
`by: judge:<model>` on the assertion). The same proposals file was applied
again to the same input at 19:38:23 and the result exported:

| | v0.2 engine (18:48 / 18:52) | v0.3 engine (19:38) |
|---|---|---|
| certification on `OAR is a dsh_plugin` | `at` 18:48:44, evidence without a judge | `at` 19:38:23, `retyped_to.judge` = `deepseek-reasoner` |
| new assertion `OAR is a upstream_project` | `by: judge` | `by: judge:deepseek-reasoner`, with the judge's reason |
| `stream/round2*.ndjson` | 375 events | 375 events; 2 ids differ |
| fresh dsh-EvoOntology workspace (ad2c16e) | 374 + 2 = 376 events | 374 + 2 = 376 events; a replay adds 0 |
| projection | Constraint 2 · Relation 177 · Term 128 | the same |
| gate | 2.9681 | 2.9681; 46 ungrounded Terms to propose for |

`stream/round1.ndjson` is byte-identical under both engines: nothing in it
names a judge. `stream_facts.py` prints the table's event counts and the
differing ids (`stream-facts.log`).

Two ids differ, not one, because a re-apply is a re-issue: the certification
gets a new `at`, and an assertion's id is taken from its claim, evidence,
verdict and author. A store that holds **both** exports of round 2 has 378
events and shows the `OAR` quote twice, once under `judge` and once under
`judge:deepseek-reasoner` — measured, and the reason FORMAT.md's contract
tells a consumer to keep the earlier export (`build/v0.3/edge-both-round2.log`).

## What was not right about this round

- **The certifications are the agent's.** The accept and the reject that seed
  the stream were issued by `agent:shanghai-window`, the same agent that built
  the artifact and wrote the exporter — not by a person, and not blind.
- **The budget extension is the agent's.** dsh-EvoOntology's kernel calls an
  extension "the explicit human act". Round 2 exists because the agent extended
  the run, after fixing the proposer's prompt on the evidence of round 1.
  Without the extension the round ends at 2.9627 against 2.9627.
- **Three adapter invocations on one stream.** The kernel's rule is now one
  stream, one run (218ee6c); when the round ran, every invocation opened a
  fresh run. The aborted run's file was completed afterwards with its reason.
- **Round 1's judge input and rows are gone** — round 2 wrote over them (the
  judge's work directory is per run; per round since 218ee6c). What survives
  of round 1 is its console log and the run file's tally.
- **Attempts 1 and 2 logged the same token totals** (46,097 in / 3,423 out)
  with different tallies (8 proposals · 39 malformed against 10 · 37). The
  same totals are what 47 temperature-0 calls returning the same text would
  give, and the adapter's parsing changed between the two; that reading has
  not been verified.
- **The `stream` fingerprint on the two earlier runs** was written onto their
  files afterwards; the runs did not record it at the time.
- **A round of one.** One stream, one corpus, one adapter, one grounded
  proposal. It shows the loop closes and the gates hold; it is not a rate.

## Files

| path | what it is |
|---|---|
| `artifacts/20261125-183444-certified.json` | the round's input: the 23-document build with the two seed certifications |
| `artifacts/20261125-193823-retyped.json` | the output under v0.3, with the re-typing's certification |
| `artifacts/discarded-first-merge-20261125-1826.json` | the merge that ran on the engine with empty type definitions — kept, unused |
| `stream/round1.ndjson` | 374 events, identical under both engines |
| `stream/round2.ndjson` | 375 events, exported by the v0.3 engine |
| `stream/round2-v02-engine.ndjson` | 375 events, exported at 18:52 by the engine on `main` |
| `build/` | the console of the merge, the certifications, the trip back and the 18:52 export and import; `v0.3/` the 19:38 import and the both-exports store |
| `evoontology/` | the three adapter invocations, both run files, the 13 proposals, round 2's judge input and rows |
| `stream_facts.py` · `stream-facts.log` | event counts and differing ids of the streams |

Everything here was built from public repositories only. The judge rows and
proposals quote those READMEs and nothing else.

## Re-running

The streams can be replayed into a dsh-EvoOntology workspace without a model:

```bash
python3 scripts/evoontology.py trajectory import --from eval/live-round/stream/round1.ndjson
python3 scripts/evoontology.py trajectory import --from eval/live-round/stream/round2.ndjson
python3 scripts/evoontology.py adapt auto-ontology --from eval/live-round/stream/round2.ndjson --dry-run
```

The build, the certifications, the proposals and the trip back are LLM calls
at temperature 0; the judge is not constant from one hour to the next
(`eval/before-after/stability/`), so a re-run is a new measurement, not a
reproduction.
