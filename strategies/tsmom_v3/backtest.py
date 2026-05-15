"""
TSMOM v3 — 4-Config Backtest
============================
Compares four progressive improvements to TSMOM v2:

  C0  Binary signal  (v2 baseline: sign(cumret_28d), long-only)
  C1  + Continuous signal  (tanh t-stat, Zarattini 2025)
  C2  + Multi-timeframe    (7/14/28/60d weighted, fixed weights)
  C3  + Strategy vol scale (Barroso & Santa-Clara 2015)

Train: 2020-06-01 → 2022-12-31
Test:  2023-01-01 → 2026-05-14  (3.5 years OOS)

Usage:
  /usr/bin/python3 -m strategies.tsmom_v3.backtest
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

import warnings
from typing import Optional
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from strategies.tsmom_v3.signal import (
    binary_signal, continuous_signal, multi_tf_signal,
    build_positions, apply_bsc_scale, weekly_lock,
    TRADING_DAYS, MTF_LOOKBACKS, MTF_WEIGHTS,
)

# ── Constants ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
    "ADA-USD", "DOT-USD", "UNI-USD", "LTC-USD", "BCH-USD",
    "MATIC-USD", "OP-USD", "ARB-USD",
]
DATA_START  = "2020-01-01"
DATA_END    = "2026-05-14"
TEST_START  = "2023-01-01"
TRAIN_END   = "2022-12-31"
VOL_TARGET  = 0.18
COST_PER_LEG = 0.00085   # 0.085% one-way (= 0.17% RT)
BSC_TARGET  = 0.15       # B&SC normalizes to this strategy vol

OUT_DIR = os.path.dirname(__file__)

WALK_FOLDS = [
    {"train_end": "2022-12-31", "test_start": "2023-01-01", "test_end": "2023-12-31"},
    {"train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-12-31"},
    {"train_end": "2024-06-30", "test_start": "2024-07-01", "test_end": "2024-12-31"},
    {"train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-12-31"},
]


# ── Data ──────────────────────────────────────────────────────────────────────

def download_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (close, log_ret) DataFrames for the full universe."""
    print(f"Downloading {len(UNIVERSE)}-asset universe ({DATA_START} → {DATA_END})...")
    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.ffill()
    available = [c for c in UNIVERSE if c in raw.columns and raw[c].dropna().shape[0] > 100]
    raw = raw[available]
    log_ret = np.log(raw / raw.shift(1)).clip(-1.0, 1.0)
    print(f"  Available: {len(available)} assets  "
          f"Range: {raw.index[0].date()} → {raw.index[-1].date()}")
    return raw, log_ret


# ── P&L engine ────────────────────────────────────────────────────────────────

def compute_pnl(
    close:     pd.DataFrame,
    positions: pd.DataFrame,
) -> pd.Series:
    """
    MEAN convention P&L.
    Returns = mean across assets of (held_position × arith_return).
    Costs on Monday rebalance days only: mean(turnover × COST_PER_LEG).
    """
    arith = close.pct_change().fillna(0.0)
    held  = positions.shift(1).fillna(0.0)
    gross = (held * arith).mean(axis=1)

    is_mon = pd.Series(close.index.dayofweek == 0, index=close.index).astype(float)
    turn   = positions.diff().abs()
    costs  = (turn * COST_PER_LEG * is_mon.values.reshape(-1, 1)).mean(axis=1)
    return gross - costs


# ── Metrics ───────────────────────────────────────────────────────────────────

def _metrics(pnl: pd.Series) -> dict:
    r = pnl.dropna()
    if len(r) < 5 or r.std() == 0:
        return {k: np.nan for k in
                ["sharpe","sortino","calmar","max_dd","pf","win_rate","max_cl_weeks"]}
    sh  = r.mean() / r.std() * np.sqrt(TRADING_DAYS)
    neg = r[r < 0]
    so  = (r.mean() / neg.std() * np.sqrt(TRADING_DAYS)) if len(neg) > 1 else np.nan
    eq  = (1 + r).cumprod()
    mdd = float((eq / eq.cummax() - 1).min())
    ann = r.mean() * TRADING_DAYS
    cal = ann / abs(mdd) if mdd != 0 else np.nan
    pf  = r[r > 0].sum() / abs(r[r < 0].sum())
    rw  = r.resample("W-MON").sum()
    wr  = float((rw > 0).mean())
    streak = cl = 0
    for x in rw:
        if x < 0:
            streak += 1; cl = max(cl, streak)
        else:
            streak = 0
    return dict(sharpe=sh, sortino=so, calmar=cal, max_dd=mdd,
                pf=pf, win_rate=wr, max_cl_weeks=cl)


def _print_metrics_row(label: str, m: dict) -> None:
    print(f"  {label:<28} {m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
          f"{m['max_dd']:>7.1%} {m['calmar']:>8.2f} "
          f"{m['pf']:>6.2f} {m['win_rate']:>8.1%} {m['max_cl_weeks']:>6d}")


# ── Config builders ───────────────────────────────────────────────────────────

def positions_c0(log_ret: pd.DataFrame) -> pd.DataFrame:
    """C0: binary sign, 28d, long-only, vol-scaled, Monday-locked."""
    sig = binary_signal(log_ret, 28)
    return build_positions(sig, log_ret, VOL_TARGET)


def positions_c1(log_ret: pd.DataFrame) -> pd.DataFrame:
    """C1: continuous tanh(t-stat), 28d, long-only."""
    sig = continuous_signal(log_ret, 28)
    return build_positions(sig, log_ret, VOL_TARGET)


def positions_c2(log_ret: pd.DataFrame) -> pd.DataFrame:
    """C2: multi-timeframe continuous, fixed weights."""
    sig = multi_tf_signal(log_ret)
    return build_positions(sig, log_ret, VOL_TARGET)


def positions_c3(log_ret: pd.DataFrame) -> pd.DataFrame:
    """C3: C2 + B&SC momentum vol scaling."""
    pos = positions_c2(log_ret)
    return apply_bsc_scale(pos, log_ret, BSC_TARGET)


# ── Walk-forward ──────────────────────────────────────────────────────────────

def run_walk_forward(
    close:   pd.DataFrame,
    log_ret: pd.DataFrame,
) -> list[dict]:
    results = []
    for i, fold in enumerate(WALK_FOLDS, 1):
        print(f"  [WF {i}] test: {fold['test_start']} → {fold['test_end']}")
        pnl_c0 = compute_pnl(close, positions_c0(log_ret))
        pnl_c3 = compute_pnl(close, positions_c3(log_ret))
        ts, te  = fold["test_start"], fold["test_end"]
        m0 = _metrics(pnl_c0[ts:te])
        m3 = _metrics(pnl_c3[ts:te])
        results.append({
            "fold": i,
            "period": f"{ts[:7]}–{te[:7]}",
            "sh_c0": m0["sharpe"], "sh_c3": m3["sharpe"],
            "dd_c0": m0["max_dd"], "dd_c3": m3["max_dd"],
        })
    return results


# ── BONUS: Portfolio A + B combination ───────────────────────────────────────

def load_carry_returns(test_start: str) -> Optional[pd.Series]:
    """
    Attempt to compute simplified BTC funding carry returns.
    Uses BTC 8h funding rates from local CSV.
    Returns daily carry return series or None if unavailable.
    """
    carry_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "funding_carry", "BTC_funding.csv"
    )
    try:
        df = pd.read_csv(carry_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")["funding_rate_1h"].sort_index()
        # 3 × 8h bars per day, sum to daily
        daily = df.resample("D").sum()
        daily.index = daily.index.tz_localize(None)
        # Carry return = daily funding collected (short perp, receive funding)
        # Minus amortized cost: 0.42% RT / ~180 holds ≈ 0.0023% per day
        daily_cost = 0.0042 / 180
        carry = daily - daily_cost
        carry = carry[carry.index >= test_start]
        if len(carry) < 100:
            return None
        print(f"  [carry] BTC funding carry loaded: {len(carry)} days "
              f"({carry.index[0].date()} → {carry.index[-1].date()})")
        return carry
    except Exception as e:
        print(f"  [carry] not available: {e}")
        return None


def portfolio_ab_combination(
    pnl_a:  pd.Series,
    carry:  pd.Series,
) -> None:
    """Test w_A in [0.5, 0.6, 0.7, 0.8]; remainder to carry B."""
    print("\n  A+B PORTFOLIO COMBINATION")
    print(f"  {'w_A':>6} {'w_B':>6} {'Sharpe':>8} {'MaxDD':>8} {'Corr(A,B)':>10}")
    print("  " + "─" * 46)
    common = pnl_a.index.intersection(carry.index)
    a = pnl_a.reindex(common).fillna(0.0)
    b = carry.reindex(common).fillna(0.0)
    corr = float(a.corr(b))
    best_sh = -np.inf
    best_wa = None
    for wa in [0.5, 0.6, 0.7, 0.8]:
        wb = 1.0 - wa
        comb = wa * a + wb * b
        m = _metrics(comb)
        flag = " ← best" if m["sharpe"] > best_sh else ""
        if m["sharpe"] > best_sh:
            best_sh = m["sharpe"]
            best_wa = wa
        print(f"  {wa:>6.0%} {wb:>6.0%} {m['sharpe']:>8.2f} "
              f"{m['max_dd']:>8.1%} {corr:>10.3f}{flag}")
    print(f"\n  Corr(TSMOM_C3, BTC_carry) : {corr:.3f}  "
          f"({'near zero ✓' if abs(corr) < 0.20 else 'correlated — check'})")
    print(f"  Best combined Sharpe      : {best_sh:.2f}  (w_A={best_wa:.0%})")


# ── Figure ────────────────────────────────────────────────────────────────────

def plot_results(
    pnls_oos: dict[str, pd.Series],
    pnl_btc:  pd.Series,
    wf:       list[dict],
    log_ret:  pd.DataFrame,
    out_path: str,
) -> None:
    configs = ["C0", "C1", "C2", "C3"]
    colors  = {"C0": "#95a5a6", "C1": "#3498db", "C2": "#e67e22", "C3": "#2c3e50"}

    fig, axes = plt.subplots(5, 1, figsize=(14, 26),
                             gridspec_kw={"height_ratios": [3, 1.5, 1.5, 1.5, 1.5]})
    fig.suptitle("TSMOM v3 — Signal Improvements vs Baseline", fontsize=14, fontweight="bold")

    # ── 1: OOS equity curves ──
    ax = axes[0]
    for cfg in configs:
        pnl = pnls_oos[cfg]
        eq  = (1 + pnl).cumprod()
        sh  = pnl.mean() / pnl.std() * np.sqrt(TRADING_DAYS)
        ax.plot(eq.index, eq.values, color=colors[cfg], lw=2 if cfg == "C3" else 1.5,
                label=f"{cfg} (Sh={sh:.2f})", alpha=1.0 if cfg == "C3" else 0.8)
    btc_eq = (1 + pnl_btc[TEST_START:]).cumprod()
    ax.plot(btc_eq.index, btc_eq.values, color="#F7931A", lw=1, ls="--",
            alpha=0.5, label="BTC buy-hold")
    ax.axhline(1.0, color="black", lw=0.5, ls="--")
    ax.set_ylabel("Equity (OOS, start=1.0)")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("OOS Equity Curves (2023–2026): C0 baseline → C3 improved", fontsize=11)
    ax.grid(alpha=0.3)

    # ── 2: Rolling 6-month Sharpe C0 vs C3 ──
    ax2 = axes[1]
    w = 182  # ~6 months in calendar days
    for cfg, lw in [("C0", 1.5), ("C3", 2.0)]:
        pnl = pnls_oos[cfg]
        roll_sh = pnl.rolling(w).apply(
            lambda x: x.mean() / x.std() * np.sqrt(TRADING_DAYS) if x.std() > 0 else 0,
            raw=True
        )
        ax2.plot(roll_sh.index, roll_sh.values, color=colors[cfg], lw=lw, label=cfg)
    ax2.axhline(0, color="black", lw=0.5, ls="--")
    ax2.axhline(2.0, color="green", lw=0.8, ls=":", alpha=0.6, label="Sharpe=2 target")
    ax2.set_ylabel("Rolling 6m Sharpe")
    ax2.set_title("Rolling 6-Month Sharpe: C0 vs C3 (stability)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)

    # ── 3: Walk-forward Sharpe bars ──
    ax3 = axes[2]
    valid_wf = [r for r in wf if not np.isnan(r.get("sh_c0", np.nan))]
    if valid_wf:
        x = np.arange(len(valid_wf))
        periods = [r["period"] for r in valid_wf]
        sh_c0 = [r["sh_c0"] for r in valid_wf]
        sh_c3 = [r["sh_c3"] for r in valid_wf]
        ax3.bar(x - 0.2, sh_c0, 0.35, label="C0 baseline", color=colors["C0"], alpha=0.9)
        ax3.bar(x + 0.2, sh_c3, 0.35, label="C3 improved", color=colors["C3"], alpha=0.9)
        ax3.set_xticks(x)
        ax3.set_xticklabels(periods, fontsize=9)
        ax3.axhline(0, color="black", lw=0.7)
        ax3.set_ylabel("Sharpe")
        ax3.set_title("Walk-Forward Sharpe by Window (C0 vs C3)", fontsize=11)
        ax3.legend(fontsize=9)
        ax3.grid(alpha=0.3, axis="y")

    # ── 4: Signal comparison on BTC ──
    ax4 = axes[3]
    oos_mask = log_ret.index >= TEST_START
    lr_btc   = log_ret.loc[oos_mask, "BTC-USD"].to_frame("BTC-USD")
    sig_c0   = binary_signal(lr_btc, 28)["BTC-USD"]
    sig_c3   = multi_tf_signal(lr_btc)["BTC-USD"]
    btc_close_proxy = np.exp(lr_btc["BTC-USD"].cumsum())

    ax4b = ax4.twinx()
    ax4b.plot(btc_close_proxy.index, btc_close_proxy.values,
              color="#F7931A", lw=0.8, alpha=0.3, label="BTC price")
    ax4.step(sig_c0.index, sig_c0.values, color=colors["C0"], lw=1.2,
             label="C0 binary (0/1)", alpha=0.8, where="post")
    ax4.plot(sig_c3.index, sig_c3.values, color=colors["C3"], lw=1.5,
             label="C3 multi-tf continuous", alpha=0.9)
    ax4.set_ylim(-0.05, 1.15)
    ax4.set_ylabel("Signal strength [0, 1]")
    ax4.set_title("Signal Comparison on BTC (OOS): Binary vs Multi-TF Continuous", fontsize=11)
    ax4.legend(loc="upper left", fontsize=9)
    ax4b.set_ylabel("BTC price (log scale)", color="#F7931A")
    ax4.grid(alpha=0.3)

    # ── 5: Drawdown comparison ──
    ax5 = axes[4]
    for cfg in ["C0", "C3"]:
        pnl = pnls_oos[cfg]
        eq  = (1 + pnl).cumprod()
        dd  = eq / eq.cummax() - 1
        ax5.fill_between(dd.index, dd.values, 0, color=colors[cfg], alpha=0.45, label=cfg)
    btc_dd = btc_eq / btc_eq.cummax() - 1
    ax5.fill_between(btc_dd.index, btc_dd.values, 0, color="#F7931A", alpha=0.2, label="BTC")
    ax5.set_ylabel("Drawdown")
    ax5.set_title("Drawdown Comparison (OOS): C0 vs C3 vs BTC", fontsize=11)
    ax5.legend(fontsize=9)
    ax5.grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 62)
    print("TSMOM v3 — CONTINUOUS + MULTI-TF + B&SC VOL SCALING")
    print("=" * 62)

    # 1. Data
    close, log_ret = download_data()

    # 2. Build all 4 config positions
    print("\nBuilding positions for all 4 configs...")
    pos = {
        "C0": positions_c0(log_ret),
        "C1": positions_c1(log_ret),
        "C2": positions_c2(log_ret),
        "C3": positions_c3(log_ret),
    }

    # 3. Compute P&L
    print("Computing P&L...")
    pnls = {cfg: compute_pnl(close, p) for cfg, p in pos.items()}
    pnl_btc = close["BTC-USD"].pct_change().fillna(0.0)

    # Slice to OOS
    pnls_oos = {cfg: pnl[TEST_START:] for cfg, pnl in pnls.items()}
    pnls_full = pnls

    # 4. OOS metrics table
    print("\n" + "─" * 62)
    print(f"OOS PERFORMANCE ({TEST_START} → {DATA_END})")
    print("─" * 62)
    hdr = (f"  {'Config':<28} {'Sharpe':>7} {'Sortino':>8} "
           f"{'MaxDD':>7} {'Calmar':>8} {'PF':>6} {'WinRate':>8} {'MaxCL':>6}")
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    config_labels = {
        "C0": "C0: TSMOM v2 baseline",
        "C1": "C1: + continuous signal",
        "C2": "C2: + multi-timeframe",
        "C3": "C3: + momentum vol scale",
    }
    for cfg in ["C0", "C1", "C2", "C3"]:
        m = _metrics(pnls_oos[cfg])
        _print_metrics_row(config_labels[cfg], m)

    # BTC buy-hold
    m_btc = _metrics(pnl_btc[TEST_START:])
    _print_metrics_row("Buy-and-hold BTC", m_btc)

    # 5. Improvement attribution
    m0 = _metrics(pnls_oos["C0"])
    m1 = _metrics(pnls_oos["C1"])
    m2 = _metrics(pnls_oos["C2"])
    m3 = _metrics(pnls_oos["C3"])
    print(f"\n  Sharpe lift breakdown:")
    print(f"    C0 → C1 (continuous signal)  : {m1['sharpe'] - m0['sharpe']:+.2f}")
    print(f"    C1 → C2 (multi-timeframe)    : {m2['sharpe'] - m1['sharpe']:+.2f}")
    print(f"    C2 → C3 (B&SC vol scale)     : {m3['sharpe'] - m2['sharpe']:+.2f}")
    print(f"    Total lift C0 → C3           : {m3['sharpe'] - m0['sharpe']:+.2f}")

    # 6. Annual breakdown
    print("\n" + "─" * 62)
    print("ANNUAL BREAKDOWN (C0 vs C3, OOS years)")
    print("─" * 62)
    print(f"  {'Year':<6} {'Sh(C0)':>8} {'Sh(C3)':>8} {'DD(C0)':>8} "
          f"{'DD(C3)':>8}  {'Better?':>8}")
    for year in range(2023, 2027):
        mask = pnls_oos["C0"].index.year == year
        if not mask.any():
            continue
        mc0 = _metrics(pnls_oos["C0"][mask])
        mc3 = _metrics(pnls_oos["C3"][mask])
        flag = "C3 ✓" if mc3["sharpe"] > mc0["sharpe"] else "C0  "
        print(f"  {year:<6} {mc0['sharpe']:>8.2f} {mc3['sharpe']:>8.2f} "
              f"{mc0['max_dd']:>8.1%} {mc3['max_dd']:>8.1%}  {flag}")

    # 7. Walk-forward
    print("\n" + "─" * 62)
    print("WALK-FORWARD (4 windows)")
    print("─" * 62)
    print("Building walk-forward positions...")
    wf_results = run_walk_forward(close, log_ret)
    print(f"\n  {'Fold':<5} {'Period':<18} {'Sh(C0)':>8} {'Sh(C3)':>8} "
          f"{'DD(C0)':>8} {'DD(C3)':>8}  {'C3>C0?':>7}")
    print("  " + "─" * 70)
    wf_wins = 0
    for r in wf_results:
        flag = "✓" if r["sh_c3"] > r["sh_c0"] else "✗"
        if r["sh_c3"] > r["sh_c0"]:
            wf_wins += 1
        print(f"  {r['fold']:<5} {r['period']:<18} {r['sh_c0']:>8.2f} "
              f"{r['sh_c3']:>8.2f} {r['dd_c0']:>8.1%} {r['dd_c3']:>8.1%}  {flag}")
    print(f"\n  C3 > C0 in {wf_wins}/{len(wf_results)} walk-forward folds")

    # 8. BONUS: A+B combination (if C3 Sharpe > 1.5)
    if m3["sharpe"] > 1.5:
        print("\n" + "─" * 62)
        print("BONUS — PORTFOLIO A+B COMBINATION")
        print("─" * 62)
        carry = load_carry_returns(TEST_START)
        if carry is not None:
            portfolio_ab_combination(pnls_oos["C3"], carry)
        else:
            print("  [carry] BTC funding carry unavailable — skipping A+B combination")
            print("  Note: Strategy B (delta-neutral) requires local funding CSV data.")
    else:
        print(f"\n  [BONUS skipped] C3 Sharpe={m3['sharpe']:.2f} < 1.5 threshold")

    # 9. Figure
    print("\nGenerating figure...")
    plot_results(
        pnls_oos, pnl_btc, wf_results, log_ret,
        os.path.join(OUT_DIR, "backtest_results.png"),
    )

    # 10. Verdict
    sh3  = m3["sharpe"]
    mdd3 = m3["max_dd"]

    # Best improvement
    lifts = {
        "continuous signal":  m1["sharpe"] - m0["sharpe"],
        "multi-timeframe":    m2["sharpe"] - m1["sharpe"],
        "B&SC vol scale":     m3["sharpe"] - m2["sharpe"],
    }
    best_imp = max(lifts, key=lifts.get)

    print("\n" + "═" * 62)
    print("VERDICT")
    print("═" * 62)
    print(f"  C3 OOS Sharpe  : {sh3:.2f}  (C0 baseline: {m0['sharpe']:.2f})")
    print(f"  C3 Max DD      : {mdd3:.1%}")
    print(f"  Biggest lift   : {best_imp}  ({lifts[best_imp]:+.2f} Sharpe)")
    print(f"  WF consistency : C3 > C0 in {wf_wins}/{len(wf_results)} folds")
    print()

    if sh3 >= 2.0 and wf_wins >= 3:
        verdict  = "DEPLOY"
        reason   = (f"Sharpe ≥ 2.0 OOS + {wf_wins}/4 WF folds — "
                    f"implement {best_imp} in production")
    elif sh3 >= 1.6:
        verdict  = "PROMISING"
        reason   = (f"Sharpe {sh3:.2f} — consistent WF improvement. "
                    f"Priority: deploy {best_imp}; investigate weakest year")
    else:
        verdict  = "WEAK"
        reason   = (f"Sharpe {sh3:.2f} < 1.6 or WF inconsistent. "
                    f"Improvements do not meaningfully exceed v2 baseline")

    print(f"  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print("═" * 62)


if __name__ == "__main__":
    main()
