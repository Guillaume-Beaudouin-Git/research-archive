# FTMO 10k 2-Step Program — Decision Memo

**Date:** 2026-06-08 · **Purpose:** approve a pivot, not re-derive results · **Scope:** synthesis of three independent research lines; no new backtests run.

## Bottom line
Three independent investigations — a top-down audit of a claimed-fundable book, a bottom-up build of the best honest book, and an outside-in broad edge search — **converge on the same wall**: on free price data over the FTMO-executable 16-instrument universe, the honest probability of passing the 10k 2-step is **~0.2–0.34**, every confidence interval and Deflated Sharpe sits **below the financiability bar**, and a 97-trial structural search finds **nothing above the noise floor**. **Recommendation: do-not-fund on free price data.** The next allocation of effort is **data sourcing + one swap measurement**, not more signal search.

---

## 1. Consolidated evidence (three angles, one ceiling)

| # | Line / path | Angle | What was tested | Honest result (with CI / DSR) | Killing mechanism |
|---|---|---|---|---|---|
| 1 | **Portfolio audit** `research/ftmo_portfolio_audit/` | Top-down: does a *claimed fundable* book reproduce? | Clean-room regen of the "decorrelated 3-sleeve" book (RSI2 + BTC-mom + US30-MR) claiming **p(pass≤3mo OOS)=0.549** | **NOT-CONFIRMED.** p(pass≤3mo) → **0.18–0.29** correct / ≤0.41 optimistic; honest 90% CI e.g. **[0.08, 0.37]** — *entirely <0.50*. All 3 sleeves miss spec (A −0.47, B −0.54, C +0.09 vs 0.97/0.51/1.00; 2 sign-flip). DSR **0.47**(N100)/**0.28**(N500). | **Stacked optimism**: inflated Sharpe (1.39 claimed vs 0.95 steel-man) × optimistic per-phase MC × favorable leverage; low Sharpe × the 3-month clock. Decorrelation was *real* (\|ρ\|<0.07) but **not** what fails. |
| 2 | **Survivors book** `research/ftmo_survivors_book/` | Bottom-up: build the *best honest book* from validated edges | Ross Hook (deployable 0.44) + swap-net TSMOM, L=2.0 fixed ex-ante on IS, real costs incl. **swap** | **No horizon clears 0.50.** OOS p(pass) **0.24 (6mo)** [0.06, 0.53] / **0.34 (12mo)** [0.08, 0.69]; IS 0.21/0.31. DSR **0.11**(N100)/**0.04**(N500). | **Real CFD overnight swap** consumes TSMOM's edge (deployable Sharpe **~0.05 full / 0.92 OOS** vs swap-free 0.85); **Sleeve-C MR failed inclusion** (OOS 0.04, CI [−1.35, 1.31]) → book is two momentum-family legs, no orthogonal diversifier. |
| 3 | **Funnel ×2** `research/ftmo_candidate_funnel/` + `…_v2/` | Outside-in: search broadly for *any* new edge | Iter-1: 66 causal real-cost configs (MR/trend/seasonality/event/vol, 16 instr). Iter-2: 27 configs in *uncovered* spaces (≥3-leg RV, regime-conditioning, sub-60min index) | **0 DSR survivors** at cumulative **N=97**. Pre-registered noise floor SE0=**0.845** → OOS-Sharpe to beat noise = **2.13**; **max observed 1.50**; genuine-edge dispersion **0.690 < 0.845**. Best lead (vol-tgt TSMOM) full-Sharpe **0.70**, WF 6/6, but p_funded ≈0.46 & DSR fails. | **Structural noise-floor exhaustion**: cross-trial OOS-Sharpe spread is *below* what chance produces; no edge clears the symmetric barrier at honest N. New fact: index returns at 15/30min **do not mean-revert** (gross IS Sharpe <0). |

**Convergence.** Three *different methodologies* — single-book DSR + reproducibility (1), multi-sleeve p(pass) with outer-bootstrap CI (2), structural noise-floor at cumulative N (3) — independently land at **p(pass) ≈ 0.2–0.34 / DSR < 0.5 / below the noise floor**. The same two real, honestly-costed edges (Ross Hook ≈0.44, TSMOM swap-net ≈0.05–0.92) recur in every line; their **decorrelation is confirmed** (worst-decile ρ negative in both 1 and 2) — yet the **raw post-cost Sharpe is too thin** for a symmetric ±target/floor barrier. This is triangulation, not repetition.

---

## 2. The ceiling, stated precisely

> **The symmetric-barrier edge on free price data / the 16 FTMO-executable instruments (10 FX majors+crosses, XAUUSD, US500/US100/US30/GER40, BTCUSD) / daily-and-coarser frequency + sub-60min on indices / under real costs (spread×markup + commission + swap + slippage) = EXHAUSTED**, evaluated against the FTMO 10k 2-step (+10%/+5% vs −5% daily / −10% static) on the 2025-26 OOS at cumulative honest N ≈ 100.

**PROVEN exhausted (do not re-search):**
- These 16 instruments, this free data (MT5/Dukascopy OHLCV + yfinance BTC), at daily frequency (all mechanism families: MR, trend, seasonality, event, vol, cross-sectional, multi-leg RV) and at 15/30min for indices.
- Against the **symmetric** FTMO barrier specifically — the binding constraint is distribution-shape-vs-barrier + thin post-swap Sharpe, not cost alone.

**UNTESTED → still open (not claimed dead):**
- Sub-60min on **FX / XAU / BTC** (only indices were tested intrabar).
- **Tick / order-flow / book** data (unavailable on free feeds; not retail-FTMO-executable anyway).
- Instruments **outside the 16** — AUS200/UK100/JP225/HK50/EU50/US2000, single-stock CFDs, rates, energy, silver — *which lack validated per-bar spreads in our data*, so they were excluded, not tested.
- **Alt-data / fundamental / cross-asset** signals (no data).
- **Non-symmetric containers** (trailing-DD/EOD prop firms, personal book): the real edges (TSMOM ~0.7 vol-targeted, RH ~0.44) may clear where the floor is *not* symmetric to the target.

> Not claimed: "momentum doesn't work" / "mean-reversion doesn't work." TSMOM and Ross Hook **are real, persistent edges** — they simply do not clear *this symmetric barrier* on *this data* financiably.

---

## 3. The two real levers (frame only — not to be pursued in this program)

**(a) NEW DATA — the only path to a genuinely orthogonal edge.** Both audit and survivors identify the *same* structural gap: too few genuinely-uncorrelated, low-swap edges. Free price data on 16 correlated instruments cannot supply a third orthogonal return source (Sleeve-C MR failed; multi-leg RV had no gross edge to dilute cost against). What could: validated-spread CFDs on **less-correlated instruments** (more RV legs → cost dilutes across legs), **order-flow / microstructure**, or **alt-data**.

**(b) SWAP MEASUREMENT on demo — the single decisive open number.** TSMOM's deployable Sharpe is gated **between ~0.05 (swap-net, no-crypto) and ~0.85 (swap-free, non-deployable)** purely by real CFD overnight financing, which is currently a *proxy* (non-crypto −3.08 bps/night; **crypto swap unmeasured**). One month on an FTMO demo resolves it. If swap-net TSMOM clears ~0.7+, the TSMOM+RH book becomes a live candidate for a non-symmetric container.

**NOT a lever — a third price-signal iteration.** Cumulative honest N is already ~100; the v2 noise-floor result shows the genuine-edge dispersion is *already below chance* (0.690 < 0.845 SE). Another search only **raises N and the bar with it** — it cannot manufacture a survivor, only inflate the multiple-testing penalty. Stop searching price.

---

## 4. Honest positive — what the program DID establish (it is not nothing)

1. **A validated adversarial audit protocol** that catches stacked optimism *before* a fee is paid: clean-room regeneration (no trusting the author's engine), reproducibility + CI + monotonicity + DSR-at-honest-N gates. It turned a "0.55 PASS" into a defensible "central ~0.2, 90% CI <0.50" — institutional-grade governance.
2. **Two real, honestly-costed edges, sized correctly:** Ross Hook (deployable Sharpe ~0.44) and multi-asset TSMOM (vol-targeted full-Sharpe ~0.70; swap-net ~0.05–0.92). Real signals, characterised end-to-end — assets for a *different container*, not waste.
3. **Confirmed decorrelation.** The portfolio-construction thesis holds independently in two lines (\|ρ\|<0.07–0.20 unconditional; **worst-decile ρ negative**; co-breach ≈ independence). When a fundable edge appears, the diversification machinery is proven.
4. **A reusable powered-validation harness:** monotone two-phase first-passage MC, DSR-at-cumulative-N, a pre-registered noise-floor module, true-UTC daily + 15/30min intraday caches, and a real CFD cost model — directly reusable for the next (new-data) program.
5. **A precise, triangulated map of the wall.** Knowing *where* the ceiling is — and that it is data/universe/barrier-specific, not a signal-quality failure — is the result that redirects capital away from a losing search.

---

## 5. Recommendation

**Do-not-fund any free-price-data FTMO book.** All three lines agree: p(pass) ≈ 0.2–0.34, DSR < 0.5 at honest N, below the pre-registered noise floor. A reproducible ~0.30 is the correct, honest outcome — not an engineered 0.55.

**Reallocate effort from signal search to data + measurement.** A NEW-DATA / container program should test, in order:
1. **Measure real CFD swap on an FTMO demo (≈1 month, near-zero cost)** — resolves TSMOM's deployable Sharpe, the single decisive open number. Decision gate: swap-net TSMOM Sharpe ≥ ~0.7 → keep TSMOM; else retire it for FTMO.
2. **Evaluate the container pivot first (cheapest test):** run the *existing* TSMOM+RH book (decorrelation already confirmed) against a **trailing-DD / EOD prop spec and a personal book** where the floor is not symmetric to the target — the edges may already clear there.
3. **Source ONE genuinely-orthogonal, intraday-flat (zero-swap) edge** to replace the failed MR diversifier — requires validated-spread data on less-correlated instruments (the structural gap both audit and survivors flag). Pre-register its OOS test before any config search.
4. **Only then** consider paid order-flow / alt-data for a from-scratch orthogonal signal — the highest-cost, highest-variance lever, justified only if (1)–(3) confirm the container/diversifier thesis.

*Synthesis only; zero new backtests. Every figure cited from `research/ftmo_portfolio_audit/`, `research/ftmo_survivors_book/`, `research/ftmo_candidate_funnel/` (+`_v2/`). The ceiling is specific to this data, universe, frequencies, and the symmetric FTMO barrier — not a claim about momentum or mean-reversion in general.*

---

**2026-06-10 registry addendum — `announcement_premium`** (`data/ftmo_research/announcement_premium/`): Savor-Wilson US500 event-day premium (FOMC/CPI/NFP, close-to-close), pre-registered K1–K5 frozen before data (commit `88cc29e`) → **NO-GO, 5/5 gates fail + DSR ≈ 0**. Event-day β = −3.2 bp (t_HAC −0.28): 2021–26 drift accrues on NON-announcement days; NFP days negative; FOMC-only trace underpowered (N=38<40, L12). Cumulative trial registry: **97 → 101** (+pooled, FOMC, CPI, NFP). Side-finding: `US500_M1.csv` has a 2018-01→2021-09-13 hole (splice misattribution, MANIFEST claim wrong; backfillable from Dukascopy).
