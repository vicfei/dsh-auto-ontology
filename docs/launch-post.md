# Launch kit v1 (facts frozen 2026-11-18 · awesome PR staged, fires after npm 0.1.0)

> Owner posts with their accounts; copy is paste-ready.
> Links: repo github.com/vicfei/dsh-auto-ontology · npm npmjs.com/package/dsh-auto-ontology
> Visual: ontologies/20261118-1030.svg (the product IS the demo — a typed cluster graph of 243 entities)
> Facts: 19 family READMEs → 243 entities / 139 relations / 0 unknown-type leaks, every assertion with evidence · zero-infra stdlib CLI (no Docker/DB) vs the upstream's enterprise stack · two-pass (TBox schema → per-doc ABox) · type guard flags, never silently drops.

---

## X / Twitter (≤280, attach the SVG rendered as PNG)

Auto-ontology from your documents — every assertion carries its evidence.

- two-pass LLM: TBox schema from the corpus, then ABox assertions per doc
- no evidence, no assertion; unknown types flagged, never silently dropped
- zero-infra stdlib CLI: no Docker, no database

npm i -g dsh-auto-ontology

**Thread 2/** The screenshot is a real run: 19 READMEs → 243 entities / 139
relations. Each node is typed; each edge carries a verbatim quote from the
source doc. The JSON keeps every evidence span for audit.

**Thread 3/** The upstream (NVIDIA/auto-ontology, 13.3k★) builds governed
semantic layers from enterprise metadata — Docker, Postgres, an API key. This
is the complementary slot: document corpora → auditable ontologies, zero
infrastructure. Clean-room, not affiliated, credit in the README.

---

## V2EX / 即刻 / 掘金（CN）

标题：把 19 篇 README 喂给 LLM，得到一张每条边都带证据的知识图谱
正文要点：双 pass（TBox 模式→逐文档断言）；无证据不落库、未知类型拦截不静默；
零基建（免 Docker 免库，stdlib+现有 key）；对标 NVIDIA auto-ontology 13.3k★ 但走文档语料互补位；
`npm i -g dsh-auto-ontology` 一行装；附 SVG 分簇图。

## Discord (rea/jevcore #showcase)

EN one-post version of the X main + repo link.

## 渠道清单
- [ ] awesome-dsh PR（staged, fires after 0.1.0 publish）
- [ ] X 主贴+线程 · V2EX · 即刻 · 掘金 · Discord（owner 账号）
- [ ] Trendshift（滞后，需基础星标）
