# FTMO Live Book — Ops / Risk Assessment (2026-07-10)

Read-only health sweep of the live deployment (VPS + MT5 + crons + reconcile + account
state). No live action taken. Account #3 is **alive and green on the hard limits**, but there
are two real governance gaps and a strategic tension worth your decision.

## Status snapshot
| Area | State | Note |
|---|:--:|---|
| **Account** | 🟠 AMBER | #3, phase P1, equity **$9,643.17 (−3.57%)**, anchor fresh (daily room $500), open_days **2/4** min, floors intact (daily 9143 / static 9000), `kill=0`, `breaker=0`. Weak spot: −3.6% *with the overnight engine gated off*. |
| **Infra (VPS/MT5/crons)** | 🟢 GREEN | `terminal64.exe` alive & connected (pid 2113903); both screens up; **0 pending security updates**; disk 56%, load 0.3, mem 1.4/3.8 GB; all FTMO crons present; watchdog self-healing correctly (frozen-heartbeat detected 07-07/08/09 but correctly NOT restarted — terminal alive). |
| **Signal engine** | 🟠 AMBER | Overnight USDJPY leg **flat since 07-06** (`w_jpy` +1.5 → 0), XAU already 0 → book is **intraday-only** (index on/off + micro-ORB). J1 gate suspending post-breach. Upside capped. |
| **Reconcile / risk gate** | 🔴 RED | (1) **STOP gate is advisory-only** and was ridden through `consec_unexplained` 3→4 on 07-01/02 (breach window) and 5→6 on 07-06/07 (`stop_recommended=1`). Now reset to 0/GREEN. (2) **EOD 22:58 snapshot fails EVERY day** → primary reconcile path degraded, Δ computed on a late fallback. |
| **Cost anchors** | 🟠 AMBER | `spec_bounds_breach=1`: broker swaps drifted more negative (XAUUSD −75.9 vs anchor −65.7; US100/GER40/USDJPY too). Benign while overnight is flat; haircuts EV if re-enabled. |

## The two governance gaps (detail)

**G1 — Reconcile STOP gate is detection-only, and was overridden through a breach.**
`reconcile.py` recommends STOP after 3 consecutive unexplained days (residual > tol) and
alerts Telegram — but **does not enforce** (no auto-FLAT). The ledger:
`06-30 consec2 · 07-01 consec3 STOP · 07-02 consec4 STOP (← account #2 breached) · 07-06
consec5 STOP · 07-07 consec6 STOP · 07-08 reset0 · 07-09 0`.
So the gate **correctly flagged trouble the day before and on the breach day**, and again
during the #3 restart — and each time it was ridden through. The 07-06 divergence
(residual $502.9 vs tol $13.4, `d_signal $83,861`) is almost certainly the **J1-suspension
transition + the degraded EOD path** (model expected a JPY position, live went flat), not
real edge decay — but that is exactly the ambiguity a working gate should resolve, not leave open.

**G2 — EOD 22:58 snapshot never fires → primary reconcile path degraded daily.**
Every day: *"snapshot EOD 22:58 absent (gel de clôture ~22:54, Do2258EOD non atteint) —
fallback sur état de clôture 22:54, pré-swap; gate STOP non évalué ce jour."* The book
freezes at ~22:54 (market close) but the EOD export is scheduled at 22:58 → it always
misses. A late "m5 tardif" Δ is computed afterward (that's what produced the consec counts
above), so it's not silent, but the **primary same-day STOP evaluation is blind every day**,
and the fallback's big residuals are partly a timing artifact — which muddies G1.

## Strategic tension (your call)
The overnight leg is the book's primary alpha (attribution: overnight ablation −10.6 pt).
It is **currently OFF** (J1 gate suspending USDJPY after the 07-02 breach). Account #3 is at
−3.6% and needs +10% — **intraday-only, that P(pass) is low**. The trade-off:
- **Ride gated-safe** → protected from the JPY tail that caused the breach, but the attempt
  likely bleeds out slowly / times out well short of +10%.
- **Re-enable overnight with tighter sizing** → restores the engine, but re-exposes the exact
  tail that breached #1/#2, and on **drifted (worse) swaps** (spec_bounds_breach).

## Prioritized actions (I did none — awaiting your go)
**P0 — safety**
1. **Fix G2**: move the EOD snapshot to ≤ 22:53 (before the 22:54 close-freeze) or diagnose why
   `Do2258EOD` doesn't fire. Until then the same-day reconcile gate is blind. *(I can prepare
   the EA/schedule change for review — not deploy.)*
2. **Resolve G1 policy**: decide whether `stop_recommended` stays advisory, requires a manual
   ACK within N hours, or auto-FLATs. At minimum, **confirm the 07-06/07 consec=6 was a
   J1-transition/degraded-path artifact, not real drift** (I can reconcile the two by hand).

**P1 — the attempt**
3. **J1 / overnight decision** (above): confirm the current USDJPY level vs the gate's
   155/160 band (auto-resume or stuck-off?), then choose ride-safe vs re-enable-tighter.
4. **Re-anchor cost specs** (`spec_bounds_breach`) before any overnight re-enable — the
   drifted swaps make overnight EV worse than the backtest assumed.

**P2 — hygiene**
5. Schedule a reboot window (84-day uptime; wine/MT5 refresh) — low urgency (0 security
   updates pending), pick a slot outside rebalances.
6. Fix the `supervisor.log` UnicodeDecodeError (non-utf8 byte in a log path).
7. Add a Telegram alert when **both** reconcile paths degrade (today the daily EOD
   degradation is only in the log).

---
*Read-only sweep 2026-07-10. Hard limits are green (kill=0, floors intact); the risks are
governance (advisory gate overridden + degraded reconcile path) and the strategic engine-off
trade-off, not an active emergency. Nothing changed on the live account.*
