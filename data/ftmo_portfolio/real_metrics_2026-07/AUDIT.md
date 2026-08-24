# AUDIT — Real book metrics (account 3, <ACCOUNT_ID>): J1 gate + low-check

Independent auditor (author≠auditor). Adversarial re-derivation from raw data. `/usr/bin/python3`.
Every number below was re-computed by the auditor from `tables/cohorts_*.csv`, `tables/funded_all.csv`,
`records/events_*.csv`, the raw `deep_history_utc` M1 and the canonical `sim_m5_repaired.parquet` —
**NOT** by running `aggregate.py`. Two validation gates (`run_equiv.py`) were re-run because the task
explicitly permits it.

## VERDICT: **CONFIRM-WITH-CAVEATS**

All four anchor numbers, the full account-3 triplet, the re-purchase distribution, the entire
decomposition with its CIs, both validation gates, and the residual-tail attribution reproduce
**exactly** (to rounding). No discrepancy and **no bug** was found — in particular the specific
"low-check silently suppressed" failure mode I hunted for is **absent**: the intra-bar offsets are
real and substantial (median 1.5–3.7 bps, p99 11–30 bps) and genuinely fire. The caveats below are
genuine *interpretation* limitations (a sample thin in the intervention zone; a pre-reg refinement
that lands on the more favorable of two arms), all of which the author already discloses. Nothing
warrants REJECT; nothing is a clean unqualified CONFIRM either.

---

## 1. Independently reproduced (auditor's numbers vs claim)

### 1.1 Anchors (Scrutiny A) — re-derived from raw cohorts CSVs
| anchor | auditor | claim | match |
|---|---|---|---|
| POLICY OFF/close p_pass | **87.0130%** (402/462) | 87.01 | ✓ exact |
| POLICY gate Δ (ON−OFF close) | **+0.6494 pt** (405−402) | +0.65 | ✓ exact |
| SWING OFF/close p_pass | **71.4286%** (330/462) | 71.43 / 71.4 | ✓ exact |
| baseline EV | **+$739.72** | +$740 | ✓ exact |

### 1.2 Headline account 3 (SWING / gate ON / low) — Scrutiny A
| metric | auditor | claim | match |
|---|---|---|---|
| p_pass | **69.6970%** (322/462) | 69.70 | ✓ exact |
| attempts/campaign | **3.2857** | 3.29 | ✓ exact |
| med_t → funded | **38.0 d** | 38 | ✓ exact |
| EV | **+$677.70** | +$678 | ✓ exact |
| Re-purchase (independent MC, seed **123**≠author 23, 20k) | E[campaigns] **1.43**, E[challenges] **4.71**, E[total] **88 d** (med 56, p90 192) | 1.44 / 4.74 / 88 (med 56, p90 195) | ✓ (MC noise only) |

### 1.3 Decomposition + CIs (Scrutiny A) — independent block-bootstrap (block=10, 3000 draws, seed=23, circular) + independent McNemar
| effect | auditor Δp [CI90] | claim | McNemar (auditor) |
|---|---|---|---|
| gate only | **−0.43 [−1.30, 0.00]** | −0.43 [−1.30, 0.00] | b01=0, b10=2, p=0.50 |
| low-check only | **−1.30 [−4.11, +1.52]** | −1.30 [−4.11, +1.52] | b01=10, b10=16, p=0.327 |
| combined (compte 3) | **−1.73 [−4.76, +1.08]** | −1.73 [−4.76, +1.08] | b01=10, b10=18, p=0.185 |
| low_both (pessimistic) | **−3.90 [−9.32, +1.52]**, p_pass 67.53% | −3.9, 67.5% | 102 discordant, spans 0 |

All CI90 span 0. The bootstrap CIs are **not** artificially wide: an independent exact-McNemar paired
test corroborates non-significance (combined p=0.185). The "small and non-significant" conclusion is
robust.

### 1.4 EV / VAL (Scrutiny G) — re-derived from `funded_all.csv`
- VAL = FEE(96) + 0.8·(mean_IS extr + mean_OOS extr)/2, re-computed independently:
  OFF/close **1437.64**, ON/close **1485.90**, ON/low **1424.92**, OFF/low 1376.67, dom 1437.64/1485.90.
- Baseline: 0.71429·1437.64 − 2.9913·96 = **+$739.72** ✓ (VAL≈1438 → ≈740 confirmed).
- Account 3 uses the **ON/low funded VAL = 1424.92** as claimed: 0.69697·1424.92 − 3.2857·96 = **+$677.70** ✓.
- Gate-only EV = 0.70996·1485.90 − 2.9892·96 = **+$767.96** ✓ (study's "gate +$768 > baseline +$740").

### 1.5 Validation gates (re-run)
- **G-EQUIV** (`run_equiv.py`, re-run): `lowcheck(mode=close)` == `engine_v22` over all **462 cohorts,
  0 mismatches**, `px_day` bit-identical, `lo≤close≤hi` PASS, **pooled = 87.01**. mode="close" is a
  true no-op → the correction is fully attributable to the adverse path. (Scrutiny C-i, E-5)
- **G-tz** (Scrutiny D, independent rebuild): deep_history M1 → Paris-localized → M5 **left-labeled**
  close == `sim_m5` close on 3 regular days incl. **2024-05-15 (NOT in author's probe set)**,
  2024-02-14, 2019-03-20: **median|Δ| = 0.000000, max 0.000000** over 288 bars each; right-labeled
  gives 0.008–0.02 (confirms left is the correct convention). Same underlying source → the low-check
  is a pure same-grid intra-bar overlay, no MT5↔Duka confound. `gtz_validation.csv` is not fabricated.

### 1.6 Low-check logic & "does it actually fire?" (Scrutiny C, E) — the make-or-break check
Independently loaded `lohi_m5_paris.parquet` + `sim_m5_repaired.parquet`, reindexed exactly as the
engine does:
- **Coverage**: 99.92% (USDJPY), 94.27% (XAU), 83.71% (US100), 83.02% (GER40) of sim bars carry a lohi row.
- **Offsets genuinely applied** (not zeroed by misalignment): on covered bars ~**100% have `lo < close`
  strictly**; |off_lo| median **1.5 (JPY) / 2.9 (XAU) / 3.4 (US100) / 3.7 (GER40) bps**, p99 **11–30 bps**,
  max 217–453 bps. Adverse sign verified in code: `lo` for long, `hi` for short; `percol.sum` (all-legs,
  conservative upper bound) vs `percol.min` (dominant-leg lower bound) correct.
- **`lo≤close≤hi`**: 0 violations over the full grid.
- Floor detection runs on `eq_adv` against `lim_eff = max(daily_limit, FLOOR)` → both daily and max-loss
  barriers checked on the adverse; **target (`ht`) stays on close** → no fabricated passes (conservative).
- Breaker on close for "low", on adverse only for "low_both" — matches the stated floor-continuous /
  breaker-discrete refinement.

→ The small challenge correction is **NOT** a suppression artifact. Mechanism confirmed: at the challenge
stage SWING margin de-levers positions, so a real 10–30 bps intra-bar dip rarely breaches; the tail lives
in the **funded stage** (vm1, full positions).

### 1.7 Funded stage & residual tail (Scrutiny E, F)
- Funded bust rates (`funded_all.csv`): **close 2.6%** (5/191), **low 30.4%** (58/191), **low_dom 13.6%**
  (26/191). Confirms "3% close vs 14–30% low" and that the low-check fires far harder at funded/vm1.
- **Residual 0%-in-zone** (Scrutiny F): USDJPY closed ≥160 on only **14 days, first 2024-06-26**, last
  2026-06-05 (consistent with USDJPY reaching 160 only in mid-2024). Of the **532** challenge low-check
  busts (swing_ON_low) **0 fall in-zone**; of the **58** funded busts **0 in-zone**. Both **0.00%** ✓.
- Sleeve attribution reproduced exactly: challenge dominant leg USDJPY 179 / XAU 158 / US100 147 /
  GER40 48; funded USDJPY 36 / XAU 22 (all-legs). Tail carried by out-of-zone JPY flashes + gold, as
  claimed — the gate (J1≥160) touches essentially none of the in-sample intra-bar tail.

### 1.8 Pre-reg deviation (Scrutiny B) — verified against the breach memory
Pre-reg §5 literally put **both** floor and breaker on the adverse (= "low_both"). The author refines the
**primary** to floor-adverse / breaker-**close** ("low"). Reading `breach_<ACCOUNT_ID>_2026-07-02.md`
confirms the justification is **empirical, not post-hoc**: FTMO's *continuous* monitor liquidated at
**06:49:41 UTC intra-bar**, while the EA breaker (`InvariantCheckM5`, `OnTimer`) "evaluates ONLY on the
M5 grid" and **never fired** — "continuous prop-firm monitor structurally beats a discrete 5-min
breaker." So modeling the floor continuously (adverse) but the breaker discretely (close) is the more
faithful mapping of the real mechanism; "low_both" would grant the breaker intra-bar foresight it
demonstrably lacks. The author **transparently reports low_both as the pessimistic bound** (67.5%,
−3.9 pt) and even that CI spans 0. This is a documented, defensible refinement, not cherry-picking — but
see R2.

---

## 2. Discrepancies / bugs found

**None.** Every headline, anchor, CI, gate and attribution reproduced to rounding. The candidate bug I
specifically pursued — a grid misalignment zeroing the low/high offsets and silently shrinking the
correction — does **not** exist: offsets are present on 84–99.9% of bars with correct magnitude and sign,
and `mode="close"` is a bit-exact no-op vs `engine_v22`. The direction of every deliberate modeling
choice is conservative *against* the author's "small correction" thesis except the breaker-on-close
refinement, which is independently justified (§1.8): all-legs simultaneity (primary) is the bust-inflating
upper bound; the bid/ask spread nudge worsens the adverse; target stays on close (no fabricated passes).

---

## 3. Reservations

- **R1 (interpretation — the important one).** The headline p_pass 69.70% and the "gate ≈ 0 in-sample /
  0% in-zone tail" are measured on data ending **2026-06-05**, which *excludes the very July 02–03
  intervention flashes that motivated the gate+low-check*, and USDJPY reached ≥160 on only **14 in-sample
  days (all 2024-06+)**. So the in-sample gate value being null and the tail being "out-of-zone" partly
  reflect a sample that is **thin in the intervention regime**, not proof that intervention risk is
  benign. The gate's real value is explicitly **prospective** (the two live in-zone breaches, per the j1
  studies) — a judgment the study labels as such and does not fold into the 69.70%. Correct framing, but
  the reader must not read 69.70% as pricing intervention-tail risk.

- **R2 (pre-reg refinement lands on the friendlier arm).** Primary "low" (−1.73) is the *less* pessimistic
  of {low −1.73, low_both −3.90}. The justification is sound and the pessimistic arm is fully reported,
  but honesty requires keeping low_both in view: the optimism correction could be as large as **−3.9 pt**
  (p_pass 67.5%, EV ≈ +$647). Qualitative conclusion (small, CI⊃0) survives under either arm.

- **R3 (leg coverage).** US100/GER40 lohi coverage is 83–84% (missing bars fall back to lo=hi=close, no
  adverse — conservative but it means the low-check cannot fire on ~16% of those two legs' bars, possibly
  marginally understating their contribution). The dominant tail carriers USDJPY (99.9%) and XAU (94%)
  are well covered, so the headline is not materially affected.

- **R4 (declared).** Low-check detects the *bust* correctly but overstates the *loss* (liquidation ≈ the
  floor, not the intra-bar low); absolute levels are indicative — only the **Δ between arms** is robust.
  Sub-M1 flashes are not modeled. Both are author-declared caveats and do not affect a bust/no-bust p_pass.

- **R5 (secondary, not re-run end-to-end).** The design/funnel raw outputs (`cohorts_*.csv`,
  `funded_all.csv`) were taken as given and re-aggregated from scratch; I re-ran only the G-EQUIV funnel
  (462 cohorts) and the offset/tz layers independently, not the full `run_design.py` 2×2×margin sweep.
  Given G-EQUIV is bit-exact and every aggregate re-derives, residual risk here is low.
