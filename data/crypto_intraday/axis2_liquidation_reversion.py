#!/usr/bin/env python3
"""AXIS #2 — intraday reversion post liquidation-cascade. Mechanism: forced (non-price-
sensitive) deleveraging overshoots -> intraday reversion. Enter AGAINST the cascade at
delay-1, flat intraday. DECISIVE L33 RISK: charge the spread DURING the cascade minutes
(blown-out), not the average. Two-sided (down-flush->long, up-squeeze->short). OOS.
Anti-mining: pre-specified cascade def (k-min return tail), single threshold sweep reported."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/crypto_intraday"
PT = 0.01; COMM_RT = 6.5


def load_min():
    df = pd.read_csv(f"{D}/panels/m5_indices/BTCUSD_M1.csv",
                     usecols=["timestamp_utc", "close", "spread"])
    df["dt"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns="timestamp_utc").set_index("dt").sort_index()
    df = df[df["close"] > 0]
    df["spr_bps"] = df["spread"] * PT / df["close"] * 1e4
    return df


def test(df, K, q, side):
    """K-min move; cascade = tail beyond quantile q. side=-1 down-flush(go long), +1 up(go short).
    Entry delay-1 (bar after the cascade window ends); charge entry-bar spread + comm."""
    c = df["close"].values; spr = df["spr_bps"].values; n = len(c)
    kret = pd.Series(c).pct_change(K).values                       # trailing K-min return (known at bar)
    if side < 0:
        thr = np.nanquantile(kret, q); trig = kret < thr           # sharp down-flush
    else:
        thr = np.nanquantile(kret, 1 - q); trig = kret > thr       # sharp up-squeeze
    res = {30: [], 60: [], 120: []}; sprs = []; gaps = 0; last = -10_000
    for i in np.where(trig)[0]:
        if i + 1 < 5 or i + 1 + 120 >= n: continue
        if i - last < K: continue                                  # don't double-count same cascade
        last = i
        entry = c[i + 1]; spr_e = spr[i + 1]; sprs.append(spr_e)   # delay-1 entry, entry-bar spread
        for h in (30, 60, 120):
            fwd = c[i + 1 + h] / entry - 1
            rev = (-side) * fwd * 1e4                               # reversion = against the cascade
            res[h].append(rev - spr_e - COMM_RT)                   # net of blown-out spread + comm
    return res, np.array(sprs)


def main():
    df = load_min()
    print(f"BTCUSD 1-min n={len(df):,}  ({df.index.min().date()}..{df.index.max().date()})")
    print("AXIS #2 — liquidation-cascade reversion, delay-1, net of CASCADE-minute spread + comm 6.5 RT\n")
    for side, slbl in [(-1, "DOWN-flush -> LONG"), (+1, "UP-squeeze -> SHORT")]:
        print(f"=== {slbl} ===")
        for K in (10, 30):
            for q in (0.005, 0.001):                               # 0.5% and 0.1% tails
                res, sprs = test(df, K, q, side)
                n = len(res[60])
                if n < 20:
                    print(f"  K={K}m tail={q*100:.1f}%: N={n} (too few)"); continue
                line = f"  K={K}m tail={q*100:.1f}%: N={n}  spread@entry med {np.median(sprs):.1f}bps p90 {np.quantile(sprs,.9):.0f}  |"
                for h in (30, 60, 120):
                    a = np.array(res[h]); line += f"  {h}m net {a.mean():+5.0f}(hit{(a>0).mean()*100:2.0f}%)"
                print(line)
        print()
    # OOS for the best-looking cell (down-flush K=30 tail0.5%)
    print("=== OOS check — DOWN-flush K=30m tail0.5%, 60m net ===")
    for lab, sl in [("pre-2023", df.index.year < 2023), ("post-2023", df.index.year >= 2023)]:
        res, sprs = test(df[sl], 30, 0.005, -1)
        a = np.array(res[60]); print(f"  {lab}: N={len(a)}  net {a.mean():+.0f}bps  hit {(a>0).mean()*100:.0f}%  median {np.median(a):+.0f}")


if __name__ == "__main__":
    main()
