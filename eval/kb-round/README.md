# kb-round — building from a WeKnora knowledge base (O5.2, issue #56)

Measured on 2026-11-25 (times are CST) on a real WeKnora knowledge base with
the models at temperature 0. Reports are stored as written.

**The result.** A `build --kb` run over all 369 chunks of a 23-document base
emitted 248 evidence records. Every one of them resolved to a real, enabled,
text chunk of the base — its `chunk_id` found, its `doc` equal to the chunk's
document title, its quote contained in the chunk's text — read by two
independent paths, the WeKnora API and the Postgres `chunks` table: **248 of
248, 0 failures**. That is the claim of O5.2.

**The same round says something else too.** The ontology this chunk build
makes of the 23 READMEs is smaller and less grounded than the file build of the
same 23 repositories: 72 entities / 55 relations with 76 of 248 quotes grounded,
against 128 / 177 with 226 of 370. The reasons are visible and are not a like-for-like
comparison — see [the same documents as files](#the-same-documents-as-files).
`--kb` delivers evidence you can address inside a base. When you have the
files, build from the files.

## The base

| | |
|---|---|
| knowledge base | `family-readmes-v1`, id `035be669-f79c-458f-b119-f295d1e65859`, on a development WeKnora (tenant 10011, Postgres vector store, keyword + vector on) |
| created | 2026-11-25 19:05:35, by the agent that ran the round — not by a person |
| documents | 23: the public README of 23 vicfei repositories, one document per repository, title = repository name. 22 are MIT, 1 is Apache-2.0 |
| chunks | 369 after WeKnora's own parse and chunking (`chunk_counts.json`: `dsh-super-agent` 111, `dsh-evoontology` 35, `dsh-wrenai` 23 … `format-anything` 6) |
| sources | `sources.tsv`, no header: name, repository, HEAD at fetch, visibility, license, bytes, sha256 of the README (first 16 hex digits) |

This is not the frozen corpus of `eval/before-after/`. Of its 19 READMEs, 17 are
byte-identical here; two were fetched at a later HEAD (`dsh-auto-ontology`
076c85ec → 2f5e4d92, `dsh-evoontology` fdbd48fa → ad2c16e6); four repositories
were not in it (`agentdiary-dsh-plugin`, `dsh-evidence-plugin`,
`dsh-super-agent`, `format-anything`).

The round's engine is `build_ontology.py` and `grounding.py` at the hashes in
`engine-hashes.txt` — the two files are unchanged since the run started — on the
branch for issue #56 over `main` 2f5e4d9.
The domain string is in `domain.txt`; the command is `run-full.sh`.

## The round (`build.log`, `ontologies/20261125-1945.json`)

```
auto-ontology build --kb 035be669-f79c-458f-b119-f295d1e65859 --domain "$(cat domain.txt)" --save
```

| | |
|---|---|
| ran | 19:36:51 → 19:45:57, 546 s, exit 0 |
| read | 369 chunks of 23 documents, no `--limit`; 0 documents skipped (all 23 had `parse_status` `completed`) |
| TBox | 15 entity types · 15 relation types, drawn by one schema call from the opening 1,500 characters of the first 4 documents (`agentdiary-dsh-plugin`, `dsh-ai-hedge-fund`, `dsh-auto-ontology`, `dsh-ccxt`) |
| assertions | 72 entities · 55 relations · 0 conflicts · 0 unknown types flagged · 0 ungrounded type clashes |
| grounding (judge `deepseek-chat`, the engine's default) | entities 35 grounded · 37 ungrounded; relations 23 grounded · 32 ungrounded; 8 quotes re-grounded |
| evidence | 248 quotes: 187 on entities, 61 on relations; 76 grounded · 172 ungrounded · 0 never judged; 112 distinct chunks cited, i.e. 257 of the 369 chunks yielded nothing |
| cost | 751 calls · 735,632 in / 31,107 out tokens (build model `deepseek-chat`) |

By type: `dsh_plugin` 44 entities (17 grounded), `agent_persona` 9 (6), then
six types with two entities each and two with one; 3 of the 15 types got no
entity. By predicate: `sibling_of` 41 of the 55 relations (13 grounded),
`has_persona` 4 (4), two predicates with two each and six with one; 5 of the 15
relation types got no relation.

Cost against the file build is not comparable: the file build reads a document
up to 6,000 characters — at most 92,688 characters of these 23 READMEs, in two
runs, 567 calls, 349,990 in / 52,789 out tokens — and the chunk build read
151,151 characters of chunk text, including all 111 chunks of `dsh-super-agent`
(45,957 characters against the file build's 6,000).

## Verification (`verify.log`, `verify.json`)

`verify_kb_round.py` reads every evidence in the artifact — entities,
relations, conflicts, flagged unknown types, ungrounded clashes,
certifications — and resolves each `chunk_id` twice:

- **API**: `GET /api/v1/chunks/by-id/{id}` (the knowledge-base document list
  is read in pages of 100 for the titles — the endpoint's default page is 20).
- **SQL**: `SELECT … FROM chunks c LEFT JOIN knowledges k ON k.id =
  c.knowledge_id` on the server's Postgres (`--sql`).

A record passes when the chunk exists, belongs to this base, is a text chunk,
is enabled and not deleted, its document's title equals the evidence's `doc`,
and the quote is contained in the chunk's text — in the build's comparison
form (`grounding.is_verbatim`: markdown code and emphasis marks and blockquote
markers dropped, whitespace collapsed). One exception is by design: a quote the
build's verbatim gate rejected is expected to be **absent** from its chunk and
must carry `grounded: false`.

| check | API | SQL |
|---|---|---|
| evidence records in the artifact | 248 | 248 |
| carrying a `chunk_id` | 248 | 248 |
| chunk found | 248 | 248 |
| in this knowledge base | 248 | 248 |
| document title equals the evidence's `doc` | 248 | 248 |
| a text chunk, enabled, not deleted | 248 | 248 |
| quote contained in the chunk | 247 | 247 |
| the one not contained | gate-rejected, ungrounded — expected | same |
| **failed records** | **0** | **0** |

Contained means in the comparison form. As raw byte substrings the count is
204: 43 quotes differ from the chunk by markdown marks or line breaks (for
example `**Buffett, Munger, Lynch and Wood value your ticker independently…`
against a chunk carrying the same sentence with its `**`). That is the
definition of verbatim the engine has had since #35; `--kb` did not change it.

The one absent quote is a sentence the model composed, not copied:
"Install dsh-compaction-semantic from https://github.com/vicfei/dsh-compaction-semantic
into this profile: run `dsh plugin --profile <name> add dsh-compaction-semantic`"
— offered for the entity `dsh-compaction-semantic`, rejected by the verbatim
gate, kept as an ungrounded evidence with its chunk id. It is the gate working,
not a `chunk_id` failure: the chunk it names is real, and the sentence is not
in it.

The two readers agreed on every record.

## The typed tool, live (`typed-tool/`)

The plugin's `ontology_build` tool took a `kb` argument and a `limit`:

| call | outcome |
|---|---|
| `ontology_build({domain})` — neither `docs` nor `kb` | throws `ontology_build needs docs (a document corpus) or kb (a WeKnora knowledge-base id)` |
| `ontology_build({docs, kb, domain})` — both | throws `ontology_build takes docs or kb, not both: one source per build` |
| `ontology_build({kb, limit: 6, domain})` | 19 s · 32 calls · 17,546 in / 2,663 out tokens · 8 entity types · 17 entities (13 grounded · 4 ungrounded) · 5 relations (5 grounded) · 22 evidences, 22 with `chunk_id` · `provenance.kb.limit = 6` |

Registered parameters: `docs, kb, limit, domain, merge, sample, max_calls, lang`,
required `["domain"]`. `limit` defaults to 40 inside the tool, so a typed call
reads a bounded slice unless the caller raises it; the timeout is 30 minutes
for a `kb` build and 10 for a `docs` build. The artifact is
`typed-tool/20261125-1949.json` — a third small build, kept.

## The 12-chunk smoke (`smoke/`)

The first run against the base, `--limit 12`: the first 12 chunks of the
reading order, which cut into the first document (`agentdiary-dsh-plugin` has
16). Finished 19:35:55, 51 s · 52 calls · 29,895 in / 3,391 out tokens ·
9 entity types · 18 entities (12 grounded · 6 ungrounded) · 5 relations
(4 grounded) · 1 quote re-grounded. Its console summary was not saved to a
file; these numbers are read off the artifact.

30 evidence records, all with a `chunk_id`, 7 distinct chunks; verification
29 contained, 0 failed. The one absent quote is the prompt's own label line,
`agentdiary-dsh-plugin · chunk 8`, which the model quoted instead of a sentence
of the chunk. The verbatim gate rejected it and it stayed as an ungrounded
evidence. FORMAT.md now says so under *Building from a knowledge base*: the
verbatim gate checks a quote against its own chunk, and a span taken from
anywhere else, the prompt's label line included, fails and is kept.

## `chunk_id` through the loop (`smoke/evo-import.log`)

The smoke's trajectory stream (`20261125-1935.trajectory.ndjson`, 32 records)
was imported into a dsh-EvoOntology workspace (branch
`feat/e2-auto-ontology-adapter`, ad2c16e): 30 assertion records, 30 with a
`chunk_id` in the evidence; the projected layer holds 24 Term evidences and 24
of them carry `chunk_id`. The id survives the stream and the projection. It is
lost one step later: the adapter's proposals and its `retype()` do not carry a
`chunk_id` back. That is a dsh-EvoOntology follow-up, not a dsh-auto-ontology
one.

## The same documents as files (`compare.log`)

`compare_builds.py` sets the chunk build beside the file build of the same 23
repositories (`eval/live-round/artifacts/20261125-183444-certified.json`: 19
documents built 17:15–17:18, 4 merged at 18:32, 22 entity types). Twenty-one of
the READMEs are byte-identical in the two builds; `dsh-auto-ontology` and
`dsh-evoontology` were read at an earlier HEAD by the file build (076c85ec and
fdbd48fa) than by the base (2f5e4d92 and ad2c16e).

| | file build | chunk build |
|---|---|---|
| entities / relations | 128 / 177 | 72 / 55 |
| quotes · grounded | 370 · 226 (61%) | 248 · 76 (30%) |
| entities grounded | 81 / 128 | 35 / 72 |
| entity types | 22 | 15 |

Where the difference sits:

- **41 names are in both.** 23 are grounded in both, 11 by the file build only,
  1 by the chunk build only, 6 in neither. The 11 were typed by the file build
  `upstream_project` (5) or `dsh_plugin` (6); `upstream_project` is a type the
  chunk build's TBox does not have.
- **87 names are only in the file build**, 47 of them grounded — types the
  chunk build's TBox lacks or barely uses: `upstream_project` 15, `guardrail`
  7, `output_artifact` 4 …
- **31 names are only in the chunk build.** Most are fragments a reader of one
  chunk at a time would take for a name — `ccxt_bridge.py`,
  `ontologies/20261118-1441`, `PASS @ 55`, `dsh-Kronos v0 (baseline)`,
  `deepseek-chat` typed `agent_persona` — beside a few real ones (`investment
  committee`, `trading guard`).
- **Of the chunk build's 37 ungrounded entities, 24 have a judge reason that
  speaks of "plugin"**: the name is a thing inside a plugin, and the TBox had no
  closer type than `dsh_plugin`.
- **41 of the 55 relations are `sibling_of`** — a sentence that says "sister
  repo" is easy to find in any chunk. The file build's 177 relations spread
  over `sister_of` 79, `enforces` 18, `inspired_by` 18, `produces` 16 …

Three causes, all visible and none isolated:

1. **A different TBox.** Each build drew its own from its own sample, so the
   chunk build had no `upstream_project`, `guardrail` or `output_artifact` to
   type with.
2. **One chunk at a time.** A chunk carries a table row or an installation
   command without the README's opening that says what the repository is; the
   names extracted from it are the row's, not the repository's.
3. **More text, where the documents are long.** 151,151 characters of chunk
   text against at most 92,688 for the file build — the difference sits in six
   READMEs longer than 6,000 characters, first of all `dsh-super-agent`
   (45,957 against 6,000).

**Not controlled.** No run held the TBox fixed while changing the source. A
same-TBox comparison has not been made, and this table should not be read as
one.

## Files

| path | what it is |
|---|---|
| `build.log` | the console of the published round, as written |
| `ontologies/20261125-1945.json` · `.md` | the round's artifact (format v0.3; `--kb` evidence carries `chunk_id`) |
| `verify.log` · `verify.json` | the verifier's output and its 248 findings, API and SQL |
| `verify_kb_round.py` | the verifier |
| `compare.log` · `compare_builds.py` | the file-versus-chunk description and the script that prints it |
| `typed-tool/` | the live `ontology_build` calls and their artifact |
| `smoke/` | the 12-chunk run, its stream, its verification, the evoontology import |
| `sources.tsv` · `chunk_counts.json` · `domain.txt` · `run-full.sh` · `engine-hashes.txt` | the base's inputs |

## Re-running

```bash
export WEKNORA_URL=… WEKNORA_API_KEY=…          # WEKNORA_TENANT_ID when the key is tenant-scoped
export DEEPSEEK_API_KEY=…
auto-ontology build --kb <knowledge-base-id> --domain "…" --save       # [--limit N] to read a slice
python3 eval/kb-round/verify_kb_round.py ontologies/<timestamp>.json --sql --json verify.json
python3 eval/kb-round/compare_builds.py FILE_BUILD.json ontologies/<timestamp>.json
```

`--sql` needs `docker exec` on the WeKnora host; without it the API reader
alone runs. The verifier exits 1 on any failed record.

## What this round does not show

- That the chunk build's TBox is worse — only that it is different and that a
  different TBox changes the ABox a great deal.
- A multi-tenant base, a base with failed parses (`skipped_documents` was
  empty), disabled chunks or non-text chunks: none was present.
- A base large enough for `--limit` to matter as a cost guard beyond two small
  runs that stopped inside their first document (12 chunks and 6 chunks).
- Any judge other than `deepseek-chat`.
