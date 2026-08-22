# Registry card — MACD fast-trend diversifier (CANDIDATE, NOT merged)
*To be merged into the FTMO-book registry later. Held in session_basic_trend/ for now. Nothing frozen/merged.*

## What it is
A **risk-shaping diversification overlay** on the TSMOM engine — **not an edge, not a crash-hedge.** Fast-trend (MACD 12/26/9) on the FTMO-tradeable basket (indices/crypto/gold-silver CFDs).

## Why kept (the measured case)
- **Additional to TSMOM:** corr **0.08** (TSMOM's slow-trend factor does not contain it). Donchian/EMA/Momentum, by contrast, were corr 0.55+ → redundant, dropped.
- **Near-free:** net carry **−0.07%/mo** (gross +0.40%/mo − swap ~0.47%/mo). Trade-skew +4.2.
- **Pulls combined maxDD under the floor:** TSMOM-alone maxDD −13.7% → **−9.1% at a 30% MACD overlay** (under the −10% total floor); worst-day −5.9% → −4.3%.
- **GATE-0: FTMO-tradeable.** (Unlike long-vol/VXX, which is perso-only.)
- Kept **precisely because near-free** — a ~zero-cost shape improvement, not because it earns.

## ⚠ TWO EXPLICIT LIMITS (so no future reading over-rates it)
**(a) It reduces CUMULATIVE drawdown (drift toward the −10% TOTAL floor), NOT DAILY risk.** The FTMO **5% daily cap is the most frequent bust mode**, and MACD does **not** cover it — on a correlated down day it is also down (just less). The two bust modes (total floor vs daily cap) are **distinct**; MACD helps the former only.

**(b) The single-day correlated-crash tail remains UNCOVERED in FTMO.** Both MACD and TSMOM are trend → both lose on the crash day. The only true hedge is **long-vol, which is perso-only (fails GATE-0)**. So the daily-cap / crash-day tail has no FTMO-tradeable hedge in the current set.

**→ MACD helps the TOTAL floor, not the DAILY cap. Do not deploy it as crash protection.**

## Pending before any merge / portfolio construction (DO NOT merge yet)
1. **ORB 15:30 spread measurement** (tomorrow).
2. **CRITICAL — validate TSMOM's CRYPTO SWAP.** The whole architecture uses TSMOM as the engine, and its net return depends on a swap that has never been measured (equity leg measured at −3.08 bps/night; crypto unmeasured, and crypto is the swing). **An overlay that pulls maxDD under the floor is worthless if the engine is net-negative after swap.** Validate the engine before optimizing its overlay.

## Lesson candidate (named, not numbered)
**"MACD = near-free fast-trend diversifier, additional to TSMOM (corr 0.08), pulls the cumulative maxDD under the floor but does NOT cover the daily cap."**
