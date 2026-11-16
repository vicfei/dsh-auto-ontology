# ROADMAP — dsh-auto-ontology

北极星：家族的本体位，吃 NVIDIA auto-ontology 13.3k★ 流量。命名全表面：
GitHub=npm=dsh-auto-ontology（镜像上游小写连字符仓名）。定位（调研实证）：
catalog 有查看器/桥接占位，**LLM 自动构建+证据溯源无人做**。

## 里程碑
### M0 ✅（2026-11-17）
双 pass 引擎（TBox schema 抽取→逐文档 ABox 断言带 evidence 原文引用）
+ 类型守卫（未知类型标注不静默丢）+ 环形分簇 SVG + JSON/markdown 产物。
真实冒烟：5 篇家族 README → 6 类型/49 实体/45 关系（含证据的家族生态本体，
人格表自动抽成 has_role 边）。

### M0.5 · 发布包
- [ ] README 打磨 + SVG 本体图截图 + npm 0.0.1 占位（owner 手动）
- [ ] 公开仓 topics + 家族互链 + marketplace + 渠道

### M1 · 规模与合并（第 2-3 周）
- [ ] 增量合并（新文档进现有本体，实体消歧/跨文档共指）
- [ ] 大语料分批（TBox 抽样策略）+ 冲突检测（同实体不同类型的断言对撞）

### M2 · 互操作（第 4-6 周）
- [ ] OWL/JSON-LD 导出（标准本体格式）+ WeKnora graph-KB 桥
  （dsh-codebase-memory 桥 MCP 的同款模式）
- [ ] cordis 插件 typed tools（ontology.build/ontology.query）

## 纪律
- 证据随断言不可剥离；未知类型拦截不静默；本体产物 append-only。
