"""
mc_sizing_vs_time.py — Sizing scan vs time-to-pass for iter_10.
================================================================
Scan: 8 sizings (1→15 MNQ) × 6 time caps (7→180d).
Generator: make_iter10_trade_generator (CRN seed=42 per sizing).
Simulator: trailing_dd_simulator.py (unmodified).
Config: Tradeify Select Flex $25K — eval_DD=$1,000, target=$1,500.

N = 20,000 runs per sizing.  Baseline only (no stress slippage/vol).

Note on NQ/MNQ ratio: 1 NQ = $20/pt, 1 MNQ = $2/pt → 1 NQ ≡ 10 MNQ in P&L.
  "1 NQ + 5 MNQ" = 15 MNQ equivalent (P&L additive).
  Labels follow user convention; actual n_mnq used is the correct 10:1 ratio.

Outputs (working tree, not committed):
  sizing_vs_time_2026-05-26.png
  sizing_vs_time_2026-05-26.md

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.mc_sizing_vs_time
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

REPO = Path(__file__).resolve().parents[5]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Portfolio.risk.trailing_dd_simulator import (
    PropfirmConfig,
    simulate_run,
    make_iter10_trade_generator,
)

# ── Parameters ────────────────────────────────────────────────────────────────
N_RUNS  = 20_000
SEED    = 42
N_DAYS  = 400   # generator length; must exceed 180

# 8 unique n_mnq values (CRN: same seed → same binary trade/win draws, scaled P&L)
SIZINGS: list[tuple[int, str]] = [
    (1,  "1 MNQ"),
    (2,  "2 MNQ (baseline)"),
    (3,  "3 MNQ"),
    (4,  "4 MNQ"),
    (5,  "5 MNQ"),
    (7,  "7 MNQ"),
    (10, "10 MNQ (cap / ~1NQ)"),   # 1 NQ ≡ 10 MNQ (P&L ratio 10:1)
    (15, "15 MNQ (~1NQ+5MNQ)"),    # 1 NQ + 5 MNQ ≡ 15 MNQ
]

CAPS: list[int] = [7, 14, 21, 30, 60, 180]

SPRINT_CAP  = 30    # "challenge-fit" gate day
SPRINT_GATE = 25.0  # P(pass in 30d) ≥ 25% → viable sprint propfirm

# Tradeify Select Flex $25K canonical config
CONFIG = PropfirmConfig(
    capital=25_000.0,
    profit_target=1_500.0,
    trailing_dd_eval=1_000.0,
    trailing_dd_funded=1_000.0,
    lock_trigger_excess=100.0,
    locked_floor_offset=100.0,
    consistency_cap_pct=0.40,
    max_eval_days=180,
    funded_days=180,
)

# Scaling formula (from trailing_dd_simulator.py)
NQ_PV, NQ_COST   = 20.0, 19.0
MNQ_PV, MNQ_COST = 2.0, 2.15

def _scale(nq_pnl: float, n_mnq: int) -> float:
    return (nq_pnl + NQ_COST) / NQ_PV * MNQ_PV * n_mnq - MNQ_COST * n_mnq

AVG_WINNER_NQ = 1_571.60
AVG_LOSER_NQ  = -421.45


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate_sizing(n_mnq: int) -> pd.DataFrame:
    gen = make_iter10_trade_generator(N_DAYS, n_mnq=n_mnq, seed=SEED)
    rows: list[tuple[bool, bool, int]] = []
    for _ in range(N_RUNS):
        pnl = gen()
        res = simulate_run(pnl, CONFIG)
        rows.append((
            res.eval_passed,
            res.busted and res.bust_phase == "eval",
            res.eval_days,
        ))
    return pd.DataFrame(rows, columns=["eval_passed", "bust_eval", "eval_days"])


def cap_stats(df: pd.DataFrame, cap: int) -> dict[str, float]:
    pm = df["eval_passed"] & (df["eval_days"] <= cap)
    bm = df["bust_eval"]   & (df["eval_days"] <= cap)
    n_p = int(pm.sum())
    n_b = int(bm.sum())
    return {
        "p_pass": round(n_p / N_RUNS * 100, 1),
        "p_bust": round(n_b / N_RUNS * 100, 1),
        "p_unf":  round((N_RUNS - n_p - n_b) / N_RUNS * 100, 1),
    }


# ── Main simulation loop ──────────────────────────────────────────────────────

def run_all() -> dict[int, dict[int, dict[str, float]]]:
    """Returns sizing → cap → {p_pass, p_bust, p_unf}."""
    results: dict[int, dict[int, dict[str, float]]] = {}
    for n_mnq, label in SIZINGS:
        aw = round(_scale(AVG_WINNER_NQ, n_mnq), 0)
        al = round(_scale(AVG_LOSER_NQ,  n_mnq), 0)
        print(f"  {label:<26}  avg_winner=${aw:>6.0f}  avg_loser=${al:>6.0f}", end="", flush=True)
        t0 = time.perf_counter()
        df  = simulate_sizing(n_mnq)
        elapsed = time.perf_counter() - t0
        sizing_stats: dict[int, dict[str, float]] = {}
        for cap in CAPS:
            sizing_stats[cap] = cap_stats(df, cap)
        results[n_mnq] = sizing_stats
        p30 = sizing_stats[SPRINT_CAP]["p_pass"]
        p180 = sizing_stats[180]["p_pass"]
        print(f"  P(pass 30d)={p30:.1f}%  P(pass 180d)={p180:.1f}%  [{elapsed:.1f}s]")
    return results


# ── Plot ──────────────────────────────────────────────────────────────────────

def make_plot(results: dict, out_path: Path) -> None:
    n_rows, n_cols = 2, 4
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 8), sharey=False)
    fig.suptitle(
        "Strategy C iter_10 — Sizing scan vs time-to-pass\n"
        "Tradeify Select $25K  |  eval_DD=$1,000  |  target=$1,500  |  N=20,000  |  seed=42",
        fontsize=11, fontweight="bold",
    )

    # Identify optimal sizing at 30d
    p30_vals = {n: results[n][SPRINT_CAP]["p_pass"] for n, _ in SIZINGS}
    best_n, best_p30 = max(p30_vals.items(), key=lambda kv: kv[1])
    best_label = next(lbl for n, lbl in SIZINGS if n == best_n)

    for i, (n_mnq, label) in enumerate(SIZINGS):
        ax = axes.flat[i]
        stats = results[n_mnq]

        p_passes = [stats[c]["p_pass"] for c in CAPS]
        p_busts  = [stats[c]["p_bust"]  for c in CAPS]
        p_unfs   = [stats[c]["p_unf"]   for c in CAPS]

        ax.plot(CAPS, p_passes, "g-o", lw=1.5, ms=4, label="P(pass)")
        ax.plot(CAPS, p_busts,  "r-s", lw=1.5, ms=4, label="P(bust)")
        ax.plot(CAPS, p_unfs,   color="gray", lw=1.0, ls="--", ms=3, marker="^", label="P(unf)")

        ax.axvline(SPRINT_CAP, color="navy", lw=1.0, ls=":", alpha=0.8)
        ax.axhline(SPRINT_GATE, color="darkgreen", lw=0.8, ls=":", alpha=0.6)

        p30 = stats[SPRINT_CAP]["p_pass"]
        colour = "green" if p30 >= SPRINT_GATE else ("orange" if p30 >= 10 else "red")
        ax.set_title(f"{label}\nP(pass 30d) = {p30:.1f}%", fontsize=9,
                     color=colour, fontweight="bold" if n_mnq == best_n else "normal")

        ax.set_xlim(0, 185)
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_xticks(CAPS)
        ax.set_xticklabels([str(c) for c in CAPS], fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.2)
        if i == 0:
            ax.legend(fontsize=7, loc="upper left")

    # Annotation on figure: optimal sizing
    fig.text(
        0.5, 0.01,
        f"Optimal sizing for P(pass in {SPRINT_CAP}d): {best_label}  →  P(pass)={best_p30:.1f}%  "
        f"(gate ≥{SPRINT_GATE:.0f}%: {'✓ PASS' if best_p30 >= SPRINT_GATE else '✗ FAIL'})",
        ha="center", fontsize=10,
        color="green" if best_p30 >= SPRINT_GATE else "red",
        fontweight="bold",
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  Plot → {out_path}")


# ── Markdown report ───────────────────────────────────────────────────────────

def write_report(results: dict, out_path: Path) -> None:

    def tbl_row(metric: str, n_mnq: int, label: str) -> str:
        vals = " | ".join(f"{results[n_mnq][c][metric]:>5.1f}%" for c in CAPS)
        return f"| {label:<28} | {vals} |"

    def hdr() -> str:
        caps_s = " | ".join(f"{c}j" for c in CAPS)
        sep = " | ".join(["------" for _ in CAPS])
        return f"| Sizing                       | {caps_s} |\n|------------------------------|{sep}|"

    # P(pass in 30d) sweet spot per cap
    sweet = {}
    for cap in CAPS:
        best = max(SIZINGS, key=lambda s: results[s[0]][cap]["p_pass"])
        best_p = results[best[0]][cap]["p_pass"]
        sweet[cap] = (best[0], best[1], best_p)

    # Check 25% gate
    max_p30 = max(results[n][SPRINT_CAP]["p_pass"] for n, _ in SIZINGS)
    best_p30_sizing = next(
        (lbl for n, lbl in SIZINGS if results[n][SPRINT_CAP]["p_pass"] == max_p30), "—"
    )
    gate_pass = max_p30 >= SPRINT_GATE

    lines: list[str] = []
    lines.append("# mc_sizing_vs_time — Strategy C iter_10 / Tradeify Select $25K")
    lines.append("")
    lines.append("*Generated: 2026-05-26 | N=20,000 | seed=42 | eval_DD=$1,000 | target=$1,500 | 8 sizings*")
    lines.append("")
    lines.append("> **Note technique** : 1 NQ = $20/point = 10 MNQ (ratio 10:1, pas 5:1).")
    lines.append("> Entrées `10 MNQ (cap / ~1NQ)` et `15 MNQ (~1NQ+5MNQ)` reflètent les équivalences correctes.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table 1: P(pass)
    lines.append("## 1. P(pass) par sizing × time_cap")
    lines.append("")
    lines.append(hdr())
    for n_mnq, label in SIZINGS:
        lines.append(tbl_row("p_pass", n_mnq, label))
    lines.append("")

    # Table 2: P(bust)
    lines.append("## 2. P(bust) par sizing × time_cap")
    lines.append("")
    lines.append(hdr())
    for n_mnq, label in SIZINGS:
        lines.append(tbl_row("p_bust", n_mnq, label))
    lines.append("")

    # Table 3: P(unfinished)
    lines.append("## 3. P(unfinished) par sizing × time_cap")
    lines.append("")
    lines.append(hdr())
    for n_mnq, label in SIZINGS:
        lines.append(tbl_row("p_unf", n_mnq, label))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sweet spot per cap
    lines.append("## 4. Sweet spot optimal par time_cap")
    lines.append("")
    lines.append("| Time cap | Sizing optimal | P(pass) optimal | Gate 25% |")
    lines.append("|----------|---------------|----------------|---------|")
    for cap in CAPS:
        n, lbl, p = sweet[cap]
        gate_str = "✓ PASS" if p >= SPRINT_GATE else "✗ FAIL"
        lines.append(f"| {cap}j | {lbl} | {p:.1f}% | {gate_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Gate analysis
    lines.append("## 5. Analyse : gate P(pass in 30d) ≥ 25%")
    lines.append("")
    lines.append(f"Maximum P(pass in 30d) observé : **{max_p30:.1f}%** (sizing : {best_p30_sizing})")
    lines.append("")
    if gate_pass:
        lines.append(f"**Gate PASSED** : {best_p30_sizing} atteint {max_p30:.1f}% ≥ {SPRINT_GATE:.0f}%.")
    else:
        lines.append(f"**Gate FAIL** : aucun sizing n'atteint {SPRINT_GATE:.0f}%.")
        lines.append(f"Le maximum observé est {max_p30:.1f}% à {best_p30_sizing}.")
    lines.append("")
    lines.append("Profil du trade iter_10 (invariant au sizing) :")
    lines.append("- Fréquence : 0.458 trades/jour → ~14 trades sur 30j")
    lines.append("- Win rate : 27.75% → E[wins in 30d] ≈ 3.9 trades gagnants")
    lines.append("- avg_winner ≈ $314 × (n_mnq/2) ; avg_loser ≈ $85 × (n_mnq/2)")
    lines.append("- Pour atteindre $1,500 en 30j il faut E[P&L 30j] >> $1,500")
    lines.append("- E[P&L 30j] = 14 × avg_trade ≈ 14 × $66 × (n_mnq/2) à 2 MNQ baseline = $924")
    lines.append("- Mais E[P&L] est insuffisant sans P&L variance favorable : path-dependance élevée")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Conclusion
    lines.append("## 6. Conclusion")
    lines.append("")

    if gate_pass:
        conclusion = (
            f"iter_10 peut être sauvable comme stratégie propfirm sprint via sizing scaling. "
            f"Le sweet spot est {best_p30_sizing} avec P(pass in 30d)={max_p30:.1f}%, "
            f"au-dessus du gate 25%. Cependant, le P(bust) correspondant doit être évalué "
            f"pour vérifier si le coût en tentatives reste acceptable."
        )
    else:
        conclusion = (
            f"iter_10 est structurellement NON VIABLE comme stratégie propfirm sprint (≤30j), "
            f"quel que soit le sizing. Le maximum P(pass in 30d) = {max_p30:.1f}% "
            f"({best_p30_sizing}) reste bien en dessous du gate 25%. "
            f"La lenteur est structurelle : faible fréquence de trades (0.458/j), "
            f"faible win rate (27.75%), ratio W:L favorable (3.73:1) mais qui nécessite "
            f"de nombreux trades pour converger statistiquement. "
            f"Augmenter le sizing accélère la décision (réduction P(unfinished)) mais "
            f"P(bust) explose avant que P(pass) n'atteigne 25%, capturant le \"sweet spot\" "
            f"autour de {sweet[SPRINT_CAP][1]} sans jamais franchir le gate. "
            f"**Recommandation** : pivoter vers une stratégie haute fréquence (≥5 trades/jour) "
            f"et low-drawdown (max SL < 0.3% du compte par trade) — ex. mean-reversion "
            f"intraday NQ 1-min avec multiple setups ou stratégie delta-neutral propfirm."
        )

    lines.append(conclusion)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Simulator: Portfolio/risk/trailing_dd_simulator.py (unmodified)*")
    lines.append("*Generator: make_iter10_trade_generator — CRN seed=42 per sizing*")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Report → {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    out_dir   = Path(__file__).parent
    plot_path = out_dir / "sizing_vs_time_2026-05-26.png"
    md_path   = out_dir / "sizing_vs_time_2026-05-26.md"

    print(f"\nmc_sizing_vs_time — Strategy C / Tradeify Select $25K")
    print(f"N={N_RUNS:,}  seed={SEED}  caps={CAPS}")
    print(f"Config: eval_DD=${CONFIG.trailing_dd_eval:,.0f}  target=${CONFIG.profit_target:,.0f}  "
          f"consistency_cap=${CONFIG.consistency_cap_pct * CONFIG.profit_target:.0f}/day")
    print(f"Sizings: {[n for n, _ in SIZINGS]}")
    print()

    print("[1] Running MC simulations (8 sizings × 20,000 runs)...")
    t0 = time.perf_counter()
    results = run_all()
    total = time.perf_counter() - t0
    print(f"\n    Total: {total:.1f}s")

    print("[2] Generating plot...")
    make_plot(results, plot_path)

    print("[3] Writing report...")
    write_report(results, md_path)

    # Quick summary table
    print("\n  P(pass) summary:")
    hdr = "  {:<28}".format("Sizing") + "".join(f"  {c:>5}d" for c in CAPS)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for n_mnq, label in SIZINGS:
        row = "  {:<28}".format(label) + "".join(
            f"  {results[n_mnq][c]['p_pass']:>5.1f}%" for c in CAPS
        )
        print(row)

    # Gate check
    p30_by_sizing = {n: results[n][SPRINT_CAP]["p_pass"] for n, _ in SIZINGS}
    best_n = max(p30_by_sizing, key=lambda k: p30_by_sizing[k])
    best_lbl = next(lbl for n, lbl in SIZINGS if n == best_n)
    best_p = p30_by_sizing[best_n]
    verdict = "VIABLE ✓" if best_p >= SPRINT_GATE else "NON VIABLE ✗"
    print(f"\n  Best P(pass in 30d) = {best_p:.1f}%  ({best_lbl})")
    print(f"  Gate ≥{SPRINT_GATE:.0f}%  →  {verdict}")
    print()


if __name__ == "__main__":
    main()
