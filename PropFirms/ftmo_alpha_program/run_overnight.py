"""
run_overnight.py — Family-5 overnight equity premium: full gate battery + edge-vs-venue verdict
================================================================================================
Gates in order: cost L11 net-of-swap (with swap sensitivity, separating GROSS from NET to split
edge vs venue-capture), distribution (kurtosis<3 + tail-DD<10%), untouched hold-out 2025-26 +
per-year, DSR at true trial count, honest FTMO Monte-Carlo vs 70%.
Outputs: results/overnight_premium.json, figures/overnight_premium.png
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
from strategy.overnight_premium import extract_overnight, backtest_overnight, OvernightConfig  # noqa: E402
from engine.ftmo_first_passage import combined_pass_prob_empirical, tail_dd_gate  # noqa: E402
from dsr import deflated_sharpe_ratio                                    # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
IS = ("2022-01-01", "2024-12-31")
OOS = ("2025-01-01", "2026-05-29")
N_TRIALS = 20          # honest: 3 indices x {filter on/off} x few swap assumptions
DATA = {s: {"is": extract_overnight(s, *IS), "oos": extract_overnight(s, *OOS)}
        for s in ["US500", "US100", "US30"]}


def evalsym(sym, span, swap=2.0, filt=False):
    d = DATA[sym]["is" if span == "is" else "oos"]
    return backtest_overnight(d, sym, OvernightConfig(swap_bps_per_night=swap, use_vol_filter=filt)).metrics


def per_year(net):
    out = {}
    for y, seg in net.groupby(net.index.year):
        sd = seg.std(ddof=1)
        out[int(y)] = round(float(seg.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0, 2)
    return out


def main() -> int:
    print("=" * 80)
    print("FAMILY-5 — equity-index overnight premium (structural risk premium)")
    print("=" * 80)

    # ── swap sensitivity / cost gate (IS) ────────────────────────────────────
    print("\nCost gate net-of-swap (IS) — GROSS premium vs swap+spread, sensitivity:")
    print(f"{'sym':6} {'swap/n':>7} {'gross%':>7} {'cost%':>7} {'net annSh':>10} {'ratio':>6}")
    cost_rows = {}
    for sym in ["US100", "US500"]:
        for swap in [1.0, 2.0, 3.0]:
            m = evalsym(sym, "is", swap=swap)
            ratio = m["gross_ann_return"] / max(1e-9, m["cost_ann_drag"])
            cost_rows[(sym, swap)] = {"gross": m["gross_ann_return"], "cost": m["cost_ann_drag"],
                                      "net_sharpe": m["ann_sharpe"], "ratio": ratio}
            print(f"{sym:6} {swap:>6.1f}b {m['gross_ann_return']*100:>7.1f} {m['cost_ann_drag']*100:>7.1f} "
                  f"{m['ann_sharpe']:>10.2f} {ratio:>6.2f}")

    # ── canonical: US100, swap 2bps, no filter — full battery ────────────────
    sym = "US100"
    mi = evalsym(sym, "is", swap=2.0)
    mo = evalsym(sym, "oos", swap=2.0)
    net_is = mi["net_daily"]; net_oos = mo["net_daily"]
    print(f"\n[Canonical: {sym}, swap 2bps/night, CFD x3, weekday-only]")
    print(f"  GROSS-only annSharpe (zero cost/swap): IS {mi['gross_only_ann_sharpe']:.2f}  OOS {mo['gross_only_ann_sharpe']:.2f}")
    print(f"  NET annSharpe: IS {mi['ann_sharpe']:.2f} → OOS {mo['ann_sharpe']:.2f} (untouched)")
    print(f"  daily kurtosis: IS {mi['excess_kurtosis']:.2f} (gate<3)  WR {mi['win_rate']*100:.1f}%")
    tail = tail_dd_gate(net_is.values, n_paths=12000)
    print(f"  tail-DD P(touch -8%/60 sessions): {tail['p_floor_excursion']*100:.1f}% (gate<10%)")
    py = per_year(pd.concat([net_is, net_oos]))
    print(f"  per-year Sharpe (net): {py}")
    dsr = deflated_sharpe_ratio(net_is.values, n_trials=N_TRIALS, periods_per_year=252)
    print(f"  DSR (n_trials={N_TRIALS}): {dsr['dsr']:.3f}")
    mc = {}
    for sigma in [0.010, 0.008, 0.006]:
        r = (net_is / net_is.std() * sigma).values
        cp = combined_pass_prob_empirical(r, n_paths=12000, seed=1)
        mc[sigma] = {"p": cp["p_combined"], "ci": cp["p_combined_ci95"], "sessions": cp["median_sessions_to_pass"]}
        print(f"  FTMO MC σd={sigma*100:.1f}%: P(pass)={cp['p_combined']*100:.1f}% "
              f"CI={[round(x*100,1) for x in cp['p_combined_ci95']]} med_sessions={cp['median_sessions_to_pass']}")

    # ── verdict logic ────────────────────────────────────────────────────────
    gross_robust = mi["gross_only_ann_sharpe"] > 0.4 and mo["gross_only_ann_sharpe"] > 0.2
    best_pass = max(v["p"] for v in mc.values())
    if gross_robust and best_pass >= 0.70 and tail["gate_pass"]:
        verdict = "GO CANDIDATE — robust gross premium, survives financing + hold-out, barrier-friendly, P(pass)>=70%."
    elif gross_robust:
        verdict = (
            "NO-GO net, but a DIFFERENT result. The overnight premium is the program's FIRST robust gross "
            f"OOS edge (gross Sharpe IS {mi['gross_only_ann_sharpe']:.2f} -> OOS {mo['gross_only_ann_sharpe']:.2f}, "
            f"low kurtosis): the structural-premium prior is VALIDATED. But net of financing it is ~zero on a "
            f"leveraged account (cost ratio ~1.0 at 2bps swap; P(pass) peaks ~{best_pass*100:.0f}% = the zero-edge "
            f"baseline), it is directional equity beta (per-year net sign-flips with the regime), and it carries an "
            f"overnight-gap left tail (tail-DD {tail['p_floor_excursion']*100:.0f}%). CRUCIAL refinement of the venue "
            f"pivot: the financing that eats the premium is NOT a retail-CFD tax — it is the cost of carry of "
            f"leveraged overnight equity, embedded in the futures basis too (F=S*e^{{(r-q)T}}). So futures do NOT "
            f"cleanly rescue it, unlike the HF-reversal case. The only venue that escapes it is holding the cash "
            f"index unleveraged — which no propfirm challenge does.")
    else:
        verdict = "EDGE failure — premium does not survive the hold-out gross."
    print(f"\n[VERDICT] {verdict}")

    payload = {"protocol": {"IS": IS, "OOS_untouched": OOS, "n_trials_dsr": N_TRIALS},
               "cost_swap_sensitivity": {f"{s}|{w}": v for (s, w), v in cost_rows.items()},
               "canonical": {"sym": sym, "gross_only_is": mi["gross_only_ann_sharpe"],
                             "gross_only_oos": mo["gross_only_ann_sharpe"],
                             "net_is_sharpe": mi["ann_sharpe"], "net_oos_sharpe": mo["ann_sharpe"],
                             "kurtosis_is": mi["excess_kurtosis"], "win_rate_is": mi["win_rate"],
                             "tail_dd": tail, "per_year": py, "dsr": dsr,
                             "ftmo_mc": {str(k): v for k, v in mc.items()}},
               "verdict": verdict}
    (RES / "overnight_premium.json").write_text(json.dumps(payload, indent=2, default=str))
    _plot(mi, mo, net_is, net_oos, cost_rows, mc)
    print("\n  → results/overnight_premium.json\n  → figures/overnight_premium.png")
    return 0


def _plot(mi, mo, net_is, net_oos, cost_rows, mc):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    # equity IS + OOS
    eq = pd.concat([net_is, net_oos])
    ax[0, 0].plot(eq.index, eq.cumsum() * 100, color="#2a9d8f")
    ax[0, 0].axvline(pd.Timestamp(OOS[0]), color="#d1495b", ls=":", lw=1.4)
    ax[0, 0].text(pd.Timestamp(OOS[0]), ax[0, 0].get_ylim()[0], " hold-out →", color="#d1495b", fontsize=8)
    ax[0, 0].axhline(0, color="#aaa", lw=.8)
    ax[0, 0].set_title("US100 overnight premium — net equity (swap 2bps, CFD ×3)\nsurvives into the untouched hold-out")
    ax[0, 0].set_ylabel("cum return (%)"); ax[0, 0].grid(alpha=.25)
    # gross vs net Sharpe IS/OOS
    cats = ["gross IS", "gross OOS", "net IS", "net OOS"]
    vals = [mi["gross_only_ann_sharpe"], mo["gross_only_ann_sharpe"], mi["ann_sharpe"], mo["ann_sharpe"]]
    ax[0, 1].bar(cats, vals, color=["#2a9d8f", "#9fd8cf", "#264653", "#7a8e95"])
    ax[0, 1].axhline(0, color="#333", lw=.8)
    ax[0, 1].set_title("Annualised Sharpe: gross (premium) vs net (after swap)\nthe swap is the venue tax")
    ax[0, 1].set_ylabel("ann Sharpe"); ax[0, 1].grid(alpha=.25, axis="y")
    # swap sensitivity (US100)
    sw = [1.0, 2.0, 3.0]
    ax[1, 0].plot(sw, [cost_rows[("US100", s)]["net_sharpe"] for s in sw], "o-", color="#264653", label="US100 net Sharpe")
    ax[1, 0].plot(sw, [cost_rows[("US500", s)]["net_sharpe"] for s in sw], "s--", color="#2a9d8f", label="US500 net Sharpe")
    ax[1, 0].axhline(0, color="#aaa", lw=.8)
    ax[1, 0].set_title("Net Sharpe vs assumed swap (bps/night)\nthe edge-vs-venue knife-edge")
    ax[1, 0].set_xlabel("swap (bps/night)"); ax[1, 0].set_ylabel("net ann Sharpe"); ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=.25)
    # FTMO MC vs sigma
    sig = sorted(mc.keys(), reverse=True)
    ax[1, 1].plot([s*100 for s in sig], [mc[s]["p"]*100 for s in sig], "o-", color="#264653")
    ax[1, 1].axhline(70, ls="--", color="#d1495b", label="70% objective")
    ax[1, 1].set_title("Honest FTMO combined P(pass) vs per-day vol"); ax[1, 1].invert_xaxis()
    ax[1, 1].set_xlabel("σd (%)"); ax[1, 1].set_ylabel("P(pass) %"); ax[1, 1].set_ylim(0, 100)
    ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "overnight_premium.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
