"""
Main driver — intraday-momentum grid (see PREREGISTRATION.md). Runs every pre-registered cell,
gross-first, costs a cell only if gross_bps_per_trade > 0, writes one row per cell to
`grille_resultats.csv`. Interpreter: /usr/bin/python3.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "mr_intraday_grille_2026-08"))
import engine_lib as EL
sys.path.insert(0, str(HERE))  # inserted LAST -> highest priority, shadows the sister dataload.py
import dataload as DL
import signals as SG

N_TRIALS_CUM = 1867  # 1526 (MR family) + 341 (this grid) -- PREREGISTRATION.md §9
ROWS = []


def bars_per_year(symbol):
    return DL.BARS_PER_DAY[symbol] * 252


def base_row(symbol, block, construction, meta, out):
    net_eligible = out.get("gross_bps_per_trade", float("nan")) > 0
    row = {
        "block": block, "symbol": symbol, "construction": construction,
        "net_eligible": net_eligible,
        "l33b_pass": out.get("gross_bps_per_trade", float("nan")) > DL.L33B_GROSS_FLOOR_BPS,
        "cost_rt_bps": DL.COST_RT_BPS[symbol],
    }
    row.update(meta)
    row.update(out)
    if not net_eligible:
        row["net_sr"] = float("nan"); row["net_t"] = float("nan")
    return row


def run_and_record(df, symbol, block, construction, sig, sl, tp, max_hold, meta):
    scale = EL.vol_target_scale(df, bars_per_year(symbol))
    meta = dict(meta)
    capped = meta.pop("_capped", False)
    if capped:
        out = SG.run_cell_capped(df, sig, sl, tp, max_hold, scale, DL.COST_RT_BPS[symbol] / 1e4,
                                 n_trials=N_TRIALS_CUM)
    else:
        out = EL.run_cell(df, sig, sl, tp, max_hold, scale, DL.COST_RT_BPS[symbol] / 1e4,
                          bars_per_year(symbol), n_trials=N_TRIALS_CUM)
    ROWS.append(base_row(symbol, block, construction, meta, out))


def qcut_bucket(values_at_trigger, labels):
    try:
        return pd.qcut(values_at_trigger, len(labels), labels=labels, duplicates="drop")
    except ValueError:
        return pd.Series(["NA"] * len(values_at_trigger))


def run_conditioning(df, symbol, construction, sig, sl, tp, max_hold, meta, cond_values, cond_name, labels):
    trig_idx = np.where(sig != 0)[0]
    if len(trig_idx) < 30:
        return
    vals = cond_values[trig_idx]
    valid = np.isfinite(vals)
    if valid.sum() < 30:
        return
    buckets = qcut_bucket(vals[valid], labels)
    scale = EL.vol_target_scale(df, bars_per_year(symbol))
    for lab in labels:
        keep = trig_idx[valid][np.asarray(buckets) == lab]
        if len(keep) < 15:
            continue
        sub_sig = np.zeros_like(sig)
        sub_sig[keep] = sig[keep]
        out = EL.run_cell(df, sub_sig, sl, tp, max_hold, scale, DL.COST_RT_BPS[symbol] / 1e4,
                          bars_per_year(symbol), n_trials=N_TRIALS_CUM)
        m = dict(meta); m[cond_name] = str(lab)
        ROWS.append(base_row(symbol, "conditioning", construction, m, out))


def run_dow(df, symbol, construction, sig, sl, tp, max_hold, meta):
    trig_idx = np.where(sig != 0)[0]
    if len(trig_idx) < 30:
        return
    dow = df.index[trig_idx].dayofweek
    scale = EL.vol_target_scale(df, bars_per_year(symbol))
    for d, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        keep = trig_idx[dow == d]
        if len(keep) < 15:
            continue
        sub_sig = np.zeros_like(sig)
        sub_sig[keep] = sig[keep]
        out = EL.run_cell(df, sub_sig, sl, tp, max_hold, scale, DL.COST_RT_BPS[symbol] / 1e4,
                          bars_per_year(symbol), n_trials=N_TRIALS_CUM)
        m = dict(meta); m["dow"] = name
        ROWS.append(base_row(symbol, "conditioning", construction, m, out))


def main():
    t0 = time.time()
    core9 = DL.CORE9

    # ---- Block A: Gao early-window return -------------------------------------------------
    for symbol in core9:
        df = DL.load(symbol)
        for K in (2, 4):
            for H in ("8bars", "rest"):
                for exit_type in ("X1", "X2"):
                    sig, sl, tp, mh, meta = SG.construction_a(df, K, H, exit_type, DL.BARS_PER_DAY, symbol)
                    run_and_record(df, symbol, "A_gao_window", "A", sig, sl, tp, mh, meta)
        print(f"A done {symbol} t={time.time()-t0:.0f}s", flush=True)

    # ---- Block B: ORB breakout --------------------------------------------------------------
    for symbol in core9:
        df = DL.load(symbol)
        for K in (2, 4):
            for exit_type in ("X2", "X4"):
                sig, sl, tp, mh, meta = SG.construction_b(df, K, exit_type, DL.BARS_PER_DAY, symbol)
                run_and_record(df, symbol, "B_orb", "B", sig, sl, tp, mh, meta)
        print(f"B done {symbol} t={time.time()-t0:.0f}s", flush=True)

    # ---- Block C: gap continuation -----------------------------------------------------------
    gap_cache = {}
    for symbol in core9:
        df = DL.load(symbol)
        for g0 in (0.5, 1.0):
            for H in ("8bars", "rest"):
                for exit_type in ("X1", "X2"):
                    sig, sl, tp, mh, meta, gz = SG.construction_c(df, g0, H, exit_type, DL.BARS_PER_DAY, symbol)
                    run_and_record(df, symbol, "C_gap_cont", "C", sig, sl, tp, mh, meta)
                    if g0 == 1.0 and H == "rest" and exit_type == "X1":
                        gap_cache[symbol] = (df, sig, sl, tp, mh, meta, gz)
        print(f"C done {symbol} t={time.time()-t0:.0f}s", flush=True)

    # ---- Block D: prior-session range position -----------------------------------------------
    for symbol in core9:
        df = DL.load(symbol)
        for (p_hi, p_lo) in ((0.8, 0.2), (0.9, 0.1)):
            for H in ("8bars", "rest"):
                sig, sl, tp, mh, meta = SG.construction_d(df, p_hi, p_lo, H, DL.BARS_PER_DAY, symbol)
                run_and_record(df, symbol, "D_range_position", "D", sig, sl, tp, mh, meta)
        print(f"D done {symbol} t={time.time()-t0:.0f}s", flush=True)

    # ---- Block E: cross-sectional lead-lag (indices only) -------------------------------------
    idx_dfs = {s: DL.load(s) for s in DL.INDICES}
    for leader in DL.INDICES:
        sig_l, sl_l, tp_l, mh_l, meta_l = SG.construction_a(
            idx_dfs[leader], K=2, H="rest", exit_type="X1", bars_per_day=DL.BARS_PER_DAY, symbol=leader)
        for follower in DL.INDICES:
            if follower == leader:
                continue
            df_f = idx_dfs[follower]
            # align leader's trigger (by timestamp) onto follower's bar index
            leader_idx = idx_dfs[leader].index
            trig_ts = leader_idx[sig_l != 0]
            trig_dir = sig_l[sig_l != 0]
            pos_map = pd.Series(trig_dir, index=trig_ts)
            aligned = df_f.index.map(lambda t: pos_map.get(t, 0.0))
            sig_f = np.asarray(aligned, dtype=float)
            mh = SG._rest_hold(follower, DL.BARS_PER_DAY)
            sl_f, tp_f = SG._time_only(len(df_f))
            meta = {"K": 2, "H": "rest", "exit": "X1", "leader": leader}
            run_and_record(df_f, follower, "E_cross_sectional", "E", sig_f, sl_f, tp_f, mh, meta)
    print(f"E done t={time.time()-t0:.0f}s", flush=True)

    # ---- Block F: FX-cross extension (canonical A + canonical B only) -------------------------
    for symbol in DL.FX_CROSS:
        df = DL.load(symbol)
        sig, sl, tp, mh, meta = SG.construction_a(df, K=2, H="rest", exit_type="X1", bars_per_day=DL.BARS_PER_DAY, symbol=symbol)
        run_and_record(df, symbol, "F_fx_cross_ext", "A", sig, sl, tp, mh, meta)
        sig, sl, tp, mh, meta = SG.construction_b(df, K=2, exit_type="X4", bars_per_day=DL.BARS_PER_DAY, symbol=symbol)
        run_and_record(df, symbol, "F_fx_cross_ext", "B", sig, sl, tp, mh, meta)
        print(f"F done {symbol} t={time.time()-t0:.0f}s", flush=True)

    # ---- Block G: conditioning (vol tercile + day-of-week on A-canonical; gap tercile on C) ----
    for symbol in core9:
        df = DL.load(symbol)
        sig, sl, tp, mh, meta = SG.construction_a(df, K=2, H="rest", exit_type="X1", bars_per_day=DL.BARS_PER_DAY, symbol=symbol)
        # realized-vol tercile: 20-session rolling std of daily close-to-close return, causal
        daily_close = df.groupby("session_date")["close"].last()
        daily_ret = daily_close.pct_change()
        rv20 = daily_ret.rolling(20, min_periods=20).std(ddof=0).shift(1)
        rv_full = df["session_date"].map(rv20).to_numpy()
        run_conditioning(df, symbol, "A_vol_tercile", sig, sl, tp, mh, dict(meta),
                         rv_full, "vol_tercile", ["Low", "Mid", "High"])
        run_dow(df, symbol, "A_dow", sig, sl, tp, mh, dict(meta))

        dfC, sigC, slC, tpC, mhC, metaC, gzC = gap_cache[symbol]
        run_conditioning(dfC, symbol, "C_gap_tercile", sigC, slC, tpC, mhC, dict(metaC),
                         np.abs(gzC), "gap_tercile", ["Low", "Mid", "High"])
        print(f"G done {symbol} t={time.time()-t0:.0f}s", flush=True)

    out = pd.DataFrame(ROWS)
    out.to_csv(HERE / "grille_resultats.csv", index=False)
    print(f"TOTAL cells: {len(out)}  elapsed {time.time()-t0:.0f}s")
    print(out["block"].value_counts())


if __name__ == "__main__":
    main()
