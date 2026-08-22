# FTMO Candidate Funnel — FULL LONGLIST with honest kill reasons

Two parts: **(A) 66 configs actually backtested** (this IS the DSR deflation count N=66), grouped by mechanism family; **(B) 16 pre-excluded dead families** (registry-cited, not re-tested). Total = 82 distinct mechanism entries spanning daily & intraday mean-reversion, breakout/momentum, cross-sectional, seasonality/calendar, volatility/regime, event-conditioned, and relative-value. Breadth ≥ the 50 requested.

Columns: `IS`/`OOS` = annualised daily Sharpe in-sample (pre-2025) / out-of-sample (2025-01→2026-06); `exk` = OOS excess kurtosis; `DSRp` = DSR on OOS, deflated at N=66 with the primary (OOS-consistent) σ_SR=0.73; bar = **0.50**. Full numbers: `results/all_trials.csv`.

---

## A. BACKTESTED (N = 66) — every one fails DSR>0.5 on OOS

### A1 · Daily mean-reversion, z-score(k) fade — FX (13 variants)
| config | IS | OOS | exk | DSRp | one-line kill |
|---|--:|--:|--:|--:|---|
| zfadeFX.k5 / k10 / k20 (inv-vol sleeves) | −0.68/−0.41/−0.27 | +0.02/+0.73/+0.80 | 5–7 | ≤0.02 | **IS negative across all k** → no persistent FX-MR edge; OOS positive is noise |
| zfade10.AUDUSD | −0.13 | +1.47 | 40.0 | 0.21 | negative IS + **exkurt 40** → OOS-luck, not FTMO-suited (fat left tail) |
| zfade10.USDJPY | −0.08 | +1.43 | 9.1 | 0.21 | negative IS → OOS-luck; best-case lenient DSR 0.62 still < real bar |
| zfade10.EURJPY | −0.22 | +1.28 | 2.4 | 0.12 | negative IS; OOS strength not reproduced in-sample |
| zfade10.GBPUSD / NZDUSD / USDCHF / AUDJPY | −0.10/−0.48/−0.33/−0.44 | +0.58/+0.73/+0.16/+0.14 | 4–30 | ≤0.05 | negative IS, low/zero OOS DSR |
| zfade10.EURUSD / EURGBP / USDCAD | −0.10/−0.10/+0.04 | −0.04/−0.56/−0.36 | 6–7 | ≤0.004 | negative both samples |

### A2 · z-score fade — indices (5)
| zfade.US30 | −0.22 | +0.73 | 42.5 | 0.069 | OOS-luck, exkurt 42 |
| zfade.US500/US100/GER40 + IDX sleeve | +0.25/+0.18/−0.36/+0.02 | −0.02/−0.17/−0.24/+0.05 | 33–65 | ≤0.013 | no edge; extreme kurtosis (fade run over on trend days) |

### A3 · RSI(2) Connors reversion — indices + crypto (5)
| rsi2.GER40 | −0.12 | +0.86 | 58.2 | 0.092 | OOS-luck, exkurt 58 |
| rsi2.US500/US100/US30 + IDX sleeve | +0.52/+0.27/+0.05/+0.07 | +0.06/−0.57/+0.13/+0.17 | 19–60 | ≤0.016 | IS↘OOS decay; US500 IS 0.52 → OOS 0.06 |

### A4 · MR on XAU / BTC (4)
| rsi2.XAU / rsi2.BTC | −0.09/+0.05 | +0.66/+0.27 | 44/20 | ≤0.06 | weak/no edge, high kurtosis |
| zfade.XAU / zfade.BTC | −0.36/−1.04 | −0.67/−0.22 | 13/16 | ≤0.007 | negative both samples |

### A5 · Overnight gap-fade (open→close) — indices + XAU (6)
| gapfade.US500 / US30 / GER40 / US100 / IDX sleeve | −0.5 to −0.9 | +0.07 to +0.48 | 15–31 | ≤0.044 | **deeply negative IS** (gap continuation, not fade); MaxDD >100% — edge inverted post-2015 (L23 microstructure) |
| gapfade.XAU | +0.42 | +0.07 | 6.6 | 0.017 | IS-only; collapses OOS |

### B1–B4 · Trend / momentum / breakout (9)
| B1.tsmom.k200 (basket, vol-tgt, 2-sided) | +0.40 | +1.80 | 1.8 | **0.447** | **best near-miss**; lumpy momentum (L24), full-exk 12, lost −17% in 2022, OOS = 2024-25 trend regime |
| B1.tsmom.k100 / k50 | +0.29/+0.39 | +1.17/+0.66 | 1.2/11.9 | 0.18/0.07 | same family, weaker; k50 lumpy (exk 12) |
| B2.tsmom100.XAUUSD | +0.12 | +1.62 | 5.9 | 0.408 | single-asset, OOS = gold 2025; IS Sharpe ≈ 0 |
| B2.tsmom100.US100 / BTCUSD | +0.41/+0.73 | +0.08/−0.16 | 17/3.5 | ≤0.017 | IS-only; no OOS persistence |
| B3.donchIDX / donchFX (Donchian-20 breakout) | −0.22/−0.19 | +0.21/−0.83 | 30/1.5 | ≤0.023 | breakout lumpy/negative; cost-eroded |
| B4.maLongIDX (long-only MA200) | +0.68 | +0.82 | 1.4 | 0.092 | **pure equity beta** (registry-dead class); p_funded high only because indices rose |

### C · Cross-sectional FX (2)
| C1.xsRevFX (1-day reversal, mkt-neutral) | −0.92 | −0.61 | 1.5 | 0.002 | negative both samples; cost-killed |
| C2.xsMomFX (60-day momentum) | −0.03 | +0.11 | 3.7 | 0.020 | no edge — confirms registry "FX X-sec momentum dead post-Menkhoff" |

### D · Seasonality / calendar (8)
| D1.tom.* (turn-of-month, idx + XAU, 6 variants) | −0.34 to +0.33 | +0.19 to +0.60 | 11–55 | ≤0.065 | weak, inconsistent; XAU best (DSR 0.065) but exkurt 54 |
| D2.sixmonthIDX (Nov–Apr long) | +0.54 | +0.22 | 35.7 | 0.022 | IS-only seasonal; decays OOS; long-only beta flavour |
| D3.dowIDX (long Tue − short Mon) | −0.43 | −1.81 | 8.9 | 0.000 | day-of-week effect absent/inverted |

### E · Event-conditioned, calendar 2018+ (8)
| E1.preFOMC.* (long idx day before FOMC, 4 idx + sleeve + 2d + EUR) | mixed | **−0.4 to −1.7** | 31–113 | ≈0.000 | **pre-FOMC drift REVERSED on 2025-26 OOS** — registry's "alive" lead does NOT replicate; sparse (8/yr) → exkurt 60–110 |
| E1.preFOMC_XAU | −0.36 | +1.02 | 112.6 | 0.050 | OOS-luck on 12 events; exkurt 113 — uncertifiable |
| E2.preNFP_IDX | −0.18 | −0.98 | 108 | 0.000 | negative; sparse |
| E3.preCPI_IDX | +0.21 | +0.85 | 294 | 0.024 | OOS-positive but exkurt 294 (≈10 events) → statistically meaningless |
| E4.postFOMC_IDX / E5.preECB_GER | −0.18/+0.01 | +0.02/−0.33 | 171/71 | ≤0.001 | no drift; sparse |

### F · Volatility / regime (2)
| F1.lowvolLong_IDX (long idx when calm) | +0.49 | +1.08 | 5.2 | 0.130 | **most FTMO-shaped** (13/15 yrs+, all 2020-26 yrs+, maxDD 18%) but DSR 0.13 and **beta-tinged** |
| F2.volBreakout_IDX (trend when stormy) | −0.11 | −0.20 | 15.1 | 0.004 | negative; regime filter doesn't rescue trend |

---

## B. PRE-EXCLUDED dead families (registry-cited — NOT re-tested, not in N)

Skipped to avoid re-deriving known negatives (CLAUDE.md "Research history" + `data/ftmo_research/` verdicts + memory). One-line kill each:

1. **G10 FX carry** — dead post-GFC; 2005-07 artefact, IC −0.028 on 2013-23 (FX-1→FX-4, G1).
2. **FX TSMOM / cross-sectional momentum** — dead post-Menkhoff (central-bank anchoring). *(C2 above re-confirms.)*
3. **Index ORB / opening-range breakout** — cost-killed; mean_R flips negative at 2-3 bps; placebo (Gaussian+floor) reproduces the "edge" (ORB real-constraints 2026-06; `_CANONICAL_STATE.md`).
4. **VWAP intraday mean-reversion / auction-scalp** — regulatory-window kill (L23: BIS WMR 2015, MiFID II 2018); HFT-mediated edge not retail-tradable (L23b).
5. **FX fix / WMR W-shape (Strategy E)** — 1-4 bp gross < 6-7 bp retail RT post-2015 reform (`strategy_e_fix_flow/POSTMORTEM`).
6. **Fix-reversal EURUSD (Krohn/Ranaldo)** — NO-GO; gross 0.22 bps vs cost 2.23 bps p95 (fix_reversal kill 2026-06).
7. **FX/equity pairs & cointegration** — 0/19 qualify; AUDNZD/EURGBP retracted; Gatev Sharpe −0.44 (`STATARB_VERDICT`).
8. **Index pairs ES/NQ (US500–US100 ratio)** — tech-premium drift destroys stationarity (EG p=0.28).
9. **VRP / options selling (SPX & BTC)** — unit error (L13); BTC gross 4.4%/yr < costs 8.9%/yr; no options on FTMO anyway.
10. **On-chain crypto (MVRV, netflow, funding)** — HAC deflation (L12b: t 2.58→0.11); momentum proxies (L17/L18).
11. **Crypto intraday MR / grid** — no gross edge; 12 bps crypto RT kills it (ftmo_alpha_program Family-4).
12. **Commodity carry / TSMOM-on-ETF** — roll-drag contamination (L5); dynamic basis Sharpe −1.15.
13. **PEAD (compliant long-only)** — needs market-neutral hedge (FTMO forbids); long-only β → maxDD −41/−59% breaches floor.
14. **Overnight equity premium (gated)** — real gross but swap eats it at 5% rates (≈−3 bps/night); personal-book SR 0.68 < beta-proxy gate (L36).
15. **Weekly two-sided crypto TSMOM on FTMO** — CLOSED; 3-axis kill at swap=0 counterfactual (crypto_cfd_ftmo_kill 2026-06).
16. **Round-number cascade FX** — all IC horizons FAIL (n=180).

---

### Reconciliation note
The funnel **re-tested** four "alive/promising" registry leads under this rig and they did **not** survive on the 2025-26 OOS: pre-FOMC drift (E1, **reversed** to OOS −1.14), turn-of-month (D1, weak), multi-asset TSMOM (B1, near-miss only), and gold/trend (B2, OOS-regime-inflated). This is a stricter, untouched-OOS re-test than the original IS-heavy studies — and it tightens, not contradicts, the registry.
