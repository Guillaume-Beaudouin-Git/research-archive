#!/usr/bin/env python3
"""
Crypto/research/passed/vpt_cmf/feasibility.py

VPT + CMF Volume Signals — Signals 40–41
=========================================
Fixes the key OBV failure (corr=0.98 with TSMOM at daily): OBV uses only
sign(ΔClose), making it a pure price-direction proxy.

Two signals that incorporate intracandle structure:

SIGNAL A — Volume Price Trend (VPT):
  Weights volume by MAGNITUDE of price change.
  A 5% up day with 2M volume counts 50× more than a 0.1% up day.
  VPT[T] = cumsum(Volume × pct_change)
  vpt_signal = tanh((VPT[T-1] - VPT_MA20[T-1]) / VPT_std20[T-1])

SIGNAL B — Chaikin Money Flow (CMF):
  Uses High + Low: where price closed within the candle.
  Close near high = bulls won. Close near low = bears won.
  MFV[T] = Volume × (2×Close - Low - High) / (High - Low + 1e-8)
  CMF[T] = sum(MFV[T-20:T]) / sum(Volume[T-20:T])
  cmf_signal = clip(CMF[T-1], 0, 1)

Assets : BTC ETH SOL AVAX LINK DOGE ADA (7 assets)
Period : 2018-01-01 → 2026-05-14
OOS    : 2022-01-01 → 2026-05-14
Cost   : 0.17% RT, weekly rebalance Monday
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
COST_RT      = 0.0017
COST_OW      = COST_RT / 2
TRADING_DAYS = 365

CMF_WINDOW   = 20
VPT_MA_WIN   = 20
TSMOM_LB     = 28
FWD_DAYS     = 5

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print(f"Downloading 7 assets OHLCV ({DATA_START} → {DATA_END})...")
    raw = yf.download(
        UNIVERSE, start=DATA_START, end=DATA_END,
        auto_adjust=True, progress=False, interval="1d",
    )

    def _ex(field: str) -> pd.DataFrame:
        df = raw[field].copy() if isinstance(raw.columns, pd.MultiIndex) else raw[[field]].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df = df.ffill(limit=2)
        df.columns = [c.replace("-USD", "") for c in df.columns]
        return df

    close  = _ex("Close")
    high   = _ex("High")
    low    = _ex("Low")
    volume = _ex("Volume")
    print(f"  {close.index[0].date()} → {close.index[-1].date()} "
          f"({len(close)} days)  assets: {sorted(close.columns.tolist())}")
    return close, high, low, volume


# ── Signal A: Volume Price Trend (VPT) ────────────────────────────────────────

def compute_vpt_signal(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """
    VPT[T] = cumsum(Volume[T] × pct_change[T])
           weights volume by MAGNITUDE of price change (not just sign)

    vpt_signal[T] = tanh((VPT[T-1] - VPT_MA20[T-1]) / VPT_std20[T-1])
    Long-only: clip(vpt_signal, 0, 1)
    All components shifted 1 — no look-ahead.
    """
    pct_change = close.pct_change()
    vpt = (volume * pct_change).fillna(0.0).cumsum()

    # VPT relative to its 20-day MA and std — computed on lagged VPT
    vpt_ma   = vpt.rolling(VPT_MA_WIN).mean().shift(1)  # MA20[T-1]
    vpt_std  = vpt.rolling(VPT_MA_WIN).std().shift(1)   # std20[T-1]
    vpt_lag  = vpt.shift(1)                              # VPT[T-1]

    vpt_signal = np.tanh((vpt_lag - vpt_ma) / (vpt_std + 1e-8))
    return vpt_signal.clip(0.0, 1.0)


# ── Signal B: Chaikin Money Flow (CMF) ────────────────────────────────────────

def compute_cmf_signal(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    volume: pd.DataFrame,
) -> pd.DataFrame:
    """
    Money Flow Volume: positive when close near high (bulls won intraday),
    negative when close near low (bears won intraday).

    MFV[T]  = Volume[T] × (2×Close[T] - Low[T] - High[T]) / (High[T] - Low[T] + 1e-8)
    CMF[T]  = sum(MFV[T-20:T]) / sum(Volume[T-20:T])   — 20-day rolling
    signal  = clip(CMF[T-1], 0, 1)                       — shift 1, long-only
    """
    hl_range = (high - low).replace(0.0, np.nan)
    mfv = volume * (2.0 * close - low - high) / (hl_range + 1e-8)
    mfv = mfv.fillna(0.0)

    cmf = mfv.rolling(CMF_WINDOW).sum() / (volume.rolling(CMF_WINDOW).sum() + 1e-8)
    cmf_signal = cmf.shift(1).clip(0.0, 1.0)   # CMF[T-1], long-only
    return cmf_signal


# ── TSMOM v3 baseline ─────────────────────────────────────────────────────────

def compute_tsmom(close: pd.DataFrame) -> pd.DataFrame:
    lr     = np.log(close / close.shift(1))
    cumret = lr.rolling(TSMOM_LB).sum().shift(1)
    vol28  = lr.rolling(TSMOM_LB).std().shift(1)
    return np.tanh(cumret / (vol28 * np.sqrt(TSMOM_LB) + 1e-8)).clip(0.0, 1.0)


# ── Portfolio Backtest ─────────────────────────────────────────────────────────

def portfolio_backtest(
    close: pd.DataFrame,
    signal: pd.DataFrame,
    label: str = "",
) -> dict[str, Any]:
    """Vol-targeted equal-weight portfolio, weekly Monday rebalance, 0.17% RT cost."""
    assets  = close.columns.intersection(signal.columns)
    lr      = np.log(close[assets] / close[assets].shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    scalar  = (VOL_TARGET / ann_vol.replace(0.0, np.nan)).clip(0.1, 2.0)

    raw_pos = (signal[assets] * scalar).fillna(0.0)

    # Weekly rebalance: Monday only
    is_mon  = raw_pos.index.dayofweek == 0
    pos_wk  = raw_pos.copy()
    pos_wk[~is_mon] = np.nan
    pos_wk  = pos_wk.ffill().fillna(0.0) / len(assets)

    # Gross cap
    gross   = pos_wk.abs().sum(axis=1).replace(0.0, np.nan)
    pos_cap = pos_wk.mul((GROSS_CAP / gross).clip(upper=1.0).fillna(1.0), axis=0)

    # P&L
    held    = pos_cap.shift(1).fillna(0.0)
    gpnl    = (held * close[assets].pct_change()).sum(axis=1)
    is_mon_s = pd.Series(is_mon.astype(float), index=pos_cap.index)
    costs   = pos_cap.diff().abs().sum(axis=1) * COST_OW * is_mon_s
    net     = (gpnl - costs).dropna()

    sharpe  = float((net.mean() / net.std()) * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    eq      = (1 + net).cumprod()
    max_dd  = float(((eq - eq.cummax()) / eq.cummax()).min())
    ann_ret = float(net.mean() * TRADING_DAYS)
    pneg    = float(abs(net[net < 0].sum()))
    pf      = float(net[net > 0].sum()) / pneg if pneg > 0 else np.inf

    return dict(label=label, sharpe=sharpe, ann_return=ann_ret,
                max_dd=max_dd, profit_factor=pf, net_rets=net, equity=eq)


def sub_sharpe(net: pd.Series, s: str, e: str) -> float:
    sub = net.loc[s:e]
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
    if period:
        signal = signal.loc[period[0]:period[1]]
        close  = close.loc[period[0]:period[1]]
    fwd = close.pct_change(FWD_DAYS).shift(-FWD_DAYS)
    all_s, all_f = [], []
    for col in close.columns:
        if col not in signal.columns:
            continue
        s = signal[col].dropna()
        f = fwd[col].dropna()
        idx = s.index.intersection(f.index)
        if len(idx) > FWD_DAYS:
            idx = idx[:-FWD_DAYS]
        if len(idx) < 30:
            continue
        all_s.append(s.loc[idx].values)
        all_f.append(f.loc[idx].values)
    if not all_s:
        return dict(label=label, ic=float("nan"), t_stat=float("nan"), n=0)
    sv = np.concatenate(all_s)
    fv = np.concatenate(all_f)
    ic, _ = stats.spearmanr(sv, fv)
    n = len(sv)
    t_stat = ic * np.sqrt(n) / np.sqrt(max(1 - ic**2, 1e-10))
    return dict(label=label, ic=float(ic), t_stat=float(t_stat), n=n)


# ── Walk-Forward ───────────────────────────────────────────────────────────────

def walk_forward(close, sig, label):
    folds = [
        ("2020-01-01", "2020-12-31"),
        ("2021-01-01", "2021-12-31"),
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2026-05-14"),
    ]
    results = []
    for i, (s, e) in enumerate(folds, 1):
        bt = portfolio_backtest(close.loc[s:e], sig.loc[s:e], label=f"W{i}")
        results.append(dict(fold=i, sharpe=bt["sharpe"], max_dd=bt["max_dd"]))
        print(f"    W{i} ({s[:4]}): Sh={bt['sharpe']:+.2f}  DD={bt['max_dd']:.1%}")
    n_pos = sum(1 for r in results if r["sharpe"] > 0)
    print(f"    → {n_pos}/4 positive")
    return results


# ── Signal Correlation with TSMOM ─────────────────────────────────────────────

def signal_corr_tsmom(sig: pd.DataFrame, tsmom: pd.DataFrame) -> float:
    corr_vals = []
    for col in sig.columns:
        if col in tsmom.columns:
            mask = sig[col].notna() & tsmom[col].notna()
            if mask.sum() > 60:
                corr_vals.append(float(sig.loc[mask, col].corr(tsmom.loc[mask, col])))
    return float(np.mean(corr_vals)) if corr_vals else float("nan")


# ── Plot ───────────────────────────────────────────────────────────────────────

def plot_results(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    volume: pd.DataFrame,
    all_bts: dict,
    ic_by_period: dict,
    wf_all: dict,
    save_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle(
        "VPT + CMF Volume Signals — Signals 40–41\n"
        "OBV fix: magnitude-weighted (VPT) + intracandle position (CMF)",
        fontsize=13, fontweight="bold",
    )
    COL = {"VPT": "#2c3e50", "CMF": "#27ae60", "TSMOM v3": "#3498db"}

    # ── Panel 1: Equity Curves ────────────────────────────────────────────────
    ax = axes[0, 0]
    for label, bt in all_bts.items():
        eq = bt["equity"]
        ls = "--" if label == "TSMOM v3" else "-"
        lw = 1.5 if label == "TSMOM v3" else 2.0
        ax.plot(eq.index, eq.values, color=COL.get(label, "gray"),
                ls=ls, lw=lw, label=f"{label} (Sh={bt['sharpe']:.2f})")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.axvline(pd.Timestamp(OOS_START), color="red", lw=1.0, ls=":", alpha=0.8, label="OOS start 2022")
    ax.set_title("Panel 1 — Equity Curves (OOS: 2022–2026)", fontsize=10)
    ax.set_ylabel("Cumulative Return (base 1.0)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Panel 2: BTC VPT + CMF overlay on Price ───────────────────────────────
    ax = axes[0, 1]
    ax2 = ax.twinx()

    btc_c   = close["BTC"].loc["2020-01-01":]
    btc_vpt_raw = (volume[["BTC"]] * close[["BTC"]].pct_change()).fillna(0).cumsum()["BTC"].loc["2020-01-01":]
    hl_range = (high[["BTC"]] - low[["BTC"]]).replace(0, np.nan)
    mfv_btc = (volume[["BTC"]] * (2 * close[["BTC"]] - low[["BTC"]] - high[["BTC"]]) / (hl_range + 1e-8)).fillna(0)
    cmf_btc = (mfv_btc.rolling(CMF_WINDOW).sum() / (volume[["BTC"]].rolling(CMF_WINDOW).sum() + 1e-8))["BTC"].loc["2020-01-01":]

    def norm01(s):
        return (s - s.min()) / (s.max() - s.min() + 1e-8)

    ax.plot(btc_c.index, norm01(btc_c).values, color="#e67e22", lw=1.5, label="BTC Price (norm.)")
    ax2.plot(btc_vpt_raw.index, norm01(btc_vpt_raw).values, color="#2c3e50", lw=1.0, alpha=0.7, label="VPT (norm.)")
    ax2.plot(cmf_btc.index, cmf_btc.values, color="#27ae60", lw=1.0, alpha=0.7, linestyle="--", label="CMF (raw)")
    ax.set_title("Panel 2 — BTC: Price vs VPT (norm.) vs CMF (raw) — 2020–2026", fontsize=10)
    ax.set_ylabel("Price / VPT", color="#e67e22")
    ax2.set_ylabel("CMF [-1, +1]", color="#27ae60")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)

    # ── Panel 3: IC by signal and sub-period ──────────────────────────────────
    ax = axes[1, 0]
    period_labels = ["2018–2021", "2022", "2023+"]
    sig_names     = ["VPT", "CMF"]
    x = np.arange(len(period_labels))
    width = 0.35

    for i, sn in enumerate(sig_names):
        ics = [ic_by_period.get((sn, p), {}).get("ic", 0.0) or 0.0 for p in period_labels]
        ts  = [ic_by_period.get((sn, p), {}).get("t_stat", 0.0) or 0.0 for p in period_labels]
        offset = (i - 0.5) * width
        bars = ax.bar(x + offset, ics, width=width, color=COL.get(sn, "gray"), alpha=0.85, label=sn)
        for bar, t in zip(bars, ts):
            if abs(t) > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + np.sign(bar.get_height()) * 0.001,
                        f"t={t:.1f}", ha="center", va="bottom" if bar.get_height() >= 0 else "top",
                        fontsize=7)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(period_labels, fontsize=9)
    ax.set_ylabel("Pooled IC (Spearman rank corr)")
    ax.set_title("Panel 3 — IC by Signal and Sub-Period\n(★ t>2.0 · t>1.5)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    # ── Panel 4: Walk-Forward Sharpe ──────────────────────────────────────────
    ax = axes[1, 1]
    fold_lbls = ["W1\n2020", "W2\n2021", "W3\n2022", "W4\n2023+"]
    x = np.arange(4)
    width = 0.28

    for i, (sn, wf) in enumerate(wf_all.items()):
        sharpes = [r["sharpe"] for r in wf]
        offset  = (i - 0.5) * width
        ax.bar(x + offset, sharpes, width=width, color=COL.get(sn, "gray"), alpha=0.85, label=sn)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(fold_lbls, fontsize=9)
    ax.set_ylabel("OOS Sharpe")
    ax.set_title("Panel 4 — Walk-Forward OOS Sharpe (4 windows)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("VPT + CMF VOLUME SIGNALS — SIGNALS 40–41")
    print("OHLC-aware volume: magnitude-weighted (VPT) + candle position (CMF)")
    print("=" * 65)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    close, high, low, volume = download_data()

    # ── 2. Compute signals ────────────────────────────────────────────────────
    print("\nComputing signals...")
    sig_vpt   = compute_vpt_signal(close, volume)
    sig_cmf   = compute_cmf_signal(close, high, low, volume)
    sig_tsmom = compute_tsmom(close)

    sig_map = {"VPT": sig_vpt, "CMF": sig_cmf, "TSMOM v3": sig_tsmom}

    # ── 3. OOS backtests ──────────────────────────────────────────────────────
    print(f"\nOOS portfolio backtests ({OOS_START} → {DATA_END})...")
    close_oos = close.loc[OOS_START:]
    all_bts: dict[str, dict] = {}
    for label, sig in sig_map.items():
        bt = portfolio_backtest(close_oos, sig.loc[OOS_START:], label=label)
        all_bts[label] = bt
        pf_s = f"{bt['profit_factor']:.2f}" if not np.isinf(bt["profit_factor"]) else "∞"
        print(f"  {label:<12}: Sh={bt['sharpe']:+.2f}  MaxDD={bt['max_dd']:.1%}  PF={pf_s}")

    # Sub-period Sharpe
    print(f"\n  {'Signal':<12}  {'2022':>6}  {'2023+':>6}")
    for label, bt in all_bts.items():
        s22 = sub_sharpe(bt["net_rets"], "2022-01-01", "2022-12-31")
        s23 = sub_sharpe(bt["net_rets"], "2023-01-01", DATA_END)
        print(f"  {label:<12}  {s22:>+6.2f}  {s23:>+6.2f}")

    # ── 4. IC tests ────────────────────────────────────────────────────────────
    ic_periods = {
        "2018–2021": ("2018-01-01", "2021-12-31"),
        "2022":      ("2022-01-01", "2022-12-31"),
        "2023+":     ("2023-01-01", DATA_END),
    }
    ic_by_period: dict[tuple, dict] = {}
    print(f"\nIC tests (→ {FWD_DAYS}-day forward return):")
    print(f"  {'Signal':<8}  {'Period':<12}  {'IC':>7}  {'t-stat':>7}  {'n':>6}")
    print(f"  {'-'*8}  {'-'*12}  {'-'*7}  {'-'*7}  {'-'*6}")
    for sn, sig in {"VPT": sig_vpt, "CMF": sig_cmf}.items():
        for pname, period in ic_periods.items():
            res = ic_test(sig, close, sn, period=period)
            ic_by_period[(sn, pname)] = res
            flag = " ★" if res["t_stat"] > 2.0 else (" ·" if res["t_stat"] > 1.5 else "  ")
            print(f"  {sn:<8}  {pname:<12}  {res['ic']:>7.4f}  {res['t_stat']:>7.2f}  "
                  f"{res['n']:>6}{flag}")

    # Full-period IC
    ic_full = {}
    print(f"\n  Full-period:")
    for sn, sig in {"VPT": sig_vpt, "CMF": sig_cmf}.items():
        res = ic_test(sig, close, sn)
        ic_full[sn] = res
        flag = " ★" if res["t_stat"] > 2.0 else (" ·" if res["t_stat"] > 1.5 else "  ")
        print(f"    {sn:<8}: IC={res['ic']:.4f}  t={res['t_stat']:.2f}{flag}")

    # ── 5. Correlation with TSMOM v3 ──────────────────────────────────────────
    corr_vpt = signal_corr_tsmom(sig_vpt, sig_tsmom)
    corr_cmf = signal_corr_tsmom(sig_cmf, sig_tsmom)
    print(f"\nCorr(VPT, TSMOM v3): {corr_vpt:.3f}  "
          f"{'→ OBV problem fixed (<0.85)' if corr_vpt < 0.85 else '→ still too similar'}")
    print(f"Corr(CMF, TSMOM v3): {corr_cmf:.3f}  "
          f"{'→ genuine diversification (<0.85)' if corr_cmf < 0.85 else '→ still too similar'}")

    # ── 6. Walk-forward ────────────────────────────────────────────────────────
    print("\nWalk-forward validation (4 windows)...")
    wf_all: dict[str, list] = {}
    for label, sig in {"VPT": sig_vpt, "CMF": sig_cmf}.items():
        print(f"\n  [{label}]")
        wf_all[label] = walk_forward(close, sig, label)

    # ── 7. Results table ───────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print("RESULTS TABLE  (OOS 2022-2026, 7 assets)")
    print(f"{'─'*80}")
    print(f"  {'Signal':<12}  {'Sharpe':>6}  {'MaxDD':>7}  {'ProfFt':>7}  "
          f"{'Sub-2022':>9}  {'corr(TSMOM)':>12}")
    print(f"  {'-'*12}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*9}  {'-'*12}")

    corr_map = {"VPT": corr_vpt, "CMF": corr_cmf, "TSMOM v3": 1.0}
    for label, bt in all_bts.items():
        s22  = sub_sharpe(bt["net_rets"], "2022-01-01", "2022-12-31")
        s22s = f"{s22:+.2f}" if not np.isnan(s22) else "  n/a"
        pf   = bt["profit_factor"]
        pfs  = f"{pf:.2f}" if not np.isinf(pf) else "∞"
        c    = corr_map.get(label, float("nan"))
        cs   = f"{c:.3f}" if not np.isnan(c) else "  n/a"
        tag  = " ← baseline" if label == "TSMOM v3" else ""
        print(f"  {label:<12}  {bt['sharpe']:>6.2f}  {bt['max_dd']:>7.1%}  "
              f"{pfs:>7}  {s22s:>9}  {cs:>12}{tag}")
    print(f"{'═'*80}")

    # ── 8. Plot ────────────────────────────────────────────────────────────────
    plot_results(close, high, low, volume, all_bts, ic_by_period, wf_all,
                 OUT_DIR / "feasibility_results.png")

    # ── 9. Verdict ─────────────────────────────────────────────────────────────
    sh_vpt = all_bts["VPT"]["sharpe"]
    sh_cmf = all_bts["CMF"]["sharpe"]
    wf_vpt = sum(1 for r in wf_all["VPT"] if r["sharpe"] > 0)
    wf_cmf = sum(1 for r in wf_all["CMF"] if r["sharpe"] > 0)
    ic_vpt_t = ic_full["VPT"]["t_stat"]
    ic_cmf_t = ic_full["CMF"]["t_stat"]
    sub22_vpt = sub_sharpe(all_bts["VPT"]["net_rets"], "2022-01-01", "2022-12-31")
    sub22_cmf = sub_sharpe(all_bts["CMF"]["net_rets"], "2022-01-01", "2022-12-31")

    print(f"\n{'═'*65}")
    print("VERDICT — VPT + CMF Volume Signals 40–41")
    print(f"{'═'*65}")
    print(f"\n[VPT — Volume Price Trend]")
    print(f"  Sharpe={sh_vpt:+.2f}  WF={wf_vpt}/4  2022={sub22_vpt:+.2f}  "
          f"IC t={ic_vpt_t:.2f}  corr(TSMOM)={corr_vpt:.3f}")
    standalone_vpt = sh_vpt > 1.0 and corr_vpt < 0.50
    deploy_vpt = sh_vpt > 1.45 and wf_vpt >= 3 and sub22_vpt > 0 and corr_vpt < 0.85
    print(f"  → {'DEPLOY overlay' if deploy_vpt else ('STANDALONE candidate' if standalone_vpt else 'SKIP')}")

    print(f"\n[CMF — Chaikin Money Flow]")
    print(f"  Sharpe={sh_cmf:+.2f}  WF={wf_cmf}/4  2022={sub22_cmf:+.2f}  "
          f"IC t={ic_cmf_t:.2f}  corr(TSMOM)={corr_cmf:.3f}")
    standalone_cmf = sh_cmf > 1.0 and corr_cmf < 0.50
    deploy_cmf = sh_cmf > 1.45 and wf_cmf >= 3 and sub22_cmf > 0 and corr_cmf < 0.85
    print(f"  → {'DEPLOY overlay' if deploy_cmf else ('STANDALONE candidate' if standalone_cmf else 'SKIP')}")

    print(f"\n[Overall]")
    if not (deploy_vpt or deploy_cmf or standalone_vpt or standalone_cmf):
        print("  → SKIP BOTH — volume OHLC signals fail OOS Sharpe/2022/corr criteria.")
        print("  → Root cause TBD: OBV-class signals regime-conditional or corr too high.")
    else:
        print("  → PARTIAL GO — see individual verdicts above.")
    print(f"{'═'*65}")


if __name__ == "__main__":
    main()
