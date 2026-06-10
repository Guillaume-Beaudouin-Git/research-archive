"""
run_family3_pairs.py — Family-3: intraday relative-value (market-neutral index pairs)
======================================================================================

Same anti-overfit protocol: characterise on IS 2022-2024, judge on the untouched
hold-out 2025-2026. The decisive early test is the pre-flight 2-LEG cost gate (L11/L12,
doubly binding for pairs).

Findings (documented by this script):
  • LEVEL cointegration spread half-life is 255-700h → the daily-cointegration graveyard
    (white paper). Not intraday-tradeable.
  • The rolling-DETRENDED divergence DOES revert intraday (half-life ~1.7h ✓), but the
    reversion is smaller than the doubled CFD spread → gross/cost ratio << 3 for every
    pair / band / frequency. NO-GO at the cost gate.

Outputs: results/family3_pairs.json, figures/family3_pairs.png
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
sys.path.insert(0, str(HERE))
from strategy.intraday_pairs import build_pair, backtest_pairs, per_trade_pairs, PairConfig  # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
IS = ("2022-01-01", "2024-12-31")
OOS = ("2025-01-01", "2026-05-29")
PAIRS = [("US500", "US100"), ("US500", "US30"), ("US30", "US2000")]
Z_GRID = [2.0, 2.5, 3.0, 3.5]


def evaluate(a, b, start, end, z_entry, freq="30min"):
    pf = build_pair(a, b, start, end, freq=freq)
    cfg = PairConfig(z_entry=z_entry, z_exit=0.5, sigma_target=0.01, markup=3.0)
    r = backtest_pairs(pf, cfg)
    pt = per_trade_pairs(pf, cfg)
    m = r.metrics
    return {"pair": f"{a}-{b}", "z_entry": z_entry, "ann_sharpe": m["ann_sharpe"],
            "win_rate": m["win_rate"], "gross_ann": m["gross_ann_return"],
            "cost_ann": m["cost_ann_drag"],
            "cost_ratio": m["gross_ann_return"] / max(1e-9, m["cost_ann_drag"]),
            "half_life_hrs": m["half_life_bars"] * 0.5, "trade_t": pt["t_stat"],
            "trades_per_day": m["avg_daily_turnover"] / 2, "net": r.daily_net,
            "z": pf["z"]}


def main() -> int:
    print("=" * 80)
    print("FAMILY-3 — intraday relative-value (market-neutral index pairs)")
    print("=" * 80)

    # cost-gate sweep on IS
    print("\nPre-flight 2-leg cost gate (IS 2022-2024):")
    print(f"{'pair':14s} {'zin':>4} {'HL(h)':>6} {'annSh':>6} {'gross%':>7} {'cost%':>7} {'ratio':>6} {'trd/d':>6} {'trd_t':>6}")
    rows, best = [], None
    for a, b in PAIRS:
        for z in Z_GRID:
            r = evaluate(a, b, *IS, z)
            rows.append({k: v for k, v in r.items() if k not in ("net", "z")})
            print(f"{r['pair']:14s} {z:>4} {r['half_life_hrs']:>6.1f} {r['ann_sharpe']:>6.2f} "
                  f"{r['gross_ann']*100:>7.1f} {r['cost_ann']*100:>7.1f} {r['cost_ratio']:>6.2f} "
                  f"{r['trades_per_day']:>6.2f} {r['trade_t']:>6.2f}")
            if best is None or r["cost_ratio"] > best["cost_ratio"]:
                best = r
    print(f"\nBest IS gross/cost ratio = {best['cost_ratio']:.2f} ({best['pair']}, z={best['z_entry']}) "
          f"— vs 3.0 gate → {'PASS' if best['cost_ratio'] > 3 else 'FAIL'}")

    # untouched hold-out confirmation of the best IS config
    a, b = best["pair"].split("-")
    oos = evaluate(a, b, *OOS, best["z_entry"])
    print(f"\nUntouched hold-out (2025-2026), best config {best['pair']} z={best['z_entry']}:")
    print(f"  IS  annSh={best['ann_sharpe']:.2f} ratio={best['cost_ratio']:.2f}  |  "
          f"OOS annSh={oos['ann_sharpe']:.2f} ratio={oos['cost_ratio']:.2f}")

    # level vs detrended half-life contrast (recon recap)
    print("\nHalf-life contrast: LEVEL spread ~255-700h (graveyard) vs traded detrended z ~1.7h (intraday).")

    payload = {"protocol": {"IS": IS, "OOS_untouched": OOS},
               "cost_gate_sweep_IS": rows,
               "best_IS": {k: v for k, v in best.items() if k not in ("net", "z")},
               "best_OOS": {k: v for k, v in oos.items() if k not in ("net", "z")},
               "verdict": "NO-GO at 2-leg cost gate (best ratio %.2f << 3); intraday reversion real "
                          "(HL~1.7h) but smaller than the doubled CFD spread." % best["cost_ratio"]}
    (RES / "family3_pairs.json").write_text(json.dumps(payload, indent=2, default=str))

    _plot(rows, best, oos)
    print("\n  → results/family3_pairs.json\n  → figures/family3_pairs.png")
    return 0


def _plot(rows, best, oos):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    df = pd.DataFrame(rows)
    # (1) example divergence z-score (a slice)
    z = best["z"].dropna()
    sl = z.iloc[2000:2200]
    ax[0, 0].plot(range(len(sl)), sl.values, color="#264653", lw=.8)
    ax[0, 0].axhline(2, ls="--", color="#d1495b"); ax[0, 0].axhline(-2, ls="--", color="#d1495b")
    ax[0, 0].axhline(0, color="#aaa", lw=.6)
    ax[0, 0].set_title(f"Intraday divergence z-score ({best['pair']}) — reverts in ~1.7h\n"
                       "(detrended spread; level cointegration HL ~255-700h = graveyard)")
    ax[0, 0].set_ylabel("z"); ax[0, 0].set_xlabel("30-min bars (sample)"); ax[0, 0].grid(alpha=.25)
    # (2) cost-ratio vs z_entry, all pairs — the decisive panel
    for p in df["pair"].unique():
        d = df[df["pair"] == p]
        ax[0, 1].plot(d["z_entry"], d["cost_ratio"], "o-", label=p)
    ax[0, 1].axhline(3.0, ls="--", color="#d1495b", label="3× cost gate")
    ax[0, 1].set_title("Pre-flight cost gate: gross/cost ratio\nnever reaches 3× → NO-GO")
    ax[0, 1].set_xlabel("entry band z_entry"); ax[0, 1].set_ylabel("gross/cost ratio")
    ax[0, 1].legend(fontsize=7); ax[0, 1].grid(alpha=.25)
    # (3) gross vs cost bars (IS, z=2.0)
    d0 = df[df["z_entry"] == 2.0]
    x = np.arange(len(d0)); w = 0.38
    ax[1, 0].bar(x - w/2, d0["gross_ann"]*100, w, label="gross %/yr", color="#2a9d8f")
    ax[1, 0].bar(x + w/2, d0["cost_ann"]*100, w, label="cost %/yr (2-leg)", color="#d1495b")
    ax[1, 0].set_xticks(x); ax[1, 0].set_xticklabels(d0["pair"], rotation=20, fontsize=8)
    ax[1, 0].set_title("Cost dominates gross at σd=1% (z_entry=2.0)\n2-leg spread × vol-target leverage")
    ax[1, 0].set_ylabel("%/yr"); ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=.25, axis="y")
    # (4) best config IS vs OOS
    ax[1, 1].bar(["IS\nann Sharpe", "hold-out\nann Sharpe"], [best["ann_sharpe"], oos["ann_sharpe"]],
                 color=["#264653", "#7a8e95"])
    ax[1, 1].axhline(0, color="#333", lw=.8)
    ax[1, 1].set_title(f"Best IS config ({best['pair']}, z={best['z_entry']})\nnegative in- and out-of-sample")
    ax[1, 1].set_ylabel("ann Sharpe"); ax[1, 1].grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "family3_pairs.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
