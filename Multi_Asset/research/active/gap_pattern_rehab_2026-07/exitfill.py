"""
exitfill.py — Phase 3c: the delay+1 gate re-priced the ENTRY only. The EXIT is
still filled at the exact stop level whenever `low[j] <= stop_lvl`.

That assumption is uniquely generous here. The pattern exit places the stop at
the gap edge — typically ~1 ATR from entry, far inside the 6-ATR risk unit — on
a universe the strategy has itself selected for gapping. When a bar OPENS beyond
the stop, no one is filled at the stop; the fill is the open.

Arms:
  'stop_exact' : as audited (stop_lvl whenever the bar touches it)
  'open_gap'   : if the bar opens beyond the stop, fill at the OPEN, else stop_lvl
And, to size the geometry effect, the realised stop distance is recorded.

Also: gap frequency by data source (yfinance continuous front-month vs broker),
and day-of-month clustering of gap events (contract-roll signature).
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd

ROOT = "<HOME>/Desktop/Algo_claude"
AUDIT = f"{ROOT}/Multi_Asset/research/archived/oxfordstrat_109_audit"
sys.path.insert(0, os.path.join(AUDIT, "code"))
os.environ.setdefault("OHLC_DIR", os.path.join(AUDIT, "ohlc"))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ftmo_lab as lab                                     # noqa: E402
from repro import UNI, COSTS, ATR_LEN, ATR_STOP            # noqa: E402
import mechanism as M                                      # noqa: E402
M.PROXY["GER40"] = "US500"
SRC = pd.read_csv(os.path.join(AUDIT, "ohlc", "_coverage.csv")).set_index("instr")
FLB, TM = 20, 10


def sim(df, variant, exit_fill="stop_exact", cost_bps=2.0):
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    A = lab.atr(df, ATR_LEN).values
    upc = pd.Series(h, index=df.index).rolling(FLB).max().shift(1).values
    loc = pd.Series(l, index=df.index).rolling(FLB).min().shift(1).values
    n = len(df); idx = df.index; out = []; i = FLB + 1
    while i < n - 2:
        k = i
        if variant == "A":
            gu, gd = l[k] > h[k - 1], h[k] < l[k - 1]
        else:
            gu, gd = l[k] > c[k - 1], h[k] < c[k - 1]
        long_s = gu and np.isfinite(upc[k]) and h[k] > upc[k]
        short_s = gd and np.isfinite(loc[k]) and l[k] < loc[k]
        if not (long_s or short_s) or not np.isfinite(A[k]) or A[k] <= 0:
            i += 1; continue
        d = 1 if long_s else -1
        eb = k + 1
        entry = o[eb]
        if eb > n - 1 or not np.isfinite(entry):
            i = k + 1; continue
        risk0 = A[k] * ATR_STOP
        gapfloor = (h[k - 1] if d == 1 else l[k - 1]) if variant == "A" else c[k - 1]
        atr_lvl = entry - d * risk0
        stop_lvl = max(gapfloor, atr_lvl) if d == 1 else min(gapfloor, atr_lvl)
        last = min(eb + TM, n - 1)
        exit_p = exit_j = reason = None
        slip = 0.0
        for j in range(eb, last + 1):
            hit = (l[j] <= stop_lvl) if d == 1 else (h[j] >= stop_lvl)
            if hit:
                px = stop_lvl
                if exit_fill == "open_gap":
                    beyond = (o[j] <= stop_lvl) if d == 1 else (o[j] >= stop_lvl)
                    if beyond and j > eb:          # bar opened through the stop
                        px = o[j]
                        slip = d * (stop_lvl - px) / risk0     # >0 = extra loss
                exit_p, reason, exit_j = px, "stop", j; break
            if j == last:
                exit_p, reason, exit_j = c[j], "time", j; break
        grossR = d * (exit_p - entry) / risk0
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        out.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), reason=reason,
                        netR=grossR - cost_R, grossR=grossR, cost_R=cost_R,
                        slipR=slip, entry_px=float(entry), risk0=float(risk0),
                        stop_dist_atr=float(abs(entry - stop_lvl) / (A[k] if A[k] else np.nan)),
                        nights=int((idx[exit_j] - idx[eb]).days)))
        i = exit_j + 1
    return pd.DataFrame(out)


def pooled(variant, exit_fill):
    fr = []
    for t, df in UNI.items():
        x = sim(df, variant, exit_fill, cost_bps=COSTS[t])
        if len(x):
            x["instr"] = t; x["cls"] = lab.CLASS.get(t, "indices")
            fr.append(x)
    return pd.concat(fr, ignore_index=True)


if __name__ == "__main__":
    RES = {}
    for variant, tag in (("A", "s035"), ("B", "s036")):
        a = pooled(variant, "stop_exact")
        b = pooled(variant, "open_gap")
        bs = M.add_swap(b)
        as_ = M.add_swap(a)
        st = a[a["reason"] == "stop"]
        R = dict(
            stop_dist_atr_median=float(a["stop_dist_atr"].median()),
            stop_dist_atr_mean=float(a["stop_dist_atr"].mean()),
            pct_exits_by_stop=float((a["reason"] == "stop").mean() * 100),
            expR_stop_exact=float(a["netR"].mean()),
            expR_open_gap=float(b["netR"].mean()),
            sharpe_stop_exact=float(lab.trade_metrics(a)["sharpe"]),
            sharpe_open_gap=float(lab.trade_metrics(b)["sharpe"]),
            pct_stopped_bars_that_gapped_through=float(
                (b.loc[b["reason"] == "stop", "slipR"] > 0).mean() * 100),
            mean_slipR_all=float(b["slipR"].mean()),
            expR_open_gap_swap=float(bs["netR_swap"].mean()),
            expR_stop_exact_swap=float(as_["netR_swap"].mean()),
            twosided_open_gap=dict(long=float(b.loc[b["dir"] == 1, "netR"].mean()),
                                   short=float(b.loc[b["dir"] == -1, "netR"].mean())),
            twosided_open_gap_swap=dict(
                long=float(bs.loc[bs["dir"] == 1, "netR_swap"].mean()),
                short=float(bs.loc[bs["dir"] == -1, "netR_swap"].mean())),
        )
        # recent regime under realistic exits + swap
        rec = bs[pd.to_datetime(bs["entry"]) > pd.Timestamp("2018-12-31")]
        R["recent_open_gap_swap_expR"] = float(rec["netR_swap"].mean())
        # broker-only under realistic exits + swap
        bs["src"] = [SRC.loc[i, "source"] for i in bs["instr"]]
        brk = bs[~bs["src"].str.startswith("yf:")]
        R["broker_only_open_gap_swap_expR"] = float(brk["netR_swap"].mean())
        R["yf_only_open_gap_swap_expR"] = float(
            bs[bs["src"].str.startswith("yf:")]["netR_swap"].mean())
        RES[tag] = R
        print("=" * 70); print(tag); print(json.dumps(R, indent=1))

    # ---- gap frequency & roll-day signature by data source -----------------
    freq = []
    for t, df in UNI.items():
        h, l, c = df["high"].values, df["low"].values, df["close"].values
        gu = np.r_[False, l[1:] > h[:-1]]
        gd = np.r_[False, h[1:] < l[:-1]]
        ev = gu | gd
        dom = pd.Series(df.index[ev]).dt.day
        freq.append(dict(instr=t, src=SRC.loc[t, "source"], n_bars=len(df),
                         gap_rate_pct=float(ev.mean() * 100),
                         mean_gap_bps=float(np.nanmean(
                             np.abs(np.r_[np.nan, c[1:] - c[:-1]])[ev] / c[ev] * 1e4)),
                         dom_top3=list(dom.value_counts().head(3).index.astype(int))))
    F = pd.DataFrame(freq)
    F["grp"] = np.where(F["src"].str.startswith("yf:"), "yfinance_=F", "broker")
    F.to_csv(os.path.join(HERE, "gap_frequency_by_source.csv"), index=False)
    print("\n=== gap frequency by data source ===")
    print(F.groupby("grp")[["gap_rate_pct", "mean_gap_bps"]].agg(["mean", "median", "count"]).round(3))
    print(F.sort_values("gap_rate_pct", ascending=False).head(12).to_string(index=False))

    with open(os.path.join(HERE, "exitfill.json"), "w") as f:
        json.dump(RES, f, indent=1)
