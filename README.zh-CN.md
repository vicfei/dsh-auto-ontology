# dsh-auto-ontology — 带证据的自动本体构建，DeepSeek Harness 原生

**喂文档，得带类型的本体（TBox+ABox）——每条实体/关系带原文证据引文。
无证据不落库；未知类型拦截标注，绝不静默丢弃。**

[![npm](https://img.shields.io/npm/v/dsh-auto-ontology)](https://www.npmjs.com/package/dsh-auto-ontology) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE)

> 结构致敬 [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)（13.3k★，Apache-2.0）——
> 净室实现，零上游代码，非官方无隶属。[English README](README.md)

## 一句话定位

双 pass LLM 管线（语料抽样抽 TBox 模式 → 逐文档抽 ABox 断言），家族差异 =
**证据溯源**：每条断言带原文引文与来源文档；类型守卫拦未知类型不静默丢；
增量合并 append-only（旧证据永不改删）；同名异型落冲突条目（双方证据保全，
绝不静默解决）；人的认证判决（`--certify`）随工件走、后续构建永远尊重；
诚实精度指标（`eval`——引文是否真的支撑断言，种子可重跑，首数 10% 照发）。

## 快速开始

```bash
npm i -g dsh-auto-ontology
auto-ontology build --docs 'docs/*.md' --domain "内部设计文档" --save
auto-ontology --query "WrenAI"                 # 该实体的全部断言+证据跨度
auto-ontology validate ontologies/*.json       # 格式 v0.2 合规校验
```

仅需 `python3`（stdlib）+ DeepSeek key。产物落 `./ontologies/`：带证据的
JSON、零依赖 SVG 分簇图、markdown 摘要、单文件 HTML、JSON-LD 导出。

**纪律**：证据不可剥离；构建期接地判定——引文是否真的支撑断言（原文逐字、
点出断言、判官严判），不支撑者标记保留（实体 `type_grounding: false`、关系
`grounding: false`），可查可认证，绝不静默丢弃；append-only；冲突双证据；每产物带
溯源（模型/判官模型/调用/token/耗时）。规范见 docs/FORMAT.md（evidence-linked
ontology v0.2 开放格式，v0.1 工件仍合规）。

**不是企业建议。**
