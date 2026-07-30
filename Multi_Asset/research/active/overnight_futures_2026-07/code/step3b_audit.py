"""Step 3b — audit of the GOLD improvement. Pre-registered scepticism: a sleeve that
looks better than its archived self is guilty until proven innocent.

1. Reproduce the ARCHIVED spec exactly (its own code path) -> do we recover SR ~1.10?
2. Decompose my number into its four differences, one at a time:
     archived -> exchange clock -> M1 entry price -> winsorisation
3. Year-by-year: does the documented 2018-2019 dead-edge regime still appear?
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import (OUT, REPO, SLEEVES, hac_t, load_h1, max_dd, obs_per_year, sharpe,
                    us_dst, vol_target, window_returns)
from step3_performance import tradable_series

sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import stats as S  # noqa: E402
from gold_research import strategy_overnight as SO  # noqa: E402

# ------------------------------------------------- 1. reproduce the archived number
h1 = load_h1("XAUUSD")
h1 = h1[h1.index >= pd.Timestamp("2007-01-01")]
print("=== 1. archived spec, archived code path (ASIA_23_8, UTC-fixed) ===")
for sp in (0.0, 1.0, 1.5, 2.0):
    net = SO.backtest(h1, spread_bps=sp, swap_bps=0.0)["net"]
    print(f"  spread {sp:>4}bp : N={len(net)}  SR(sqrt252)={S.sharpe_ratio(net.to_numpy(), 252):.3f}"
          f"  SR(obs/yr)={sharpe(net):.3f}  maxDD={100*max_dd(net):.1f}%  "
          f"mean={1e4*net.mean():.2f}bp")
print("  reference published: net@1.5bp Sharpe 1.10 (report) / 1.18 (code docstring),"
      " maxDD -19.4% / -15.6%")

# --------------------------------------------------------- 2. one-at-a-time ladder
print("\n=== 2. difference ladder (gross, vol-targeted, no cost) ===")
rows = []


def block(name, win, note):
    pos = vol_target(win)
    g = (pos * win).dropna()
    g = g[g.index >= win.index[20]]
    mu, t = hac_t(g)
    rows.append(dict(step=name, N=len(g), obs_yr=round(obs_per_year(g), 1),
                     mean_bps=round(1e4 * g.mean(), 3), SR=round(sharpe(g), 3),
                     t_hac=round(t, 2), maxDD_pct=round(100 * max_dd(g), 1),
                     vol_ann=round(100 * g.std(ddof=1) * np.sqrt(obs_per_year(g)), 2),
                     note=note))
    return g


wA = window_returns(h1, 23, 8, anchor="utc")
block("0_archived_specA_H1", wA, "UTC clock, H1 close-to-close, halt gap included")
wB = window_returns(h1, 23, 8, anchor="exchange")
block("1_+exchange_clock_H1", wB, "exchange clock, H1, halt gap still included")

raw = tradable_series.__wrapped__("GOLD") if hasattr(tradable_series, "__wrapped__") \
    else None


def m1_series(winsor: bool):
    from step1c_gap_decomposition import REOPEN_ET, WINDOW_HOURS, load_m1, price_at
    sp = SLEEVES["GOLD"]
    df = load_m1(sp["cfd"], sp["sample_start"])
    ts = pd.DatetimeIndex(df["ts"])
    et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")
    keys, vals = et.asi8, df["close"].to_numpy()
    ro, hours = REOPEN_ET["GOLD"], WINDOW_HOURS["GOLD"]
    sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sess + pd.Timedelta(hours=ro)).asi8
    H = np.int64(3_600_000_000_000)
    p0 = price_at(vals, keys, base, "first", 20)
    p1 = price_at(vals, keys, base + hours * H, "last", 30)
    s = pd.Series(np.log(p1 / p0), index=sess).dropna()
    s = s[np.isfinite(s.to_numpy())]
    if winsor:
        lo, hi = s.quantile([0.005, 0.995])
        s = s.clip(lo, hi)
    return s


w_m1_raw = m1_series(False)
block("2_+M1_entry_gapExcluded", w_m1_raw, "exchange clock, M1 prices, halt gap EXCLUDED, NO winsor")
w_m1_win = m1_series(True)
g_final = block("3_+winsorise_0.5/99.5", w_m1_win, "as reported in step 3")

lad = pd.DataFrame(rows)
pd.set_option("display.width", 300, "display.max_columns", 30)
print(lad.to_string(index=False))
lad.to_csv(OUT / "step3b_ladder.csv", index=False)

# ------------------------------------------------------------ 3. year-by-year
print("\n=== 3. year-by-year (gross, vol-targeted): does the 2018-19 drought survive? ===")
yr = []
for label, w in (("archived_specA", wA), ("specB_M1_gapExcl", w_m1_win)):
    pos = vol_target(w)
    g = (pos * w).dropna()
    for y, s in g.groupby(g.index.year):
        if len(s) < 50:
            continue
        yr.append(dict(spec=label, year=int(y), N=len(s),
                       mean_bps=round(1e4 * s.mean(), 2), SR=round(sharpe(s), 2)))
Y = pd.DataFrame(yr).pivot(index="year", columns="spec", values=["mean_bps", "SR"])
print(Y.to_string())
Y.to_csv(OUT / "step3b_yearly.csv")

# correlation of the two specs' daily series
common = wA.index.intersection(w_m1_win.index)
print(f"\ncorr(archived specA, specB_M1) on {len(common)} common days = "
      f"{np.corrcoef(wA.reindex(common), w_m1_win.reindex(common))[0,1]:.3f}")
