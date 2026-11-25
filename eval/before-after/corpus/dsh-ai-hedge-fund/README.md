# dsh-ai-hedge-fund — an AI hedge fund of investor legends, on DeepSeek Harness

**Buffett, Munger, Lynch and Wood value your ticker independently — the PM aggregates,
names who moved the verdict, and records dissent. Every claim carries an evidence tag.**
**让巴菲特、芒格、林奇、木头姐各自独立估值你的标的——PM 聚合裁决、点名动因、
异议在案。每个主张带证据标签，输出可审计的 IC-MEMO。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![IC-MEMO](https://img.shields.io/badge/output-IC--MEMO-ff6b35)](templates/IC-MEMO.md)

> Inspired by [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) —
> restructured as a native DeepSeek Harness experience. Not affiliated; independent
> community project. Sister project of [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents)
> (the bull/bear debate committee).

## Why this exists

| | ai-hedge-fund | **dsh-ai-hedge-fund** |
|---|---|---|
| Runs where | Python lab | **Your DSH terminal** — the model key you already have |
| Calls/session | 10+ | **7 (≈40s)** |
| Personas see each other | sequential agents | **independent valuations, blind to each other** — no herd drift |
| Output | trade tables | **[IC-MEMO](templates/IC-MEMO.md)** — auditable open format |
| Dissent | — | **recorded, never deleted** — PM must name unrebutted objections |
| Abstention | — | **PASS is first-class** — “证据不足，拒绝表态” |

## Quick start (zero extra keys)

```bash
git clone https://github.com/vicfei/dsh-ai-hedge-fund && cd dsh-ai-hedge-fund
python3 scripts/hedge_fund.py --ticker DEMO                    # offline smoke, ~40s
python3 scripts/fetch_card.py --ticker NVDA                    # real US data card
python3 scripts/hedge_fund.py --ticker NVDA --data cards/NVDA.json
```

First smoke verdict (2026-11-16, temperature=0) — the value/growth split on synthetic data:

| 人格 | 立场 | 信念 |
|---|---|---|
| 沃伦·巴菲特 | PASS | 70 |
| 查理·芒格 | PASS | 72 |
| 彼得·林奇 | HOLD | 55 |
| 凯瑟琳·伍德 | HOLD | 58 |

PM: **PASS @ 68** — "巴菲特与芒格关于转换成本与定价权的论点压制了木头姐的
'降价即赛道被验证'；两位 HOLD 均为等待验证而非看多……" 而林奇与木头姐的
异议被完整记录在案（"可能错过 GARP 机会"/"低估飞轮期权价值"）。

## The fund

```
analyst ──► 4 personas value INDEPENDENTLY (blind, method-faithful)
                                │
                       risk guardrails (constraints only)
                                │
                    portfolio manager ──► IC-MEMO
                    (names its influences; dissent recorded)
```

Persona packs are config: value wing (Buffett/Munger) vs growth wing (Lynch/Wood)
by design — real disagreement is the product. `--personas` selects a subset.

## Status & roadmap

v0 engine smoke-tested (see `memos/`). Real-data adapters (US & A-share, zero keys,
CN-cloud friendly ladder) inherited from the sister project. See [ROADMAP](ROADMAP.md).

## Credits & disclaimer

Inspired by virattt/ai-hedge-fund — independent native re-implementation, MIT.
**Not investment advice.** Demo data is synthetic; real-data modes cite sources.
