# RESULTS — Piste B iteration: amplitude-filtered range fade

**Run:** 2026-07-08, hourly, intraday-flat, net of active-fill cost. Engine `run_B2.py`. Honest daily-basis Sharpe.

## Verdict: **NEAR-MISS — improved but does not clear 0.5.** No challenge-suitable candidate.

The new lever vs iteration-1: an **amplitude filter** (fade only when band width ≥ k× round-trip cost) +
a causal **vol-persistence** gate, on the higher-amplitude instruments (gold + indices).

| best cell | value |
|---|---|
| XAU, band 2.5σ, ADX<25 | **net Sharpe 0.46** (two-sided: long +1.20 / short +0.86 bps) |
| gross/cost ratio | **2.57** (< 3 → still fails the L33b cost gate) |
| MaxDD (unlevered) / worst day | −37.9 % / −3.65 % |
| cells with net Sharpe > 0.5 | **0 / 48** |

**Reading — honest:**
1. **Progress:** gold's range-fade is now genuinely **two-sided** (both legs positive) and net-positive
   (Sharpe 0.46), up from iteration-1's cost-dead / one-sided negative. The amplitude filter + gold's large
   intraday amplitude relative to its ~2.6 bps cost is what moved it.
2. **But the cost gate still binds:** gross/cost = 2.57 < 3. The edge does not clear cost with margin, so it
   is fragile — a small cost increase flips it negative. The amplitude filter is not binding on gold (its
   bands always exceed the threshold), so it cannot push the ratio higher.
3. **DD is un-FTMO:** MaxDD −38 % unlevered; vol-targeting to <10 % DD would keep the (vol-invariant) Sharpe
   at 0.46 — still below 0.5.
4. **No tuning past this.** Forcing 0.46→0.5 by exit/threshold mining would be p-hacking a cost-fragile edge
   that would not survive DSR on the 48-cell space. Reported as a near-miss, not a pass.

**Conclusion:** Piste B remains the structural laggard — consistent with iteration-1 and the repo's
`xauusd_rangefade` / `breakout_deepdive` NO-GOs. Gold is the one instrument with a real two-sided range
tendency, but at retail FTMO cost it clears the bar only *barely* on gross and not at all on net-Sharpe>0.5.
**Only route forward:** a sub-spread execution venue (maker fills) — not retail FTMO. No audited-engine
re-test warranted at net Sharpe 0.46 / gross-cost 2.57.
