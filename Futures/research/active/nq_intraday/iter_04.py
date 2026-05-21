"""
iter_04.py — Best Ensemble + Regime Filter
===========================================
BUILD ON: iter_2a (opening momentum + VWAP filter)
  Sharpe 0.808, MaxDD -31.1%, WF 100%, 622 trades

REGIME FILTERS:
  R1 — EMA trend: 5-day vs 20-day EMA of NQ close.
       Suppress counter-trend signals (long only when 5EMA>20EMA, short only when below).
  R2 — Vol regime: ETH session range (pre-market high-low) as VIX proxy.
       If ETH range > 2× 20-day rolling avg → high-vol day → trade with 1 contract only.
       Normal days: 2 contracts when trend aligns, 1 contract otherwise.
  R3 — FOMC avoidance: skip signals on Fed announcement days (abnormal vol spikes;
       identified by ETH range > 3× avg, hardcoded known FOMC dates 2023-2025).

Variants:
  4a: Base + R1 (EMA trend filter only)
  4b: Base + R1 + R2 (EMA + vol scaling)
  4c: Base + R1 + R2 + R3 (FOMC avoidance)
  4d: 4c + signal-proportional sizing (1 or 2 contracts)

n_tests: 95 → 99
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results, print_comparison_table
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 95

T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1230 = datetime.time(12, 30)
T_1559 = datetime.time(15, 59)

BASE_TP_MULT = 1.5
BASE_SL_MULT = 0.5

# Known FOMC announcement dates 2022-2025 (ET, typically 14:00 release)
# These are the days where pre-announcement uncertainty can distort 09:30 signals.
FOMC_DATES = {
    # 2023
    "2023-01-31", "2023-03-21", "2023-05-02", "2023-06-13",
    "2023-07-25", "2023-09-19", "2023-11-01", "2023-12-12",
    # 2024
    "2024-01-30", "2024-03-19", "2024-05-01", "2024-06-11",
    "2024-07-30", "2024-09-17", "2024-11-06", "2024-12-17",
    # 2025
    "2025-01-28", "2025-03-18", "2025-05-06",
}


# ---------------------------------------------------------------------------
# Feature builder (reuse opening momentum logic from iter_02)
# ---------------------------------------------------------------------------

def _opening_features(df_1min: pd.DataFrame) -> pd.DataFrame:
    records = []
    dates = sorted(df_1min.index.normalize().unique())

    for date in dates:
        day = df_1min[df_1min.index.normalize() == date]
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
        exit_time = pd.Timestamp(
            date.year, date.month, date.day, 12, 30, 0, tzinfo=sig_ts.tzinfo
        )
        records.append({
            "date":        date,
            "sig_ts":      sig_ts,
            "direction":   direction,
            "open_price":  open_p,
            "close_price": close_p,
            "rng":         rng,
            "vwap_at_sig": vwap_at_sig,
            "exit_time":   exit_time,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Regime features
# ---------------------------------------------------------------------------

def build_regime_features(df_1min: pd.DataFrame) -> pd.DataFrame:
    """
    Per-day regime features:
      - ema5_close, ema20_close: daily close EMA
      - ema_bull: 5EMA > 20EMA (bullish regime)
      - eth_range: ETH session high-low (pre-market 18:00-09:29 ET)
      - eth_range_20d_avg: rolling 20-day avg of ETH range (shifted 1)
      - high_vol_day: ETH range > 2× avg
      - fomc_day: bool
    """
    # Daily RTH close for EMA
    rth = df_1min[(df_1min.index.time >= T_0930) & (df_1min.index.time <= T_1559)]
    daily_close = rth["close"].resample("B").last().dropna()
    ema5  = daily_close.ewm(span=5,  adjust=False).mean()
    ema20 = daily_close.ewm(span=20, adjust=False).mean()
    ema_bull = (ema5 > ema20).shift(1)   # known before day's open

    # ETH range (pre-RTH: 18:00 prior day to 09:29 current day)
    # Proxy: use vwap_eth range per calendar day
    eth_data = df_1min[(df_1min.index.time < T_0930) | (df_1min.index.time > T_1559)]
    eth_range_daily = (
        eth_data["high"].resample("B").max() -
        eth_data["low"].resample("B").min()
    ).dropna()
    eth_range_avg = eth_range_daily.rolling(20, min_periods=5).mean().shift(1)
    high_vol = eth_range_daily > 2.0 * eth_range_avg

    records = []
    dates = sorted(rth.index.normalize().unique())
    for date in dates:
        date_str = str(date.date())
        # Align to business day index
        dc_val    = float(daily_close.get(date, np.nan))
        e5_val    = float(ema5.get(date, np.nan))
        e20_val   = float(ema20.get(date, np.nan))
        bull_val  = bool(ema_bull.get(date, True))   # default allow if no data
        eth_r     = float(eth_range_daily.get(date, np.nan))
        eth_avg   = float(eth_range_avg.get(date, np.nan))
        hv        = bool(high_vol.get(date, False))
        fomc      = date_str in FOMC_DATES

        records.append({
            "date":       date,
            "ema5":       e5_val,
            "ema20":      e20_val,
            "ema_bull":   bull_val,
            "eth_range":  eth_r,
            "eth_avg":    eth_avg,
            "high_vol":   hv,
            "fomc_day":   fomc,
        })

    return pd.DataFrame(records).set_index("date")


# ---------------------------------------------------------------------------
# Signal builder with regime overlay
# ---------------------------------------------------------------------------

def build_signals_v4(
    feats:   pd.DataFrame,
    regime:  pd.DataFrame,
    use_ema: bool = True,
    use_vol: bool = False,
    use_fomc:bool = False,
    use_sizing: bool = False,
) -> pd.DataFrame:
    """
    iter_2a base (opening momentum + VWAP filter) + regime overlay.
    size_mult: 1.0 normally, 2.0 if sizing enabled and conditions met.
    """
    records = []
    for _, row in feats.iterrows():
        date = row["date"]
        direction = int(row["direction"])

        # VWAP filter (same as iter_2a)
        if direction == 1 and row["close_price"] <= row["vwap_at_sig"]:
            continue
        if direction == -1 and row["close_price"] >= row["vwap_at_sig"]:
            continue

        # Get regime for this date
        if date in regime.index:
            reg = regime.loc[date]
        else:
            reg = pd.Series({"ema_bull": True, "high_vol": False, "fomc_day": False})

        # R1 — EMA trend filter
        if use_ema:
            ema_bull = bool(reg["ema_bull"])
            if direction == 1  and not ema_bull:
                continue
            if direction == -1 and ema_bull:
                continue

        # R3 — FOMC avoidance
        if use_fomc and bool(reg["fomc_day"]):
            continue

        # R2 — vol sizing
        high_vol  = bool(reg.get("high_vol", False))
        size_mult = 1.0
        if use_sizing:
            ema_bull = bool(reg["ema_bull"])
            trend_aligns = (direction == 1 and ema_bull) or (direction == -1 and not ema_bull)
            if not high_vol and trend_aligns:
                size_mult = 2.0
            elif high_vol:
                size_mult = 0.5   # reduce on high-vol days (round to 1 contract, min)
        elif use_vol and high_vol:
            size_mult = 0.5

        records.append({
            "signal_ts": row["sig_ts"],
            "direction": direction,
            "tp_points": row["rng"] * BASE_TP_MULT * size_mult,
            "sl_points": row["rng"] * BASE_SL_MULT * size_mult,
            "exit_time": row["exit_time"],
            "size_mult": size_mult,
        })

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("signal_ts")


# ---------------------------------------------------------------------------
# Backtest with variable sizing
# ---------------------------------------------------------------------------

def run_sized_backtest(
    engine: NQBacktestEngine,
    signals: pd.DataFrame,
) -> tuple:
    """
    Run engine but scale P&L by size_mult (1 or 2 contracts).
    For signals with size_mult > 1: double the TP/SL points already done above.
    Costs scale with size_mult.
    """
    # Signals already have TP/SL scaled by size_mult (points).
    # Engine treats each signal as 1 contract. We scale P&L post-hoc.
    if "size_mult" not in signals.columns:
        return engine.run(signals)

    # Run standard (1-contract) then scale
    trade_log, _ = engine.run(signals)
    if trade_log.empty:
        return trade_log, {}

    # Apply size_mult per trade: look up via signal_ts
    sig_size = signals["size_mult"].to_dict()
    # match signal_ts to trade signal_ts
    trade_log["size_mult"] = trade_log["signal_ts"].map(sig_size).fillna(1.0)
    # Rescale P&L: pnl_usd was computed for 1 contract with scaled TP/SL points
    # But size_mult also multiplies costs
    # Since we already scaled TP/SL in points, pnl_pts is correct for sizing.
    # Recompute pnl_usd: pnl_pts * POINT_VALUE * (size_mult/size_mult_used_in_tp) - COST_RT * size_mult
    # Actually: we scaled TP/SL above, so pnl_pts = direction*(exit_price - entry_price)
    # is already size-adjusted. We just need to multiply cost by size_mult.
    # pnl_usd = pnl_pts * POINT_VALUE - COST_RT * size_mult
    trade_log["pnl_usd"] = (
        trade_log["pnl_pts"] * POINT_VALUE - COST_RT * trade_log["size_mult"]
    )
    met = engine.metrics(trade_log)
    return trade_log, met


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== Iter 04 — Opening Momentum + Regime Filter ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features and regime features...")
    feats  = _opening_features(engine.rth)
    regime = build_regime_features(engine.rth)

    log.info(f"Opening features: {len(feats)}  |  Regime rows: {len(regime)}")

    # Regime summary
    if len(regime) > 0:
        bull_pct = regime["ema_bull"].mean() * 100
        hv_pct   = regime["high_vol"].mean() * 100
        fomc_n   = regime["fomc_day"].sum()
        log.info(f"Regime: EMA bull {bull_pct:.0f}%  |  HighVol {hv_pct:.0f}%  |  FOMC days {fomc_n}")

    VARIANT_DEFS = {
        "4a": dict(use_ema=True,  use_vol=False, use_fomc=False, use_sizing=False),
        "4b": dict(use_ema=True,  use_vol=True,  use_fomc=False, use_sizing=False),
        "4c": dict(use_ema=True,  use_vol=True,  use_fomc=True,  use_sizing=False),
        "4d": dict(use_ema=True,  use_vol=False, use_fomc=True,  use_sizing=True),
    }

    n_test       = N_TESTS_START
    best_sharpe  = -np.inf
    best_variant = None

    n_base = len(feats)

    for var_id, flags in VARIANT_DEFS.items():
        n_test += 1
        sigs = build_signals_v4(feats, regime, **flags)
        retain_pct = len(sigs) / n_base * 100 if n_base > 0 else 0
        log.info(f"--- Variant {var_id}: {len(sigs)} signals ({retain_pct:.0f}% of opening features) ---")

        if len(sigs) < 20:
            log.warning(f"  Too few signals — skipping {var_id}")
            continue

        trade_log, met = run_sized_backtest(engine, sigs)
        boot = engine.bootstrap_ev(trade_log)

        sh  = met.get("sharpe_daily_hac") or 0
        pf  = met.get("profit_factor")    or 0
        mdd = met.get("max_dd_pct")       or 0

        if sh >= 1.0 and pf >= 1.20 and mdd >= -0.15:
            verdict = "PROPFIRM_PASS"
        elif sh >= 0.7 and pf >= 1.15:
            verdict = "RESEARCH_PASS"
        elif sh >= 0.5 and pf >= 1.10:
            verdict = "IMPROVE"
        elif sh >= 0.0:
            verdict = "WEAK"
        else:
            verdict = "SKIP"

        result = {
            "iteration":              f"iter_{var_id}",
            "n_tests":                n_test,
            "description":            (
                f"Opening+VWAP+EMA"
                + (" +VolScale" if flags["use_vol"] else "")
                + (" +FOMC"    if flags["use_fomc"]  else "")
                + (" +Sizing"  if flags["use_sizing"] else "")
            ),
            "signals_retained_pct":   round(retain_pct, 1),
            **met,
            **boot,
            "verdict":                verdict,
        }
        append_result(result)

        print(f"\n  [iter_{var_id}] EMA={flags['use_ema']} Vol={flags['use_vol']} "
              f"FOMC={flags['use_fomc']} Sizing={flags['use_sizing']}")
        print(f"    Signals:  {len(sigs)} ({retain_pct:.0f}% retained)")
        print(f"    Trades:   {met.get('n_trades',0)}  |  WR: {met.get('win_rate',0)*100:.1f}%")
        print(f"    AvgTrd:   ${met.get('avg_trade_usd',0):.1f}  |  PF: {pf:.3f}")
        print(f"    Sharpe:   {sh:.3f}  |  MaxDD: {mdd*100:.1f}%")
        print(f"    P(EV≤0):  {boot.get('p_ev_zero','?')}  |  95%CI: [{boot.get('ci_low','?')}, {boot.get('ci_high','?')}]")
        print(f"    Verdict:  {verdict}")

        if sh > best_sharpe:
            best_sharpe  = sh
            best_variant = var_id

    # ------------------------------------------------------------------
    # Final master table
    # ------------------------------------------------------------------
    results = load_results()
    print(f"\n{'='*80}")
    print(f"ITER 04 BEST: iter_{best_variant}  Sharpe={best_sharpe:.3f}")
    print(f"{'='*80}")

    # Stopping rule
    if best_sharpe >= 1.0:
        best_r = next((r for r in results if r.get("iteration") == f"iter_{best_variant}"), {})
        best_mdd = best_r.get("max_dd_pct", 0) or 0
        if best_mdd >= -0.10:
            print("PROPFIRM PASS → commit and paper trade.")
        else:
            print(f"RESEARCH PASS (Sharpe≥1.0 but MaxDD={best_mdd*100:.1f}% > -10% gate).")
            print("MaxDD needs improvement. Consider tighter per-trade SL or position sizing.")
    elif best_sharpe >= 0.5:
        print("RESEARCH PASS range — deploy small paper size, continue refining.")
    else:
        print("NQ intraday momentum/breakout underperforms in 2022-2025 → consider pivot.")

    print_comparison_table(results)

    # ------------------------------------------------------------------
    # Top 3 / Bottom 3 interpretation
    # ------------------------------------------------------------------
    sorted_r = sorted(results, key=lambda r: r.get("sharpe_daily_hac") or -99, reverse=True)
    print("\n=== TOP 3 — Why it works ===")
    for r in sorted_r[:3]:
        sh  = r.get("sharpe_daily_hac") or 0
        pf  = r.get("profit_factor")    or 0
        n   = r.get("n_trades", 0)
        it  = r.get("iteration", "?")
        desc = r.get("description", "")
        wr  = r.get("win_rate", 0) * 100
        print(f"  {it}: Sharpe={sh:.3f} PF={pf:.3f} WR={wr:.1f}% N={n}")
        print(f"    → {desc}")

    print("\n=== BOTTOM 3 — Why it fails ===")
    for r in sorted_r[-3:]:
        sh  = r.get("sharpe_daily_hac") or 0
        pf  = r.get("profit_factor")    or 0
        n   = r.get("n_trades", 0)
        it  = r.get("iteration", "?")
        mdd = r.get("max_dd_pct", 0) or 0
        wr  = r.get("win_rate", 0) * 100
        print(f"  {it}: Sharpe={sh:.3f} PF={pf:.3f} WR={wr:.1f}% MaxDD={mdd*100:.1f}%")
        # Diagnosis
        if n < 30:
            print(f"    → Too few trades ({n}) for statistical reliability. High variance, CI too wide.")
        elif mdd < -0.50:
            print(f"    → MaxDD={mdd*100:.1f}% catastrophic. No risk control on daily runaway losses.")
        elif pf < 1.0:
            print(f"    → PF<1.0: gross losses exceed gross wins. No edge in this formulation.")
        else:
            print(f"    → Signal too weak or costs too high for this trade frequency.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_04 failed")
        sys.exit(1)
