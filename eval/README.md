# eval — the measurements behind the README numbers

Everything below was measured on 2026-11-25 (times are CST) with the judge
prompt in `scripts/grounding.py` and DeepSeek models at temperature 0. Reports
are stored as written. No run was repeated to improve a number: the repeated
passes below exist to measure the judge's own variability, and all of them are
kept.

- `traps/` — a five-document end-to-end trap corpus and what the build makes of it
- `before-after/` — the before/after that closes #35: frozen corpus, two
  artifacts, every judge row, a blind audit, pass-to-pass runs

## traps/ — end-to-end trap corpus

Five tiny README-style documents (tools, people, languages, traps, one in
Chinese). Build them with:

```bash
auto-ontology build --docs 'eval/traps/*/README.md' \
  --domain "internal notes of a small software studio (tools, people, companies, databases, programming languages)"
```

`build-20261125-1656.*` is that run with the shipped engine (16:56:38–16:56:54,
30 calls, 16 s): 11 entities / 8 relations.

| sentence in the corpus | what the build did |
|---|---|
| "If the studio ever builds one, PicoGraph would be a database for graph queries." | typed `database`, judged **not** grounded (hypothetical) — kept with ⚠ |
| "Oakfield is not a database." | no `database` typing; Oakfield stays `company` only |
| "It is a build tool nobody on the team can name." | no entity — there is no name to assert |
| "LedgerDB is not open source." | no assertion |
| "…and so does the Wren team." | `Wren team` typed `team`, judged grounded on an implicit statement — a gray zone: the quote is about the platform team |
| "Mara mentioned Rusty during standup…" and "周明在站会上提到了 Rusty。" | both typed `person`, judged grounded on a mention — a lenient call; the adversarial set rejects the same shape for other types (`name-absent-mention`) |

The two `person` calls and the `Wren team` call are the judge's, not a rule's.
They are reported here rather than patched: no prompt was tuned on this corpus.

## before-after/ — closing #35

| path | what it is |
|---|---|
| `corpus/` + `corpus.sha256` + `corpus.sources.tsv` | the 19 public READMEs of the vicfei dsh family, frozen on 2026-11-25. Each is byte-identical to the README GitHub serves at the commit in `head`; all 19 repositories are public (MIT, one Apache-2.0) |
| `before/20261125-1715.*` | built by the engine at c3389d4 — no grounding pass (17:14:58–17:15:50, 21 calls, 52 s) |
| `../ontologies/20261125-1718.*` | the shipped engine (17:15:51–17:18:55, 514 calls, 184 s, 311,824 in / 48,048 out tokens) |
| `reports/` | `eval` output as written — summary, then every judged row — and the same rows as JSON; the last line of each report is the scratch path the rows were written to during the run |
| `stability/` | two more deepseek-chat passes over the shipped artifact |
| `audit/` | the blind-audit sheet, its shuffled order, the auditor's verdicts, the join with the judges |
| `adversarial-v0.3.*` | the 28-case adversarial set against both judges: report and rows |
| `superseded/` | earlier adversarial runs, kept |

The BEFORE svg is drawn by the current writer from the old engine's JSON. The
old writer's own svg for this build has 11 text elements off the canvas — a
title 1,398 px wide on an 860 px canvas, labels above the top edge and left
of x = 0.

The two builds are separate LLM extractions and the extraction prompt changed
between them, so the populations differ (232 and 275 assertions) and so do the
type vocabularies (17 and 12 entity types). Nothing that was judged is
dropped: the shipped build keeps all 275, 86 of them ⚠, after re-grounding 111
quotes.

### Strict-judge precision — whole population (`--n 0`)

| build | assertions | deepseek-chat | deepseek-reasoner | name in quote | ≥ 1 endpoint in quote | verbatim |
|---|---|---|---|---|---|---|
| before | 232 (91 E + 141 R) | 58/232 = **25%** (E 24%, R 26%) | 22/232 = **9%** (E 5%, R 12%) | 80% | 85% | 95% |
| after | 275 (109 E + 166 R) | 183/275 = **67%** (E 62%, R 69%) | 138/275 = **50%** (E 39%, R 58%) | 92% | 95% | 100% |

The plan's target was ≥ 50%. It is met under both judges. What is still weak
in the shipped build, under deepseek-chat: `harness_service` 1/5 (typed tools
are not service slots), `output_artifact` 5/15 and `guardrail` 6/18 (a
fragment that names a deliverable or a "guard" without saying it is emitted or
fail-closed), `agent_role` 3/7; among predicates `resolves` 2/5.

All six evaluations ran at 17:20:03–17:23:19, one to four minutes after the
shipped build finished.

### Do the build's ✓ / ⚠ flags hold up? (after, 275)

| build flag | confirmed by deepseek-chat | confirmed by deepseek-reasoner |
|---|---|---|
| ✓ grounded — 189 | 182 = 96% | 134 = 71% |
| ⚠ not grounded — 86 | 85 = 99% | 82 = 95% |
| flag agrees with the judge, all 275 | 267 = 97% | 216 = 79% |

The two judges agree with each other on 220/275 = 80%. Of the 189 ✓, 133 are
confirmed by both judges, 49 by deepseek-chat only, 1 by the reasoner only and
6 by neither. Of the 86 ⚠, 81 are rejected by both, 1 is accepted by
deepseek-chat only, 4 by the reasoner only, and none lacked a verbatim quote.

So a ⚠ is reliable under both judges, and a ✓ means "grounded" to the model
that built it more than to the other one.

### Blind audit (n = 80 of 275; sample seed 20261125, presentation order seed 777)

The auditor saw only the type definition, the claim, the quote and the source
document name — not the build flag, not a judge verdict. It was GLM-5.4, the
same agent that built the system, applying the adversarial gold as its
precedents. **Not independent.** Every verdict carries its class and a note
in `audit/after.verdicts.tsv`.

| audit says grounded | build flag ✓ | deepseek-chat ✓ | deepseek-reasoner ✓ |
|---|---|---|---|
| 55/80 = 69% | 55/80 | 54/80 | 42/80 |

| the audit against | agrees | audit's "grounded" confirmed | audit's "not grounded" rejected |
|---|---|---|---|
| build flag | 76/80 = 95% | 53/55 | 23/25 |
| deepseek-chat | 77/80 = 96% | 53/55 | 24/25 |
| deepseek-reasoner | 67/80 = 84% | 42/55 | 25/25 |

The audit and deepseek-chat differ on three items. The audit accepted two
deliverables the judge rejected — "You get a terminal brief, a zero-dependency
SVG chart card…" and "Versioned research artifacts: … trails" — and rejected
one the judge accepted: "the evidence-linked evolution records as a versioned
open format" for a `produces` claim, a fragment that names the thing without
saying it is emitted. The reasoner rejected thirteen items the audit accepted.

One precedent decides a large class and is worth stating: a line labelled
`Family:` in a plugin's README grounds `sister_of` to every repository it
lists (the subject is the document's own plugin); a bare run of links with no
label does not.

### The judge is not constant

- **Pass to pass.** Three deepseek-chat passes over the shipped artifact, all
  within 17:20:03–17:21:35, agree pairwise on 267/275, 267/275 and 269/275
  (97–98%). Eleven assertions changed verdict; by class: `output_artifact` 2,
  `dsh_plugin` 2, `enforces` 2, and one each of `agent_role`, `evidence_tag`,
  `guardrail`, `resolves`, `built_on`. The flag agreement was 267/275 in all
  three passes.
- **Later.** On an unpublished build (below) flags matched a re-judge 52
  minutes later on 91% and one 4 minutes later on 96%; re-judging the exact
  logged requests of a 5-document probe build matched on 131/133.

A ✓ or ⚠ is one verdict at build time. Expect a few percent to read
differently on a re-judge, more as time passes. The mechanism is not
established.

### Adversarial set

| set | run | deepseek-chat | deepseek-reasoner |
|---|---|---|---|
| v0.2 — 23 cases | 15:03:03–15:03:49 | 23/23 | 22/23 |
| v0.3 — 28 cases | 16:45 | 27/28 | 25/28 |
| v0.3 — one case's names replaced | 17:26 | 27/28 | 25/28 |
| v0.3 | 17:27 | 27/28 | 24/28 |
| v0.3 — published run | 17:31:21–17:31:37 | **27/28** | **25/28** |

All 18 traps are rejected in every run. deepseek-chat misses the same
must-accept case each time (`relation-implicit-object`). deepseek-reasoner
scores 24 or 25 of 28: `alias-label` is missed in all four runs;
`relation-implicit-object`, `predication-entails-type` and `name-with-alias`
in three of four.

Two things are owned here. The v0.2 numbers were taken **before** one case's
quote was corrected at 15:05:46, and the 23-case set was not re-run in its
final state. And one v0.3 case had been copied from a private repository's
document; its names were replaced at 17:25 and the set was re-run — once for
that, then twice more for a report footer and a file name, not for the score.
Every run is in the table. Misses ship as-is.

### Why a quote without the name is still judged

Until 2026-11-25 the build rejected a quote mechanically when it did not spell
the entity's name or a relation endpoint. The before-artifact shows what that
rule does: 39 of its 232 quotes do not spell the name or an endpoint, and the
judge grounds 9 of them under deepseek-chat (6 of 18 name-absent, 3 of 21
endpoint-absent) — 1 under deepseek-reasoner. The rule was right more often
than wrong, and still threw away a plugin typed from its own title line
("A DeepSeek Harness plugin (skill + `trustquant-dsh` CLI") and a payload
described without its type word ("Every payload carries its exchange and
timestamp"). On an unpublished intermediate build (below) the same count was
13 of 22.

So the rule is gone: the verbatim check is the only mechanical reject, the
judge decides the rest, and three v0.3 traps (`substituted-instance`,
`substituted-endpoint`, `name-absent-mention`) pin what it used to catch.

**A tension left as measured.** The judge prompt still says an alias "does
not count", while the gold labels `alias-label` true — there the claim's own
name (`market_data_payload`) carries the link to the quote's wording
("payload"), so no outside knowledge is needed. deepseek-chat follows the
gold, deepseek-reasoner the clause. The prompt was not reworded after the
measurements above; the decision is tracked in #49.

### An earlier measurement on 23 documents

The before/after was first measured on 23 documents: the 19 above plus three
private repositories and a third-party clone. Its numbers were lower —
**24% → 57%** under deepseek-chat and **11% → 44%** under deepseek-reasoner
(388 and 350 assertions) — because those four documents are harder than the
public ones: inside the same two builds their assertions scored 8% → 19%
under deepseek-chat, the 19 public ones 33% → 65%. That measurement also
covered an intermediate engine state (grounding pass with the name/endpoint
pre-reject still active, never merged: 55% and 29% on 312 assertions) and a
n = 80 audit of both states. None of its artifacts or rows are published,
since they quote documents that are not public; the numbers are kept here as
the more conservative reading.

### Re-run it

```bash
# the shipped artifact, same model as the build — a consistency check
auto-ontology eval --from ontologies/20261125-1718.json --n 0 --seed 42 --jobs 8 \
  --judge-model deepseek-chat --corpus 'eval/before-after/corpus/*/README.md'
# a different model is the only independent audit of a build's own verdicts
auto-ontology eval --from ontologies/20261125-1718.json --n 0 --jobs 8 \
  --judge-model deepseek-reasoner --corpus 'eval/before-after/corpus/*/README.md'
auto-ontology eval --adversarial --judge-model deepseek-reasoner
```

Every table above can be recomputed from the `.jsonl` rows: `supported` is
the verdict, `flag` the build's ✓ (true) or ⚠ (false). Rebuilding the corpus
is a fresh extraction: expect different counts, and verdicts within a few
percent of the reports.
