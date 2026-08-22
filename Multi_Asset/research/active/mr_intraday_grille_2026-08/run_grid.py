"""
Executes the 396-cell grid pre-registered in PREREGISTRATION.md (Blocks 1-4).
Writes grille_resultats.csv (one row per variant) and t_distribution.json (the
full vector of gross-both HAC-t values, for the placebo/order-statistic comparison
done in placebo.py). Gross first (cost 0); net at the calibrated native cost is
also reported per PREREGISTRATION.md §2, but never gates the verdict.
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataload as DL
import engine_lib as E
from engine import indicators as ind

INSTRUMENTS = DL.ALL
H_BACKSTOP = 8
ATR_DEFAULT_K = 20


def bars_per_year(df: pd.DataFrame) -> float:
    return float(df.groupby("session_date").size().median()) * 252.0


def base_frame(sym: str, freq: str = "15min"):
    df = DL.load(sym, bar=freq)
    bpy = bars_per_year(df)
    scale = E.vol_target_scale(df, bars_per_year=bpy)
    cost = DL.COST_RT_BPS[sym] / 1e4
    no_entry_cache = {}
    return df, bpy, scale, cost, no_entry_cache


def no_entry_mask(df, H, cache):
    if H not in cache:
        b2e = E.bars_to_session_end(df)
        cache[H] = b2e <= H
    return cache[H]


def run_one(df, bpy, scale, cost, no_entry_cache, *, dist: pd.Series, mode: str, threshold,
           entry: str, sl_dist: np.ndarray, tp_dist: np.ndarray, max_hold: int, meta: dict):
    d = dist.to_numpy(float)
    d = np.nan_to_num(d, nan=(1e9 if mode == "signed" else 50.0))
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    if entry == "CROSS":
        long_m, short_m = E.entry_cross(d, threshold, mode)
    elif entry == "CONFIRM":
        long_m, short_m = E.entry_confirm(d, threshold, mode)
    elif entry == "REVERSAL_CANDLE":
        long_m, short_m = E.entry_reversal_candle(d, threshold, o, c, mode)
    else:
        raise ValueError(entry)
    ne = no_entry_mask(df, max_hold, no_entry_cache)
    sig = E.signal_from_masks(long_m, short_m, ne)
    res = E.run_cell(df, sig, sl_dist, tp_dist, max_hold, scale, cost, bpy, n_trials=396)
    res.update(meta)
    return res


def cell_bracket_sym(atr, sl_mult=1.0, tp_mult=1.0):
    return E.exit_atr_bracket(atr, sl_mult, tp_mult)


def main():
    t0 = time.time()
    rows = []
    for sym in INSTRUMENTS:
        df, bpy, scale, cost, ne_cache = base_frame(sym, "15min")
        close = df["close"]

        # ---- Block 1a: VWMA anchor, ATR-distance, k in {10,20,50}, z0 in {1.5,2,2.5}
        for k in (10, 20, 50):
            anchor = E.anchor_vwma(df, k)
            atr = ind.atr(df["high"], df["low"], df["close"], n=k)
            dist = E.dist_atr(close, anchor, atr)
            sl, tp = cell_bracket_sym(atr, 1.0, 1.0)
            for z0 in (1.5, 2.0, 2.5):
                meta = dict(block="1a_vwma_atr", sym=sym, freq="15min", anchor="VWMA", metric="ATR",
                           k=k, threshold=z0, entry="CROSS", exit="ATR_BRACKET_SYM_1_1_H8",
                           price_level="close")
                rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=dist, mode="signed",
                                    threshold=z0, entry="CROSS", sl_dist=sl, tp_dist=tp,
                                    max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 1b: inverse-vol-weighted MA anchor, ATR-distance, k in {10,20,50}
        for k in (10, 20, 50):
            anchor = E.anchor_ivol_ma(df, k)
            atr = ind.atr(df["high"], df["low"], df["close"], n=k)
            dist = E.dist_atr(close, anchor, atr)
            sl, tp = cell_bracket_sym(atr, 1.0, 1.0)
            for z0 in (1.5, 2.0, 2.5):
                meta = dict(block="1b_ivolma_atr", sym=sym, freq="15min", anchor="IVOL_MA",
                           metric="ATR", k=k, threshold=z0, entry="CROSS",
                           exit="ATR_BRACKET_SYM_1_1_H8", price_level="close")
                rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=dist, mode="signed",
                                    threshold=z0, entry="CROSS", sl_dist=sl, tp_dist=tp,
                                    max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 1c/1d/1e: session anchors, ATR20-distance, z0 in {1.0,1.5,2.0}
        atr20 = ind.atr(df["high"], df["low"], df["close"], n=ATR_DEFAULT_K)
        sl20, tp20 = cell_bracket_sym(atr20, 1.0, 1.0)
        session_anchors = {
            "1c_session_open": E.anchor_session_open(df),
            "1d_session_vwap": E.anchor_session_vwap(df),
            "1e_prior_close": E.anchor_prior_close(df),
        }
        for blk, anchor in session_anchors.items():
            dist = E.dist_atr(close, anchor, atr20)
            for z0 in (1.0, 1.5, 2.0):
                meta = dict(block=blk, sym=sym, freq="15min",
                           anchor={"1c_session_open": "SESSION_OPEN", "1d_session_vwap": "SESSION_VWAP",
                                   "1e_prior_close": "PRIOR_CLOSE"}[blk],
                           metric="ATR", k="NA", threshold=z0, entry="CROSS",
                           exit="ATR_BRACKET_SYM_1_1_H8", price_level="close")
                rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=dist, mode="signed",
                                    threshold=z0, entry="CROSS", sl_dist=sl20, tp_dist=tp20,
                                    max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 1f: price-level sweep, SMA20+zscore, z0=2.0 fixed, level in {open,typical,median}
        for lvl in ("open", "typical", "median"):
            level = E.price_level(df, lvl)
            dist = E.dist_zscore(level, 20)
            atr = atr20
            sl, tp = sl20, tp20
            meta = dict(block="1f_price_level", sym=sym, freq="15min", anchor="SMA", metric="ZSCORE",
                       k=20, threshold=2.0, entry="CROSS", exit="ATR_BRACKET_SYM_1_1_H8",
                       price_level=lvl)
            rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=dist, mode="signed",
                                threshold=2.0, entry="CROSS", sl_dist=sl, tp_dist=tp,
                                max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 1g: percentile-rank conditioner, k in {20,50}, thresholds (5,95)/(10,90)
        for k in (20, 50):
            pct = E.percentile_rank(close, k)
            atr = ind.atr(df["high"], df["low"], df["close"], n=k)
            sl, tp = cell_bracket_sym(atr, 1.0, 1.0)
            for lo, hi in ((5.0, 95.0), (10.0, 90.0)):
                meta = dict(block="1g_percentile", sym=sym, freq="15min", anchor="NA",
                           metric="PERCENTILE", k=k, threshold=f"{lo}/{hi}", entry="CROSS",
                           exit="ATR_BRACKET_SYM_1_1_H8", price_level="close")
                rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=pct, mode="percentile",
                                    threshold=(lo, hi), entry="CROSS", sl_dist=sl, tp_dist=tp,
                                    max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 2: entry-logic sweep. SMA20+zscore, z0=2.0, ATR_BRACKET_SYM(1:1,H=8)
        dist_sma20 = E.dist_zscore(close, 20)
        anchor_sma20 = ind.sma(close, 20)
        for entry in ("CROSS", "CONFIRM", "REVERSAL_CANDLE"):
            meta = dict(block="2_entry_logic", sym=sym, freq="15min", anchor="SMA", metric="ZSCORE",
                       k=20, threshold=2.0, entry=entry, exit="ATR_BRACKET_SYM_1_1_H8",
                       price_level="close")
            rows.append(run_one(df, bpy, scale, cost, ne_cache, dist=dist_sma20, mode="signed",
                                threshold=2.0, entry=entry, sl_dist=sl20, tp_dist=tp20,
                                max_hold=H_BACKSTOP, meta=meta))

        # ---- Block 3: exit-logic sweep. SMA20+zscore z0=2.0, entry=CROSS
        long_m, short_m = E.entry_cross(np.nan_to_num(dist_sma20.to_numpy(float), nan=1e9), 2.0, "signed")
        exits = []
        sl_a, tp_a = cell_bracket_sym(atr20, 1.0, 1.5)
        exits.append(("ATR_BRACKET_ASYM_1_1.5_H8", sl_a, tp_a, H_BACKSTOP))
        sl_mr, tp_mr = E.exit_mean_revert(close, anchor_sma20, atr20, 1.0, fraction=1.0)
        exits.append(("MEAN_REVERT_TARGET_H8", sl_mr, tp_mr, H_BACKSTOP))
        sl_f5, tp_f5 = E.exit_mean_revert(close, anchor_sma20, atr20, 1.0, fraction=0.5)
        exits.append(("FRACTION50_TARGET_H8", sl_f5, tp_f5, H_BACKSTOP))
        sl_t4, tp_t4 = E.exit_time_only(len(df))
        exits.append(("TIME_ONLY_H4", sl_t4, tp_t4, 4))
        sl_t16, tp_t16 = E.exit_time_only(len(df))
        exits.append(("TIME_ONLY_H16", sl_t16, tp_t16, 16))
        for ename, sl, tp, H in exits:
            ne = no_entry_mask(df, H, ne_cache)
            sig = E.signal_from_masks(long_m, short_m, ne)
            meta = dict(block="3_exit_logic", sym=sym, freq="15min", anchor="SMA", metric="ZSCORE",
                       k=20, threshold=2.0, entry="CROSS", exit=ename, price_level="close")
            res = E.run_cell(df, sig, sl, tp, H, scale, cost, bpy, n_trials=396)
            res.update(meta)
            rows.append(res)

        print(f"  {sym} 15min done ({len(rows)} cumulative rows, {time.time()-t0:.1f}s)", flush=True)

    # ---- Block 4: bar-frequency extension, 60-min, k in {20,50}
    # NB: H_BACKSTOP=8 (bars) is calibrated for 15-min sessions (26-36 bars/day); at
    # 60-min a session only has 6-9 bars, so an 8-bar no-entry-near-close guard would
    # blank out the entire session (caught by a 0-trade sanity check on first run).
    # H_60 is derived per-instrument from its own bars/day so the intraday-flat guard
    # still leaves room to enter.
    for sym in INSTRUMENTS:
        df60, bpy60, scale60, cost60, ne60 = base_frame(sym, "60min")
        close60 = df60["close"]
        bars_per_day_60 = df60.groupby("session_date").size().median()
        H_60 = max(2, int(bars_per_day_60 // 3))
        for k in (20, 50):
            dist = E.dist_zscore(close60, k)
            atr = ind.atr(df60["high"], df60["low"], df60["close"], n=k)
            sl, tp = cell_bracket_sym(atr, 1.0, 1.0)
            meta = dict(block="4_bar_frequency", sym=sym, freq="60min", anchor="SMA", metric="ZSCORE",
                       k=k, threshold=2.0, entry="CROSS", exit=f"ATR_BRACKET_SYM_1_1_H{H_60}",
                       price_level="close")
            rows.append(run_one(df60, bpy60, scale60, cost60, ne60, dist=dist, mode="signed",
                                threshold=2.0, entry="CROSS", sl_dist=sl, tp_dist=tp,
                                max_hold=H_60, meta=meta))
    print(f"Block 4 done ({len(rows)} total rows, {time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    cols = ["block", "sym", "freq", "anchor", "metric", "k", "threshold", "entry", "exit",
            "price_level", "n_trades", "gross_sr", "gross_t", "gross_bps_per_trade", "gross_wf",
            "gross_dsr", "long_sr", "long_t", "short_sr", "short_t", "net_sr", "net_t",
            "avg_bars_held", "frac_sl", "frac_tp", "frac_time", "win_rate"]
    out = out[[c for c in cols if c in out.columns]]
    out.to_csv(HERE / "grille_resultats.csv", index=False)
    tvec = out["gross_t"].dropna().tolist()
    (HERE / "t_distribution.json").write_text(json.dumps({"n_cells": len(out), "gross_t": tvec}))
    print(f"\nWrote {len(out)} rows -> grille_resultats.csv  ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
