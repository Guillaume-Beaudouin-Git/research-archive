"""Audit month-end bounce — reconstruction indépendante depuis la data brute.
Build daily feature table (cache) + verify §2 reference numbers.
"""
import sys, time
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path("<HOME>/Desktop/Algo_claude")
CSV = ROOT / "data/panels/m5_indices/binance/BTCUSD_M1.csv"
CACHE = ROOT / "outputs/audit_month_end/data/daily_features.parquet"
COST_RT = 0.00119  # 11.9 bps RT (coût implicite du rapport : brut 0.59 -> net 0.471)


def build_daily():
    t0 = time.time()
    df = pd.read_csv(CSV, usecols=["timestamp_utc", "open", "high", "low", "close"])
    df["ts"] = pd.to_datetime(df["timestamp_utc"])
    df["date"] = df["ts"].dt.normalize()
    df["hm"] = df["ts"].dt.hour * 100 + df["ts"].dt.minute
    print(f"[load] {len(df):,} rows in {time.time()-t0:.1f}s  range {df.ts.min()}..{df.ts.max()}")
    o04 = df.loc[df.hm == 400].set_index("date")["open"].rename("o04")
    o08 = df.loc[df.hm == 800].set_index("date")["open"].rename("o08")
    c1159 = df.loc[df.hm == 1159].set_index("date")["close"].rename("c1159")
    win = df.loc[(df.hm >= 800) & (df.hm <= 1159)]
    low_min = win.groupby("date")["low"].min().rename("low_min")
    high_max = win.groupby("date")["high"].max().rename("high_max")
    daily = pd.concat([o04, o08, c1159, low_min, high_max], axis=1).sort_index()
    daily.to_parquet(CACHE)
    print(f"[daily] {len(daily):,} days -> {CACHE.name}")
    return daily


def last_friday_dates(idx):
    fri = pd.Series(idx[idx.dayofweek == 4])
    key = fri.dt.year * 100 + fri.dt.month
    return set(fri.groupby(key).max().values)


def hac_t(x, lags=6):
    x = np.asarray(x, float)
    res = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.tvalues[0])


def stats_block(net, gross, mae, label):
    N = len(net)
    mean_net = net.mean(); sd = net.std(ddof=1); sr = mean_net / sd
    wr_net = (net > 0).mean(); wr_gross = (gross > 0).mean()
    wins = net[net > 0].mean(); losses = -net[net < 0].mean()
    wl = wins / losses if losses > 0 else np.nan
    print(f"\n=== {label} ===")
    print(f"N={N}")
    print(f"mean gross = {gross.mean()*100:+.3f}%   mean net(@11.9bps) = {mean_net*100:+.3f}%")
    print(f"sigma net/trade = {sd*100:.3f}%   SR/trade = {sr:.3f}   SR_ann(√8) = {sr*np.sqrt(8):.2f}")
    print(f"t plain = {mean_net/(sd/np.sqrt(N)):.2f}   t HAC(6) = {hac_t(net):.2f}")
    print(f"WR net = {wr_net:.3f}   WR gross = {wr_gross:.3f}   W/L(net) = {wl:.2f}")
    print(f"MAE mean = {mae.mean()*100:.3f}%   MAE worst = {mae.min()*100:.3f}%   best gross = {gross.max()*100:+.3f}%")
    return dict(N=N, mean_net=mean_net, sd=sd, sr=sr, t_hac=hac_t(net),
                skew=float(pd.Series(net).skew()), kurt=float(pd.Series(net).kurt()+3))


if __name__ == "__main__":
    daily = pd.read_parquet(CACHE) if CACHE.exists() and "--rebuild" not in sys.argv else build_daily()
    daily.index = pd.to_datetime(daily.index)
    lf = last_friday_dates(daily.index)
    d = daily.dropna(subset=["o04", "o08", "c1159", "low_min"]).copy()
    d["is_last_fri"] = d.index.isin(lf)
    d["pre"] = d.o08 / d.o04 - 1
    d["gross"] = d.c1159 / d.o08 - 1
    d["mae"] = d.low_min / d.o08 - 1
    d["net"] = d.gross - COST_RT
    d["year"] = d.index.year

    # SURVIVOR: last Friday, pre<0, 2023+
    s = d[d.is_last_fri & (d.pre < 0) & (d.year >= 2023)]
    st = stats_block(s.net, s.gross, s.mae, "SURVIVOR last-Fri pre<0 2023+")
    print("\nTrade dates:", [str(x.date()) for x in s.index])
    # save survivor trades for TEST1/TEST2 reuse
    s[["o04", "o08", "c1159", "low_min", "pre", "gross", "mae", "net"]].to_parquet(
        ROOT / "outputs/audit_month_end/data/survivor_trades.parquet")

    # sanity: pre>=0 last-Fri (should be excluded / weaker), and full-sample last-Fri pre<0
    print("\n--- context ---")
    allpre = d[d.is_last_fri & (d.year >= 2023)]
    print(f"last-Fri 2023+ total (any pre): N={len(allpre)}  of which pre<0: {int((allpre.pre<0).sum())}")
    pre2022 = d[d.is_last_fri & (d.pre < 0) & (d.year < 2022)]
    print(f"last-Fri pre<0 PRE-2022: N={len(pre2022)} mean net={pre2022.net.mean()*100:+.2f}%")
