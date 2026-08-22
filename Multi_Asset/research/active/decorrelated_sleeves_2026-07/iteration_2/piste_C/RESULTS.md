# RESULTS — Piste C iteration: Connors RSI2 + trend gate  (CORRECTED — win retracted)

**Run:** 2026-07-08, daily, 4-index portfolio, net of active-fill cost + swap. Engine `run_connors.py`.
> **⚠ Correction 2026-07-08:** an earlier version of this file reported Sharpe 0.69 and challenge
> P(pass)≈0.5. That was inflated by a **financing sign bug** (`net = gross - tc - fin` with `fin` already
> signed-negative → swap credited as income). See `../CORRECTION_2026-07-08.md`. Corrected numbers below.

## Verdict: **FAILS the bar** — Sharpe 0.37 after correct overnight financing. 0/24 cells > 0.5.

The idea (Connors RSI2<10 above the 200-day SMA, long-only, vol-filtered, intraday-stopped, 4-index
portfolio, vol-targeted 8%) has a real *gross* dip-buying tendency, but it holds long index CFDs
**overnight for ~3 days**, and the FTMO long-index financing (~**−2.1 bps/night**, current high-rate era)
eats the edge:

| metric | buggy (as-reported) | **corrected** | bar | pass |
|---|--:|--:|---|:--:|
| Net Sharpe (best cell) | 0.69 | **0.37** | >0.5 | ✗ |
| HAC t | 3.00 | 1.58 | >2.5 | ✗ |
| Cells with Sharpe>0.5 | 15/24 | **0/24** | — | ✗ |
| Ann. return | 2.8 % | **1.5 %** | — | — |
| MaxDD / worst day | −8.5 % / −4.2 % | −8.8 % / −4.3 % | DD ok | (DD fine, edge gone) |
| DSR | 0.99 | 0.89 | — | (of a sub-0.5 Sharpe) |

The DD profile is still FTMO-safe (−8.8 % / −4.3 %) — the fix did not change the drawdowns, it removed the
fake financing income. So the honest reading: **the drawdown was controllable, but the net edge after
real financing is only 0.37 Sharpe — below the bar.**

## Why it fails (the real, structural reason)
Long-only index mean-reversion **must** hold overnight (reversion takes days), so it pays the ~2 bps/night
CFD financing on the full notional. At ~3-day holds and ~110 trades/yr that is ~1.3 %/yr of financing drag
— almost exactly the strategy's gross return. This is the same overnight-financing killer the repo
documented (why the book's validated gold edge, ASIA_23_8, is deliberately **swap-free by timing**).

## What could still work (honest next step, not yet built)
A **swap-free** long-index variant that captures the overnight drift *without paying the rollover* — enter
after the financing rollover, exit before the next (the ASIA_23_8 template, Lou-Polk-Skouras overnight
drift). That avoids the killer identified here but is a *directional* (non-decorrelated) sleeve and a
different construction from Connors. Recommended as the next iteration if directional challenge sleeves are
in scope.
