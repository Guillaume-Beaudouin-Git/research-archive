# Commodities — FTMO deep-dive (the literature's best bet — battery + honest correction)

**Why here:** the literature points to commodities for a **two-sided, all-regime, cost-surviving** edge —
the property that killed every FX/index/crypto family (all one-sided beta). Commodities have **no secular
drift** and a documented two-sided **carry/basis** premium (Koijen et al. 2018; Gorton-Rouwenhorst 2006;
Novy-Marx-Velikov 2016: low-turnover survives costs).

**Universe (your FTMO platform, verified):** XAGUSD, XAUUSD, XPDUSD, XPTUSD, USOIL, UKOIL, COCOA, COFFEE,
SOYBEAN, WHEAT. Data: yfinance continuous front-month 2005–2026; carry from your real commodity swaps.
Protocol: signal T-1, monthly rebalance, two-sided, **real per-commodity CFD costs**, walk-forward, DSR,
**and a dynamic-basis robustness check**.

---

## Verdict (corrected after the dynamic-basis test)

> **Commodities is the right asset class — the signals are genuinely two-sided and OOS-stable (a first in the arc) — but it TIES the ~50 % incumbent, it does not beat it.** The honest, dynamic-safe book (momentum + seasonality, **real costs**) is **Sharpe 0.26, walk-forward stable (train 0.28 ≈ test 0.25), p(pass) ≈ 48 %.** Too weak to beat ORB+floor.
>
> **The carry/basis leg that briefly showed a "beat" (combined Sharpe 0.52, p57 %) was largely HINDSIGHT and is retracted.** It used *today's* static swap snapshot (oil backwardated *now*). The dynamic-basis check shows today's "long oil" sign matches the historical time-varying basis only **38 % of the time** (oil was mostly *contango* over 2006–2026), and the ETF-roll dynamic carry is **negative (Sharpe −0.81)**. The static carry does not survive a time-varying basis.
>
> **Open, decisive:** a *proper* dynamic carry needs the futures **term structure** (2nd-month contracts), which yfinance can serve per-contract but requires a multi-contract splice (a real data build, not done here). Until that confirms or kills a dynamic carry, **commodities ties, not beats.**

This is the discipline doing its job: the pre-filter surfaced a candidate that looked like it beat ~50 %;
the dynamic-basis robustness check caught the hindsight before any capital risk.

---

## What survives (honest, dynamic-safe)

**Momentum + seasonality (no carry), net of real per-commodity costs** (metals 4–7, energy 8, softs 12–20 bps RT):

| metric | value |
|---|---:|
| ann | +1.8 %/yr |
| Sharpe | **0.26** |
| t-stat | 1.14 |
| walk-forward | **train 0.28 ≈ test 0.25 (stable)** |
| FTMO p(pass) | **48 % (L2), 47 % (L3)** — ties incumbent |

- **Seasonality** (expanding-OOS, two-sided): Sharpe 0.30, positive every sub-period — the one genuinely OOS-stable signal in the whole arc.
- **TS-momentum** (vol-scaled): Sharpe 0.12–0.25, decayed mid-decade — weak.
- Both are **real, two-sided, not beta** — a qualitative win over every prior family — but **Sharpe 0.26 combined only ties ~50 %.**

## What does NOT survive (the carry/basis)

The carry/basis is the literature's strongest commodity signal, but I can only rank it from **today's**
swap snapshot, and that fails the dynamic test:

| commodity | static sign (today) | dynamic-basis agreement | note |
|---|---|---:|---|
| USOIL | long (backwardated now) | **38 %** | oil was mostly **contango** 2006–2026 |
| WHEAT | short (contango) | 89 % | structural contango holds |
| XPD/XAG | short | ~78 % | metals structurally contango |

- **Static carry (hindsight): Sharpe 0.46** — but it projects today's oil backwardation onto 20 years where oil was usually contango.
- **ETF-roll dynamic carry (USO/SLV/PALL/WEAT): Sharpe −0.81 (t=−3.52)** — the time-varying basis *inverts* the result (imperfect proxy, N=4, but unambiguous direction).
- ⇒ the carry leg is **unconfirmed (leaning hindsight-artifact)**; it cannot be counted until tested on a proper dynamic term structure.

## Battery results (on the dynamic-safe book)

- **Real costs:** survives (Sharpe 0.26 net) — softs are expensive (12–20 bps) but monthly/low-turnover keeps the drag manageable (Novy-Marx-Velikov).
- **Walk-forward:** **stable** (train 0.28 ≈ test 0.25) — unlike the carry-inflated version (test 0.68 ≫ train 0.35, the tell-tale of recent-data hindsight).
- **DSR:** the *carry-inflated* combo passed (0.50 vs 0.37 bar); the **honest book (0.26) does not clear DSR** — consistent with "real but too weak."

## Bottom line

The literature was right about the **asset class**: commodities is the only place in the arc where the
signals are **two-sided and OOS-stable** (momentum + seasonality), not one-sided beta — a real qualitative
break. But honestly, **momentum + seasonality alone tie the ~50 % incumbent (Sharpe 0.26, p(pass) ~48 %)**
— they don't beat it. The **carry/basis** that would beat it is **not confirmed**: the static snapshot is
hindsight, and the dynamic proxy inverts it. **The one decisive remaining test is a dynamic carry on the
real futures term structure (2nd-month splice).** If that confirms a dynamic carry Sharpe ~0.4+, the combo
beats the incumbent; the current evidence says it likely won't.

### Next step (the only thing that settles it)
Build the **2nd-month continuous** (splice deferred yfinance contracts, ~per-commodity) → compute the
**time-varying basis** → re-rank the carry monthly → re-run two-sided + DSR + p(pass). This is a data
build (many contract fetches), but it is the single experiment that confirms or kills the commodity carry
for FTMO.

### Artifacts
- `outputs/commod_daily.parquet`, `ftmo_specs_full.csv` (real swaps), `panels/commodity_panel.csv` (ETFs for the dynamic-basis proxy). Code inline.
- Sources: Koijen-Moskowitz-Pedersen-Vrugt (2018); Gorton-Rouwenhorst (2006); Novy-Marx-Velikov (2016).
