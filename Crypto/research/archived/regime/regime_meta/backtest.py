"""
Regime-Conditional Meta-Strategy — Full Backtest
=================================================
Train: 2020-06-01 → 2022-12-31  (HMM fitted here only)
Test:  2023-01-01 → 2026-05-14  (OOS, 3.5 years)

Routing:
  BULL_TREND → TSMOM long-only  (18% vol target, 14 assets)
  BEAR_TREND → TSMOM short-only (12% vol target, BTC/ETH/SOL)
  RANGE      → flat
  CRASH      → cash (immediate exit)

Usage:
  /usr/bin/python3 -m strategies.regime_meta.backtest
"""

import sys
import os
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
from typing import List, Tuple
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

from strategies.regime_meta.regime_detector import (
    detect_regimes, COLORS, validate_regime_timeline,
)
from strategies.regime_meta.strategy_router import (
    TSMOM_UNIVERSE, SHORT_ASSETS,
    build_raw_positions, route_positions, compute_pnl,
)

DATA_START = "2020-01-01"
DATA_END   = "2026-05-14"
TRAIN_END  = "2022-12-31"
TEST_START = "2023-01-01"
TRADING_DAYS = 365
OUT_DIR = os.path.dirname(__file__)


# ── Data ──────────────────────────────────────────────────────────────────────

def download_data() -> pd.DataFrame:
    print(f"Downloading {len(TSMOM_UNIVERSE)}-asset universe ({DATA_START} → {DATA_END})...")
    raw = yf.download(TSMOM_UNIVERSE, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.dropna(how="all")
    available = [c for c in raw.columns if raw[c].dropna().shape[0] > 200]
    raw = raw[available].ffill()
    print(f"  Available: {len(available)} assets  Range: {raw.index[0].date()} → {raw.index[-1].date()}")
    return raw


# ── Metrics ───────────────────────────────────────────────────────────────────

def sharpe(pnl: pd.Series) -> float:
    if pnl.std() == 0:
        return 0.0
    return pnl.mean() / pnl.std() * np.sqrt(TRADING_DAYS)


def max_drawdown(pnl: pd.Series) -> float:
    eq = (1 + pnl).cumprod()
    dd = eq / eq.cummax() - 1
    return float(dd.min())


def sortino(pnl: pd.Series) -> float:
    neg = pnl[pnl < 0]
    if neg.std() == 0:
        return 0.0
    return pnl.mean() / neg.std() * np.sqrt(TRADING_DAYS)


def calmar(pnl: pd.Series) -> float:
    ann_ret = (1 + pnl).prod() ** (TRADING_DAYS / len(pnl)) - 1
    mdd = abs(max_drawdown(pnl))
    return ann_ret / mdd if mdd > 0 else np.nan


def profit_factor(pnl: pd.Series) -> float:
    g = pnl[pnl > 0].sum()
    l = abs(pnl[pnl < 0].sum())
    return g / l if l > 0 else np.nan


def win_rate(pnl_weekly: pd.Series) -> float:
    return (pnl_weekly > 0).mean()


def max_consec_losing_weeks(pnl_weekly: pd.Series) -> int:
    streak = 0
    best = 0
    for r in pnl_weekly:
        if r < 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def metrics_dict(pnl: pd.Series, label: str) -> dict:
    pnl_w = pnl.resample("W-MON").sum()
    return {
        "label":        label,
        "sharpe":       sharpe(pnl),
        "sortino":      sortino(pnl),
        "max_dd":       max_drawdown(pnl),
        "calmar":       calmar(pnl),
        "pf":           profit_factor(pnl),
        "win_rate":     win_rate(pnl_w),
        "max_cl_weeks": max_consec_losing_weeks(pnl_w),
    }


# ── TSMOM baseline (no regime routing) ───────────────────────────────────────

def tsmom_baseline_pnl(close: pd.DataFrame) -> pd.Series:
    """Pure TSMOM v2 long-only for comparison."""
    assets = [a for a in TSMOM_UNIVERSE if a in close.columns]
    log_ret = np.log(close[assets] / close[assets].shift(1)).clip(-1.0, 1.0)
    mom28   = log_ret.rolling(28).sum()
    signal  = np.sign(mom28).clip(lower=0)

    vol20   = log_ret.rolling(20).std() * np.sqrt(TRADING_DAYS)
    vol20   = vol20.replace(0, np.nan).ffill().fillna(0.18)
    scalar  = (0.18 / vol20).clip(0.1, 2.0)

    raw_pos = signal * scalar
    is_mon  = raw_pos.index.dayofweek == 0
    locked  = raw_pos.copy()
    locked[~is_mon] = np.nan
    pos     = locked.ffill().fillna(0.0)

    arith   = close[assets].pct_change().fillna(0.0)
    held    = pos.shift(1).fillna(0.0)
    gross   = (held * arith).mean(axis=1)
    is_mon_s = pd.Series(is_mon, index=pos.index).astype(float)
    turn     = pos.diff().abs()
    costs    = (turn * 0.0017 * is_mon_s.values.reshape(-1, 1)).mean(axis=1)
    return gross - costs


def btc_buy_hold(close: pd.DataFrame) -> pd.Series:
    return close["BTC-USD"].pct_change().fillna(0.0)


# ── Regime decomposition ──────────────────────────────────────────────────────

def regime_decomposition(pnl_oos: pd.Series, regimes_oos: pd.Series) -> pd.DataFrame:
    results = []
    for lbl in ["BULL_TREND", "BEAR_TREND", "RANGE", "CRASH"]:
        mask = regimes_oos.reindex(pnl_oos.index).ffill() == lbl
        sub  = pnl_oos[mask]
        frac = mask.mean()
        if len(sub) < 5:
            results.append({"regime": lbl, "pct_time": frac,
                            "sharpe": np.nan, "avg_weekly_ret": np.nan})
            continue
        sub_w = sub.resample("W-MON").sum()
        results.append({
            "regime":       lbl,
            "pct_time":     frac,
            "sharpe":       sharpe(sub),
            "avg_weekly_ret": sub_w.mean(),
        })
    return pd.DataFrame(results)


# ── Walk-forward ──────────────────────────────────────────────────────────────

WALK_FOLDS = [
    {"train_end": "2022-12-31", "test_start": "2023-01-01", "test_end": "2023-12-31"},
    {"train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-12-31"},
    {"train_end": "2024-06-30", "test_start": "2024-07-01", "test_end": "2024-12-31"},
    {"train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-12-31"},
]


def run_walk_forward(close: pd.DataFrame, btc_close: pd.Series) -> List[dict]:
    results = []
    for i, fold in enumerate(WALK_FOLDS, 1):
        print(f"\n  [WF fold {i}] train→{fold['train_end']}  "
              f"test: {fold['test_start']}→{fold['test_end']}")
        try:
            regimes, method = detect_regimes(
                btc_close, train_end=fold["train_end"],
                use_funding=False, use_dom=True,
            )
            pos_bull, pos_bear = build_raw_positions(close)
            positions = route_positions(pos_bull, pos_bear, regimes, close)
            pnl       = compute_pnl(close, positions, regimes)
            pnl_oos   = pnl[fold["test_start"]: fold["test_end"]]
            reg_oos   = regimes[fold["test_start"]: fold["test_end"]]

            # TSMOM baseline for same period
            pnl_base  = tsmom_baseline_pnl(close)
            pnl_b_oos = pnl_base[fold["test_start"]: fold["test_end"]]

            dist = reg_oos.value_counts(normalize=True).to_dict()
            results.append({
                "fold":         i,
                "test_period":  f"{fold['test_start'][:7]}–{fold['test_end'][:7]}",
                "method":       method,
                "sharpe_meta":  sharpe(pnl_oos),
                "sharpe_tsmom": sharpe(pnl_b_oos),
                "max_dd_meta":  max_drawdown(pnl_oos),
                "regime_dist":  dist,
            })
            for lbl, frac in dist.items():
                print(f"    {lbl}: {frac:.0%}")
        except Exception as e:
            print(f"  [WF fold {i}] ERROR: {e}")
            results.append({"fold": i, "error": str(e)})
    return results


# ── Regime timeline (monthly) ─────────────────────────────────────────────────

def monthly_regime_table(regimes: pd.Series) -> pd.DataFrame:
    regimes.index = pd.to_datetime(regimes.index)
    months = pd.period_range(regimes.index[0], regimes.index[-1], freq="M")
    rows = []
    for m in months:
        mask = (regimes.index.year == m.year) & (regimes.index.month == m.month)
        sub  = regimes[mask]
        if len(sub) == 0:
            continue
        dominant = sub.value_counts().index[0]
        rows.append({"month": str(m), "dominant": dominant,
                     **{l: (sub == l).mean() for l in ["BULL_TREND","BEAR_TREND","RANGE","CRASH"]}})
    return pd.DataFrame(rows).set_index("month")


# ── Figure ────────────────────────────────────────────────────────────────────

def plot_results(pnl_meta, pnl_tsmom, pnl_btc, regimes,
                 decomp, wf_results, out_path):
    fig, axes = plt.subplots(5, 1, figsize=(14, 26),
                             gridspec_kw={"height_ratios": [3, 1.5, 1.5, 1, 1.5]})
    fig.suptitle("Regime-Conditional Meta-Strategy — OOS Analysis", fontsize=14, fontweight="bold")

    # ── Subplot 1: Equity curves + regime background ──
    ax = axes[0]
    oos_start = pd.Timestamp(TEST_START)

    def equity(pnl):
        return (1 + pnl[pnl.index >= oos_start]).cumprod()

    eq_meta  = equity(pnl_meta)
    eq_tsmom = equity(pnl_tsmom)
    eq_btc   = equity(pnl_btc)

    # Color-code regime background
    reg_oos = regimes.reindex(eq_meta.index).ffill().fillna("RANGE")
    dates   = reg_oos.index
    prev_r  = None
    seg_start = dates[0]
    for i, (dt, r) in enumerate(reg_oos.items()):
        if r != prev_r or i == len(dates) - 1:
            if prev_r is not None:
                ax.axvspan(seg_start, dt, alpha=0.15,
                           color=COLORS.get(prev_r, "#cccccc"), lw=0)
            seg_start = dt
            prev_r = r

    ax.plot(eq_meta,  color="#2c3e50", lw=2,   label="Regime Meta")
    ax.plot(eq_tsmom, color="#3498db", lw=1.5, label="TSMOM v2 alone", alpha=0.8)
    ax.plot(eq_btc,   color="#e67e22", lw=1,   label="BTC buy-hold",   alpha=0.6)
    ax.axhline(1.0, color="black", lw=0.5, ls="--")
    ax.set_ylabel("Equity (OOS, start=1.0)")
    ax.legend(loc="upper left", fontsize=9)
    # Legend for regime colors
    patches = [mpatches.Patch(color=c, alpha=0.3, label=l)
               for l, c in COLORS.items()]
    ax.legend(handles=ax.get_legend_handles_labels()[0] + patches,
              labels=ax.get_legend_handles_labels()[1] + [p.get_label() for p in patches],
              loc="upper left", fontsize=8, ncol=2)
    ax.set_title("OOS Equity Curves (2023–2026) — shaded by regime", fontsize=11)

    # ── Subplot 2: Monthly regime timeline ──
    ax2 = axes[1]
    monthly = monthly_regime_table(regimes)
    regime_order = ["BULL_TREND", "BEAR_TREND", "RANGE", "CRASH"]
    bottoms = np.zeros(len(monthly))
    for lbl in regime_order:
        col = monthly[lbl].fillna(0).values if lbl in monthly.columns else np.zeros(len(monthly))
        ax2.bar(range(len(monthly)), col, bottom=bottoms,
                color=COLORS[lbl], label=lbl, alpha=0.85, width=1.0)
        bottoms += col
    ax2.set_xticks(range(0, len(monthly), 6))
    ax2.set_xticklabels(monthly.index[::6], rotation=45, fontsize=7)
    ax2.set_ylabel("Fraction of month")
    ax2.set_title("Monthly Regime Distribution (2020–2026)", fontsize=11)
    ax2.legend(fontsize=8, loc="upper right", ncol=2)

    # ── Subplot 3: Sharpe contribution per regime ──
    ax3 = axes[2]
    if decomp is not None:
        bars = ax3.bar(decomp["regime"], decomp["sharpe"].fillna(0),
                       color=[COLORS.get(r, "#999") for r in decomp["regime"]],
                       alpha=0.85)
        for bar, row in zip(bars, decomp.itertuples()):
            pct = f"{row.pct_time:.0%}"
            ax3.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.05, pct,
                     ha="center", va="bottom", fontsize=9)
        ax3.axhline(0, color="black", lw=0.7)
        ax3.set_ylabel("Sharpe (regime sub-period)")
        ax3.set_title("Sharpe Contribution per Regime (labels show % time in regime)", fontsize=11)

    # ── Subplot 4: Walk-forward Sharpe ──
    ax4 = axes[3]
    valid_wf = [r for r in wf_results if "sharpe_meta" in r]
    if valid_wf:
        fold_labels = [r["test_period"] for r in valid_wf]
        sh_meta  = [r["sharpe_meta"]  for r in valid_wf]
        sh_tsmom = [r["sharpe_tsmom"] for r in valid_wf]
        x = np.arange(len(fold_labels))
        ax4.bar(x - 0.2, sh_meta,  0.35, label="Regime Meta",   color="#2c3e50", alpha=0.85)
        ax4.bar(x + 0.2, sh_tsmom, 0.35, label="TSMOM alone",   color="#3498db", alpha=0.85)
        ax4.set_xticks(x)
        ax4.set_xticklabels(fold_labels, fontsize=8)
        ax4.axhline(0, color="black", lw=0.7)
        ax4.set_ylabel("Sharpe")
        ax4.set_title("Walk-Forward Sharpe by Window", fontsize=11)
        ax4.legend(fontsize=9)

    # ── Subplot 5: Drawdown ──
    ax5 = axes[4]
    def dd_series(pnl):
        eq = (1 + pnl[pnl.index >= oos_start]).cumprod()
        return eq / eq.cummax() - 1

    ax5.fill_between(eq_meta.index,  dd_series(pnl_meta),  0,
                     color="#2c3e50", alpha=0.5, label="Regime Meta")
    ax5.fill_between(eq_tsmom.index, dd_series(pnl_tsmom), 0,
                     color="#3498db", alpha=0.3, label="TSMOM alone")
    ax5.fill_between(eq_btc.index,   dd_series(pnl_btc),   0,
                     color="#e67e22", alpha=0.2, label="BTC buy-hold")
    ax5.set_ylabel("Drawdown")
    ax5.set_title("Drawdown Comparison (OOS 2023–2026)", fontsize=11)
    ax5.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("REGIME-CONDITIONAL META-STRATEGY — BACKTEST")
    print("=" * 60)

    # 1. Data
    close = download_data()
    missing = [a for a in TSMOM_UNIVERSE if a not in close.columns]
    if missing:
        print(f"  Assets not available (dropped): {missing}")
    btc_close = close["BTC-USD"]

    # 2. Regime detection (full period, HMM fit on train only)
    regimes, method = detect_regimes(
        btc_close, train_end=TRAIN_END,
        use_funding=True, use_dom=True,
    )
    print(f"\n  Regime method: {method}")

    # Regime distribution
    print("\nRegime distribution (full period):")
    dist = regimes.value_counts(normalize=True) * 100
    for lbl in ["BULL_TREND", "BEAR_TREND", "RANGE", "CRASH"]:
        print(f"  {lbl:<14}: {dist.get(lbl, 0):.1f}%")

    # Monthly regime timeline
    print("\nMonthly regime timeline (dominant regime per month):")
    monthly = monthly_regime_table(regimes)
    prev_yr = None
    for month_str, row in monthly.iterrows():
        yr = month_str[:4]
        if yr != prev_yr:
            print(f"  {yr}:", end=" ")
            prev_yr = yr
        mo = month_str[5:7]
        dom = row["dominant"]
        shortcode = {"BULL_TREND": "BULL", "BEAR_TREND": "BEAR",
                     "RANGE": "RNG ", "CRASH": "CRSH"}[dom]
        print(f"{mo}:{shortcode}", end="  ")
    print()

    # 3. Build positions
    print("\nBuilding positions...")
    pos_bull, pos_bear = build_raw_positions(close)
    positions = route_positions(pos_bull, pos_bear, regimes, close)

    # 4. P&L
    print("Computing P&L...")
    pnl_meta  = compute_pnl(close, positions, regimes)
    pnl_tsmom = tsmom_baseline_pnl(close)
    pnl_btc   = btc_buy_hold(close)

    # 5. OOS metrics
    pnl_meta_oos  = pnl_meta[TEST_START:]
    pnl_tsmom_oos = pnl_tsmom[TEST_START:]
    pnl_btc_oos   = pnl_btc[TEST_START:]

    # No-bear variant
    reg_no_bear = regimes.copy()
    reg_no_bear[reg_no_bear == "BEAR_TREND"] = "RANGE"
    pos_nb       = route_positions(pos_bull,
                                   pd.DataFrame(0.0, index=close.index, columns=close.columns),
                                   reg_no_bear, close)
    pnl_no_bear  = compute_pnl(close, pos_nb, reg_no_bear)
    pnl_nb_oos   = pnl_no_bear[TEST_START:]

    print("\n" + "─" * 60)
    print("OOS PERFORMANCE (2023–2026)")
    print("─" * 60)
    hdr = f"  {'Strategy':<24} {'Sharpe':>7} {'Sortino':>8} {'MaxDD':>7} {'Calmar':>7} {'PF':>6} {'WinRate':>8} {'MaxCL':>6}"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    for pnl, lbl in [
        (pnl_meta_oos,  "Regime meta (full)"),
        (pnl_nb_oos,    "Regime meta (no BEAR)"),
        (pnl_tsmom_oos, "TSMOM v2 alone"),
        (pnl_btc_oos,   "Buy-and-hold BTC"),
    ]:
        m = metrics_dict(pnl, lbl)
        print(f"  {m['label']:<24} {m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
              f"{m['max_dd']:>7.1%} {m['calmar']:>7.2f} "
              f"{m['pf']:>6.2f} {m['win_rate']:>8.1%} {m['max_cl_weeks']:>6d}")

    # 6. Regime decomposition
    print("\n" + "─" * 60)
    print("REGIME DECOMPOSITION (OOS)")
    print("─" * 60)
    regimes_oos = regimes.reindex(pnl_meta_oos.index).ffill().fillna("RANGE")
    decomp = regime_decomposition(pnl_meta_oos, regimes_oos)
    print(f"  {'Regime':<14} {'% Time':>8} {'Sharpe':>8} {'Avg Wk Ret':>12}  vs cash")
    print("  " + "─" * 50)
    for _, row in decomp.iterrows():
        beats_cash = "✓ beats cash" if (not np.isnan(row["sharpe"]) and row["sharpe"] > 0) else "✗ below cash"
        print(f"  {row['regime']:<14} {row['pct_time']:>8.1%} "
              f"{row['sharpe']:>8.2f} {row['avg_weekly_ret']:>12.3%}  {beats_cash}")

    # 7. Walk-forward
    print("\n" + "─" * 60)
    print("WALK-FORWARD (4 expanding folds)")
    print("─" * 60)
    wf_results = run_walk_forward(close, btc_close)
    print(f"\n  {'Fold':<5} {'Test Period':<18} {'Method':<12} {'Sharpe Meta':>12} {'Sharpe TSMOM':>13} {'MaxDD Meta':>11}")
    print("  " + "─" * 76)
    for r in wf_results:
        if "error" in r:
            print(f"  {r['fold']:<5} ERROR: {r['error']}")
            continue
        flag = " ✓" if r["sharpe_meta"] > r["sharpe_tsmom"] else "  "
        print(f"  {r['fold']:<5} {r['test_period']:<18} {r['method']:<12} "
              f"{r['sharpe_meta']:>12.2f} {r['sharpe_tsmom']:>13.2f} "
              f"{r['max_dd_meta']:>11.1%}{flag}")

    wf_valid = [r for r in wf_results if "sharpe_meta" in r]
    wf_wins  = sum(1 for r in wf_valid if r["sharpe_meta"] > r["sharpe_tsmom"])
    print(f"\n  Meta > TSMOM alone: {wf_wins}/{len(wf_valid)} folds")

    # 8. Plot
    print("\nGenerating figure...")
    out_path = os.path.join(OUT_DIR, "backtest_results.png")
    plot_results(
        pnl_meta_oos, pnl_tsmom_oos, pnl_btc_oos,
        regimes, decomp, wf_results, out_path,
    )

    # 9. Verdict
    sh_meta  = sharpe(pnl_meta_oos)
    sh_tsmom = sharpe(pnl_tsmom_oos)
    mdd_meta = max_drawdown(pnl_meta_oos)

    best_regime = decomp.loc[decomp["sharpe"].fillna(-99).idxmax(), "regime"]
    worst_regime = decomp.loc[decomp["sharpe"].fillna(99).idxmin(), "regime"]

    print("\n" + "═" * 60)
    print("VERDICT")
    print("═" * 60)
    print(f"  OOS Sharpe:          {sh_meta:.2f}  (TSMOM alone: {sh_tsmom:.2f})")
    print(f"  Max DD (OOS):        {mdd_meta:.1%}")
    print(f"  Regime method:       {method}")
    print(f"  Best regime:         {best_regime}")
    print(f"  Worst regime:        {worst_regime}")
    print(f"  WF folds meta>TSMOM: {wf_wins}/{len(wf_valid)}")
    print()

    if sh_meta >= 2.0 and abs(mdd_meta) <= 0.20:
        verdict = "STRONG"
        reason  = "proceed to live implementation"
    elif sh_meta >= 1.5:
        verdict = "PROMISING"
        reason  = f"identify weakest regime ({worst_regime}) and improve"
    else:
        verdict = "WEAK"
        reason  = "regime detection not adding value over TSMOM alone"

    print(f"  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print("═" * 60)


if __name__ == "__main__":
    main()
