"""
mechanism.py — Phase 3: the gates that are still VALID after the DSR is repaired.

  A. anatomy      : where the edge lives (class / instrument / direction / era),
                    P&L concentration, gross edge expressed in bps of NOTIONAL.
  B. swap (L36)   : re-price with the MEASURED FTMO overnight carry
                    (data/ftmo_portfolio/outputs/phase0_swap_model.csv, bps/night).
  C. cost (L33)   : sensitivity of the round-turn assumption.
  D. L58          : the unconditional-expectation control. Same trade shape,
                    same exit machinery, entered unconditionally -> is the GAP
                    doing anything the trade shape was not already doing?
  E. L38          : beta orthogonality, strategy daily P&L vs vol-targeted
                    buy&hold of the traded universe (beta, alpha HAC-6, R2).
  F. L31          : regime / decay split.
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

import ftmo_lab as lab                      # noqa: E402
import statsmodels.api as sm                # noqa: E402
from repro import UNI, COSTS, run_point, simulate_gap, ATR_LEN, ATR_STOP  # noqa: E402

RISK_FRAC = lab.RISK_FRAC
FLB_REP, TM_REP = 20, 10

# ---------------------------------------------------------------- swap model
SW = pd.read_csv(f"{ROOT}/data/ftmo_portfolio/outputs/phase0_swap_model.csv", index_col=0)
FX_PROXY = ("EURUSD", "GBPUSD AUDUSD NZDUSD".split())      # USD-quoted, est in the source table
PROXY = {"AUS200": "US500", "EU50": "US500", "HK50": "US500", "JP225": "US500",
         "UK100": "US500", "US2000": "US500", "XPTUSD": "XAUUSD", "XPDUSD": "XAUUSD",
         "WHEAT": "SOYBEAN", "GBPUSD": "EURUSD", "AUDUSD": "EURUSD", "NZDUSD": "EURUSD"}


def swap_bps(instr, direction):
    """bps of notional per night. Negative = paid. Measured where available."""
    key = PROXY.get(instr, instr)
    if key not in SW.index:
        raise KeyError(instr)
    row = SW.loc[key]
    v = row["lb"] if direction == 1 else row["sb"]
    return float(v), (instr not in PROXY) and (not bool(row["est"]))


def add_swap(tr, mult=1.0):
    """Charge the measured overnight carry on held notional (L36)."""
    bps = np.array([swap_bps(i, d)[0] for i, d in zip(tr["instr"], tr["dir"])])
    swap_R = (bps * mult / 1e4) * tr["entry_px"].values * tr["nights"].values / tr["risk0"].values
    out = tr.copy()
    out["swap_R"] = swap_R
    out["netR_swap"] = tr["netR"].values + swap_R
    return out


def bps_of_notional(tr, col="netR"):
    return tr[col].values * tr["risk0"].values / tr["entry_px"].values * 1e4


# ---------------------------------------------------------------- L58 baseline
def simulate_uncond(df, time_index, direction, variant="A", mode="all", flb=FLB_REP,
                    cost_bps=0.0):
    """Same trade shape / same exit machinery, entered on EVERY eligible bar.

    mode 'all'    : unconditional (no gap, no filter)  -> the L58 baseline
    mode 'filter' : trend filter only (no gap)
    mode 'gap'    : gap only (no trend filter)
    Overlapping by construction: this estimates E[trade shape], not a tradable book.
    """
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    A = lab.atr(df, ATR_LEN).values
    upc = pd.Series(h, index=df.index).rolling(flb).max().shift(1).values
    loc = pd.Series(l, index=df.index).rolling(flb).min().shift(1).values
    n = len(df); idx = df.index; d = direction
    rs, yrs = [], []
    for k in range(flb + 1, n - 2):
        if not np.isfinite(A[k]) or A[k] <= 0:
            continue
        if mode in ("gap", "both"):
            if variant == "A":
                ok = (l[k] > h[k - 1]) if d == 1 else (h[k] < l[k - 1])
            else:
                ok = (l[k] > c[k - 1]) if d == 1 else (h[k] < c[k - 1])
            if not ok:
                continue
        if mode in ("filter", "both"):
            ok = (np.isfinite(upc[k]) and h[k] > upc[k]) if d == 1 else \
                 (np.isfinite(loc[k]) and l[k] < loc[k])
            if not ok:
                continue
        eb = k + 1
        entry = o[eb]
        if not np.isfinite(entry):
            continue
        risk0 = A[k] * ATR_STOP
        gapfloor = (h[k - 1] if d == 1 else l[k - 1]) if variant == "A" else c[k - 1]
        atr_lvl = entry - d * risk0
        stop_lvl = max(gapfloor, atr_lvl) if d == 1 else min(gapfloor, atr_lvl)
        last = min(eb + time_index, n - 1)
        exit_p = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p = stop_lvl; break
            if d == -1 and h[j] >= stop_lvl: exit_p = stop_lvl; break
            if j == last: exit_p = c[j]; break
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        rs.append(d * (exit_p - entry) / risk0 - cost_R)
        yrs.append(idx[eb].year)
    return np.array(rs), np.array(yrs)


def l58_baseline(variant, tag):
    """Matched unconditional baseline: instrument x direction x YEAR weights taken
    from the actual gap trades (L58 -- the placebo pool must not drift off the
    unconditional expectation of the trade shape)."""
    tr = pd.read_parquet(os.path.join(HERE, f"{tag}_trades_point.parquet"))
    tr["year"] = pd.to_datetime(tr["entry"]).dt.year
    rows = []
    for instr, df in UNI.items():
        for d in (1, -1):
            for mode in ("all", "filter", "gap", "both"):
                r, y = simulate_uncond(df, TM_REP, d, variant=variant, mode=mode)
                if len(r) == 0:
                    continue
                s = pd.DataFrame({"r": r, "year": y})
                rows.append(dict(instr=instr, dir=d, mode=mode, n=len(r),
                                 mean=float(r.mean()),
                                 by_year=s.groupby("year")["r"].agg(["mean", "size"])))
    B = pd.DataFrame(rows)
    # weights = the real gap-trade counts per (instr, dir, year)
    w = tr.groupby(["instr", "dir", "year"]).size().rename("w").reset_index()
    out = {}
    for mode in ("all", "filter", "gap", "both"):
        sub = B[B["mode"] == mode]
        tot_w, tot_v, flat_n, flat_v = 0.0, 0.0, 0, 0.0
        for _, b in sub.iterrows():
            by = b["by_year"]
            flat_n += b["n"]; flat_v += b["mean"] * b["n"]
            ww = w[(w["instr"] == b["instr"]) & (w["dir"] == b["dir"])]
            for _, x in ww.iterrows():
                if x["year"] in by.index:
                    tot_w += x["w"]; tot_v += by.loc[x["year"], "mean"] * x["w"]
        out[mode] = dict(matched_expR=tot_v / tot_w if tot_w else np.nan,
                         matched_w=tot_w,
                         flat_expR=flat_v / flat_n if flat_n else np.nan, flat_n=flat_n)
    return out


# ---------------------------------------------------------------- L38 beta
def daily_series(tr):
    """Strategy daily return in fraction of equity (RISK_FRAC per trade, booked on exit)."""
    s = pd.Series(tr["netR"].values * RISK_FRAC, index=pd.to_datetime(tr["exit"]))
    return s.groupby(s.index).sum().sort_index()


def bench_voltgt(instruments, target_vol=None):
    """Equal-weight, inverse-vol-scaled buy&hold of the traded universe (L38 benchmark)."""
    cols = {}
    for t in instruments:
        r = UNI[t]["close"].pct_change()
        v = r.rolling(63).std().shift(1)
        cols[t] = (r / v).replace([np.inf, -np.inf], np.nan)
    R = pd.DataFrame(cols).mean(axis=1).dropna()
    if target_vol is not None and R.std() > 0:
        R = R / R.std() * target_vol
    return R


def l38(tr):
    y = daily_series(tr)
    x = bench_voltgt(sorted(tr["instr"].unique()))
    idx = y.index.union(x.index)
    y = y.reindex(idx).fillna(0.0)
    x = x.reindex(idx).fillna(0.0)
    m = (x != 0)                       # keep bench trading days
    y, x = y[m], x[m]
    x = x / x.std() * y.std()          # scale bench to strategy vol
    res = sm.OLS(y.values, sm.add_constant(x.values)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 6})
    return dict(beta=float(res.params[1]), beta_t=float(res.tvalues[1]),
                alpha_daily=float(res.params[0]), alpha_t=float(res.tvalues[0]),
                alpha_ann_pct=float(res.params[0] * 252 * 100),
                r2=float(res.rsquared), n=int(len(y)))


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    RES = {}
    for variant, tag in (("A", "s035"), ("B", "s036")):
        tr = pd.read_parquet(os.path.join(HERE, f"{tag}_trades_point.parquet"))
        tr["year"] = pd.to_datetime(tr["entry"]).dt.year
        R = {}

        # --- A. anatomy -----------------------------------------------------
        gross_bps = bps_of_notional(tr, "grossR")
        net_bps = bps_of_notional(tr, "netR")
        R["anatomy"] = dict(
            n=len(tr), expR=float(tr["netR"].mean()),
            mean_gross_bps=float(gross_bps.mean()), mean_net_bps=float(net_bps.mean()),
            median_nights=float(tr["nights"].median()), mean_nights=float(tr["nights"].mean()),
            mean_cost_R=float(tr["cost_R"].mean()),
            risk0_over_px_pct=float((tr["risk0"] / tr["entry_px"]).mean() * 100),
            pnl_share_top1pct=float(np.sort(tr["netR"].values)[-max(1, len(tr) // 100):].sum()
                                    / tr["netR"].sum() * 100),
            pnl_share_top5pct=float(np.sort(tr["netR"].values)[-max(1, len(tr) // 20):].sum()
                                    / tr["netR"].sum() * 100),
        )
        by_cls = tr.groupby(["cls", "dir"])["netR"].agg(["count", "mean", "sum"])
        R["by_class"] = json.loads(by_cls.reset_index().to_json(orient="records"))
        by_i = tr.groupby("instr")["netR"].agg(["count", "mean", "sum"]).sort_values("sum")
        R["instr_worst_best"] = json.loads(
            pd.concat([by_i.head(4), by_i.tail(4)]).reset_index().to_json(orient="records"))

        # --- B. swap (L36) --------------------------------------------------
        sw = add_swap(tr)
        m_sw = lab.trade_metrics(sw.assign(netR=sw["netR_swap"]))
        by_cls_sw = sw.groupby(["cls", "dir"])["netR_swap"].agg(["count", "mean"])
        R["swap"] = dict(
            mean_swap_R=float(sw["swap_R"].mean()),
            mean_swap_bps=float((sw["swap_R"] * sw["risk0"] / sw["entry_px"] * 1e4).mean()),
            expR_after=float(sw["netR_swap"].mean()), sharpe_after=float(m_sw["sharpe"]),
            maxdd_after=float(m_sw["maxdd"]),
            long_after=float(sw.loc[sw["dir"] == 1, "netR_swap"].mean()),
            short_after=float(sw.loc[sw["dir"] == -1, "netR_swap"].mean()),
            share_of_gross_eaten=float(-sw["swap_R"].mean() / tr["grossR"].mean() * 100),
            by_class=json.loads(by_cls_sw.reset_index().to_json(orient="records")),
        )
        for mult, lab_ in ((0.5, "half"), (2.0, "double")):
            s2 = add_swap(tr, mult)
            R["swap"][f"expR_{lab_}"] = float(s2["netR_swap"].mean())

        # --- C. cost sensitivity (L33) --------------------------------------
        R["cost"] = {}
        for cm, lb in ((1.0, "as_audited"), (1.5, "x1.5"), (3.0, "x3")):
            p = run_point(variant, FLB_REP, TM_REP, cost_mult=cm)
            m = lab.trade_metrics(p)
            R["cost"][lb] = dict(expR=float(m["expR"]), sharpe=float(m["sharpe"]))

        # --- D. L58 unconditional baseline ----------------------------------
        R["l58"] = l58_baseline(variant, tag)

        # --- E. L38 beta orthogonality --------------------------------------
        R["l38_all"] = l38(tr)
        R["l38_long"] = l38(tr[tr["dir"] == 1])
        R["l38_short"] = l38(tr[tr["dir"] == -1])

        # --- F. regime / decay ----------------------------------------------
        eras = [(1999, 2007), (2008, 2012), (2013, 2018), (2019, 2026)]
        R["eras"] = []
        for a, b in eras:
            s = tr[(tr["year"] >= a) & (tr["year"] <= b)]
            if len(s) < 20:
                continue
            m = lab.trade_metrics(s)
            sws = add_swap(s)
            R["eras"].append(dict(era=f"{a}-{b}", n=len(s), expR=float(m["expR"]),
                                  sharpe=float(m["sharpe"]),
                                  expR_swap=float(sws["netR_swap"].mean()),
                                  long=float(s.loc[s["dir"] == 1, "netR"].mean()),
                                  short=float(s.loc[s["dir"] == -1, "netR"].mean())))
        RES[tag] = R
        print(f"===== {tag} =====")
        print(json.dumps(R, indent=1, default=str))

    with open(os.path.join(HERE, "mechanism.json"), "w") as f:
        json.dump(RES, f, indent=1, default=str)
