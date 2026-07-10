# P0-2 / G1 — Hand-reconciliation of the 07-06/07 STOP fires + gate policy

**Date:** 2026-07-10 · Read-only analysis. No live action. Gate is **GREEN now**
(`consec_unexplained=0` since 07-08), so nothing is urgent tonight — this resolves whether
the 07-06/07 `stop_recommended` fires were real drift, and what to do about the gate.

## Verdict: the 07-06/07 consec=5,6 fires were ARTIFACTS, not real drift

**How the gate works** (`reconcile.py`): `residual = d_total − (d_cost + d_timing + d_micro)`,
`unexplained = |residual| > tol`; `d_signal` (EA-vs-model target mismatch) is REPORTED but
**deliberately excluded** from the residual ("a real divergence must stay unexplained to
trigger the gate"). 3 consecutive unexplained days → `stop_recommended`.

**2026-07-06 — J1-suspension transition artifact.**
- `pnl_real +480.44` vs `pnl_model −73.34`; `residual 502.90` (tol 13.41); **`d_signal $83,861`**.
- Brain: `w_jpy` **+1.5000 (07-03) → +0.0000 (07-06)** — the J1 gate suspended USDJPY. The
  account **carried the JPY leg over the weekend** and flattened it Monday 07-06; the model
  had already zeroed JPY. The +$480 real is that JPY position's transition-day P&L; the model
  (flat) couldn't attribute it → residual. The **$83,861 `d_signal`** is the full JPY-notional
  mismatch between the EA's carried/flattening position and the model's flat target.
- Also a **DÉGRADÉ (G2)** day → the model replay was late/fragile, inflating the residual.
- → one-time position-state mismatch on a gate-transition day, **not** execution drift or edge decay.

**2026-07-07 — marginal noise.**
- `pnl_real −354.14` vs `pnl_model −378.11`; **`d_signal 0.0`** (positions now reconciled);
  `residual 24.82` vs tol 17.58 → unexplained by only **$7.24**. Real & model agree within $24
  on the index legs. Also a DÉGRADÉ (pre-swap fallback) day. → noise, not drift.

**2026-07-08 — `consec` self-reset to 0** on the first clean day → confirms no persistent problem.

**Counter accumulation caveat.** The streak spanned *two different* turbulent episodes without
an anchor-boundary reset: `06-30(2) → 07-01(3) → 07-02(4 = account #2 BREACH day) → 07-03
(degraded, held 4) → 07-06(5 = #3 J1 transition) → 07-07(6) → 07-08(0)`. "6 consecutive
unexplained days" here is really *breach-#2 turbulence* + *attempt-#3 startup transition*
stitched together — not 6 days of the same drift. That is a gate-design weakness (below).

## G1 policy recommendation

**1. Do NOT auto-FLAT on the current gate.** Both recent fires were **false positives**
(J1 transition + degraded path). An auto-FLAT policy on today's logic would have needlessly
flattened a healthy book at the worst time. Enforcement must wait until the gate is specific.

**2. Harden the gate FIRST (after G2 deploys and cleans the input).** G2 removes the degraded
days that inflate residuals; then:
- **(a) Reset `consec_unexplained` at the attempt/anchor boundary.** A new `attempt_start` /
  fresh anchor must zero the counter — a prior attempt's breach turbulence must not bleed into
  the next attempt. (Would have prevented the 5/6 accumulation entirely.)
- **(b) Don't count a DÉGRADÉ day toward `consec`.** When the model can't be replayed cleanly,
  the residual is not trustworthy — treat as "no information" (preserve, don't extend). G2
  makes these rare, but guard anyway.
- **(c) Separate the two failure modes.** `d_signal` (position conformance) and `residual`
  (unexplained P&L at matched positions) are different problems. A **sustained** `d_signal`
  (EA persistently NOT holding the model's targets, ≥2 clean days) is the more important STOP
  signal (execution/config broken); a **one-day transition `d_signal`** must not gate. Only
  `residual` unexplained **with `d_signal≈0`** (matched positions, mystery P&L) is a true
  model/edge STOP. Gate on the right one.

**3. Then escalate enforcement gradually:** advisory (today) → **manual-ACK** (a
`stop_recommended` must be acknowledged via Telegram within N hours, else the supervisor
sends `FLAT`) → consider **auto-FLAT** only once the post-hardening false-positive rate is
demonstrably ≈ 0 over a clean window.

## Immediate state / tonight
- Gate GREEN (`consec=0`), account #3 alive (−3.6%, floors intact). **No live action needed for G1 tonight.**
- Sequencing: deploy **G2** first (tonight) → it eliminates the degraded-path days that were
  half the false-positive source. Re-evaluate G1 hardening on clean input afterward; I can then
  prepare the `reconcile.py` patch for (a)/(b)/(c) — a Python cron change (not the live EA),
  for review.

---
*Read-only, 2026-07-10. Conclusion: 07-06/07 STOP fires = J1-transition + degraded-path
artifacts, NOT drift; gate currently green. Recommend harden-then-escalate, not auto-FLAT.
Nothing changed on the live account.*
