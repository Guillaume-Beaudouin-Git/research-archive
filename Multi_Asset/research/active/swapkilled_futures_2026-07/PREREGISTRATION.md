# PRE-REGISTRATION — Swap-killed families re-examined on IBKR real-futures costs

**Date frozen:** 2026-07-15 · **Author:** quant research session (personal-account universe)
**Branch:** `claude/research-swapkilled-futures-2026-07` (worktree, off `origin/main`)
**Status:** FROZEN before any result. Any change to signal/kill-rules after a result = new N, logged.

> **This file is written and committed BEFORE running a single backtest.** Results go in
> `RESULTS_H*.md`. The spec below (signals, instruments, cost model, kill rules, gate) does not move
> once a result exists; a post-result modification is a new registered test, never an in-place edit.

---

## 0. Why this session exists (the reframe)

All prior repo research was selected under **propfirm constraints** (symmetric −10% barrier, daily cap,
min trading days, consistency cap, CFD/FTMO vehicle). Two death causes were conflated:
- **(i) the barrier** — removed on a personal IBKR account;
- **(ii) the economics** — CFD swap markup, beta-dominance, no edge — most of which *survive* on a
  personal account.

Three audits this week (2026-07-15) deflated every high-headline candidate once viewed through the
personal-account / Kelly lens:

| Strategy | Headline SR | Deflated reality | Killer |
|---|---|---|---|
| Ross Hook | 1.5–1.87 | **0.44** (deployable MTM), DSR N≥6 = 0.00 | trade-sequential / optimistic-fill inflation |
| Strategy A (crypto TSMOM) | 1.33 | **~0.6 forward**, non-stationary (bear SR −1.0, skew −4) | crypto beta, regime-dependent |
| Gold/Silver RV (3A) | 0.77 | single-leg **0.44 < B&H gold 0.60**; 2-leg RV **−0.28** | no relative-value alpha; beta remnant |

**Conclusion: the repo contains no validated stationary non-beta scalable edge.** This session hunts one
in the ONE place the propfirm lens systematically under-explored: **families whose *only* killer was the
CFD swap markup (L28/L30/L32/L36)** — which vanishes on IBKR real futures (carry is priced into the
basis, not charged as a marked-up nightly swap).

## 1. Objective & account model

- **Vehicle:** IBKR real futures (CME/CBOT micros where they exist). No CFD, no swap markup.
- **Objective:** a **stationary, non-beta edge** deployable for **growth-optimal (Kelly-fractional)
  scaling** on a DD-tolerant personal account (~€12k start, DD budget 40–50%).
- **Not** a propfirm gate. DD is a *sizing lever*, not a selection criterion.

## 2. `PERSONAL_PASS` gate (anti-artefact — every criterion mandatory, frozen)

A candidate is PROMOTED only if it clears ALL of:

1. **Beat-the-benchmark** — a directional sleeve must beat a **vol-targeted buy-&-hold of its own
   underlying** (net). Kills the beta-in-disguise that sank 3A single-leg and Strategy A.
2. **Two-sided / hedged-neutral** — edge positive on **both legs / both directions**, or genuinely
   market-neutral with *positive* alpha. Kills single-leg-beta (L25).
3. **DSR ≥ 0.70 at honest N** (Bailey-LdP, `dsr.py`), N = tests run in THIS session's family.
4. **Regime-stable** — per-regime Sharpe split; edge NOT concentrated in one bull. Report worst regime.
5. **Real-futures cost survival** — net of measured IBKR cost (§4), gross/cost ≥ 1.5 per L43 pre-flight;
   ORB-class intraday needs >3 bps gross (L33b).

**Reporting discipline (L46 honesty checklist):** one canonical ledger, measured cost, frozen spec,
full-sample regime. DSR is BLOCKING and printed in the main results table (not a footnote) — the process
failure that let the BTC month-end candidate through (2026-07) does not repeat.

## 3. Hypotheses (frozen)

### H1 — Overnight-session drift on real index futures (HIGHEST EV, best data)
- **Mechanism / prior:** index overnight (Globex) drift is a documented real gross edge
  (repo `overnight_verification_2026-06`: midweek NQ +4.9 bps/night, t=4.04). It was killed on **CFD**
  by a −3.08 bps/night swap. On the **real future** the overnight session return is captured directly
  with no swap → the killer is removed.
- **Signal:** long the underlying from RTH close → next RTH open (overnight session). Variants
  pre-registered: (a) all nights, (b) midweek only (Tue/Wed/Thu). NO further tuning.
- **Instruments:** NQ (MNQ), ES (MES), RTY (M2K), YM (MYM), DAX (FDXM), + XAU (MGC) as commodity control.
  Data: `data/overnight_research/nq_rth_daily.parquet` (NQ 2010-2026, ov/in bps precomputed) +
  `data/deep_history_utc/*_M1.csv` (US100/US500/US30/GER40/XAUUSD — build overnight from M1 RTH bounds).
- **Kill rules (frozen):** (K1) net-of-cost overnight SR < 0.5 → fail. (K2) fails PERSONAL_PASS #1
  (does not beat vol-targeted B&H of the same index) → it is beta, KILL. (K3) edge concentrated in a
  single regime (one year drives >60% of P&L) → KILL. (K4) two-sided check: the *intraday* (RTH) leg
  must NOT be the mirror that makes overnight look good by construction — report both.

### H2 — Commodity term-structure / carry on real futures (DATA-GATED)
- **Mechanism / prior:** retail-CFD commodity carry is one-sided-uncollectable (L32/L32b) because the
  short-contango leg costs −46+ bps/month in CFD swap. On real futures the roll is transacted, not
  swapped. Test whether a **backwardation-gated long / contango-gated short** basis signal survives on
  real-futures cost.
- **BLOCKER:** requires the futures **curve** (front vs deferred). Repo has continuous front-month only
  (yfinance =F). **H2 runs ONLY if** ≥2 maturities per commodity are obtainable; else DEFERRED with an
  explicit "data-gated" note. No proxy on front-month alone (would re-test TSMOM, already closed).
- **Kill rules:** (K1) no curve data → DEFER, do not fabricate. (K2) L32b already found long-only
  collectable side ≈ 0 over 19y on real data → require the *two-sided* basis edge to clear PERSONAL_PASS,
  not just significance.

### H3 — Month-end Treasury rally on real bond futures (STRONG PRIOR)
- **Mechanism / prior:** month-end index-rebalancing flow into Treasuries. Repo `b1` sleeve:
  long Treasury last 3 trading days of month, **t=4.65, 23/23 years positive, cost-immune, flow-not-beta,
  decorr −0.03** (`data/personal_book/sleeves/b1_month_end_bond_rally.md`, src skew_research/session_3).
  Never deployable under FTMO (bonds out of universe). On IBKR: **ZN / ZB / ZF futures, or TLT**.
- **Signal:** long the bond from close of T-3 (business days to month-end) to month-end close. Pre-reg
  the exact window {last 3 BD}. NO tuning of the window post-result.
- **Instruments:** ZN=F (10y), ZB=F (30y), TLT (ETF cross-check). Data: **fetch via yfinance**
  (network available) — ZN=F, ZB=F, TLT, IEF; 2002-2026.
- **Kill rules (frozen):** (K1) t_HAC (lag-6) < 2.5 on the fetched real series → fail. (K2) DSR < 0.70 at
  session-N → fail. (K3) regime split: if the effect died post-2015 (ZIRP→hiking transition) → KILL
  (L31 alpha-decay). (K4) placebo calendar: compare to random 3-day windows (matched vol) — must exceed
  placebo p95 (L49 discipline).

## 4. Cost model — IBKR real futures (measured/reference, frozen)

| Instrument | Contract | RT commission | Spread (typical) | RT cost (bps of notional) | Overnight |
|---|---|---|---|---|---|
| MNQ | micro NQ $2/pt | ~$1.0 | ~1 tick ($0.50) | ~0.7 bps | **0 swap** (carry in basis) |
| MES | micro ES $5/pt | ~$1.0 | ~1 tick ($1.25) | ~0.8 bps | 0 |
| M2K | micro RTY $5/pt | ~$1.0 | ~1 tick ($0.50) | ~0.8 bps | 0 |
| MGC | micro gold 10oz | ~$1.0 | ~1 tick ($1.00) | ~0.5 bps | 0 |
| ZN | 10y note $1000/pt | ~$1.5 | ~1 tick ($15.6) | ~0.3 bps | 0 |

Round-trip stress applied per PERSONAL_PASS #5: test at 0 / measured / 2× measured. **Contrast with the
CFD killer:** index CFD swap ≈ −1.5 to −3 bps/night (L30/L36) — the entire reason these families were
closed. Removing it is the experimental treatment.

## 5. N-tracking & integrity

- Session N starts at the current repo global ledger and increments per distinct test. Each hypothesis's
  variant count is logged in its `RESULTS_H*.md`.
- **Session close (MAIN dir, not worktree):** `python3 tools/check_register_integrity.py` before the
  closing commit (cited paths exist + git-tracked, N chain monotonic).
- No live file touched. Additive folder only. No git-HEAD ops on other sessions' branches.

## 6. Execution order

1. **H1** (best data, highest EV) — run first.
2. **H3** (strong prior, fetch ZN/TLT) — run second.
3. **H2** — only if curve data obtainable, else DEFER with note.

*Reproduce:* engines `engine_h1_overnight.py`, `engine_h3_monthend.py`; cost model this §4; gate this §2.
