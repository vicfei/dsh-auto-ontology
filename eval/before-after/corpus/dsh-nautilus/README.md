# dsh-Nautilus — a professional backtesting engine as DeepSeek Harness tools

**Trend strategies, fees, drawdowns — computed by NautilusTrader's compiled-core
indicators and event-driven engine, not hand-rolled arithmetic. Every result
carries bars/trades/span/fee metadata; the honest number wins.**
**专业级回测引擎进 DSH：策略、费率、回撤——出自 NautilusTrader 的编译核心指标
与事件驱动引擎。每个结果带 bars/trades/span/费率元数据，诚实的数字说了算。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![NautilusTrader LGPL-3.0](https://img.shields.io/badge/upstream-NautilusTrader%20LGPL--3.0-c25b9e)](https://github.com/nautechsystems/nautilus_trader)

> Built on [NautilusTrader](https://github.com/nautechsystems/nautilus_trader)
> (31.6k★) — independent community bridge, not affiliated.
> Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund) ·
> [dsh-Vibe-Trading](https://github.com/vicfei/dsh-Vibe-Trading) ·
> [dsh-OpenBB](https://github.com/vicfei/dsh-OpenBB) · [dsh-CCXT](https://github.com/vicfei/dsh-CCXT).

## License posture (upstream is LGPL-3.0 — how we stay clean)

MIT bridge over an **unmodified pip dependency**: no vendoring, no source
modification, user installs `nautilus_trader` themselves. LGPL explicitly permits
this use; the red line (modifying the library without open-sourcing changes) is
never crossed. See [ROADMAP](ROADMAP.md) for details.

## Why (Vibe-Trading already has a mini backtest — what's this?)

| | toy SMA cross in dsh-Vibe-Trading | **dsh-Nautilus** |
|---|---|---|
| Engine | 20-line hand-rolled loop | **NautilusTrader compiled-core indicators + event-driven execution** |
| Fees/slippage | none ("fee-free structural probe") | **fee-aware, order-book slippage in M1** |
| Results | return + rough DD | **trades/drawdown/span/fee metadata on every payload** |
| Live trading | — | guarded off (family fail-closed DNA, M2) |

## Quick start

```bash
pip install --user nautilus_trader
git clone https://github.com/vicfei/dsh-nautilus_trader && cd dsh-Nautilus
python3 scripts/nautilus_bridge.py --run backtest.sma_cross \
  --data /path/to/klines.json --params '{"fast":20,"slow":60,"fee_bps":5}'
```

Real smoke (2026-11-17, binance BTC/USDT 365d via relay): SMA 20/60
**−10.3% (4 trades, max DD −24.8%) vs buy-hold −29.9%** — trend-following cut the
loss in a bear year but didn't save it. An honest number, honestly labeled.

## Status & roadmap

v0 bridge (backtest.sma_cross + indicator.compute) smoke-tested on live data.
[ROADMAP](ROADMAP.md): M1 full Actor/Strategy wiring + order-book slippage;
M2 live trading behind the family's fail-closed guard.

## Disclaimer

**Not investment advice.** Past performance ≠ future results; bar-level execution
limits are stated on every payload.
