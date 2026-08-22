#!/usr/bin/env python3
"""
audnzd_engine.py — Idea 1A: AUD/NZD single-leg mean-reversion.
Step 1: data + mean-reversion confirmation gate + causal OU signal + single-leg
backtest (R-multiples) + 1-bar delay test + by-year/OOS. Writes the canonical
trade ledger for the barrier sim (step 2).

Strictly causal: fair value f_t & sigma_t use a rolling window ending at t;
the ENTRY fills at the NEXT close (t+1) — no same-bar look-ahead. Delay test
fills at t+2.
"""
from __future__ import annotations
import glob, json, os
import numpy as np, pandas as pd

DATA = "/sessions/affectionate-epic-faraday/mnt/data"
OUT = "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/statarb_audnzd"
os.makedirs(OUT, exist_ok=True)

# ---- params (frozen baseline; grid swept later) ----
W = 60          # fair-value / sigma window (days)
Z_IN = 2.0      # entry threshold
Z_STOP = 3.0    # hard stop threshold
T_MAX = 20      # time stop (days)
COST_PIPS = 2.0 # round-trip cross spread (pips)
SWAP_BPS_DAY = 0.3
FILL_LAG = 1    # baseline: enter at next close


# ---------- data ----------
def load_audnzd() -> pd.DataFrame:
    a = pd.read_parquet(glob.glob(f"{DATA}/raw/yf_AUDUSD=X_1d_*.parquet")[0])["close"]
    n = pd.read_parquet(glob.glob(f"{DATA}/raw/yf_NZDUSD=X_1d_*.parquet")[0])["close"]
    df = pd.DataFrame({"AUDUSD": a, "NZDUSD": n}).dropna()
    df["AUDNZD"] = df["AUDUSD"] / df["NZDUSD"]
    df = df[(df["AUDNZD"] > 0.8) & (df["AUDNZD"] < 1.3)]   # sanity clip (range guard)
    df["logpx"] = np.log(df["AUDNZD"])
    return df


# ---------- mean-reversion confirmation ----------
def hurst(x: np.ndarray, lags=range(2, 40)) -> float:
    x = np.asarray(x, float)
    tau = [np.sqrt(np.std(x[l:] - x[:-l])) for l in lags]
    m = np.polyfit(np.log(list(lags)), np.log(tau), 1)[0]
    return float(m * 2.0)


def variance_ratio(r: np.ndarray, q: int) -> float:
    r = r[~np.isnan(r)]
    n = len(r)
    var1 = r.var(ddof=1)
    rq = np.convolve(r, np.ones(q), "valid")
    return float(rq.var(ddof=1) / (q * var1))


def half_life(dev: np.ndarray) -> float:
    dev = dev[~np.isnan(dev)]
    y = dev[1:]
    x = dev[:-1]
    b = np.polyfit(x, y - x, 1)[0]          # Δdev = a + b·dev_{t-1}
    return float(-np.log(2) / b) if b < 0 else float("inf")


def confirm_reversion(df: pd.DataFrame) -> dict:
    lp = df["logpx"].values
    r = np.diff(lp)
    dev = (df["logpx"] - df["logpx"].rolling(W).mean()).dropna().values
    return dict(hurst_logpx=round(hurst(lp), 3),
                VR5=round(variance_ratio(r, 5), 3), VR10=round(variance_ratio(r, 10), 3),
                half_life_dev_days=round(half_life(dev), 1),
                interpretation="H<0.5 & VR<1 & finite half-life => mean-reverting")


# ---------- causal signal ----------
def build_signal(df: pd.DataFrame, w=W) -> pd.DataFrame:
    lp = df["logpx"]
    f = lp.rolling(w).mean()                 # includes t (decision at close t)
    sig = (lp - f).rolling(w).std()
    z = (lp - f) / sig
    out = df.copy()
    out["f"], out["sigma"], out["z"] = f, sig, z
    return out.dropna(subset=["z"])


# ---------- single-leg backtest -> R-multiple trades ----------
def backtest(sig: pd.DataFrame, z_in=Z_IN, z_stop=Z_STOP, t_max=T_MAX,
             cost_pips=COST_PIPS, swap_bps_day=SWAP_BPS_DAY, fill_lag=FILL_LAG,
             price_col="AUDNZD") -> pd.DataFrame:
    px = sig[price_col].values
    z = sig["z"].values
    sg = sig["sigma"].values
    dates = sig.index
    n = len(sig)
    trades = []
    i = 0
    while i < n - fill_lag - 1:
        direction = 0
        if z[i] <= -z_in:
            direction = 1
        elif z[i] >= z_in:
            direction = -1
        if direction == 0:
            i += 1
            continue
        # fill at t+fill_lag close (no same-bar look-ahead)
        e = i + fill_lag
        entry_px = px[e]
        z_entry = z[i]
        sigma_entry = sg[i]
        # risk distance in log-price to the hard stop (entry-time sigma)
        risk_log = (z_stop - abs(z_entry)) * sigma_entry
        if risk_log <= 0:
            i += 1
            continue
        # walk forward to exit
        j = e + 1
        exit_px, exit_reason, exit_j = px[-1], "end", n - 1
        while j < n:
            zj = z[j]
            held = j - e
            if direction == 1 and zj >= 0:
                exit_px, exit_reason, exit_j = px[j], "target", j; break
            if direction == -1 and zj <= 0:
                exit_px, exit_reason, exit_j = px[j], "target", j; break
            if (direction == 1 and zj <= -z_stop) or (direction == -1 and zj >= z_stop):
                exit_px, exit_reason, exit_j = px[j], "stop", j; break
            if held >= t_max:
                exit_px, exit_reason, exit_j = px[j], "time", j; break
            j += 1
        days = exit_j - e
        gross_log = direction * np.log(exit_px / entry_px)
        cost_log = (cost_pips * 1e-4 / entry_px) + (swap_bps_day * 1e-4 * max(days, 0))
        net_ret = gross_log - cost_log
        R = net_ret / risk_log
        trades.append(dict(entry_date=dates[e], exit_date=dates[exit_j], direction=direction,
                           z_entry=round(float(z_entry), 2), days=int(days), reason=exit_reason,
                           gross_ret=float(gross_log), net_ret=float(net_ret), R=float(R)))
        i = exit_j + 1     # no overlapping positions (single leg, one at a time)
    return pd.DataFrame(trades)


def trade_stats(tr: pd.DataFrame, label="") -> dict:
    R = tr["R"].values
    if len(R) == 0:
        return {"label": label, "n": 0}
    wins = R[R > 0]
    s = R.std(ddof=1)
    return dict(label=label, n_trades=int(len(R)), mean_R=round(float(R.mean()), 4),
                win_rate=round(float((R > 0).mean()), 3),
                avg_win=round(float(wins.mean()), 2) if len(wins) else 0.0,
                avg_loss=round(float(R[R <= 0].mean()), 2) if (R <= 0).any() else 0.0,
                skew=round(float(((R - R.mean()) ** 3).mean() / s ** 3), 2) if s > 0 else None,
                sharpe_per_trade=round(float(R.mean() / s), 3) if s > 0 else None,
                med_days=int(np.median(tr["days"])), tot_R=round(float(R.sum()), 1))


# ---------- run ----------
def main():
    df = load_audnzd()
    rev = confirm_reversion(df)
    sig = build_signal(df)
    base = backtest(sig, fill_lag=1)
    delay = backtest(sig, fill_lag=2)        # 1-bar delay test
    base.to_csv(f"{OUT}/trades_ledger.csv", index=False)

    print("=" * 64)
    print(f"AUD/NZD daily | {df.index.min().date()} .. {df.index.max().date()} | {len(df)} days")
    print("MEAN-REVERSION GATE:", json.dumps(rev))
    print("=" * 64)
    print("BACKTEST baseline (fill t+1):", json.dumps(trade_stats(base, "baseline")))
    print("DELAY test       (fill t+2):", json.dumps(trade_stats(delay, "delay")))
    print("exit reasons:", base["reason"].value_counts().to_dict())
    # by-year
    base["yr"] = pd.to_datetime(base["entry_date"]).dt.year
    print("\nby-year mean_R / n / sum_R:")
    for y, g in base.groupby("yr"):
        print(f"  {y}: mean_R {g['R'].mean():+.3f}  n {len(g):2d}  sumR {g['R'].sum():+.1f}  win {(g['R']>0).mean()*100:.0f}%")
    # train/OOS
    tr_is = base[base.yr <= 2020]; tr_oos = base[base.yr >= 2021]
    print("\nIN-SAMPLE 2015-2020:", json.dumps(trade_stats(tr_is, "IS")))
    print("OUT-SAMPLE 2021-2026:", json.dumps(trade_stats(tr_oos, "OOS")))
    summary = dict(period=f"{df.index.min().date()}..{df.index.max().date()}", n_days=len(df),
                   reversion=rev, baseline=trade_stats(base, "baseline"),
                   delay=trade_stats(delay, "delay"),
                   IS=trade_stats(tr_is, "IS"), OOS=trade_stats(tr_oos, "OOS"))
    json.dump(summary, open(f"{OUT}/step1_summary.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
