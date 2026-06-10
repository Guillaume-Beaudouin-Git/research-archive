# N_ledger — cumulative trial count (intraday-FX deep-dive)

**Convention:** program cumulative N entering this run = **108**. Every backtested CONFIGURATION (IC test,
delay variant, param-grid point, ablation, sub-period-as-selection) increments N. Pure data validation
(true-UTC check, cache build) and per-pair *decompositions of a single pre-registered test* do NOT each
count — but each independent signal SPEC does. Honest rule of thumb: if swapping it could have been the
"winner" I'd have reported, it counts.

| Step | What | ΔN | Cumulative N | Note |
|---|---|--:|--:|---|
| — | Program baseline entering run | — | **108** | per PROGRAM_DECISION_MEMO + memory |
| pre | True-UTC verification + 15-min cache build | 0 | 108 | data validation, no strategy return |
| H1-prior | B3 EURUSD 4h London reversal look (t=−2.45, 2020–24) | +1 | 109 | disclosed prior look (PRE_REG §6) |
| H1-P1 | Phase-1 IC gate, H1 primary spec (asian23/open07/exit12/delay+1) | +1 | 110 | the pre-registered single IC test |
| H1-surf | Cost-kill surface: asian_start{22,23,0}×exit{10,11,12,13,15} (14 new cells; primary already counted) | +14 | 124 | bulletproof the negative — every cell net-Sharpe<0 |
| H1-delay | Delay sweep {0,2,3} on primary cell (delay+1 already counted) | +3 | 127 | F4: gross flat → no fill artifact |
| H1-VERDICT | **DEAD net** (cost-killed ~5–10× L34, one-sided L25); mechanism real (F2 contrast); gross at floor | 0 | **127** | recent-regime view = sub-sample, +0 |

**H1 closed at N=127.** Real mechanism, untradeable net. Proceed to H2 (new pre-registration below).

| H2-P1 | H2 IC gate, post-USD-news continuation (impulse15/hold45/entry r+30) | +1 | 128 | pooled HAC-t 0.19 ≪ 2.5 |
| H2-grid | impulse{15,30}×hold{30,60,120}×{all,majors} = 12 cells | +12 | 140 | best cont_t 2.33 (<2.5); all net-Sh<0 |
| H2-VERDICT | **DEAD** — no continuation at ≥15min, cost-dead below; majors show none/fade | 0 | **140** | cleaner null than H1 |

**H2 closed at N=140.** No edge + cost-killed. Proceed to H3.

| H3-scan | Day-of-week × session seasonal scan: 10 FX × 5 dow × 2 sessions = 100 cells | +100 | 240 | WF sleeve −4.27 Sh; best cell at luck ceiling |
| H3-VERDICT | **DEAD** — no cost-beating seasonal; EURUSD-Fri net-+ but decayed to 0 post-2015 (F6) | 0 | **240** | sub-period check = decomposition, +0 |

**H3 closed at N=240.** Space burned across all 3 angles. → SYNTHESIS.md.

---
_Updated per hypothesis. Each delay variant / grid point / ablation appends a row._

### Final cumulative N = 240
- 108 program baseline + 1 prior-look + **H1** 18 (1 IC + 14 surface + 3 delay) + **H2** 13 (1 IC + 12 grid)
  + **H3** 100 (scan cells) = **240**. All three hypotheses CLEAN NEGATIVE. Deflated bar at N=240:
  noise-floor Sharpe ≈ 0.63; nothing in this run approached it net.
