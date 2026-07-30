# PRE-REG H1 — Diversified TSMOM / managed-futures core engine

**Frozen 2026-07-16 before any result.** Growth gate (RESEARCH_PLAN §3). Primary engine candidate.

## Signal (frozen)
- Universe (~19 futures, continuous front-month + roll-clean cross-check on deep_history where available):
  equity ES/NQ/RTY/YM · bonds ZN/ZB/ZF · energy CL/NG · metals GC/SI/HG · grains ZC/ZW/ZS · FX 6E/6J/6A/6B.
- Per instrument: **multi-lookback TSMOM** = mean of sign(total return over {21, 63, 126, 252} trading days),
  giving a signal in [-1,+1]. **Lagged 1 day** (position at t uses data through t-1). LONG-SHORT (no clip).
- **Vol-scaling**: position_i = signal_i × (target_vol / realized_vol_i), realized_vol = 60d std ×√252,
  lagged. Equal-risk across instruments; portfolio = mean of positions. Monthly rebalance.
- Cost: futures ~1.5 bps per instrument per rebalance (commission+slippage, micro). Applied on turnover.
- NO parameter tuning beyond the frozen {21,63,126,252} set and 60d vol window.

## Growth-gate tests (frozen kill-rules)
1. **Geometric growth > 0 at half-Kelly**, net of cost. (Growth = objective; report full frontier.)
2. **Skew ≥ 0** on the daily strategy return distribution. (Trend expected positive-skew; if negative → fail.)
3. **DSR** (Bailey-LdP) at honest N; **walk-forward OOS ≥5 folds** (expanding); report OOS growth/SR.
4. **Two-sided**: decompose long-leg-only vs short-leg-only P&L — BOTH must contribute (short leg is the
   ruin-hedge / crash-alpha). If short leg ≤ 0 → it is leveraged-long beta → FAIL as core engine.
5. **MC ruin**: block-bootstrap (Politis-Romano) + trade-based generator → P(account < 20% of start) over
   6mo & 1yr at ¼/½/full Kelly. Promote the sizing that MAXIMIZES growth s.t. **P(ruin 1yr) < 25%**.
6. **€12k micro-deployability**: confirm 1 micro ≤ ~1 vol-unit; report which legs need full-size (blocker).

## Kelly sizing (frozen)
Full-Kelly leverage L* = SR/σ (targets portfolio vol = SR). Growth at fraction f: g = f(2−f)·SR²/2.
Size at **half-Kelly of the DEFLATED SR** (OOS/DSR-shrunk, not in-sample). Report frontier + ruin at each f.

## Success for H1
A promoted engine = positive-skew, two-sided, DSR-surviving TSMOM with a growth-vs-ruin frontier showing
max half-Kelly growth at P(ruin 1yr) < 25%, deployable at €12k on micros. Realistic prior: SR 0.6–0.9 →
half-Kelly growth ~15–40%/yr. Report honestly; do not inflate.
