# RESULTS — Piste A iteration: factor residual + gold/silver  (CORRECTED — win retracted)

**Run:** 2026-07-08, daily, net of active-fill 2-leg cost + asymmetric swap. Engines `run_A2.py`, `autopsy_A2.py`.
> **⚠ Correction 2026-07-08:** an earlier version reported the US500 factor-residual at Sharpe 1.13 (OOS
> 0.97), two-sided, challenge P(pass) 0.70–0.84. That was **entirely a financing sign bug** — the
> market-neutral book pays financing on **both legs** (~−1.9 bps/night), and the bug credited it as income.
> Independent recompute exposed it. See `../CORRECTION_2026-07-08.md`.

## Verdict: **BOTH angles FAIL.** The factor residual has no gross edge and dies on 2-leg financing.

### H2 — Avellaneda-Lee factor residual (long index / short basket)
Decisive independent check (fresh code, no engine reuse):
```
US500 residual:  GROSS Sharpe = 0.06   (no edge before cost)
                 NET  Sharpe = -1.09   (2-leg financing ~-1.9 bps/night kills it)
                 the +1.13 "win" = gross - fin (the bug), not gross + fin (correct)
```
| variant (corrected, net) | Sharpe | MaxDD | short-leg t |
|---|--:|--:|--:|
| US500 residual | **−1.17** | −43 % | −3.03 |
| US30 residual | −0.80 | −50 % | −2.38 |
| US100 / GER40 residual | −0.48 / −0.59 | −52 % / −60 % | −1.6 / −1.9 |
| residual PORTFOLIO | **−1.02** | −64 % | — |

The residual has **essentially zero gross edge** (0.06 Sharpe) — the 4-index complex is efficient enough
that idiosyncratic deviations do not reliably revert net of the tiny signal — and once the **two legs'
financing** is charged correctly, every variant is deeply negative. This *confirms* iteration-1 and the
repo's `statarb_deepdive_ftmo`: **market-neutral stat-arb on FTMO dies on multi-leg financing.** (Small-N
factor model — only a 3-instrument basket — also limits the Avellaneda-Lee approach vs its ~500-stock origin.)

### H1 — gold/silver ratio (DD-controlled): FAIL
Corrected net Sharpe **−0.61**, MaxDD **−82 %**. The spread drifts within the z-band over long holds
(financing accrues) and diverges in the tails; neither a z-stop nor vol-targeting rescues it.

## Note on the FTMO hedging rule (still useful even though the edge failed)
The market-neutral long/short-correlated construction *is* permitted within a single FTMO account (the ban
is on cross-account hedging / gaming the profit-distribution rule). So the *vehicle* is fine — it is the
*edge* (0.06 gross) and the *2-leg financing* that fail, not the rule.

## Conclusion
No Piste-A variant clears the bar. The failure is structural (no gross residual edge + 2-leg overnight
financing), consistent across iteration-1, iteration-2, and the repo. No audited-engine re-test warranted.
