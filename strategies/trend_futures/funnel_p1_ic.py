"""
Phase 1 — IC feasibility (PREREG section 9). Does a trend signal exist on the
non-crypto futures universe before any full backtest?

  Primary: pooled TSMOM IC. Build a vol-scaled, equal-weight TSMOM overlay return
           = mean_i( sign/strength of trailing signal_{i,t-1} x scaled excess ret_{i,t} ),
           HAC lag-6 t-stat of its mean (excess returns vs DTB3, L8). Several signals.
  Secondary: breakout-conditional forward payoff vs a block-shuffle placebo that
             RE-DERIVES breakout features on shuffled returns (L25).

Gate: primary |t|>2.5 PASS; 1.65-2.5 MARGINAL (proceed, DSR decisive); else with
      secondary ~ placebo -> STOP.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
DAILY = HERE / "daily"
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
RAW = Path("<HOME>/Desktop/Algo_claude/data/raw")


def load_rf_daily(index: pd.DatetimeIndex) -> pd.Series:
    f = RAW / "fred_DTB3_37358bdf84.parquet"
    df = pd.read_parquet(f)
    col = "DTB3" if "DTB3" in df.columns else df.columns[-1]
    s = df[col].copy()
    s.index = pd.to_datetime(df.index if not isinstance(df.index, pd.RangeIndex) else df.iloc[:, 0])
    s = pd.to_numeric(s, errors="coerce").dropna()
    rf = (s / 100.0 / 252.0)
    rf.index = rf.index.tz_localize(None).normalize()
    return rf.reindex(index, method="ffill").fillna(0.0)


def load_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    closes = {}
    for s in CORE:
        closes[s] = pd.read_parquet(DAILY / f"{s}.parquet")["close"]
    px = pd.DataFrame(closes).sort_index()
    px = px[px.index >= "2013-06-01"]
    ret = np.log(px).diff()
    rf = load_rf_daily(px.index)
    exc = ret.sub(rf, axis=0)                          # excess log returns
    vol = ret.rolling(63).std()                        # 63d vol (L8)
    scaled = (exc / vol).clip(-5, 5)                   # unit-vol excess returns
    return px, scaled


def hac_t(y: np.ndarray, lags: int = 6) -> tuple[float, float]:
    y = y[np.isfinite(y)]
    m = sm.OLS(y, np.ones(len(y))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.params[0]), float(m.tvalues[0])


def tsmom_overlay_t(px: pd.DataFrame, scaled: pd.DataFrame, signal_fn, start="2014-01-01"):
    sig = signal_fn(px).shift(1)                       # L1: signal at t-1
    contrib = (sig * scaled)                           # per-instrument signed scaled return
    overlay = contrib.mean(axis=1).loc[start:]         # equal-weight across instruments
    overlay = overlay.dropna()
    mean, t = hac_t(overlay.values)
    sharpe = overlay.mean() / overlay.std() * np.sqrt(252)
    return dict(mean_daily=mean, t_hac=t, sharpe=sharpe, n=len(overlay))


def sig_trail(h):
    return lambda px: np.sign(np.log(px).diff(h))
def sig_ema(span):
    return lambda px: np.sign(px - px.ewm(span=span, adjust=False).mean())
def sig_cont(h):
    # continuous vol-scaled trailing return, tanh-squashed (Strategy-A style)
    def f(px):
        r = np.log(px).diff()
        m = r.rolling(h).sum()
        v = r.rolling(h).std() * np.sqrt(h)
        return np.tanh(m / v)
    return f


def breakout_payoff(px: pd.DataFrame, scaled: pd.DataFrame, bk=20, ema=100, fwd=20, start="2014-01-01"):
    """Mean forward scaled-return in signal direction after a 20d breakout entry."""
    payoffs = []
    for s in px.columns:
        c = px[s]
        e = c.ewm(span=ema, adjust=False).mean()
        hh = c.shift(1).rolling(bk).max(); ll = c.shift(1).rolling(bk).min()
        long_e = (c > hh) & (c > e)
        short_e = (c < ll) & (c < e)
        d = long_e.astype(int) - short_e.astype(int)
        d = d[d != 0]
        fr = scaled[s].shift(-1).rolling(fwd).sum().shift(-(fwd - 1))  # next fwd-day scaled sum
        ev = (np.sign(d) * fr.reindex(d.index)).loc[start:].dropna()
        payoffs.append(ev)
    allp = pd.concat(payoffs)
    return float(allp.mean()), len(allp)


def placebo_breakout(px: pd.DataFrame, n_boot=200, block=20, seed=7, **kw):
    rng = np.random.default_rng(seed)
    rets = np.log(px).diff()
    means = []
    for _ in range(n_boot):
        shuf = {}
        for s in px.columns:
            r = rets[s].dropna().values; n = len(r); out = []
            idx = rng.integers(0, n)
            while len(out) < n:
                L = rng.geometric(1 / block)
                out.extend(r[(idx + np.arange(L)) % n]); idx = rng.integers(0, n)
            p0 = px[s].dropna().iloc[0]
            shuf[s] = pd.Series(p0 * np.exp(np.cumsum(out[:n])), index=px[s].dropna().index[:n])
        sp = pd.DataFrame(shuf)
        sret = np.log(sp).diff()
        svol = sret.rolling(63).std()
        sscaled = (sret / svol).clip(-5, 5)
        m, _ = breakout_payoff(sp, sscaled, **kw)
        means.append(m)
    return np.array(means)


def main():
    px, scaled = load_panel()
    print("=== Phase 1 primary: pooled TSMOM IC (HAC lag-6 t, excess vol-scaled, 2014-2026) ===")
    rows = []
    for name, fn in [("EMA100_sign", sig_ema(100)), ("EMA50_sign", sig_ema(50)),
                     ("trail20_sign", sig_trail(20)), ("trail60_sign", sig_trail(60)),
                     ("trail120_sign", sig_trail(120)), ("trail250_sign", sig_trail(250)),
                     ("cont60_tanh", sig_cont(60)), ("cont120_tanh", sig_cont(120))]:
        r = tsmom_overlay_t(px, scaled, fn)
        rows.append((name, r["t_hac"], r["sharpe"], r["n"]))
        print(f"  {name:14s} t_HAC={r['t_hac']:5.2f}  overlay_Sharpe={r['sharpe']:5.2f}  n={r['n']}")
    best = max(rows, key=lambda x: abs(x[1]))
    print(f"\n  best |t_HAC| = {best[1]:.2f} ({best[0]})")

    print("\n=== Phase 1 secondary: 20d breakout forward payoff vs block-shuffle placebo (L25) ===")
    actual, nev = breakout_payoff(px, scaled)
    pl = placebo_breakout(px, n_boot=200)
    pctl = float((pl < actual).mean())
    print(f"  actual mean fwd scaled-payoff={actual:.4f} (n_events={nev})")
    print(f"  placebo mean={pl.mean():.4f}  p95={np.quantile(pl,0.95):.4f}  actual percentile={pctl:.3f}")

    gate = "PASS" if abs(best[1]) > 2.5 else ("MARGINAL" if abs(best[1]) >= 1.65 else "WEAK")
    sec = "present" if pctl > 0.90 else ("absent" if pctl < 0.6 else "weak")
    verdict = "STOP" if (gate == "WEAK" and sec == "absent") else "PROCEED"
    print(f"\n  GATE primary={gate} (best t={best[1]:.2f}); secondary breakout payoff={sec} (pctile {pctl:.2f})")
    print(f"  PHASE-1 DECISION: {verdict}")


if __name__ == "__main__":
    main()
