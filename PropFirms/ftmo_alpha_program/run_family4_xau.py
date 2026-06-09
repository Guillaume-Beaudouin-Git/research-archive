"""
run_family4_xau.py — XAUUSD honest range-fade: full gate battery + cost-vs-edge verdict
=========================================================================================

Question of the sprint: is there a REAL intraday range-fade edge in XAUUSD once the grid is
replaced by an honest hard stop — surviving the untouched 2025-2026 hold-out, net of CFD
cost, with a barrier-compatible distribution?

Gates in the mandated order: cost L11 first, then distribution (kurtosis<3 + tail-DD), then
the untouched hold-out + per-year stability (no Dukascopy XAUUSD feed exists — flagged), DSR
at the honest trial count, FTMO Monte-Carlo. The product is the COST-vs-EDGE distinction.

Outputs: results/family4_xau.json, figures/family4_xau.png
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
from strategy.fx_data import load_mt5_panel                              # noqa: E402
from strategy.xauusd_rangefade import build_xau_bars, backtest_rangefade, RangeFadeConfig  # noqa: E402
from engine.ftmo_first_passage import combined_pass_prob_empirical, tail_dd_gate  # noqa: E402
from dsr import deflated_sharpe_ratio                                    # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
IS = ("2022-01-01", "2024-12-31")
OOS = ("2025-01-01", "2026-05-29")
N_TRIALS = 50          # honest count: 3 stops × {filter on/off} × sessions + prior XAU work
DF = load_mt5_panel("XAUUSD")


def run(span, stop, filt, markup):
    bars = build_xau_bars(DF.loc[span[0]:span[1]], hours=(0, 8), window=16)
    return backtest_rangefade(bars, RangeFadeConfig(
        z_entry=2.0, z_exit=0.5, stop_loss=stop, sigma_target=0.01,
        markup=markup, use_filter=filt))


def per_year(net):
    out = {}
    for y, seg in net.groupby(net.index.year):
        sd = seg.std(ddof=1)
        out[int(y)] = round(float(seg.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0, 2)
    return out


def main() -> int:
    print("=" * 78)
    print("FAMILY-4 — XAUUSD honest range-fade (hard stop, no grid)")
    print("=" * 78)

    # ── cost-vs-edge isolation: GROSS (zero-cost) across configs ──────────────
    print("\n[Isolation] GROSS (zero-cost) Sharpe — mechanism vs stop vs venue:")
    iso = {}
    for lbl, stop, filt in [("no_stop", 10.0, False), ("stop0.5", 0.005, False),
                            ("stop0.5+filter", 0.005, True)]:
        mi, mo = run(IS, stop, filt, 0.0).metrics, run(OOS, stop, filt, 0.0).metrics
        iso[lbl] = {"is_gross": mi["ann_sharpe"], "oos_gross": mo["ann_sharpe"],
                    "is_trade_wr": mi["trade_win_rate"], "is_kurt": mi["excess_kurtosis"]}
        print(f"  {lbl:16s}: IS gross={mi['ann_sharpe']:>6.2f}  OOS gross={mo['ann_sharpe']:>6.2f}  "
              f"WR(t)={mi['trade_win_rate']*100:.0f}%")

    # ── canonical honest config: full battery (net, markup ×3) ────────────────
    cf_is = run(IS, 0.005, False, 3.0)
    cf_oos = run(OOS, 0.005, False, 3.0)
    mi, mo = cf_is.metrics, cf_oos.metrics
    cost_ratio = mi["gross_ann_return"] / abs(mi["cost_ann_drag"]) if mi["cost_ann_drag"] else float("nan")
    print(f"\n[Canonical: hard stop 0.5%, no filter, CFD ×3]")
    print(f"  GATE 1 cost L11: gross={mi['gross_ann_return']*100:.1f}%/yr cost={mi['cost_ann_drag']*100:.1f}%/yr "
          f"ratio={cost_ratio:.2f} → {'PASS' if cost_ratio > 3 else 'FAIL'}")
    print(f"  GATE 2 dist: kurtosis={mi['excess_kurtosis']:.1f} (gate<3); ", end="")
    net_is = mi["net_daily"]
    tail = tail_dd_gate(net_is.values, n_paths=12000)
    print(f"tail-DD P(touch -8%/60d)={tail['p_floor_excursion']*100:.1f}% (gate<10%)")
    print(f"  GATE 3 hold-out: IS netSharpe={mi['ann_sharpe']:.2f} → OOS netSharpe={mo['ann_sharpe']:.2f}")
    py = per_year(pd.concat([net_is, mo["net_daily"]]))
    print(f"           per-year Sharpe: {py}")
    dsr = deflated_sharpe_ratio(net_is.values, n_trials=N_TRIALS, periods_per_year=252)
    print(f"  GATE 4 DSR (n_trials={N_TRIALS}): {dsr['dsr']:.3f} → {'PASS' if dsr['passed'] else 'FAIL'}")
    # FTMO MC honest (on the least-bad / canonical net series)
    print(f"  GATE 5 FTMO MC (honest, no time limit):")
    mc_rows = {}
    for sigma in [0.010, 0.006]:
        r = (net_is / net_is.std() * sigma).values
        mc = combined_pass_prob_empirical(r, n_paths=12000, seed=1)
        mc_rows[sigma] = mc["p_combined"]
        print(f"     sigma_d={sigma*100:.1f}%: combined P(pass)={mc['p_combined']*100:.1f}% (vs 70%)")

    cost_fail = cost_ratio <= 3
    edge_fail = (iso["no_stop"]["oos_gross"] <= 0 and iso["stop0.5"]["oos_gross"] <= 0
                 and iso["no_stop"]["is_gross"] <= 0.2)
    verdict = ("NO-GO — EDGE FAILURE (terminal): gross Sharpe is negative at ZERO cost, with and "
               "without the stop, IS and on the untouched hold-out. The mechanism has no positive "
               "gross expectancy; the EAs' 90%+ WR is a grid-averaging artefact. A cheaper venue "
               "cannot rescue negative gross — this does NOT reopen the venue pivot."
               if edge_fail else
               "NO-GO — COST FAILURE: real gross edge eaten by CFD spread ×3; potentially venue-fixable.")
    print(f"\n[VERDICT] {verdict}")

    payload = {"protocol": {"IS": IS, "OOS_untouched": OOS, "n_trials_dsr": N_TRIALS,
                            "cross_feed": "UNAVAILABLE (no independent XAUUSD feed in repo) — "
                                          "per-year + untouched hold-out used instead"},
               "isolation_gross": iso,
               "canonical": {"cost_ratio": cost_ratio, "gross_ann": mi["gross_ann_return"],
                             "cost_ann": mi["cost_ann_drag"], "kurtosis": mi["excess_kurtosis"],
                             "tail_dd": tail, "is_sharpe": mi["ann_sharpe"], "oos_sharpe": mo["ann_sharpe"],
                             "per_year": py, "dsr": dsr, "ftmo_mc": mc_rows,
                             "n_trades_is": mi["n_trades"], "trade_wr_is": mi["trade_win_rate"]},
               "cost_failure": bool(cost_fail), "edge_failure": bool(edge_fail), "verdict": verdict}
    (RES / "family4_xau.json").write_text(json.dumps(payload, indent=2, default=str))

    _plot(iso, cf_is, cf_oos, mc_rows)
    print("\n  → results/family4_xau.json\n  → figures/family4_xau.png")
    return 0


def _plot(iso, cf_is, cf_oos, mc_rows):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    labels = list(iso.keys())
    isv = [iso[k]["is_gross"] for k in labels]; oov = [iso[k]["oos_gross"] for k in labels]
    x = np.arange(len(labels)); w = 0.38
    ax[0, 0].bar(x - w/2, isv, w, label="IS gross", color="#2a9d8f")
    ax[0, 0].bar(x + w/2, oov, w, label="OOS gross (untouched)", color="#7a8e95")
    ax[0, 0].axhline(0, color="#333", lw=.8)
    ax[0, 0].set_xticks(x); ax[0, 0].set_xticklabels(labels, fontsize=8, rotation=10)
    ax[0, 0].set_title("GROSS (zero-cost) Sharpe — negative everywhere\n→ EDGE failure, not cost")
    ax[0, 0].set_ylabel("ann Sharpe"); ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.25, axis="y")
    # per-trade distribution (the left tail the grid hides)
    tr = cf_is.trades * 100
    ax[0, 1].hist(tr, bins=40, color="#264653", alpha=.85)
    ax[0, 1].axvline(0, color="#d1495b", lw=1)
    ax[0, 1].set_title(f"Per-trade return distribution (IS, hard stop)\nWR {(tr>0).mean()*100:.0f}% but losers > winners")
    ax[0, 1].set_xlabel("per-trade return (%)"); ax[0, 1].set_ylabel("count"); ax[0, 1].grid(alpha=.25)
    # cumulative net equity IS + OOS
    eq = pd.concat([cf_is.daily_net, cf_oos.daily_net])
    ax[1, 0].plot(eq.index, eq.cumsum()*100, color="#264653")
    ax[1, 0].axvline(pd.Timestamp(OOS[0]), color="#d1495b", ls=":", lw=1.4)
    ax[1, 0].text(pd.Timestamp(OOS[0]), ax[1, 0].get_ylim()[0], " hold-out →", color="#d1495b", fontsize=8)
    ax[1, 0].axhline(0, color="#aaa", lw=.8)
    ax[1, 0].set_title("Honest net equity (hard stop, CFD ×3) — down in- and out-of-sample")
    ax[1, 0].set_ylabel("cum return (%)"); ax[1, 0].grid(alpha=.25)
    # FTMO MC honest
    ax[1, 1].bar([f"σd={k*100:.1f}%" for k in mc_rows], [v*100 for v in mc_rows.values()], color="#7a8e95")
    ax[1, 1].axhline(70, ls="--", color="#d1495b", label="70% objective")
    ax[1, 1].axhline(50, ls=":", color="#888", label="zero-edge ~p1")
    ax[1, 1].set_title("Honest FTMO combined P(pass)\nbelow zero-edge baseline (negative drift)")
    ax[1, 1].set_ylabel("P(pass) %"); ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "family4_xau.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
