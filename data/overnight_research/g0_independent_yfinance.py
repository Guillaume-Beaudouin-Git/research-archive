"""G0 — Independent falsification test, OUT of the Cowork pipeline.

Downloads QQQ + ^NDX daily from yfinance 2010-2026.
Computes overnight (open[t]/close[t-1]-1) vs intraday (close[t]/open[t]-1).
Reports mean (bps), Newey-West HAC t-stat (lag 6), per-weekday split.

Does NOT import verify_overnight.py. Independently coded.
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm

WD = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def hac_tstat(x: np.ndarray, lag: int = 6) -> tuple[float, float]:
    """Mean and HAC Newey-West t-stat (no autocorr correction = same as basic but robust)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 30:
        return np.nan, np.nan
    X = np.ones((len(x), 1))
    res = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    mu = float(res.params[0])
    se = float(res.bse[0])
    return mu, mu / se if se > 0 else np.nan


def analyze(ticker: str, start: str = "2010-01-01", end: str = "2026-06-03") -> dict:
    print(f"\n{'='*72}\nTICKER: {ticker}  ({start} → {end})\n{'='*72}")
    raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw[["Open", "Close"]].dropna().copy()
    df.columns = ["o", "c"]
    df.index = pd.to_datetime(df.index)
    df["pc"] = df["c"].shift(1)
    df["ov_bps"] = (df["o"] / df["pc"] - 1) * 1e4
    df["in_bps"] = (df["c"] / df["o"] - 1) * 1e4
    df["tot_bps"] = (df["c"] / df["pc"] - 1) * 1e4
    df["wd"] = df.index.weekday
    df["yr"] = df.index.year
    df = df.dropna(subset=["ov_bps"])

    rows = []
    for col in ["ov_bps", "in_bps", "tot_bps"]:
        label = {"ov_bps": "OVERNIGHT", "in_bps": "INTRADAY", "tot_bps": "TOTAL (close→close)"}[col]
        print(f"\n--- {label} (bps/day) — weekday = OPEN day ---")
        print(f"{'wd':5s}{'n':>7s}{'mean':>10s}{'t_HAC6':>10s}{'IN<2019':>10s}{'OOS≥2019':>10s}")
        for wd in range(5):
            s = df[df.wd == wd][col].values
            if len(s) < 30:
                continue
            mu, t = hac_tstat(s, lag=6)
            ins = df[(df.wd == wd) & (df.yr < 2019)][col].mean()
            oos = df[(df.wd == wd) & (df.yr >= 2019)][col].mean()
            print(f"{WD[wd]:5s}{len(s):7d}{mu:10.3f}{t:10.2f}{ins:10.3f}{oos:10.3f}")
            rows.append({"ticker": ticker, "metric": label, "wd": WD[wd], "n": len(s),
                         "mean_bps": mu, "t_hac6": t, "in_pre2019": ins, "oos_2019plus": oos})
        s = df[col].values
        mu, t = hac_tstat(s, lag=6)
        ins = df[df.yr < 2019][col].mean()
        oos = df[df.yr >= 2019][col].mean()
        print(f"{'ALL':5s}{len(s):7d}{mu:10.3f}{t:10.2f}{ins:10.3f}{oos:10.3f}")
        rows.append({"ticker": ticker, "metric": label, "wd": "ALL", "n": len(s),
                     "mean_bps": mu, "t_hac6": t, "in_pre2019": ins, "oos_2019plus": oos})

    # Annual positive years for overnight
    yr = df.groupby("yr")["ov_bps"].mean()
    pos_years = (yr > 0).sum()
    print(f"\novernight years positive: {pos_years}/{len(yr)}  worst {yr.min():.2f} bps  best {yr.max():.2f} bps")

    # Gap tail (overnight midweek = Tue+Wed open day, i.e. Mon-night + Tue-night holds)
    midweek = df[df.wd.isin([1, 2])]["ov_bps"].values
    if len(midweek) > 100:
        print(f"\nMidweek overnight tail (n={len(midweek)}):")
        print(f"  p1 ={np.percentile(midweek, 1):.1f} bps   p5 ={np.percentile(midweek, 5):.1f}")
        print(f"  p50={np.percentile(midweek, 50):.1f}    p95={np.percentile(midweek, 95):.1f}")
        print(f"  worst={midweek.min():.1f} bps   best={midweek.max():.1f} bps   std={midweek.std():.1f}")

    return {"ticker": ticker, "df": df, "rows": rows}


if __name__ == "__main__":
    out_rows = []
    for tkr in ["QQQ", "^NDX", "SPY", "^GSPC"]:
        try:
            r = analyze(tkr)
            out_rows.extend(r["rows"])
        except Exception as e:
            print(f"FAIL {tkr}: {e}")
    pd.DataFrame(out_rows).to_csv(
        "<HOME>/Desktop/Algo_claude/data/overnight_research/g0_yfinance_summary.csv",
        index=False,
    )
    print("\nSaved: data/overnight_research/g0_yfinance_summary.csv")
