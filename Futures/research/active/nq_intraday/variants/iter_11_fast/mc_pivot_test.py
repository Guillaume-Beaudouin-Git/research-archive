"""
mc_pivot_test.py — MC P(pass) for iter_11_fast at 5 MNQ.
==========================================================
Calibrates the generator from actual iter_11_fast backtest trade distribution.
N=20,000 paths | seed=42 | CRN | Tradeify Select Flex $25K canonical config.

Comparison baseline (sizing_vs_time_2026-05-26.md):
  iter_10 @ 2 MNQ:  P(pass in 30d) =  8.0%
  iter_10 @ 5 MNQ:  P(pass in 30d) = 38.4%

H3 gate: iter_11_fast @ 5 MNQ — P(pass in 30d) > 25%.

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.variants.iter_11_fast.mc_pivot_test
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from numpy.typing import NDArray

REPO = Path(__file__).resolve().parents[6]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine
from Futures.research.active.nq_intraday.iter_05 import build_opening_features
from Portfolio.risk.trailing_dd_simulator import PropfirmConfig, simulate_run, RunResult
from Futures.research.active.nq_intraday.variants.iter_11_fast.iter_11_refined import (
    build_signals_fast,
)

# ── Simulation parameters ────────────────────────────────────────────────────
N_RUNS  = 20_000
SEED    = 42
N_MNQ   = 5
N_DAYS  = 400   # generator length: must exceed max_eval_days (180)
CAPS    = [7, 14, 21, 30, 60, 180]

# Tradeify Select Flex $25K (canonical — DO NOT change, confirmed 2026-05-25)
CONFIG = PropfirmConfig()   # DD_eval=$1,000, DD_funded=$1,000, lock=$26,100

# NQ→MNQ scaling constants
NQ_COST = 19.0
NQ_PV   = 20.0
MNQ_PV  = 2.0
MNQ_COST = 2.15

# iter_10 @ 5 MNQ baseline (sizing_vs_time_2026-05-26.md)
ITER10_P_PASS_30D_5MNQ = 38.4
ITER10_P_PASS_30D_2MNQ =  8.0

H3_GATE  = 25.0     # P(pass in 30d) > 25%


# ── Calibrate generator from actual iter_11_fast trade distribution ───────────

def _scale_nq_to_mnq(nq_pnl: float, n_mnq: int) -> float:
    """Convert per-trade NQ net P&L to n_mnq MNQ net P&L."""
    return (nq_pnl + NQ_COST) / NQ_PV * MNQ_PV * n_mnq - MNQ_COST * n_mnq


def build_iter11_fast_generator(
    trade_log: pd.DataFrame,
    n_mnq: int,
    n_days: int,
    seed: int = SEED,
) -> tuple[Callable[[], NDArray[np.float64]], dict]:
    """
    Trade-based daily P&L generator calibrated to iter_11_fast backtest.

    Models iter_11_fast correctly: max 1 trade per day, hard SL cap.
    Losers are approximately fixed (dollar_stop=$400 → max loss ≈$419 NQ net).
    Winners are normally distributed around avg_winner with 30% std.

    Returns (generator_fn, calibration_stats_dict).
    """
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

    # Trade frequency
    dates_traded = tl["date"].unique()
    d_min, d_max = tl["date"].min(), tl["date"].max()
    n_biz_days = len(pd.bdate_range(d_min, d_max, freq="C"))
    trade_freq = len(tl) / n_biz_days

    # Win/loss distribution from actual backtest
    winners = tl[tl["pnl_usd"] > 0]["pnl_usd"].values
    losers  = tl[tl["pnl_usd"] <= 0]["pnl_usd"].values
    win_rate = len(winners) / len(tl)

    avg_winner_nq = float(winners.mean()) if len(winners) > 0 else 1000.0
    avg_loser_nq  = float(losers.mean())  if len(losers)  > 0 else -400.0

    # Scale to n_mnq MNQ
    avg_winner_mnq = _scale_nq_to_mnq(avg_winner_nq, n_mnq)
    avg_loser_mnq  = _scale_nq_to_mnq(avg_loser_nq,  n_mnq)
    winner_std     = abs(avg_winner_mnq) * 0.30

    stats = {
        "n_trades":        len(tl),
        "n_biz_days":      n_biz_days,
        "trade_freq":      round(trade_freq, 4),
        "win_rate":        round(win_rate, 4),
        "avg_winner_nq":   round(avg_winner_nq, 2),
        "avg_loser_nq":    round(avg_loser_nq, 2),
        "avg_winner_mnq":  round(avg_winner_mnq, 2),
        "avg_loser_mnq":   round(avg_loser_mnq, 2),
        "winner_std":      round(winner_std, 2),
        "n_mnq":           n_mnq,
    }

    rng = np.random.default_rng(seed)

    def generate() -> NDArray[np.float64]:
        trade = rng.random(n_days) < trade_freq
        win   = trade & (rng.random(n_days) < win_rate)
        lose  = trade & ~win

        pnl = np.zeros(n_days)
        n_wins = int(win.sum())
        if n_wins > 0:
            raw = rng.normal(avg_winner_mnq, winner_std, n_wins)
            pnl[win] = np.clip(raw, avg_loser_mnq, None)
        pnl[lose] = avg_loser_mnq
        return pnl

    return generate, stats


# ── MC simulation with time caps ─────────────────────────────────────────────

def simulate_with_caps(
    n_runs: int,
    generator: Callable[[], NDArray[np.float64]],
    config: PropfirmConfig,
    caps: list[int],
) -> list[dict]:
    """
    Run MC and compute P(pass), P(bust), P(unfinished) for each time cap.

    Returns list of row dicts keyed by cap.
    """
    rows_by_cap = {cap: {"n_pass": 0, "n_bust": 0} for cap in caps}
    all_eval_passed = []
    all_bust_eval   = []
    all_eval_days   = []

    for _ in range(n_runs):
        pnl = generator()
        res = simulate_run(pnl, config)
        all_eval_passed.append(res.eval_passed)
        all_bust_eval.append(res.busted and res.bust_phase == "eval")
        all_eval_days.append(res.eval_days)

    df_sim = pd.DataFrame({
        "passed": all_eval_passed,
        "bust":   all_bust_eval,
        "days":   all_eval_days,
    })

    stats = []
    for cap in caps:
        pass_m = df_sim["passed"] & (df_sim["days"] <= cap)
        bust_m = df_sim["bust"]   & (df_sim["days"] <= cap)
        unf_m  = ~pass_m & ~bust_m

        n_pass = int(pass_m.sum())
        n_bust = int(bust_m.sum())

        days_pass = df_sim.loc[pass_m, "days"].values.astype(int)
        e_days = float(np.mean(days_pass)) if n_pass > 0 else float("nan")

        stats.append({
            "cap":    cap,
            "p_pass": round(n_pass / n_runs * 100, 1),
            "p_bust": round(n_bust / n_runs * 100, 1),
            "p_unf":  round(int(unf_m.sum()) / n_runs * 100, 1),
            "n_pass": n_pass,
            "e_days": round(e_days, 1) if np.isfinite(e_days) else None,
        })

    return stats


# ── Verdict markdown ──────────────────────────────────────────────────────────

def write_verdict(
    mc_stats: list[dict],
    calib: dict,
    full_met: dict,
    wf_pct: float,
    h1_pass: bool,
    h2_pass: bool,
    n_runs: int,
    elapsed: float,
    out_path: Path,
) -> None:
    sh  = full_met.get("sharpe_daily_hac") or 0
    mdd = full_met.get("max_dd_pct") or 0
    n   = full_met.get("n_trades", 0)
    wr  = full_met.get("win_rate", 0)
    avg_bars = full_met.get("avg_bars_held") or 0

    row_30 = next(r for r in mc_stats if r["cap"] == 30)
    row_7  = next(r for r in mc_stats if r["cap"] == 7)
    row_180 = next(r for r in mc_stats if r["cap"] == 180)

    h3_pass = row_30["p_pass"] > H3_GATE

    all_pass  = h1_pass and h2_pass and h3_pass
    go_no_go  = "GO" if all_pass else "NO-GO"

    table_header = (
        "| Time cap | P(pass) | P(bust) | P(unfinished) | E[days\\|pass] |\n"
        "|----------|---------|---------|---------------|---------------|\n"
    )
    table_rows = "\n".join(
        f"| {r['cap']}d | {r['p_pass']:.1f}% | {r['p_bust']:.1f}% | "
        f"{r['p_unf']:.1f}% | "
        + (f"{r['e_days']:.1f}" if r['e_days'] is not None else "—") + " |"
        for r in mc_stats
    )

    content = f"""# iter_11_fast Verdict — 2026-05-26

*Strategy C pivot: TP=1.0R, time_stop=11:30 ET, sizing=5 MNQ*

---

## 1. Full backtest (2022-2025)

| Metric | iter_11_fast | iter_10 baseline | Delta |
|--------|-------------|-----------------|-------|
| N trades | {n} | 346 | {n-346:+d} |
| Win rate | {wr*100:.2f}% | 27.75% | |
| Sharpe HAC | {sh:.4f} | 1.5212 | {sh-1.5212:+.4f} |
| MaxDD | {mdd*100:.2f}% | -13.42% | {(mdd+0.1342)*100:+.1f}pp |
| avg_bars_held | {avg_bars:.1f} | 23.6 | {avg_bars-23.6:+.1f} |
| avg_winner (NQ) | ${calib['avg_winner_nq']:,.0f} | $1,572 | ${calib['avg_winner_nq']-1572:+,.0f} |
| avg_loser (NQ) | ${calib['avg_loser_nq']:,.0f} | $-421 | ${calib['avg_loser_nq']+421:+,.0f} |
| WF% positive | {wf_pct:.0f}% | 77.8% | |

---

## 2. MC P(pass) — iter_11_fast @ {N_MNQ} MNQ

*N={n_runs:,} | seed={SEED} | CRN | config: DD_eval=$1,000 DD_funded=$1,000 lock=$26,100*

Generator calibration (from actual backtest):
- trade_freq = {calib['trade_freq']:.4f} trade/day
- win_rate   = {calib['win_rate']*100:.2f}%
- avg_winner = ${calib['avg_winner_mnq']:.0f}/trade ({N_MNQ} MNQ)
- avg_loser  = ${calib['avg_loser_mnq']:.0f}/trade ({N_MNQ} MNQ)

{table_header}{table_rows}

**Comparison baseline (sizing_vs_time_2026-05-26.md):**
- iter_10 @ 2 MNQ: P(pass in 30d) = {ITER10_P_PASS_30D_2MNQ:.1f}%
- iter_10 @ 5 MNQ: P(pass in 30d) = {ITER10_P_PASS_30D_5MNQ:.1f}%
- iter_11_fast @ {N_MNQ} MNQ: P(pass in 30d) = **{row_30['p_pass']:.1f}%**

---

## 3. Gate matrix

| Hypothesis | Gate | Actual | Result |
|------------|------|--------|--------|
| H1: WF Sharpe ≥ 1.22 | ≥ 1.22 | {sh:.4f} (full BT) | {'PASS ✓' if h1_pass else 'FAIL ✗'} |
| H2: avg_bars_held < 120 | < 120 bars | {avg_bars:.1f} bars | {'PASS ✓' if h2_pass else 'FAIL ✗'} |
| H3: P(pass 30d) > 25% | > 25% | {row_30['p_pass']:.1f}% | {'PASS ✓' if h3_pass else 'FAIL ✗'} |

---

## 4. Verdict: **{go_no_go}**

{'**ALL GATES PASS.** iter_11_fast is a candidate for paper trade at 5 MNQ on Tradeify Select Flex $25K.' if all_pass else ''}
{'**H1 FAIL**: TP=1.0R destroys the edge — Sharpe degrades > 20% vs iter_10 baseline. Archive iter_11_fast.' if not h1_pass else ''}
{'**H3 FAIL**: P(pass in 30d) = ' + f"{row_30['p_pass']:.1f}%" + f' is below the 25% gate. The sizing/TP combo is not sufficient for sprint propfirm.' if h1_pass and h2_pass and not h3_pass else ''}
{'**H2 FAIL**: avg_bars_held = ' + f"{avg_bars:.1f}" + ' bars exceeds 120 (unexpected — check time stop logic).' if h1_pass and not h2_pass else ''}

### Trade-off analysis
- Sharpe: iter_11_fast {sh:.4f} vs iter_10 1.5212 → {(sh/1.5212-1)*100:+.1f}% change
- P(pass 30d): {row_30['p_pass']:.1f}% vs iter_10@5MNQ {ITER10_P_PASS_30D_5MNQ:.1f}% → {row_30['p_pass']-ITER10_P_PASS_30D_5MNQ:+.1f}pp
- P(pass 180d): {row_180['p_pass']:.1f}% (marathon window reference)

### Next steps
{'- **Paper trade**: configure Tradovate with TP=1.0R and 11:30 time stop, sizing=5 MNQ' if all_pass else ''}
{'- **Sizing alternative**: if P(pass 30d) is marginal, test 4 MNQ vs 6 MNQ (already in sizing_vs_time — compare iter_11_fast calibration separately)' if not all_pass and row_30['p_pass'] > 15 else ''}
{'- **Modification #2 budget**: if H1 fail, try TP=1.2R as intermediate (preserves Sharpe better, less frequency boost)' if not h1_pass else ''}
{'- **Archive**: no further modifications viable' if not h1_pass and not h3_pass and not h2_pass else ''}

---

*Simulator: Portfolio/risk/trailing_dd_simulator.py (unmodified)*
*Generator: build_iter11_fast_generator — trade-based, calibrated to actual backtest*
*Runtime: {elapsed:.1f}s*
"""

    out_path.write_text(content, encoding="utf-8")
    print(f"\n  [Verdict → {out_path}]")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    out_dir = Path(__file__).parent

    print("=" * 80)
    print(f"mc_pivot_test — iter_11_fast @ {N_MNQ} MNQ | N={N_RUNS:,} | seed={SEED}")
    print(f"Config: DD_eval=${CONFIG.trailing_dd_eval:,.0f} "
          f"DD_funded=${CONFIG.trailing_dd_funded:,.0f} "
          f"lock=${CONFIG.capital + CONFIG.trailing_dd_funded + CONFIG.lock_trigger_excess:,.0f}")
    print(f"H3 gate: P(pass in 30d) > {H3_GATE:.0f}%")
    print(f"Baseline: iter_10@5MNQ={ITER10_P_PASS_30D_5MNQ:.1f}%, iter_10@2MNQ={ITER10_P_PASS_30D_2MNQ:.1f}%")
    print("=" * 80)

    t0 = time.perf_counter()

    # ── Run actual iter_11_fast backtest to get trade distribution ────────────
    print("\n[1] Running iter_11_fast backtest for trade distribution calibration...")
    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    sigs   = build_signals_fast(feats)

    if sigs.empty:
        print("  ERROR: No signals generated. Check iter_11_refined.py.")
        return

    tl, met = engine.run(sigs)
    n = len(tl)
    sh  = met.get("sharpe_daily_hac") or 0
    wr  = met.get("win_rate") or 0
    avg_bars = met.get("avg_bars_held") or 0

    print(f"  N={n} trades | Sharpe={sh:.4f} | WR={wr*100:.2f}% | avg_bars={avg_bars:.1f}")

    # ── Build calibrated generator ────────────────────────────────────────────
    print(f"\n[2] Calibrating generator from iter_11_fast trade distribution...")
    gen, calib = build_iter11_fast_generator(tl, n_mnq=N_MNQ, n_days=N_DAYS, seed=SEED)

    print(f"  trade_freq  = {calib['trade_freq']:.4f}/day")
    print(f"  win_rate    = {calib['win_rate']*100:.2f}%")
    print(f"  avg_winner  = ${calib['avg_winner_mnq']:>8.0f} ({N_MNQ} MNQ)  ← NQ ${calib['avg_winner_nq']:,.0f}")
    print(f"  avg_loser   = ${calib['avg_loser_mnq']:>8.0f} ({N_MNQ} MNQ)  ← NQ ${calib['avg_loser_nq']:,.0f}")
    print(f"  winner_std  = ${calib['winner_std']:>8.0f}")
    print(f"  E[daily]    = ${calib['trade_freq'] * (calib['win_rate'] * calib['avg_winner_mnq'] + (1-calib['win_rate']) * calib['avg_loser_mnq']):>8.0f}/day")

    # ── Run MC simulation ─────────────────────────────────────────────────────
    print(f"\n[3] Running MC simulation (N={N_RUNS:,}, seed={SEED})...")
    mc_stats = simulate_with_caps(N_RUNS, gen, CONFIG, CAPS)

    elapsed = time.perf_counter() - t0

    # ── Results table ─────────────────────────────────────────────────────────
    print(f"\n  {'Time cap':>9} {'P(pass)':>8} {'P(bust)':>8} {'P(unf)':>9} {'E[days|pass]':>13}")
    print(f"  {'-'*52}")
    for r in mc_stats:
        e_str = f"{r['e_days']:.1f}" if r["e_days"] is not None else "—"
        print(f"  {r['cap']:>7}d  {r['p_pass']:>7.1f}%  {r['p_bust']:>7.1f}%  "
              f"{r['p_unf']:>8.1f}%  {e_str:>12}")

    row_30 = next(r for r in mc_stats if r["cap"] == 30)

    print(f"\n  Baseline comparison:")
    print(f"    iter_10 @ 2 MNQ : P(pass in 30d) = {ITER10_P_PASS_30D_2MNQ:.1f}%")
    print(f"    iter_10 @ 5 MNQ : P(pass in 30d) = {ITER10_P_PASS_30D_5MNQ:.1f}%")
    print(f"    iter_11_fast @{N_MNQ}MNQ: P(pass in 30d) = {row_30['p_pass']:.1f}%  "
          f"({'above' if row_30['p_pass'] > ITER10_P_PASS_30D_5MNQ else 'below'} iter_10@5MNQ)")

    h3_pass = row_30["p_pass"] > H3_GATE

    # ── Load h1/h2 results from iter_11_refined results.json ──────────────────
    results_path = out_dir / "results.json"
    h1_pass = False
    h2_pass = False
    wf_pct  = 0.0
    if results_path.exists():
        try:
            saved = json.loads(results_path.read_text(encoding="utf-8"))
            if saved:
                r0 = saved[0]
                h1_pass = bool(r0.get("h1_pass", False))
                h2_pass = bool(r0.get("h2_pass", False))
                wf_pct  = float(r0.get("wf_pct_positive", 0))
        except Exception:
            pass
    else:
        # Compute inline (fallback)
        wf_med = met.get("wf_pct_positive") or 0
        h1_pass = sh >= 1.22
        h2_pass = avg_bars < 120

    # ── STOP-POINT 2 ──────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("STOP-POINT 2 — MC P(pass) results + full verdict")
    print("=" * 80)
    print(f"  P(pass in 30d) @ {N_MNQ} MNQ:  {row_30['p_pass']:.1f}%  (gate > {H3_GATE:.0f}%)")
    print(f"  H3 gate: {'PASS ✓' if h3_pass else 'FAIL ✗'}")
    print(f"\n  H1 (WF Sharpe ≥ 1.22): {'PASS ✓' if h1_pass else 'FAIL ✗'}")
    print(f"  H2 (avg_bars < 120):    {'PASS ✓' if h2_pass else 'FAIL ✗'}")
    print(f"  H3 (P(pass 30d)>25%):   {'PASS ✓' if h3_pass else 'FAIL ✗'}")

    all_pass = h1_pass and h2_pass and h3_pass
    print(f"\n  VERDICT: {'GO ✓' if all_pass else 'NO-GO ✗'}")

    if all_pass:
        print(f"\n  → All gates pass. iter_11_fast is a sprint-viable candidate.")
        print(f"     Paper trade: 5 MNQ, TP=1.0R, time_stop=11:30 ET")
        print(f"     Tradeify Select Flex $25K, DD=$1,000, target=$1,500")
    else:
        print(f"\n  → Verdict NO-GO. See verdict_2026-05-26.md for detailed analysis.")

    print(f"\n  Runtime: {elapsed:.1f}s")
    print("=" * 80)

    # ── Save verdict markdown ──────────────────────────────────────────────────
    write_verdict(
        mc_stats=mc_stats,
        calib=calib,
        full_met=met,
        wf_pct=wf_pct,
        h1_pass=h1_pass,
        h2_pass=h2_pass,
        n_runs=N_RUNS,
        elapsed=elapsed,
        out_path=out_dir / "verdict_2026-05-26.md",
    )

    # ── Update results.json with H3 and final verdict ─────────────────────────
    if results_path.exists():
        try:
            saved = json.loads(results_path.read_text(encoding="utf-8"))
            if saved:
                saved[0]["p_pass_30d"] = row_30["p_pass"]
                saved[0]["p_bust_30d"] = row_30["p_bust"]
                saved[0]["p_pass_7d"]  = next(r for r in mc_stats if r["cap"] == 7)["p_pass"]
                saved[0]["mc_n_mnq"]   = N_MNQ
                saved[0]["mc_n_runs"]  = N_RUNS
                saved[0]["mc_calibration"] = calib
                saved[0]["h3_pass"]    = h3_pass
                all_pass_final = h1_pass and h2_pass and h3_pass
                saved[0]["verdict"]    = "GO_PAPER" if all_pass_final else (
                    "H1_FAIL" if not h1_pass else (
                    "H2_FAIL" if not h2_pass else "H3_FAIL"
                ))
                results_path.write_text(json.dumps(saved, indent=2), encoding="utf-8")
                print(f"\n  [results.json updated with H3 and final verdict]")
        except Exception as e:
            print(f"  WARNING: Could not update results.json: {e}")


if __name__ == "__main__":
    main()
