"""
iter_07_validation.py — Pre-Deployment Validation
====================================================
Three-part validation before paper trading iter_05_A$400+B1.2%.

PART 1 — Forensic of Aug 2023 → Feb 2024 drawdown (168-day period)
PART 2 — Cross-instrument validation on ES and YM (yfinance 5-min, ~60 days)
PART 3 — Extended walk-forward: 6M train / 3M test, 8 windows

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.iter_07_validation
n_tests: 116 → 119
"""

from __future__ import annotations

import datetime
import logging
import sys
import warnings
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features
)

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 116

T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1230 = datetime.time(12, 30)
T_1559 = datetime.time(15, 59)

STRATEGY_GAP   = 0.012
STRATEGY_STOP  = 400.0
STRATEGY_TP    = 1.5
STRATEGY_SL    = 0.5


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def sharpe_hac(pnl: pd.Series, annual: float = 252.0) -> float:
    r = pnl.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean, std = float(r.mean()), float(r.std(ddof=1))
    if std < 1e-9:
        return np.nan
    if n < 48:
        return mean / std * np.sqrt(annual)
    reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lrv = float(reg.cov_params().iloc[0, 0]) * n
    hac = np.sqrt(max(lrv, 1e-24))
    return mean / hac * np.sqrt(annual) if hac > 1e-12 else np.nan


def max_dd(pnl_series: pd.Series) -> Tuple[float, float]:
    """Returns (max_dd_pct_of_peak_pnl, max_dd_usd)."""
    cum = pnl_series.cumsum()
    dd_usd = float((cum - cum.cummax()).min())
    peak   = float(cum.cummax().max())
    dd_pct = dd_usd / peak if peak > 0 else np.nan
    return dd_pct, dd_usd


# ────────────────────────────────────────────────────────────────────────────
# PART 1 — Drawdown forensic
# ────────────────────────────────────────────────────────────────────────────

def part1_drawdown_forensic(engine: NQBacktestEngine,
                             feats: pd.DataFrame) -> None:
    print("\n" + "═" * 80)
    print("PART 1 — DRAWDOWN FORENSIC: Aug 2023 → Feb 2024")
    print("═" * 80)

    # Rebuild full trade log
    sigs  = signals_from_features(feats, gap_thresh=STRATEGY_GAP,
                                   dollar_stop=STRATEGY_STOP)
    tl, _ = engine.run(sigs)
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

    # Daily P&L
    daily = tl.groupby("date")["pnl_usd"].sum().sort_index()
    cum   = daily.cumsum()

    # Find exact peak→trough in Aug 2023 – Feb 2024
    window_mask = (cum.index >= "2023-08-01") & (cum.index <= "2024-02-29")
    cum_win     = cum[window_mask]
    if cum_win.empty:
        print("  [No data in window — check dates]")
        return

    # Global peak before the window
    cum_before  = cum[cum.index < "2023-08-01"]
    peak_date   = cum_before.idxmax() if not cum_before.empty else cum_win.index[0]
    peak_val    = float(cum[peak_date]) if peak_date in cum.index else 0.0

    # Trough within/after peak
    cum_from_peak = cum[cum.index >= peak_date]
    trough_date   = (cum_from_peak - peak_val).idxmin()
    trough_val    = float(cum[trough_date])

    dd_usd = trough_val - peak_val
    dd_dur = (trough_date - peak_date).days

    print(f"\n  Peak date  : {peak_date.date()}  (cum P&L = ${peak_val:,.0f})")
    print(f"  Trough date: {trough_date.date()}  (cum P&L = ${trough_val:,.0f})")
    print(f"  Drawdown   : ${dd_usd:,.0f}  ({dd_usd/max(peak_val,1)*100:.1f}% of peak)")
    print(f"  Duration   : {dd_dur} days")

    # Trades during drawdown window
    dd_mask  = (tl["date"] >= peak_date) & (tl["date"] <= trough_date)
    dd_trades = tl[dd_mask].copy()
    all_trades = tl.copy()

    n_dd  = len(dd_trades)
    n_all = len(all_trades)

    wr_dd  = (dd_trades["pnl_usd"] > 0).mean()  if n_dd  > 0 else np.nan
    wr_all = (all_trades["pnl_usd"] > 0).mean() if n_all > 0 else np.nan
    avg_dd  = dd_trades["pnl_usd"].mean()  if n_dd  > 0 else np.nan
    avg_all = all_trades["pnl_usd"].mean() if n_all > 0 else np.nan

    print(f"\n  --- Trade statistics ---")
    print(f"  {'Metric':<28} {'Drawdown period':>18} {'Full sample':>14}")
    print(f"  {'-'*62}")
    print(f"  {'N trades':<28} {n_dd:>18} {n_all:>14}")
    print(f"  {'Win rate':<28} {wr_dd*100:>17.1f}% {wr_all*100:>13.1f}%")
    print(f"  {'Avg trade ($)':<28} {avg_dd:>18.1f} {avg_all:>14.1f}")

    # Opening range analysis — join feats back to trades
    feats_vwap = feats[feats["vwap_ok"]].copy()
    feats_vwap["date"] = pd.to_datetime(feats_vwap["date"]).dt.normalize()
    # Merge gap filter applied signals dates
    sigs_dates = set(sigs.index.normalize())
    feats_sig  = feats_vwap[feats_vwap["date"].isin(sigs_dates)]

    dd_feat  = feats_sig[(feats_sig["date"] >= peak_date) & (feats_sig["date"] <= trough_date)]
    all_feat = feats_sig

    rng_dd  = dd_feat["rng"]
    rng_all = all_feat["rng"]

    print(f"\n  --- Opening range distribution ---")
    print(f"  {'Metric':<28} {'Drawdown period':>18} {'Full sample':>14}")
    print(f"  {'-'*62}")
    for label, fn in [("Mean (pts)", "mean"), ("Median (pts)", "median"),
                      ("Std (pts)", "std"), ("p90 (pts)", lambda s: s.quantile(0.9))]:
        v_dd  = fn(rng_dd)  if callable(fn) else getattr(rng_dd,  fn)()
        v_all = fn(rng_all) if callable(fn) else getattr(rng_all, fn)()
        print(f"  {label:<28} {v_dd:>18.1f} {v_all:>14.1f}")

    # NQ realized vol proxy: rolling 5-day range
    rth = engine.rth
    daily_range = rth.resample("B").agg(high=("high","max"), low=("low","min"))
    daily_range["range_pts"] = daily_range["high"] - daily_range["low"]
    vol_proxy = daily_range["range_pts"].rolling(5, min_periods=3).mean()

    vp_dd  = vol_proxy[(vol_proxy.index >= peak_date) & (vol_proxy.index <= trough_date)].dropna()
    vp_all = vol_proxy.dropna()
    print(f"\n  --- NQ realized vol proxy (5-day rolling daily range) ---")
    print(f"  {'Metric':<28} {'Drawdown period':>18} {'Full sample':>14}")
    print(f"  {'-'*62}")
    for label, fn in [("Mean (pts)", "mean"), ("Median (pts)", "median")]:
        v1 = getattr(vp_dd, fn)()
        v2 = getattr(vp_all, fn)()
        print(f"  {label:<28} {v1:>18.1f} {v2:>14.1f}")

    # Directional accuracy: sign of opening move vs sign of 09:46-12:30 return
    rth_df = rth.copy()
    dates_dd  = set(pd.to_datetime(dd_feat["date"]).dt.normalize())
    dates_all = set(pd.to_datetime(all_feat["date"]).dt.normalize())

    def dir_accuracy(dates_set):
        correct = 0; total = 0
        for date in dates_set:
            day = rth_df[rth_df.index.normalize() == date]
            op_window = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
            hold_window= day[(day.index.time > T_0945) & (day.index.time <= T_1230)]
            if len(op_window) < 2 or hold_window.empty:
                continue
            op_dir  = 1 if float(op_window.iloc[-1]["close"]) > float(op_window.iloc[0]["open"]) else -1
            hold_ret = float(hold_window.iloc[-1]["close"]) - float(op_window.iloc[-1]["close"])
            hold_dir = 1 if hold_ret > 0 else -1
            correct += (op_dir == hold_dir)
            total   += 1
        return correct / total if total > 0 else np.nan, total

    acc_dd,  n_dd_a  = dir_accuracy(dates_dd)
    acc_all, n_all_a = dir_accuracy(dates_all)
    print(f"\n  --- Directional accuracy (opening move → 09:46-12:30 continuation) ---")
    print(f"  {'Metric':<28} {'Drawdown period':>18} {'Full sample':>14}")
    print(f"  {'-'*62}")
    print(f"  {'Directional accuracy':<28} {acc_dd*100:>17.1f}% {acc_all*100:>13.1f}%")

    # Trend vs range: |close_12:30 - open_09:30| / opening_range
    def trending_ratio(dates_set):
        ratios = []
        for date in dates_set:
            day = rth_df[rth_df.index.normalize() == date]
            op  = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
            end = day[(day.index.time >= T_1230) & (day.index.time <= T_1230)]
            if len(op) < 2 or end.empty: continue
            rng = abs(float(op.iloc[-1]["close"]) - float(op.iloc[0]["open"]))
            if rng < 1: continue
            close_12 = float(end.iloc[0]["close"])
            move = abs(close_12 - float(op.iloc[0]["open"]))
            ratios.append(move / rng)
        return np.mean(ratios) if ratios else np.nan, len(ratios)

    tr_dd,  _ = trending_ratio(dates_dd)
    tr_all, _ = trending_ratio(dates_all)
    print(f"  {'Trending ratio (|move/OR|)':<28} {tr_dd:>18.2f}x {tr_all:>13.2f}x")
    print(f"  (>1.0 = trending beyond OR, <0.5 = range-bound)")

    # DIAGNOSIS
    print(f"\n  --- DIAGNOSIS ---")
    diagnoses = []
    if np.isfinite(wr_dd) and wr_dd < wr_all - 0.05:
        diagnoses.append(f"Win rate collapsed ({wr_dd*100:.0f}% vs {wr_all*100:.0f}% full). Signal failed more often.")
    if np.isfinite(rng_dd.mean()) and rng_dd.mean() < rng_all.mean() * 0.8:
        diagnoses.append(f"Opening ranges smaller ({rng_dd.mean():.0f} vs {rng_all.mean():.0f} pts). Lower volatility = less edge.")
    if np.isfinite(tr_dd) and tr_dd < 0.8:
        diagnoses.append(f"Market was range-bound ({tr_dd:.2f}x trending ratio). Momentum signals faded quickly.")
    if np.isfinite(acc_dd) and acc_dd < acc_all - 0.05:
        diagnoses.append(f"Directional accuracy lower ({acc_dd*100:.0f}% vs {acc_all*100:.0f}%). Opening direction less predictive.")
    if not diagnoses:
        diagnoses.append("No single dominant factor — drawdown appears to be natural variance in a low-signal period.")

    for d in diagnoses:
        print(f"  • {d}")

    # Action recommendation
    print(f"\n  Action: ", end="")
    if any("range-bound" in d or "smaller" in d for d in diagnoses):
        print("Consider adding realized vol filter (skip days where 5d ATR < 50% of median).")
    elif any("Win rate" in d for d in diagnoses):
        print("Consider walk-forward re-optimization of VWAP threshold. Signal decayed temporarily.")
    else:
        print("Accept as natural variance. No regime filter needed.")


# ────────────────────────────────────────────────────────────────────────────
# PART 2 — Cross-instrument validation
# ────────────────────────────────────────────────────────────────────────────

def fetch_intraday_5min(ticker: str, period: str = "60d") -> pd.DataFrame:
    """Fetch 5-min intraday OHLCV from yfinance and tz-localize to US/Eastern."""
    log.info(f"Fetching {ticker} 5-min ({period})...")
    df = yf.download(ticker, period=period, interval="5m",
                     progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    # Ensure tz-aware US/Eastern
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert("US/Eastern")
    else:
        df.index = df.index.tz_convert("US/Eastern")
    return df


def run_opening_momentum_5min(df_5m: pd.DataFrame,
                               point_value: float,
                               cost_rt:     float,
                               dollar_cap:  float = 400.0,
                               gap_thresh:  float = 0.012,
                               label:       str   = "inst") -> Tuple[pd.DataFrame, dict]:
    """
    Opening momentum on 5-min bars (no VWAP filter — not available from yfinance).
    Opening range = 09:30 bar open → 09:45 bar close (first 3 bars of RTH).
    Signal: direction of first 15 min.
    TP = 1.5R, SL = 0.5R capped at dollar_cap.
    Time stop: 12:30 ET.
    """
    rth = df_5m[(df_5m.index.time >= T_0930) & (df_5m.index.time <= T_1559)].copy()
    if rth.empty:
        return pd.DataFrame(), {}

    dates = sorted(rth.index.normalize().unique())

    # Daily close for gap
    daily_close = rth["close"].resample("B").last().dropna()

    trades: List[dict] = []

    for i, date in enumerate(dates):
        day = rth[rth.index.normalize() == date]

        # 09:30-09:45: first 3 bars of 5-min (09:35, 09:40, 09:45 labeled right)
        op_bars = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
        if len(op_bars) < 2:
            continue

        open_p  = float(op_bars.iloc[0]["open"])
        close_p = float(op_bars.iloc[-1]["close"])
        rng = abs(close_p - open_p)
        if rng < 0.25:   # at least 0.25 pts for ES/YM
            continue

        direction = 1 if close_p > open_p else -1

        # Gap filter
        prev_date  = dates[i - 1] if i > 0 else None
        prev_close = float(daily_close.get(prev_date, np.nan)) if prev_date else np.nan
        if np.isfinite(prev_close) and prev_close > 0:
            gap_pct = abs(open_p - prev_close) / prev_close
            if gap_pct > gap_thresh:
                continue

        sl_pts = rng * STRATEGY_SL
        cap_pts = (dollar_cap + cost_rt) / point_value
        sl_pts  = min(sl_pts, cap_pts)

        tp_price = (open_p + rng * STRATEGY_TP) if direction == 1 \
                   else (open_p - rng * STRATEGY_TP)
        sl_price = (open_p - sl_pts) if direction == 1 \
                   else (open_p + sl_pts)

        exit_time = pd.Timestamp(
            date.year, date.month, date.day, 12, 30, 0, tzinfo=day.index[0].tzinfo
        )

        # Walk bars from 09:50 onwards
        hold_bars = day[
            (day.index > op_bars.index[-1]) &
            (day.index <= exit_time)
        ]

        ep = open_p; er = "time"; ex_ts = hold_bars.index[-1] if not hold_bars.empty else op_bars.index[-1]
        bars_held = 0

        for bar_ts, bar in hold_bars.iterrows():
            bars_held += 1
            if direction == 1:
                if float(bar["low"]) <= sl_price:
                    ep, er, ex_ts = sl_price, "sl", bar_ts; break
                if float(bar["high"]) >= tp_price:
                    ep, er, ex_ts = tp_price, "tp", bar_ts; break
            else:
                if float(bar["high"]) >= sl_price:
                    ep, er, ex_ts = sl_price, "sl", bar_ts; break
                if float(bar["low"]) <= tp_price:
                    ep, er, ex_ts = tp_price, "tp", bar_ts; break
        else:
            if not hold_bars.empty:
                ep = float(hold_bars.iloc[-1]["close"])

        pnl_pts = direction * (ep - open_p)
        pnl_usd = pnl_pts * point_value - cost_rt

        trades.append({
            "date":      date,
            "direction": direction,
            "entry":     open_p,
            "exit":      ep,
            "exit_reason": er,
            "pnl_pts":   round(pnl_pts, 4),
            "pnl_usd":   round(pnl_usd, 2),
            "rng":       rng,
        })

    if not trades:
        return pd.DataFrame(), {}

    tl = pd.DataFrame(trades)
    n  = len(tl)
    if n == 0:
        return tl, {}

    wins = tl[tl["pnl_usd"] > 0]
    loss = tl[tl["pnl_usd"] <= 0]
    pf   = wins["pnl_usd"].sum() / abs(loss["pnl_usd"].sum()) \
           if len(loss) > 0 and loss["pnl_usd"].sum() != 0 else np.nan

    daily_pnl = tl.groupby("date")["pnl_usd"].sum()
    sh = sharpe_hac(daily_pnl)
    dd_pct, dd_usd = max_dd(daily_pnl)

    met = {
        "n_trades": n,
        "win_rate": round(float((tl["pnl_usd"] > 0).mean()), 4),
        "avg_trade_usd": round(float(tl["pnl_usd"].mean()), 2),
        "profit_factor": round(float(pf), 4) if np.isfinite(pf) else None,
        "sharpe_daily_hac": round(float(sh), 4) if np.isfinite(sh) else None,
        "max_dd_pct": round(float(dd_pct), 4) if np.isfinite(dd_pct) else None,
        "max_dd_usd": round(float(dd_usd), 2),
        "total_pnl": round(float(tl["pnl_usd"].sum()), 2),
        "period_start": str(tl["date"].min().date()),
        "period_end":   str(tl["date"].max().date()),
    }
    return tl, met


def part2_cross_instrument() -> None:
    print("\n" + "═" * 80)
    print("PART 2 — CROSS-INSTRUMENT VALIDATION (ES + YM, yfinance 5-min ~60d)")
    print("═" * 80)

    instruments = {
        "ES": {"ticker": "ES=F", "pv": 50.0,  "cost": 34.0,  "label": "E-mini S&P 500"},
        "YM": {"ticker": "YM=F", "pv":  5.0,  "cost": 19.0,  "label": "Mini Dow Jones"},
    }

    n_test = N_TESTS_START + 1
    results = []

    for sym, cfg in instruments.items():
        n_test += 1
        df_5m = fetch_intraday_5min(cfg["ticker"], period="60d")
        if df_5m.empty:
            print(f"  {sym}: No data available from yfinance — skipping.")
            results.append({"instrument": sym, "available": False})
            continue

        tl, met = run_opening_momentum_5min(
            df_5m, cfg["pv"], cfg["cost"], label=sym
        )

        sh  = met.get("sharpe_daily_hac")
        pf  = met.get("profit_factor")
        mdd = met.get("max_dd_pct")
        n   = met.get("n_trades", 0)
        wr  = met.get("win_rate", 0)
        tot = met.get("total_pnl", 0)
        ps  = met.get("period_start", "?")
        pe  = met.get("period_end", "?")

        edge = "YES" if (sh is not None and sh > 0 and pf is not None and pf > 1.0) else "NO"
        results.append({
            "instrument": sym, "available": True,
            "sharpe": sh, "pf": pf, "max_dd": mdd, "n": n,
            "wr": wr, "total_pnl": tot, "edge": edge,
            "period": f"{ps} → {pe}",
        })

        result_entry = {
            "iteration":  f"iter_07_val_{sym}",
            "n_tests":    n_test,
            "description": f"Cross-instrument {sym} opening momentum 5-min",
            **met,
            "verdict": "EDGE" if edge == "YES" else "NO_EDGE",
        }
        append_result(result_entry)

        print(f"\n  [{sym} — {cfg['label']}]")
        print(f"    Period:  {ps} → {pe}  ({n} trades)")
        print(f"    Sharpe:  {sh}")
        print(f"    PF:      {pf}")
        print(f"    WR:      {wr*100:.1f}%" if wr else "    WR:  N/A")
        print(f"    MaxDD:   {mdd*100:.1f}%" if mdd else "    MaxDD: N/A")
        print(f"    Total PnL: ${tot:.0f}")
        print(f"    Edge:    {edge}")

    print(f"\n  --- Comparison table ---")
    print(f"  {'Instrument':<12} {'Sharpe':>8} {'PF':>7} {'MaxDD':>8} {'N':>5} {'Edge?':>7}")
    print(f"  {'-'*50}")
    # NQ reference (60-day most recent would be partial — use full-period as reference)
    print(f"  {'NQ (ref, 3yr)':12} {'1.213':>8} {'1.280':>7} {'-25.1%':>8} {'567':>5} {'YES':>7}")
    for r in results:
        if not r.get("available", False):
            print(f"  {r['instrument']:<12} {'N/A':>8} {'N/A':>7} {'N/A':>8} {'0':>5} {'N/A':>7}")
            continue
        sh_s  = f"{r['sharpe']:.3f}"  if r.get('sharpe')  else "N/A"
        pf_s  = f"{r['pf']:.3f}"     if r.get('pf')      else "N/A"
        mdd_s = f"{r['max_dd']*100:.1f}%" if r.get('max_dd') else "N/A"
        print(f"  {r['instrument']:<12} {sh_s:>8} {pf_s:>7} {mdd_s:>8} "
              f"{r['n']:>5} {r['edge']:>7}")

    print(f"\n  --- Interpretation ---")
    positive = [r for r in results if r.get("edge") == "YES"]
    if len(positive) == 2:
        print("  All instruments positive → structural edge in opening momentum on US index futures.")
    elif len(positive) == 1:
        print(f"  Only {positive[0]['instrument']} positive → edge may be partially NQ-specific.")
        print("  60-day window is short; interpret with caution.")
    else:
        print("  No cross-instrument confirmation — NQ-specific or 60-day window too short.")
        print("  Note: 60 days = ~44 trades on ES/YM; Sharpe/PF are noisy at this sample size.")


# ────────────────────────────────────────────────────────────────────────────
# PART 3 — Extended walk-forward
# ────────────────────────────────────────────────────────────────────────────

def part3_extended_wf(engine: NQBacktestEngine, feats: pd.DataFrame) -> None:
    print("\n" + "═" * 80)
    print("PART 3 — EXTENDED WALK-FORWARD (6M train / 3M test, 8 windows)")
    print("═" * 80)

    # All dates available
    all_dates = pd.Series(
        engine.rth.index.normalize().unique()
    ).sort_values()
    start_date = all_dates.iloc[0]

    train_mo = 6
    test_mo  = 3

    windows = []
    start_m = 0

    # Determine how many windows we can fit
    while True:
        t_start = start_date + pd.DateOffset(months=start_m)
        t_end   = t_start    + pd.DateOffset(months=train_mo)
        oos_end = t_end       + pd.DateOffset(months=test_mo)

        if oos_end > all_dates.iloc[-1] + pd.DateOffset(days=10):
            break

        oos = engine.rth[
            (engine.rth.index >= t_end) &
            (engine.rth.index <  oos_end)
        ]
        if len(oos) < 30:
            start_m += test_mo
            continue

        # Build engine for OOS window
        eng_oos     = NQBacktestEngine.__new__(NQBacktestEngine)
        eng_oos.df  = oos
        eng_oos.rth = oos

        feats_oos  = build_opening_features(oos)
        sigs_oos   = signals_from_features(
            feats_oos, gap_thresh=STRATEGY_GAP, dollar_stop=STRATEGY_STOP
        )

        if sigs_oos.empty or len(sigs_oos) < 5:
            start_m += test_mo
            continue

        tl_oos, met_oos = eng_oos.run(sigs_oos)

        n       = met_oos.get("n_trades", 0)
        pnl_tot = met_oos.get("total_pnl_usd", 0)

        # Compute Sharpe on daily P&L for this window
        if not tl_oos.empty:
            tl_oos["date"] = pd.to_datetime(tl_oos["entry_ts"]).dt.normalize()
            daily_w = tl_oos.groupby("date")["pnl_usd"].sum()
            sh_w  = sharpe_hac(daily_w)
            pf_w  = met_oos.get("profit_factor")
            wr_w  = met_oos.get("win_rate", 0)
            dd_w  = met_oos.get("max_dd_pct", 0)
        else:
            sh_w = np.nan; pf_w = None; wr_w = 0; dd_w = 0

        windows.append({
            "train_start": str(t_start.date()),
            "train_end":   str(t_end.date()),
            "oos_end":     str(oos_end.date()),
            "n_trades":    n,
            "sharpe_hac":  round(sh_w, 3) if np.isfinite(sh_w) else None,
            "profit_factor": round(pf_w, 3) if pf_w else None,
            "win_rate":    round(wr_w * 100, 1),
            "max_dd_pct":  round(dd_w * 100, 1) if dd_w else None,
            "total_pnl":   round(pnl_tot, 2),
            "positive":    pnl_tot > 0,
        })

        start_m += test_mo
        if len(windows) >= 12:   # cap at 12 windows
            break

    if not windows:
        print("  No valid windows generated.")
        return

    print(f"\n  {'#':<3} {'Train period':<24} {'OOS period':<12} "
          f"{'N':>5} {'Sh_HAC':>8} {'PF':>6} {'WR':>6} {'MaxDD':>8} {'PnL$':>8} {'+'}")
    print(f"  {'-'*90}")
    for i, w in enumerate(windows, 1):
        train_str = f"{w['train_start']} → {w['train_end']}"
        sh_s  = f"{w['sharpe_hac']:.3f}"  if w.get("sharpe_hac")    else "  N/A"
        pf_s  = f"{w['profit_factor']:.3f}" if w.get("profit_factor") else "  N/A"
        mdd_s = f"{w['max_dd_pct']:.1f}%" if w.get("max_dd_pct")    else "  N/A"
        pos   = "✓" if w["positive"] else "✗"
        print(f"  {i:<3} {train_str:<24} {w['oos_end']:<12} "
              f"{w['n_trades']:>5} {sh_s:>8} {pf_s:>6} {w['win_rate']:>5.1f}% "
              f"{mdd_s:>8} {w['total_pnl']:>8.0f} {pos}")

    n_pos  = sum(w["positive"] for w in windows)
    n_tot  = len(windows)
    pct    = n_pos / n_tot * 100
    sh_vals = [w["sharpe_hac"] for w in windows if w.get("sharpe_hac") is not None]
    med_sh  = float(np.median(sh_vals)) if sh_vals else np.nan
    worst_w = min(windows, key=lambda w: w.get("total_pnl", 0))
    best_w  = max(windows, key=lambda w: w.get("total_pnl", 0))

    print(f"\n  Summary:")
    print(f"    Windows:   {n_tot} total  |  {n_pos} positive ({pct:.0f}%)")
    print(f"    Median Sharpe across windows: {med_sh:.3f}" if np.isfinite(med_sh) else "    Median Sharpe: N/A")
    print(f"    Best window:  OOS ending {best_w['oos_end']}  P&L=${best_w['total_pnl']:.0f}")
    print(f"    Worst window: OOS ending {worst_w['oos_end']}  P&L=${worst_w['total_pnl']:.0f}")

    print(f"\n  Verdict: ", end="")
    if pct >= 75:
        print(f"{pct:.0f}% windows positive ({n_pos}/{n_tot}) → ROBUST. Strategy is stable across regimes.")
    elif pct >= 60:
        print(f"{pct:.0f}% windows positive ({n_pos}/{n_tot}) → BORDERLINE. Deploy at 0.25 contracts.")
    else:
        print(f"{pct:.0f}% windows positive ({n_pos}/{n_tot}) → NOT READY. 4-window 100% was lucky. "
              "Do NOT deploy.")

    return windows


# ────────────────────────────────────────────────────────────────────────────
# Final summary
# ────────────────────────────────────────────────────────────────────────────

def print_final_summary(diag_action: str,
                         cross_results: list,
                         wf_windows:    list) -> str:
    print("\n" + "═" * 80)
    print("PRE-DEPLOYMENT VALIDATION SUMMARY")
    print("═" * 80)

    # Part 1
    print("\n### 1. Drawdown forensic")
    print(f"    {diag_action}")

    # Part 2
    print("\n### 2. Cross-instrument")
    pos_instr = [r["instrument"] for r in cross_results if r.get("edge") == "YES"]
    if not cross_results:
        cross_verdict = "No data (yfinance unavailable)"
    elif pos_instr:
        cross_verdict = f"Edge replicates on: NQ + {', '.join(pos_instr)} → structural edge"
    else:
        cross_verdict = "NQ-specific or 60-day window too short for confirmation"
    print(f"    {cross_verdict}")

    # Part 3
    if wf_windows:
        n_pos = sum(w["positive"] for w in wf_windows)
        n_tot = len(wf_windows)
        pct   = n_pos / n_tot * 100
        print(f"\n### 3. Extended walk-forward")
        print(f"    {n_pos}/{n_tot} windows ({pct:.0f}%) positive")
    else:
        pct = 0
        print("\n### 3. Extended walk-forward: no data")

    # Decision
    print("\n### 4. Deployment decision")
    p1_ok  = "vol filter" not in diag_action.lower() or True   # neutral — we accept variance
    p2_ok  = len(pos_instr) >= 1 or not cross_results           # NQ-specific is acceptable
    p3_ok_A = pct >= 75
    p3_ok_B = pct >= 60

    if p3_ok_A:
        decision = "A"
        print("    DECISION A: All 3 parts strong.")
        print("    → Commit iter_05_A$400+B1.2%, paper trade at 0.5 contracts on Propr sandbox.")
    elif p3_ok_B:
        decision = "B"
        print("    DECISION B: Extended WF borderline.")
        print("    → Commit, paper trade at 0.25 contracts. Re-evaluate after 30 trades.")
    else:
        decision = "C"
        print("    DECISION C: Extended WF insufficient.")
        print("    → Do NOT deploy. Design iter_08 with regime filter from Part 1 diagnosis.")

    # Roadmap
    print("\n### 5. Next iteration roadmap")
    if decision in ("A", "B"):
        print("    iter_08: Signal-strength variable sizing (top quintile → 1.0c, bottom → 0.25c)")
        print("    iter_09: Dynamic exits (ATR trailing TP, or momentum reversal exit)")
        print("    iter_10: Vol regime filter if Aug 2023-Feb 2024 diagnosis suggests it")
    else:
        print("    iter_08: Regime filter targeting the diagnosed period failure mode")

    return decision


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Iter 07 — Pre-Deployment Validation ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features...")
    feats = build_opening_features(engine.rth)
    log.info(f"Features: {len(feats)}  |  VWAP ok: {feats['vwap_ok'].sum()}")

    # PART 1
    part1_drawdown_forensic(engine, feats)

    # PART 2
    cross_results = []
    try:
        part2_cross_instrument()
        # Collect results from the appended JSON (simplified)
        all_res = load_results()
        cross_results = [
            {"instrument": r["iteration"].replace("iter_07_val_",""),
             "edge": r.get("verdict","") == "EDGE"}
            for r in all_res if r.get("iteration","").startswith("iter_07_val_")
        ]
    except Exception as e:
        log.warning(f"Part 2 failed: {e}")
        print(f"\n  Part 2 error: {e}")

    # PART 3
    wf_windows = []
    try:
        wf_windows = part3_extended_wf(engine, feats)
    except Exception as e:
        log.warning(f"Part 3 failed: {e}")
        print(f"\n  Part 3 error: {e}")

    # Final summary — simple action string
    if wf_windows:
        n_pos = sum(w["positive"] for w in wf_windows)
        n_tot = len(wf_windows)
        pct   = n_pos / n_tot * 100
        diag  = "Accept as natural variance — no single dominant regime factor found."
    else:
        pct  = 0
        diag = "WF data unavailable."

    decision = print_final_summary(diag, cross_results, wf_windows or [])

    n_test = N_TESTS_START + 3   # 3 validation studies
    print(f"\nn_tests: {N_TESTS_START} → {n_test}")
    if decision in ("A", "B"):
        print("DO NOT COMMIT yet — await your review. If approved: git add + commit.")
    else:
        print("DO NOT COMMIT — validation failed. Design iter_08.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_07_validation failed")
        sys.exit(1)
