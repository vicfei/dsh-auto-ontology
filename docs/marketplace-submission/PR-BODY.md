# PR body (fires at awesome-dsh-plugin AFTER npm 0.1.0 is published)

**Adds vicfei/dsh-auto-ontology — auto ontology construction with evidence (tools)**

One file: `data/plugins/vicfei__dsh-auto-ontology--npm.yml` (monorepo subpackage
format — the installable package lives in `npm/` and on npm as `dsh-auto-ontology`).

- Install: `dsh plugin add dsh-auto-ontology` (npm 0.1.0: bin `auto-ontology` +
  skill; empty-patch distribution vehicle, typed-tools is the 0.2.0 track)
- Real working code: two-pass engine (TBox from corpus → ABox per doc), evidence
  on every assertion, type guard, SVG/JSON/md artifacts, CI green — 19-doc family
  corpus → 243 entities / 139 relations / 0 unknown-type leaks
- Repo created 2026-11-17 (meets the 1-day bar), MIT, concept credited to
  NVIDIA/auto-ontology (13.3k★) with explicit non-affiliation, clean-room

> ⚠ Sequence gate: file this PR only after `npm publish` of 0.1.0 — reviewers
> install-test, and 0.0.1 is the name-squat placeholder without a bin.
