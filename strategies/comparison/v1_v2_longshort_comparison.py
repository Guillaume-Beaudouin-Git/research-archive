#!/usr/bin/env python3
"""
strategies/comparison/v1_v2_longshort_comparison.py

TSMOM Variants Comparison — V1 vs V2 vs Long/Short on Propr Starter
====================================================================
44 simulations per variant: 2025-01-06 to 2025-11-03 (weekly Mondays)
Propr Starter: $5,000 initial, 10% target, 6% total DD, 3% daily DD

WHY WE WENT LONG-ONLY
──────────────────────
In v1 backtests (2019–2025), the cross-sectional momentum strategy showed:
  Long leg:  +105% cumulative return
  Short leg: −107% cumulative return (LOST money)
  Net:       −1%  (short side destroyed all long-side gains)

Reason: crypto LOSERS mean-revert. Coins that dropped 80% in a bear market
bounce violently when sentiment shifts. Shorting them systematically gets
squeezed repeatedly.

Conclusion at the time: short side has no edge → long-only for v2.

BUT: v1 live Telegram shows ETH SHORT generating POSITIVE returns because
the TSMOM signal correctly identified ETH as bearish (28-day return < 0)
and shorted it profitably.

The key distinction:
  Cross-sectional momentum short (short the WORST performers) = BAD
  Time-series momentum short (short when OWN 28d return < 0)  = ???

This script tests whether TSMOM short signals have edge on these assets.

FOUR VARIANTS
─────────────
V1: 3-asset L/S   — BTC/ETH/SOL, signal = ±1 (original style)
V2: 11-asset Long — long-only at signal=+1, flat at signal=−1 (current live)
V3: 11-asset L/S  — full ±1 signal on all 11 assets
V4: 11-asset L+hS — long at full vol (15%), short at half vol (7.5%)
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from pathlib import Path
from dataclasses import dataclass, field
from scipy import stats
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# ── constants ──────────────────────────────────────────────────────────────────

ASSETS_V1: List[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]
ASSETS_FULL: List[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD", "OP-USD",
]
# MATIC-USD and UNI-USD: silently skipped (delisted)

PROPR_INITIAL: float = 5_000.0
PROPR_TARGET:  float = 5_500.0
PROPR_TOTAL_DD: float = 0.06     # 6% of initial equity
PROPR_DAILY_DD: float = 0.03     # 3% of day-start equity
COST_RT:         float = 0.0017  # 0.17% round trip
VOL_TARGET_LONG:  float = 0.15
VOL_TARGET_SHORT: float = 0.075  # V4 cautious short
VOL_WINDOW:  int = 30
SIG_WINDOW:  int = 28
GROSS_CAP:  float = 0.90
ENTRY_FEE:  float = 60.0

DATA_START = "2024-07-01"
DATA_END   = "2026-05-14"
SIM_DATES  = pd.date_range("2025-01-06", "2025-11-03", freq="W-MON")

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {"V1": "#2196F3", "V2": "#4CAF50", "V3": "#F44336", "V4": "#FF9800"}


# ── data types ─────────────────────────────────────────────────────────────────

@dataclass
class DayRecord:
    """Position record for one asset on one day (used for edge analysis)."""
    asset: str
    direction: int         # +1 long, -1 short
    notional: float        # absolute USD
    daily_return: float    # asset close-to-close return


@dataclass
class SimResult:
    start_date: pd.Timestamp
    outcome: str           # "PASS", "FAIL_DAILY", "FAIL_TOTAL", "INCOMPLETE"
    n_days: int
    final_equity: float
    max_dd: float          # positive fraction of initial equity
    equity_curve: List[float] = field(default_factory=list)
    daily_pnl: List[float] = field(default_factory=list)
    daily_pnl_long: List[float] = field(default_factory=list)
    daily_pnl_short: List[float] = field(default_factory=list)
    position_records: List[DayRecord] = field(default_factory=list)


# ── data loading ───────────────────────────────────────────────────────────────

def load_prices(assets: List[str]) -> pd.DataFrame:
    """Download adjusted close prices. Silently skip unavailable tickers."""
    frames: Dict[str, pd.Series] = {}
    for ticker in assets:
        try:
            raw = yf.download(
                ticker, start=DATA_START, end=DATA_END,
                auto_adjust=True, progress=False, multi_level_index=False,
            )
            if raw.empty or len(raw) < SIG_WINDOW + VOL_WINDOW + 5:
                continue
            close = raw["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.squeeze()
            frames[ticker] = close
        except Exception:
            pass
    if not frames:
        raise RuntimeError("No price data downloaded — check network/yfinance.")
    df = pd.DataFrame(frames).sort_index().ffill()
    return df


# ── signal & vol computation ──────────────────────────────────────────────────

def compute_signals_and_vol(
    prices: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    signals:     +1 (long) or -1 (short), based on sign of 28d log return.
    vol_scalars: VOL_TARGET_LONG / ann_vol, clipped to [0.1, 2.0].
    Both DataFrames share the same index and columns as prices.
    """
    log_rets    = np.log(prices / prices.shift(1))
    cum28       = log_rets.rolling(SIG_WINDOW).sum()
    signals     = np.sign(cum28).replace(0, 1)   # exact-zero → default long

    ann_vol     = log_rets.rolling(VOL_WINDOW).std() * np.sqrt(252)
    ann_vol     = ann_vol.replace(0, np.nan)
    vol_scalars = (VOL_TARGET_LONG / ann_vol).clip(0.1, 2.0)

    return signals.astype(float), vol_scalars


# ── position builder ──────────────────────────────────────────────────────────

def build_positions(
    equity: float,
    assets: List[str],
    sig_row: pd.Series,
    vs_row: pd.Series,
    long_only: bool = False,
    short_vol_target: Optional[float] = None,
) -> Dict[str, float]:
    """
    Compute target notional positions in USD (negative = short).

    Applies 90% gross cap: sum(|notionals|) ≤ 0.90 × equity.

    short_vol_target: if provided, short positions use a different vol target
                      (e.g., 0.075 for V4 cautious short at half-size).
                      If None, short positions use the same VOL_TARGET_LONG.
    """
    raw: Dict[str, float] = {}

    for asset in assets:
        sig = float(sig_row.get(asset, np.nan))
        vs  = float(vs_row.get(asset, np.nan))
        if np.isnan(sig) or np.isnan(vs):
            continue

        if sig > 0:
            # Long: notional = equity × (VOL_TARGET_LONG / ann_vol)
            raw[asset] = equity * vs
        else:
            # Short
            if long_only:
                continue
            if short_vol_target is not None:
                # Scale vol scalar proportionally to the desired short vol target
                # vs = VOL_TARGET_LONG / ann_vol  →  short_vs = short_vol_target / ann_vol
                short_vs = vs * (short_vol_target / VOL_TARGET_LONG)
                short_vs = min(short_vs, 2.0)
            else:
                short_vs = vs
            raw[asset] = -equity * short_vs

    # Apply 90% gross cap
    gross = sum(abs(v) for v in raw.values())
    cap   = equity * GROSS_CAP
    if gross > cap and gross > 0:
        scale = cap / gross
        raw   = {k: v * scale for k, v in raw.items()}

    return raw


# ── simulation engine ─────────────────────────────────────────────────────────

def simulate_one(
    start_date: pd.Timestamp,
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    vol_scalars: pd.DataFrame,
    assets: List[str],
    long_only: bool = False,
    short_vol_target: Optional[float] = None,
) -> SimResult:
    """
    Run one Propr challenge simulation from start_date.

    Rebalance every Monday using signal from previous trading day (Friday).
    Costs applied on every position change (0.17% RT).
    Daily limit check uses market P&L only (not transaction costs).
    """
    # Get all trading days from start_date onward in our price data
    all_days = prices.index[prices.index >= start_date]
    if len(all_days) == 0:
        return SimResult(
            start_date=start_date, outcome="INCOMPLETE",
            n_days=0, final_equity=PROPR_INITIAL, max_dd=0.0,
        )

    equity    = PROPR_INITIAL
    positions: Dict[str, float] = {}   # asset → notional (negative = short)

    equity_curve     : List[float]     = [equity]
    daily_pnl_all    : List[float]     = []
    daily_pnl_long   : List[float]     = []
    daily_pnl_short  : List[float]     = []
    position_records : List[DayRecord] = []

    max_dd  = 0.0
    outcome = "INCOMPLETE"
    n_days  = 0

    for day in all_days:
        n_days += 1
        day_start_equity = equity

        # Previous trading day (for signal and close-to-close return)
        prev_days_before = prices.index[prices.index < day]
        if len(prev_days_before) == 0:
            equity_curve.append(equity)
            daily_pnl_all.append(0.0)
            daily_pnl_long.append(0.0)
            daily_pnl_short.append(0.0)
            continue
        prev_day = prev_days_before[-1]

        # ── Monday rebalance ────────────────────────────────────────────────
        if day.dayofweek == 0:
            if prev_day in signals.index and prev_day in vol_scalars.index:
                sig_row = signals.loc[prev_day]
                vs_row  = vol_scalars.loc[prev_day]

                # Only trade assets with valid prices on both days
                valid = [
                    a for a in assets
                    if a in prices.columns
                    and not pd.isna(prices.at[day, a])
                    and not pd.isna(prices.at[prev_day, a])
                ]

                new_pos = build_positions(
                    equity=equity,
                    assets=valid,
                    sig_row=sig_row,
                    vs_row=vs_row,
                    long_only=long_only,
                    short_vol_target=short_vol_target,
                )

                # Transaction costs on notional changes
                all_touched = set(positions) | set(new_pos)
                for a in all_touched:
                    old_n  = positions.get(a, 0.0)
                    new_n  = new_pos.get(a, 0.0)
                    change = abs(new_n - old_n)
                    if change > 0.01:
                        equity -= change * COST_RT

                positions = new_pos

        # ── Mark to market ─────────────────────────────────────────────────
        pnl   = 0.0
        pnl_l = 0.0
        pnl_s = 0.0

        for asset, notional in positions.items():
            if asset not in prices.columns:
                continue
            c_d = prices.at[day, asset]
            c_p = prices.at[prev_day, asset]
            if pd.isna(c_d) or pd.isna(c_p) or c_p == 0:
                continue

            ret    = (c_d - c_p) / c_p
            dp     = notional * ret    # negative notional → loss when price rises
            pnl   += dp

            if notional > 0:
                pnl_l += dp
            else:
                pnl_s += dp

            position_records.append(DayRecord(
                asset=asset,
                direction=1 if notional > 0 else -1,
                notional=abs(notional),
                daily_return=ret,
            ))

        # ── End-of-day checks ───────────────────────────────────────────────
        daily_dd_frac = -pnl / day_start_equity if day_start_equity > 0 else 0.0

        equity += pnl
        equity_curve.append(equity)
        daily_pnl_all.append(pnl)
        daily_pnl_long.append(pnl_l)
        daily_pnl_short.append(pnl_s)

        current_dd = max(0.0, (PROPR_INITIAL - equity) / PROPR_INITIAL)
        if current_dd > max_dd:
            max_dd = current_dd

        # Order matters: daily DD first, then total DD, then target
        if daily_dd_frac > PROPR_DAILY_DD:
            outcome = "FAIL_DAILY"
            break
        if current_dd > PROPR_TOTAL_DD:
            outcome = "FAIL_TOTAL"
            break
        if equity >= PROPR_TARGET:
            outcome = "PASS"
            break

    return SimResult(
        start_date=start_date,
        outcome=outcome,
        n_days=n_days,
        final_equity=equity,
        max_dd=max_dd,
        equity_curve=equity_curve,
        daily_pnl=daily_pnl_all,
        daily_pnl_long=daily_pnl_long,
        daily_pnl_short=daily_pnl_short,
        position_records=position_records,
    )


def run_variant(
    label: str,
    assets: List[str],
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    vol_scalars: pd.DataFrame,
    long_only: bool,
    short_vol_target: Optional[float] = None,
) -> Tuple[str, List[SimResult]]:
    """Run all 44 simulations for one variant. Print progress summary."""
    print(f"  Running {label}...", end="", flush=True)
    results: List[SimResult] = []
    for date in SIM_DATES:
        results.append(simulate_one(
            start_date=date,
            prices=prices,
            signals=signals,
            vol_scalars=vol_scalars,
            assets=assets,
            long_only=long_only,
            short_vol_target=short_vol_target,
        ))

    n        = len(results)
    passes   = sum(1 for r in results if r.outcome == "PASS")
    fail_d   = sum(1 for r in results if r.outcome == "FAIL_DAILY")
    fail_t   = sum(1 for r in results if r.outcome == "FAIL_TOTAL")
    print(f" {passes/n*100:.0f}%  ({passes} pass | {fail_d} daily | {fail_t} total DD)")
    return label, results


# ── short-signal edge analysis ────────────────────────────────────────────────

def analyze_short_edge(
    results: List[SimResult],
    assets: List[str],
    signals_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per-asset short signal edge analysis.

    Returns DataFrame with columns:
      asset, short_signal_freq (% of weeks signal=-1),
      short_mean_return (% per day), long_mean_return,
      short_tstat (t-test vs zero), n_short_days.
    """
    # Signal frequency from the full dataset (not just simulation period)
    sig_freq: Dict[str, float] = {}
    for a in assets:
        if a in signals_df.columns:
            s = signals_df[a].dropna()
            sig_freq[a] = float((s == -1).mean() * 100)
        else:
            sig_freq[a] = float("nan")

    # Per-asset P&L from position records
    long_rets_map:  Dict[str, List[float]] = {a: [] for a in assets}
    short_rets_map: Dict[str, List[float]] = {a: [] for a in assets}

    for r in results:
        for rec in r.position_records:
            if rec.asset not in long_rets_map:
                continue
            if rec.direction > 0:
                long_rets_map[rec.asset].append(rec.daily_return)
            else:
                # Short earns when price falls: pnl_pct = -ret
                short_rets_map[rec.asset].append(-rec.daily_return)

    rows = []
    for asset in assets:
        short_arr = np.array(short_rets_map.get(asset, []))
        long_arr  = np.array(long_rets_map.get(asset, []))

        short_mean  = float(np.mean(short_arr) * 100) if len(short_arr) >= 3 else float("nan")
        long_mean   = float(np.mean(long_arr)  * 100) if len(long_arr)  >= 3 else float("nan")

        if len(short_arr) >= 3:
            std_s = np.std(short_arr, ddof=1)
            short_t = float(np.mean(short_arr) / (std_s / np.sqrt(len(short_arr)))) if std_s > 0 else float("nan")
        else:
            short_t = float("nan")

        rows.append({
            "asset":             asset.replace("-USD", ""),
            "short_signal_freq": round(sig_freq.get(asset, float("nan")), 1),
            "short_mean_pct":    round(short_mean, 4) if not np.isnan(short_mean) else float("nan"),
            "long_mean_pct":     round(long_mean, 4)  if not np.isnan(long_mean)  else float("nan"),
            "short_tstat":       round(short_t, 2)    if not np.isnan(short_t)    else float("nan"),
            "n_short_days":      len(short_arr),
        })

    return pd.DataFrame(rows)


# ── daily distribution analysis ───────────────────────────────────────────────

def analyze_daily_distribution(results: List[SimResult]) -> Dict[str, float]:
    """
    Collect all daily P&L pct values across all simulations.
    Returns mean, std, skew, p5, p1, and breach frequency.
    """
    all_pct: List[float] = []
    for r in results:
        for i, pnl in enumerate(r.daily_pnl):
            eq = r.equity_curve[i] if i < len(r.equity_curve) else PROPR_INITIAL
            if eq > 0:
                all_pct.append(pnl / eq * 100)
    if not all_pct:
        return {}
    arr = np.array(all_pct)
    return {
        "mean":           float(np.mean(arr)),
        "std":            float(np.std(arr)),
        "skew":           float(stats.skew(arr)),
        "p5":             float(np.percentile(arr, 5)),
        "p1":             float(np.percentile(arr, 1)),
        "pct_breach_3":   float(np.mean(arr < -3) * 100),   # % days below -3%
        "pct_abs_gt3":    float(np.mean(np.abs(arr) > 3) * 100),
        "n_days":         len(arr),
    }


# ── correlation between long and short legs ───────────────────────────────────

def analyze_leg_correlation(results: List[SimResult]) -> float:
    """
    Average correlation between long-leg and short-leg daily P&L.
    Returns NaN if fewer than 10 days with both legs active.
    """
    corrs: List[float] = []
    for r in results:
        l_arr = np.array(r.daily_pnl_long)
        s_arr = np.array(r.daily_pnl_short)
        mask  = (np.abs(l_arr) > 0.01) & (np.abs(s_arr) > 0.01)
        if mask.sum() < 10:
            continue
        try:
            c = float(np.corrcoef(l_arr[mask], s_arr[mask])[0, 1])
            if not np.isnan(c):
                corrs.append(c)
        except Exception:
            pass
    return float(np.mean(corrs)) if corrs else float("nan")


# ── calendar analysis ─────────────────────────────────────────────────────────

def calendar_analysis(results: List[SimResult]) -> pd.DataFrame:
    """Pass rate by start month."""
    records = [
        {
            "month":      r.start_date.strftime("%Y-%m"),
            "month_name": r.start_date.strftime("%b %Y"),
            "passed":     r.outcome == "PASS",
        }
        for r in results
    ]
    df = pd.DataFrame(records)
    agg = (
        df.groupby(["month", "month_name"])["passed"]
        .agg(passes=("sum"), total=("count"))
        .reset_index()
    )
    agg["pass_rate"] = agg["passes"] / agg["total"] * 100
    return agg.sort_values("month").reset_index(drop=True)


# ── printing ──────────────────────────────────────────────────────────────────

def _fmt(value: float, fmt: str, nan_str: str = " N/A") -> str:
    if np.isnan(value):
        return nan_str
    return fmt.format(value)


def print_comparison_table(
    variants: List[Tuple[str, List[SimResult]]],
) -> None:
    def _s(results: List[SimResult]) -> Dict:
        n       = len(results)
        pass_ct = sum(1 for r in results if r.outcome == "PASS")
        fail_d  = sum(1 for r in results if r.outcome == "FAIL_DAILY")
        fail_t  = sum(1 for r in results if r.outcome == "FAIL_TOTAL")
        pr      = pass_ct / n * 100
        pass_rs = [r.n_days for r in results if r.outcome == "PASS"]
        avg_d   = float(np.mean(pass_rs)) if pass_rs else float("nan")
        med_dd  = float(np.median([r.max_dd for r in results])) * 100
        exp_fee = ENTRY_FEE / (pr / 100) if pr > 0 else float("inf")
        return dict(
            pass_ct=pass_ct, fail_d=fail_d, fail_t=fail_t,
            pr=pr, avg_d=avg_d, med_dd=med_dd, exp_fee=exp_fee, n=n,
        )

    sv = [_s(res) for _, res in variants]

    header_row = f"{'':24s}"
    for lbl, _ in variants:
        header_row += f" | {lbl:>14s}"
    print()
    print("=" * (25 + 18 * len(variants)))
    print("TSMOM VARIANTS COMPARISON — Propr Starter Challenge")
    print(f"44 simulations, {SIM_DATES[0].date()} to {SIM_DATES[-1].date()}")
    print("=" * (25 + 18 * len(variants)))
    print(header_row)
    print("-" * (25 + 18 * len(variants)))

    rows_spec = [
        ("Pass rate",          "pr",      "{:.0f}%"),
        ("Daily limit fails",  "fail_d",  "{}/44"),
        ("Total DD fails",     "fail_t",  "{}/44"),
        ("Avg days to pass",   "avg_d",   "{:.0f}d"),
        ("Median max DD",      "med_dd",  "-{:.1f}%"),
        ("Expected fee/pass",  "exp_fee", "${:.0f}"),
    ]

    for (row_lbl, key, fmt) in rows_spec:
        row = f"  {row_lbl:22s}"
        for s in sv:
            val = s[key]
            row += " | " + _fmt(val, fmt).rjust(14)
        print(row)

    print("=" * (25 + 18 * len(variants)))


def print_short_edge(label: str, edge_df: pd.DataFrame) -> None:
    if edge_df.empty:
        return
    print(f"\nSHORT SIGNAL EDGE — {label}")
    print(f"  {'Asset':<8} {'Sig=-1%':>8} {'LongRet%':>9} {'ShortRet%':>10} "
          f"{'t-stat':>8} {'n_days':>7}  {'edge?':>5}")
    print(f"  {'-'*62}")
    for _, row in edge_df.iterrows():
        asset  = str(row["asset"])
        sf     = _fmt(row["short_signal_freq"], "{:.0f}%")
        lr     = _fmt(row["long_mean_pct"],     "{:.3f}%")
        sr     = _fmt(row["short_mean_pct"],    "{:.3f}%")
        ts     = _fmt(row["short_tstat"],       "{:.2f}")
        nd     = int(row["n_short_days"])
        flag   = " ✓" if (not np.isnan(row["short_tstat"]) and row["short_tstat"] > 2.0) else ""
        print(f"  {asset:<8} {sf:>8} {lr:>9} {sr:>10} {ts:>8} {nd:>7}  {flag}")


def print_distribution_analysis(
    variants: List[Tuple[str, List[SimResult]]],
) -> None:
    print("\nDAILY P&L DISTRIBUTION ANALYSIS:")
    print(f"  {'Variant':16s} {'Mean%':>7} {'Std%':>6} {'Skew':>6} "
          f"{'P5%':>6} {'P1%':>6} {'<-3%':>6} {'|>3|%':>6}")
    print(f"  {'-'*62}")
    for label, results in variants:
        d = analyze_daily_distribution(results)
        if not d:
            continue
        print(
            f"  {label:16s} "
            f"{d['mean']:>6.3f}% "
            f"{d['std']:>5.2f}% "
            f"{d['skew']:>5.2f}  "
            f"{d['p5']:>5.2f}% "
            f"{d['p1']:>5.2f}% "
            f"{d['pct_breach_3']:>5.1f}% "
            f"{d['pct_abs_gt3']:>5.1f}%"
        )


def print_correlation_analysis(
    ls_variants: List[Tuple[str, List[SimResult]]],
) -> None:
    print("\nLONG/SHORT LEG CORRELATION:")
    for label, results in ls_variants:
        corr = analyze_leg_correlation(results)
        if np.isnan(corr):
            interp = "insufficient data"
        elif corr < -0.3:
            interp = "real diversification — shorts reduce portfolio risk"
        elif corr > 0.3:
            interp = "noise — shorts add correlated exposure"
        else:
            interp = "neutral — modest correlation"
        print(f"  {label:18s}: corr = {corr:+.3f}  → {interp}")


def print_verdict(
    variants: List[Tuple[str, List[SimResult]]],
    short_edge_df: pd.DataFrame,
) -> str:
    """Print full verdict section. Returns best variant key (V1/V2/V3/V4)."""
    pass_rates  = {
        lbl.split(" ")[0]: sum(1 for r in res if r.outcome == "PASS") / len(res)
        for lbl, res in variants
    }
    best_key    = max(pass_rates, key=lambda k: pass_rates[k])
    best_pr     = pass_rates[best_key] * 100
    v2_pr       = pass_rates.get("V2", 0) * 100

    # Assess short edge
    sig_assets: List[str] = []
    for _, row in short_edge_df.iterrows():
        if not np.isnan(row["short_tstat"]) and row["short_tstat"] > 2.0:
            sig_assets.append(str(row["asset"]))

    if len(sig_assets) >= 2:
        short_verdict = f"YES — t > 2.0 on {len(sig_assets)} assets: {', '.join(sig_assets)}"
        recommendation = "Add short positions to live strategy (V4 recommended: half-size shorts)"
    elif len(sig_assets) == 1:
        short_verdict = f"MAYBE — only {sig_assets[0]} shows significant short edge (t > 2.0)"
        recommendation = "Test live on that asset only with small size; keep others long-only"
    else:
        short_verdict = "NO — short signal shows no consistent edge across assets"
        recommendation = "Keep long-only; short positions add risk without proportional return"

    delta = best_pr - v2_pr
    if delta > 5:
        decision_review = (
            f"WRONG — {best_key} ({best_pr:.0f}%) significantly outperforms "
            f"V2 ({v2_pr:.0f}%) by {delta:.0f}pp → reconsider long-only decision"
        )
    elif delta > 2:
        decision_review = (
            f"MARGINAL — {best_key} ({best_pr:.0f}%) slightly edges V2 ({v2_pr:.0f}%) "
            f"by {delta:.0f}pp → marginal benefit from shorts"
        )
    elif delta > -5:
        decision_review = (
            f"CONFIRMED — V2 ({v2_pr:.0f}%) and {best_key} ({best_pr:.0f}%) "
            f"perform comparably → long-only was correct"
        )
    else:
        decision_review = (
            f"STRONGLY CONFIRMED — V2 ({v2_pr:.0f}%) outperforms {best_key} "
            f"({best_pr:.0f}%) by {abs(delta):.0f}pp → long-only clearly superior"
        )

    print()
    print("WHY WE WENT LONG-ONLY (original v1 cross-sectional test):")
    print("  Long leg:  +105%    Short leg: −107%    Net: −1%")
    print("  That was CROSS-SECTIONAL momentum (short the WORST performers).")
    print("  TSMOM shorts are DIFFERENT: short only when OWN 28-day return < 0.")
    print(f"  Original decision review: {decision_review}")

    print()
    print(f"SHORT SIGNAL VERDICT: {short_verdict}")

    descriptions = {
        "V1": "3-asset L/S (original TSMOM style, 3 assets)",
        "V2": "11-asset long-only (current live strategy)",
        "V3": "11-asset full L/S (same vol target for long and short)",
        "V4": "11-asset long at 15% vol + cautious short at 7.5% vol",
    }

    print()
    print("VERDICT:")
    print(f"  Best variant for Propr Starter: {best_key}")
    print(f"  Description: {descriptions.get(best_key, best_key)}")
    print(f"  Pass rate:   {best_pr:.0f}%  |  Expected fee/pass: ${ENTRY_FEE / (best_pr/100):.0f}")
    print()
    print(f"  Should we add shorts to the live strategy?")
    print(f"  {short_verdict}")
    print(f"  Recommendation: {recommendation}")

    return best_key


# ── plotting ──────────────────────────────────────────────────────────────────

def save_plots(
    variants: List[Tuple[str, List[SimResult]]],
    short_edge_df: pd.DataFrame,
) -> None:
    """
    4-subplot figure:
    (1) Pass rate grouped bar chart
    (2) Daily P&L distribution (4 variants overlaid)
    (3) Short position returns by asset
    (4) Equity curve examples (one PASS + one FAIL per variant)
    """
    fig = plt.figure(figsize=(18, 14))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.35)

    vkeys  = ["V1", "V2", "V3", "V4"]
    clrs   = [COLORS[k] for k in vkeys]

    # ── (1) Pass rate bar chart ─────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])

    x = np.arange(len(variants))
    w = 0.26
    pass_pcts   = [sum(1 for r in res if r.outcome == "PASS") / len(res) * 100 for _, res in variants]
    daily_pcts  = [sum(1 for r in res if r.outcome == "FAIL_DAILY") / len(res) * 100 for _, res in variants]
    total_pcts  = [sum(1 for r in res if r.outcome == "FAIL_TOTAL") / len(res) * 100 for _, res in variants]

    b1 = ax1.bar(x - w,     pass_pcts,  w, label="PASS",          color="#4CAF50", alpha=0.88, edgecolor="black", linewidth=0.4)
    b2 = ax1.bar(x,         daily_pcts, w, label="Fail daily DD",  color="#FF9800", alpha=0.88, edgecolor="black", linewidth=0.4)
    b3 = ax1.bar(x + w,     total_pcts, w, label="Fail total DD",  color="#F44336", alpha=0.88, edgecolor="black", linewidth=0.4)

    for bar, pct in zip(b1, pass_pcts):
        ax1.text(bar.get_x() + bar.get_width() / 2, pct + 0.8,
                 f"{pct:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels([lbl for lbl, _ in variants], fontsize=9)
    ax1.set_ylabel("% of 44 simulations")
    ax1.set_title("Pass / Fail Rates by Variant", fontweight="bold", fontsize=11)
    ax1.legend(fontsize=8, loc="upper right")
    ax1.set_ylim(0, 115)
    ax1.grid(axis="y", alpha=0.3)

    # ── (2) Daily P&L distribution ─────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])

    for (lbl, results), clr in zip(variants, clrs):
        pcts: List[float] = []
        for r in results:
            for i, pnl in enumerate(r.daily_pnl):
                eq = r.equity_curve[i] if i < len(r.equity_curve) else PROPR_INITIAL
                if eq > 0:
                    pcts.append(pnl / eq * 100)
        if pcts:
            ax2.hist(np.array(pcts), bins=80, density=True,
                     alpha=0.38, color=clr, label=lbl, range=(-15, 15))

    ax2.axvline(-3, color="red", linestyle="--", alpha=0.8, linewidth=1.8, label="−3% daily limit")
    ax2.axvline(0,  color="black", linestyle="-", alpha=0.25, linewidth=1)
    ax2.set_xlabel("Daily P&L (% of equity)")
    ax2.set_ylabel("Density")
    ax2.set_title("Daily P&L Distribution — All Variants", fontweight="bold", fontsize=11)
    ax2.set_xlim(-12, 12)
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    # ── (3) Short position returns by asset ─────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])

    if not short_edge_df.empty:
        sdf = short_edge_df[short_edge_df["n_short_days"] >= 5].copy()
        sdf = sdf.dropna(subset=["short_mean_pct"]).sort_values("short_mean_pct", ascending=False)
        if not sdf.empty:
            bar_clrs = ["#4CAF50" if v > 0 else "#F44336" for v in sdf["short_mean_pct"]]
            bars = ax3.bar(
                range(len(sdf)), sdf["short_mean_pct"],
                color=bar_clrs, alpha=0.85, edgecolor="black", linewidth=0.5,
            )
            # Annotate with t-stat
            for i, (_, row) in enumerate(sdf.iterrows()):
                ts = row["short_tstat"]
                if not np.isnan(ts):
                    flag = "✓" if ts > 2.0 else ""
                    ax3.text(i, row["short_mean_pct"] + (0.002 if row["short_mean_pct"] >= 0 else -0.004),
                             f"t={ts:.1f}{flag}", ha="center", va="bottom" if row["short_mean_pct"] >= 0 else "top",
                             fontsize=7.5)
            ax3.axhline(0, color="black", linewidth=1)
            ax3.set_xticks(range(len(sdf)))
            ax3.set_xticklabels(sdf["asset"], rotation=30, ha="right", fontsize=9)
            ax3.set_ylabel("Avg daily return when short (%)")
            ax3.set_title("Short Position Returns by Asset\n(positive = short earned money)",
                          fontweight="bold", fontsize=11)
            ax3.grid(axis="y", alpha=0.3)
    else:
        ax3.text(0.5, 0.5, "No short data", ha="center", va="center",
                 transform=ax3.transAxes, fontsize=12)
        ax3.set_title("Short Position Returns by Asset", fontweight="bold", fontsize=11)

    # ── (4) Equity curve examples ───────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])

    for (lbl, results), clr in zip(variants, clrs):
        pass_ex = next((r for r in results if r.outcome == "PASS"), None)
        fail_ex = next(
            (r for r in results if r.outcome in ("FAIL_DAILY", "FAIL_TOTAL")), None
        )
        if pass_ex and pass_ex.equity_curve:
            ax4.plot(pass_ex.equity_curve, color=clr, linewidth=1.8, alpha=0.85,
                     label=f"{lbl} PASS")
        if fail_ex and fail_ex.equity_curve:
            ax4.plot(fail_ex.equity_curve, color=clr, linewidth=1.0, alpha=0.42,
                     linestyle="--", label=f"{lbl} FAIL")

    ax4.axhline(PROPR_TARGET,                        color="#388E3C", linewidth=1.8,
                linestyle="-", alpha=0.75, label=f"Target ${PROPR_TARGET:,.0f}")
    ax4.axhline(PROPR_INITIAL * (1 - PROPR_TOTAL_DD), color="#D32F2F", linewidth=1.8,
                linestyle="-", alpha=0.75, label="Total DD floor $4,700")
    ax4.set_xlabel("Trading days")
    ax4.set_ylabel("Equity ($)")
    ax4.set_title("Sample Equity Curves (one PASS + one FAIL per variant)",
                  fontweight="bold", fontsize=11)
    ax4.legend(fontsize=7, ncol=2, loc="upper left")
    ax4.grid(alpha=0.3)
    ax4.set_ylim(4400, 5900)

    fig.suptitle(
        "TSMOM Variants Comparison — Propr Starter Challenge\n"
        "V1: 3-asset L/S  ·  V2: 11-asset Long-only (live)  ·  "
        "V3: 11-asset L/S  ·  V4: 11-asset Long + Half-short",
        fontsize=12, fontweight="bold", y=0.98,
    )

    out_path = OUT_DIR / "v1_v2_comparison.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nChart saved: {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("TSMOM Variants Comparison: V1 vs V2 vs Long/Short on Propr")
    print(f"44 simulations  ·  {SIM_DATES[0].date()} to {SIM_DATES[-1].date()}")
    print("=" * 70)

    # ── 1. Data ─────────────────────────────────────────────────────────────
    print("\nDownloading prices...")
    all_assets = list(dict.fromkeys(ASSETS_V1 + ASSETS_FULL))
    prices     = load_prices(all_assets)
    available  = [a for a in all_assets if a in prices.columns]
    print(f"  Assets loaded : {[a.replace('-USD','') for a in available]}")
    print(f"  Date range    : {prices.index[0].date()} → {prices.index[-1].date()}")
    print(f"  Trading days  : {len(prices)}")

    assets_v1   = [a for a in ASSETS_V1   if a in available]
    assets_full = [a for a in ASSETS_FULL if a in available]

    # ── 2. Signals & vol ────────────────────────────────────────────────────
    signals_df, vol_scalars_df = compute_signals_and_vol(prices)

    # Signal frequency (for context)
    print("\nSignal statistics (fraction of days signal = -1):")
    for a in assets_full:
        if a in signals_df.columns:
            sf = (signals_df[a] == -1).mean() * 100
            print(f"  {a.replace('-USD',''):<8}: {sf:.1f}% short signal")

    # ── 3. Run simulations ──────────────────────────────────────────────────
    print("\nRunning 4 × 44 simulations...")
    v1_label, v1_res = run_variant(
        "V1 (3A L/S)", assets_v1, prices, signals_df, vol_scalars_df,
        long_only=False, short_vol_target=None,
    )
    v2_label, v2_res = run_variant(
        "V2 (11A Long)", assets_full, prices, signals_df, vol_scalars_df,
        long_only=True, short_vol_target=None,
    )
    v3_label, v3_res = run_variant(
        "V3 (11A L/S)", assets_full, prices, signals_df, vol_scalars_df,
        long_only=False, short_vol_target=None,
    )
    v4_label, v4_res = run_variant(
        "V4 (11A L/hS)", assets_full, prices, signals_df, vol_scalars_df,
        long_only=False, short_vol_target=VOL_TARGET_SHORT,
    )

    all_variants = [
        (v1_label, v1_res),
        (v2_label, v2_res),
        (v3_label, v3_res),
        (v4_label, v4_res),
    ]

    # ── 4. Comparison table ─────────────────────────────────────────────────
    print_comparison_table(all_variants)

    # ── 5. Short signal edge ────────────────────────────────────────────────
    print("\nAnalyzing short signal edge...")
    edge_v1 = analyze_short_edge(v1_res, assets_v1,   signals_df)
    edge_v3 = analyze_short_edge(v3_res, assets_full, signals_df)
    edge_v4 = analyze_short_edge(v4_res, assets_full, signals_df)

    print_short_edge(v1_label, edge_v1)
    print_short_edge(v3_label, edge_v3)

    # ── 6. Daily distribution ───────────────────────────────────────────────
    print_distribution_analysis(all_variants)

    # ── 7. Leg correlation ──────────────────────────────────────────────────
    ls_variants = [(v1_label, v1_res), (v3_label, v3_res), (v4_label, v4_res)]
    print_correlation_analysis(ls_variants)

    # ── 8. Calendar analysis (best variant) ────────────────────────────────
    pass_rates_map = {
        "V1": sum(1 for r in v1_res if r.outcome == "PASS") / len(v1_res),
        "V2": sum(1 for r in v2_res if r.outcome == "PASS") / len(v2_res),
        "V3": sum(1 for r in v3_res if r.outcome == "PASS") / len(v3_res),
        "V4": sum(1 for r in v4_res if r.outcome == "PASS") / len(v4_res),
    }
    best_key = max(pass_rates_map, key=lambda k: pass_rates_map[k])
    best_res_map = {"V1": v1_res, "V2": v2_res, "V3": v3_res, "V4": v4_res}
    best_lbl_map = {"V1": v1_label, "V2": v2_label, "V3": v3_label, "V4": v4_label}
    best_lbl = best_lbl_map[best_key]
    best_res = best_res_map[best_key]

    print(f"\nCALENDAR ANALYSIS — {best_lbl} (best variant):")
    cal = calendar_analysis(best_res)
    print(f"  {'Month':>10} {'Pass':>5} {'Tot':>5} {'Rate':>6}  Chart")
    for _, row in cal.iterrows():
        bar = "█" * int(row["pass_rate"] / 10)
        print(f"  {row['month_name']:>10}  {int(row['passes']):>4}  {int(row['total']):>4}  "
              f"{row['pass_rate']:>5.0f}%  {bar}")

    # ── 9. Verdict ──────────────────────────────────────────────────────────
    # Use V3 edge data for verdict (largest sample of short positions)
    best_variant_key = print_verdict(all_variants, edge_v3)

    # ── 10. Plots ────────────────────────────────────────────────────────────
    print("\nGenerating plots...")
    save_plots(all_variants, edge_v3)

    print("\nDone.")


if __name__ == "__main__":
    main()
