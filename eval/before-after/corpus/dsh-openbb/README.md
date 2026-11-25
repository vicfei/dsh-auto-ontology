# dsh-OpenBB — the OpenBB data platform as DeepSeek Harness tools

**A curated bridge from OpenBB (75k★, Apache-2.0) into DSH agents: an LLM plans
commands from a catalog, a deterministic bridge executes them, and findings cite
their fields — providers and timestamps travel with every row.**
**OpenBB 数据平台的 DSH 工具化：LLM 按目录规划 → 确定性桥执行 → 结论挂靠字段，
每行数据带 provider 与时间戳。**

[![DeepSeek Harness](https://img.shields.io/badge/DSH-plugin-4E6DD4)](https://github.com/deepseek-ai) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE) [![OpenBB Apache-2.0](https://img.shields.io/badge/upstream-OpenBB%20Apache--2.0-6b4fbb)](https://github.com/openbq-org/OpenBB)

> Built on [OpenBB](https://github.com/openbq-org/OpenBB) — independent community
> bridge, not affiliated. Family: [dsh-TradingAgents](https://github.com/vicfei/dsh-TradingAgents) ·
> [dsh-ai-hedge-fund](https://github.com/vicfei/dsh-ai-hedge-fund) ·
> [dsh-Vibe-Trading](https://github.com/vicfei/dsh-Vibe-Trading).

## Why (OpenBB already has an agent story — what does this add?)

| | raw `pip install openbb` in DSH | **dsh-OpenBB** |
|---|---|---|
| Surface | full Python API — huge, unscoped | **curated command catalog** with schemas — agents plan reliably |
| Numbers | model-driven calls, raw dumps | **deterministic bridge** + findings cite fields `[F#]`, model never invents figures |
| Provenance | varies | **provider + fetched_at on every payload**; failures reported honestly ("data missing, no speculation") |
| Family | — | feeds the committee/fund/research engines as the rich multi-provider data tier |

Real smoke (2026-11-16, 36s, temperature=0): asked about NVDA pricing — surfaced the
**IV30-at-annual-high vs price-at-annual-low** tension from cboe fields, and when
`equity.profile` errored, the findings said so and declined to speculate. That's the product.

## Quick start

```bash
pip install --user openbb openbb-equity openbb-news openbb-economy openbb-yfinance openbb-sec
git clone https://github.com/vicfei/dsh-OpenBB && cd dsh-OpenBB
python3 scripts/obb.py --list                                    # command catalog
python3 scripts/obb.py --run equity.price.quote --params '{"symbol":"NVDA"}'
python3 scripts/obb_research.py --question "NVDA 当前定价什么状态？" --symbols NVDA --save
```

Multi-provider by default (cboe/sec keyless today; yfinance/fred/polygon… configurable).

## Status & roadmap

v0 bridge + research engine smoke-tested. See [ROADMAP](ROADMAP.md) — M1: family data
tier (feeds all three sibling engines), catalog expansion, REST/OpenAPI mode; M2: cordis
plugin typed tools (`dsh plugin add dsh-openbb`).

## License & disclaimer

MIT bridge over Apache-2.0 upstream — no upstream code vendored; install via pip.
**Not investment advice.**
