"""
repro.py — Phase 1: reproduce S035/S036 and PERSIST what the audit never wrote.

The audit stored only the EXPECTANCY grid (`s03*_sensitivity_expectancy.csv`).
The per-cell SHARPE grid (`sg` in the strat scripts) was computed and thrown away,
so the "one line of arithmetic on already-stored Sharpes" the inventory promised
is not available: the grid has to be re-run to recover the trial dispersion.

This module re-runs the two 3x3 grids VERBATIM (same code path, same universe,
same costs) and additionally records, per trade:
  - instrument, class, direction
  - entry / exit dates  -> nights held (for the overnight swap re-pricing)
  - entry price, risk0   -> to convert R-multiples into bps of notional

No parameter is changed. This is a REPRODUCTION, not a new test.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd

AUDIT = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit"
sys.path.insert(0, os.path.join(AUDIT, "code"))
os.environ.setdefault("OHLC_DIR", os.path.join(AUDIT, "ohlc"))

import ftmo_lab as lab  # noqa: E402

ATR_LEN, ATR_STOP = 20, 6.0
FLS, TMS = [10, 20, 40], [5, 10, 20]
FLB_REP, TM_REP = 20, 10

UNI = lab.load_universe()
COSTS = {t: lab.round_turn_cost_bps(t, df) for t, df in UNI.items()}


def simulate_gap(df, flb, time_index, *, variant="A", atr_stop=ATR_STOP, cost_bps=2.0,
                 allow_short=True, fill="stop"):
    """Verbatim copy of strat_s035/s036 simulate_gap + extra recorded fields.

    variant 'A' : gap = Low[i] > High[i-1]   (S035), pattern exit at prior extreme
    variant 'B' : gap = Low[i] > Close[i-1]  (S036), pattern exit at prior close
    """
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    A = lab.atr(df, ATR_LEN).values
    upc = pd.Series(h, index=df.index).rolling(flb).max().shift(1).values
    loc = pd.Series(l, index=df.index).rolling(flb).min().shift(1).values
    n = len(df); idx = df.index; trades = []; i = flb + 1
    while i < n - 2:
        k = i
        if variant == "A":
            gap_up, gap_dn = l[k] > h[k - 1], h[k] < l[k - 1]
        else:
            gap_up, gap_dn = l[k] > c[k - 1], h[k] < c[k - 1]
        long_s = gap_up and np.isfinite(upc[k]) and h[k] > upc[k]
        short_s = allow_short and gap_dn and np.isfinite(loc[k]) and l[k] < loc[k]
        if not (long_s or short_s) or not np.isfinite(A[k]) or A[k] <= 0:
            i += 1; continue
        d = 1 if long_s else -1
        if fill == "stop":        eb = k + 1; entry = o[eb] if eb <= n - 1 else np.nan
        elif fill == "close":     eb = k + 1; entry = c[eb] if eb <= n - 1 else np.nan
        elif fill == "next_open": eb = k + 2; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i = k + 1; continue
        risk0 = A[k] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        if variant == "A":
            gapfloor = h[k - 1] if d == 1 else l[k - 1]
        else:
            gapfloor = c[k - 1]
        atr_lvl = entry - d * risk0
        stop_lvl = max(gapfloor, atr_lvl) if d == 1 else min(gapfloor, atr_lvl)
        last = min(eb + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, "stop", j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, "stop", j; break
            if j == last: exit_p, reason, exit_j = c[j], "time", j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d),
                           netR=grossR - cost_R, grossR=grossR, cost_R=cost_R,
                           reason=reason, entry_px=float(entry), risk0=float(risk0),
                           nights=int((idx[exit_j] - idx[eb]).days), instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)


def run_point(variant, flb, time_index, fill="stop", cost_mult=1.0):
    frames = []
    for t, df in UNI.items():
        tr = simulate_gap(df, flb, time_index, variant=variant,
                          cost_bps=COSTS[t] * cost_mult, fill=fill)
        if len(tr):
            tr["instr"] = t
            tr["cls"] = lab.CLASS.get(t, "indices")
            frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def grid(variant):
    """3x3 sweep -> per-cell metrics. Returns (DataFrame of cells, dict of pooled trades)."""
    rows, pools = [], {}
    for fl in FLS:
        for tm in TMS:
            pool = run_point(variant, fl, tm)
            m = lab.trade_metrics(pool)
            e = pd.to_datetime(pool["exit"])
            days = max((e.max() - pd.to_datetime(pool["entry"]).min()).days, 1)
            rows.append(dict(cell=f"F{fl}_T{tm}", flb=fl, tm=tm, trades=m["trades"],
                             win=m["win"], expR=m["expR"], pf=m["pf"], sharpe=m["sharpe"],
                             maxdd=m["maxdd"], cagr=m["cagr"],
                             tpy=m["trades"] / (days / 365.0), span_days=days))
            pools[f"F{fl}_T{tm}"] = pool
    return pd.DataFrame(rows), pools


if __name__ == "__main__":
    out = {}
    HERE = os.path.dirname(os.path.abspath(__file__))
    for variant, tag in (("A", "s035"), ("B", "s036")):
        g, pools = grid(variant)
        g.to_csv(os.path.join(HERE, f"{tag}_grid_metrics.csv"), index=False)
        best = g.loc[g["sharpe"].idxmax()]
        pt = pools[f"F{FLB_REP}_T{TM_REP}"]
        pt.to_parquet(os.path.join(HERE, f"{tag}_trades_point.parquet"))
        pools[best["cell"]].to_parquet(os.path.join(HERE, f"{tag}_trades_best.parquet"))
        m_pt = lab.trade_metrics(pt)
        m_d1 = lab.trade_metrics(run_point(variant, FLB_REP, TM_REP, fill="next_open"))
        r, d = pt["netR"].values, pt["dir"].values
        out[tag] = dict(
            point=dict(cell=f"F{FLB_REP}_T{TM_REP}", **{k: float(v) if v is not None else None
                                                        for k, v in m_pt.items()}),
            delay1_sharpe=float(m_d1["sharpe"]), delay1_expR=float(m_d1["expR"]),
            two_sided=dict(long=float(r[d == 1].mean()), short=float(r[d == -1].mean()),
                           n_long=int((d == 1).sum()), n_short=int((d == -1).sum())),
            grid_sharpes=[float(x) for x in g["sharpe"]],
            grid_expR=[float(x) for x in g["expR"]],
            best_cell=str(best["cell"]), best_sharpe=float(best["sharpe"]),
            best_trades=int(best["trades"]), best_tpy=float(best["tpy"]),
            grid_pct_positive=float((g["expR"] > 0).mean() * 100),
        )
        print(f"=== {tag.upper()} variant {variant} ===")
        print(g.to_string(index=False))
        print(json.dumps(out[tag], indent=1, default=str))
    with open(os.path.join(HERE, "repro_summary.json"), "w") as f:
        json.dump(out, f, indent=1)
