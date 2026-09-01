"""
Config search for "Dedale" -- adds the TDI filter block (tdi.py) on top of the existing
carry+pivot skeleton engine (dedale_strategy_2026-08/code/dedale_engine.py, reused unmodified via
import). NOT an optimization for Sharpe/P&L: the objective is DISTANCE TO THE AUTHOR'S DECLARED
METADATA (trades/pair/year ~3.5, win rate ~63.58%, avg hold ~11 days), per the identification
mandate -- Sharpe/P&L are reported for context only, never used to pick a winner.

Usage:
    /usr/bin/python3 search_engine.py single      # 15 single-filter configs, all 7 pairs
    /usr/bin/python3 search_engine.py angle_only   # isolates the rejection rate of the angle band
    /usr/bin/python3 search_engine.py h4cross      # Config B sensitivity (video-4 demo config)
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ENGINE_DIR = Path("<HOME>/Desktop/Algo_claude_dedale2/Forex/research/active/"
                   "dedale_strategy_2026-08/code")
sys.path.insert(0, str(ENGINE_DIR))
import dedale_engine as de  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tdi  # noqa: E402

CACHE_DIR = de.CACHE_DIR
OUT_DIR = Path(__file__).resolve().parent.parent

FILTER_NAMES = []
for tf_idx in range(5):
    for kind in ["CROSS", "TREND", "ANGLE"]:
        FILTER_NAMES.append(f"TDI_TIMEFRAME{tf_idx}_{kind}")


def load_m1_close(pair: str) -> pd.Series:
    df = pd.read_parquet(CACHE_DIR / f"{pair}_M1.parquet")
    return df["close"]


def run_pair_filtered(pair: str, active_filters: set, tf_cache: dict = None,
                       verbose: bool = False) -> pd.DataFrame:
    """active_filters: set of (tf_idx, kind) with kind in {'CROSS','TREND','ANGLE'}. Empty set =
    config A (identical to dedale_engine.run_pair with direction_mode='swap')."""
    t0 = time.time()
    base, quote = de.PAIR_CCY[pair]
    h1 = de.load_h1(pair)
    piv = de.load_weekly_pivots(pair)
    rate_diff = de.load_rate_diff(base, quote)
    pip = de.pip_size(pair)
    sl_min = de.SL_DISTANCE_MIN_PIPS * pip
    tp_min = de.TP_DISTANCE_MIN_PIPS * pip

    piv_al = piv.reindex(h1.index, method="ffill")
    rd_al = rate_diff.reindex(h1.index, method="ffill")

    needed_tfs = sorted({tf for tf, _ in active_filters})
    if tf_cache is None:
        tf_cache = {}
    if needed_tfs and pair not in tf_cache:
        m1_close = load_m1_close(pair)
        tf_cache[pair] = tdi.build_all_tf_conditions(m1_close, h1.index)
    tf_conditions = tf_cache.get(pair, {})

    idx = h1.index
    o = h1["open"].values
    hi = h1["high"].values
    lo = h1["low"].values
    cl = h1["close"].values
    S1 = piv_al["S1"].values
    S2 = piv_al["S2"].values
    R1 = piv_al["R1"].values
    R2 = piv_al["R2"].values
    rd = rd_al.values

    # precompute per-direction admission arrays for each active filter (vectorized), then AND them
    n = len(h1)
    buy_ok = np.ones(n, dtype=bool)
    sell_ok = np.ones(n, dtype=bool)
    for tf_idx, kind in active_filters:
        cdf = tf_conditions[tf_idx]
        if kind == "CROSS":
            buy_ok &= cdf["cross_up"].fillna(False).values
            sell_ok &= cdf["cross_down"].fillna(False).values
        elif kind == "TREND":
            buy_ok &= cdf["trend_up"].fillna(False).values
            sell_ok &= cdf["trend_down"].fillna(False).values
        elif kind == "ANGLE":
            buy_ok &= cdf["angle_buy_ok"].fillna(False).values
            sell_ok &= cdf["angle_sell_ok"].fillna(False).values

    trades = []
    position = None
    n_raw_signals = 0  # candidate bars where swap-direction + pivot band would have fired, pre-TDI
    n_tdi_pass = 0

    for t in range(1, n - 1):
        if position is None:
            if np.isnan(S1[t]) or np.isnan(rd[t]):
                continue
            diff = rd[t]
            if diff == 0:
                continue
            direction = 0 if diff > 0 else 1
            mid = cl[t]
            sl, tp = de.get_trade_info(direction, mid, mid, S1[t], S2[t], R1[t], R2[t])
            if direction == 0:
                dist_sl = mid - sl
                dist_tp = tp - mid
            else:
                dist_sl = sl - mid
                dist_tp = mid - tp
            if dist_sl < sl_min or dist_tp < tp_min or dist_sl <= 0 or dist_tp <= 0:
                continue
            n_raw_signals += 1
            if active_filters:
                ok = buy_ok[t] if direction == 0 else sell_ok[t]
                if not ok:
                    continue
            n_tdi_pass += 1
            entry_time = idx[t + 1]
            entry_price = o[t + 1]
            position = dict(direction=direction, entry_idx=t + 1, entry_time=entry_time,
                             entry_price=entry_price, sl=sl, tp=tp,
                             sl_dist=dist_sl, tp_dist=dist_tp, rate_diff_entry=diff)
        else:
            d = position["direction"]
            exit_price = None
            reason = None
            if d == 0:
                if lo[t] <= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif hi[t] >= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            else:
                if hi[t] >= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif lo[t] <= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            if exit_price is not None:
                entry_price = position["entry_price"]
                if d == 0:
                    r_multiple = (exit_price - entry_price) / position["sl_dist"]
                else:
                    r_multiple = (entry_price - exit_price) / position["sl_dist"]
                entry_time = position["entry_time"]
                exit_time = idx[t]
                hold_days = (exit_time - entry_time).total_seconds() / 86400.0
                nights = 0.0
                day = entry_time.normalize()
                end_day = exit_time.normalize()
                while day < end_day:
                    mult = 3 if day.dayofweek == de.SWAP_TRIPLE_DOW else 1
                    nights += mult
                    day = day + pd.Timedelta(days=1)
                sign = 1 if d == 0 else -1
                swap_bps_annual = sign * position["rate_diff_entry"]
                frac_to_sl = position["sl_dist"] / entry_price
                notional_per_risk_unit = 1.0 / frac_to_sl if frac_to_sl > 0 else np.nan
                trades.append(dict(
                    pair=pair, direction="buy" if d == 0 else "sell",
                    entry_time=entry_time, exit_time=exit_time, exit_reason=reason,
                    entry_price=entry_price, exit_price=exit_price,
                    sl=position["sl"], tp=position["tp"],
                    r_multiple=r_multiple, hold_days=hold_days, nights=nights,
                    notional_per_risk_unit=notional_per_risk_unit,
                    swap_bps_annual=swap_bps_annual,
                ))
                position = None

    df = pd.DataFrame(trades)
    if verbose:
        print(f"[{pair}] filters={sorted(active_filters)} raw={n_raw_signals} "
              f"pass_tdi={n_tdi_pass} trades_closed={len(df)} {time.time()-t0:.1f}s", flush=True)
    return df, n_raw_signals, n_tdi_pass


def summarize(all_trades: pd.DataFrame, n_pairs: int, n_years: float) -> dict:
    if all_trades.empty:
        return dict(n=0, trades_per_pair_year=0.0, win_rate=np.nan, hold_days=np.nan,
                    worst_trade_pct=np.nan)
    n = len(all_trades)
    win_rate = (all_trades["r_multiple"] > 0).mean() * 100.0
    hold_days = all_trades["hold_days"].mean()
    # worst_trade_pct: R-multiple at RISK_PCT=1% of balance -> pct P&L = r_multiple * 1%
    worst_trade_pct = all_trades["r_multiple"].min() * de.RISK_PCT
    trades_per_pair_year = n / (n_pairs * n_years)
    return dict(n=n, trades_per_pair_year=trades_per_pair_year, win_rate=win_rate,
                hold_days=hold_days, worst_trade_pct=worst_trade_pct)


TARGET = dict(trades_per_pair_year=3.5, win_rate=63.58, hold_days=11.0, worst_trade_pct=-1.27)


def distance(summary: dict) -> float:
    """Normalized L2 distance to the author's declared metadata. Each component scaled by a
    plausible spread so no single metric dominates purely from units."""
    if summary["n"] < 5:
        return np.inf
    d_tpy = (summary["trades_per_pair_year"] - TARGET["trades_per_pair_year"]) / 3.5
    d_wr = (summary["win_rate"] - TARGET["win_rate"]) / 15.0
    d_hold = (summary["hold_days"] - TARGET["hold_days"]) / 11.0
    d_worst = (summary["worst_trade_pct"] - TARGET["worst_trade_pct"]) / 1.27
    return float(np.sqrt(d_tpy**2 + d_wr**2 + d_hold**2 + d_worst**2))


def run_config(active_filters: set, pairs=None, tf_cache=None, verbose=True):
    pairs = pairs or de.PAIRS
    dfs = []
    raw_total = 0
    pass_total = 0
    for p in pairs:
        df, raw, passed = run_pair_filtered(p, active_filters, tf_cache=tf_cache, verbose=verbose)
        raw_total += raw
        pass_total += passed
        if not df.empty:
            dfs.append(df)
    all_trades = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    n_years = (pd.Timestamp("2026-06-05") - pd.Timestamp("2007-01-01")).days / 365.25
    summ = summarize(all_trades, len(pairs), n_years)
    summ["raw_signals"] = raw_total
    summ["pass_tdi"] = pass_total
    summ["reject_pct"] = 100.0 * (1 - pass_total / raw_total) if raw_total else np.nan
    summ["dist"] = distance(summ)
    return summ, all_trades


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "single"
    tf_cache = {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "single":
        rows = []
        # baseline config A for reference
        summ, _ = run_config(set(), tf_cache=tf_cache, verbose=True)
        summ["config"] = "A_no_filter"
        rows.append(summ)
        pd.DataFrame(rows).to_csv(OUT_DIR / "config_search_results.csv", index=False)
        for tf_idx in range(5):
            for kind in ["CROSS", "TREND", "ANGLE"]:
                name = f"TDI_TIMEFRAME{tf_idx}_{kind}"
                summ, _ = run_config({(tf_idx, kind)}, tf_cache=tf_cache, verbose=True)
                summ["config"] = name
                rows.append(summ)
                pd.DataFrame(rows).to_csv(OUT_DIR / "config_search_results.csv", index=False)
                print(f"== {name}: {summ}", flush=True)

    elif mode == "h4cross":
        summ, trades = run_config({(3, "CROSS")}, tf_cache=tf_cache, verbose=True)
        print("Config B (H4 CROSS only):", summ)
        trades.to_csv(OUT_DIR / "trades_configB_h4cross.csv", index=False)
        pd.Series(summ).to_csv(OUT_DIR / "configB_summary.csv")

    elif mode == "angle_only":
        # measure the raw rejection fraction of the angle band alone, per timeframe, without
        # running the full trade engine (pure indicator-level measurement)
        rows = []
        for pair in de.PAIRS:
            m1_close = load_m1_close(pair)
            h1 = de.load_h1(pair)
            conds = tdi.build_all_tf_conditions(m1_close, h1.index)
            for tf_idx in range(5):
                c = conds[tf_idx]
                valid = c["angle"].notna()
                n_valid = valid.sum()
                frac_buy_ok = c.loc[valid, "angle_buy_ok"].mean()
                frac_sell_ok = c.loc[valid, "angle_sell_ok"].mean()
                frac_either_ok = (c.loc[valid, "angle_buy_ok"] | c.loc[valid, "angle_sell_ok"]).mean()
                rows.append(dict(pair=pair, tf_idx=tf_idx, n_valid=int(n_valid),
                                  frac_buy_ok=frac_buy_ok, frac_sell_ok=frac_sell_ok,
                                  frac_either_ok=frac_either_ok))
                print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(OUT_DIR / "angle_only_rejection.csv", index=False)

    else:
        raise ValueError(mode)
