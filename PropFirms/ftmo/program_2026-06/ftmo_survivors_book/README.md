# FTMO survivors book — honest baseline

Built only from independently-validated inputs (Ross Hook deployable + TSMOM), reusing the audit's
monotone first-passage engine (`research/ftmo_portfolio_audit/code/firstpassage.py`, read-only).
Never the discredited author engine. READ-ONLY on source data + audit deliverables.

- **`REPORT.md`** — findings + the plain verdict (start here).
- **`figures/survivors_ppass.png`** — leverage sweep + p(pass) ±90% CI.
- **`results/ppass_table.csv`** — {6mo,12mo}×{IS,OOS} p(pass) with 90% CIs, all books.
- **`results/book_results.json`** — full machine-readable results.
- **`results/tsmom_*.csv`** — TSMOM regenerated swap-free vs swap-net variants.

### code/ (run with `/usr/bin/python3`, cwd = `code/`)
| file | purpose |
|---|---|
| `tsmom_regen.py` | regen TSMOM net of REAL per-night swap (validates swap-free vs chosen_returns, corr 1.000) |
| `book.py` | sleeve re-verify + vol-target + combine + IS-fixed leverage + p(pass) w/ outer-bootstrap CI + tail-corr + DSR |
| `finalize_book.py` | p(pass) table + figure |

### Verdict
HONEST 2-sleeve book (RH + swap-net TSMOM; Sleeve C failed inclusion), L=2.0 fixed on IS:
**OOS p(pass) = 0.24 (6mo) / 0.34 (12mo)** — neither clears 0.50. Real CFD swap consumes TSMOM's edge
(deployable Sharpe ~0.05 full / 0.92 OOS, not the swap-free 0.85). DSR ≈0.04-0.11 at honest N≥100.
**Free-price-data edge too thin to financiably clear 0.50. Do not fund.** A reproducible ~0.30 > an
unreproducible 0.55.
