"""
iter_05.py — Surgical MaxDD Reduction on iter_2a
==================================================
Goal: reduce MaxDD from -31.1% without destroying Sharpe 0.808 / WF 100%.
DO NOT touch the opening momentum signal or VWAP filter — they work.

Approach:
  STEP 1 — Forensic analysis: worst 20 trading days, pattern identification.
  STEP 2 — Four targeted fixes tested independently:
    Fix A: Dollar stop per trade (daily loss limit) — $200 / $300 / $400 variants
    Fix B: Gap filter — skip day if |overnight gap| > threshold (0.5% / 0.8% / 1.2%)
    Fix C: Pre-market vol filter — skip if 08:00-09:29 ETH range > 2× 20d avg
    Fix D: Trailing stop — tighten to entry+0.25R once trade is up 0.75R
  STEP 3 — Best two fixes combined.

n_tests: 99 → ~105 (6 new variants + 3 sensitivity sub-variants for Fix A/B)
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results, print_comparison_table
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_BASE = 99

T_0800 = datetime.time(8, 0)
T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1230 = datetime.time(12, 30)
T_1559 = datetime.time(15, 59)

BASE_TP_MULT = 1.5
BASE_SL_MULT = 0.5

# iter_2a baseline reference
BASELINE = {"iteration": "iter_2a", "sharpe": 0.8078, "max_dd": -0.3115,
            "pf": 1.174, "wf_pct": 100.0, "n_trades": 622, "p_ev_zero": 0.069}


# ────────────────────────────────────────────────────────────────────────────
# Feature builders
# ────────────────────────────────────────────────────────────────────────────

def build_opening_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full opening features including gap and pre-market ETH range.
    Returns one row per trading day with a valid opening signal.
    """
    records = []
    dates = sorted(df.index.normalize().unique())

    # Daily RTH close for gap computation
    rth_all = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)]
    daily_rth_open  = rth_all["open"].resample("B").first().dropna()
    daily_rth_close = rth_all["close"].resample("B").last().dropna()

    # Pre-RTH (ETH) range: 08:00–09:29 each day as macro vol proxy
    pre_rth = df[(df.index.time >= T_0800) & (df.index.time < T_0930)]
    eth_range_daily = (
        pre_rth["high"].resample("B").max() -
        pre_rth["low"].resample("B").min()
    ).dropna()
    eth_range_avg20 = eth_range_daily.rolling(20, min_periods=5).mean().shift(1)

    for i, date in enumerate(dates):
        day = df[df.index.normalize() == date]
        opening = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
        if len(opening) < 2:
            continue

        open_p  = float(opening.iloc[0]["open"])
        close_p = float(opening.iloc[-1]["close"])
        rng     = abs(close_p - open_p)
        if rng < 1.0:
            continue

        direction   = 1 if close_p > open_p else -1
        sig_ts      = opening.index[-1]
        vwap_at_sig = float(opening.iloc[-1]["vwap_rth"])

        # VWAP filter (iter_2a filter A)
        vwap_ok = (direction == 1 and close_p > vwap_at_sig) or \
                  (direction == -1 and close_p < vwap_at_sig)

        # Overnight gap
        prev_date   = dates[i - 1] if i > 0 else None
        prev_close  = float(daily_rth_close.get(prev_date, np.nan)) if prev_date else np.nan
        today_open  = float(daily_rth_open.get(date, np.nan))
        gap_pct     = (today_open - prev_close) / prev_close \
                      if np.isfinite(prev_close) and prev_close > 0 else np.nan

        # Pre-RTH ETH range
        eth_rng     = float(eth_range_daily.get(date, np.nan))
        eth_avg     = float(eth_range_avg20.get(date, np.nan))
        eth_hi_vol  = (eth_rng > 2.0 * eth_avg) \
                      if (np.isfinite(eth_rng) and np.isfinite(eth_avg) and eth_avg > 0) \
                      else False

        exit_time = pd.Timestamp(
            date.year, date.month, date.day, 12, 30, 0, tzinfo=sig_ts.tzinfo
        )

        records.append({
            "date":       date,
            "dow":        date.day_name(),
            "sig_ts":     sig_ts,
            "direction":  direction,
            "open_price": open_p,
            "close_price":close_p,
            "rng":        rng,
            "vwap_at_sig":vwap_at_sig,
            "vwap_ok":    vwap_ok,
            "gap_pct":    gap_pct,
            "eth_range":  eth_rng,
            "eth_avg20":  eth_avg,
            "eth_hi_vol": eth_hi_vol,
            "exit_time":  exit_time,
        })

    df_feats = pd.DataFrame(records)
    return df_feats


def signals_from_features(feats: pd.DataFrame,
                           gap_thresh: Optional[float] = None,
                           skip_hi_vol: bool = False,
                           dollar_stop: Optional[float] = None) -> pd.DataFrame:
    """
    iter_2a base signals (vwap_ok) with optional Fix B / Fix C filters.
    Fix A (dollar stop) is stored as a column for use in custom run.
    """
    f = feats[feats["vwap_ok"]].copy()

    if gap_thresh is not None:
        f = f[f["gap_pct"].abs() <= gap_thresh]

    if skip_hi_vol:
        f = f[~f["eth_hi_vol"]]

    rows = []
    for _, row in f.iterrows():
        rng = float(row["rng"])
        sl_pts = rng * BASE_SL_MULT
        if dollar_stop is not None:
            cap_pts = (dollar_stop + COST_RT) / POINT_VALUE
            sl_pts  = min(sl_pts, cap_pts)

        rows.append({
            "signal_ts":  row["sig_ts"],
            "direction":  int(row["direction"]),
            "tp_points":  rng * BASE_TP_MULT,
            "sl_points":  sl_pts,
            "exit_time":  row["exit_time"],
            "rng":        rng,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ────────────────────────────────────────────────────────────────────────────
# Custom run with trailing stop (Fix D)
# ────────────────────────────────────────────────────────────────────────────

def run_with_trailing_stop(engine: NQBacktestEngine,
                           signals: pd.DataFrame,
                           trail_trigger_r: float = 0.75,
                           trail_lock_r:    float = 0.25) -> Tuple[pd.DataFrame, dict]:
    """
    iter_2a signals with trailing stop:
    Once trade is up > trail_trigger_r × R, tighten SL to entry + trail_lock_r × R.
    """
    trades: List[dict] = []

    for sig_ts, sig in signals.iterrows():
        direction   = int(sig["direction"])
        tp_pts      = float(sig["tp_points"])
        sl_pts      = float(sig["sl_points"])
        exit_ts     = sig["exit_time"]
        rng         = float(sig.get("rng", sl_pts / BASE_SL_MULT))

        trail_trigger = rng * trail_trigger_r   # distance in points, in profit direction
        trail_lock    = rng * trail_lock_r       # minimum profit to protect

        future = engine.rth[engine.rth.index > sig_ts]
        if future.empty:
            continue
        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        if direction == 1:
            tp_price = entry_price + tp_pts
            sl_price = entry_price - sl_pts
        else:
            tp_price = entry_price - tp_pts
            sl_price = entry_price + sl_pts

        window = engine.rth[
            (engine.rth.index >= entry_bar) &
            (engine.rth.index <= exit_ts)
        ]

        exit_price  = None
        exit_reason = "time"
        bars_held   = 0
        trailing_active = False

        for bar_ts, bar in window.iterrows():
            bars_held += 1
            bar_h = float(bar["high"])
            bar_l = float(bar["low"])

            # Activate trailing stop if profit threshold reached
            if not trailing_active:
                unrealised = (bar_h - entry_price) if direction == 1 \
                             else (entry_price - bar_l)
                if unrealised >= trail_trigger:
                    trailing_active = True
                    if direction == 1:
                        sl_price = max(sl_price, entry_price + trail_lock)
                    else:
                        sl_price = min(sl_price, entry_price - trail_lock)

            if direction == 1:
                if bar_l <= sl_price:
                    exit_price  = sl_price
                    exit_reason = "trail_sl" if trailing_active else "sl"
                    break
                if bar_h >= tp_price:
                    exit_price  = tp_price
                    exit_reason = "tp"
                    break
            else:
                if bar_h >= sl_price:
                    exit_price  = sl_price
                    exit_reason = "trail_sl" if trailing_active else "sl"
                    break
                if bar_l <= tp_price:
                    exit_price  = tp_price
                    exit_reason = "tp"
                    break

        if exit_price is None:
            if window.empty:
                continue
            exit_price  = float(window.iloc[-1]["close"])
            exit_reason = "time"

        pnl_pts = direction * (exit_price - entry_price)
        pnl_usd = pnl_pts * POINT_VALUE - COST_RT

        trades.append({
            "signal_ts":   sig_ts,
            "entry_ts":    entry_bar,
            "exit_ts":     bar_ts if exit_reason != "time" else window.index[-1],
            "direction":   direction,
            "entry_price": entry_price,
            "exit_price":  exit_price,
            "exit_reason": exit_reason,
            "pnl_pts":     round(pnl_pts, 4),
            "pnl_usd":     round(pnl_usd, 2),
            "bars_held":   bars_held,
            "tp_pts":      tp_pts,
            "sl_pts":      sl_pts,
        })

    tl = pd.DataFrame(trades)
    met = engine.metrics(tl) if len(tl) > 0 else {}
    return tl, met


# ────────────────────────────────────────────────────────────────────────────
# Sharpe HAC (daily P&L series)
# ────────────────────────────────────────────────────────────────────────────

def sharpe_hac(daily_pnl: pd.Series) -> float:
    return NQBacktestEngine._sharpe_hac_daily(daily_pnl)


# ────────────────────────────────────────────────────────────────────────────
# STEP 1 — Forensic analysis
# ────────────────────────────────────────────────────────────────────────────

def forensic_analysis(engine: NQBacktestEngine,
                      feats: pd.DataFrame) -> pd.DataFrame:
    """
    Run iter_2a (VWAP-only), get full trade log, build worst-20-days table.
    """
    log.info("Running iter_2a for forensic trade log...")
    sigs = signals_from_features(feats)
    trade_log, met = engine.run(sigs)

    if trade_log.empty:
        print("No trades generated.")
        return pd.DataFrame()

    trade_log["date"] = pd.to_datetime(trade_log["entry_ts"]).dt.normalize()

    # Build per-day P&L
    daily = trade_log.groupby("date").agg(
        daily_pnl=("pnl_usd", "sum"),
        n_trades=("pnl_usd", "count"),
        exit_reasons=("exit_reason", lambda x: ",".join(x.unique())),
    ).reset_index()

    # Join opening features metadata
    feats_vwap = feats[feats["vwap_ok"]].copy()
    feats_vwap["date"] = pd.to_datetime(feats_vwap["date"]).dt.normalize()
    daily = daily.merge(
        feats_vwap[["date","dow","gap_pct","eth_range","eth_avg20","eth_hi_vol","rng"]],
        on="date", how="left"
    )
    daily = daily.sort_values("daily_pnl")

    worst20 = daily.head(20)

    print("\n" + "=" * 100)
    print("FORENSIC ANALYSIS — WORST 20 TRADING DAYS (iter_2a baseline)")
    print("=" * 100)
    print(f"{'Date':<12} {'DOW':<10} {'P&L':>8} {'N':>3} {'Exit':>12} "
          f"{'Gap%':>7} {'ETH_rng':>8} {'ETH_avg':>8} {'HiVol':>6} {'OR_pts':>7}")
    print("-" * 100)
    for _, row in worst20.iterrows():
        gap_str  = f"{row['gap_pct']*100:+.2f}%" if pd.notna(row['gap_pct']) else "  N/A"
        eth_str  = f"{row['eth_range']:.1f}" if pd.notna(row['eth_range']) else "  N/A"
        avg_str  = f"{row['eth_avg20']:.1f}" if pd.notna(row['eth_avg20']) else "  N/A"
        hv_str   = "YES" if row.get('eth_hi_vol') else "no"
        rng_str  = f"{row['rng']:.1f}" if pd.notna(row['rng']) else "N/A"
        print(f"{str(row['date'].date()):<12} {str(row['dow']):<10} "
              f"{row['daily_pnl']:>8.1f} {int(row['n_trades']):>3} "
              f"{str(row['exit_reasons']):>12} "
              f"{gap_str:>7} {eth_str:>8} {avg_str:>8} {hv_str:>6} {rng_str:>7}")

    # Pattern analysis
    print("\n--- PATTERN ANALYSIS (worst 20 days) ---")

    # Day of week
    dow_counts = worst20["dow"].value_counts()
    print(f"\nDay of week distribution:")
    for dow, cnt in dow_counts.items():
        print(f"  {dow:<10} : {cnt:>2} of 20 ({cnt/20*100:.0f}%)")

    # Gap size
    large_gap = worst20[worst20["gap_pct"].abs() > 0.008].shape[0]
    med_gap   = worst20[worst20["gap_pct"].abs() > 0.005].shape[0]
    print(f"\nGap >0.8% abs: {large_gap}/20  |  Gap >0.5% abs: {med_gap}/20")

    # Pre-market hi vol
    hv_count = worst20["eth_hi_vol"].sum() if "eth_hi_vol" in worst20.columns else 0
    print(f"Pre-mkt HiVol (ETH range > 2× avg): {hv_count}/20")

    # Exit reasons
    sl_days = worst20["exit_reasons"].str.contains("sl").sum()
    tp_days = worst20["exit_reasons"].str.contains("tp").sum()
    time_days = worst20["exit_reasons"].str.contains("time").sum()
    print(f"Exit reasons: SL={sl_days}, TP={tp_days}, TIME={time_days}")

    # Opening range size
    med_rng  = worst20["rng"].median()
    all_med  = feats_vwap["rng"].median()
    print(f"Median opening range worst 20: {med_rng:.1f} pts  |  All days: {all_med:.1f} pts")

    # Quarter concentration
    worst20_copy = worst20.copy()
    worst20_copy["quarter"] = pd.to_datetime(worst20_copy["date"]).dt.to_period("Q")
    q_counts = worst20_copy["quarter"].value_counts().head(5)
    print(f"\nQuarter concentration (top 5):")
    for q, c in q_counts.items():
        print(f"  {q}: {c}/20")

    # P&L distribution of all trades
    print(f"\nBaseline P&L stats:")
    print(f"  Total trades     : {len(trade_log)}")
    print(f"  Positive days    : {(daily['daily_pnl'] > 0).sum()} / {len(daily)}")
    print(f"  Worst day        : ${daily['daily_pnl'].min():.1f}")
    print(f"  Best day         : ${daily['daily_pnl'].max():.1f}")
    print(f"  Mean daily P&L   : ${daily['daily_pnl'].mean():.1f}")
    print(f"  Avg losing trade : ${trade_log[trade_log['pnl_usd']<0]['pnl_usd'].mean():.1f}")
    print(f"  Avg winning trade: ${trade_log[trade_log['pnl_usd']>0]['pnl_usd'].mean():.1f}")
    print(f"  1.5× avg loss    : ${trade_log[trade_log['pnl_usd']<0]['pnl_usd'].mean() * 1.5:.1f}")
    print("=" * 100)

    return daily, trade_log


# ────────────────────────────────────────────────────────────────────────────
# Evaluation helper
# ────────────────────────────────────────────────────────────────────────────

def evaluate(engine: NQBacktestEngine,
             sigs: pd.DataFrame,
             label: str,
             n_test: int,
             use_trail: bool = False) -> dict:
    """Run backtest, compute all metrics, return result dict."""
    if sigs.empty or len(sigs) < 10:
        return {"iteration": label, "n_trades": 0, "verdict": "SKIP"}

    if use_trail:
        tl, met = run_with_trailing_stop(engine, sigs)
    else:
        tl, met = engine.run(sigs)

    boot = engine.bootstrap_ev(tl)
    wf   = engine.walk_forward(
        lambda df_w, p: signals_from_features(build_opening_features(df_w),
                                               gap_thresh=sigs.attrs.get("gap_thresh"),
                                               skip_hi_vol=sigs.attrs.get("skip_hi_vol", False),
                                               dollar_stop=sigs.attrs.get("dollar_stop")),
        {},
        train_months=12, test_months=6,
    )

    sh  = met.get("sharpe_daily_hac") or 0
    pf  = met.get("profit_factor")    or 0
    mdd = met.get("max_dd_pct")       or 0
    n   = met.get("n_trades", 0)

    if   sh >= 1.0 and mdd >= -0.10 and pf >= 1.20:
        verdict = "PROPFIRM_PASS"
    elif sh >= 0.7 and mdd >= -0.15 and pf >= 1.15:
        verdict = "RESEARCH_PASS"
    elif sh >= 0.5 and pf >= 1.10:
        verdict = "IMPROVE"
    elif sh >= 0.0:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    result = {
        "iteration":       label,
        "n_tests":         n_test,
        **met,
        **boot,
        "wf_pct_positive": wf.get("wf_pct_positive"),
        "wf_n_windows":    wf.get("n_windows"),
        "verdict":         verdict,
    }
    append_result(result)
    return result


def print_row(r: dict, ref: dict) -> None:
    sh  = r.get("sharpe_daily_hac") or 0
    mdd = r.get("max_dd_pct") or 0
    pf  = r.get("profit_factor") or 0
    wf  = r.get("wf_pct_positive") or 0
    n   = r.get("n_trades", 0)
    p   = r.get("p_ev_zero") or 1.0
    vd  = r.get("verdict","?")

    dsh  = sh  - (ref.get("sharpe") or 0)
    dmdd = mdd - (ref.get("max_dd") or 0)
    dn   = n   - (ref.get("n_trades") or 0)

    print(f"  {r.get('iteration','?'):<22} Sh={sh:+.3f}({dsh:+.3f})  "
          f"MaxDD={mdd*100:+.1f}%({dmdd*100:+.1f}pp)  "
          f"PF={pf:.3f}  WF={wf:.0f}%  N={n}({dn:+d})  "
          f"P(EV≤0)={p:.3f}  → {vd}")


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Iter 05 — Surgical MaxDD Reduction ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features...")
    feats = build_opening_features(engine.rth)
    log.info(f"Total day features: {len(feats)}  |  VWAP-filtered (iter_2a base): "
             f"{feats['vwap_ok'].sum()}")

    # ──────────────────────────────────────────────────────────────────
    # STEP 1 — Forensic analysis
    # ──────────────────────────────────────────────────────────────────
    daily_pnl_df, trade_log_2a = forensic_analysis(engine, feats)

    avg_loss = float(trade_log_2a[trade_log_2a["pnl_usd"] < 0]["pnl_usd"].mean())
    suggested_stop = abs(avg_loss) * 1.5
    log.info(f"Suggested dollar stop (1.5× avg loss): ${suggested_stop:.0f}")

    n_test   = N_TESTS_BASE
    results  = []
    ref      = BASELINE

    # ──────────────────────────────────────────────────────────────────
    # STEP 2 — Individual fixes
    # ──────────────────────────────────────────────────────────────────

    # --- Fix A: Dollar stop (three thresholds) ---
    print("\n" + "=" * 80)
    print("FIX A — Dollar stop per trade")
    print("=" * 80)
    fix_a_best_sh = -np.inf
    fix_a_best    = None
    for thresh in [200, 300, 400]:
        n_test += 1
        lbl  = f"iter_05_A${thresh}"
        sigs = signals_from_features(feats, dollar_stop=float(thresh))
        sigs.attrs["dollar_stop"] = float(thresh)
        r    = evaluate(engine, sigs, lbl, n_test)
        results.append(r)
        print_row(r, ref)
        if (r.get("sharpe_daily_hac") or 0) > fix_a_best_sh:
            fix_a_best_sh = r.get("sharpe_daily_hac") or 0
            fix_a_best    = (thresh, r)

    best_A_thresh = fix_a_best[0]
    best_A_result = fix_a_best[1]
    print(f"  → Fix A best threshold: ${best_A_thresh}")

    # --- Fix B: Gap filter (three thresholds) ---
    print("\n" + "=" * 80)
    print("FIX B — Gap filter (skip large overnight gaps)")
    print("=" * 80)
    fix_b_best_mdd = 0
    fix_b_best     = None
    for thresh in [0.005, 0.008, 0.012]:
        n_test += 1
        lbl  = f"iter_05_B{thresh:.3f}"
        sigs = signals_from_features(feats, gap_thresh=thresh)
        sigs.attrs["gap_thresh"] = thresh
        r    = evaluate(engine, sigs, lbl, n_test)
        results.append(r)
        print_row(r, ref)
        mdd = r.get("max_dd_pct") or 0
        if mdd > fix_b_best_mdd:
            fix_b_best_mdd = mdd
            fix_b_best     = (thresh, r)

    best_B_thresh = fix_b_best[0] if fix_b_best else 0.008
    best_B_result = fix_b_best[1] if fix_b_best else {}
    print(f"  → Fix B best threshold: {best_B_thresh:.1%}")

    # --- Fix C: Pre-market vol filter ---
    print("\n" + "=" * 80)
    print("FIX C — Pre-market high-vol filter (ETH range > 2× 20d avg)")
    print("=" * 80)
    n_test += 1
    sigs_C = signals_from_features(feats, skip_hi_vol=True)
    sigs_C.attrs["skip_hi_vol"] = True
    r_C = evaluate(engine, sigs_C, "iter_05_C_pmvol", n_test)
    results.append(r_C)
    print_row(r_C, ref)
    n_filtered_C = feats["vwap_ok"].sum() - len(sigs_C)
    print(f"  Filtered by pre-mkt hi-vol: {n_filtered_C} days removed")

    # --- Fix D: Trailing stop ---
    print("\n" + "=" * 80)
    print("FIX D — Trailing stop (lock 0.25R once up 0.75R)")
    print("=" * 80)
    n_test += 1
    sigs_D = signals_from_features(feats)
    r_D = evaluate(engine, sigs_D, "iter_05_D_trail", n_test, use_trail=True)
    results.append(r_D)
    print_row(r_D, ref)

    # ──────────────────────────────────────────────────────────────────
    # STEP 3 — Pick best two fixes and combine
    # ──────────────────────────────────────────────────────────────────

    # Rank individual fixes by (MaxDD improvement, Sharpe preservation)
    single_fixes = [
        ("A", best_A_result, {"dollar_stop": float(best_A_thresh)}),
        ("B", best_B_result, {"gap_thresh":  float(best_B_thresh)}),
        ("C", r_C,           {"skip_hi_vol": True}),
        ("D", r_D,           {"use_trail":   True}),
    ]
    # Sort by MaxDD improvement (higher = less negative = better)
    single_fixes.sort(key=lambda x: (x[1].get("max_dd_pct") or -99), reverse=True)

    print("\n" + "=" * 80)
    print("FIX RANKING by MaxDD improvement:")
    for rank, (name, r, _) in enumerate(single_fixes, 1):
        mdd_imp = ((r.get("max_dd_pct") or 0) - BASELINE["max_dd"]) * 100
        sh_imp  = (r.get("sharpe_daily_hac") or 0) - BASELINE["sharpe"]
        n_ret   = (r.get("n_trades") or 0) / BASELINE["n_trades"] * 100
        print(f"  #{rank} Fix {name}: MaxDD Δ={mdd_imp:+.1f}pp  Sharpe Δ={sh_imp:+.3f}  "
              f"Trades retained={n_ret:.0f}%")

    # Best two: filter by >60% trade retention
    eligible = [(nm, r, kw) for nm, r, kw in single_fixes
                if (r.get("n_trades") or 0) / BASELINE["n_trades"] >= 0.60]

    if len(eligible) >= 2:
        fx1_name, fx1_r, fx1_kw = eligible[0]
        fx2_name, fx2_r, fx2_kw = eligible[1]

        print(f"\n  Combining Fix {fx1_name} + Fix {fx2_name}:")
        n_test += 1

        # Build combined signals
        gap_t    = fx1_kw.get("gap_thresh") or fx2_kw.get("gap_thresh")
        hi_vol   = fx1_kw.get("skip_hi_vol") or fx2_kw.get("skip_hi_vol", False)
        dstop    = fx1_kw.get("dollar_stop") or fx2_kw.get("dollar_stop")
        use_tr   = fx1_kw.get("use_trail")   or fx2_kw.get("use_trail", False)

        sigs_combo = signals_from_features(
            feats,
            gap_thresh   = gap_t,
            skip_hi_vol  = bool(hi_vol),
            dollar_stop  = dstop,
        )
        sigs_combo.attrs.update({
            "gap_thresh":   gap_t,
            "skip_hi_vol":  bool(hi_vol),
            "dollar_stop":  dstop,
        })

        combo_lbl = f"iter_05_{fx1_name}+{fx2_name}"
        r_combo = evaluate(engine, sigs_combo, combo_lbl, n_test, use_trail=bool(use_tr))
        results.append(r_combo)

        print("\n" + "=" * 80)
        print("STEP 3 — Best combination vs iter_2a baseline:")
        print("=" * 80)
        print_row(r_combo, ref)

        # Try triple combo if MaxDD still > -20%
        if (r_combo.get("max_dd_pct") or 0) < -0.20 and len(eligible) >= 3:
            fx3_name, fx3_r, fx3_kw = eligible[2]
            print(f"\n  MaxDD still > -20%. Adding Fix {fx3_name}...")
            n_test += 1

            gap_t2   = gap_t   or fx3_kw.get("gap_thresh")
            hi_vol2  = hi_vol  or fx3_kw.get("skip_hi_vol", False)
            dstop2   = dstop   or fx3_kw.get("dollar_stop")
            use_tr2  = use_tr  or fx3_kw.get("use_trail", False)

            sigs_triple = signals_from_features(
                feats,
                gap_thresh  = gap_t2,
                skip_hi_vol = bool(hi_vol2),
                dollar_stop = dstop2,
            )
            triple_lbl = f"iter_05_{fx1_name}+{fx2_name}+{fx3_name}"
            r_triple   = evaluate(engine, sigs_triple, triple_lbl, n_test, use_trail=bool(use_tr2))
            results.append(r_triple)
            print_row(r_triple, ref)
            r_combo = r_triple   # use triple as best
    else:
        print("\n  WARNING: fewer than 2 eligible fixes (>60% trade retention). "
              "Using best single fix as combo.")
        r_combo = eligible[0][1] if eligible else results[0]

    # ──────────────────────────────────────────────────────────────────
    # Final summary table
    # ──────────────────────────────────────────────────────────────────
    all_results = load_results()
    print_comparison_table(all_results)

    # ──────────────────────────────────────────────────────────────────
    # Final deliverable
    # ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL DELIVERABLE")
    print("=" * 80)

    # Pattern summary
    if daily_pnl_df is not None and not daily_pnl_df.empty:
        worst20 = daily_pnl_df.head(20)
        patterns = []
        lg = worst20[worst20["gap_pct"].abs() > 0.008].shape[0]
        if lg >= 6:
            patterns.append(f"{lg}/20 worst days had |gap| > 0.8% (large overnight gap)")
        hv = int(worst20["eth_hi_vol"].sum()) if "eth_hi_vol" in worst20.columns else 0
        if hv >= 5:
            patterns.append(f"{hv}/20 worst days had elevated pre-market volatility")
        dow_top = worst20["dow"].value_counts().idxmax()
        dow_n   = worst20["dow"].value_counts().max()
        if dow_n >= 5:
            patterns.append(f"{dow_n}/20 worst days fell on {dow_top}")
        if not patterns:
            patterns = ["No strong single pattern — losses distributed across conditions"]
        print(f"\nTop patterns in worst 20 days:")
        for p in patterns[:3]:
            print(f"  • {p}")

    # Best combo decision
    best_sh  = r_combo.get("sharpe_daily_hac") or 0
    best_mdd = r_combo.get("max_dd_pct") or 0
    best_pf  = r_combo.get("profit_factor") or 0
    best_n   = r_combo.get("n_trades") or 0
    best_p   = r_combo.get("p_ev_zero") or 1.0
    best_vd  = r_combo.get("verdict", "?")

    print(f"\nBest combination: {r_combo.get('iteration','?')}")
    print(f"  Sharpe={best_sh:.3f}  MaxDD={best_mdd*100:.1f}%  PF={best_pf:.3f}  "
          f"N={best_n}  P(EV≤0)={best_p:.3f}")

    if best_sh >= 1.0 and best_mdd >= -0.10 and best_pf >= 1.20 and best_n >= 0.60 * 622:
        print("\n  DECISION: PROPFIRM PASS → Ready for paper trading. Commit and deploy.")
    elif best_sh >= 0.7 and best_mdd >= -0.15:
        print("\n  DECISION: RESEARCH PASS. Paper trade at 0.5 contract sizing.")
        print("  One more iteration targeting MaxDD.")
    else:
        print(f"\n  DECISION: MaxDD={best_mdd*100:.1f}% still too high.")
        print("  Design iter_06 specifically around dominant loss pattern.")

    print(f"\nn_tests: {N_TESTS_BASE} → {n_test}")
    print("DO NOT COMMIT — review forensic summary + best combo metrics first.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_05 failed")
        sys.exit(1)
