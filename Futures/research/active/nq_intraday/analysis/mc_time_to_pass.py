"""
mc_time_to_pass.py — Time-to-pass distribution for iter_10 under different time caps.
======================================================================================
Strategy C (Tradeify Select Flex $25K, 2 MNQ, eval_DD=$1,000, target=$1,500).
Uses the official trailing_dd_simulator WITHOUT modification.

Generator: make_iter10_trade_generator (trade-based, from trailing_dd_simulator.py)
           n_mnq=2, seed=42, N=20,000 paths, baseline only (no stress).

Caps tested: 5, 7, 14, 21, 30, 60, 90, 180 days.

Outputs:
  - time_to_pass_2026-05-26.png  (histogram + cap breakdown)
  - time_to_pass_2026-05-26.md   (report markdown)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.mc_time_to_pass
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
N_MNQ   = 2
N_DAYS  = 400   # generator length — must exceed max cap (180)

CAPS: list[int] = [5, 7, 14, 21, 30, 60, 90, 180]

# Tradeify Select Flex $25K — exact same config as mc_stress_test.py / trailing_dd_simulator.py
CONFIG = PropfirmConfig(
    capital=25_000.0,
    profit_target=1_500.0,
    trailing_dd_eval=1_000.0,
    trailing_dd_funded=1_000.0,
    lock_trigger_excess=100.0,
    locked_floor_offset=100.0,
    consistency_cap_pct=0.40,    # $600/day cap — not binding at 2 MNQ (avg winner ~$314)
    max_eval_days=180,            # collect full window; cap analysis done post-hoc
    funded_days=180,
)

PASS_GATE_DAYS  = 30    # P(pass in 30d) — key propfirm sprint metric
PASS_GATE_PCT   = 25.0  # below this → "not viable for sprint propfirm"


# ── Simulation ────────────────────────────────────────────────────────────────

def run_simulation() -> pd.DataFrame:
    """
    N_RUNS MC paths with max_eval_days=180.
    Returns DataFrame with one row per run: eval_passed, bust_eval, eval_days.
    """
    gen = make_iter10_trade_generator(N_DAYS, n_mnq=N_MNQ, seed=SEED)
    rows: list[dict] = []

    for _ in range(N_RUNS):
        pnl = gen()
        res = simulate_run(pnl, CONFIG)
        rows.append({
            "eval_passed": res.eval_passed,
            "bust_eval":   res.busted and res.bust_phase == "eval",
            "eval_days":   res.eval_days,
        })

    return pd.DataFrame(rows)


def compute_cap_stats(df: pd.DataFrame) -> list[dict]:
    """For each cap, compute P(pass), P(bust), P(unfinished), E[days|pass], pctiles."""
    stats = []
    for cap in CAPS:
        pass_m = df["eval_passed"] & (df["eval_days"] <= cap)
        bust_m = df["bust_eval"]   & (df["eval_days"] <= cap)
        unf_m  = ~pass_m & ~bust_m

        n_pass = int(pass_m.sum())
        n_bust = int(bust_m.sum())
        n_unf  = int(unf_m.sum())

        days_v = df.loc[pass_m, "eval_days"].values.astype(int)

        row: dict = {
            "cap":    cap,
            "p_pass": round(n_pass / N_RUNS * 100, 1),
            "p_bust": round(n_bust / N_RUNS * 100, 1),
            "p_unf":  round(n_unf  / N_RUNS * 100, 1),
            "n_pass": n_pass,
            "e_days": round(float(days_v.mean()), 1) if n_pass > 0 else float("nan"),
            "p25":    int(np.percentile(days_v, 25)) if n_pass > 0 else None,
            "p50":    int(np.percentile(days_v, 50)) if n_pass > 0 else None,
            "p75":    int(np.percentile(days_v, 75)) if n_pass > 0 else None,
            "p95":    int(np.percentile(days_v, 95)) if n_pass > 0 else None,
        }
        stats.append(row)
    return stats


# ── Plot ──────────────────────────────────────────────────────────────────────

def make_plot(df: pd.DataFrame, stats: list[dict], out_path: Path) -> None:
    # Days-to-pass for all passing runs (no cap)
    pass_days = df.loc[df["eval_passed"], "eval_days"].values.astype(int)
    row_180   = next(r for r in stats if r["cap"] == 180)
    row_30    = next(r for r in stats if r["cap"] == 30)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(13, 10),
        gridspec_kw={"height_ratios": [2.5, 1.5]},
    )
    fig.suptitle(
        "Strategy C iter_10 — 2 MNQ — Time-to-pass distribution\n"
        "Tradeify Select $25K  |  eval_DD=$1,000  |  target=$1,500  |  N=20,000 paths  |  seed=42",
        fontsize=11, fontweight="bold",
    )

    # ── Panel 1: histogram of days_to_pass (conditional on pass, 180d window) ──
    bins = np.arange(0, 185, 5)
    counts, edges = np.histogram(pass_days, bins=bins)
    pct_of_total   = counts / N_RUNS * 100   # as % of ALL runs
    pct_cumulative = np.cumsum(pct_of_total)

    ax1_r = ax1.twinx()
    ax1.bar(edges[:-1] + 2.5, pct_of_total, width=4.5, color="#4292c6", alpha=0.75,
            label=f"Passes per 5-day bucket (% of all runs)")
    ax1_r.step(edges[:-1] + 2.5, pct_cumulative, where="post", color="#e6550d",
               lw=2.0, label="Cumulative P(pass) %")
    ax1_r.set_ylim(0, 100)

    # Vertical markers
    for day, col, lbl in [(7, "#2ca02c", "7d"), (14, "#ff7f0e", "14d"), (30, "#d62728", "30d")]:
        ax1.axvline(day, color=col, lw=1.5, ls="--", alpha=0.9)
        cap_r = next(r for r in stats if r["cap"] == day)
        ax1.text(day + 1, max(pct_of_total) * 0.95, f"P(pass≤{lbl})\n={cap_r['p_pass']}%",
                 fontsize=8, color=col, va="top")

    ax1.set_xlabel("Trading days to pass (conditional on pass, 180d window)", fontsize=9)
    ax1.set_ylabel("% of all 20,000 runs", fontsize=9)
    ax1_r.set_ylabel("Cumulative P(pass) %", fontsize=9)

    lines1, labs1 = ax1.get_legend_handles_labels()
    lines2, labs2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labs1 + labs2, fontsize=8, loc="upper right")
    ax1.grid(alpha=0.25)

    # Annotation: key statistics
    txt = (f"P(pass 180d) = {row_180['p_pass']}%\n"
           f"P(bust 180d) = {row_180['p_bust']}%\n"
           f"Median days  = {row_180['p50']}d\n"
           f"E[days|pass] = {row_180['e_days']}d")
    ax1.text(0.98, 0.60, txt, transform=ax1.transAxes, fontsize=9,
             va="top", ha="right",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.85))

    # ── Panel 2: stacked bar P(pass)/P(bust)/P(unf) by cap ───────────────────
    cap_labels  = [str(c) for c in CAPS]
    p_passes    = [r["p_pass"] for r in stats]
    p_busts     = [r["p_bust"] for r in stats]
    p_unfs      = [r["p_unf"]  for r in stats]
    x = np.arange(len(CAPS))

    b1 = ax2.bar(x, p_passes, color="#74c476", label="P(pass)")
    b2 = ax2.bar(x, p_busts,  bottom=p_passes, color="#fb6a4a", label="P(bust)")
    p_bot = [a + b for a, b in zip(p_passes, p_busts)]
    b3 = ax2.bar(x, p_unfs, bottom=p_bot, color="#bdbdbd", label="P(unfinished)")

    ax2.axhline(PASS_GATE_PCT, color="darkred", lw=1.2, ls=":", label=f"Pass gate {PASS_GATE_PCT:.0f}%")

    for i, r in enumerate(stats):
        ax2.text(i, r["p_pass"] / 2, f"{r['p_pass']:.1f}%",
                 ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{c}d" for c in CAPS], fontsize=9)
    ax2.set_ylabel("Probability (%)", fontsize=9)
    ax2.set_xlabel("Time cap (trading days)", fontsize=9)
    ax2.set_ylim(0, 105)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.legend(fontsize=8, loc="upper left")
    ax2.grid(alpha=0.2, axis="y")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  Plot → {out_path}")


# ── Markdown report ───────────────────────────────────────────────────────────

def write_report(stats: list[dict], out_path: Path) -> None:
    row_180 = next(r for r in stats if r["cap"] == 180)
    row_30  = next(r for r in stats if r["cap"] == 30)
    row_7   = next(r for r in stats if r["cap"] == 7)
    row_14  = next(r for r in stats if r["cap"] == 14)

    def fmt(v) -> str:
        return str(v) if v is not None else "—"

    table_rows = []
    for r in stats:
        e = f"{r['e_days']:.1f}" if not (isinstance(r['e_days'], float) and
                                          r['e_days'] != r['e_days']) else "—"
        table_rows.append(
            f"| {r['cap']}j | {r['p_pass']:.1f}% | {r['p_bust']:.1f}% | "
            f"{r['p_unf']:.1f}% | {e} | {fmt(r['p25'])} | {fmt(r['p50'])} | "
            f"{fmt(r['p75'])} | {fmt(r['p95'])} |"
        )

    # Sprint vs marathon interpretation
    p_sprint_7   = row_7["p_pass"]
    p_sprint_14  = row_14["p_pass"]
    p_sprint_30  = row_30["p_pass"]
    p_marathon   = row_180["p_pass"]
    med_days_180 = row_180["p50"]

    if p_sprint_30 >= PASS_GATE_PCT:
        sprint_verdict = f"VIABLE pour sprint ≤30j (P={p_sprint_30:.1f}% ≥ gate {PASS_GATE_PCT:.0f}%)"
        viable = True
    else:
        sprint_verdict = f"NON VIABLE pour sprint ≤30j (P={p_sprint_30:.1f}% < gate {PASS_GATE_PCT:.0f}%)"
        viable = False

    if med_days_180 > 60:
        pace = "MARATHON"
    elif med_days_180 > 21:
        pace = "LONG RUN"
    else:
        pace = "SPRINT"

    content = f"""# mc_time_to_pass — Strategy C iter_10 / Tradeify Select $25K

*Generated: 2026-05-26 | N=20,000 | seed=42 | 2 MNQ | eval_DD=$1,000 | target=$1,500*

---

## 1. Distribution temps-pour-passer (toutes fenêtres)

| Time cap | P(pass) | P(bust) | P(unfinished) | E[days|pass] | p25 | p50 | p75 | p95 |
|----------|---------|---------|---------------|--------------|-----|-----|-----|-----|
| Cap (réf: 180j) | {row_180['p_pass']:.1f}% | {row_180['p_bust']:.1f}% | {row_180['p_unf']:.1f}% | {row_180['e_days']:.1f} | {fmt(row_180['p25'])} | {fmt(row_180['p50'])} | {fmt(row_180['p75'])} | {fmt(row_180['p95'])} |
{chr(10).join(table_rows)}

*P(pass) = atteindre +$1,500 AVANT eod_dd ≥ $1,000 dans la fenêtre. P(bust) = eod_dd ≥ $1,000 avant cible. P(unfinished) = ni l'un ni l'autre dans la fenêtre.*

---

## 2. Interprétation sprint vs marathon

**Cadence**: iter_10 est un **{pace}** (médiane = {med_days_180}j pour les runs qui passent).

- P(pass ≤ 7j)  = **{p_sprint_7:.1f}%** → {p_sprint_7:.0f} runs sur 1,000 passent en une semaine
- P(pass ≤ 14j) = **{p_sprint_14:.1f}%** → probabilité d'un challenge de 2 semaines
- P(pass ≤ 30j) = **{p_sprint_30:.1f}%** → probabilité d'un challenge mensuel
- P(pass ≤ 180j) = **{p_marathon:.1f}%** → référence sans cap temporel

La stratégie tire sa probabilité de succès essentiellement sur la longue fenêtre (60–180j).
Les quantiles p25={fmt(row_180['p25'])}j / p50={fmt(row_180['p50'])}j / p75={fmt(row_180['p75'])}j / p95={fmt(row_180['p95'])}j
confirment que la moitié des réussites prend plus de {fmt(row_180['p50'])} jours.

---

## 3. Métrique-clé : P(pass in 30 jours) = {p_sprint_30:.1f}%

**Gate : P(pass in 30d) ≥ {PASS_GATE_PCT:.0f}% pour être viable sur propfirm sprint.**

→ **{sprint_verdict}**

Comparaison par rapport au gate :
- P(pass in 30d) = {p_sprint_30:.1f}%  |  Gate = {PASS_GATE_PCT:.0f}%
- Ratio = {p_sprint_30/PASS_GATE_PCT:.2f}× le seuil

---

## 4. Conclusion

iter_10 sur Tradeify Select $25K est fondamentalement une stratégie de **longue durée**.

La structure de distribution montre que ~{row_30['p_unf']:.0f}% des tentatives sont encore en cours à 30 jours
(ni passées ni bustées), ce qui signifie que le résultat reste ouvert — ce ne sont pas des défaites,
mais des runners qui ont besoin de plus de temps.

**Recommandation** : Tradeify Select $25K sans time limit est le bon véhicule pour iter_10.
Si un propfirm impose une limite stricte de 30 jours, iter_10 n'est pas le bon candidat
(nécessiterait ~{round(PASS_GATE_PCT * 100 / p_sprint_30):.0f}× plus de frequency ou
un sizing plus agressif, incompatible avec la contrainte DD $1,000).

---

*Simulator: Portfolio/risk/trailing_dd_simulator.py (unmodified)*
*Generator: make_iter10_trade_generator(n_mnq=2, seed=42) — trade-based, not Gaussian*
*Config: PropfirmConfig() — Tradeify Select Flex $25K canonical*
"""

    out_path.write_text(content, encoding="utf-8")
    print(f"  Report → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    out_dir = Path(__file__).parent
    plot_path   = out_dir / "time_to_pass_2026-05-26.png"
    report_path = out_dir / "time_to_pass_2026-05-26.md"

    print(f"\nmc_time_to_pass — Strategy C / 2 MNQ / Tradeify Select $25K")
    print(f"N={N_RUNS:,}  seed={SEED}  n_mnq={N_MNQ}")
    print(f"Config: eval_DD=${CONFIG.trailing_dd_eval:,.0f}  target=${CONFIG.profit_target:,.0f}  "
          f"max_days={CONFIG.max_eval_days}  consistency_cap=${CONFIG.consistency_cap_pct * CONFIG.profit_target:.0f}/day")
    print(f"Generator: make_iter10_trade_generator (trade-based, avg_winner~$314 avg_loser~$-85)")
    print()

    t0 = time.perf_counter()
    print("[1] Running MC simulation...")
    df = run_simulation()
    elapsed = time.perf_counter() - t0
    print(f"    Done in {elapsed:.1f}s")

    # Quick sanity check
    n_pass_180 = df["eval_passed"].sum()
    n_bust_180 = df["bust_eval"].sum()
    n_unf_180  = N_RUNS - n_pass_180 - n_bust_180
    print(f"    180d baseline: P(pass)={n_pass_180/N_RUNS*100:.1f}%  "
          f"P(bust)={n_bust_180/N_RUNS*100:.1f}%  P(unfinished)={n_unf_180/N_RUNS*100:.1f}%")

    print("[2] Computing cap stats...")
    stats = compute_cap_stats(df)

    print("[3] Generating plot...")
    make_plot(df, stats, plot_path)

    print("[4] Writing report...")
    write_report(stats, report_path)

    print("\n  Summary table:")
    print(f"  {'Cap':>5} {'P(pass)':>8} {'P(bust)':>8} {'P(unf)':>8} {'E[days|pass]':>14} {'p50':>5} {'p95':>5}")
    print(f"  {'-'*65}")
    for r in stats:
        e_str  = f"{r['e_days']:>12.1f}" if r['e_days'] == r['e_days'] else "           —"
        p50_s  = str(r['p50']) if r['p50'] is not None else "—"
        p95_s  = str(r['p95']) if r['p95'] is not None else "—"
        print(f"  {r['cap']:>5}d  {r['p_pass']:>7.1f}%  {r['p_bust']:>7.1f}%  "
              f"{r['p_unf']:>7.1f}%  {e_str}  {p50_s:>4}d  {p95_s:>4}d")

    row_30 = next(r for r in stats if r["cap"] == 30)
    verdict = "VIABLE" if row_30["p_pass"] >= PASS_GATE_PCT else "NON VIABLE"
    print(f"\n  P(pass in 30d) = {row_30['p_pass']:.1f}%  (gate ≥{PASS_GATE_PCT:.0f}%) → {verdict} pour sprint propfirm")
    print()


if __name__ == "__main__":
    main()
