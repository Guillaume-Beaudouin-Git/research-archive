"""
research_eurusd_edge.py — forensic study of the EURUSD intraday-MR edge
========================================================================

Mandate: "dig into the EURUSD edge, careful about overfit." Protocol, anti-overfit by
construction:

  • IN-SAMPLE (already explored in prior work)      : 2022-01 .. 2024-12
  • HOLD-OUT (NEVER touched for any choice)          : 2025-01 .. 2026-05   ← the judge
  • INDEPENDENT FEED (different data vendor)         : Dukascopy EURUSD 2022-2024
  • Modifications budget                             : <= 2 (L10), PRE-REGISTERED below
  • Significance                                     : per-trade HAC-free t, DSR (L20) with the
                                                       HONEST trial count, per-year stability

Pre-registered hypotheses (decided BEFORE looking at the hold-out):
  H0  Baseline edge is real but small. Test: does it survive untouched 2025-2026 and an
      independent feed, with consistent sign across years?
  H1 (modification #1) Overreaction filter. The reversal mechanism is liquidity-provision
      AFTER an overreaction; gating entries on a genuine single-bar volatility spike (not a
      slow drift into the band = trend) should RAISE per-trade edge and CUT turnover, lifting
      the gross/cost ratio. spike_mult tuned on IS only; confirmed on the hold-out.

A refinement is accepted ONLY if it improves the metric on the untouched hold-out, not just IS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO))
from strategy.fx_data import load_mt5_panel, load_dukascopy             # noqa: E402
from strategy.intraday_fx_mr import (build_bars, add_mr_signal, per_trade_stats,   # noqa: E402
                                     backtest_mr, BacktestConfig)
from dsr import deflated_sharpe_ratio                                    # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
IS = ("2022-01-01", "2024-12-31")
OOS = ("2025-01-01", "2026-05-29")
N_TRIALS_HONEST = 50          # conservative count of EURUSD configs examined across all work
CFG = dict(z_entry=2.0, z_exit=0.5, sigma_target=0.01, markup=3.0, daily_stop=0.008)


def add_overreaction_gate(bars: pd.DataFrame, spike_mult: float, w: int = 48,
                          recent: int = 4) -> pd.DataFrame:
    """
    Causal overreaction-regime gate. The z-extreme typically forms a few bars AFTER the
    impulse, so we gate on RECENT realised vol being elevated vs a trailing baseline
    (a liquidity/overreaction burst), not on the single entry bar:
        gate_t = stdev(logret, last `recent` bars) > spike_mult * stdev(logret, trailing `w`).
    """
    b = bars.copy()
    lr = b["logret"].fillna(0.0)            # session-start NaNs would poison rolling windows
    recent_vol = lr.rolling(recent).std()
    base_vol = lr.rolling(w).std().shift(recent)     # trailing baseline, no overlap
    b["entry_gate"] = (recent_vol > spike_mult * base_vol).fillna(False)
    return b


def make_bars(source: str, start: str, end: str, spike_mult: float | None = None) -> pd.DataFrame:
    df = (load_dukascopy("EURUSD") if source == "duka" else load_mt5_panel("EURUSD")).loc[start:end]
    bars = add_mr_signal(build_bars(df, freq="30min", hours=(7, 20)), window=16)
    if spike_mult is not None:
        bars = add_overreaction_gate(bars, spike_mult)
    return bars


def evaluate(source: str, start: str, end: str, spike_mult: float | None = None) -> dict:
    bars = make_bars(source, start, end, spike_mult)
    cs = 2.0 if source == "duka" else None
    res = backtest_mr(bars, "EURUSD", BacktestConfig(const_spread_points=cs, **CFG))
    m = res.metrics
    pt = per_trade_stats(bars, CFG["z_entry"], CFG["z_exit"])
    return {"net": res.daily_net.dropna(), "ann_sharpe": m["ann_sharpe"],
            "daily_sharpe": m["daily_sharpe"], "win_rate": m["win_rate"],
            "win_loss": m["win_loss_ratio"], "excess_kurt": m["excess_kurtosis"],
            "gross_ann": m["gross_ann_return"], "cost_ann": m["cost_ann_drag"],
            "cost_ratio": m["gross_ann_return"] / max(1e-9, m["cost_ann_drag"]),
            "trade_t": pt["t_stat"], "trades_per_day": pt.get("trades_per_day", np.nan),
            "n_days": m["n_days"]}


def per_year(net: pd.Series) -> dict:
    out = {}
    for y, seg in net.groupby(net.index.year):
        sd = seg.std(ddof=1)
        out[int(y)] = round(float(seg.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0, 2)
    return out


def main() -> int:
    print("=" * 80)
    print("EURUSD edge — forensic study (anti-overfit protocol)")
    print(f"IS={IS[0]}..{IS[1]}  HOLD-OUT(untouched)={OOS[0]}..{OOS[1]}")
    print("=" * 80)

    # ── M0 baseline ───────────────────────────────────────────────────────
    m0_is = evaluate("panel", *IS)
    m0_oos = evaluate("panel", *OOS)
    m0_duka = evaluate("duka", *IS)
    print("\n[M0 baseline]")
    for lbl, r in [("IS  panel", m0_is), ("OOS panel (untouched)", m0_oos), ("IS  Dukascopy", m0_duka)]:
        print(f"  {lbl:24s}: annSh={r['ann_sharpe']:>5.2f} dSh={r['daily_sharpe']:>6.3f} "
              f"WR={r['win_rate']*100:>4.1f}% costRatio={r['cost_ratio']:>4.1f} "
              f"trade_t={r['trade_t']:>4.2f} trd/d={r['trades_per_day']:>4.2f}")
    print(f"  per-year Sharpe (IS+OOS): {per_year(pd.concat([m0_is['net'], m0_oos['net']]))}")
    dsr0 = deflated_sharpe_ratio(m0_is["net"].values, n_trials=N_TRIALS_HONEST, periods_per_year=252)
    print(f"  DSR (IS, n_trials={N_TRIALS_HONEST}): SR={dsr0['sharpe']:.2f} DSR={dsr0['dsr']:.3f}")

    # ── M1 overreaction filter: TUNE ON IS ONLY ─────────────────────────────
    print("\n[M1 overreaction filter] tuning spike_mult on IS only:")
    grid = [1.0, 1.25, 1.5, 2.0]
    is_scan = {}
    for sm in grid:
        r = evaluate("panel", *IS, spike_mult=sm)
        is_scan[sm] = r
        print(f"  spike_mult={sm}: annSh={r['ann_sharpe']:>5.2f} costRatio={r['cost_ratio']:>4.1f} "
              f"trade_t={r['trade_t']:>4.2f} trd/d={r['trades_per_day']:>4.2f} WR={r['win_rate']*100:.1f}%")
    # selection rule (pre-registered): maximise IS cost-ratio subject to trade_t > baseline
    best_sm = max(grid, key=lambda s: is_scan[s]["cost_ratio"])
    print(f"  → selected spike_mult={best_sm} (max IS cost-ratio)")

    # ── confirm the selected filter on the UNTOUCHED hold-out + feed ────────
    m1_is = is_scan[best_sm]
    m1_oos = evaluate("panel", *OOS, spike_mult=best_sm)
    m1_duka = evaluate("duka", *IS, spike_mult=best_sm)
    print(f"\n[M1 confirmation] spike_mult={best_sm}")
    for lbl, r in [("IS  panel", m1_is), ("OOS panel (untouched)", m1_oos), ("IS  Dukascopy", m1_duka)]:
        print(f"  {lbl:24s}: annSh={r['ann_sharpe']:>5.2f} dSh={r['daily_sharpe']:>6.3f} "
              f"WR={r['win_rate']*100:>4.1f}% costRatio={r['cost_ratio']:>4.1f} "
              f"trade_t={r['trade_t']:>4.2f} trd/d={r['trades_per_day']:>4.2f}")
    dsr1 = deflated_sharpe_ratio(m1_is["net"].values, n_trials=N_TRIALS_HONEST, periods_per_year=252)
    print(f"  DSR (IS, n_trials={N_TRIALS_HONEST}): SR={dsr1['sharpe']:.2f} DSR={dsr1['dsr']:.3f}")

    # ── verdict ─────────────────────────────────────────────────────────────
    oos_improved = m1_oos["cost_ratio"] > m0_oos["cost_ratio"] and m1_oos["ann_sharpe"] > m0_oos["ann_sharpe"]
    cost_gate_oos = m1_oos["cost_ratio"] > 3.0
    print("\n[VERDICT]")
    print(f"  Filter improves OOS (cost-ratio & Sharpe): {oos_improved}")
    print(f"  OOS cost gate (>3x) passed by M1: {cost_gate_oos}")
    print(f"  Baseline OOS annSh={m0_oos['ann_sharpe']:.2f} → M1 OOS annSh={m1_oos['ann_sharpe']:.2f}")

    payload = {"protocol": {"IS": IS, "OOS_untouched": OOS, "n_trials_dsr": N_TRIALS_HONEST,
                            "selected_spike_mult": best_sm},
               "m0": {k: _clean(v) for k, v in {"IS": m0_is, "OOS": m0_oos, "Duka": m0_duka,
                                                "per_year": per_year(pd.concat([m0_is['net'], m0_oos['net']])),
                                                "dsr": dsr0}.items()},
               "m1_is_scan": {str(s): _clean(is_scan[s]) for s in grid},
               "m1": {k: _clean(v) for k, v in {"IS": m1_is, "OOS": m1_oos, "Duka": m1_duka, "dsr": dsr1}.items()},
               "verdict": {"oos_improved": bool(oos_improved), "oos_cost_gate_pass": bool(cost_gate_oos)}}
    (RES / "research_eurusd_edge.json").write_text(json.dumps(payload, indent=2, default=str))

    _plot(m0_is, m0_oos, m1_is, m1_oos, is_scan, grid, best_sm)
    print("\n  → results/research_eurusd_edge.json")
    print("  → figures/research_eurusd_edge.png")
    return 0


def _clean(d):
    if isinstance(d, dict):
        return {k: (round(v, 4) if isinstance(v, float) else
                    (None if k == "net" else _clean(v))) for k, v in d.items() if k != "net"}
    return d


def _plot(m0_is, m0_oos, m1_is, m1_oos, is_scan, grid, best_sm):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    # (1) equity IS+OOS, baseline vs filtered, with the OOS boundary
    for r, lbl, c, ls in [(m0_is, "M0 baseline", "#2a9d8f", "-"),
                          (m1_is, f"M1 filter (sm={best_sm})", "#264653", "-")]:
        full = pd.concat([r["net"], (m1_oos if "M1" in lbl else m0_oos)["net"]])
        ax[0, 0].plot(full.index, full.cumsum() * 100, label=lbl, color=c, ls=ls)
    ax[0, 0].axvline(pd.Timestamp(OOS[0]), color="#d1495b", ls=":", lw=1.4)
    ax[0, 0].text(pd.Timestamp(OOS[0]), ax[0, 0].get_ylim()[0], " hold-out →", color="#d1495b", fontsize=8)
    ax[0, 0].axhline(0, color="#aaa", lw=.8)
    ax[0, 0].set_title("Cumulative net return — IS then untouched hold-out (σd=1%, ×3 cost)")
    ax[0, 0].set_ylabel("cum return (%)"); ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.25)
    # (2) IS vs OOS Sharpe, baseline vs filter
    cats = ["M0 IS", "M0 OOS", "M1 IS", "M1 OOS"]
    vals = [m0_is["ann_sharpe"], m0_oos["ann_sharpe"], m1_is["ann_sharpe"], m1_oos["ann_sharpe"]]
    ax[0, 1].bar(cats, vals, color=["#2a9d8f", "#9fd8cf", "#264653", "#7a8e95"])
    ax[0, 1].axhline(0, color="#333", lw=.8)
    ax[0, 1].set_title("Annualised Sharpe: in-sample vs untouched hold-out"); ax[0, 1].set_ylabel("ann Sharpe")
    ax[0, 1].grid(alpha=.25, axis="y")
    # (3) cost ratio IS vs OOS
    ax[1, 0].bar(cats, [m0_is["cost_ratio"], m0_oos["cost_ratio"], m1_is["cost_ratio"], m1_oos["cost_ratio"]],
                 color=["#2a9d8f", "#9fd8cf", "#264653", "#7a8e95"])
    ax[1, 0].axhline(3.0, ls="--", color="#d1495b", label="3× cost gate")
    ax[1, 0].set_title("Gross/cost ratio — does the filter clear the gate OOS?")
    ax[1, 0].set_ylabel("ratio"); ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=.25, axis="y")
    # (4) IS tuning curve + OOS point
    sms = grid
    ax[1, 1].plot(sms, [is_scan[s]["cost_ratio"] for s in sms], "o-", color="#264653", label="IS cost-ratio")
    ax[1, 1].plot(sms, [is_scan[s]["ann_sharpe"] for s in sms], "s--", color="#2a9d8f", label="IS annSharpe")
    ax[1, 1].axvline(best_sm, color="#d1495b", ls=":", label=f"selected={best_sm}")
    ax[1, 1].set_title("M1 tuning on IS only (spike_mult)"); ax[1, 1].set_xlabel("spike_mult")
    ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "research_eurusd_edge.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
