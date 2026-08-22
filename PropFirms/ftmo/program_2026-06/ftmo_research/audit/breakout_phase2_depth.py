"""
breakout_phase2_depth.py — Depth on two-sided survivors from phase 1.

For each survivor (from breakout_phase1_full.csv where two_sided_pass=True):
  1. Re-extract trades with multiple EXIT variants:
       - EOD (baseline)
       - Trail-ATR (give back 1×ATR from peak)
       - Trail-BE @ 1R (move stop to breakeven after +1R)
       - TP partial @ +2R (take half, runner to EOD)
  2. Test FILTER variants:
       - No filter (baseline)
       - HTF trend filter: only long if H1-EMA20 above H1-EMA50, only short opposite
       - Vol regime: only trade if rv20 (intraday vol) in mid/high tercile
  3. Cost sensitivity: 0.5, 1, 2, 3 bps RT.
  4. By-year + by-regime breakdown.
  5. Delay-1 sensitivity (same logic as phase 1).
  6. Reconciliation with the ORB-30min result we already have.

Output: structured comparison table per survivor.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache
from breakout_deepdive import (
    load_nq_5min, extract_all_trades, compute_metrics, cluster_t_stat,
    signal_orb, signal_donchian, signal_vol_breakout, signal_squeeze,
    signal_pdh_pdl, signal_bollinger, signal_range_expansion,
    VARIANTS,
)


SIGNAL_FN_MAP = {name: (fn, kwargs, needs_prior) for name, fn, kwargs, needs_prior in VARIANTS}


REGIMES_TAGS = [
    ("2010-12_recovery",   "2010-06-07", "2012-12-31", "trending"),
    ("2013-14_qe_trend",   "2013-01-01", "2014-12-31", "trending"),
    ("2015-16_china_chop", "2015-01-01", "2016-06-30", "chop"),
    ("2016H2-17_trend",    "2016-07-01", "2017-12-31", "trending"),
    ("2018_vol_shock",     "2018-01-01", "2018-12-31", "vol_shock"),
    ("2019_dovish_pivot",  "2019-01-01", "2019-12-31", "trending"),
    ("2020_covid",         "2020-01-01", "2020-12-31", "vol_shock"),
    ("2021_recovery",      "2021-01-01", "2021-12-31", "trending"),
    ("2022_bear",          "2022-01-01", "2022-12-31", "trending"),
    ("2023_chop",          "2023-01-01", "2023-12-31", "chop"),
    ("2024-26_bull",       "2024-01-01", "2026-05-29", "trending"),
]


# ---------- Exit variants ----------
def exit_R(day_bars: pd.DataFrame, sig: dict, exit_type: str = "EOD",
            cost_bps: float = 1.0, exec_model: str = "EXEC_0",
            trail_atr_mult: float = 1.0, tp_R: float = 2.0,
            partial_frac: float = 0.5, be_trigger_R: float = 1.0) -> dict:
    """Compute R under various exit variants."""
    direction = sig["direction"]
    level = sig["level"]
    stop_level = sig["stop_level"]
    or_range = sig["or_range"]
    bi = sig["entry_bar"]
    H = day_bars["high"].values
    L = day_bars["low"].values
    C = day_bars["close"].values
    O = day_bars["open"].values

    if exec_model == "EXEC_0":
        entry_bar = bi
        entry = level
    else:
        if bi + 1 >= len(O):
            return {"r_net": np.nan, "outcome": "OOB"}
        entry_bar = bi + 1
        entry = O[bi + 1]

    cost_pts = cost_bps * level / 10000.0
    fh = H[entry_bar:]
    fl = L[entry_bar:]
    fc = C[entry_bar:]

    # Baseline stop check
    if direction == 1:
        stop_hit = np.where(fl <= stop_level)[0]
    else:
        stop_hit = np.where(fh >= stop_level)[0]
    first_stop = stop_hit[0] if len(stop_hit) else 10**9

    if exit_type == "EOD":
        if first_stop < len(fh):
            exit_px = stop_level
        else:
            exit_px = C[-1]
        r_gross = direction * (exit_px - entry) / or_range
        return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range,
                "outcome": "STOP" if first_stop < len(fh) else "EOD"}

    if exit_type == "TP_2R_partial":
        # Half off at +2R, runner to EOD (or stop)
        tp_px = entry + direction * tp_R * or_range
        if direction == 1:
            tp_hit = np.where(fh >= tp_px)[0]
        else:
            tp_hit = np.where(fl <= tp_px)[0]
        first_tp = tp_hit[0] if len(tp_hit) else 10**9
        if first_stop < first_tp:
            # Full stop before TP
            r_gross = direction * (stop_level - entry) / or_range
            return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range,
                    "outcome": "STOP"}
        if first_tp == 10**9:
            # Neither hit, exit at EOD
            r_gross = direction * (C[-1] - entry) / or_range
            return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range,
                    "outcome": "EOD"}
        # TP hit first — take partial, runner with same stop
        partial_r = tp_R - (cost_pts / 2) / or_range
        if direction == 1:
            runner_stop = np.where(fl[first_tp:] <= stop_level)[0]
        else:
            runner_stop = np.where(fh[first_tp:] >= stop_level)[0]
        if len(runner_stop):
            runner_exit = stop_level
        else:
            runner_exit = C[-1]
        runner_r = direction * (runner_exit - entry) / or_range - (cost_pts / 2) / or_range
        r_net = partial_frac * partial_r + (1 - partial_frac) * runner_r
        return {"r_gross": partial_frac * tp_R + (1 - partial_frac) * direction * (runner_exit - entry) / or_range,
                "r_net": r_net, "outcome": "PARTIAL"}

    if exit_type == "trail_BE@1R":
        # When profit hits +1R, move stop to entry. Then EOD or stop.
        trigger_px = entry + direction * be_trigger_R * or_range
        if direction == 1:
            trig_hit = np.where(fh >= trigger_px)[0]
        else:
            trig_hit = np.where(fl <= trigger_px)[0]
        first_trig = trig_hit[0] if len(trig_hit) else 10**9
        if first_stop < first_trig:
            # Stop hit before trigger — full -1R
            r_gross = direction * (stop_level - entry) / or_range
            return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range,
                    "outcome": "STOP"}
        if first_trig == 10**9:
            # Never reached +1R — original stop or EOD
            if first_stop < len(fh):
                exit_px = stop_level
                out = "STOP"
            else:
                exit_px = C[-1]
                out = "EOD"
            r_gross = direction * (exit_px - entry) / or_range
            return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range, "outcome": out}
        # Triggered: stop now at entry
        new_stop = entry
        if direction == 1:
            new_stop_hit = np.where(fl[first_trig:] <= new_stop)[0]
        else:
            new_stop_hit = np.where(fh[first_trig:] >= new_stop)[0]
        if len(new_stop_hit):
            exit_px = new_stop
            out = "BE"
        else:
            exit_px = C[-1]
            out = "EOD"
        r_gross = direction * (exit_px - entry) / or_range
        return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range, "outcome": out}

    if exit_type == "trail_ATR":
        # Trailing stop at peak − trail_atr_mult × or_range (rough proxy for ATR)
        trail_dist = trail_atr_mult * or_range
        peak = entry
        exit_px = None
        out = "EOD"
        for k in range(len(fh)):
            if direction == 1:
                peak = max(peak, fh[k])
                t_stop = peak - trail_dist
                # Also respect original stop
                eff_stop = max(t_stop, stop_level)
                if fl[k] <= eff_stop:
                    exit_px = eff_stop
                    out = "TRAIL_STOP"
                    break
            else:
                peak = min(peak, fl[k])
                t_stop = peak + trail_dist
                eff_stop = min(t_stop, stop_level)
                if fh[k] >= eff_stop:
                    exit_px = eff_stop
                    out = "TRAIL_STOP"
                    break
        if exit_px is None:
            exit_px = C[-1]
        r_gross = direction * (exit_px - entry) / or_range
        return {"r_gross": r_gross, "r_net": r_gross - cost_pts / or_range, "outcome": out}

    raise ValueError(exit_type)


def extract_with_exits(survivor_name: str, exit_types: list[str],
                        cost_bps: float = 1.0) -> pd.DataFrame:
    sig_fn, sig_kwargs, needs_prior = SIGNAL_FN_MAP[survivor_name]
    # Use optimized per-day cache from phase 1 module
    from breakout_deepdive import _get_per_day_bars, load_nq_5min
    per_day = _get_per_day_bars()
    days = sorted(per_day.keys())
    # Pre-compute prior data
    if needs_prior:
        df_5m = load_nq_5min()
        daily_close = df_5m.groupby(df_5m.index.date)["close"].last()
        daily_high = df_5m.groupby(df_5m.index.date)["high"].max()
        daily_low = df_5m.groupby(df_5m.index.date)["low"].min()
        prior_close_map = {pd.Timestamp(k): v for k, v in daily_close.shift(1).to_dict().items()}
        atr20_map = {pd.Timestamp(k): v for k, v in (daily_high - daily_low).rolling(20).mean().shift(1).to_dict().items()}
        pdh_map = {pd.Timestamp(k): v for k, v in daily_high.shift(1).to_dict().items()}
        pdl_map = {pd.Timestamp(k): v for k, v in daily_low.shift(1).to_dict().items()}
    import inspect as _inspect
    params_set = set(_inspect.signature(sig_fn).parameters.keys())
    rows = []
    for day in days:
        day_bars = per_day[day]
        if len(day_bars) < 30:
            continue
        kwargs = sig_kwargs.copy()
        if needs_prior:
            if "prior_close" in params_set:
                kwargs["prior_close"] = prior_close_map.get(day, np.nan)
            if "atr20" in params_set:
                kwargs["atr20"] = atr20_map.get(day, np.nan)
            if "pdh" in params_set:
                kwargs["pdh"] = pdh_map.get(day, np.nan)
            if "pdl" in params_set:
                kwargs["pdl"] = pdl_map.get(day, np.nan)
        sig = sig_fn(day_bars, **kwargs)
        if sig is None:
            continue
        row = {"date": pd.Timestamp(day), "signal": survivor_name,
                "direction": sig["direction"], "level": sig["level"],
                "or_range": sig["or_range"]}
        for et in exit_types:
            r = exit_R(day_bars, sig, exit_type=et, cost_bps=cost_bps)
            row[f"r_net_{et}"] = r["r_net"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def add_regime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["regime"] = "unknown"
    df["regime_tag"] = "unknown"
    for name, lo, hi, tag in REGIMES_TAGS:
        mask = (df.index >= pd.Timestamp(lo)) & (df.index <= pd.Timestamp(hi))
        df.loc[mask, "regime"] = name
        df.loc[mask, "regime_tag"] = tag
    return df


if __name__ == "__main__":
    # Load phase 1 results
    df_phase1 = pd.read_csv("breakout_phase1_full.csv")
    survivors = df_phase1[df_phase1["two_sided_pass"]]["variant"].tolist()
    print("=" * 110)
    print(f"PHASE 2 — Depth on {len(survivors)} two-sided survivors")
    print("=" * 110)
    print(f"Survivors: {survivors}")
    print()

    if len(survivors) == 0:
        print("\n⚠ NO TWO-SIDED SURVIVORS from Phase 1.")
        print("The breakout family on NQ 2010-2026 has a structural long-bias (L25 'beta in disguise').")
        print("Phase 2 cannot proceed without survivors.")
        print()
        # Save empty deliverable signal
        with open("breakout_phase2_no_survivors.txt", "w") as f:
            f.write("No two-sided survivors from Phase 1.\n")
        exit(0)

    exit_types = ["EOD", "trail_BE@1R", "TP_2R_partial", "trail_ATR"]
    all_rows = []
    for sname in survivors:
        print(f"\n--- {sname} ---")
        df = extract_with_exits(sname, exit_types, cost_bps=1.0)
        df = add_regime(df)
        df.to_parquet(f"breakout_phase2_trades_{sname}.parquet")

        for et in exit_types:
            r_col = f"r_net_{et}"
            m = compute_metrics(df.rename(columns={r_col: "r_net_exec0"}), r_col="r_net_exec0")
            m["variant"] = sname
            m["exit_type"] = et
            all_rows.append(m)
            print(f"  {et:>20s}: n={m['n_total']:>4d} total={m['mean_R_total']:+.3f} "
                  f"long={m['mean_R_long']:+.3f} short={m['mean_R_short']:+.3f} "
                  f"(t_short={m['t_stat_short']:+.2f})")

    df_phase2 = pd.DataFrame(all_rows)
    df_phase2.to_csv("breakout_phase2_full.csv", index=False)
    print()
    print("=" * 110)
    print("PHASE 2 SUMMARY")
    print("=" * 110)
    piv = df_phase2.pivot_table(index="variant", columns="exit_type",
                                  values="mean_R_total")
    print("\nMean R total by (variant × exit):")
    print(piv.round(4).to_string())
    piv2 = df_phase2.pivot_table(index="variant", columns="exit_type",
                                   values="mean_R_short")
    print("\nMean R SHORT-ONLY by (variant × exit):")
    print(piv2.round(4).to_string())
