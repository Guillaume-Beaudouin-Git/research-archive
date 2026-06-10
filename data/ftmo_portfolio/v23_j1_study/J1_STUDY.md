# v2.3 J1 STUDY — VERDICT: NULL. J1 STAYS (budget 0.5, unbanded). NO SPEC CHANGE.

1. **No variant qualifies** under the pre-registered rule (Δp pooled or ΔEV > 0 at 90% CI):
   best ΔEV = +$2.8 [−86.7;+90.3] (A_raw), best Δp = 0.0 [−2.2;+2.4] (B_raw) — all noise.
2. **J1 OFF is CI-significantly HARMFUL on the frozen v2.2 baseline**: Δp −7.6 pts
   [90% CI −13.0;−2.8] raw / −7.4 [−13.0;−2.4] iso-leverage; ΔEV −$88 [−171;−11] / −$98
   [−194;−9]. The v2.1 read "removal ~free (−2.2 ns, EV +$8)" **reverses** inside the
   ORB-challenge-OFF baseline — interaction ≈ −5.4 pts. The mission's premise (measure inside
   v2.2, never v2.1) is what caught this.
3. A (budget 0.5→0.25): pooled ns (−1.5/−1.1 pts); era-split flag IS −5.6/−5.2 vs OOS
   +2.6/+3.1 — recorded, not actionable under the pooled rule.
4. B (no-trade band): exact null by anatomy — daily vol-target jitter is only ~4.5% of J1's
   executed turnover (62% = forced flattens, 84% of the 22:05 channel = re-entries).
5. Baseline reproduced the contractual anchors exactly (87.01, 462/462 cohorts ≡ committed
   table); attribution identity exact; X* and iso-factors frozen before variant runs.

---

## Gate & baseline
- v2.2 commit **605f4a4** (`605f4a426da3eac4f5a2644bca774a07f1e5f754`), file SHAs in
  `baseline_pin.json`. Canonical table `v22/tables/v22_challenge_91.csv` (IS 90.6 / OOS 83.4 /
  pooled 87.0, att 3.24). EV convention VAL=$1,422 / FEE=$96 (contractual, re-derived).
- Engine: `j1_engine.py` = instrumented clone of `v22/engine_v22.py` (micro-ORB "nothing
  opened by 21:30" semantics). **Acceptance: EQUIV PASS** — 462/462 cohorts identical
  (funded/attempts/t/micro) vs the committed engine AND vs the canonical CSV (`equiv.log`).
  Cash + attribution identities asserted per attempt (tolerance = documented micro-dip
  phantom on s2/s3-bust micro days); zero violations.
- Instrumented baseline: pooled 87.01 / IS 90.6 / OOS 83.4, att 3.24 — anchor-exact.
  12,667 day-attempt records, 444 bust events, 17,930 margin snapshots.

## Pre-registered variants (≤3 per L10) — 6 arms, each vs baseline, paired per cohort
| arm | Δp pooled (90% CI) | Δp IS / OOS | ΔEV (90% CI) | Δatt | Δmed_t | Δbust/coh (90%) | ΔMonday-busts (90%) | ΔJ1-gap $/coh (90%) |
|---|---|---|---|---|---|---|---|---|
| A_raw (J1 ×0.5) | −1.5 [−6.9;+3.7] | −5.6 / **+2.6** | +$2.8 [−87;+90] | −0.25 | −1j | −0.13 [−0.27;+0.00] | −0.02 ns | +$9.5 ns |
| A_iso (vm ×1.129) | −1.1 [−6.1;+3.7] | −5.2 / **+3.1** | −$0.8 [−89;+84] | −0.15 | −3j | −0.11 ns | −0.01 ns | +$8.3 ns |
| B_raw (band X*=30%) | 0.0 [−2.2;+2.4] | −0.9 / +0.9 | +$1.0 [−35;+39] | −0.01 | 0j | −0.02 ns | +0.01 ns | +$2.5 ns |
| B_iso | ≡ B_raw — measured FACT_B = 0.9903, \|FACT_B−1\| ≤ 0.01 ⇒ declared identical (pre-registered rule; marginal at 0.0097) |||||||||
| C_raw (J1 OFF) | **−7.6 [−13.0;−2.8]** | −12.0 / −3.1 | **−$88 [−171;−11]** | −0.21 | +2j | −0.03 ns | +0.01 ns | **+$28 [+9;+53]** |
| C_iso (vm ×1.184) | **−7.4 [−13.0;−2.4]** | −6.9 / −7.9 | **−$98 [−194;−9]** | −0.07 | 0j | +0.04 ns | +0.08 ns | **+$28 [+9;+53]** |

n=462 cohorts (step-7, IS 2013-10→2019-12, OOS 2020-01→2026-02), N_eff=174 (autocorr ESS,
battery convention). CIs: paired circular block bootstrap, blocks 10, 3,000 draws, seed 23.
95% CIs in `tables/paired_deltas.csv`. Levels per arm in `tables/summary_arms.csv`.

## Decision rule application
Gate (Δp or ΔEV > 0 at 90%): **0/6 arms pass.** Guards (bust, Monday-gap) never rescue a
failed gate. → **Study closes on the documented null. J1 stays. No spec change in this
session** (per mission: a winning variant would have become THE one frozen change of a
v2.3 contractual re-run; there is none).

## Findings behind the null
**F1 — J1 is load-bearing under ORB-off (the v2.1→v2.2 interaction).** v2.1 LOO (ORB P&L on,
baseline 84.6): J1-off raw −2.2 ns, EV +$8. v2.2 (ORB challenge-OFF, micro-ORB, baseline
87.0): −7.6 sig. Mechanism (descriptive, `tables/attempt_outcomes.csv`): without J1 the book
is SLOWER, not bustier — per-attempt P1 pass actually rises (50.9% vs 46.2%) but **P2
collapses (55.8% vs 61.1%)**, attempts shrink 1,498→1,401 (the 91-day wall truncates),
med_t +2j, book vol $413/day vs $449. J1's 28.8% risk share is diversifying variance that
paces the funnel; re-levering gold/overnight does not replace it (C_iso ≈ C_raw, confirming
v2.1's iso finding, now ×3 the size). Day-count is NOT the channel (micro-ORB fires before
the 22:05 rebalance; J1 cannot suppress it).

**F2 — The J1 "re-trading bleed" is flatten-cycle churn, not vol-target jitter.** Executed J1
turnover $842M over 12,667 day-attempts: 62.3% forced flattens (breaker/target-hit), and of
the 22:05 channel 83.8% entries / 4.3% exits / 11.8% same-sign re-trades (median re-trade
3.6% of target). The pre-registered band therefore caps out at a 4.5% turnover cut
(X grid ≤30%: ratio 0.955 at X*=0.30; realized in B_raw: −1.0%, cost $4.49 vs $4.53/day).
A no-trade band cannot address a churn structure made of full-position cycles — any future
turnover work must target the flatten/re-entry cycle (a governor/spec question, NOT this
study's mandate).

**F3 — A's era split.** Halving J1 hurts IS (−5.6) and helps OOS (+2.6) consistently across
both forms. Pooled-ns by construction of the rule; logged as a watch item for any future
v2.4 program (would need its own pre-registration; nothing adopted here).

**F4 — Side effects of J1 (levels, baseline).** Margin: J1 is the main margin user — bind
rate 6.3% → 3.0% (A_raw) / 2.0% (C_raw); pre-cap p99 0.81 → 0.72/0.69. Monday-gap busts:
J1's weekend-gap P&L on breach days is only −$28/cohort (C eliminates it, +$28 [+9;+53] —
real but ~2% of VAL, immaterial vs C's −$88 EV harm). Monday busts/cohort 0.33 of 0.96
total busts (34%), consistent with v2.1's "31% Monday" anatomy.

## Honesty block
- Trial accounting: +6 pre-registered arms (3 variants × 2 forms), 1 fixed decision rule,
  0 post-hoc arms; v2-program ledger. X* selected by frozen mechanical rule on the frozen
  grid (target ratio 0.50 unreachable → closest = 0.30, documented above, NOT re-mined).
- FACT_B=0.9903 sits 0.0003 inside the ≤0.01 identity threshold — the B_iso≡B_raw call is
  rule-driven but marginal; a distinct B_iso run would change nothing material (B_raw itself
  is a 0.0-pt null with the tightest CI of the study).
- In-container per-leg drift is path-conditional (e.g. J1 drift −$7.1/day at full size,
  +$0.8/day at half size: different bust/flatten windows) — these are attribution numbers
  inside the container, not standalone signal stats (J1 standalone SR +0.42 unchanged, v2.1).
- The study reuses the v2.2 stack bit-frozen (SHAs pinned); any change to v22/ after
  2026-06-10 21:00 invalidates these numbers.
- Lesson candidate (NAMED, no number minted in-session per reconciliation convention):
  **"loo-nontransfer"** — a LOO/removal verdict is container-conditional; re-measure inside
  the amended frozen baseline before acting on it (here: −2.2 ns → −7.6 sig across one spec
  change). For the L-registry reconciliation session to engrave or reject.

## Artifacts
`PREREGISTRATION.md` (frozen pre-run) · `baseline_pin.json` · `equiv.log` · `band_X.json` ·
`factors.json` · `j1_engine.py` / `run_arms.py` / `calibrate_band.py` / `aggregate.py` /
`make_tornado.py` · `tables/` (cohorts/attempts × 6 arms, summary_arms, paired_deltas,
attempt_outcomes, decision.json) · `records/` (day records, bust events, margin snapshots
per arm — parquet) · `plots/tornado.png`.
