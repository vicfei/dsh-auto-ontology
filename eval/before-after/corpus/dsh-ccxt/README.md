# dsh-CCXT — 100+ crypto exchanges as DeepSeek Harness tools, fail-closed by design

**Read-only market data flows freely; orders don't — a triple-armed guard with
notional caps and a symbol whitelist, enforced in bridge code the LLM cannot bypass.
Every payload carries its exchange and timestamp.**
**读类行情自由流动，下单默认锁死：三重解锁 + 名义额上限 + 交易对白名单，
护栏在代码层，LLM 绕不过。每条数据带交易所与时间戳。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![ccxt MIT](https://img.shields.io/badge/upstream-ccxt%20MIT-2b8a3e)](https://github.com/ccxt/ccxt)

> Built on [ccxt](https://github.com/ccxt/ccxt) (44.9k★, MIT) — independent community
> bridge, not affiliated. Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund) ·
> [dsh-Vibe-Trading](https://github.com/vicfei/dsh-Vibe-Trading) ·
> [dsh-OpenBB](https://github.com/vicfei/dsh-OpenBB).

## Why (ccxt is a library — and two DSH plugins already touch it)

Existing DSH entries wire ccxt K-lines into *their own* invest apps. This is the
**standalone, agent-first bridge** — and the only one with a trading guard:

| | raw ccxt via bash | invest-app ccxt providers | **dsh-CCXT** |
|---|---|---|---|
| Surface | full API, unscoped | their app's data needs | **curated read catalog + guarded write catalog** |
| Orders | nothing stops a fat finger | n/a | **fail-closed**: dry-run default, `--live` + env key + notional cap + whitelist |
| Provenance | — | — | exchange + fetched_at on every payload |
| Research | — | — | 2-call engine, findings cite fields, scope limits reported honestly |

## Quick start

```bash
pip install --user ccxt
git clone https://github.com/vicfei/dsh-CCXT && cd dsh-CCXT
python3 scripts/ccxt_bridge.py --run market.fetch_ticker --params '{"exchange":"binance","symbol":"BTC/USDT"}'
python3 scripts/ccxt_research.py --question "BTC 近 90 日量价结构？" --save
```

The guard, demonstrated:

```
trade.create_limit_order … → {"guard":"BLOCKED","reason":"DRY-RUN（默认）：订单未发送。
实盘需 --live + CCXT_LIVE_TRADING=1 + 密钥三重解锁"}
```

Real smoke (2026-11-17, binance via relay, 8s, temperature=0): BTC −16.2% over the
visible window with **volume expanding into the breakdown**; and when the bridge's
15-candle payload didn't cover the requested 90d range, the findings said so —
"整体判断不成立，仅为可见片段结论" — instead of over-claiming. That's the product.

## Status & roadmap

v0 bridge + guard + research engine smoke-tested on live data. [ROADMAP](ROADMAP.md):
M1 full-range summaries, cross-exchange spreads/funding, paper-trading simulator;
M2 **native TypeScript cordis plugin** (ccxt is JS-first — this family member goes
pure-TS naturally).

## License & disclaimer

MIT bridge over MIT upstream. **Not investment advice. Live trading is guarded
off by default; enabling it is your decision and your risk.**
