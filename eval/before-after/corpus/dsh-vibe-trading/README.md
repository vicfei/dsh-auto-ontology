# dsh-vibe-trading — interactive trading research, natively on DeepSeek Harness

**Ask a market question → a deterministic pipeline plans, pulls data, computes, and
explains — every number from code, every finding tagged to its computation.
You get a terminal brief, a zero-dependency SVG chart card, and an auditable trail.**

[English](README.md) | [简体中文](README.zh-CN.md)

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE)

> Inspired by [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) —
> restructured as a native DeepSeek Harness experience. Not affiliated; independent
> community project. Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents)
> (bull/bear committee) · [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund) (persona fund).

## Install

```bash
npm i -g dsh-vibe-trading          # or: dsh plugin add dsh-vibe-trading
dsh-vibe-trading run --question "Moutai vs the index: whose price-volume structure is weaker?" \
  --symbols sh600519,sh000001 --name moutai-vs-index
dsh-vibe-trading scan --symbols sh600519,sz000001,sh000001 --board momentum
```

Requires `python3` on PATH (stdlib only, no pip installs). The npm package
also registers typed host tools (`vibe_research`, `vibe_scan`) and a skill.
From source: clone and call `python3 scripts/vibe_research.py` directly.

## Why a plugin (Vibe-Trading ships an MCP server — isn't `mcp.json` enough?)

| | raw Vibe-Trading MCP in DSH | **dsh-vibe-trading** |
|---|---|---|
| Interaction | you drive tool calls per step | **the research loop is orchestrated** — plan → data → compute → explain in one command |
| Numbers | produced inside model-driven calls | **deterministic compute layer** — LLM only interprets, cites fields `[F#]`, invents nothing |
| Artifact | chat text | **terminal brief + inline-SVG chart card + full trail** (question/plan/stats/backtests/findings) |
| Auditability | — | every finding points at the computation that produced it; gaps stated honestly |

## Quick start (zero extra keys)

```bash
git clone https://github.com/vicfei/dsh-Vibe-Trading && cd dsh-vibe-trading
python3 scripts/vibe_research.py --save \
  --question "Moutai vs the Shanghai index: which leg is weaker, and what does the price-volume structure say?" \
  --symbols sh600519,sh000001
python3 scripts/vibe_research.py --question "茅台 vs 上证：量价结构谁更弱？" --lang zh   # zh fallback
```

Real smoke run (2026-11-16, 6s, 2 LLM calls, temperature=0): identified the index as
the weaker leg (ret20 −3.44% vs +9.73%), flagged the shrinking-volume-up vs
shrinking-volume-down structure, and **honestly declined to lean on the 4-trade
backtest sample** — findings cite their computation fields throughout. Open
`trails/*.html` for the chart card. Output is English-first; `--lang zh` switches
user-facing labels (and the interpreter's language) to Chinese.

## What's in the box

- A-share / index K-lines via the CN-reachable Tencent ladder (no keys);
  US history is currently **degraded upstream** (the endpoint returns boundary
  bars only) — the engine refuses degenerate series honestly instead of
  computing on them
- Stats: ret20/60, SMA60 posture, 30d vol, drawdown from 120d peak, volume
  z-score, MACD histogram, Wilder RSI14 — every field is a number or an
  explicit `unavailable (reason)`, never a fake 0
- Mini trend backtest (SMA20/60 cross, position-only, fees excluded) with
  **in-sample vs out-of-sample** segments (frozen a-priori params)
- Deterministic screener boards: momentum / volatility / volume rankings +
  60d correlation matrix — zero LLM calls
- Multi-question chat sessions on cached data (`chat`)
- **Versioned research artifacts**: append-only named trails with revision
  diff (`artifacts list|show|diff|export`) — research that outlives the chat,
  in open files you own
- Typed DSH host tools (`vibe_research`, `vibe_scan`) + skill
- Zero-dependency inline SVG chart cards (offline-safe, no CDN) with the
  data-source metadata line riding on every card

## Status & roadmap

v0.3.0 — V1 hardening, V2 artifacts, V3 workbench all shipped; 35 hermetic
checks + CI green; typed tools verified on the real host shape. See
[ROADMAP](ROADMAP.md) — V4 factor workshop + family interop, V5
RESEARCH-TRAIL spec + WeKnora-backed question history.

## Credits & disclaimer

Inspired by HKUDS/Vibe-Trading — independent native re-implementation, MIT.
**Not investment advice.** Backtests are structural probes with fees excluded.
