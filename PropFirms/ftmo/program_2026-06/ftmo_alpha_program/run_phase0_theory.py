"""
run_phase0_theory.py — Phase 0 go/no-go gate: "simulator reproduces a known case"
==================================================================================

Three deliverables (white paper §3, Table 1, Fig. 1):

  1. Reproduce Table 1 — single-phase pass-probability P = 1/(1+e^{-2 Sd n}) for the
     symmetric 10%/10% barrier, over (annualised Sharpe) x (per-day vol).
  2. VALIDATE the Monte-Carlo against the closed form across a grid of (Sd, n).
     This is the Phase-0 gate; we assert max abs error < tol.
  3. Reproduce Figure 1 — combined two-phase pass-prob vs annualised Sharpe for
     three per-day volatility levels, no time limit, marking the 70% objective.

Outputs:
  results/phase0_theory.json
  figures/phase0_table1.png
  figures/phase0_validation.png
  figures/phase0_figure1_combined.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine.ftmo_first_passage import (   # noqa: E402
    pass_prob_closed_form, combined_pass_prob_closed_form,
    simulate_bm_first_passage, annual_to_daily_sharpe,
    FTMO_MAX_DD_PCT, FTMO_P1_TGT_PCT, FTMO_P2_TGT_PCT,
)

FIG = HERE / "figures"
RES = HERE / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

SHARPES = [0.48, 0.95, 1.43, 1.90]
SIGMAS = [0.02, 0.01, 0.005]          # σd → n = 0.10/σd = {5, 10, 20}
N_OF_SIGMA = {s: FTMO_MAX_DD_PCT / s for s in SIGMAS}


# ── 1. Table 1 ────────────────────────────────────────────────────────────────
def reproduce_table1() -> dict:
    table = {}
    for sa in SHARPES:
        Sd = annual_to_daily_sharpe(sa)
        row = {}
        for s in SIGMAS:
            n = N_OF_SIGMA[s]
            row[f"sigma_{s}"] = round(pass_prob_closed_form(Sd, n), 3)
        table[f"sharpe_{sa}"] = row
    return table


# ── 2. Validation: MC vs closed form ────────────────────────────────────────
def validate_simulator(tol: float = 0.012) -> dict:
    """Run the fine-grid BM sim across (Sd_annual, n) and compare to closed form."""
    rows = []
    max_err = 0.0
    for sa in SHARPES:
        Sd = annual_to_daily_sharpe(sa)
        for s in SIGMAS:
            n = N_OF_SIGMA[s]
            cf = pass_prob_closed_form(Sd, n)
            mc = simulate_bm_first_passage(
                daily_sharpe=Sd, sigma_d=s, max_dd=FTMO_MAX_DD_PCT,
                target=FTMO_P1_TGT_PCT, n_paths=40_000, max_days=None,
                substeps=40, seed=11)
            err = abs(mc["p_pass"] - cf)
            max_err = max(max_err, err)
            rows.append({"sharpe_ann": sa, "sigma_d": s, "n": n,
                         "closed_form": round(cf, 4),
                         "monte_carlo": round(mc["p_pass"], 4),
                         "abs_err": round(err, 4),
                         "mc_median_days": mc["median_days_to_pass"]})
    return {"rows": rows, "max_abs_err": round(max_err, 4),
            "tol": tol, "gate_pass": bool(max_err < tol)}


# ── 3. Figure 1 ──────────────────────────────────────────────────────────────
def reproduce_figure1(sharpe_grid: np.ndarray) -> dict:
    curves = {}
    for s in SIGMAS:
        ys = [combined_pass_prob_closed_form(annual_to_daily_sharpe(sa), s)["p_combined"]
              for sa in sharpe_grid]
        curves[s] = ys
    # Sharpe that clears 70% at σd = 1%
    s_ref = 0.01
    cross = None
    for sa in np.linspace(0.5, 2.5, 4001):
        if combined_pass_prob_closed_form(annual_to_daily_sharpe(sa), s_ref)["p_combined"] >= 0.70:
            cross = round(float(sa), 3)
            break
    return {"curves": {str(k): v for k, v in curves.items()},
            "sharpe_70pct_at_sigma1pct": cross}


def plot_table1(table: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.axis("off")
    col_labels = [f"σd={int(s*1000)/10:g}% (n={int(N_OF_SIGMA[s])})" for s in SIGMAS]
    row_labels = [f"{sa:.2f}" for sa in SHARPES]
    cells = [[f"{table[f'sharpe_{sa}'][f'sigma_{s}']:.3f}" for s in SIGMAS]
             for sa in SHARPES]
    t = ax.table(cellText=cells, rowLabels=row_labels, colLabels=col_labels,
                 cellLoc="center", loc="center")
    t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 1.5)
    for j in range(len(SIGMAS)):                       # shade the grind column n=20
        if SIGMAS[j] == 0.005:
            for i in range(len(SHARPES) + 1):
                t[(i, j)].set_facecolor("#e6f2ea")
    ax.set_title("Table 1 — single-phase pass-probability  P = 1/(1+e^{-2 Sₐ n})\n"
                 "symmetric 10%/10% barrier (rows: annualised Sharpe)", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "phase0_table1.png", dpi=130)
    plt.close(fig)


def plot_validation(val: dict) -> None:
    cf = [r["closed_form"] for r in val["rows"]]
    mc = [r["monte_carlo"] for r in val["rows"]]
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.scatter(cf, mc, s=46, c="#2a6f97", edgecolor="white", zorder=3)
    ax.plot([0, 1], [0, 1], "--", color="#888", lw=1)
    ax.set_xlabel("Closed-form  P(pass)"); ax.set_ylabel("Monte-Carlo  P(pass)")
    ax.set_title(f"Phase-0 gate: simulator vs closed form\n"
                 f"max abs error = {val['max_abs_err']:.4f}  "
                 f"({'PASS' if val['gate_pass'] else 'FAIL'} @ tol {val['tol']})")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(FIG / "phase0_validation.png", dpi=130)
    plt.close(fig)


def plot_figure1(grid: np.ndarray, fig1: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    colors = {0.02: "#d1495b", 0.01: "#2a9d8f", 0.005: "#264653"}
    for s in SIGMAS:
        ax.plot(grid, np.array(fig1["curves"][str(s)]) * 100,
                color=colors[s], lw=2.2,
                label=f"σd = {s*100:g}%  (n = {int(N_OF_SIGMA[s])})")
    ax.axhline(70, ls="--", color="#555", lw=1.2)
    ax.text(0.52, 71.5, "70% objective", fontsize=9, color="#555")
    if fig1["sharpe_70pct_at_sigma1pct"]:
        xc = fig1["sharpe_70pct_at_sigma1pct"]
        ax.axvline(xc, ls=":", color="#2a9d8f", lw=1.2)
        ax.text(xc + 0.02, 12, f"Sharpe ≈ {xc}\nclears 70% @ σd=1%",
                fontsize=8.5, color="#2a9d8f")
    ax.axvspan(0.5, 1.0, color="#f2f2f2", zorder=0)
    ax.set_xlabel("Annualised Sharpe ratio"); ax.set_ylabel("Combined P(pass), two phases (%)")
    ax.set_title("Figure 1 — combined two-phase pass-probability vs Sharpe\n"
                 "FTMO symmetric 10/10 (P1) + 5/10 (P2), no time limit")
    ax.set_xlim(0.5, 2.5); ax.set_ylim(0, 100); ax.grid(alpha=.25); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / "phase0_figure1_combined.png", dpi=130)
    plt.close(fig)


def main() -> int:
    print("=" * 74)
    print("PHASE 0 — First-passage theory validation (go/no-go gate)")
    print("=" * 74)

    table1 = reproduce_table1()
    print("\nTable 1 (closed form):")
    print(f"{'Sharpe':>8} | " + " | ".join(f"σd={s*100:g}% (n={int(N_OF_SIGMA[s])})" for s in SIGMAS))
    for sa in SHARPES:
        print(f"{sa:>8.2f} | " + " | ".join(
            f"{table1[f'sharpe_{sa}'][f'sigma_{s}']:>11.3f}" for s in SIGMAS))

    print("\nValidation — Monte-Carlo vs closed form:")
    val = validate_simulator()
    for r in val["rows"]:
        print(f"  Sₐ={r['sharpe_ann']:.2f} σd={r['sigma_d']*100:>4.1f}% n={r['n']:>4.0f} | "
              f"CF={r['closed_form']:.4f}  MC={r['monte_carlo']:.4f}  |Δ|={r['abs_err']:.4f}")
    print(f"\n  max |Δ| = {val['max_abs_err']:.4f}  →  "
          f"GATE {'PASS ✓' if val['gate_pass'] else 'FAIL ✗'} (tol {val['tol']})")

    grid = np.linspace(0.5, 2.5, 81)
    fig1 = reproduce_figure1(grid)
    print(f"\nFigure 1: combined 70% cleared at annualised Sharpe ≈ "
          f"{fig1['sharpe_70pct_at_sigma1pct']} when σd = 1% (n = 10).")

    plot_table1(table1); plot_validation(val); plot_figure1(grid, fig1)
    out = {"table1_closed_form": table1, "validation": val,
           "figure1": {"sharpe_70pct_at_sigma1pct": fig1["sharpe_70pct_at_sigma1pct"]},
           "params": {"max_dd": FTMO_MAX_DD_PCT, "p1_tgt": FTMO_P1_TGT_PCT,
                      "p2_tgt": FTMO_P2_TGT_PCT}}
    (RES / "phase0_theory.json").write_text(json.dumps(out, indent=2))
    print(f"\n  → results/phase0_theory.json")
    print(f"  → figures/phase0_table1.png, phase0_validation.png, phase0_figure1_combined.png")
    return 0 if val["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
