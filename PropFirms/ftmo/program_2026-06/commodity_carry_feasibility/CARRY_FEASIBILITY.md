# Commodity-carry IC feasibility gate — VERDICT: **FAIL** (closed cheaply, no backtest run)

**Date:** 2026-06-08 · **Task:** gate the L37 commodity-carry/backwardation thesis with an IC test
*before* any backtest. **No backtest, no p(pass), no parameter search; READ-ONLY on source data.**
**n_tests consumed: 0.**

## TL;DR

The gate **FAILS at Question 1** — and, decisively, **this angle is NOT untested**: it was already run
with *superior* data (a real deferred contract) and is a **documented NO-GO**. Two independent reasons,
either of which closes it:

1. **No term structure on disk.** The 13 commodity series in `data/deep_history_utc/` are single-price
   Dukascopy **cash CFDs** (`LIGHTCMDUSD`/`BRENTCMDUSD`/`GASCMDUSD`/…) — one price per instrument, the roll
   embedded in broker swap, **no F1/F2, no deferred contract**. The yfinance set in `data/raw/` (`CL=F`,
   `BZ=F`, `NG=F`, `HG=F`…) is **front-month-continuous only** — also no deferred leg. You **cannot measure
   roll-yield/backwardation** (a term-structure slope) from a single price path. A momentum/spot stand-in is
   **not carry** (and is the proven-exhausted price-momentum box) → per the hard rule, **FAIL rather than
   fabricate a term structure.**
2. **Already tested → NO-GO.** `data/ftmo_research/commod_carry_makeorbreak.md` ran exactly this gate with a
   **real CLZ26 deferred contract** for the historical basis: the static swap-snapshot carry (Sharpe +0.46)
   was **hindsight**; the causal point-in-time basis signal (T-1) gives **Sharpe −1.15, t = −5.18,
   −19.5%/yr, negative every sub-period** (it doesn't decay, it **inverts**); it **fails the 2020
   contango/negative-price tail** (L31); it is **one-sided-uncollectable** on retail CFDs (L32); and it is
   **77% oil-concentrated**. The thesis's central hook ("the swap killer inverts for backwardated
   commodities") is true **only in the current snapshot regime** and collapses dynamically.

The task's framing — "the only **untested** orthogonal angle" — is **outdated**: it is tested and closed.

---

## Q1 — Carry-proxy existence  → **FAIL** (STOP here per the gate's own rule)

**What's on disk (my own check, read-only):**
- `data/deep_history_utc/{USOIL,UKOIL,NGAS,COPPER,XAGUSD,SUGAR,COCOA,COFFEE,SOYBEAN,COTTON,OJUICE,DIESEL,
  XAUUSD}_M1.csv` — Dukascopy CFD codes per `audit-fetch-B/MANIFEST_commodities.md`: `LIGHTCMDUSD`,
  `BRENTCMDUSD`, `GASCMDUSD`, `COPPERCMDUSD`, etc. **OHLC = a single BID price series; no second contract,
  no expiry column, no roll markers.** Spreads `ECN_RAW_UNCALIBRATED` / silver gold-proxied (MANIFEST §⚠).
- `data/raw/yf_*=F_1d_*.parquet` — yfinance **front-month continuous** futures (`CL/BZ/NG/HG/SI/GC/KC/SB/
  CC/CT/OJ/ZS/HO/RB…`). yfinance `=F` returns the active front-month only — **no deferred (F2) leg**.

**Therefore a roll-yield / backwardation slope cannot be computed from on-disk data** (it is by definition
F1-vs-F2, and only F1 exists). The candidate proxies and why each is rejected:

| Proxy | Verdict | Why |
|---|---|---|
| Nearby vs deferred (F1/F2) | **unavailable** | no deferred contract anywhere on disk |
| Spot vs front-future basis | **unavailable** | no separate spot+future pair (CFD *is* the front-month track) |
| Static swap snapshot (`ftmo_specs_full.csv`) | **not a signal** | a single 2024-25 point, not a time series → can't lag/IC-test it; **and it is exactly the hindsight artifact** the prior work showed inverts dynamically |
| Momentum/trend stand-in | **rejected** | momentum ≠ carry (Koijen 2018); and it is the proven-exhausted free-price-momentum box (would re-test a killed edge, N-inflating) |
| NGAS seasonal curve | **rejected** | imposing a known seasonal shape = fabricating a term structure; single-instrument |

**The one genuinely informative on-disk datum** — the static swap snapshot — *does* confirm L37 directionally
**for today**: `USOIL.cash swap_long = +36.55`, `UKOIL.cash = +27.62` (positive = a **credit** to longs =
backwardation), vs `SOYBEAN.c −39.12`, `COCOA.c −15.52` (negative = contango/cost). So in the **current
regime** holding long oil earns carry, exactly as the thesis claims. But a single snapshot **cannot** seed a
causal historical IC test, and (Q4) the regime is not stable. → **Gate fails at Q1; STOP.**

---

## Q2–Q5 — already answered by the prior gate (with *real* basis data we no longer hold)

I did **not** re-run these (no signal survives Q1, and re-deriving with a weaker proxy would fabricate a term
structure). The prior gate `commod_carry_makeorbreak.md` answered each — and failed all:

- **Q2 Signal (causal):** point-in-time basis sign (long backwardation / short contango), **T-1 lagged**,
  monthly rotation, built against a **real CLZ26 deferred contract**. ✓ built — then killed downstream.
- **Q3 IC test:** static (snapshot) Sharpe **+0.46, t=1.92** → dynamic (historical basis) Sharpe **−1.15,
  t=−5.18**, **negative every sub-period** (2006-12 −1.72 / 2013-19 −1.03 / 2020-26 −0.68). The HAC-class
  t-stat is hugely negative — it fails the **t>2.5** gate with the **wrong sign**. The +0.46 was the recent
  oil-backwardation regime projected onto 20 years that were **contango 57% of the time**.
- **Q4 Tail test (L31, mandatory):** the **2020 contango + negative-price COVID crash** is precisely where a
  static-long-backwardation bet is **long into the crash** — the dominant loss. The edge exists only in the
  recent (2022-25) backwardation regime → **decayed/regime-bound**, fails the tail.
- **Q5 Cost sanity / collectability (L32):** the short-contango leg (needed 57% of history) costs **−46 to
  −64 %/yr** in retail-CFD swap (short-oil swap −17.47 bps/night). **Commodity carry on retail CFDs is
  one-sided-uncollectable** — the convenience yield that rewards being *long* backwardated oil makes shorting
  contango brutally expensive. The "+50% ECN-spread stress" is moot: the edge is negative *before* spread.
- **Attribution:** **77% of carry P&L is oil** — a levered bet on the oil term structure "in carry costume,"
  with the 2020 curve-flip as a fat left tail.

**Prior verdict:** *Commodity carry/basis (FTMO CFD) — NO-GO.* The residual (seasonality 0.30 + TSMOM 0.12 ≈
0.26, p~48%) **ties the ~50% incumbent, does not beat it.** Full battery explicitly **not warranted**.

---

## Honest limitations & corrections

- **Prior primary artifacts are gone:** `outputs/basis_oil.parquet` and `commod_daily.parquet` (cited by the
  prior report) are **no longer on disk** — so the −1.15 / t=−5.18 numbers are **cited from the documented
  report, not independently re-verified** here. I *did* independently confirm the two load-bearing facts the
  conclusion rests on: (a) no term structure exists on disk (so a fresh gate can't even start), and (b) the
  swap snapshot confirms current backwardation but is a single point.
- **"L37" is mislabeled in the task:** L37 in `STRATEGY_RESEARCH_LOG.md` is a *filter-sanity* lesson (cosmetic
  conditional filters), **not** the commodity-carry-pays-roll claim. The substantive, correctly-attributed
  lessons from this thread are **L31** (regime-dependent carry → mandatory tail test) and **L32**
  (one-sided-uncollectable carry on retail CFDs) — both of which this prior work *generated*.
- **Spread caveat moot:** the ECN_RAW_UNCALIBRATED / +50%-spread-stress concern never binds — the signal is
  negative pre-cost. **Do NOT calibrate MT5 commodity spreads on demo** (the gate's own precondition: only if
  PASS). Gate FAILED → no demo calibration.

## Recommendation

**Close the L37 commodity-carry angle. FAIL.** Do not spend the full battery; do not fetch/calibrate MT5
spreads. Reasons, ordered: (1) the on-disk data **physically cannot** express a carry signal (no term
structure); (2) the angle is **already a documented NO-GO** with better data — the carry *inverts* out of the
current snapshot, fails the 2020 tail, and is one-sided-uncollectable on retail CFDs. The current-regime
backwardation is real but is a **directional long-oil tailwind**, not a systematic two-sided carry edge — and
the directional leg is itself the proven-exhausted price box. **Re-opening would require a genuine historical
term-structure dataset (paid deferred-futures curves), not free CFD/spot** — i.e. it is not a zero-marginal-
cost test, contrary to the premise. A clean, cheap close.
