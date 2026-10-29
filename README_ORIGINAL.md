> **Note (2026-10-29).** This is the original README of the working repository, kept as it was in August 2026. The Sharpe and account figures it shows were later reviewed; the current statement is in [proof-of-edge](https://github.com/Guillaume-Beaudouin-Git/proof-of-edge).

# Algo_claude

Systematic trading research, run solo, with one rule: **a strategy is guilty until proven
innocent, and most of them stay guilty.**

The repository holds the full record — the live trading system, the research that produced it,
and the several hundred hypotheses that were killed along the way. Negative results are kept with
the same care as positive ones, because they are the expensive part.

---

## Status — August 2026

| | |
|---|---|
| **Live** | FTMO funded account, $10 000, Swing 2-step — passed both phases in **23 days** (+10.06 % / +5.39 %) |
| **Deployed book** | 2 overnight index legs (US100, GER40 — Mon/Tue) + 1 intraday breakout (ORB) |
| **Execution** | MT5 Expert Advisor on a Linux VPS, under a watchdog, with nightly reconciliation |
| **Honest Sharpe** | **0.83** over 154 months of reconstruction — *not* the 1.91 the last 24 months show, which is in-sample |
| **Expected** | ≈ **$790–1 130** net over 2 years (median, 280 simulated cohorts), 7 withdrawals/year |

The account is small and so are the returns. That is the point: the system is a **falsification
engine** first and a money engine second.

---

## How research works here

This is the part worth reading. Five rules, each written after a specific failure.

**1. Pre-registration.** Hypothesis, signal construction, universe, metrics and **kill rules** are
frozen in a `PREREGISTRATION.md` *before the data is touched*. Kill rules are not renegotiated
after seeing results. When a verdict later needs revisiting, an **amendment** is appended — never
an edit.

**2. Measure the cost on the venue you actually trade.** A strategy was killed for months on a
spread borrowed from a different broker. Measured natively on the real account, the true cost was
**1.045 bps** round-trip where the pipeline had hardcoded **2.2**. A passive sampler now runs
inside the live EA and records the real bid/ask every minute.

**3. Read the distribution, never the maximum.** Testing hundreds of variants of one idea is not
data-mining *if the deliverable is the shape of the result distribution*. A real mechanism makes
its whole neighbourhood positive; a dead one produces a t-distribution indistinguishable from
noise. The maximum of N noisy trials is always impressive — it is compared against its own null.

**4. A matched placebo, every time.** Three separate false positives were caught this way in a
single week — including one that cleared every gate (18/18 cells at t > 2.5, positive after
costs) and turned out to be an artifact of **path-dependent position sizing**, invisible to
HAC standard errors because it lives in the sizing, not the residual.

**5. Adversarial audit.** Findings are re-derived by an independent pass whose job is to break
them. It has overturned the author's own conclusions more than once — including a claim in this
very README's earlier drafts.

### The lesson registry

Sixty numbered lessons (`_meta/lessons_registry.md`), each a verdict plus the number that earned
it. A few, to give the flavour:

- **L33** — the instrument's real cost structure decides. A backtest at 2 bps does not transfer to
  a CFD at 6.
- **L38** — regress any "structural premium" on a vol-targeted buy-and-hold of its own underlying.
  R² > 30 % means it is timing on beta, not alpha.
- **L52** — never trust a provider's field name. `ZN=F.Open` is the *previous* calendar day's
  Globex open; a field named `timestamp_utc` was in fact Paris time, which had silently left
  38.7 % of the trading session untested.
- **L59** — `delay+1` certifies the *entry* only. Re-price the exit separately: assuming exact
  stop fills moved a Sharpe from 0.99 to 0.49.

---

## What was found

Mostly nothing, and that is reported precisely.

| family | verdict | evidence |
|---|---|---|
| Intraday mean-reversion (FTMO universe) | **closed** | **1 526 cells**, Šidák threshold t > 4.15, zero survivors. Invariant across indices, FX, metals, and new crosses |
| Crypto cross-sectional | closed | β-dominance holds regardless of information coefficient |
| FX carry (G10) | closed | dead post-GFC; the 2005-07 sample carried the whole effect |
| Commodity carry on CFD | closed | both sides of the trade are uncollectable at retail cost |
| Overnight index premium | **live** | the deployed book — beta compressed by the clock, not alpha |

The intraday mean-reversion closure has a structural explanation rather than a merely empirical
one: Nagel (2012) frames reversal profits as **compensation to liquidity providers**. A retail CFD
account is the public side of that trade, paying the very spread the literature identifies as the
market maker's reward.

---

## Repository map

```
ftmo_live/            live trading system — MT5 EA, brain, supervisor, watchdog, reconciliation
strategies/           deployed strategy code
Portfolio/            sizing, risk, propfirm barrier models
data/                 immutable sources + generated caches (caches are gitignored)
PropFirms/            venue rules, verified against primary sources
_meta/                lesson registry, research inventory, roadmap
docs/                 long-form reports and the historical research journal
<AssetClass>/research/{active,archived}/    per-asset research, each with its pre-registration
```

Research folders are self-contained: pre-registration, code, results, and a report that states
the verdict and what would have changed it.

---

## Infrastructure

The live system is deliberately boring and heavily instrumented.

- **Expert Advisor** enforcing the account's barriers itself — a static floor, a daily loss limit
  on intraday equity, a circuit breaker, and a margin cap — rather than trusting the broker to
  stop it.
- **A spec chain sealed by hash.** The EA refuses to initialise if the deployed specification does
  not match the one it was compiled against.
- **Watchdog** distinguishing a genuine broker disconnection from an ordinary gap in ticks, with
  an anti-loop guard and post-restart verification.
- **Nightly reconciliation** comparing realised P&L against the model and raising an alert when
  the unexplained residual exceeds tolerance. Typical residual: **under one dollar**.
- **CI** that refuses to auto-merge anything touching live paths.

---

## Reading this repository

Start with `_meta/lessons_registry.md` — it is the compressed version of everything learned.
Then `_meta/roadmap_ftmo_2026.md` for where the work is going, and any
`research/active/*/PREREGISTRATION.md` for what a study looks like before it knows its answer.

The historical journal, superseded but kept for the record, is in
`docs/RESEARCH_JOURNAL_2026-05.md`. Several of its figures have since been corrected — the
corrections are documented rather than overwritten.
