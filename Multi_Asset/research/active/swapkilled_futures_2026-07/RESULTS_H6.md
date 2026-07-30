# RESULTS H6 — Month-end FX rebalancing flow — FALSIFIED

**Verdict: FALSIFIED (fails K1 + K3).** Tested on CLEAN data (deep_history_utc real broker FX,
2007-2026), after the yfinance-FX run was flagged data-confounded (repo lesson: yfinance daily FX
return-corr ≈ 0 vs real). Data sanity confirmed clean: EURUSD daily vol 0.52% (real ~0.5-0.6%).

| Version | SR | 2007-2014 | 2015-2026 |
|---|---|---|---|
| Conditional (Melvin-Prins) | **0.05** | 0.15 | **−0.03** |
| Unconditional month-end USD | −0.11 | — | — |

- Conditional sleeve SR 0.05 ≈ zero → fails K1 (<0.5). Post-2015 SR −0.03 → fails K3 (decayed).
- The hedge-flow conditioning adds essentially nothing (0.05 vs unconditional −0.11 — both ~0).
- (yfinance-FX run gave −0.28 but is discounted per the known data defect.)

**Note:** clean-data discipline mattered — yfinance would have given a falsely-strong negative. The verdict
is the same (no edge) but now trustworthy. Consistent with the repo's broad FX closure: retail-accessible
FX flow edges do not survive (L34/L43); month-end hedge flow is no exception on this sample.
