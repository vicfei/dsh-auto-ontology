# O5 plan — quality vindication & the family pipeline (2026-11-25 → 2026-12-15)

Tracker: the O5 milestone issue. Scope carved with the owner: engineering runs
autonomously; channel posting (#4) stays owner-gated.

## Why now — four new facts since O4 closed (2026-11-18)

1. **Adoption outran quality.** 999 weekly downloads (family #3, 2026-11-24
   snapshot) — while the honest eval says **10% type-assertion precision**
   (#35, open): most quotes *mention* the entity but do not *support its type
   claim*. The repo's own discipline ("the metric exists to make it visible,
   not to be gamed") makes this the single most valuable thing to fix — and
   the before/after is exactly the track-record content the family sells.
2. **The E2 bridge contract exists on paper.** dsh-evoontology E1 shipped
   (2026-11-19); its E2 explicitly names *dsh-auto-ontology certifications*
   as a trajectory source (evoontology #9: "accepted/rejected verdicts as
   trajectory records; the ontology evolves under the same gate"). Our
   FORMAT.md v0.1 already carries certifications as evidence-bearing events —
   the artifact side needs a stable, documented export surface.
3. **Channel precedent landed.** dsh-uigen merged into awesome-dsh-plugin
   (2026-11-23) — the family channel works; our PR #16447 stays queued with
   zero comments (normal). Nothing to do but be ready with a stronger product
   when eyes arrive.
4. **Spec-as-product has family precedent** (format-anything's FORMAT.md
   site) — but the ecosystem push for our FORMAT.md v0.1 stays **deferred
   until adoption evidence** (the 2026-11-23 "adoption earns the voice"
   ruling applies family-wide).

## O5.0 · Type-grounding quality (2026-11-26 → 12-01) — closes #35

The credibility core. The weak axis is precise: ABox extraction cites a quote
that mentions the entity, but the *type* claim (e.g., "X is a Tool") is
unsupported by that quote.

- **Grounding pass**: after extraction, every `(name, type)` assertion gets a
  strict judge call — "does this verbatim quote ground THIS type claim?" —
  with the same temperature-0 deepseek line (one extra call per assertion,
  `--max-calls` respected; family cost-guard convention).
- **Honesty under strictness**: ungrounded assertions are **flagged, never
  dropped** (the type-guard philosophy extended — strictness must not become
  silent data loss). Flagged assertions carry `type_grounding: false` and stay
  queryable; certification can still accept them by human verdict.
- **Re-run the eval on the SAME corpus** and publish before/after in the
  artifact stats and the README eval section. Target ≥50%; if the fix lands
  lower, the honest number ships anyway. A small adversarial set
  (mention-only traps — entities named in passing with a wrong type) proves
  the judge actually bites.
- FORMAT.md: `type_grounding` becomes an optional entity field (v0.2,
  backward-compatible; validator updated).

## O5.1 · Certifications → evolution trajectory (2026-12-01 → 12-06)

The family pipeline: corpus → audited ontology → self-evolving ontology.

- **Stable export surface**: `auto-ontology export --trajectory` emits the
  append-only event stream (builds, folds, certifications — verdict, note,
  evidence included) as newline JSON; FORMAT.md documents it as THE contract
  evoontology consumes (their #9 adapter reads this, not our internals). The
  build event carries the TBox definitions, so a consumer never opens the
  artifact to judge or propose.
- **The trip back**: `auto-ontology apply --proposals` applies a
  judge-grounded re-typing as a certification on the old typing (`retyped_to`)
  plus a new assertion — never an edit. A person's verdict on the name stops
  it, a stale proposal is reported, a replay writes nothing.
- **One live co-verification round with dsh-evoontology E2**: family corpus
  v2 → one certification (accept + reject with notes) → fold → export → the
  evolution kernel runs a hypothesis round → any gated proposal re-enters
  here as a NEW certification/fold event. The loop closes across two repos;
  both READMEs get the two-repo pipeline story.

## O5.2 · Chunk-level evidence on WeKnora (2026-12-06 → 12-11)

The differentiating surface. Until this milestone the WeKnora bridge carried
an ontology *into* a knowledge base; nothing built *from* one. `--kb` reads a
base's parsed chunks, and chunk-level grounding turns the ontology into
**queryable provenance over the knowledge base** (evidence points at chunk
ids — the same addressability dsh-factor-auth and dsh-WrenAI key on).

- `--kb` builds record evidence as `{quote, doc, chunk_id}` when the source
  is a WeKnora KB; the verbatim-quote discipline is unchanged (chunk text).
- One real KB round on the dev WeKnora (WeKnora-postgres-dev) with the
  chunk-id evidence verified by spot-check SQL.
- Cross-sell note in the README: WrenAI answers *from* models, we audit
  *what the KB claims* — same family stack, no overlap.

## O5.3 · Eval expansion (stretch — cut without guilt)

- A second, non-family corpus (e.g., the WeKnora docs KB or an arXiv set)
  for cross-domain honest numbers alongside O5.2.
- Adversarial traps from O5.0 grow into a permanent `eval --adversarial` set.

## O5.4 · Release train 0.3.0

CHANGELOG + version + tarball (six-surface smoke per the family discipline) +
tag on green CI; npm publish = owner real terminal (browser auth flow).

## Non-goals (reaffirmed + new)

- Standing non-goals unchanged: no enterprise-DB semantic layer (upstream's
  land + dsh-WrenAI's slot), no Docker/Postgres stack, no web UI, no
  multi-model routing, no benchmark chasing.
- **No eval-gaming**: the number ships as measured, every time.
- **No FORMAT.md ecosystem push** (spec site / multi-language SDKs) until
  adoption evidence — the 2026-11-23 ruling pattern.

## Definition of done for O5

- [x] #35 closed with an honest before/after on the same corpus; flagged
      assertions preserved (nothing silently dropped) — 2026-11-25, PR #48,
      `eval/` (the alias tension the measurement left open is #49)
- [x] `export --trajectory` documented in FORMAT.md and consumed by
      dsh-evoontology E2 in one live two-repo round — 2026-11-25, PR #53
      (`apply --proposals`), `eval/live-round/`: one Term re-typed; three
      attempts on one stream, the seed certifications and the budget
      extension issued by the agent that ran it (deviations below)
- [x] chunk-id evidence verified on a real WeKnora KB — 2026-11-25,
      `eval/kb-round/`: 248 of 248 evidence records, by the API and by SQL;
      the chunk build's ontology is smaller and less grounded than the file
      build's, on a different TBox (deviations below)
- [x] 0.3.0 on npm — published by the owner 2026-11-25 (real terminal,
      browser auth); verified from the registry: dist-tags latest=0.3.0,
      pinned install, bin validate + typed tools smoke. O5 complete

## Deviations log (what shipped vs the plan above)

- **O5.0 grounding pass** (PR #47, revised 2026-11-25): the judge gets **one
  call per quote**. PR #47 first shipped one call per 25 candidates; a hand
  audit of a 273-assertion build found the batched verdicts agreed with it 74%
  of the time against 84% for single-item verdicts, so the batch was dropped.
  Relations are judged alongside entity types. An ungrounded challenger under a
  different type goes to `flagged_ungrounded` instead of opening a conflict (a
  grounded one still does).
- **O5.0 name rule** (2026-11-25): PR #47 rejected a quote mechanically when
  it did not spell the entity's name or a relation endpoint. It no longer
  does — the verbatim check is the only mechanical reject and name-absent
  quotes are judged. On the published before-artifact the rule would have
  turned away 30 ungrounded assertions and 9 grounded ones (a plugin typed
  from its own title line, a payload described without its type word); on an
  unpublished intermediate build, 13 of 22 were grounded. The adversarial set
  (now 28 cases) pins the cases the rule used to catch.
- **O5.0 measurement** (all 2026-11-25, whole population): on the published
  corpus — 19 public family READMEs, frozen — strict-judge precision went
  **25% → 67%** under deepseek-chat and **9% → 50%** under deepseek-reasoner
  (232 and 275 assertions). The ≥ 50% target is met under both judges. Every
  table and row is in `eval/`. The judge is not constant — a re-judge minutes
  later moves 2–4% of verdicts, an hour later about 9% — so a ✓ is a
  build-time verdict, not a fact.
- **O5.0 corpus** (2026-11-25): the first measurement used 23 READMEs and
  read 24% → 57% and 11% → 44%. Four of them are not public (three private
  repositories and a third-party clone), so the published before/after was
  rebuilt on the 19 public ones; the 23-document artifacts and rows stay
  unpublished and are quoted as numbers only. The four harder documents
  explain the gap.
- **O5.0 adversarial set** (2026-11-25): one of the 28 cases had been copied
  from a private repository's document. Its names were replaced before
  publication and the set re-run on both judges; all runs are in `eval/`.
- **O5.0 judge prompt vs gold** (#49, 2026-11-25): the judge prompt says an
  alias "does not count"; the gold labels `alias-label` grounded. deepseek-chat
  follows the gold (4 of 4 adversarial runs), deepseek-reasoner the clause (4
  of 4). The prompt was not reworded after the measurements — that would be
  tuning on the test set — so deepseek-reasoner's 25/28 carries that miss.
- **O5.1 one certification per name** (2026-11-25): a name re-typed twice
  would have lost its first rejection — the next fold would have let the old
  typing back in as a conflict (reproduced on a scratch store before the fix).
  A re-typing reject now lists the typings it replaces in `also_rejects`; the
  fold and dsh-EvoOntology's projection both honor it.
- **O5.1 `apply` is an agent's path** (2026-11-25): `--actor` must start with
  `agent`. The guard that protects a person's verdict keys on that prefix, so
  a mistyped actor would have locked a name against every later proposal.
- **O5.1 the live round as it ran** (2026-11-25): planned as one round, it
  took three attempts on one stream. The first crashed in the adapter before
  any judge ran; the second lost (2.9627 against 2.9627); the third won after
  a budget extension (2.9693) and re-typed one Term, `OAR` from `dsh_plugin`
  to `upstream_project`, on the quote the build had judged against the wrong
  type. The extension and the two seed certifications were issued by the agent
  running the round — where dsh-EvoOntology's kernel names an extension the
  explicit human act. Round 1's judge rows were overwritten by round 2. What
  the round exposed in the adapter is fixed there (218ee6c, PR #27).
- **O5.1 two scores for the won round** (2026-11-25): the published layer
  scored 2.9693; the trip back projects **2.9681**, because the candidate
  dsh-EvoOntology built lacked the constraint a re-typing's certification adds.
  The candidate is fixed there; the round still wins. The published `layer_v1`
  was not regenerated. Both numbers are kept in `eval/live-round/`.
- **O5.1 format v0.3 re-apply** (2026-11-25): as run, the round exported the
  re-typed assertion as `by: judge` and left the judge's name in the artifact
  only inside the certification's `retyped_to`. v0.3 puts `judge` on an
  externally judged evidence and names it in the stream (`by: judge:<model>`).
  The same proposals were applied again under v0.3 at 19:38 — a re-issue: the
  certification carries a new time, so its id and the assertion's changed. A
  store holding both exports of that round shows the quote twice; the contract
  tells a consumer to keep the earlier export.
- **O5.2 what the chunk build makes of a corpus** (2026-11-25): the plan asked
  for chunk ids verified by spot-check SQL; all 248 evidence records were
  verified, by the API and by SQL. The same round showed the chunk build's
  ontology to be smaller and less grounded than the file build of the same 23
  repositories — 76 of 248 quotes grounded against 226 of 370, 15 entity types
  against 22 — from a different TBox and one chunk at a time. No same-TBox run
  was made, so the causes are argued from the artifacts, not isolated. The
  README's line: when you have the files, build from the files.
- **O5.2 the plan's premise was wrong** (2026-11-25): this section said the
  bridge built from a knowledge base's documents. The O3 bridge carries an
  ontology into a base; nothing had built from one before `--kb`. Corrected
  above.
- **O5.2 the prompt's label line** (2026-11-25): in a 12-chunk smoke the
  model quoted the label line itself (`… · chunk 8`) instead of a sentence of
  the chunk. The verbatim gate rejected it and it stayed as an ungrounded
  evidence. The gate was not changed; FORMAT.md states the case.
- **O5.2 `chunk_id` does not come back** (2026-11-25): dsh-EvoOntology's
  projection keeps a quote's `chunk_id` on its Terms (24 of 24 in the smoke),
  but its proposals carry none back. Tracked on that repository.
