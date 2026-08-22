"""
mr_univers_complet_2026-08 — Block A (canonical cell, M1-resolved) + Block B (RSI n=7/21/28)
+ Block C (Bollinger %B width) on the 7 new FX crosses. PREREGISTRATION.md §2-3.

Reuses, read-only:
  - engine_lib.py / dataload.py's conventions from mr_intraday_grille_2026-08 (generic library,
    no instrument-specific state, safe to import)
  - m1_resolve.py from mr_grille_suite_2026-08 (pure numpy functions, no side effects)
  - yt_strategy_replications/engine/{indicators,stats} (the shared, tracked engine)
Data itself comes from THIS study's own dataload_fx.py (writes confined to this folder).
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "Multi_Asset" / "research" / "active" / "mr_intraday_grille_2026-08"))
sys.path.insert(0, str(REPO / "Multi_Asset" / "research" / "active" / "mr_grille_suite_2026-08"))
sys.path.insert(0, str(REPO / "yt_strategy_replications"))

import engine_lib as E
import m1_resolve as MR
from engine import indicators as ind

import dataload_fx as DFX

N_TRIALS_LOCAL = 0  # filled in main() = number of cells this script itself runs (honest local n)
H_BACKSTOP = 8
W_MINUTES = H_BACKSTOP * 15


def bars_per_year(df):
    return float(df.groupby("session_date").size().median()) * 252.0


def m1_arrays(sym):
    df = DFX.build_m1(sym)
    ts_dt = df.index
    ts = ts_dt.values.astype("datetime64[ns]").astype(np.int64)
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    return ts, ts_dt, o, h, l, c


def map_15to1(ts15, ts1):
    idx = np.searchsorted(ts1, ts15)
    idx = np.clip(idx, 0, len(ts1) - 1)
    ok = ts1[idx] == ts15
    return np.where(ok, idx, -1)


def build_trades(et, xt, dirs, epx, xpx, reason):
    if not et:
        return pd.DataFrame(columns=["entry_time", "exit_time", "direction", "entry_px",
                                     "exit_px", "ret_gross", "reason"])
    entry_time = pd.DatetimeIndex(et); exit_time = pd.DatetimeIndex(xt)
    direction = np.asarray(dirs, float); entry_px = np.asarray(epx, float); exit_px = np.asarray(xpx, float)
    ret_gross = direction * (exit_px / entry_px - 1.0)
    return pd.DataFrame({"entry_time": entry_time, "exit_time": exit_time,
                        "direction": direction.astype(int), "entry_px": entry_px,
                        "exit_px": exit_px, "ret_gross": ret_gross, "reason": np.asarray(reason)})


def compute_metrics(trades, scale, cost_rt, days, n_trials):
    n_trades = int(len(trades))
    out = {"n_trades": n_trades}
    if n_trades < 10:
        out.update({k: float("nan") for k in
                   ["gross_sr", "gross_t", "gross_wf", "gross_dsr", "gross_bps_per_trade",
                    "long_sr", "long_t", "short_sr", "short_t", "net_sr", "net_t", "win_rate"]})
        return out

    def leg(sub):
        if sub.empty:
            return dict(sharpe=float("nan"), hac_t=float("nan"), dsr=float("nan"), wf=float("nan"))
        dr = E.trade_daily(sub, scale, 0.0, days)
        return E.leg_metrics(dr, E.PPY_DAILY, n_trials)

    g_both = leg(trades); g_long = leg(trades[trades["direction"] > 0])
    g_short = leg(trades[trades["direction"] < 0])
    net_dr = E.trade_daily(trades, scale, cost_rt, days)
    net = E.leg_metrics(net_dr, E.PPY_DAILY, n_trials)
    out.update({
        "gross_sr": g_both["sharpe"], "gross_t": g_both["hac_t"], "gross_wf": g_both["wf"],
        "gross_dsr": g_both["dsr"], "gross_bps_per_trade": float(trades["ret_gross"].mean() * 1e4),
        "long_sr": g_long["sharpe"], "long_t": g_long["hac_t"],
        "short_sr": g_short["sharpe"], "short_t": g_short["hac_t"],
        "net_sr": net["sharpe"], "net_t": net["hac_t"],
        "win_rate": float((trades["ret_gross"] > 0).mean()),
    })
    return out


# ---------------------------------------------------------------- Block A: canonical, M1-resolved

def run_block_a(sym, n_trials):
    df15 = DFX.load(sym, "15min")
    close = df15["close"]
    dist = E.dist_zscore(close, 20)
    atr20 = ind.atr(df15["high"], df15["low"], df15["close"], n=20)
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E.entry_cross(d, 2.0, "signed")
    b2e = E.bars_to_session_end(df15)
    no_entry = b2e <= H_BACKSTOP
    long_m = long_m & ~no_entry; short_m = short_m & ~no_entry

    ts1, ts1_dt, o1, h1, l1, c1 = m1_arrays(sym)
    ts15 = df15.index.values.astype("datetime64[ns]").astype(np.int64)
    map15 = map_15to1(ts15, ts1)

    idx15 = np.where(long_m | short_m)[0]
    direction_all = np.where(long_m[idx15], 1.0, -1.0)
    sl_arr = atr20.to_numpy(float); tp_arr = atr20.to_numpy(float)  # 1x ATR both sides

    et, xt, dirs, epx, xpx, reason = [], [], [], [], [], []
    next_allowed = -1
    n15 = len(df15)
    for k in range(idx15.size):
        i = idx15[k]; e15 = i + 1
        if e15 >= n15:
            continue
        idx1 = map15[e15]
        if idx1 < 0 or idx1 <= next_allowed:
            continue
        sl_d, tp_d = sl_arr[i], tp_arr[i]
        if not (np.isfinite(sl_d) and np.isfinite(tp_d) and sl_d > 0 and tp_d > 0):
            continue
        res = MR.resolve_bracket_one(idx1, direction_all[k], sl_d, tp_d, o1, h1, l1, c1, W_MINUTES)
        if res is None:
            continue
        et.append(df15.index[e15]); xt.append(ts1_dt[res["exit_idx"]])
        dirs.append(direction_all[k]); epx.append(res["entry_px"]); xpx.append(res["exit_px"])
        reason.append(res["reason"]); next_allowed = res["exit_idx"]

    trades = build_trades(et, xt, dirs, epx, xpx, reason)
    bpy = bars_per_year(df15)
    scale = E.vol_target_scale(df15, bars_per_year=bpy)
    cost = DFX.COST_RT_BPS[sym] / 1e4
    days = pd.DatetimeIndex(df15["session_date"].drop_duplicates().to_numpy())
    out = compute_metrics(trades, scale, cost, days, n_trials)
    out.update(dict(block="A_canonical_M1resolved", sym=sym, freq="15min->M1exit",
                   anchor="SMA", metric="ZSCORE", k=20, threshold=2.0, entry="CROSS",
                   exit="M1_BRACKET_SYM_1x_H8"))
    return out


# ---------------------------------------------------------------- Block B: RSI(n) conditioner

def run_block_b(sym, n_trials):
    rows = []
    df = DFX.load(sym, "15min")
    close = df["close"]
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    sl, tp = E.exit_atr_bracket(atr20, 1.0, 1.0)
    bpy = bars_per_year(df)
    scale = E.vol_target_scale(df, bars_per_year=bpy)
    cost = DFX.COST_RT_BPS[sym] / 1e4
    ne = E.bars_to_session_end(df) <= H_BACKSTOP
    days = pd.DatetimeIndex(df["session_date"].drop_duplicates().to_numpy())
    for n in (7, 21, 28):
        rsi = ind.rsi(close, n)
        r = rsi.to_numpy(float)
        prev = np.empty_like(r); prev[0] = np.nan; prev[1:] = r[:-1]
        for lo, hi in ((20.0, 80.0), (30.0, 70.0)):
            long_m = (prev <= lo) & (r > lo)   # CROSS back up through oversold threshold
            short_m = (prev >= hi) & (r < hi)  # CROSS back down through overbought threshold
            long_m = long_m & ~ne
            short_m = short_m & ~ne
            sig = E.signal_from_masks(long_m, short_m, np.zeros(len(df), dtype=bool))
            res = E.run_cell(df, sig, sl, tp, H_BACKSTOP, scale, cost, bpy, n_trials=n_trials)
            res.update(dict(block="B_rsi_bracket", sym=sym, freq="15min", anchor="NA",
                           metric=f"RSI{n}", k=n, threshold=f"{lo}/{hi}", entry="CROSS",
                           exit="ATR_BRACKET_SYM_1_1_H8"))
            rows.append(res)
    return rows


# ---------------------------------------------------------------- Block C: Bollinger %B width

def run_block_c(sym, n_trials):
    rows = []
    df = DFX.load(sym, "15min")
    close = df["close"]
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    sl, tp = E.exit_atr_bracket(atr20, 1.0, 1.0)
    bpy = bars_per_year(df)
    scale = E.vol_target_scale(df, bars_per_year=bpy)
    cost = DFX.COST_RT_BPS[sym] / 1e4
    ne = (E.bars_to_session_end(df) <= H_BACKSTOP)
    sma20 = ind.sma(close, 20)
    std20 = ind.rolling_std(close, 20)
    for width in (1.5, 2.0, 2.5):
        upper = sma20 + width * std20
        lower = sma20 - width * std20
        pctb = (close - lower) / (upper - lower)
        p = np.nan_to_num(pctb.to_numpy(float), nan=0.5)
        long_m = p < 0.0    # close below the lower band
        short_m = p > 1.0   # close above the upper band
        long_m = long_m & ~ne
        short_m = short_m & ~ne
        sig = E.signal_from_masks(long_m, short_m, np.zeros(len(df), dtype=bool))
        res = E.run_cell(df, sig, sl, tp, H_BACKSTOP, scale, cost, bpy, n_trials=n_trials)
        res.update(dict(block="C_bollinger_pctb", sym=sym, freq="15min", anchor="SMA20+/-std",
                       metric="PCTB", k=20, threshold=width, entry="CROSS_BAND",
                       exit="ATR_BRACKET_SYM_1_1_H8"))
        rows.append(res)
    return rows


def main():
    t0 = time.time()
    all_rows = []
    n_trials_local = 7 * (1 + 6 + 3)  # 7 symbols x (A:1 + B:6 + C:3) = 70 cells, this script's own N
    for sym in DFX.FX_NEW:
        all_rows.append(run_block_a(sym, n_trials_local))
        all_rows.extend(run_block_b(sym, n_trials_local))
        all_rows.extend(run_block_c(sym, n_trials_local))
        print(f"  {sym} done ({time.time()-t0:.1f}s, {len(all_rows)} cumulative rows)", flush=True)

    out = pd.DataFrame(all_rows)
    cols = ["block", "sym", "freq", "anchor", "metric", "k", "threshold", "entry", "exit",
            "n_trades", "gross_sr", "gross_t", "gross_bps_per_trade", "gross_wf", "gross_dsr",
            "long_sr", "long_t", "short_sr", "short_t", "net_sr", "net_t", "win_rate"]
    out = out[[c for c in cols if c in out.columns]]
    out.to_csv(HERE / "grille_fx_new.csv", index=False)
    print(f"\nWrote {len(out)} rows -> grille_fx_new.csv ({time.time()-t0:.1f}s total, n_trials_local={n_trials_local})")


if __name__ == "__main__":
    main()
