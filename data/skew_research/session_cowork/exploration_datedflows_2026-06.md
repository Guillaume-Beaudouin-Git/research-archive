# Dated mechanical-flow sleeves — session_cowork (batch 3: 5 candidates)
*2026-06, fresh VM, MEASURED. Phase 1 (raw edge + skew at holding horizon). Daily only (OOM-safe). Calendar = `economic_calendar.csv` (NFP/CPI/FOMC, 2020–2026). Scope: session_cowork only; archive cited; nothing frozen/merged.*

## TL;DR — 0 survivor
**Pre-CPI drift — the only gate-passer — is NON-SURVIVOR.** Its full-sample t 2.12 is an **aggregation artifact**: absent in 2021–23 (t 0.39), carried by 2024–26 + a single 2025 outlier year (+121 bps). **Decisive test — bootstrap ex-2025: t 1.53, 95% CI [−0.41, +3.29] crosses zero → not significant** (and ex-single-largest-event: t 1.95, CI lower bound +0.05 ≈ 0). Same pattern as the "94%-on-6-months" we rejected elsewhere → **dead, archived; not pushed to Phase 2** (that would only confirm the kill). The rest: NFP no-edge, FOMC = parallel session's (longer data), month-end fade = negative-skew (wrong profile), **Treasury auction = bonds → NOT FTMO-tradeable (GATE-0 fail) → perso-only**, futures-roll = cost-not-edge, expiry = archived-negative.

---

## PHASE 1 — measured

| # | Candidate | n | mean (bps) | t | SKEW | verdict |
|---|---|---:|---:|---:|---:|---|
| 1·CPI | Pre-CPI drift | 77 | +37 / +48 | +2.12 / +2.21 | +3.0 | ❌ **NON-SURVIVOR** — t is an aggregation artifact (bootstrap ex-2025 → t 1.53, CI crosses 0) |
| 1·NFP | Pre-NFP drift | 77 | −17 | −1.19 | −1.08 | ❌ no edge (pre-event drift does NOT generalize to jobs) |
| 1·FOMC | Pre-FOMC drift | 52 | +30 | +1.28 | +3.24 | ⤳ parallel session (longer data); underpowered here, not re-measured |
| 5 | Month-end FADE (perf-cond., last 3d) | 951 | +7.4 | +2.05 | **−0.24** | ⚑ wrong-profile (MR fade, neg skew); plain TOM-equity dead (archive) |
| 2 | Treasury auction cycle | — | — | — | — | ⛔ **GATE-0 FAIL — bonds NOT FTMO-tradeable → perso-only** (skip regardless of calendar) |
| 3 | Futures calendar roll | — | — | — | — | not an edge (a COST you pay; captured by LPs) — CITE |
| 4 | Expiry / pinning | — | — | — | — | options-OI absent; archive quad-witching NEGATIVE — CITE |

### Decisive test on the lone gate-passer (pre-CPI) — bootstrap
| sample | n | mean | t | bootstrap 95% CI | significant? |
|---|---:|---:|---:|---|---|
| FULL | 77 | +37.0 | +2.12 | [+0.47, +3.57] | barely |
| **EX-2025** | 65 | +21.5 | **1.53** | **[−0.41, +3.29]** | **NO (crosses 0)** |
| ex single-largest event | 76 | +25.0 | 1.95 | [+0.05, +3.73] | ≈ no |

By year: 2020 +42 / 2021 −3 / 2022 −1 / 2023 +24 / 2024 +38 / **2025 +121** / 2026 +39 → significance is carried by one outlier year. **Verdict: small-sample noise, NON-SURVIVOR, archive. Do not run a full Phase 2.**

---

## ⛔ NEW RULE BANKED — GATE-0 FTMO-tradeability (lesson from B1)
**Before ANY measurement, check the instrument is in the FTMO universe.** FTMO = **Forex, Indices, Commodities, Stocks (23 large-caps), Crypto** — **NOT** bonds, ETFs, options, futures-as-such, or spot. Any candidate outside this universe is **reclassified perso-only immediately, or skipped** — never run the full science on a non-FTMO-tradeable edge (the B1 mistake: a complete study on an untradeable instrument). This gate runs first, ahead of edge/skew/cost.

**Re-applying GATE-0 retroactively across this session's 3 batches:**
- **Long-vol (VXX)** — the prior "survivor" — is an **ETF / VIX product with no FTMO CFD → perso-only, GATE-0 FAIL for FTMO.** (Real and decorrelated, but not an FTMO sleeve.)
- **Treasury auction (this batch)** — bonds → GATE-0 FAIL → perso-only.
- The trend/metals/crypto/index work used ETF *proxies* (GLD/SLV/USO/VXX) for backtest, but the underlying FTMO CFDs (XAUUSD, XAGUSD, USOIL, indices, BTC/ETH) ARE tradeable — except VIX, which is not.

---

## SESSION BILAN — 15 candidates / 3 batches → 0 clean FTMO-tradeable survivor
| Batch | candidates | outcome |
|---|---|---|
| 1 — trend/convexity | TSMOM, Donchian, XS-mom, carry, **long-vol** | TSMOM/Donchian cost-killed; XS-mom/carry wrong-profile; **long-vol = real skew+ but ETF → perso-only (GATE-0)** |
| 2 — microstructure | gap-fade, post-limit, intraday-vol, sector-pairs, VVIX | gap-fade artifact; **post-limit = disguised long beta** (two-sided fail); rest no-edge/cited-killed |
| 3 — dated flows | NFP/CPI, treasury, roll, expiry, month-end | **pre-CPI = recent small-sample noise** (bootstrap-killed); treasury = bonds (GATE-0); rest no-edge/cost/archived-neg |

**Honest result, not a failure:** of 15 skew-positive candidates, **0 is a clean FTMO-tradeable decorrelated sleeve.** The two that were "real" are out of scope (long-vol = perso-only ETF) or disguised beta (post-limit). This is a clean, falsified negative — consistent with the program's broader finding.

**Lesson candidates (named, not numbered):**
- **"GATE-0 FTMO-tradeability first"** — check the instrument is tradeable on the target firm before any edge science (the B1 mistake: full study on an untradeable bond edge).
- **"pre-event drift doesn't generalize across macros"** — CPI (weakly)/FOMC yes, NFP no.
- **"regime-slice + ex-outlier-bootstrap any dated flow before trusting its full-sample t"** — pre-CPI's t 2.12 was one outlier year; ex-2025 it's 1.53 (n.s.).
- **"a real edge can still be out-of-scope"** — long-vol (VXX) is genuinely skew+ and decorrelated, but perso-only, not FTMO.

*Coordination: written only in `skew_research/session_cowork/`. Phase 1 only. Nothing frozen/merged. `phase1c_engine.py` reproduces.*
