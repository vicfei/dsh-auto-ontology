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
  evoontology consumes (their #9 adapter reads this, not our internals).
- **One live co-verification round with dsh-evoontology E2**: family corpus
  v2 → one certification (accept + reject with notes) → fold → export → the
  evolution kernel runs a hypothesis round → any gated proposal re-enters
  here as a NEW certification/fold event. The loop closes across two repos;
  both READMEs get the two-repo pipeline story.

## O5.2 · Chunk-level evidence on WeKnora (2026-12-06 → 12-11)

The differentiating surface. Today the bridge builds from a KB's documents
with doc-level evidence; chunk-level grounding turns the ontology into
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

- [ ] #35 closed with an honest before/after on the same corpus; flagged
      assertions preserved (nothing silently dropped)
- [ ] `export --trajectory` documented in FORMAT.md and consumed by
      dsh-evoontology E2 in one live two-repo round
- [ ] chunk-id evidence verified on a real WeKnora KB
- [ ] 0.3.0 on npm

## Deviations log (what shipped vs the plan above)

- **O5.0 grounding pass** (PR #47): the judge is **batched per document** — one
  call per 25 candidates, plus at most one re-ground and one re-judge call per
  document — instead of "one extra call per assertion". Same verdict per
  assertion, a fraction of the calls. Relations are judged alongside entity
  types. An ungrounded challenger under a different type goes to
  `flagged_ungrounded` instead of opening a conflict (a grounded one still
  does).
