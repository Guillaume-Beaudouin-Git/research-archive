#!/usr/bin/env python3
"""
Crypto/research/passed/halving_cycle/feasibility.py

Bitcoin Halving Cycle Timing Signal — Signals 42–44
====================================================
Economic mechanism — SUPPLY SHOCK:
  Bitcoin halving reduces new block reward by 50% every ~4 years.
  This creates a structural supply shock: fewer new BTC per day.
  Historical pattern: BTC strong 6-18 months POST-halving (4 cycles observed).
  Unlike OBV/VPT, this signal is orthogonal to price — it's SUPPLY-based.

Halving dates:
  2012-11-28, 2016-07-09, 2020-05-11, 2024-04-19

Signals:
  V1 — Phase filter: long if 0.3 < years_since_halving < 1.5 (golden zone)
  V2 — Gaussian: continuous signal, peak at 9 months, FWHM ~6 months
  V3 — Halving × TSMOM: cycle phase multiplier on TSMOM direction

Asset : BTC only (ETH Merge is a different mechanism)
Period: 2014-09 → 2026-05 (2 full cycles visible: 2016 and 2020)
OOS   : 2024-04-19 → 2026-05 (last halving = genuine OOS)
Note  : n=4 halvings, n=2 full cycles — small sample, flag DSR

Cost  : 0.17% RT, weekly rebalance Monday, vol target 15%
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────

DATA_START = "2014-09-17"   # earliest BTC-USD on yfinance
DATA_END   = "2026-05-14"
OOS_START  = "2024-04-19"   # 4th halving date — strict OOS

# Hardcoded halving dates
HALVINGS = pd.to_datetime([
    "2012-11-28",
    "2016-07-09",
    "2020-05-11",
    "2024-04-19",
])

TSMOM_LB     = 28
VOL_TARGET   = 0.15
VOL_WINDOW   = 20
GROSS_CAP    = 0.90
COST_RT      = 0.0017
COST_OW      = COST_RT / 2
TRADING_DAYS = 365
FWD_DAYS     = 5

# V1 "golden zone" parameters
PHASE_LOW  = 0.3   # 3.6 months post-halving
PHASE_HIGH = 1.5   # 18 months post-halving

# V2 Gaussian parameters
GAUSS_MU    = 0.75  # peak at 9 months post-halving
GAUSS_SIGMA = 0.5   # FWHM ~6 months

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data() -> pd.Series:
    print(f"Downloading BTC-USD ({DATA_START} → {DATA_END})...")
    raw = yf.download(
        "BTC-USD", start=DATA_START, end=DATA_END,
        auto_adjust=True, progress=False, interval="1d",
    )
    if raw.index.tz is not None:
        raw.index = raw.index.tz_convert(None)
    close_raw = raw["Close"]
    # yfinance may return DataFrame (1 col) or Series depending on version
    if isinstance(close_raw, pd.DataFrame):
        close_raw = close_raw.iloc[:, 0]
    close = close_raw.ffill(limit=2)
    close = pd.Series(close.values, index=close.index, name="BTC")
    print(f"  {close.index[0].date()} → {close.index[-1].date()} ({len(close)} days)")
    return close


# ── Cycle Phase Computation ────────────────────────────────────────────────────

def compute_cycle_phase(dates: pd.DatetimeIndex) -> pd.Series:
    """
    For each date T, compute years since the most recent prior halving.
    List-based — avoid Series index-assignment bugs.
    Returns: pd.Series(index=dates, values=cycle_phase_in_years)
    """
    halvings_sorted = [pd.Timestamp(h) for h in sorted(HALVINGS)]
    phase_vals = []
    for t in dates:
        t_ts = pd.Timestamp(t)
        prior = [h for h in halvings_sorted if h <= t_ts]
        if not prior:
            phase_vals.append(float("nan"))
        else:
            last_h = prior[-1]      # already sorted, last is most recent
            phase_vals.append((t_ts - last_h).days / 365.25)
    return pd.Series(phase_vals, index=dates, dtype=float)


# ── Signals ────────────────────────────────────────────────────────────────────

def compute_signals(close: pd.Series) -> dict[str, pd.Series]:
    """
    Compute V1/V2/V3 signals. All use cycle_phase.shift(1) — no look-ahead.
    Also returns TSMOM v3 baseline.
    """
    # Cycle phase (shift 1 for no look-ahead)
    phase_raw   = compute_cycle_phase(close.index)
    phase       = phase_raw.shift(1)   # phase[T] uses data through T-1

    # ── V1: Phase filter (long 4-18 months post-halving) ──────────────────────
    v1 = ((phase > PHASE_LOW) & (phase < PHASE_HIGH)).astype(float)
    v1[phase.isna()] = 0.0

    # ── V2: Gaussian signal, peak at 9 months ─────────────────────────────────
    v2 = np.exp(-((phase - GAUSS_MU) / GAUSS_SIGMA) ** 2)
    v2 = v2.fillna(0.0)

    # ── TSMOM v3 ──────────────────────────────────────────────────────────────
    lr      = np.log(close / close.shift(1))
    cumret  = lr.rolling(TSMOM_LB).sum().shift(1)
    vol28   = lr.rolling(TSMOM_LB).std().shift(1)
    tsmom   = np.tanh(cumret / (vol28 * np.sqrt(TSMOM_LB) + 1e-8)).clip(0.0, 1.0)
    tsmom   = tsmom.fillna(0.0)

    # ── V3: TSMOM × halving multiplier ────────────────────────────────────────
    halving_mult = 0.5 + 0.5 * v2   # ranges 0.5 (off-cycle) to 1.0 (peak halving)
    v3 = (tsmom * halving_mult).clip(0.0, 1.0)

    return {
        "V1 (Phase filter)": v1,
        "V2 (Gaussian)":     v2,
        "V3 (TSMOM×cycle)":  v3,
        "TSMOM v3":          tsmom,
    }


# ── Single-Asset Backtest ──────────────────────────────────────────────────────

def single_asset_backtest(
    close: pd.Series,
    signal: pd.Series,
    label: str = "",
) -> dict[str, Any]:
    """BTC-only backtest: vol-targeted, weekly rebalance, 0.17% RT costs."""
    lr      = np.log(close / close.shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    scalar  = (VOL_TARGET / ann_vol.replace(0.0, np.nan)).clip(0.1, 2.0)

    raw_pos = (signal * scalar).fillna(0.0)

    # Weekly rebalance Monday only
    is_mon  = raw_pos.index.dayofweek == 0
    pos_wk  = raw_pos.copy()
    pos_wk[~is_mon] = np.nan
    pos_wk  = pos_wk.ffill().fillna(0.0)
    pos_wk  = pos_wk.clip(-GROSS_CAP, GROSS_CAP)  # single asset cap

    # P&L
    arith    = close.pct_change()
    held     = pos_wk.shift(1).fillna(0.0)
    gpnl     = held * arith
    is_mon_s = pd.Series(is_mon.astype(float), index=pos_wk.index)
    costs    = pos_wk.diff().abs() * COST_OW * is_mon_s
    net      = (gpnl - costs).dropna()

    ann_ret = float(net.mean() * TRADING_DAYS)
    sharpe  = float((net.mean() / net.std()) * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    eq      = (1 + net).cumprod()
    max_dd  = float(((eq - eq.cummax()) / eq.cummax()).min())
    calmar  = ann_ret / abs(max_dd) if max_dd < 0 else float("nan")
    pneg    = float(abs(net[net < 0].sum()))
    pf      = float(net[net > 0].sum()) / pneg if pneg > 0 else np.inf

    return dict(label=label, sharpe=sharpe, ann_return=ann_ret, max_dd=max_dd,
                calmar=calmar, profit_factor=pf, net_rets=net, equity=eq)


def sub_sharpe(net: pd.Series, s: str, e: str) -> float:
    sub = net.loc[s:e]
    if len(sub) < 20 or sub.std() == 0:
        return float("nan")
    return float((sub.mean() / sub.std()) * np.sqrt(TRADING_DAYS))


# ── Phase Bucket Analysis ──────────────────────────────────────────────────────

def phase_bucket_analysis(close: pd.Series) -> pd.DataFrame:
    """
    For each cycle phase bucket, compute BTC 5-day return statistics.
    Tests whether the pattern is consistent across 2016 and 2020 cycles.

    Buckets (years since halving):
      [0, 0.25), [0.25, 0.5), [0.5, 1.0), [1.0, 1.5), [1.5, 2.0), [2.0, ∞)
    """
    fwd_ret_5d = close.pct_change(FWD_DAYS).shift(-FWD_DAYS)
    phase_raw  = compute_cycle_phase(close.index)

    buckets = [
        ("0–3m",   0.00, 0.25),
        ("3–6m",   0.25, 0.50),
        ("6–12m",  0.50, 1.00),
        ("12–18m", 1.00, 1.50),
        ("18–24m", 1.50, 2.00),
        ("24m+",   2.00, 9.99),
    ]

    # Unconditional baseline (all dates)
    all_ret = fwd_ret_5d.dropna()

    idx = close.index
    in_c2 = pd.Series((idx >= "2016-07-09") & (idx < "2020-05-11"), index=idx)
    in_c3 = pd.Series((idx >= "2020-05-11") & (idx < "2024-04-19"), index=idx)

    rows = []
    for name, lo, hi in buckets:
        mask = (phase_raw >= lo) & (phase_raw < hi) & fwd_ret_5d.notna()

        # Use .values[mask.values] to avoid any pandas alignment issues
        rets_full_vals = fwd_ret_5d.values[mask.values.astype(bool)]
        if len(rets_full_vals) < 10:
            continue
        t_full, _ = stats.ttest_1samp(rets_full_vals, 0)

        mask_c2 = (mask & in_c2).values.astype(bool)
        mask_c3 = (mask & in_c3).values.astype(bool)
        rets_c2 = fwd_ret_5d.values[mask_c2]
        rets_c3 = fwd_ret_5d.values[mask_c3]

        mean_c2 = float(np.nanmean(rets_c2)) if len(rets_c2) > 5 else float("nan")
        mean_c3 = float(np.nanmean(rets_c3)) if len(rets_c3) > 5 else float("nan")

        rows.append(dict(
            bucket=name,
            n=int(len(rets_full_vals)),
            mean_ret=float(np.nanmean(rets_full_vals)),
            std_ret=float(np.nanstd(rets_full_vals)),
            t_stat=float(t_full),
            mean_c2=mean_c2,
            mean_c3=mean_c3,
            n_c2=int(len(rets_c2)),
            n_c3=int(len(rets_c3)),
        ))

    df = pd.DataFrame(rows)
    uncond_vals = fwd_ret_5d.dropna().values
    uncond_mean = float(np.mean(uncond_vals))
    uncond_t, _ = stats.ttest_1samp(uncond_vals, 0)
    uncond_t    = float(uncond_t)

    print(f"\n{'─'*80}")
    print("PHASE BUCKET ANALYSIS (5-day forward BTC returns by cycle phase)")
    print(f"{'─'*80}")
    print(f"  {'Bucket':<10}  {'n':>5}  {'Mean%':>7}  {'t-stat':>7}  "
          f"{'Cycle2 mean%':>13}  {'Cycle3 mean%':>13}  {'consistent?':>11}")
    print(f"  {'-'*10}  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*13}  {'-'*13}  {'-'*11}")
    for _, r in df.iterrows():
        c2s = f"{r['mean_c2']*100:>+8.3f}%" if not np.isnan(r["mean_c2"]) else "      n/a"
        c3s = f"{r['mean_c3']*100:>+8.3f}%" if not np.isnan(r["mean_c3"]) else "      n/a"
        flag  = " ★" if abs(r["t_stat"]) > 2.0 else ("  " if abs(r["t_stat"]) <= 1.5 else " ·")
        consistent = ("YES" if (not np.isnan(r["mean_c2"]) and not np.isnan(r["mean_c3"])
                                and np.sign(r["mean_c2"]) == np.sign(r["mean_c3"])) else "NO ")
        print(f"  {r['bucket']:<10}  {int(r['n']):>5}  "
              f"{r['mean_ret']*100:>+7.3f}%  {r['t_stat']:>7.2f}{flag}  "
              f"{c2s}  {c3s}  {consistent:>11}")
    print(f"  {'Unconditional':<10}  {len(all_ret):>5}  "
          f"{uncond_mean*100:>+7.3f}%  {uncond_t:>7.2f}  (baseline)")
    return df


# ── Signal Correlation with TSMOM ─────────────────────────────────────────────

def corr_with_tsmom(sig: pd.Series, tsmom: pd.Series) -> float:
    mask = sig.notna() & tsmom.notna()
    if mask.sum() < 60:
        return float("nan")
    return float(sig[mask].corr(tsmom[mask]))


# ── Walk-Forward ───────────────────────────────────────────────────────────────

def walk_forward(close: pd.Series, signals: dict[str, pd.Series]) -> dict[str, list]:
    """
    For halving signals, OOS windows are the halving cycle periods themselves:
    - Cycle 2 OOS: 2016-07-09 → 2020-05-11
    - Cycle 3 OOS: 2020-05-11 → 2024-04-19
    - Cycle 4 OOS: 2024-04-19 → 2026-05-14  (strict OOS, last halving)
    Also include pre-halving as W1 for reference.
    """
    folds = [
        ("W1 pre-2016",  "2014-09-17", "2016-07-08"),
        ("W2 2016-2020", "2016-07-09", "2020-05-10"),
        ("W3 2020-2024", "2020-05-11", "2024-04-18"),
        ("W4 2024-2026", "2024-04-19", "2026-05-14"),
    ]
    results: dict[str, list] = {lb: [] for lb in signals}
    for fold_name, s, e in folds:
        c_slice = close.loc[s:e]
        for label, sig in signals.items():
            sig_slice = sig.loc[s:e]
            if len(c_slice) < 60:
                results[label].append(dict(fold=fold_name, sharpe=float("nan"), max_dd=float("nan")))
                continue
            bt = single_asset_backtest(c_slice, sig_slice, label=fold_name)
            results[label].append(dict(fold=fold_name, sharpe=bt["sharpe"], max_dd=bt["max_dd"]))

    print("\nWalk-forward (halving cycle windows):")
    print(f"  {'Signal':<20}  {'pre-2016':>9}  {'2016-2020':>9}  {'2020-2024':>9}  {'2024-2026':>9}")
    for label, wf in results.items():
        sharpes = [f"{r['sharpe']:>+8.2f}" if not np.isnan(r["sharpe"]) else "     n/a " for r in wf]
        print(f"  {label:<20}  {'  '.join(sharpes)}")
    return results


# ── DSR Caveat ─────────────────────────────────────────────────────────────────

def dsr_caveat(sharpe_oos: float, n_tests: int, n_obs: int) -> dict[str, float]:
    """
    Deflated Sharpe Ratio (Bailey et al.).
    E[max SR] ≈ (1 - γ + γ/n_obs) × sqrt(2 log n_tests)   (Bailey 2014 simplified)
    DSR = SR / E[max SR]
    Note: conservative estimate; actual DSR lower if tests are correlated.
    """
    e_max_sr = (1 - 0.5772 + 0.5772 / n_obs) * np.sqrt(2 * np.log(n_tests))
    dsr      = sharpe_oos / e_max_sr if e_max_sr > 0 else float("nan")
    return dict(e_max_sr=e_max_sr, dsr=dsr, n_tests=n_tests)


# ── Plot ───────────────────────────────────────────────────────────────────────

def plot_results(
    close: pd.Series,
    signals: dict[str, pd.Series],
    all_bts: dict[str, dict],
    bucket_df: pd.DataFrame,
    save_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle(
        "Bitcoin Halving Cycle Timing Signal — Signals 42–44\n"
        "Supply-shock mechanism: 4 halvings, 2 full cycles visible",
        fontsize=13, fontweight="bold",
    )

    COL = {
        "V1 (Phase filter)": "#e74c3c",
        "V2 (Gaussian)":     "#8e44ad",
        "V3 (TSMOM×cycle)":  "#2c3e50",
        "TSMOM v3":          "#3498db",
    }

    # ── Panel 1: Equity Curves (full period) ──────────────────────────────────
    ax = axes[0, 0]
    for label, bt in all_bts.items():
        eq = bt["equity"]
        ls = "--" if label == "TSMOM v3" else "-"
        lw = 1.5 if label == "TSMOM v3" else 2.0
        ax.plot(eq.index, eq.values, color=COL.get(label, "gray"),
                ls=ls, lw=lw, label=f"{label} (Sh={bt['sharpe']:.2f})")

    # Mark halving dates
    for h in HALVINGS:
        if pd.Timestamp(DATA_START) <= h <= pd.Timestamp(DATA_END):
            ax.axvline(h, color="gold", lw=1.5, alpha=0.8)
    ax.axvline(pd.Timestamp(OOS_START), color="red", lw=1.0, ls=":", alpha=0.9,
               label="OOS (2024 halving)")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.set_title("Panel 1 — Equity Curves  (gold lines = halvings)", fontsize=10)
    ax.set_ylabel("Cumulative Return (base 1.0)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Panel 2: Cycle Phase Signal Over Time ─────────────────────────────────
    ax = axes[0, 1]
    phase_raw = compute_cycle_phase(close.index)
    # normalize price for overlay
    c_norm = (close - close.min()) / (close.max() - close.min())

    ax.plot(close.index, c_norm.values, color="#e67e22", lw=1.0, alpha=0.5, label="BTC price (norm.)")
    ax2 = ax.twinx()
    # V2 Gaussian signal
    sig_v2 = signals["V2 (Gaussian)"]
    ax2.fill_between(sig_v2.index, 0, sig_v2.values,
                     alpha=0.35, color="#8e44ad", label="V2 Gaussian signal")
    ax2.plot(sig_v2.index, sig_v2.values, color="#8e44ad", lw=1.0, alpha=0.7)

    for h in HALVINGS:
        if pd.Timestamp(DATA_START) <= h <= pd.Timestamp(DATA_END):
            ax.axvline(h, color="gold", lw=1.5, alpha=0.7)

    ax.set_title("Panel 2 — Halving Cycle Signal (V2 Gaussian) vs BTC Price", fontsize=10)
    ax.set_ylabel("BTC Price (normalized)", color="#e67e22")
    ax2.set_ylabel("V2 Signal [0–1]", color="#8e44ad")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)

    # ── Panel 3: Phase Bucket Mean Returns ────────────────────────────────────
    ax = axes[1, 0]
    bk_names  = bucket_df["bucket"].tolist()
    bk_means  = (bucket_df["mean_ret"] * 100).tolist()
    bk_c2     = (bucket_df["mean_c2"].fillna(0.0) * 100).tolist()
    bk_c3     = (bucket_df["mean_c3"].fillna(0.0) * 100).tolist()
    bk_tstats = bucket_df["t_stat"].tolist()
    x = np.arange(len(bk_names))
    w = 0.27

    ax.bar(x - w, bk_means, width=w, label="Full period", color="#34495e", alpha=0.85)
    ax.bar(x,     bk_c2,    width=w, label="Cycle 2 (2016-2020)", color="#e74c3c", alpha=0.85)
    ax.bar(x + w, bk_c3,    width=w, label="Cycle 3 (2020-2024)", color="#3498db", alpha=0.85)

    for i, (m, t) in enumerate(zip(bk_means, bk_tstats)):
        ax.text(i - w, m + np.sign(m) * 0.02, f"t={t:.1f}",
                ha="center", va="bottom" if m >= 0 else "top", fontsize=7)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(bk_names, fontsize=8)
    ax.set_ylabel("Mean 5-day return (%)")
    ax.set_title("Panel 3 — BTC 5d Returns by Cycle Phase\n(consistency across cycles = genuine pattern)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    # ── Panel 4: OOS period (2024-2026) equity curves ─────────────────────────
    ax = axes[1, 1]
    oos_start_ts = pd.Timestamp(OOS_START)
    for label, bt in all_bts.items():
        eq = bt["equity"]
        eq_oos = eq.loc[oos_start_ts:]
        if len(eq_oos) == 0:
            continue
        eq_oos = eq_oos / eq_oos.iloc[0]  # rebase at OOS start
        ls = "--" if label == "TSMOM v3" else "-"
        lw = 1.5 if label == "TSMOM v3" else 2.0
        sh_oos = sub_sharpe(bt["net_rets"], OOS_START, DATA_END)
        sh_str = f"{sh_oos:.2f}" if not np.isnan(sh_oos) else "n/a"
        ax.plot(eq_oos.index, eq_oos.values, color=COL.get(label, "gray"),
                ls=ls, lw=lw, label=f"{label} (Sh={sh_str})")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.set_title(f"Panel 4 — OOS Equity (2024-04-19 → 2026-05-14)\n"
                 f"4th halving cycle — currently at ~{(pd.Timestamp(DATA_END)-pd.Timestamp(OOS_START)).days/365.25:.1f}y",
                 fontsize=10)
    ax.set_ylabel("Cumulative Return (rebased at OOS start)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("BITCOIN HALVING CYCLE TIMING — SIGNALS 42–44")
    print("Supply-shock mechanism: n=4 halvings, n=2 full cycles visible")
    print("=" * 65)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    close = download_data()

    # ── 2. Phase bucket analysis ─────────────────────────────────────────────
    bucket_df = phase_bucket_analysis(close)

    # ── 3. Compute signals ────────────────────────────────────────────────────
    print("\nComputing signals...")
    signals = compute_signals(close)
    for label, sig in signals.items():
        print(f"  {label}: non-NaN={sig.notna().sum()}  mean={sig.dropna().mean():.3f}")

    # ── 4. Full-period backtests ───────────────────────────────────────────────
    print(f"\nFull-period backtests ({DATA_START} → {DATA_END})...")
    all_bts: dict[str, dict] = {}
    for label, sig in signals.items():
        bt = single_asset_backtest(close, sig, label=label)
        all_bts[label] = bt
        print(f"  {label:<22}: Sh={bt['sharpe']:+.2f}  MaxDD={bt['max_dd']:.1%}  "
              f"Calmar={bt['calmar']:+.2f}")

    # ── 5. OOS Sharpe (2024-04-19 onwards — strict OOS) ──────────────────────
    print(f"\nOOS period ({OOS_START} → {DATA_END}):")
    print(f"  {'Signal':<22}  {'Sharpe':>6}  {'MaxDD':>7}  {'Calmar':>7}")
    close_oos = close.loc[OOS_START:]
    oos_bts: dict[str, dict] = {}
    for label, sig in signals.items():
        bt_oos = single_asset_backtest(close_oos, sig.loc[OOS_START:], label=label)
        oos_bts[label] = bt_oos
        calmar_s = f"{bt_oos['calmar']:+.2f}" if not np.isnan(bt_oos["calmar"]) else "   n/a"
        print(f"  {label:<22}  {bt_oos['sharpe']:>+6.2f}  {bt_oos['max_dd']:>7.1%}  "
              f"{calmar_s:>7}")

    # ── 6. Correlation with TSMOM ─────────────────────────────────────────────
    tsmom = signals["TSMOM v3"]
    print(f"\nCorrelation with TSMOM v3:")
    for label, sig in signals.items():
        if label == "TSMOM v3":
            continue
        c = corr_with_tsmom(sig, tsmom)
        print(f"  {label:<22}: {c:+.3f}  "
              f"{'→ new info (<0.85)' if c < 0.85 else '→ too similar'}")

    # ── 7. Walk-forward (halving cycle windows) ───────────────────────────────
    wf_results = walk_forward(close, signals)

    # ── 8. DSR caveat ─────────────────────────────────────────────────────────
    sh_oos_v2 = oos_bts["V2 (Gaussian)"]["sharpe"]
    n_obs_oos = len(close_oos.dropna())
    dsr = dsr_caveat(sh_oos_v2, n_tests=40, n_obs=n_obs_oos)
    print(f"\nDSR caveat (n_tests=40, n=3 halvings × 3 variants × ~13 configs):")
    print(f"  E[max SR]  = {dsr['e_max_sr']:.2f}")
    print(f"  V2 OOS Sh  = {sh_oos_v2:+.2f}")
    print(f"  DSR        = {dsr['dsr']:.3f}  "
          f"{'(> 1.0 → stat-significant)' if dsr['dsr'] > 1.0 else '(< 1.0 → multiple-testing killed)'}")
    print(f"  ⚠ n=2 full cycles only — sample size severely limits inference.")

    # ── 9. Results table ───────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print("RESULTS TABLE  (BTC only, weekly rebalance, cost 0.17% RT)")
    print(f"{'─'*80}")
    print(f"  {'Signal':<22}  {'Full Sh':>7}  {'OOS Sh':>7}  {'MaxDD':>7}  {'Note'}")
    print(f"  {'-'*22}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*30}")
    notes = {
        "V1 (Phase filter)": "n=2 cycles only",
        "V2 (Gaussian)":     "n=2 cycles only",
        "V3 (TSMOM×cycle)":  "n=2 cycles only",
        "TSMOM v3":          "baseline",
    }
    for label, bt in all_bts.items():
        bt_oos = oos_bts[label]
        note   = notes.get(label, "")
        print(f"  {label:<22}  {bt['sharpe']:>+7.2f}  {bt_oos['sharpe']:>+7.2f}  "
              f"{bt['max_dd']:>7.1%}  {note}")
    print(f"{'═'*80}")

    # ── 10. Plot ──────────────────────────────────────────────────────────────
    plot_results(close, signals, all_bts, bucket_df,
                 OUT_DIR / "feasibility_results.png")

    # ── 11. Verdict ───────────────────────────────────────────────────────────
    sh_v1_oos = oos_bts["V1 (Phase filter)"]["sharpe"]
    sh_v2_oos = oos_bts["V2 (Gaussian)"]["sharpe"]
    sh_v3_oos = oos_bts["V3 (TSMOM×cycle)"]["sharpe"]
    sh_tm_oos = oos_bts["TSMOM v3"]["sharpe"]
    c_v1 = corr_with_tsmom(signals["V1 (Phase filter)"], tsmom)
    c_v2 = corr_with_tsmom(signals["V2 (Gaussian)"], tsmom)
    c_v3 = corr_with_tsmom(signals["V3 (TSMOM×cycle)"], tsmom)

    # Bucket consistency: is 6-12m (golden zone) positive in both cycles?
    golden_row = bucket_df[bucket_df["bucket"] == "6–12m"]
    golden_consistent = (
        not golden_row.empty
        and not np.isnan(golden_row["mean_c2"].values[0])
        and not np.isnan(golden_row["mean_c3"].values[0])
        and golden_row["mean_c2"].values[0] > 0
        and golden_row["mean_c3"].values[0] > 0
    )

    print(f"\n{'═'*65}")
    print("VERDICT — Halving Cycle Timing Signals 42–44")
    print(f"{'═'*65}")
    print(f"\n[V1 Phase Filter]  OOS Sh={sh_v1_oos:+.2f}  corr(TSMOM)={c_v1:+.3f}")
    print(f"[V2 Gaussian]      OOS Sh={sh_v2_oos:+.2f}  corr(TSMOM)={c_v2:+.3f}  "
          f"DSR={dsr['dsr']:.2f}")
    print(f"[V3 TSMOM×cycle]   OOS Sh={sh_v3_oos:+.2f}  corr(TSMOM)={c_v3:+.3f}")
    print(f"[TSMOM v3 base]    OOS Sh={sh_tm_oos:+.2f}")
    print(f"\nPhase bucket 6-12m consistent across both full cycles: "
          f"{'YES ✓' if golden_consistent else 'NO ✗'}")
    print(f"DSR < 1.0: {'MULTIPLE TESTING KILLS SIGNIFICANCE' if dsr['dsr'] < 1.0 else 'passes'}")
    print(f"Sample size warning: n=2 full cycles — pattern not statistically robust.")

    any_beat_tsmom = any(sh > sh_tm_oos for sh in [sh_v1_oos, sh_v2_oos, sh_v3_oos])
    deploy_any    = any_beat_tsmom and dsr["dsr"] > 1.0 and golden_consistent

    if deploy_any:
        best_v = max([
            ("V1", sh_v1_oos), ("V2", sh_v2_oos), ("V3", sh_v3_oos)
        ], key=lambda x: x[1])
        print(f"\n→ CONDITIONAL GO: {best_v[0]} beats TSMOM OOS (Sh={best_v[1]:.2f}). "
              f"But n=2 cycles is too small. Revisit after 2028 halving.")
    else:
        reasons = []
        if not any_beat_tsmom:
            reasons.append(f"no variant beats TSMOM OOS (best={max(sh_v1_oos,sh_v2_oos,sh_v3_oos):.2f} vs {sh_tm_oos:.2f})")
        if dsr["dsr"] < 1.0:
            reasons.append(f"DSR={dsr['dsr']:.2f} < 1.0 (n_tests too high for sample)")
        if not golden_consistent:
            reasons.append("6-12m bucket not consistent across both cycles")
        print(f"\n→ SKIP — {'; '.join(reasons)}")
        print("  Halving cycle may add value at n=3+ full cycles (2028+).")
        print("  Signal 42–44: SKIP")

    print(f"{'═'*65}")


if __name__ == "__main__":
    main()
