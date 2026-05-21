"""
iter_10_refined.py — Strategy C Refined: A$400 + B1.2% + M1(rng≥30)
======================================================================
Combines iter_05_A400+B012 with the adopted range filter (rng_min=30 pts).

Parts run:
  D1 — Full backtest + gate matrix
  D2 — Extended walk-forward (6M/3M, 9 windows)
  D3 — FTMO trailing-DD Monte Carlo (10,000 paths × 30 trading days)
  E  — Regime analysis (observational only)

Generates: analysis/refinement_summary.md

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.iter_10_refined
n_tests: 141 → 142
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT, append_result,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)
from Futures.research.active.nq_intraday.iter_07_validation import sharpe_hac
from Futures.research.active.nq_intraday.analysis.conditional_analysis import (
    build_context, load_vix,
)
from Futures.research.active.nq_intraday.analysis.signal_refinements import extended_wf

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

STRATEGY_GAP   = 0.012
STRATEGY_STOP  = 400.0
RNG_MIN        = 30.0           # M1 adopted filter
N_TESTS_START  = 141

# Gate thresholds
RESEARCH_SHARPE   = 0.7
PROPFIRM_SHARPE   = 1.0
RESEARCH_MDD      = -0.20
PROPFIRM_MDD      = -0.10
RESEARCH_WF       = 55.0

# FTMO Monte Carlo parameters
FTMO_INITIAL      = 100_000.0   # $100K starting balance
FTMO_TARGET_PCT   = 0.10        # 10% profit target = $10K
FTMO_DD_PCT       = 0.10        # 10% trailing drawdown limit
FTMO_DAYS         = 30          # trading days to simulate
MC_PATHS          = 10_000
MC_SEED           = 42


# ─────────────────────────────────────────────────────────────────────────────
# Signal builder
# ─────────────────────────────────────────────────────────────────────────────

def build_signals(feats: pd.DataFrame) -> pd.DataFrame:
    """iter_10: VWAP + A$400 + B1.2% + M1(rng≥30pt)."""
    feats_filtered = feats[feats["rng"] >= RNG_MIN].copy()
    return signals_from_features(
        feats_filtered,
        gap_thresh=STRATEGY_GAP,
        dollar_stop=STRATEGY_STOP,
    )


def signal_fn_iter10(df_1min: pd.DataFrame, params: dict) -> pd.DataFrame:
    feats_w = build_opening_features(df_1min)
    return build_signals(feats_w)


# ─────────────────────────────────────────────────────────────────────────────
# PART D1 — Full backtest + gate matrix
# ─────────────────────────────────────────────────────────────────────────────

def part_d1(engine: NQBacktestEngine,
            tl: pd.DataFrame, met: dict,
            baseline: dict) -> None:
    print("\n" + "═" * 80)
    print("PART D1 — FULL BACKTEST + GATE MATRIX")
    print("═" * 80)

    sh  = met.get("sharpe_daily_hac") or 0
    mdd = met.get("max_dd_pct") or 0
    pf  = met.get("profit_factor") or 0
    n   = met.get("n_trades", 0)
    wr  = met.get("win_rate", 0)
    tot = met.get("total_pnl_usd", 0)

    boot = engine.bootstrap_ev(tl)
    p_ev = boot.get("p_ev_zero", np.nan)

    # Short WF (12M/6M) for gate check
    short_wf = engine.walk_forward(signal_fn_iter10, {},
                                    train_months=12, test_months=6)
    wf_pct  = short_wf.get("wf_pct_positive", 0)

    print(f"\n  iter_10 vs baseline (iter_05_A400+B012):")
    print(f"  {'Metric':<28} {'iter_10':>12} {'Baseline':>12} {'Delta':>10}")
    print(f"  {'-'*64}")
    metrics = [
        ("N trades",    f"{n}",         f"{baseline['n_trades']}",  f"{n-baseline['n_trades']:+d}"),
        ("Win rate",    f"{wr*100:.1f}%", f"{baseline['wr']*100:.1f}%", ""),
        ("Sharpe HAC",  f"{sh:.4f}",     f"{baseline['sharpe']:.4f}", f"{sh-baseline['sharpe']:+.4f}"),
        ("MaxDD",       f"{mdd*100:.1f}%", f"{baseline['mdd']*100:.1f}%", f"{(mdd-baseline['mdd'])*100:+.1f}pp"),
        ("PF",          f"{pf:.4f}",     f"{baseline['pf']:.4f}",   f"{pf-baseline['pf']:+.4f}"),
        ("Total P&L",   f"${tot:,.0f}",  f"${baseline['total']:,.0f}", f"${tot-baseline['total']:,.0f}"),
        ("P(EV≤0)",     f"{p_ev:.4f}",   f"{baseline['p_ev']:.4f}",  ""),
        ("WF% (12/6)",  f"{wf_pct:.0f}%", f"{baseline['wf_pct']:.0f}%", ""),
    ]
    for m in metrics:
        print(f"  {m[0]:<28} {m[1]:>12} {m[2]:>12} {m[3]:>10}")

    # Gate matrix
    print(f"\n  Gate matrix:")
    print(f"  {'Gate':<30} {'Required':>12} {'Actual':>12} {'Pass?':>7}")
    print(f"  {'-'*64}")

    def gate(label, req_val, actual_val, req_str, actual_str, higher_better=True):
        pss = (actual_val >= req_val) if higher_better else (actual_val <= req_val)
        mark = "PASS" if pss else "FAIL"
        print(f"  {label:<30} {req_str:>12} {actual_str:>12} {mark:>7}")
        return pss

    g1 = gate("Sharpe ≥ 1.0 (PROPFIRM)",  1.0,   sh,       "≥1.0",   f"{sh:.4f}")
    g2 = gate("MaxDD ≥ -10% (PROPFIRM)",  -0.10,  mdd,      "≥-10%",  f"{mdd*100:.1f}%")
    g3 = gate("Sharpe ≥ 0.7 (RESEARCH)",  0.7,   sh,       "≥0.7",   f"{sh:.4f}")
    g4 = gate("MaxDD ≥ -20% (RESEARCH)",  -0.20,  mdd,      "≥-20%",  f"{mdd*100:.1f}%")
    g5 = gate("WF% ≥ 55% (RESEARCH)",     55.0,  wf_pct,   "≥55%",   f"{wf_pct:.0f}%")
    g6 = gate("P(EV≤0) < 0.05",           0.05,  p_ev,     "<0.05",  f"{p_ev:.4f}", higher_better=False)

    if sh >= PROPFIRM_SHARPE and mdd >= PROPFIRM_MDD and pf >= 1.20:
        verdict = "PROPFIRM_PASS"
    elif sh >= RESEARCH_SHARPE and mdd >= RESEARCH_MDD and wf_pct >= RESEARCH_WF:
        verdict = "RESEARCH_PASS"
    else:
        verdict = "FAIL"

    print(f"\n  VERDICT: {verdict}")
    return {
        "sharpe": sh, "max_dd": mdd, "pf": pf, "n_trades": n,
        "win_rate": wr, "total_pnl": tot, "p_ev": p_ev,
        "wf_pct_short": wf_pct, "verdict": verdict,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART D2 — Extended walk-forward
# ─────────────────────────────────────────────────────────────────────────────

def part_d2(engine: NQBacktestEngine) -> dict:
    print("\n" + "═" * 80)
    print("PART D2 — EXTENDED WALK-FORWARD (6M train / 3M test)")
    print("═" * 80)

    wf = extended_wf(engine, signal_fn_iter10)
    windows = wf.get("windows", [])

    print(f"\n  {'#':<3} {'OOS start':<12} {'OOS end':<12} "
          f"{'N':>5} {'Sh':>8} {'PnL$':>8} {'+'}")
    print(f"  {'-'*55}")
    for i, w in enumerate(windows, 1):
        sh_s = f"{w['sharpe']:.3f}" if w.get("sharpe") else "  N/A"
        pos  = "✓" if w["positive"] else "✗"
        print(f"  {i:<3} {w['oos_start']:<12} {w['oos_end']:<12} "
              f"{w['n_trades']:>5} {sh_s:>8} {w['total_pnl']:>8.0f} {pos}")

    n_pos = sum(w["positive"] for w in windows)
    n_tot = len(windows)
    pct   = n_pos / n_tot * 100 if n_tot > 0 else 0
    sh_vals = [w["sharpe"] for w in windows if w.get("sharpe") is not None]
    med_sh  = float(np.median(sh_vals)) if sh_vals else np.nan

    print(f"\n  Summary: {n_tot} windows  |  {n_pos} positive ({pct:.0f}%)")
    print(f"  Median OOS Sharpe: {med_sh:.3f}" if np.isfinite(med_sh) else "  Median OOS Sharpe: N/A")
    print(f"  Total OOS P&L: ${wf['total_pnl']:,.0f}")

    return {"n_windows": n_tot, "wf_pct": pct, "median_sharpe": med_sh,
            "total_pnl": wf["total_pnl"]}


# ─────────────────────────────────────────────────────────────────────────────
# PART D3 — FTMO trailing-DD Monte Carlo
# ─────────────────────────────────────────────────────────────────────────────

def part_d3(trade_log: pd.DataFrame) -> dict:
    print("\n" + "═" * 80)
    print("PART D3 — FTMO TRAILING-DD MONTE CARLO")
    print(f"  FTMO params: ${FTMO_INITIAL:,.0f} initial  |  "
          f"+{FTMO_TARGET_PCT*100:.0f}% target (${FTMO_INITIAL*FTMO_TARGET_PCT:,.0f})  |  "
          f"{FTMO_DD_PCT*100:.0f}% trailing DD (${FTMO_INITIAL*FTMO_DD_PCT:,.0f})  |  "
          f"{FTMO_DAYS} trading days  |  {MC_PATHS:,} paths  |  1 contract")
    print("═" * 80)

    # Build daily P&L including zero days (days with no trade)
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    daily_trade = tl.groupby("date")["pnl_usd"].sum()

    # All trading days (expand to zero-return days)
    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max(), freq="C", holidays=[])
    daily_pnl = daily_trade.reindex(pd.DatetimeIndex(all_dates).normalize(), fill_value=0.0)

    print(f"\n  Historical daily P&L statistics ({len(daily_pnl)} trading days):")
    print(f"    Mean:   ${daily_pnl.mean():.1f}  |  Std: ${daily_pnl.std():.1f}")
    print(f"    Min:    ${daily_pnl.min():.1f}  |  Max: ${daily_pnl.max():.1f}")
    print(f"    Non-zero days: {(daily_pnl != 0).sum()}")

    pnl_arr = daily_pnl.values.astype(float)
    rng_gen = np.random.default_rng(MC_SEED)

    target   = FTMO_INITIAL * FTMO_TARGET_PCT   # $10,000
    dd_limit = FTMO_INITIAL * FTMO_DD_PCT        # $10,000

    n_success = 0
    n_bust    = 0
    n_neither = 0
    peak_dds  = []
    final_pnls = []

    for _ in range(MC_PATHS):
        # Sample FTMO_DAYS P&L values from historical distribution
        path_pnl = rng_gen.choice(pnl_arr, size=FTMO_DAYS, replace=True)

        equity      = FTMO_INITIAL
        max_equity  = FTMO_INITIAL
        bust        = False
        success_day = None

        for day_pnl in path_pnl:
            equity += day_pnl
            if equity > max_equity:
                max_equity = equity

            # Trailing stop: floor = max_equity × (1 - DD_PCT)
            trailing_floor = max_equity * (1 - FTMO_DD_PCT)
            if equity <= trailing_floor:
                bust = True
                break

            if success_day is None and (equity - FTMO_INITIAL) >= target:
                success_day = True

        final_pnl = equity - FTMO_INITIAL
        peak_dd   = (equity - max_equity) / FTMO_INITIAL

        if bust:
            n_bust    += 1
            peak_dds.append(peak_dd)
        elif success_day:
            n_success += 1
            peak_dds.append(peak_dd)
        else:
            n_neither += 1
            peak_dds.append(peak_dd)
        final_pnls.append(final_pnl)

    p_success = n_success / MC_PATHS
    p_bust    = n_bust    / MC_PATHS
    p_neither = n_neither / MC_PATHS

    final_arr = np.array(final_pnls)
    ci_lo, ci_hi = np.percentile(final_arr, [5, 95])

    print(f"\n  Monte Carlo results ({MC_PATHS:,} paths × {FTMO_DAYS} days):")
    print(f"    P(reach +${target:,.0f} profit target)  = {p_success*100:.1f}%")
    print(f"    P(trailing DD breach)                = {p_bust*100:.1f}%")
    print(f"    P(neither in {FTMO_DAYS} days)           = {p_neither*100:.1f}%")
    print(f"    E[final P&L]:  ${final_arr.mean():,.0f}  "
          f"[5th: ${ci_lo:,.0f}  |  95th: ${ci_hi:,.0f}]")
    print(f"    E[trailing DD breach size]: "
          f"{np.mean([d for d in peak_dds if d < -0.001])*100:.1f}% of initial")

    # FTMO compatibility verdict
    if p_success >= 0.40 and p_bust <= 0.20:
        ftmo_verdict = "FTMO_COMPATIBLE"
    elif p_success >= 0.25 and p_bust <= 0.35:
        ftmo_verdict = "MARGINAL"
    else:
        ftmo_verdict = "FTMO_RISKY"

    print(f"\n  FTMO verdict: {ftmo_verdict}")

    return {
        "p_success": p_success, "p_bust": p_bust, "p_neither": p_neither,
        "mean_final_pnl": float(final_arr.mean()),
        "ci_lo": float(ci_lo), "ci_hi": float(ci_hi),
        "ftmo_verdict": ftmo_verdict,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART E — Regime analysis (observational)
# ─────────────────────────────────────────────────────────────────────────────

def part_e(tl_ctx: pd.DataFrame, engine: NQBacktestEngine) -> None:
    print("\n" + "═" * 80)
    print("PART E — REGIME ANALYSIS (observational, no signal changes)")
    print("═" * 80)

    # Regime 1: NQ 12-month trend (bull/bear/sideways)
    rth_close = (
        engine.rth[(engine.rth.index.time >= pd.Timestamp("09:30").time()) &
                   (engine.rth.index.time <= pd.Timestamp("15:59").time())]
        ["close"].resample("B").last().dropna()
    )
    rth_close.index = rth_close.index.normalize()

    ret_12m = (rth_close / rth_close.shift(252) - 1).shift(1)  # no lookahead

    def _regime(r):
        if not np.isfinite(r): return "Unknown"
        if r > 0.10:  return "Bull (>+10%)"
        if r < -0.10: return "Bear (<-10%)"
        return "Sideways (±10%)"

    tl_ctx = tl_ctx.copy()
    # Strip tz for joining with tz-naive ret_12m index
    date_naive = tl_ctx["date"].apply(
        lambda d: d.tz_localize(None) if hasattr(d, "tz_localize") and d.tzinfo is not None else d
    )
    ret_12m_dict = {k.tz_localize(None) if hasattr(k, "tz_localize") and k.tzinfo is not None else k: v
                    for k, v in ret_12m.items()}
    tl_ctx["ret_12m"] = date_naive.map(ret_12m_dict)
    tl_ctx["regime"]  = tl_ctx["ret_12m"].apply(_regime)

    print(f"\n  --- Regime 1: 12-month NQ trend ---")
    print(f"  {'Regime':<22} {'N':>5} {'Win%':>7} {'AvgP&L':>9} {'TotalP&L':>11}")
    print(f"  {'-'*58}")
    for reg in ["Bull (>+10%)", "Sideways (±10%)", "Bear (<-10%)", "Unknown"]:
        g = tl_ctx[tl_ctx["regime"] == reg]
        if len(g) == 0: continue
        wr = (g["pnl_usd"] > 0).mean()
        print(f"  {reg:<22} {len(g):>5} {wr*100:>6.1f}% "
              f"{g['pnl_usd'].mean():>9.1f} {g['pnl_usd'].sum():>11.0f}")

    # Regime 2: VIX (from conditional analysis)
    print(f"\n  --- Regime 2: VIX regime (from context) ---")
    print(f"  {'VIX Regime':<22} {'N':>5} {'Win%':>7} {'AvgP&L':>9} {'TotalP&L':>11}")
    print(f"  {'-'*58}")
    for reg in ["Low", "Medium", "High"]:
        g = tl_ctx[tl_ctx["vix_regime"] == reg]
        if len(g) == 0: continue
        wr = (g["pnl_usd"] > 0).mean()
        print(f"  {reg:<22} {len(g):>5} {wr*100:>6.1f}% "
              f"{g['pnl_usd'].mean():>9.1f} {g['pnl_usd'].sum():>11.0f}")

    # Regime 3: Year over year
    tl_ctx["year"] = pd.to_datetime(tl_ctx["date"]).dt.year
    print(f"\n  --- Regime 3: Calendar year ---")
    print(f"  {'Year':<22} {'N':>5} {'Win%':>7} {'AvgP&L':>9} {'TotalP&L':>11} {'Sharpe':>8}")
    print(f"  {'-'*66}")
    for yr, g in tl_ctx.groupby("year"):
        wr  = (g["pnl_usd"] > 0).mean()
        g2  = g.copy()
        g2["date2"] = pd.to_datetime(g2["date"]).dt.normalize()
        daily = g2.groupby("date2")["pnl_usd"].sum()
        sh    = sharpe_hac(daily) if len(daily) >= 10 else np.nan
        sh_s  = f"{sh:.3f}" if np.isfinite(sh) else "  N/A"
        print(f"  {yr:<22} {len(g):>5} {wr*100:>6.1f}% "
              f"{g['pnl_usd'].mean():>9.1f} {g['pnl_usd'].sum():>11.0f} {sh_s:>8}")

    print(f"\n  [OBSERVATIONAL ONLY — no signal changes from regime analysis]")


# ─────────────────────────────────────────────────────────────────────────────
# Generate refinement_summary.md
# ─────────────────────────────────────────────────────────────────────────────

def write_summary(d1: dict, d2: dict, d3: dict) -> None:
    out_path = Path(__file__).parent / "refinement_summary.md"
    n_tests_end = N_TESTS_START + 1

    summary = f"""## Strategy C Refinement — iter_10 Summary

*Generated: 2026-05-21  |  n_tests: {N_TESTS_START} → {n_tests_end}*


### 1. Methodology

Starting point: **iter_05_A400+B012** — VWAP + A$400 dollar stop + B1.2% gap filter
Baseline Sharpe: 1.2132  |  MaxDD: -25.1%  |  N trades: 567

**Part A** — Descriptive analytics: 567 trades enriched with 13 contextual variables.
Key findings: Q3 range (38-63pts) avg +$184/trade, Q1 (≤20pts) avg -$15/trade. Strong range-P&L relationship.

**Part B** — 6 pre-specified hypotheses, Bonferroni p*=0.0083:
- H1 DOW effect: p=0.143 FAIL
- H2 VIX level: p=0.020 FAIL
- H3 Opening range: p≈0.000 **PASS** (Kruskal-Wallis 4-group)
- H4 Trend alignment: p=0.172 FAIL
- H5 Long/Short: p=0.481 FAIL
- H6 30-min ORB: p=0.920 FAIL

**Part C** — M1 range filter tested at rng_min ∈ {{20..50pts}}:
- rng_min=30pt adopted: ΔSharpe=+0.31, retention=61%, WF%=78% (all 3 rules passed)

**Part D** — iter_10 = baseline + M1(rng_min=30pt)


### 2. iter_10 Performance

| Metric | iter_10 | Baseline | Delta |
|--------|---------|----------|-------|
| N trades | {d1['n_trades']} | 567 | {d1['n_trades']-567:+d} |
| Win rate | {d1['win_rate']*100:.1f}% | 26.1% | |
| Sharpe HAC | {d1['sharpe']:.4f} | 1.2132 | {d1['sharpe']-1.2132:+.4f} |
| MaxDD | {d1['max_dd']*100:.1f}% | -25.1% | {(d1['max_dd']+0.2506)*100:+.1f}pp |
| Profit Factor | {d1['pf']:.4f} | 1.2798 | {d1['pf']-1.2798:+.4f} |
| Total P&L | ${d1['total_pnl']:,.0f} | $37,897 | |
| P(EV≤0) | {d1['p_ev']:.4f} | 0.0188 | |
| WF% (12M/6M) | {d1['wf_pct_short']:.0f}% | 100% | |

**Verdict: {d1['verdict']}**


### 3. Extended Walk-Forward (6M/3M)

- Windows: {d2['n_windows']}  |  Positive: {d2['wf_pct']:.0f}%
- Median OOS Sharpe: {d2['median_sharpe']:.3f}
- Total OOS P&L: ${d2['total_pnl']:,.0f}


### 4. FTMO Trailing-DD Analysis (Monte Carlo)

Parameters: $100K initial  |  +10% target ($10K)  |  10% trailing DD  |  30 days  |  {MC_PATHS:,} paths

| Outcome | Probability |
|---------|------------|
| Hit +$10K target | {d3['p_success']*100:.1f}% |
| Trailing DD breach | {d3['p_bust']*100:.1f}% |
| Neither (still running) | {d3['p_neither']*100:.1f}% |

E[final P&L]: ${d3['mean_final_pnl']:,.0f}  [5th pct: ${d3['ci_lo']:,.0f}  |  95th pct: ${d3['ci_hi']:,.0f}]

**FTMO verdict: {d3['ftmo_verdict']}**


### 5. Decision

iter_10 = **iter_05_A400+B012 + rng_min=30pt** is adopted as the refined Strategy C.

Gate matrix: See Part D1 output.
Next step: Paper trade at 1 contract, log to paper_trade_log.csv.


### 6. n_tests counter

- Start: {N_TESTS_START}
- End:   {n_tests_end} (+1 iter_10 full run)
- Total from beginning of Strategy C refinement: 134 → {n_tests_end}
"""
    out_path.write_text(summary)
    print(f"\n  [Saved: {out_path}]")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print("iter_10 — Strategy C Refined: A$400 + B1.2% + M1(rng≥30pt)")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_START+1}")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    sigs   = build_signals(feats)
    tl_raw, met = engine.run(sigs)

    print(f"\n  iter_10 full-period: {len(tl_raw)} trades  "
          f"Sh={met.get('sharpe_daily_hac',0):.4f}  "
          f"MaxDD={met.get('max_dd_pct',0)*100:.1f}%")

    # Build baseline dict for comparison
    baseline = {
        "sharpe":   1.2132, "mdd":  -0.2506,
        "n_trades": 567,    "wr":    0.261,
        "pf":       1.2798, "total": 37896.5,
        "p_ev":     0.0188, "wf_pct": 100.0,
    }

    # D1 — full backtest gate matrix
    d1 = part_d1(engine, tl_raw, met, baseline)

    # D2 — extended WF
    d2 = part_d2(engine)

    # D3 — FTMO MC
    d3 = part_d3(tl_raw)

    # E — regime analysis (needs context)
    vix = load_vix()
    tl_ctx = build_context(tl_raw, feats, engine.rth, vix)
    part_e(tl_ctx, engine)

    # Save result
    result_entry = {
        "iteration":       "iter_10",
        "n_tests":         N_TESTS_START + 1,
        "description":     "Opening+VWAP, dollar_stop=400, gap_thresh=1.2%, rng_min=30pt",
        **met,
        "p_ev_zero":       d1["p_ev"],
        "wf_pct_positive": d1["wf_pct_short"],
        "wf_pct_extended": d2["wf_pct"],
        "wf_n_windows":    d2["n_windows"],
        "ftmo_p_success":  d3["p_success"],
        "ftmo_p_bust":     d3["p_bust"],
        "ftmo_verdict":    d3["ftmo_verdict"],
        "verdict":         d1["verdict"],
    }
    append_result(result_entry)

    # Summary markdown
    write_summary(d1, d2, d3)

    print("\n" + "=" * 80)
    print(f"  FINAL VERDICT: {d1['verdict']}")
    print(f"  Sharpe={d1['sharpe']:.4f}  MaxDD={d1['max_dd']*100:.1f}%  "
          f"WF={d2['wf_pct']:.0f}%  FTMO={d3['ftmo_verdict']}")
    print(f"  n_tests: {N_TESTS_START} → {N_TESTS_START+1}")
    print("=" * 80)


if __name__ == "__main__":
    main()
