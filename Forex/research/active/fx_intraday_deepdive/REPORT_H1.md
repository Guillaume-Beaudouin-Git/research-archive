# REPORT — H1: London-open reversal of the Asian-session displacement

**Status:** CLOSED at the Phase-1 IC gate (cheap close). **Verdict: real mechanism, DEAD net — cost-killed
~5–10× (L34) + one-sided (L25) + gross only at the cumulative-N noise floor.** No Phase-2 deep-dive run
(pre-reg: Phase-2 only if Phase-1 passes; it did not). Negative is robust across 15 entry/exit windows,
4 entry delays, full-history and recent-regime cost.

**Cumulative N after H1: 127** (108 baseline + 1 prior-look + 1 primary IC + 14 surface cells + 3 delay
variants — see `N_ledger.md`). Data: `cache/*_15min.parquet`, TRUE-UTC verified (below).

---

## 0. Data integrity — TRUE UTC verified empirically (not just label-trusted)

From `cache/utc_verification.json` (computed on raw M1, no strategy returns). The true-UTC FX signature
holds for every pair:

| signature | observed (FX majors) | true-UTC expectation | EET(broker) would show |
|---|---|---|---|
| spread **min** hour | **14:00 UTC** (AUDUSD 09:00) | London/NY overlap ~13–16 UTC | ~16–18 |
| volume **max** hour | **14:00–16:00 UTC** | overlap | ~16–18 |
| Friday last-active | **21:00 UTC** | FX close 21:00 UTC (Fri 17:00 ET) | ~23:00 |
| Sunday reopen | **21:00 UTC** | FX open 21:00–22:00 UTC | ~23:00 |
| Saturday bars | **0** | closed | 0 |

→ Confirms the MANIFEST's tz fix and overlap-corr gates **on the data itself**. Session windows below are
genuine UTC. (XAUUSD cached as out-of-class contrast; not used in the FX pools.)

---

## 1. The hypothesis (frozen — PRE_REGISTRATION.md §2)

At the London open, fade the overnight (Asian-session) displacement. Mechanism: EUR/GBP/CHF/CAD trade their
*thinnest, least-informed* window in Asia; when London (their dominant liquidity venue) opens, real price
discovery **reverts** the noise-driven Asian drift. Prediction: **corr(asian_ret, London-morning ret) < 0**,
**concentrated in European pairs** and **absent in Asia-native pairs** (whose Asian session is *informed*).

- Signal `x_d = −asian_ret_d / σ₆₀(lagged)`, asian_ret over 23:00(prev)→07:00 UTC (known at 07:00).
- IC target `fwd_ret` = 07:00→12:00 UTC. Entry delay+1 (causal). Intraday-flat → swap-free.
- Primary pool (predict reversal): EURUSD, GBPUSD, EURGBP, USDCHF, USDCAD.
- Contrast pool (predict none): USDJPY, EURJPY, AUDJPY, AUDUSD, NZDUSD.

---

## 2. Phase-1 IC gate result — `results/phase1_ic.json`

### 2.1 Per-pair (full history 2007–2026, ~5,030 trades/pair, ~260/yr — N≫50/yr ✓)

**PRIMARY (European — mechanism predicts reversal: corr<0, Spearman>0):**

| pair | corr(asian,fwd) | Spearman | gross Sharpe | **net Sharpe** | gross bps/trade | cost bps/trade | gross HAC-t |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | **−0.0418** | +0.0267 | 0.43 | **−0.42** | 0.80 | 1.56 | 1.93 |
| GBPUSD | −0.0139 | +0.0245 | 0.33 | −0.77 | 0.70 | 2.32 | 1.51 |
| EURGBP | −0.0274 | +0.0136 | 0.01 | −2.62 | 0.01 | 5.22 | 0.02 |
| USDCHF | −0.0239 | +0.0222 | 0.33 | −1.65 | 0.81 | 4.87 | 1.46 |
| USDCAD | +0.0025 | +0.0186 | 0.33 | −1.46 | 0.50 | 2.76 | 1.50 |

**CONTRAST (Asia-native — mechanism predicts none):**

| pair | corr(asian,fwd) | Spearman | gross Sharpe | net Sharpe | gross HAC-t |
|---|---:|---:|---:|---:|---:|
| USDJPY | +0.0134 | −0.0163 | −0.45 | −1.81 | **−2.01** |
| EURJPY | −0.0034 | +0.0028 | 0.05 | −1.32 | 0.22 |
| AUDJPY | +0.0312 | +0.0027 | −0.19 | −2.58 | −0.86 |
| AUDUSD | +0.0094 | +0.0109 | 0.03 | −1.76 | 0.14 |
| NZDUSD | −0.0125 | −0.0038 | 0.07 | −3.29 | 0.31 |

### 2.2 Pooled & falsification verdicts

| test | metric | result | verdict |
|---|---|---|---|
| **Sign** | mean corr(asian,fwd) primary | **−0.021 (<0)** | ✅ reversal confirmed |
| **F2 mechanism contrast** | primary port HAC-t **2.11** vs contrast **−0.57** | primary ≫ contrast | ✅ **edge concentrates in European pairs, absent in Asia-native — mechanism is real** |
| **F1 strict t-gate** | honest port HAC-t **2.11** (cross-pair-robust) | < 2.5 | ❌ FAIL (literal stacked-OLS t=3.06 is SE-inflated: ignores the 5 pairs' correlation) |
| **F3 two-sided (L25)** | fade-up t **3.33** (+0.93 bps) vs fade-down t **0.63** (+0.17 bps) | one-sided | ❌ FAIL — 85% is shorting EUR/GBP after Asian rallies = beta-disguised |
| **F4 delay (L26)** | gross flat across delay 0/1/2/3 (0.56/0.53/0.55/0.42 bps) | no delay-0 spike | ✅ genuine signal, NOT a fill artifact |
| **F5 cost (L34)** | pooled gross **0.56 bps** / cost-p95 **5.7 bps** = ratio **0.099** | ≪ 1.5 | ❌ **FAIL hard — cost-killed by ~10×** |

**GATE_PASS = False.** The signal is real (F2 ✅, F4 ✅, sign ✅) but fails the strict t-gate, is one-sided
(L25), and is cost-killed (L34).

---

## 3. Bulletproofing the cost-kill — `results/phase1_surface.json`

Is gross<cost an artifact of the primary (23:00 start / 12:00 exit)? Swept asian-start × exit on the
European pool (each cell counts toward N). **Every cell has net Sharpe < 0 and gross/cost ≪ 1.5:**

| start\exit | 10:00 | 11:00 | 12:00 | 13:00 | 15:00 |
|---|---|---|---|---|---|
| **22:00** | r0.13 / nS−3.19 | r0.14 / −2.82 | r0.16 / −2.47 | r0.21 / −2.00 | r0.26 / −1.53 |
| **23:00** | r0.12 / −3.18 | r0.13 / −2.82 | r0.16 / −2.46 | r0.25 / −1.92 | **r0.29 / −1.49** |
| **00:00** | r0.08 / −3.26 | r0.08 / −2.95 | r0.09 / −2.65 | r0.15 / −2.14 | r0.23 / −1.60 |

*(r = gross/cost ratio; nS = net Sharpe. Best cell = a23_e15: gross 0.96 bps, cost 3.33 bps, ratio 0.287.)*

- **Best gross/cost ratio across all 15 windows = 0.287** — 5× under the L34 bar (1.5). Gross is bounded by the
  total London-morning move; no exit choice closes a 5–10× cost gap.
- **Delay sweep (F4):** gross 0.56/0.53/0.55/0.42 bps at delay 0/1/2/3 → flat → real signal, graceful decay,
  no fill artifact. (This is what a real-but-tiny edge looks like.)
- **Recent regime (≥2016, tighter spreads):** best cell ratio rises only to **0.354**, net Sharpe **−1.32**.
  No regime rescue.

---

## 4. Deflated Sharpe & p(pass) at cumulative N — `results/phase1_finalize.json`

Best gross/cost cell (a23_e15), primary pool, T = 5,028 days, **N = 127**:

| metric | gross (un-tradeable) | **net (the only honest number)** |
|---|---:|---:|
| rf-free Sharpe | **0.597** | **−1.486** |
| Sharpe (dsr.py, rf=0.02) | 0.10 *(rf artifact on unlevered P&L)* | −1.983 |
| Noise floor Sharpe @ N=127 (SE₀·E[max₁₂₇], SE₀=√(252/T)=0.224) | **0.585** | — |
| gross vs floor | **0.597 ≈ 0.585 → AT the floor** | — |
| DSR(P) @ N=127 | 0.00 (std_sr=1 convention) | **0.00** |
| p(pass) FTMO 2-step | — | **0.031** |

- **Even the gross signal, deflated for the program's cumulative search (N=127), sits exactly at the noise
  floor** — statistically indistinguishable from the best of 127 zero-edge draws over 5,028 days.
- **Net is dead:** Sharpe ≈ −1.5, DSR 0, p(pass) 0.03. FundedNext geometry not computed — moot for a
  negative-Sharpe net series (any symmetric-barrier geometry rejects it).

---

## 5. Verdict

**H1 = REAL mechanism, DEAD net.** Closest pre-registered label: **real-but-sub-threshold (gross) → dead (net)**.

- ✅ **New, genuine finding:** the London-open session-handoff reversal *exists* in European majors — sign
  correct on all 5 pairs, **textbook European-vs-Asia-native contrast** (port HAC-t 2.11 vs −0.57), and
  **delay-robust** (not a fill artifact). This was **untested** in the repo (distinct from the burned B1
  all-hours MR, B3/B4 breakouts, B5/B6 fix windows).
- ❌ **Untradeable on retail FTMO MT5 CFD:** gross ~0.5–0.6 bps/trade vs cost ~2–5 bps → **net Sharpe
  negative on every pair and every window**; one-sided (L25); gross only at the N=127 noise floor.
- This is the **same death as B1/B5/B6** and **extends L34**: not only fix windows, but the **London-open
  handoff** too, is a real-gross / dead-net retail FX intraday flow edge. The binding fact is structural —
  the FX intraday microstructure displacement that mean-reverts (~0.5 bps) is an order of magnitude smaller
  than the retail CFD round-trip (~2–5 bps). **Candidate lesson L43** (proposed, see below).

### Proposed lesson (candidate — for user ratification into CLAUDE.md)
> **L43 — London-open session-handoff reversal is real but cost-dead at retail.** The overnight (Asian)
> displacement of *European* FX majors partially reverts in the London morning (mechanism-true: present in
> EUR/GBP/CHF/CAD, absent/continuation in Asia-native JPY/AUD/NZD; delay-robust; pooled gross HAC-t ~2–3).
> But the revertible displacement is ~0.5 bps/trade vs ~2–5 bps FTMO MT5 RT cost → net Sharpe < 0 across all
> entry/exit windows and regimes, one-sided (L25). Generalises L34 from *fix windows* to the *session open*:
> **any retail FX intraday flow-reversal edge must clear `gross/cost ≥ 1.5` at pre-flight or it is dead** —
> the London open does not escape it despite being the day's tightest-spread window.

### What's burned now (add to the FX intraday burn list)
- **H1 London-open Asian-drift reversal** — real mechanism, cost-dead (this report). Do not re-test as a
  standalone retail CFD strategy. *Untested-for-lack-of-data:* whether it clears at **institutional** cost
  (≤1 bp RT) — plausibly yes (gross/cost ≈ 0.6/1.0–1.5), but out of scope (no institutional execution).

### Untested / next (proceed to H2)
Per pre-reg ranking: **H2 — post-scheduled-news intraday drift** (next pre-registration). Caveat already
flagged: H2's binding risk is the *same* cost wall, *amplified* at release (spread blowout) — H1's result
raises the prior that H2 also dies on cost unless the post-news drift is ≫ the (blown-out) spread.
