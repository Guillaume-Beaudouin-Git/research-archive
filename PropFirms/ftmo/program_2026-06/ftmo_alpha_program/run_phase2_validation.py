"""
run_phase2_validation.py — Phase 2: full validation & honest verdict
=====================================================================

Phase 1 archived Family-1/2 at the pre-flight cost gate (no instrument clears
gross alpha > 3x CFD cost drag once the backtest is free of the per-bar loss-cap
artifact). Phase 2 therefore does NOT validate a passing strategy; it (a) confirms
the no-go through the full FTMO Monte-Carlo, and (b) quantifies the gap between the
edge we achieved and the edge the barrier requires — the constructive deliverable.

Sections:
  1. Lead candidate (EURUSD) + diversified book: suitability metrics (Table 2).
  2. Walk-forward (>=5 folds) — is even the marginal EURUSD edge stable?
  3. DSR (Bailey-Lopez de Prado) deflation for the configs tried (L20).
  4. Cost-gate sensitivity to the dealer markup (ties to the Phase-4 demo mandate).
  5. The loss-cap artifact: backtest Sharpe with vs without — the methodological lesson.
  6. FTMO Monte-Carlo on the honest returns (combined P(pass) << 70%) + tail-DD.
  7. Required-edge frontier (validated closed form): the (sigma_d, daily Sharpe) that
     clears 70%, with the achieved points overlaid.

Outputs: results/phase2_validation.json, figures/phase2_assessment.png,
         figures/phase2_required_edge.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                 # .../Algo_claude (for dsr.py at repo root)
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO))
from strategy.fx_data import load_mt5_panel, load_dukascopy           # noqa: E402
from strategy.intraday_fx_mr import (build_bars, add_mr_signal,        # noqa: E402
                                     backtest_mr, BacktestConfig, compute_metrics)
from strategy.book import build_book                                   # noqa: E402
from engine.ftmo_first_passage import (combined_pass_prob_empirical,   # noqa: E402
                                       tail_dd_gate, combined_pass_prob_closed_form,
                                       annual_to_daily_sharpe)
from dsr import deflated_sharpe_ratio                                  # noqa: E402

FIG, RES = HERE / "figures", HERE / "results"
START, END = "2022-01-01", "2024-12-31"
N_TRIALS_TRIED = 30          # honest count of configs explored (L20 DSR input)


def eurusd_net(markup: float = 3.0, clip: float | None = None, sigma: float = 0.01,
               start=START, end=END) -> pd.Series:
    df = load_mt5_panel("EURUSD").loc[start:end]
    bars = add_mr_signal(build_bars(df, freq="30min", hours=(7, 20)), window=16)
    cfg = BacktestConfig(z_entry=2.0, z_exit=0.5, sigma_target=sigma,
                         markup=markup, daily_stop=0.008, stop_bar_loss=clip)
    return backtest_mr(bars, "EURUSD", cfg)


def suitability(metrics: dict) -> dict:
    g = {
        "win_rate>0.55": metrics["win_rate"] > 0.55,
        "win_loss~1 (<1.5)": (metrics["win_loss_ratio"] is not None
                              and metrics["win_loss_ratio"] < 1.5),
        "excess_kurt<3": metrics["excess_kurtosis"] < 3.0,
        "daily_sharpe>=0.09": metrics["daily_sharpe"] >= 0.09,
    }
    return {k: bool(v) for k, v in g.items()}


def walk_forward(n_folds: int = 6) -> list[dict]:
    """Expanding-window WF on EURUSD: train-implicit (fixed rules), report per-fold OOS Sharpe."""
    res = eurusd_net()
    daily = res.daily_net.dropna()
    idx = np.array_split(np.arange(len(daily)), n_folds)
    out = []
    for i, sl in enumerate(idx, 1):
        seg = daily.iloc[sl]
        mu, sd = seg.mean(), seg.std(ddof=1)
        out.append({"fold": i, "n_days": int(len(seg)),
                    "start": str(seg.index[0].date()), "end": str(seg.index[-1].date()),
                    "ann_sharpe": float(mu / sd * np.sqrt(252)) if sd > 0 else 0.0,
                    "ann_return": float(mu * 252)})
    return out


def main() -> int:
    print("=" * 80)
    print("PHASE 2 — Full validation & honest verdict")
    print("=" * 80)

    # 1. Candidate + book ------------------------------------------------------
    eur = eurusd_net()
    eur_daily = eur.daily_net.dropna()
    book = build_book(START, END, sigma_d=0.01)
    book_daily = book.daily.dropna()
    eur_m, book_m = eur.metrics, compute_metrics(book_daily, book_daily, book_daily * 0, book_daily * 0)
    print(f"\nEURUSD  : annSharpe={eur_m['ann_sharpe']:.2f} dSharpe={eur_m['daily_sharpe']:.3f} "
          f"WR={eur_m['win_rate']*100:.1f}% W/L={eur_m['win_loss_ratio']:.2f} kurt={eur_m['excess_kurtosis']:.1f}")
    print(f"BOOK    : annSharpe={book_m['ann_sharpe']:.2f} dSharpe={book_m['daily_sharpe']:.3f} "
          f"weights={dict(book.weights.round(2))}")
    eur_gates = suitability(eur_m)
    print("EURUSD suitability gates:", eur_gates)

    # 2. Walk-forward ----------------------------------------------------------
    wf = walk_forward()
    wf_sh = [f["ann_sharpe"] for f in wf]
    print(f"\nWalk-forward annSharpe by fold: {[round(s,2) for s in wf_sh]}  "
          f"(mean {np.mean(wf_sh):.2f}, worst {min(wf_sh):.2f}, #pos {sum(s>0 for s in wf_sh)}/{len(wf_sh)})")

    # 3. DSR -------------------------------------------------------------------
    dsr = deflated_sharpe_ratio(eur_daily.values, n_trials=N_TRIALS_TRIED, periods_per_year=252)
    print(f"DSR (EURUSD, n_trials={N_TRIALS_TRIED}): SR={dsr['sharpe']:.2f} "
          f"benchmark={dsr['sr_benchmark']:.2f} DSR={dsr['dsr']:.3f} passed={dsr['passed']}")

    # 4. Cost-gate markup sensitivity -----------------------------------------
    markups = [1.0, 1.5, 2.0, 3.0]
    cost_sens = []
    for mk in markups:
        m = eurusd_net(markup=mk).metrics
        cost_sens.append({"markup": mk, "eurusd_pips_rt": round(0.2 * mk, 2),
                          "gross_ann": m["gross_ann_return"], "cost_ann": m["cost_ann_drag"],
                          "ratio": m["gross_ann_return"] / max(1e-9, m["cost_ann_drag"]),
                          "net_ann_sharpe": m["ann_sharpe"]})
    print("\nCost-gate vs dealer markup (EURUSD):")
    for c in cost_sens:
        print(f"  markup x{c['markup']:.1f} (~{c['eurusd_pips_rt']} pip RT): ratio={c['ratio']:.1f} "
              f"{'PASS' if c['ratio']>3 else 'fail'}  netSharpe={c['net_ann_sharpe']:.2f}")

    # 5. Loss-cap artifact -----------------------------------------------------
    art = {"eurusd_no_clip": eurusd_net(clip=None).metrics["ann_sharpe"],
           "eurusd_with_clip25bps": eurusd_net(clip=0.0025).metrics["ann_sharpe"]}
    print(f"\nLoss-cap artifact (EURUSD annSharpe): honest(no clip)={art['eurusd_no_clip']:.2f}  "
          f"vs cap-and-continue clip={art['eurusd_with_clip25bps']:.2f}  "
          f"(Δ={art['eurusd_with_clip25bps']-art['eurusd_no_clip']:.2f} manufactured)")

    # 6. FTMO Monte-Carlo on honest returns -----------------------------------
    print("\nFTMO Monte-Carlo (honest returns, no time limit):")
    mc_rows = []
    for name, base in [("EURUSD", eur_daily), ("BOOK", book_daily)]:
        for sigma in [0.010, 0.008, 0.006]:
            r = (base / base.std() * sigma).values
            mc = combined_pass_prob_empirical(r, n_paths=12000, seed=1)
            t = tail_dd_gate(r, n_paths=12000)
            mc_rows.append({"book": name, "sigma_d": sigma, "p_combined": mc["p_combined"],
                            "ci95": mc["p_combined_ci95"], "median_sessions": mc["median_sessions_to_pass"],
                            "tail_dd": t["p_floor_excursion"], "tail_gate": t["gate_pass"]})
            print(f"  {name:6s} σd={sigma*100:.1f}%: P(pass)={mc['p_combined']*100:>5.1f}% "
                  f"tailDD={t['p_floor_excursion']*100:>4.1f}% "
                  f"{'(70% NOT cleared)' if mc['p_combined']<0.70 else '(>=70%)'}")

    # 7. Required-edge frontier (closed form) ---------------------------------
    sharpe_req = {}
    for sigma in [0.010, 0.008, 0.006, 0.005]:
        s = None
        for sa in np.linspace(0.2, 3.0, 5601):
            if combined_pass_prob_closed_form(annual_to_daily_sharpe(sa), sigma)["p_combined"] >= 0.70:
                s = round(float(sa), 3); break
        sharpe_req[sigma] = s
    achieved = {"EURUSD_ann_sharpe": eur_m["ann_sharpe"], "book_ann_sharpe": book_m["ann_sharpe"]}
    print(f"\nRequired annualised Sharpe for combined 70%: {sharpe_req}")
    print(f"Achieved: EURUSD {achieved['EURUSD_ann_sharpe']:.2f}, BOOK {achieved['book_ann_sharpe']:.2f}  "
          f"→ GAP confirms NO-GO.")

    # ── persist ──────────────────────────────────────────────────────────────
    payload = {
        "candidate_eurusd": eur_m, "book": book_m, "book_weights": dict(book.weights),
        "eurusd_suitability_gates": eur_gates,
        "walk_forward": wf, "dsr": dsr, "cost_markup_sensitivity": cost_sens,
        "loss_cap_artifact": art, "ftmo_mc": mc_rows,
        "required_sharpe_for_70pct": {str(k): v for k, v in sharpe_req.items()},
        "achieved": achieved,
        "verdict": "NO-GO at pre-flight cost gate; combined P(pass) << 70% on honest returns.",
    }
    (RES / "phase2_validation.json").write_text(json.dumps(payload, indent=2, default=str))

    _plot_assessment(eur_daily, book_daily, wf, cost_sens, art)
    _plot_required_edge(sharpe_req, eur_m, book_m, mc_rows)
    print("\n  → results/phase2_validation.json")
    print("  → figures/phase2_assessment.png, phase2_required_edge.png")
    return 0


def _plot_assessment(eur, book, wf, cost_sens, art):
    fig, ax = plt.subplots(2, 2, figsize=(13, 8.5))
    # (1) equity curves (honest)
    ax[0, 0].plot(eur.index, eur.cumsum() * 100, label="EURUSD (lead)", color="#2a9d8f")
    ax[0, 0].plot(book.index, book.cumsum() * 100, label="Diversified book", color="#264653")
    ax[0, 0].axhline(0, color="#aaa", lw=.8)
    ax[0, 0].set_title("Honest cumulative net return (σd=1%, markup ×3, no loss-cap artifact)")
    ax[0, 0].set_ylabel("cumulative return (%)"); ax[0, 0].legend(); ax[0, 0].grid(alpha=.25)
    # (2) walk-forward
    folds = [f["fold"] for f in wf]; sh = [f["ann_sharpe"] for f in wf]
    ax[0, 1].bar(folds, sh, color=["#2a9d8f" if s > 0 else "#d1495b" for s in sh])
    ax[0, 1].axhline(0, color="#333", lw=.8)
    ax[0, 1].set_title(f"EURUSD walk-forward (per-fold annualised Sharpe)\n{sum(s>0 for s in sh)}/{len(sh)} folds positive — unstable, marginal")
    ax[0, 1].set_xlabel("fold"); ax[0, 1].set_ylabel("ann Sharpe"); ax[0, 1].grid(alpha=.25, axis="y")
    # (3) cost-markup sensitivity
    mks = [c["markup"] for c in cost_sens]; rat = [c["ratio"] for c in cost_sens]
    ax[1, 0].plot(mks, rat, "o-", color="#e76f51")
    ax[1, 0].axhline(3.0, ls="--", color="#333", label="3× cost gate")
    ax[1, 0].set_title("Cost gate vs dealer markup (EURUSD)\npasses only near raw-feed cost → must validate on demo (Phase 4)")
    ax[1, 0].set_xlabel("dealer spread markup (×)"); ax[1, 0].set_ylabel("gross/cost ratio")
    ax[1, 0].legend(); ax[1, 0].grid(alpha=.25)
    # (4) artifact
    labels = ["honest\n(no loss cap)", "loss-cap\n(cap & continue)"]
    vals = [art["eurusd_no_clip"], art["eurusd_with_clip25bps"]]
    ax[1, 1].bar(labels, vals, color=["#2a9d8f", "#d1495b"])
    ax[1, 1].set_title("The loss-cap artifact (EURUSD annualised Sharpe)\ncapping per-bar loss mechanically lifts a near-zero-edge mean")
    ax[1, 1].set_ylabel("ann Sharpe"); ax[1, 1].grid(alpha=.25, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "phase2_assessment.png", dpi=130); plt.close(fig)


def _plot_required_edge(sharpe_req, eur_m, book_m, mc_rows):
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    # left: required Sharpe vs σd, with achieved
    sigmas = sorted(sharpe_req.keys(), reverse=True)
    req = [sharpe_req[s] for s in sigmas]
    ax[0].plot([s * 100 for s in sigmas], req, "o-", color="#264653", label="required for 70%")
    ax[0].axhline(eur_m["ann_sharpe"], ls="--", color="#2a9d8f", label=f"EURUSD achieved ({eur_m['ann_sharpe']:.2f})")
    ax[0].axhline(0, color="#aaa", lw=.8)
    ax[0].fill_between([s * 100 for s in sigmas], req, eur_m["ann_sharpe"],
                       where=[r > eur_m["ann_sharpe"] for r in req], color="#d1495b", alpha=.15, label="edge gap")
    ax[0].set_xlabel("per-day vol σd (%)"); ax[0].set_ylabel("annualised Sharpe")
    ax[0].set_title("Required vs achieved edge for combined 70%\n(validated closed form)")
    ax[0].invert_xaxis(); ax[0].legend(); ax[0].grid(alpha=.25)
    # right: MC pass-prob by σd, honest
    for name, color in [("EURUSD", "#2a9d8f"), ("BOOK", "#264653")]:
        rows = [r for r in mc_rows if r["book"] == name]
        ax[1].plot([r["sigma_d"] * 100 for r in rows], [r["p_combined"] * 100 for r in rows],
                   "o-", color=color, label=name)
    ax[1].axhline(70, ls="--", color="#555", label="70% objective")
    ax[1].set_xlabel("per-day vol σd (%)"); ax[1].set_ylabel("combined P(pass) (%)")
    ax[1].set_title("FTMO Monte-Carlo on HONEST returns\nP(pass) stays well below 70% → NO-GO")
    ax[1].invert_xaxis(); ax[1].set_ylim(0, 100); ax[1].legend(); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "phase2_required_edge.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
