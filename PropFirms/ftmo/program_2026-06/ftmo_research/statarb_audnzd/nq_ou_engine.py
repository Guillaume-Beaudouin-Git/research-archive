#!/usr/bin/env python3
"""Idea 2B — NQ intraday OU mean-reversion (single-leg). Decisive tests first:
measured-cost sweep (L33) + 1-bar delay (bid-ask-bounce artifact check).
Causal: intraday rolling fair value/z use only bars <= t within the session;
entry fills at the NEXT bar; flat at session end (no overnight)."""
from __future__ import annotations
import json
import numpy as np, pandas as pd

DATA = "/sessions/affectionate-epic-faraday/mnt/data/raw/NQ_1min_databento_2010-2026.parquet"
OUT = "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/statarb_audnzd"


def load_days():
    df = pd.read_parquet(DATA, columns=["close", "is_rth", "is_roll_day"])
    df = df[df["is_rth"] & ~df["is_roll_day"]]
    idx = df.index.tz_convert("US/Eastern")
    day_int = (idx.year * 10000 + idx.month * 100 + idx.day).to_numpy()
    C = df["close"].to_numpy()
    chg = np.where(np.diff(day_int) != 0)[0] + 1
    starts = np.concatenate([[0], chg]); ends = np.concatenate([chg, [len(C)]])
    day_ts = pd.to_datetime(idx.normalize().to_numpy())[starts]
    return C, starts, ends, day_ts


def roll_z(c, W):
    n = len(c)
    z = np.full(n, np.nan)
    if n < W + 2:
        return z
    cs = np.concatenate([[0.0], np.cumsum(c)])
    cs2 = np.concatenate([[0.0], np.cumsum(c * c)])
    idx = np.arange(W - 1, n)
    m = (cs[idx + 1] - cs[idx + 1 - W]) / W
    v = (cs2[idx + 1] - cs2[idx + 1 - W]) / W - m * m
    sd = np.sqrt(np.maximum(v, 1e-9))
    z[idx] = (c[idx] - m) / sd
    return z


def build_trades(C, starts, ends, day_ts, W=30, Zin=2.5, Zstop=4.0, fill_lag=1):
    rows = []
    for k in range(len(starts)):
        s, e = starts[k], ends[k]
        c = C[s:e]; n = len(c)
        if n < W + 5:
            continue
        z = roll_z(c, W)
        pos = 0; entry_px = 0.0; entry_i = -1
        i = W
        while i < n - fill_lag:
            if pos == 0:
                if z[i] >= Zin:
                    d = -1
                elif z[i] <= -Zin:
                    d = 1
                else:
                    i += 1; continue
                entry_i = i + fill_lag
                entry_px = c[entry_i]; pos = d
                i = entry_i + 1
            else:
                zi = z[i]
                ex = (pos == 1 and zi >= 0) or (pos == -1 and zi <= 0) or (abs(zi) >= Zstop) or (i == n - 1)
                if ex:
                    rows.append((day_ts[k], pos, entry_px, c[i], i - entry_i,
                                 pos * (c[i] - entry_px) / entry_px))
                    pos = 0
                i += 1
        if pos != 0:   # force flat at session end
            rows.append((day_ts[k], pos, entry_px, c[n - 1], (n - 1) - entry_i,
                         pos * (c[n - 1] - entry_px) / entry_px))
    return pd.DataFrame(rows, columns=["date", "dir", "entry_px", "exit_px", "bars", "gross_ret"])


def net_stats(tr, cost_pts, label=""):
    g = tr["gross_ret"].to_numpy()
    cost = cost_pts / tr["entry_px"].to_numpy()       # round-trip cost in return terms
    r = g - cost
    s = r.std(ddof=1)
    return dict(label=label, n=int(len(r)), mean_bps=round(float(r.mean() * 1e4), 2),
                t=round(float(r.mean() / s * np.sqrt(len(r))), 2) if s > 0 else None,
                win=round(float((r > 0).mean()), 3), tot_pct=round(float(r.sum() * 100), 1),
                med_bars=int(tr["bars"].median()))


def main():
    import time
    t0 = time.time()
    C, starts, ends, day_ts = load_days()
    print(f"[load {time.time()-t0:.1f}s] NQ RTH {day_ts[0].date()}..{day_ts[-1].date()} days={len(starts)} bars={len(C)}")
    t1 = time.time()
    base = build_trades(C, starts, ends, day_ts, W=30, Zin=2.5, Zstop=4.0, fill_lag=1)
    print(f"[build baseline {time.time()-t1:.1f}s] trades={len(base)} (~{len(base)/len(starts):.1f}/day)")
    # VR gate on 1-min returns (bounce caveat)
    r1 = np.diff(C) / C[:-1]
    vr = np.var(r1[:len(r1)//5*5].reshape(-1,5).sum(1), ddof=1) / (5*np.var(r1, ddof=1))
    print(f"GATE: 1-min return VR(5)={vr:.3f} (bounce inflates <1; not trustworthy intraday -> rely on delay+cost)")
    print("\n=== DECISIVE TEST 1: measured-cost sweep (baseline 30/2.5/4, fill t+1) ===")
    for cp in (0.0, 0.25, 0.5, 1.0, 2.0):
        print("  cost", cp, "pt RT:", json.dumps(net_stats(base, cp)))
    print("\n=== DECISIVE TEST 2: 1-bar delay (bid-ask-bounce artifact check) ===")
    t2 = time.time()
    delay = build_trades(C, starts, ends, day_ts, W=30, Zin=2.5, Zstop=4.0, fill_lag=2)
    print(f"  [build delay {time.time()-t2:.1f}s]")
    print("  fill t+1 @0.5pt:", json.dumps(net_stats(base, 0.5)))
    print("  fill t+2 @0.5pt:", json.dumps(net_stats(delay, 0.5)), " <- collapse => bounce artifact")
    print("  fill t+1 @0  pt:", json.dumps(net_stats(base, 0.0)))
    print("  fill t+2 @0  pt:", json.dumps(net_stats(delay, 0.0)))
    # by-year at realistic cost
    base["yr"] = base["date"].dt.year
    print("\nby-year net @0.5pt (mean_bps / n):")
    for y, gdf in base.groupby("yr"):
        gg = gdf["gross_ret"].to_numpy() - 0.5/gdf["entry_px"].to_numpy()
        print(f"  {y}: {gg.mean()*1e4:+.2f}bps  n{len(gdf)}")
    base.to_csv(f"{OUT}/trades_nq_ou.csv", index=False)


if __name__ == "__main__":
    main()
