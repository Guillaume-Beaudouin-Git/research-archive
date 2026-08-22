# Container evaluation — the survivors book under non-symmetric prop-firm geometries

**Date:** 2026-06-08 · **Question:** does a *container change alone* (no new strategy/signal/parameter) make the sub-threshold-on-FTMO-Standard book financiable? · **Method:** the EXISTING combined book (`research/ftmo_survivors_book/results/final_book_daily.csv`, RH + swap-net TSMOM, vol-targeted, equal-weight) re-run through the audit's monotone first-passage engine under each verified geometry; only the barrier (P1 target) + weekend legality change. Leverage fixed ex-ante on IS (L*=2.0 every geometry). 90% CIs from outer block-bootstrap of the data series. Code `container_eval.py`; data `results/container_eval.json`.

## VERDICT: **A container change alone does NOT clear the bar. Best case (FundedNext 8% target + legal weekend holds) = OOS p(pass) 0.371 — ~13 pts short of 0.50, CI [0.10, 0.75] does not clear it.** All three geometries are NO-GO. But the container choice is *not* irrelevant: it moves p(pass) a real +4 pts and decides legality.

## 1. p(pass) ± 90% CI per geometry (existing weekend-holding book, L*=2.0 on IS)

| geometry (verified vs scan) | P1/P2 | weekend | deployable as-is | OOS 6mo [CI] | OOS 12mo [CI] | IS 12mo [CI] | OOS CI clears 0.50? |
|---|---|---|---|--:|--:|--:|:--:|
| **FTMO Standard** | 10/5 | ✗ prohibited | **No** (book holds wknds) | 0.234 [0.06, 0.57] | 0.329 [0.08, 0.71] | 0.304 [0.24, 0.39] | **No** |
| **FTMO Swing** | 10/5 | ✓ allowed | **Yes** | 0.234 [0.06, 0.57] | 0.329 [0.08, 0.71] | 0.304 [0.24, 0.39] | **No** |
| **FundedNext Stellar 2-Step** | **8**/5 | ✓ allowed | **Yes** | **0.282** [0.08, 0.62] | **0.371** [0.10, 0.75] | **0.344** [0.26, 0.43] | **No** |

p(pass) is monotone in horizon everywhere (FundedNext OOS 3/6/9/12mo = 0.118/0.250/0.310/0.331 ✓). L-sweep flat across L∈[1.5,3.5] (FundedNext OOS-12mo 0.305–0.331) — no leverage rescues it; headline uses the IS-fixed L*=2.0.

**Reading it:**
- **The 8% target (FundedNext) is the single barrier-math lever** and it works *in the right direction*: OOS 12mo 0.329 → **0.371** (+4.2 pts), IS 12mo 0.304 → 0.344 (+4.0 pts, tight CI). Asymmetric-favorable target (8% < 10% floor) genuinely helps lumpy momentum — just not enough.
- **FTMO Swing = FTMO Standard barrier** (both 10/5) → identical p(pass) (0.329). Swing's value is **legality**, not math: it makes the weekend-holding book *deployable*. **The program's prior "FTMO NO-GO ~0.33" was effectively the *Swing* number all along** (the book always held weekends); FTMO Standard cannot run this book as-is.
- **It is not just short-OOS noise.** The IS p(pass) (full-sample, *tight* CI: FundedNext 0.344 [0.26, 0.43]) is also ~0.30–0.34 and its upper bound is < 0.44. The book is **structurally ~0.33 p(pass)** because its full-sample Sharpe is ~0.30; the geometry shifts that ~+0.04, not across 0.50. **The binding constraint is the thin Sharpe, not the barrier.**

## 2. Weekend-holding re-cost (does the weekend unlock help TSMOM?)
Replication of the survivors TSMOM construction matches the book's series **corr = 1.000** (faithful). Weekend-HOLD vs weekend-FLAT (zero Monday holds, swap×1.0, +re-entry; *conservatively over-penalized* — misses all Monday, not just the Fri→Mon-open gap):

| TSMOM (no-crypto, swap-net) | full Sharpe | OOS Sharpe |
|---|--:|--:|
| weekend **HOLD** (the book, verbatim) | **+0.025** | **+0.945** |
| weekend **FLAT** (Standard-compliant) | −0.078 | +0.270 |
| Δ (hold − flat) | **+0.103** | +0.675 |

**Weekend holding HELPS the trend book** (+0.10 full Sharpe, conservatively bounded) — the captured Monday trend-continuation outweighs the extra ×1.45 weekend swap. So legal-weekend geometries (Swing, FundedNext) are genuinely *better containers* than FTMO Standard, which would force a weekend-flat book that is **net-negative full-sample (−0.078)**. (Caveat: RH's weekend dependence is an uncosted residual — RH is a fixed deployable series I cannot re-execute weekend-flat; the TSMOM-sleeve effect is the measurable part.)

## 3. Per-geometry GO / NO-GO
- **FTMO Standard — NO-GO / not deployable.** Book holds weekends (illegal here); the compliant weekend-flat version is *worse* (TSMOM full Sharpe −0.078). Do not use Standard for this book.
- **FTMO Swing — NO-GO, but the deployable FTMO path.** Legal weekend holds; p(pass) OOS 12mo 0.329 [0.08, 0.71]. Reputable, fee refunded on pass — but sub-0.50.
- **FundedNext Stellar 2-Step — NO-GO, but the *best* geometry.** 8% target + legal holds → 0.371 [0.10, 0.75], the closest to the line; clean payouts (24h), fee refunded on pass. Still ~13 pts short. (Daily-loss balance-vs-equity granularity is **[UNVERIFIED]** in the scan — balance-based would be *kinder*, so this p(pass) is, if anything, conservative.)

## 4. EV ranking (directional — fee tables are [UNVERIFIED] in the scan)
EV ≈ p(pass) × payout − fee × E[attempts]. With both firms **refunding the fee on first payout** and p < 0.5, the cost driver is fee × E[*failed* attempts before a pass] ≈ fee × (1/p − 1): FundedNext ≈ 1.7 failed attempts (p 0.371), FTMO Swing ≈ 2.0 (p 0.329). Both ~80→90-95% split, both clean payouts.

| rank | geometry | OOS 12mo p(pass) | E[failed attempts] | payout reliability | EV read |
|---|---|--:|--:|---|---|
| 1 | **FundedNext Stellar 2-Step** | 0.371 | ~1.7 | clean (24h) | **least-bad**: highest p(pass), asymmetric target, fee-refund |
| 2 | FTMO Swing | 0.329 | ~2.0 | top-tier | deployable FTMO path; lower p(pass), pay ~2× fee in expectation |
| — | FTMO Standard | n/a | — | top-tier | not deployable (weekend-flat book net-negative) |

**Fees are [UNVERIFIED]** (scan §5 — behind JS/checkout), so absolute EV is not computable here; the *ranking* is robust (driven by the computed p(pass) + verified refund/split/reliability). **No geometry is a +EV layup** — with p ≈ 0.33–0.37 you fund roughly one account per ~3 paid attempts; EV is positive only if the funded account's realized payout (account × split × months-survived) exceeds ~3× the fee, which a ~0.30-live-Sharpe book makes marginal.

## 5. Bottom line
The container is the **right lever to pull and it pulled in the right direction** — FundedNext's 8% asymmetric target + legal weekend holds lift the book from a non-deployable 0.329 to a deployable, best-available **0.371 at zero new research** — but it **does not cross 0.50**. The wall is the **~0.30 book Sharpe**, which the prior swap analysis showed is gated by overnight financing (TSMOM swap-free +1.11 → swap-net ~0). **Consistent with `research/PROGRAM_DECISION_MEMO.md`:** the container is a real +4-pt free improvement and FundedNext-Swing-class is the correct home *if* the Sharpe rises; the remaining decisive lever is **measuring/reducing the real CFD swap** (and the [UNVERIFIED] FundedNext daily-loss granularity — balance-based would help), not the barrier. Recommendation: **do not fund yet**; if pursuing, **FundedNext Stellar 2-Step** is the least-hostile container, and the next action is the demo swap measurement, not another container.

*Reused verbatim: monotone first-passage engine, survivors book series + TSMOM construction (replication corr 1.000), measured per-leg swap. Geometry params verified vs `research/propfirm_scan/PROPFIRM_SCAN.md`; [UNVERIFIED] items flagged. CIs on every p(pass); leverage fixed ex-ante on IS. READ-ONLY except `research/container_eval/`. Design-stage MC on bootstrap history — not realised performance; paper-trade before funding.*
