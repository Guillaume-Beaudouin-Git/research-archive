#!/usr/bin/env python3
"""Idea 1B — EUR/GBP single-leg cross-level reversion. Reuses the 1A engine
on a synthetic daily EURGBP = EURUSD/GBPUSD (yfinance 2015-2026). Same gate,
baseline, pre-registered 18-trial grid, and raw-return significance check."""
import glob, json
import numpy as np, pandas as pd
import audnzd_engine as E

DATA = "/sessions/affectionate-epic-faraday/mnt/data"
OUT = "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/statarb_audnzd"


def load_eurgbp():
    e = pd.read_parquet(glob.glob(f"{DATA}/raw/yf_EURUSD=X_1d_*.parquet")[0])["close"]
    g = pd.read_parquet(glob.glob(f"{DATA}/raw/yf_GBPUSD=X_1d_*.parquet")[0])["close"]
    df = pd.DataFrame({"EURUSD": e, "GBPUSD": g}).dropna()
    df["EURGBP"] = df["EURUSD"] / df["GBPUSD"]
    df = df[(df["EURGBP"] > 0.6) & (df["EURGBP"] < 1.0)]
    df["logpx"] = np.log(df["EURGBP"])
    return df


def raw(tr, lab):
    if len(tr) < 5:
        print(f"  {lab}: n<5"); return
    r = tr["net_ret"].values
    t = r.mean() / r.std(ddof=1) * np.sqrt(len(r))
    tr = tr.copy(); tr["yr"] = pd.to_datetime(tr["entry_date"]).dt.year
    oos = tr[tr.yr >= 2021]["net_ret"]
    print(f"  {lab}: n{len(r):3d}  sum {r.sum()*100:+6.1f}%  /trade {r.mean()*1e4:+6.1f}bps  "
          f"t {t:+.2f}  win {(r>0).mean()*100:.0f}%  OOS {oos.sum()*100:+.1f}%")


def main():
    df = load_eurgbp()
    rev = E.confirm_reversion(df)
    sig = E.build_signal(df)
    base = E.backtest(sig, price_col="EURGBP", fill_lag=1)
    delay = E.backtest(sig, price_col="EURGBP", fill_lag=2)
    print("=" * 64)
    print(f"EUR/GBP daily | {df.index.min().date()} .. {df.index.max().date()} | {len(df)} days")
    print("MEAN-REVERSION GATE:", json.dumps(rev))
    print("BACKTEST baseline (t+1):", json.dumps(E.trade_stats(base, "baseline")))
    print("DELAY test       (t+2):", json.dumps(E.trade_stats(delay, "delay")))
    print("exit reasons:", base["reason"].value_counts().to_dict())
    print("\nRAW cost-aware return (un-distortable):")
    raw(base, "baseline 60/2/3")
    print("\nPre-registered 18-trial grid (raw return):")
    pos_ret = pos_oos = tot = 0; best = None
    for W in (40, 60, 90):
        s = E.build_signal(df, w=W)
        for zin in (1.5, 2.0, 2.5):
            for zst in (3.0, 4.0):
                tr = E.backtest(s, z_in=zin, z_stop=zst, t_max=20, price_col="EURGBP")
                if len(tr) < 10:
                    continue
                r = tr["net_ret"].values
                t = r.mean() / r.std(ddof=1) * np.sqrt(len(r))
                tr2 = tr.copy(); tr2["yr"] = pd.to_datetime(tr2["entry_date"]).dt.year
                oos = tr2[tr2.yr >= 2021]["net_ret"].sum()
                tot += 1; pos_ret += (r.sum() > 0); pos_oos += (oos > 0)
                if best is None or t > best[-1]:
                    best = (W, zin, zst, len(tr), r.sum(), oos, t)
                print(f"  W{W} zin{zin} zst{zst}: n{len(tr):3d} sum {r.sum()*100:+6.1f}% "
                      f"OOS {oos*100:+6.1f}% t {t:+.2f} win {(r>0).mean()*100:.0f}%")
    print(f"\npositive total-return configs: {pos_ret}/{tot} | positive-OOS: {pos_oos}/{tot}")
    print(f"BEST by t-stat: W{best[0]} zin{best[1]} zst{best[2]} -> sum {best[4]*100:+.1f}% "
          f"OOS {best[5]*100:+.1f}% t {best[6]:+.2f}  (vs noise-max |t|~2.0-2.2 over {tot} trials)")
    bh = df["EURGBP"].iloc[-1] / df["EURGBP"].iloc[0] - 1
    print(f"buy&hold EURGBP 2015-2026: {bh*100:+.1f}%")
    base.to_csv(f"{OUT}/trades_ledger_eurgbp.csv", index=False)


if __name__ == "__main__":
    main()
