# dsh-tradingagents — TradingAgents, natively on DeepSeek Harness

**A multi-agent investment committee that debates in your terminal — every claim tagged, every verdict auditable.**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![IC-MEMO](https://img.shields.io/badge/output-IC--MEMO-ff6b35)](templates/IC-MEMO.md) [![ci](https://github.com/vicfei/dsh-TradingAgents/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml) [![npm](https://img.shields.io/npm/v/dsh-tradingagents)](https://www.npmjs.com/package/dsh-tradingagents)

> Inspired by [Tauric Research's TradingAgents](https://github.com/TauricResearch/TradingAgents) and
> [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) — restructured as a
> native DeepSeek Harness experience. Not affiliated; independent community project.
> [中文文档](README.zh-CN.md)

![demo](assets/demo.png)

*A real `tradingagents demo --guests all --save` run (npm 0.1.0, 10 calls · 56s): the four
guest seats split three ways — Buffett/Munger PASS@72, Lynch HOLD@55, Wood BUY@62 — the
risk officer logs the split as guardrail [G8], and the PM rules PASS@72 naming it.
Replay: `asciinema play assets/demo.cast`*

![session map](assets/session.svg)

*The same session as a map — parsed from the archived IC-MEMO (`scripts/render_session_svg.py`,
a product feature: every memo can render one): the pipeline with how much tagged evidence
each stage produced, the guest split with stance colors and conviction bars, and the PM
verdict banner. (The map above shows a second real run: guests split PASS@72 / PASS@72 /
HOLD@55 / OVERWEIGHT@62 — five-tier vocabulary in the wild — and the PM rules HOLD@58.)*

## Why this exists

| | TradingAgents | ai-hedge-fund | **dsh-tradingagents** |
|---|---|---|---|
| Runs where | Python lab | Python lab | **Your DSH terminal/session** — model key you already have |
| Model calls/session | dozens (tool loops × debates) | 10+ | **6 (+1 per guest seat, ≈31–40s)** |
| Market data | Yahoo-centric, keys optional | — | **zero-key by default: CBOE quote/K-line/options-IV + SEC 10-K + nasdaq news (OpenBB), Tencent fallback** |
| Output | text logs | trades table | **[IC-MEMO](templates/IC-MEMO.md)** — open, auditable memo format |
| Evidence discipline | — | — | **every claim tagged `[A#][B#][R#][G#]`, verdict must name what moved it** |
| Abstention | — | — | **PASS is a first-class verdict** — "insufficient evidence, decline to rule"; an unparseable verdict surfaces as REVIEW, never silently a Hold |
| Risk officer | team output | — | guardrails **only** — constrains, never decides |

The differentiator is **auditability**: analyst → bull → bear → rebuttal →
risk guardrails → portfolio manager. The PM cannot cite anything untagged, cannot overrule
the guardrails, and cannot dress up thin evidence as conviction. When the data doesn't
support a call, the committee **abstains with reasons** — and tells you exactly what new
evidence would reopen the case.

## Quick start (zero extra keys)

Install as a plugin (npm 0.1.0, ships the engine + skill):

```bash
npm i -g dsh-tradingagents
tradingagents demo --guests all --save          # offline synthetic smoke, ~40s
tradingagents card --ticker NVDA --committee    # zero-key real data → full committee
# register the DSH skill:
ln -s "$(npm root -g)/dsh-tradingagents/skills/dsh-tradingagents" ~/.dsh/skills/dsh-tradingagents
```

Or run from source:

```bash
git clone https://github.com/vicfei/dsh-TradingAgents && cd dsh-tradingagents
python3 scripts/tradingagents.py --ticker DEMO                  # offline synthetic smoke, ~30s
python3 scripts/tradingagents.py --ticker DEMO --guests all --save   # + 4 guest seats, ~40s
python3 scripts/fetch_card.py --ticker NVDA --committee         # real US data → full committee
python3 scripts/fetch_card.py --ticker 600519 --committee       # real A-share data → full committee
```

Output language is English by default; `--lang zh` switches memos and cards to Chinese
(env `TRADINGAGENTS_LANG`).

Real data runs on a multi-provider ladder, CN-cloud friendly and **Yahoo-free**:
**OpenBB rich card (default, `pip install --user openbb`): CBOE quote / K-line /
options-implied vol + SEC 10-K statements + nasdaq news — all zero-key
→ Tencent gtimg fallback (works behind the GFW: quote / PE / mcap / PB +
K-line technicals, same engine for US & A-share) → `--via-relay` full yfinance
through any SSH relay**. Every card item carries its source and as-of date —
the evidence-tag discipline starts at the data layer.

DEMO verdict from the very first smoke run (2026-11-16, temperature=0; translated
from the archived Chinese memo):

> **PASS @ 55** — "Abstain rather than lean bullish or bearish… the bear's timing-mismatch
> argument ([R1][R2][R4]: revenue / gross margin / share all predate the price-cut
> signal [A7]) persuades me toward caution; [A8] undisclosed contract value and
> [A9] an unverifiable valuation basis are two hard gaps; the evidence does not
> support a ruling, so by discipline PASS — reopen when any [G8] re-review event lands."

A committee that **abstains with reasons** is the feature.

## The committee

```
analyst ──► bull ──► bear (cross-exam) ──► bull rebuttal
                                               │
                 ┌─ optional guest seats ──────┤   Buffett / Munger / Lynch / Wood
                 │  (persona pack cross-linked │   from sister repo dsh-ai-hedge-fund;
                 │   each critiques the debate │   they judge the bull-bear clash
                 └────────── through their own methodology)
                                               ▼
                        risk (guardrails only) ──► portfolio manager ──► IC-MEMO
                                                   (BUY/HOLD/SELL/PASS + confidence
                                                    + invalidation triggers)
```

## IC-MEMO — an open format

Every session emits an [IC-MEMO](templates/IC-MEMO.md): decision yaml head, tagged
fact layer, full debate, guardrails, and a verdict that must name its influences.
Unresolved dissent is recorded, never deleted. Spec evolution lives in `docs/`.

## The family bridge (0.3.0)

dsh-vibe-trading research trails feed this committee directly:

```bash
python3 scripts/vibe_research.py --save --question "..." --symbols sh600519,sh000001   # dsh-vibe-trading
tradingagents --data trails/<name>/r1.json --ticker sh600519 --save                     # this repo
```

The trail's deterministic computed layer (stats, OOS backtest segments,
source metadata) enters as covenant-safe evidence; its findings ride as a
research note conspicuously marked **PRIOR LLM INTERPRETATION — context
only, never data**. Live E2E: a real Moutai trail → OVERWEIGHT@58 with the
4-trade win-rate dismissed as statistically empty.

## Status & roadmap

v1 engine shipped (npm 0.1.1, English-first): 6-role committee + guest seats + OpenBB
zero-key rich cards + CI. The **track-record loop** is live: every archived verdict
becomes a pending ledger entry; once its 5-trading-day window trades out it settles with
raw return and alpha vs the market benchmark (SPY / SSE Composite), a short reflection
is written, and the next committee session reads the lessons before ruling
(`tradingagents settle`). See [ROADMAP](ROADMAP.md) for the launch battle (marketplace +
channels), the verdict dual-exit work, and the ecosystem track (portfolio committee,
typed-tools plugin, IC-MEMO spec).

## Credits & disclaimer

Structure inspired by TradingAgents (Tauric Research) and ai-hedge-fund (virattt) —
this project is an independent native re-implementation for DeepSeek Harness, MIT.
**Not investment advice.** Demo data is synthetic; real-data modes cite their sources.
