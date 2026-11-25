# dsh-QuantLib — derivatives pricing as DeepSeek Harness tools

**Black-Scholes prices, full Greeks, implied vol, American binomial trees —
computed by a zero-dependency analytic core that ships its own proof: parity,
Greek identities and IV round-trips must pass exactly before any price leaves
the house. Assumptions ride on every payload.**
**BS 定价、全套希腊字母、隐含波动率、美式二叉树——零依赖解析核心，自带证明：
平价关系/希腊恒等式/IV 往返必须精确通过，价格才能出门。假设随每份载荷披露。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![QuantLib BSD](https://img.shields.io/badge/concept-QuantLib%20BSD-2f9e8f)](https://github.com/lballabio/QuantLib)

> Implements the core of [QuantLib](https://github.com/lballabio/QuantLib) —
> the standard open-source quant finance library — natively for DSH.
> Not affiliated. Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund) ·
> [dsh-Vibe-Trading](https://github.com/vicfei/dsh-Vibe-Trading) ·
> [dsh-OpenBB](https://github.com/vicfei/dsh-OpenBB) · [dsh-CCXT](https://github.com/vicfei/dsh-CCXT) ·
> [dsh-nautilus_trader](https://github.com/vicfei/dsh-nautilus_trader) ·
> [dsh-hummingbot](https://github.com/vicfei/dsh-hummingbot) · [dsh-jesse](https://github.com/vicfei/dsh-jesse) ·
> [dsh-quantstats](https://github.com/vicfei/dsh-quantstats).

## Why (QuantLib exists — what's the DSH-native angle?)

| | QuantLib (C++/SWIG) | **dsh-QuantLib** |
|---|---|---|
| Runs where | C++/Python labs | **DSH in-session** — agents price instruments in the loop |
| Deps | heavy SWIG build | **zero-dependency analytic core** (stdlib math only) |
| Trust | industry standard | **ships its own proof**: `--selftest` runs parity/identity/round-trip checks that must pass exactly |
| Coverage | everything | v0: BS76 + Greeks + IV + CRR American; curves/bonds in M1 |

## Quick start

```bash
git clone https://github.com/vicfei/dsh-QuantLib && cd dsh-quantlib
python3 scripts/pricing.py --selftest        # the proof: parity, Greeks, IV round-trip
python3 scripts/pricing.py --cmd option.european \
  --params '{"S":162.85,"K":165,"T":0.25,"r":0.04,"q":0,"sigma":0.6309,"type":"call"}'
```

Real-input smoke (2026-11-17): NVDA at its live price 162.85 with the live
IV30 63.09% (cboe via the family's OpenBB bridge) prices the 165 call at
**20.19, delta 0.559, gamma 0.0077** — assumptions disclosed on the payload.
American BTC put at live spot 64344 / 45% vol: 7904 via 400-step CRR, and the
self-test proves American ≥ European holds.

## Status & roadmap

v0 analytic core smoke-tested. [ROADMAP](ROADMAP.md): M1 yield curves + bonds +
QuantLib-Python adapter (`--via quantlib` for engine-grade coverage); M2
volatility surfaces.

## License & disclaimer

MIT; concept inspired by BSD-licensed upstream — no upstream code used.
**Not investment advice.**
