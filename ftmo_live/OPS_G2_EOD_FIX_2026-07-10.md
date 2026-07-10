# P0-1 / G2 — EOD 22:58 snapshot fix (prepared for review, NOT deployed)

**Date:** 2026-07-10 · **Scope:** `mt5/book_executor.mq5` only (logic; no spec change).
**Status:** patch written on branch, **not compiled, not deployed** to the live terminal.

## Problem (G2, from the ops/risk sweep)
Every trading day the reconcile logs `snapshot EOD 22:58 absent (gel de clôture ~22:54,
Do2258EOD non atteint)` → the primary same-day reconcile path is degraded and
`m5_today.json` is missing (it is written **only** inside `Do2258EOD`).

## Root cause (confirmed in code)
All schedule gates in `OnTimer()` compare against `ParisHM()`, and
`ParisNow()` (line 129) is derived from **`TimeCurrent()` = the last known *tick* time**:
```
datetime ParisNow() { return (datetime)(TimeCurrent() - InpServerTZOffsetMin*60); }
```
When the instruments go quiet at the ~22:54 close, `TimeCurrent()` **freezes at 22:54**, so
`ParisHM()` never advances to 2258 and `Do2258EOD()` never fires. Every earlier action
(2130/2145/2200/2205) fires because ticks still flow before the close — only the post-close
EOD is stranded. This is why `m5_today.json` is absent and the same-day STOP gate is blind.

## Fix (minimal, low blast radius)
Add a wall-clock time source — `TimeTradeServer()` advances by the server clock **without
ticks** — and use it **only** for the 22:58 EOD gate, OR'd with the existing tick condition:
```mql5
// helper (next to ParisHM)
int ParisHMWall(){ MqlDateTime p; TimeToStruct((datetime)(TimeTradeServer()-InpServerTZOffsetMin*60), p); return p.hour*100 + p.min; }

// OnTimer, 2258 gate
if((hm>=2258 || ParisHMWall()>=2258) && !g_done_2258) { g_done_2258=true; Do2258EOD(); SaveState(); }
```
- **Active-day behaviour unchanged**: on a normal day `hm>=2258` still fires it; the wall
  clause only adds a fallback for quiet closes.
- `g_done_2258` (persisted in `state.json`, restored on init line 1429) still prevents a
  double-fire, so an EA restart is safe.
- `Do2258EOD()` internals use `CopyRates(..., TimeCurrent(), r)` → captures the full session
  (last tick = 22:54 = session end), so `m5_today.json` is complete.
- **Only the EOD gate changes.** The other gates stay tick-based on purpose (they must align
  with real market activity).

## Why it is safe to deploy
- **No spec change**: `spec_v22.mqh` / the yaml / `spec_v22.sha256` are untouched → the EA's
  spec-refusal guard (ancre #20) will NOT trip; **no `spec_v22.sha256` re-deposit needed**.
- Pure executor-logic change; invariants (daily 5% floor, breaker, margin cap) untouched.
- `TimeTradeServer()-offset` mirrors the existing `ParisNow()` formula exactly (same offset
  convention), so the Paris conversion is consistent.

## What this does NOT fix
G1 (the reconcile STOP gate is advisory-only and was ridden through the breach) — separate
item, still open. This fix only restores the daily EOD snapshot so the gate has clean input.

## Deploy procedure (human — live-account sensitive)
1. Recompile `mt5/book_executor.mq5` in MetaEditor → new `book_executor.ex5`
   (the committed `.ex5` is now **stale** vs `.mq5` until recompiled).
2. **No** `spec_v22.sha256` re-deposit (spec unchanged).
3. Copy the new `.ex5` to the live terminal and reattach/restart the EA **in a quiet window**
   (e.g. after 23:05 Paris once the day's actions are done, or before 09:00) to avoid a
   mid-session restart. On init the EA restores `g_done_*` from `state.json`.
4. **Verify next EOD**: the reconcile log should show NO "DÉGRADÉ", `m5_today.json` present,
   and `gate STOP évalué` (not "non évalué"). Confirm `reconcile_log.csv` residual within tol.
5. Rollback: redeploy the previous `.ex5`.

**Test caveat:** MQL5 is not unit-testable locally here; validate on the next live EOD (or a
demo terminal first if one is available). The change is 2 lines + 1 helper, tick-safe by
construction.

---
*Prepared 2026-07-10. Patch on branch `claude/ftmo-g2-eod-fix`; live terminal unchanged.*
