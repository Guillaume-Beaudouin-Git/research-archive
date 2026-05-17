#!/usr/bin/env python3
"""
Crypto/research/passed/obv_signal/feasibility.py

OBV Volume Signal Feasibility — Signals 37–39
==============================================
First volume-based alpha in 36-signal search.

Economic mechanism:
  Volume leads price. OBV (cumulative signed volume) measures buying vs
  selling pressure. Vo & Yost-Bremm (2018): OBV is 2nd most important
  feature in RF model achieving Sharpe 8.22 (15-min, after RSI).
  Finding Alphas (Tulchinsky): price-volume divergence alphas work because
  accumulation (OBV up, price flat) precedes rallies; distribution
  (OBV down, price up) signals smart-money exits.

Signals:
  1. OBV Momentum          — pure OBV trend, long-only
  2. Price-Volume Divergence — long when OBV stronger than price (accumulation)
  3. OBV × TSMOM           — OBV as size scaler on TSMOM (volume confirmation)

Assets : BTC ETH SOL AVAX LINK DOGE ADA (7, max yfinance history)
Period : 2018-01-01 → 2026-05-14
OOS    : 2022-01-01 → 2026-05-14  (train 2018-2021)
Cost   : 0.17% RT, weekly rebalance Monday
Baseline: TSMOM v3 OOS Sharpe 1.33
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

UNIVERSE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD",
    "LINK-USD", "DOGE-USD", "ADA-USD",
]

DATA_START   = "2018-01-01"
DATA_END     = "2026-05-14"
OOS_START    = "2022-01-01"

VOL_TARGET   = 0.15
VOL_WINDOW   = 20
GROSS_CAP    = 0.90
COST_RT      = 0.0017       # 0.17% round-trip
COST_OW      = COST_RT / 2  # per leg
TRADING_DAYS = 365

OBV_LB       = 14           # OBV momentum lookback
OBV_STD_WIN  = 20           # OBV normalization rolling window
TSMOM_LB     = 28           # TSMOM lookback
FWD_DAYS     = 5            # IC forward return window

TSMOM_BASELINE_SHARPE = 1.33

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download daily close + volume from yfinance for 7 assets."""
    print(f"Downloading {len(UNIVERSE)} assets ({DATA_START} → {DATA_END})...")
    raw = yf.download(
        UNIVERSE, start=DATA_START, end=DATA_END,
        auto_adjust=True, progress=False, interval="1d",
    )

    def _extract(field: str) -> pd.DataFrame:
        if isinstance(raw.columns, pd.MultiIndex):
            df = raw[field].copy()
        else:
            df = raw[[field]].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df = df.ffill(limit=2)
        df.columns = [c.replace("-USD", "") for c in df.columns]
        return df

    close  = _extract("Close")
    volume = _extract("Volume")
    print(f"  {close.index[0].date()} → {close.index[-1].date()} "
          f"({len(close)} days)  assets: {sorted(close.columns.tolist())}")
    return close, volume


# ── OBV Core ───────────────────────────────────────────────────────────────────

def compute_obv(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """
    OBV[T] = cumsum(volume[t] × sign(close[t] - close[t-1]))
    Positive = buying pressure dominant; falling = selling pressure.
    """
    direction = np.sign(close.diff())
    return (volume * direction).fillna(0.0).cumsum()


def compute_obv_mom(obv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    14-day OBV momentum, normalized by rolling std.
    Uses only past data — OBV[T-1] and OBV[T-15] — no look-ahead.

    Returns
    -------
    obv_mom : tanh-normalized (ranges −1 to +1)
    obv_ret : raw 14-day OBV rate-of-change
    """
    obv_lag1  = obv.shift(1)
    obv_lag15 = obv.shift(15)
    obv_ret   = (obv_lag1 - obv_lag15) / (obv_lag15.abs() + 1e-8)
    obv_std   = obv_ret.rolling(OBV_STD_WIN).std()
    obv_mom   = np.tanh(obv_ret / (obv_std + 1e-8))
    return obv_mom, obv_ret


# ── Signal 1: OBV Momentum ─────────────────────────────────────────────────────

def signal_obv_momentum(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """
    signal_obv[T] = tanh(obv_ret_14d[T] / rolling_std(obv_ret_14d, 20)[T])
    Long-only: clip(signal_obv, 0, 1)
    Positive = OBV trending up = buying pressure dominating.
    """
    obv = compute_obv(close, volume)
    obv_mom, _ = compute_obv_mom(obv)
    return obv_mom.clip(0.0, 1.0)


# ── Signal 2: Price-Volume Divergence ──────────────────────────────────────────

def signal_pv_divergence(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """
    price_mom_14d[T]  = tanh(cumret_14d[T] / (vol_14d[T] × sqrt(14)))
    obv_mom_14d[T]    = tanh(obv_ret_14d[T] / rolling_std(obv_ret_14d,20)[T])
    divergence[T]     = obv_mom - price_mom
    signal_div[T]     = clip(divergence, 0, 1)

    Positive divergence = OBV stronger than price = accumulation.
    Negative divergence = price stronger than OBV = distribution (go flat).
    """
    # Price 14-day momentum (shift 1 → no look-ahead)
    lr       = np.log(close / close.shift(1))
    cumret   = lr.rolling(OBV_LB).sum().shift(1)
    vol_14d  = lr.rolling(OBV_LB).std().shift(1)
    price_mom = np.tanh(cumret / (vol_14d * np.sqrt(OBV_LB) + 1e-8))

    # OBV momentum
    obv = compute_obv(close, volume)
    obv_mom, _ = compute_obv_mom(obv)

    divergence = obv_mom - price_mom
    return divergence.clip(0.0, 1.0)


# ── Signal 3: OBV × TSMOM ─────────────────────────────────────────────────────

def signal_obv_tsmom(
    close: pd.DataFrame, volume: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    tsmom[T]        = tanh(cumret_28d[T] / (vol_28d[T] × sqrt(28)))
    vol_confirm[T]  = 0.5 + 0.5 × tanh(obv_mom_14d[T] × 2)
                      ← ranges ~0.07 (OBV falling) to ~0.93 (OBV rising)
    combined[T]     = clip(tsmom × vol_confirm, 0, 1)
                      ← OBV acts as position SIZE SCALER on TSMOM

    Also returns pure TSMOM v3 long-only for baseline.
    """
    lr      = np.log(close / close.shift(1))
    cumret  = lr.rolling(TSMOM_LB).sum().shift(1)
    vol_28d = lr.rolling(TSMOM_LB).std().shift(1)
    tsmom   = np.tanh(cumret / (vol_28d * np.sqrt(TSMOM_LB) + 1e-8))

    obv = compute_obv(close, volume)
    obv_mom, _ = compute_obv_mom(obv)
    vol_confirm = 0.5 + 0.5 * np.tanh(obv_mom * 2.0)

    combined   = (tsmom * vol_confirm).clip(0.0, 1.0)
    tsmom_long = tsmom.clip(0.0, 1.0)
    return combined, tsmom_long


# ── Portfolio Backtest Engine ──────────────────────────────────────────────────

def portfolio_backtest(
    close: pd.DataFrame,
    signal: pd.DataFrame,
    label: str = "",
) -> dict[str, Any]:
    """
    Equal vol-weighted portfolio, 7 assets, gross cap 90%.
    Weekly rebalance Monday only; 0.17% RT cost on Monday changes.

    P&L[T] = weight[T-1] × arith_ret[T]     (weight[T-1] ← data through T-1)
    """
    assets  = close.columns.intersection(signal.columns)
    lr      = np.log(close[assets] / close[assets].shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    scalar  = (VOL_TARGET / ann_vol.replace(0.0, np.nan)).clip(0.1, 2.0)

    raw_pos = (signal[assets] * scalar).fillna(0.0)

    # Weekly rebalance: update only on Monday
    is_mon  = raw_pos.index.dayofweek == 0
    pos_wk  = raw_pos.copy()
    pos_wk[~is_mon] = np.nan
    pos_wk  = pos_wk.ffill().fillna(0.0)

    # Equal-weight across N assets (each already vol-targeted)
    n_assets = len(assets)
    pos_wk   = pos_wk / n_assets

    # Gross cap
    gross    = pos_wk.abs().sum(axis=1).replace(0.0, np.nan)
    scale    = (GROSS_CAP / gross).clip(upper=1.0).fillna(1.0)
    pos_cap  = pos_wk.mul(scale, axis=0).fillna(0.0)

    # P&L
    arith    = close[assets].pct_change()
    held     = pos_cap.shift(1).fillna(0.0)
    gpnl     = (held * arith).sum(axis=1)

    # Costs only on Monday rebalance
    is_mon_s = pd.Series(is_mon.astype(float), index=pos_cap.index)
    costs    = pos_cap.diff().abs().sum(axis=1) * COST_OW * is_mon_s
    net      = (gpnl - costs).dropna()

    ann_ret  = float(net.mean() * TRADING_DAYS)
    sharpe   = float((net.mean() / net.std()) * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    eq       = (1 + net).cumprod()
    max_dd   = float(((eq - eq.cummax()) / eq.cummax()).min())
    ppos     = float(net[net > 0].sum())
    pneg     = float(abs(net[net < 0].sum()))
    pf       = ppos / pneg if pneg > 0 else np.inf

    return dict(
        label=label, sharpe=sharpe, ann_return=ann_ret,
        max_dd=max_dd, profit_factor=pf, net_rets=net, equity=eq,
    )


def sub_sharpe(net: pd.Series, start: str, end: str) -> float:
    """Annualized Sharpe for a sub-period slice of net_rets."""
    sub = net.loc[start:end]
    if len(sub) < 20 or sub.std() == 0:
        return float("nan")
    return float((sub.mean() / sub.std()) * np.sqrt(TRADING_DAYS))


# ── IC Test ────────────────────────────────────────────────────────────────────

def ic_test(
    signal: pd.DataFrame,
    close: pd.DataFrame,
    label: str,
    period: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """
    Pooled cross-sectional IC: Spearman rank_corr(signal[T], fwd_ret[T:T+5])
    across all assets and dates in the given period.
    """
    if period:
        signal = signal.loc[period[0]:period[1]]
        close  = close.loc[period[0]:period[1]]

    # Forward FWD_DAYS return: at T, we get close[T+FWD_DAYS]/close[T] - 1
    fwd = close.pct_change(FWD_DAYS).shift(-FWD_DAYS)

    all_s: list[np.ndarray] = []
    all_f: list[np.ndarray] = []

    for col in close.columns:
        if col not in signal.columns:
            continue
        s   = signal[col].dropna()
        f   = fwd[col].dropna()
        idx = s.index.intersection(f.index)
        if len(idx) > FWD_DAYS:
            idx = idx[:-FWD_DAYS]  # drop rows with no forward data
        if len(idx) < 30:
            continue
        all_s.append(s.loc[idx].values)
        all_f.append(f.loc[idx].values)

    if not all_s:
        return dict(label=label, ic=float("nan"), t_stat=float("nan"))

    sv = np.concatenate(all_s)
    fv = np.concatenate(all_f)
    ic, _ = stats.spearmanr(sv, fv)
    n      = len(sv)
    denom  = np.sqrt(max(1 - ic ** 2, 1e-10))
    t_stat = ic * np.sqrt(n) / denom

    return dict(label=label, ic=float(ic), t_stat=float(t_stat), n=n)


# ── Walk-Forward Validation ────────────────────────────────────────────────────

def walk_forward(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    sig_fn,
    label: str,
) -> list[dict[str, Any]]:
    """
    4 expanding-window OOS folds — parameters are fixed (no fitting),
    so walk-forward tests consistency across time periods.
    OOS windows: 2020, 2021, 2022, 2023-2026.
    """
    folds = [
        ("2020-01-01", "2020-12-31"),
        ("2021-01-01", "2021-12-31"),
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2026-05-14"),
    ]

    # Compute signal on full dataset (cumulative OBV needs all history)
    sig = sig_fn(close, volume)
    if isinstance(sig, tuple):
        sig = sig[0]

    results = []
    for i, (s, e) in enumerate(folds, 1):
        bt = portfolio_backtest(close.loc[s:e], sig.loc[s:e], label=f"W{i}")
        results.append(dict(
            fold=i, oos_start=s, oos_end=e,
            sharpe=bt["sharpe"], max_dd=bt["max_dd"],
        ))
        year_lbl = s[:4] if s[:4] != "2023" else "2023+"
        print(f"    W{i} ({year_lbl}): Sh={bt['sharpe']:+.2f}  MaxDD={bt['max_dd']:.1%}")

    n_pos = sum(1 for r in results if r["sharpe"] > 0)
    print(f"    → {n_pos}/4 positive Sharpe")
    return results


# ── Plot ───────────────────────────────────────────────────────────────────────

def plot_results(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    all_bts: dict[str, dict],
    ic_by_period: dict[tuple, dict],
    wf_all: dict[str, list],
    save_path: Path,
) -> None:
    """
    4-panel figure:
    1. Equity curves: all 3 signals vs TSMOM v3 baseline
    2. OBV vs price for BTC (visual divergence)
    3. IC by signal and sub-period
    4. Walk-forward Sharpe comparison
    """
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle(
        "OBV Volume Signal Feasibility — Signals 37–39\n"
        "First volume-based alpha in 36-signal search",
        fontsize=13, fontweight="bold",
    )

    COL = {
        "OBV Momentum":  "#2c3e50",
        "PV Divergence": "#27ae60",
        "OBV×TSMOM":     "#8e44ad",
        "TSMOM v3":      "#3498db",
    }

    # ── Panel 1: Equity Curves ────────────────────────────────────────────────
    ax = axes[0, 0]
    for label, bt in all_bts.items():
        eq  = bt["equity"]
        lw  = 2.0 if label != "TSMOM v3" else 1.5
        ls  = "-" if label != "TSMOM v3" else "--"
        sh  = bt["sharpe"]
        ax.plot(eq.index, eq.values, color=COL.get(label, "gray"),
                lw=lw, ls=ls, label=f"{label} (Sh={sh:.2f})")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.axvline(pd.Timestamp(OOS_START), color="red", lw=1.0, ls=":",
               alpha=0.8, label="OOS start (2022)")
    ax.set_title("Panel 1 — Equity Curves (OOS: 2022–2026)", fontsize=10)
    ax.set_ylabel("Cumulative Return (base 1.0)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Panel 2: BTC Price vs OBV (normalized) ────────────────────────────────
    ax  = axes[0, 1]
    ax2 = ax.twinx()

    btc_c   = close["BTC"].loc["2020-01-01":]
    btc_obv = compute_obv(close[["BTC"]], volume[["BTC"]])["BTC"].loc["2020-01-01":]

    def norm01(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / (rng + 1e-8)

    ax.plot(btc_c.index, norm01(btc_c).values,
            color="#e67e22", lw=1.5, label="BTC Price (norm.)")
    ax2.plot(btc_obv.index, norm01(btc_obv).values,
             color="#2c3e50", lw=1.0, alpha=0.75, label="OBV (norm.)")
    ax.set_title("Panel 2 — BTC Price vs OBV (2020–2026, normalized)", fontsize=10)
    ax.set_ylabel("Price", color="#e67e22")
    ax2.set_ylabel("OBV", color="#2c3e50")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)

    # ── Panel 3: IC by signal and sub-period ──────────────────────────────────
    ax = axes[1, 0]
    period_labels = ["2018–2021", "2022", "2023+"]
    sig_names     = ["OBV Momentum", "PV Divergence", "OBV×TSMOM"]
    x = np.arange(len(period_labels))
    width = 0.26

    for i, sn in enumerate(sig_names):
        ics = []
        for pn in period_labels:
            res = ic_by_period.get((sn, pn), {})
            ics.append(res.get("ic", 0.0) if not np.isnan(res.get("ic", float("nan"))) else 0.0)
        offset = (i - 1) * width
        ax.bar(x + offset, ics, width=width, color=COL.get(sn, "gray"),
               alpha=0.85, label=sn)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(period_labels, fontsize=9)
    ax.set_ylabel("Pooled IC (Spearman rank corr)")
    ax.set_title("Panel 3 — IC by Signal and Sub-Period", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    # ── Panel 4: Walk-Forward Sharpe ──────────────────────────────────────────
    ax = axes[1, 1]
    fold_lbls = ["W1\n2020", "W2\n2021", "W3\n2022", "W4\n2023+"]
    x = np.arange(4)
    width = 0.26

    for i, (sn, wf) in enumerate(wf_all.items()):
        sharpes = [r["sharpe"] for r in wf]
        offset  = (i - 1) * width
        ax.bar(x + offset, sharpes, width=width, color=COL.get(sn, "gray"),
               alpha=0.85, label=sn)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(fold_lbls, fontsize=9)
    ax.set_ylabel("OOS Sharpe")
    ax.set_title("Panel 4 — Walk-Forward OOS Sharpe (4 windows)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("OBV VOLUME SIGNAL FEASIBILITY — SIGNALS 37–39")
    print("First volume-based alpha in 36-signal search")
    print("=" * 65)

    # ── 1. Data ──────────────────────────────────────────────────────────────
    close, volume = download_data()

    # ── 2. Compute signals (full period — OBV needs cumulative history) ───────
    print("\nComputing signals...")
    sig1            = signal_obv_momentum(close, volume)
    sig2            = signal_pv_divergence(close, volume)
    sig3, sig_tsmom = signal_obv_tsmom(close, volume)

    sig_map = {
        "OBV Momentum":  sig1,
        "PV Divergence": sig2,
        "OBV×TSMOM":     sig3,
        "TSMOM v3":      sig_tsmom,
    }

    # ── 3. OOS portfolio backtests ────────────────────────────────────────────
    print(f"\nOOS portfolio backtests ({OOS_START} → {DATA_END})...")
    close_oos = close.loc[OOS_START:]
    all_bts: dict[str, dict] = {}
    for label, sig in sig_map.items():
        bt = portfolio_backtest(close_oos, sig.loc[OOS_START:], label=label)
        all_bts[label] = bt
        pf_s = f"{bt['profit_factor']:.2f}" if not np.isinf(bt["profit_factor"]) else "∞"
        print(f"  {label:<22}: Sh={bt['sharpe']:+.2f}  MaxDD={bt['max_dd']:.1%}  PF={pf_s}")

    # ── 4. Sub-period Sharpe (from OOS net_rets) ──────────────────────────────
    SP = {
        "2022":   ("2022-01-01", "2022-12-31"),
        "2023+":  ("2023-01-01", DATA_END),
    }
    print(f"\nSub-period Sharpe:")
    print(f"  {'Signal':<22}  {'2022':>6}  {'2023+':>6}")
    for label, bt in all_bts.items():
        sh22  = sub_sharpe(bt["net_rets"], *SP["2022"])
        sh23  = sub_sharpe(bt["net_rets"], *SP["2023+"])
        s22   = f"{sh22:+.2f}" if not np.isnan(sh22) else "  n/a"
        s23   = f"{sh23:+.2f}" if not np.isnan(sh23) else "  n/a"
        print(f"  {label:<22}  {s22:>6}  {s23:>6}")

    # ── 5. IC tests by sub-period ────────────────────────────────────────────
    ic_periods = {
        "2018–2021": ("2018-01-01", "2021-12-31"),
        "2022":      ("2022-01-01", "2022-12-31"),
        "2023+":     ("2023-01-01", DATA_END),
    }
    ic_by_period: dict[tuple, dict] = {}
    print(f"\nIC tests (→ {FWD_DAYS}-day forward return):")
    print(f"  {'Signal':<22}  {'Period':<12}  {'IC':>7}  {'t-stat':>7}  {'n':>6}")
    print(f"  {'-'*22}  {'-'*12}  {'-'*7}  {'-'*7}  {'-'*6}")

    ic_test_sigs = {"OBV Momentum": sig1, "PV Divergence": sig2, "OBV×TSMOM": sig3}
    for sn, sig in ic_test_sigs.items():
        for pname, period in ic_periods.items():
            res = ic_test(sig, close, sn, period=period)
            ic_by_period[(sn, pname)] = res
            t_s   = res.get("t_stat", float("nan"))
            ic_s  = res.get("ic", float("nan"))
            n_s   = res.get("n", 0)
            flag  = " ★" if t_s > 2.0 else (" ·" if t_s > 1.5 else "  ")
            print(f"  {sn:<22}  {pname:<12}  {ic_s:>7.4f}  {t_s:>7.2f}  "
                  f"{n_s:>6}{flag}")

    # Also pooled full-period IC for verdict
    ic_full: dict[str, dict] = {}
    print(f"\n  Full-period pooled IC:")
    for sn, sig in ic_test_sigs.items():
        res = ic_test(sig, close, sn)
        ic_full[sn] = res
        flag = " ★" if res["t_stat"] > 2.0 else (" ·" if res["t_stat"] > 1.5 else "  ")
        print(f"    {sn:<22}: IC={res['ic']:.4f}  t={res['t_stat']:.2f}{flag}")

    # ── 6. Walk-forward (4 expanding windows) ─────────────────────────────────
    wf_fns = {
        "OBV Momentum":  signal_obv_momentum,
        "PV Divergence": signal_pv_divergence,
        "OBV×TSMOM":     signal_obv_tsmom,
    }
    wf_all: dict[str, list] = {}
    print("\nWalk-forward validation (4 windows):")
    for label, fn in wf_fns.items():
        print(f"\n  [{label}]")
        wf_all[label] = walk_forward(close, volume, fn, label)

    # ── 7. Signal 3 vs TSMOM v3 correlation ──────────────────────────────────
    corr_vals = []
    for col in close.columns:
        if col in sig3.columns and col in sig_tsmom.columns:
            mask = sig3[col].notna() & sig_tsmom[col].notna()
            if mask.sum() > 60:
                corr_vals.append(float(sig3.loc[mask, col].corr(sig_tsmom.loc[mask, col])))
    corr3 = float(np.mean(corr_vals)) if corr_vals else float("nan")
    add_info = "→ OBV adds new info" if corr3 < 0.85 else "→ too similar to TSMOM"
    print(f"\nCorr(Signal 3, TSMOM v3): {corr3:.3f}  {add_info}")

    # ── 8. Results table ──────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print("RESULTS TABLE  (OOS 2022-2026, 7 assets, weekly rebalance, cost 0.17% RT)")
    print(f"{'─'*80}")
    print(f"  {'Signal':<26}  {'Sharpe':>6}  {'MaxDD':>7}  {'ProfFt':>7}  {'Sub-2022':>9}")
    print(f"  {'-'*26}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*9}")
    for label, bt in all_bts.items():
        sub22 = sub_sharpe(bt["net_rets"], "2022-01-01", "2022-12-31")
        s22   = f"{sub22:+.2f}" if not np.isnan(sub22) else "  n/a"
        pf    = bt["profit_factor"]
        pf_s  = f"{pf:.2f}" if not np.isinf(pf) and not np.isnan(pf) else "∞"
        tag   = " ← baseline" if label == "TSMOM v3" else ""
        print(f"  {label:<26}  {bt['sharpe']:>6.2f}  {bt['max_dd']:>7.1%}  "
              f"{pf_s:>7}  {s22:>9}{tag}")
    print(f"{'═'*80}")

    # ── 9. Plot ───────────────────────────────────────────────────────────────
    plot_results(
        close, volume, all_bts, ic_by_period, wf_all,
        OUT_DIR / "feasibility_results.png",
    )

    # ── 10. Verdict ───────────────────────────────────────────────────────────
    sh3      = all_bts["OBV×TSMOM"]["sharpe"]
    wf3_pos  = sum(1 for r in wf_all["OBV×TSMOM"] if r["sharpe"] > 0)
    sub22_3  = sub_sharpe(all_bts["OBV×TSMOM"]["net_rets"], "2022-01-01", "2022-12-31")
    sh1      = all_bts["OBV Momentum"]["sharpe"]
    sh2      = all_bts["PV Divergence"]["sharpe"]
    ic1_t    = ic_full["OBV Momentum"]["t_stat"]
    ic2_t    = ic_full["PV Divergence"]["t_stat"]
    ic3_t    = ic_full["OBV×TSMOM"]["t_stat"]

    deploy_3     = sh3 > 1.45 and wf3_pos >= 3 and not np.isnan(sub22_3) and sub22_3 > 0
    standalone_1 = sh1 > 1.0 and corr3 < 0.50
    standalone_2 = sh2 > 1.0 and corr3 < 0.50

    print(f"\n{'═'*65}")
    print("VERDICT — OBV Volume Signals 37–39")
    print(f"{'═'*65}")

    print(f"\n[Signal 3: OBV×TSMOM — Deploy as TSMOM overlay?]")
    print(f"  OOS Sharpe  : {sh3:+.2f}   (need > 1.45)")
    print(f"  Walk-forward: {wf3_pos}/4   (need ≥ 3)")
    print(f"  2022 Sharpe : {sub22_3:+.2f}   (need > 0 for regime-agnostic)")
    print(f"  Corr(TSMOM) : {corr3:.3f}  (need < 0.85 for new info)")
    if deploy_3:
        print("  → DEPLOY as TSMOM overlay (replace signal in tsmom_strategy.py)")
        print("    Update README 6.12")
    else:
        missing = []
        if sh3 <= 1.45:       missing.append(f"Sh={sh3:.2f}≤1.45")
        if wf3_pos < 3:       missing.append(f"WF={wf3_pos}/4<3")
        if np.isnan(sub22_3) or sub22_3 <= 0:
                              missing.append(f"2022={sub22_3:+.2f}≤0")
        if corr3 >= 0.85:     missing.append(f"corr={corr3:.2f}≥0.85")
        print(f"  → SKIP deploy ({', '.join(missing)})")

    print(f"\n[Signal 1: OBV Momentum — Standalone Strategy C?]")
    print(f"  OOS Sharpe  : {sh1:+.2f}   (need > 1.0)")
    print(f"  IC t-stat   : {ic1_t:.2f}   (need > 1.5)")
    print(f"  Corr(TSMOM) : {corr3:.3f}  (need < 0.50 standalone)")
    print(f"  → {'STANDALONE Strategy C candidate' if standalone_1 else 'SKIP standalone'}")

    print(f"\n[Signal 2: PV Divergence — Standalone Strategy C?]")
    print(f"  OOS Sharpe  : {sh2:+.2f}   (need > 1.0)")
    print(f"  IC t-stat   : {ic2_t:.2f}   (need > 1.5)")
    print(f"  → {'STANDALONE Strategy C candidate' if standalone_2 else 'SKIP standalone'}")

    all_ic_t = [ic1_t, ic2_t, ic3_t]
    print(f"\n[Overall]")
    if all(t < 1.5 for t in all_ic_t):
        print(f"  ALL IC t-stats < 1.5 {[f'{t:.2f}' for t in all_ic_t]}")
        print("  → SKIP ALL — OBV at daily frequency adds noise, not alpha.")
        print("  → Volume signals not viable as primary alpha at daily/weekly timescale.")
        print("  → Signal 37–39: SKIP")
    elif deploy_3:
        print("  → PARTIAL GO: deploy Signal 3 as TSMOM overlay, skip standalone.")
    elif standalone_1 or standalone_2:
        print("  → PARTIAL GO: standalone candidate — run full OOS before committing.")
    else:
        print("  → SKIP ALL (IC + Sharpe criteria not met at daily frequency).")

    print(f"{'═'*65}")


if __name__ == "__main__":
    main()
