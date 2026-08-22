# FTMO 3-sleeve portfolio — independent adversarial audit

Clean-room regeneration of `PropFirms/ftmo_decorrelated_portfolio/REPORT.md`. Does **not** import the
author's engine or trust cached series. READ-ONLY on source data.

- **`AUDIT_REPORT.md`** — full findings + per-gate verdicts (start here).
- **`figures/ppass_audit.png`** — p(pass) CDF (independent vs report) + leverage curve.
- **`results/ppass_sidebyside.csv`** — p(pass) table, report vs independent, with CIs.

### code/ (run with `/usr/bin/python3`, cwd = `code/`)
| file | purpose |
|---|---|
| `gate1_tz_check.py` | empirical timezone verification (Gate 1) |
| `audit_common.py` | shared loaders / RSI2 / metrics / vol-target |
| `sleeve_a.py`, `sleeve_a_variants.py` | Sleeve A regen + charitable sweep |
| `sleeve_bc.py`, `sleeve_bc_sweep.py` | Sleeves B/C regen + charitable sweep |
| `build_steelman.py` | best-reconstruction sleeves + combined |
| `firstpassage.py` | INDEPENDENT 2-phase first-passage MC (sequential monotone + author replication + CIs) |
| `gate0_run.py` | Gate 0 (MC reliability, monotonicity, headline) |
| `gate_BCG.py`, `gate_DEF.py` | Gates B,C,G and D,E,F |
| `finalize.py` | side-by-side table + figures |

### Headline
p(pass≤3mo) regenerates to **0.18–0.29** (correct) / ≤0.41 (author's optimistic method) even at the
report's *claimed* Sharpe 1.39 — not **0.549**. Honest 90% CI for ≤3mo lies **entirely below 0.50**.
All three sleeves fail to reproduce their claimed Sharpe at the stated spec. **VERDICT: NOT-CONFIRMED.**
