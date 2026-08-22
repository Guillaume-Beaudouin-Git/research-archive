# FTMO 10k 2-step — Candidate Funnel

Triage funnel: 50+ distinct FTMO-suited strategy mechanisms → causal real-cost backtest on
reused deep-history data → filter to survivors clearing **Deflated Sharpe > 0.5 on untouched
2025-26 OOS**, deflated at the **true trial count N**. Feeds fuller validation later; rigor lives
in honest DSR + real costs + untouched OOS, not in exhaustive per-candidate audits.

## Result in one line
**0 of 66 backtested candidates are DSR-certified** (DSR>0.5 on OOS at honest N=66, conservative
deflation). Per the brief, the certified shortlist is **empty** — output fewer, do not pad. The
best near-miss (multi-asset TSMOM-K200, DSR 0.45) is flagged for fuller validation, not for trading.

## Read in this order
1. **`SHORTLIST.md`** — the (empty) certified shortlist + a clearly-labelled conditional watchlist with the mutual-correlation & tail-correlation matrices and the ≤5 max-decorrelated picks.
2. **`LONGLIST.md`** — all 66 backtested configs (the honest N) + 16 pre-excluded dead families, one-line kill reason each.
3. **`LIMITATIONS.md`** — why 17mo×N=66 can't certify, the DSR N/σ sensitivity, cost & calendar assumptions, what's not testable.
4. **`STEP2_VALIDATION.md`** — powered follow-up (walk-forward ≥5 folds + full-history DSR + intraday-aware FTMO floors + F1 beta diagnostic + 2× cost). Upgrades the verdict from "uncertified" to **verified sub-threshold**: best lead (vol-targeted TSMOM basket) full-history Sharpe 0.70 < bar; F1 low-vol is sub-beta. Code `step2_validation.py`.

## Reused infrastructure (verbatim — never re-derived)
- `PropFirms/ftmo_alpha_program/engine/cfd_costs.py` — `CFDCostModel` (real spread × markup).
- `PropFirms/ftmo_alpha_program/engine/ftmo_first_passage.py` — `combined_pass_prob_empirical` (FTMO static-DD 2-step, p_funded colour).
- `dsr.py` (repo root) — `deflated_sharpe_ratio` (Bailey–López de Prado).
- `data/deep_history_utc/*_M1.csv` — true-UTC M1, 16 instruments (READ-ONLY); + `calendar/economic_calendar_2018_2026.csv`; + `data/panels/btc_full.csv`.

## Code (this folder, self-contained)
- `build_cache.py` — M1 → 22:00-UTC-anchored daily bars (+ spread floors). Output: `cache/*.parquet`.
- `funnel_lib.py` — cost layer, causal signal library, backtester, IS/OOS split, stats, DSR & p_funded wrappers.
- `run_funnel.py` — the 66-config roster, DSR at true N (3 deflations), survivor filter, decorrelation. Output: `results/`.

## Reproduce
```bash
PY="<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python"
"$PY" research/ftmo_candidate_funnel/build_cache.py     # ~80s (reads ~6GB M1, READ-ONLY)
"$PY" research/ftmo_candidate_funnel/run_funnel.py       # ~5s
```

## Artifacts (`results/`)
| file | contents |
|---|---|
| `all_trials.csv` / `.json` | all 66 configs: IS/OOS Sharpe, kurtosis, skew, per-year, 3×DSR, p_funded |
| `summary.json` | N, σ_SR, benchmark, certified=[], conditional list, chosen ≤5, artifacts nulled |
| `watchlist_corr.csv` / `watchlist_tailcorr.csv` | mutual + stress correlation matrices |
| `chosen_pfunded_sweep.json` | p_funded vs daily-vol sizing {0.6%,1.0%,1.5%} for the chosen set |

## Key parameters
- OOS hold-out: **2025-01-01 → 2026-06-05** (untouched). IS: instrument start → 2024-12-31.
- Cost: feed spread × **markup 3.0** + FTMO commission (FX 0.9 / idx 1.0 / XAU 1.3 / BTC 8.5 bps RT) + slippage; charged on turnover; **2× stress** available.
- DSR gate: **0.5**, deflated at **N=66**, periods/yr=252, primary σ_SR=0.73 (OOS-consistent).
- Causal: signal from data ≤ T-1 (price features `.shift(1)`-ed; calendar/event positions known in advance), trade T.
