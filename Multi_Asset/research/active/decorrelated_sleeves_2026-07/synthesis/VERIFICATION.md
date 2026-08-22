# VERIFICATION — independent recompute (author ≠ auditor)

**Date:** 2026-07-08 · **Method:** a from-scratch script (`verify.py`) that recomputes the three decisive
claims **directly from the cached pickles**, importing **none** of the piste engines or `lib/`. Purpose:
catch look-ahead, sign, or cost bugs by reproducing the verdicts on an independent code path.

## Result: all three decisive claims CONFIRMED (two strengthened).

| Claim | Independent recompute | vs main study | Verdict |
|---|---|---|:--:|
| **A — US500/US30 not OOS-coint; profit is directional drift** | OOS EG ADF p = **0.824**; per-year coint **2/14 (0.14)**; long-spread +53 bps / win 37 % vs **short-spread −63 bps / win 33 %** | p matches exactly; leg asymmetry reproduced (short leg *outright negative* under the auditor's simpler exit) | **CONFIRM (stronger)** |
| **B — fading overbought indices fails** | event study, fwd-5d after RSI2>90: US100 **+18 bps (t 2.65)**, US500 **+10 (t 2.02)**, US30 **+11 (t 2.01)**, GER40 +6 (t 0.82); all < unconditional but **positive** → a short loses | independent of the backtest state machine; same beta-trap conclusion | **CONFIRM** |
| **C — range-fade is look-ahead** | EURUSD hourly, fixed 8-bar hold: **causal (ADX<25 trailing) −0.11 bps/trade, Sharpe −0.08** vs **oracle (next-8-bar vol low) +0.98 bps/trade, Sharpe +1.78** | different params, same causal≈0 / oracle≫0 signature | **CONFIRM** |

## Notes
- **Claim A nuance (honest):** the main backtest reported the short-spread leg as marginally *positive*
  (+148 bps, 53 % win) under its z_out=0.5 + hard-stop + 1-bar-delay execution; the auditor's cruder
  exit (|z|<0.5 only) makes the short-spread leg *negative* (−63 bps). Both agree the signal is
  **directional** (long-spread pays, short-spread does not) — the substantive beta-trap claim is robust
  to execution; only the borderline sign of the weak short leg moves. This does not change the verdict
  (the pair fails the OOS-cointegration gate regardless).
- **Claim B nuance:** forward returns after overbought are *below* unconditional (mild reversion exists
  **relative to drift**) but remain **absolutely positive** — precisely why the short leg loses: the
  "reversion" never overcomes the index up-drift. This is the exact mechanism named in the Piste C verdict.
- No sign error, look-ahead, or cost mistake was found on the independent path. The three FALSIFIED
  verdicts stand.
