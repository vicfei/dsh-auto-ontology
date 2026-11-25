# dsh-Kronos — K-line scenario forecasting for DeepSeek Harness

**A seeded, reproducible scenario fan over future K-lines from real history —
the statistical baseline that any neural foundation model will have to beat.
Zero dependencies, determinism by seed, disclosure on every payload.**

[English](README.md) | [简体中文](README.zh-CN.md)

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![Kronos MIT](https://img.shields.io/badge/upstream-Kronos%20MIT-4f46e5)](https://github.com/shiyu-coder/Kronos)

> The concept slot of [Kronos](https://github.com/shiyu-coder/Kronos) — the
> 47.9k★ "foundation model for the language of financial markets" — natively in
> DSH. **v0 ships the statistical baseline (stationary block bootstrap), not the
> neural model**: honest disclosure rides on every payload, and when the real
> model lands in M1 (`--via kronos`, HF weights), this baseline becomes its
> control anchor — the network must beat bootstrap to count. Not affiliated.
> Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-OpenBB](https://github.com/vicfei/dsh-OpenBB) · [dsh-CCXT](https://github.com/vicfei/dsh-CCXT) ·
> [dsh-nautilus_trader](https://github.com/vicfei/dsh-nautilus_trader) · [dsh-jesse](https://github.com/vicfei/dsh-jesse) ·
> [dsh-quantstats](https://github.com/vicfei/dsh-quantstats) · [dsh-QuantLib](https://github.com/vicfei/dsh-QuantLib) ·
> [dsh-hummingbot](https://github.com/vicfei/dsh-hummingbot) · [dsh-Vibe-Trading](https://github.com/vicfei/dsh-Vibe-Trading) ·
> [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund).

## Why (Kronos is a neural model — why ship a bootstrap first?)

| | Kronos (neural FM) | **dsh-Kronos v0 (baseline)** |
|---|---|---|
| Deps | torch + HF weights (~GB) | **zero** (stdlib only) |
| Determinism | sampling seeds | **seeded bootstrap — bit-exact reproducible** |
| Where | Python/GPU lab | **DSH in-session** — agents get scenario fans in the loop |
| Role | learned conditional structure | **the anchor any learned model must beat** — and the honest fallback when weights/network aren't there |

## Install

```bash
npm i -g dsh-kronos             # or: dsh plugin add dsh-kronos
dsh-kronos --data <klines.json> --horizon 30 --paths 1000 --seed 42 --save
```

Requires `python3` on PATH (stdlib only, no pip installs). From source: clone
and call `python3 scripts/scenario.py` directly.

## Quick start

```bash
git clone https://github.com/vicfei/dsh-Kronos && cd dsh-kronos
python3 scripts/scenario.py --data <klines.json> --horizon 30 --paths 1000 --seed 42 --save
python3 scripts/scenario.py --data klines.json --lang zh ...   # Chinese fallback
```

Real smoke (binance BTC/USDT 365d, 2026-11-17, seed 42): 30-step fan with
terminal P10/P50/P90 = **53.1k / 62.6k / 73.2k** and P(above current) = **38.9%** —
the market's own history prices the downside wider than the upside. Reproduce
bit-exact with the same seed.

## Status & roadmap

v0.3.0 — V1 hardening, V2 comparison flagship, V3 depth all shipped; 31
hermetic checks + CI green.

**In the box**: scenario fans with a reproducibility envelope on every
payload; the **self-evaluation harness** (rolling OOS coverage/CRPS of the
fan itself); the **head-to-head layer** (`compare.py` — bootstrap vs gaussian
vs optional `--via kronos` over upstream HF weights; neural only counts when
it significantly beats bootstrap); joint multi-symbol scenarios preserving
realized co-movement; vol-regime conditioning (pool disclosed); optimizer
objective interface for family consumption. See [ROADMAP](ROADMAP.md) for V4
(SCENARIO-REPORT spec, WeKnora-backed history).

## License & disclaimer

MIT; concept slot of an MIT upstream — no upstream code used. **Scenarios are
not predictions; not investment advice.**
