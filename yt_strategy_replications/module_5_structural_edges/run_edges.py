"""
Module 5 — the three directly-testable "structural edges" from video 5:
  (2) Opening Range Breakout (ORB) on NQ 1-min  — the "13.5% skew" claim
  (4) Variance Risk Premium (VRP)               — VIX vs realised SPY vol
  (5) Bitcoin smart-DCA (MVRV/price-z proxy)     — vs static DCA / buy & hold

PEAD and Congressional copy-trading are data-gated and assessed separately in the
report. Usage: python run_edges.py [orb|vrp|mvrv|all]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import stats as S  # noqa: E402

REPO = HERE.parent.parent
NQ_PATH = REPO / "data" / "raw" / "NQ_1min_databento_2010-2026.parquet"
MACRO = HERE.parent / "data_cache" / "equities" / "macro_daily.parquet"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)


# ============================================================ (2) ORB on NQ
def _day_orb(g, cost_pts, or_bars=30):
    g = g.sort_index()
    if len(g) < or_bars + 30:
        return None
    orb, sess = g.iloc[:or_bars], g.iloc[or_bars:]
    oh, ol = orb["high"].max(), orb["low"].min()
    R = oh - ol
    if R <= 0:
        return None
    H, L, C = sess["high"].to_numpy(), sess["low"].to_numpy(), sess["close"].to_numpy()
    up = np.argmax(H >= oh) if (H >= oh).any() else -1
    dn = np.argmax(L <= ol) if (L <= ol).any() else -1
    if up == -1 and dn == -1:
        return None
    if dn == -1 or (up != -1 and up <= dn):
        side, entry, k = 1, oh, up
    else:
        side, entry, k = -1, ol, dn
    tp, sl = entry + side * R, entry - side * R
    exit_px, reason = C[-1], "close"
    for j in range(k, len(C)):
        if side > 0:
            if L[j] <= sl:
                exit_px, reason = sl, "sl"; break
            if H[j] >= tp:
                exit_px, reason = tp, "tp"; break
        else:
            if H[j] >= sl:
                exit_px, reason = sl, "sl"; break
            if L[j] <= tp:
                exit_px, reason = tp, "tp"; break
    pnl = side * (exit_px - entry) - cost_pts
    sess_close = C[-1]
    follow = int((side > 0 and sess_close > entry) or (side < 0 and sess_close < entry))
    return {"side": side, "R_pts": R, "pnl_pts": pnl, "pnl_R": pnl / R, "reason": reason,
            "follow": follow}


def orb(cost_pts=1.5):
    df = pd.read_parquet(NQ_PATH, columns=["open", "high", "low", "close", "volume",
                                           "is_roll_day", "is_rth"])
    df = df[(df["is_rth"]) & (~df["is_roll_day"])]
    et = df.index.tz_convert("America/New_York")
    df = df.assign(d=et.normalize())
    recs = []
    for day, g in df.groupby("d"):
        r = _day_orb(g[["open", "high", "low", "close"]], cost_pts)
        if r:
            r["date"] = day
            recs.append(r)
    t = pd.DataFrame(recs).set_index("date").sort_index()
    daily = t["pnl_R"]
    # one trade per day -> ~252/yr for annualisation
    tdays_yr = len(t) / ((t.index[-1] - t.index[0]).days / 365.25)
    sharpe = S.sharpe_ratio(daily.to_numpy(), tdays_yr)
    _, hac = S.hac_tstat(daily.to_numpy())
    # gross (no cost) for skew claim
    follow_rate = float(t["follow"].mean())
    summary = dict(
        n_days=int(len(t)), follow_rate=follow_rate, directional_skew=follow_rate - 0.5,
        win_rate=float((t["pnl_pts"] > 0).mean()),
        expectancy_R_net=float(t["pnl_R"].mean()),
        expectancy_pts_net=float(t["pnl_pts"].mean()),
        sharpe_net=float(sharpe), hac_t=float(hac), cost_pts=cost_pts,
        frac_tp=float((t["reason"] == "tp").mean()), frac_sl=float((t["reason"] == "sl").mean()),
        total_pts_net=float(t["pnl_pts"].sum()),
    )
    # gross skew via zero cost (recompute expectancy without cost is pnl+cost)
    summary["expectancy_pts_gross"] = summary["expectancy_pts_net"] + cost_pts
    json.dump(summary, open(RESULTS / "orb_summary.json", "w"), indent=2)
    t.to_csv(RESULTS / "orb_trades.csv")
    print("[ORB]", json.dumps(summary, indent=2))

    eq = (t["pnl_pts"]).cumsum()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(eq.index, eq.values, color="seagreen", lw=1.2, label=f"ORB net ({cost_pts} pts/RT)")
    ax.plot(eq.index, (t["pnl_pts"] + cost_pts).cumsum().values, color="gray", ls="--", lw=1.0, label="gross")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Module 5 — NQ Opening-Range Breakout cumulative P&L (points)")
    ax.set_ylabel("Cumulative NQ points"); ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(RESULTS / "fig_orb.png", dpi=120); plt.close(fig)
    return summary


# ============================================================ (4) VRP
def vrp():
    d = pd.read_parquet(MACRO)
    vix, spy = d["^VIX"].dropna(), d["SPY"].dropna()
    r = np.log(spy / spy.shift(1)).dropna()
    rv_trail = r.rolling(21).std() * np.sqrt(252) * 100
    rv_fwd = rv_trail.shift(-21)                      # realised vol over the next ~month
    df = pd.DataFrame({"iv": vix, "rv_fwd": rv_fwd}).dropna()
    iv_gt = float((df["iv"] > df["rv_fwd"]).mean())
    # non-overlapping monthly variance premium (variance units, annualised)
    idx = df.index[::21]
    prem = ((df["iv"] / 100) ** 2 - (df["rv_fwd"] / 100) ** 2).loc[idx]
    pv = prem.to_numpy()
    summary = dict(
        n_months=int(len(prem)), iv_gt_rv_freq=iv_gt,
        mean_premium_var=float(pv.mean()), pct_months_positive=float((pv > 0).mean()),
        sharpe_annual=float(pv.mean() / pv.std() * np.sqrt(12)),
        skew=float(pd.Series(pv).skew()), kurtosis=float(pd.Series(pv).kurtosis()),
        worst_month=float(pv.min()), best_month=float(pv.max()),
        worst_to_mean_ratio=float(pv.min() / pv.mean()) if pv.mean() else float("nan"),
    )
    eq = np.cumsum(pv)
    mdd, _ = S.max_drawdown(1 + eq - eq.min() + 1e-9)
    summary["cum_maxdd_proxy"] = float(mdd)
    json.dump(summary, open(RESULTS / "vrp_summary.json", "w"), indent=2)
    print("[VRP]", json.dumps(summary, indent=2))

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), height_ratios=[1, 1])
    a1.plot(df.index, df["iv"], lw=0.7, label="VIX (implied vol)", color="navy")
    a1.plot(df.index, df["rv_fwd"], lw=0.7, label="SPY realised vol (fwd 1m)", color="darkorange")
    a1.legend(fontsize=8); a1.set_ylabel("vol %"); a1.set_title("Module 5 — VRP: implied (VIX) vs forward realised vol")
    a2.bar(prem.index, pv, width=20, color=["seagreen" if x > 0 else "indianred" for x in pv])
    a2.axhline(0, color="black", lw=0.8); a2.set_ylabel("monthly variance premium")
    a2.set_title("Short-variance monthly P&L (note left-tail crashes)")
    fig.tight_layout(); fig.savefig(RESULTS / "fig_vrp.png", dpi=120); plt.close(fig)
    return summary


# ============================================================ (5) MVRV smart-DCA (BTC)
def mvrv():
    d = pd.read_parquet(MACRO)
    btc = d["BTC-USD"].dropna()
    lp = np.log(btc)
    z = (lp - lp.rolling(365, min_periods=200).mean()) / lp.rolling(365, min_periods=200).std()
    wk = btc.resample("W").last().dropna()
    zwk = z.reindex(wk.index).ffill()
    px = wk.to_numpy()
    zz = np.nan_to_num(zwk.to_numpy(), nan=0.0)   # neutral weight during the z warmup

    def run_dca(weights):
        coins = np.cumsum(weights / px)           # coins held after each weekly buy
        invested = np.cumsum(weights)
        value = coins * px
        # mark-to-market drawdown of holdings
        mdd, _ = S.max_drawdown(value / invested)  # value per $ invested
        return dict(final_value=float(value[-1]), invested=float(invested[-1]),
                    multiple=float(value[-1] / invested[-1]), maxdd=float(mdd))

    n = len(px)
    static = run_dca(np.ones(n))
    w_dyn = np.clip(1.0 - zz, 0.1, 3.0)            # buy more when cheap (z<0), less when hot
    dynamic = run_dca(w_dyn)
    # buy & hold: all capital at start
    bh_value = (1.0 / px[0]) * px
    bh = dict(multiple=float(bh_value[-1] / 1.0), maxdd=float(S.max_drawdown(bh_value)[0]))

    summary = dict(start=str(wk.index[0].date()), end=str(wk.index[-1].date()),
                   static_DCA=static, dynamic_DCA=dynamic, buy_hold=bh,
                   dyn_vs_static_multiple=float(dynamic["multiple"] / static["multiple"]))
    json.dump(summary, open(RESULTS / "mvrv_summary.json", "w"), indent=2)
    print("[MVRV]", json.dumps(summary, indent=2))

    inv_s = np.cumsum(np.ones(n)); val_s = np.cumsum(np.ones(n) / px) * px
    inv_d = np.cumsum(w_dyn); val_d = np.cumsum(w_dyn / px) * px
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(wk.index, val_s / inv_s, label="static DCA (value / $ invested)", color="steelblue")
    ax.plot(wk.index, val_d / inv_d, label="dynamic DCA (z-scaled)", color="seagreen")
    ax.plot(wk.index, bh_value, label="buy & hold (×)", color="gray", ls="--", alpha=0.7)
    ax.set_yscale("log"); ax.axhline(1, color="black", lw=0.6)
    ax.set_title("Module 5 — Bitcoin smart-DCA (price-z proxy) vs static DCA / buy & hold")
    ax.set_ylabel("value per $ invested (log)"); ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(RESULTS / "fig_mvrv.png", dpi=120); plt.close(fig)
    return summary


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("orb", "all"):
        orb()
    if cmd in ("vrp", "all"):
        vrp()
    if cmd in ("mvrv", "all"):
        mvrv()
