"""
iter_06.py — Constant Dollar Risk Sizing
==========================================
ROOT CAUSE (from iter_05 forensics): SL in dollars = 0.5×R×$20×1 contract.
On catastrophic days (R = 4× normal), loss is 4×. Not a signal failure —
uncapped position sizing relative to volatility.

CORRECT FIX: size inversely with opening range so every trade risks ~$300.
  contracts = target_risk / (sl_points × POINT_VALUE), clipped [0.1, 2.0]
  fractional = /MNQ micro-equivalent (10 MNQ = 1 NQ)

BUILD ON: iter_2a (Opening momentum + VWAP filter) + Fix B 1.2% gap filter.
Fix A (dollar cap) is redundant when risk per trade is already constant.

Variants:
  6a: Constant $300 risk, no gap filter (pure sizing effect)
  6b: Constant $300 risk + 1.2% gap filter (natural combination)
  6c: Constant $300 risk + 1.2% gap + max 1.0 contract (no leverage)
  6d: Constant $200 risk + 1.2% gap filter (conservative)
  6e: Constant $400 risk + 1.2% gap filter (aggressive)

Propfirm context ($50K account):
  Max drawdown gate: -10% = -$5,000 absolute
  With $300/trade risk, expected max streak ≈ 18 losses → $5,400 = 10.8%
  With $250/trade risk: $4,500 = 9.0% → comfortably clears

n_tests: 111 → 116
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results, print_comparison_table
)
from Futures.research.active.nq_intraday.iter_05 import build_opening_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 111
ACCOUNT_SIZE  = 50_000.0   # propfirm account for MaxDD% context

BASE_TP_MULT  = 1.5
BASE_SL_MULT  = 0.5
MIN_CONTRACTS = 0.1        # 1 /MNQ micro contract
MAX_CONTRACTS = 2.0        # hard leverage cap

# Reference benchmarks (from prior iterations)
REFS = {
    "iter_2a":         {"sharpe": 0.808,  "max_dd": -0.311, "pf": 1.174, "n": 622,  "p_ev": 0.069},
    "A$400+B1.2% (05)":{"sharpe": 1.213,  "max_dd": -0.251, "pf": 1.280, "n": 567,  "p_ev": 0.019},
}

PROPFIRM_GATES = {
    "sharpe":  1.00,
    "max_dd": -0.10,   # as fraction of account, must be ≥ -0.10
    "pf":      1.20,
    "wf_pct":  65.0,
    "p_ev":    0.05,
}


# ────────────────────────────────────────────────────────────────────────────
# Signal + sizing builder
# ────────────────────────────────────────────────────────────────────────────

def build_sized_signals(feats: pd.DataFrame,
                        target_risk: float,
                        gap_thresh: Optional[float],
                        max_contr:  float = MAX_CONTRACTS) -> pd.DataFrame:
    """
    iter_2a base (VWAP filter) with constant-dollar-risk sizing.
    Each trade risks exactly target_risk USD (before costs).

    contracts = target_risk / (0.5 × rng × POINT_VALUE), clipped [MIN, max_contr]
    """
    rows = []
    f = feats[feats["vwap_ok"]].copy()

    if gap_thresh is not None:
        f = f[f["gap_pct"].abs() <= gap_thresh]

    for _, row in f.iterrows():
        rng   = float(row["rng"])
        sl_pts = rng * BASE_SL_MULT
        # Dollar risk at 1 contract
        risk_1c = sl_pts * POINT_VALUE
        # Scale contracts to hit target_risk
        raw_c   = target_risk / risk_1c if risk_1c > 0 else MIN_CONTRACTS
        contracts = float(np.clip(raw_c, MIN_CONTRACTS, max_contr))

        rows.append({
            "signal_ts": row["sig_ts"],
            "direction": int(row["direction"]),
            "tp_points": rng * BASE_TP_MULT,
            "sl_points": sl_pts,
            "exit_time": row["exit_time"],
            "rng":       rng,
            "contracts": contracts,
            "risk_usd":  sl_pts * POINT_VALUE * contracts,  # actual risk after clipping
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ────────────────────────────────────────────────────────────────────────────
# Custom backtest engine with fractional sizing
# ────────────────────────────────────────────────────────────────────────────

def run_sized(engine: NQBacktestEngine,
              signals: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Execute signals with per-trade contract sizing.
    signals must have 'contracts' column.
    P&L = direction × (exit - entry) × contracts × POINT_VALUE - COST_RT × contracts
    """
    trades: List[dict] = []

    for sig_ts, sig in signals.iterrows():
        direction   = int(sig["direction"])
        tp_pts      = float(sig["tp_points"])
        sl_pts      = float(sig["sl_points"])
        exit_ts_sig = sig["exit_time"]
        contracts   = float(sig.get("contracts", 1.0))

        future = engine.rth[engine.rth.index > sig_ts]
        if future.empty:
            continue
        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        if direction == 1:
            tp_price = entry_price + tp_pts
            sl_price = entry_price - sl_pts
        else:
            tp_price = entry_price - tp_pts
            sl_price = entry_price + sl_pts

        window = engine.rth[
            (engine.rth.index >= entry_bar) &
            (engine.rth.index <= exit_ts_sig)
        ]

        exit_price  = None
        exit_reason = "time"
        bars_held   = 0
        exit_bar_ts = window.index[-1] if not window.empty else entry_bar

        for bar_ts, bar in window.iterrows():
            bars_held += 1
            if direction == 1:
                if float(bar["low"])  <= sl_price:
                    exit_price, exit_reason, exit_bar_ts = sl_price, "sl", bar_ts
                    break
                if float(bar["high"]) >= tp_price:
                    exit_price, exit_reason, exit_bar_ts = tp_price, "tp", bar_ts
                    break
            else:
                if float(bar["high"]) >= sl_price:
                    exit_price, exit_reason, exit_bar_ts = sl_price, "sl", bar_ts
                    break
                if float(bar["low"])  <= tp_price:
                    exit_price, exit_reason, exit_bar_ts = tp_price, "tp", bar_ts
                    break

        if exit_price is None:
            if window.empty:
                continue
            exit_price  = float(window.iloc[-1]["close"])
            exit_reason = "time"
            exit_bar_ts = window.index[-1]

        pnl_pts = direction * (exit_price - entry_price)
        pnl_usd = pnl_pts * POINT_VALUE * contracts - COST_RT * contracts

        trades.append({
            "signal_ts":   sig_ts,
            "entry_ts":    entry_bar,
            "exit_ts":     exit_bar_ts,
            "direction":   direction,
            "entry_price": entry_price,
            "exit_price":  exit_price,
            "exit_reason": exit_reason,
            "pnl_pts":     round(pnl_pts, 4),
            "contracts":   round(contracts, 3),
            "pnl_usd":     round(pnl_usd, 2),
            "risk_usd":    round(sig.get("risk_usd", sl_pts * POINT_VALUE * contracts), 2),
            "bars_held":   bars_held,
        })

    tl = pd.DataFrame(trades)
    if tl.empty:
        return tl, {}
    met = metrics_sized(tl, engine)
    return tl, met


def metrics_sized(tl: pd.DataFrame, engine: NQBacktestEngine) -> dict:
    """Extended metrics including contract distribution and account-based MaxDD."""
    base = engine.metrics(tl)  # standard metrics on dollar P&L

    # Contract distribution
    c = tl["contracts"]
    dist = {
        "contr_avg":    round(float(c.mean()), 3),
        "contr_p10":    round(float(c.quantile(0.10)), 3),
        "contr_p50":    round(float(c.median()), 3),
        "contr_p90":    round(float(c.quantile(0.90)), 3),
        "contr_pct_lt05": round(float((c < 0.5).mean() * 100), 1),   # < 0.5c (MNQ territory)
        "contr_pct_gt10": round(float((c > 1.0).mean() * 100), 1),   # > 1c (leveraged)
    }

    # Risk consistency
    if "risk_usd" in tl.columns:
        r = tl["risk_usd"]
        dist["risk_mean"] = round(float(r.mean()), 2)
        dist["risk_std"]  = round(float(r.std(ddof=1)), 2)

    # Account-relative MaxDD (vs $50K account)
    tl_copy = tl.copy()
    tl_copy["date"] = pd.to_datetime(tl_copy["entry_ts"]).dt.normalize()
    daily_pnl = tl_copy.groupby("date")["pnl_usd"].sum()
    cum = daily_pnl.cumsum()
    dd_usd = float((cum - cum.cummax()).min())   # worst drawdown in absolute dollars
    max_dd_account = dd_usd / ACCOUNT_SIZE       # as fraction of $50K account

    dist["max_dd_usd"]     = round(dd_usd, 2)
    dist["max_dd_account"] = round(max_dd_account, 4)

    return {**base, **dist}


# ────────────────────────────────────────────────────────────────────────────
# Walk-forward wrapper
# ────────────────────────────────────────────────────────────────────────────

def make_signal_fn(target_risk: float, gap_thresh: Optional[float],
                   max_contr: float = MAX_CONTRACTS):
    def signal_fn(df_window: pd.DataFrame, params: dict) -> pd.DataFrame:
        feats = build_opening_features(df_window)
        sigs  = build_sized_signals(feats, target_risk, gap_thresh, max_contr)
        # strip the 'contracts' and 'risk_usd' columns so the stock engine
        # can process it (WF uses engine.run, not run_sized — handled below)
        return sigs
    return signal_fn


def walk_forward_sized(engine: NQBacktestEngine,
                       target_risk: float,
                       gap_thresh:  Optional[float],
                       max_contr:   float = MAX_CONTRACTS,
                       train_months: int = 12,
                       test_months:  int = 6) -> dict:
    """Roll walk-forward using run_sized for each OOS window."""
    dates = pd.Series(engine.rth.index.normalize().unique()).sort_values()
    total_m = (dates.iloc[-1].year  - dates.iloc[0].year) * 12 + \
              (dates.iloc[-1].month - dates.iloc[0].month)

    windows = []
    start_m = 0
    while start_m + train_months + test_months <= total_m:
        train_start = dates.iloc[0] + pd.DateOffset(months=start_m)
        train_end   = train_start   + pd.DateOffset(months=train_months)
        test_end    = train_end     + pd.DateOffset(months=test_months)

        oos = engine.rth[
            (engine.rth.index >= train_end) &
            (engine.rth.index <  test_end)
        ]
        if len(oos) < 100:
            start_m += test_months
            continue

        eng_oos      = NQBacktestEngine.__new__(NQBacktestEngine)
        eng_oos.df   = oos
        eng_oos.rth  = oos

        try:
            feats_oos = build_opening_features(oos)
            sigs_oos  = build_sized_signals(feats_oos, target_risk, gap_thresh, max_contr)
            if sigs_oos.empty:
                start_m += test_months
                continue
            tl_oos, met_oos = run_sized(eng_oos, sigs_oos)
            windows.append({
                "train_start": str(train_start.date()),
                "test_end":    str(test_end.date()),
                **met_oos,
            })
        except Exception as e:
            log.warning("WF window failed: %s", e)

        start_m += test_months

    if not windows:
        return {"n_windows": 0, "wf_pct_positive": np.nan}
    pct_pos = float(np.mean([w.get("total_pnl_usd", 0) > 0 for w in windows])) * 100
    return {"n_windows": len(windows), "wf_pct_positive": round(pct_pos, 1), "windows": windows}


# ────────────────────────────────────────────────────────────────────────────
# Contract distribution report
# ────────────────────────────────────────────────────────────────────────────

def print_contract_dist(tl: pd.DataFrame, label: str) -> None:
    if tl.empty or "contracts" not in tl.columns:
        return
    c = tl["contracts"]
    bins = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
    print(f"\n  Contract distribution [{label}]:")
    for lo, hi in bins:
        n   = ((c >= lo) & (c < hi)).sum()
        pct = n / len(c) * 100
        print(f"    [{lo:.1f}–{hi:.1f}c): {n:>4} trades ({pct:.1f}%)")
    if "risk_usd" in tl.columns:
        r = tl["risk_usd"]
        print(f"  Risk/trade: mean=${r.mean():.1f}  std=${r.std():.1f}  "
              f"min=${r.min():.1f}  max=${r.max():.1f}")


# ────────────────────────────────────────────────────────────────────────────
# Gate check
# ────────────────────────────────────────────────────────────────────────────

def check_gates(met: dict) -> Tuple[str, list]:
    sh  = met.get("sharpe_daily_hac") or 0
    mdd = met.get("max_dd_account")   or met.get("max_dd_pct") or 0
    pf  = met.get("profit_factor")    or 0
    wf  = met.get("wf_pct_positive")  or 0
    p   = met.get("p_ev_zero")        or 1.0

    gates = [
        ("Sharpe ≥ 1.0",    sh  >= PROPFIRM_GATES["sharpe"]),
        ("MaxDD ≥ -10%",     mdd >= PROPFIRM_GATES["max_dd"]),
        ("PF ≥ 1.20",        pf  >= PROPFIRM_GATES["pf"]),
        ("WF% ≥ 65%",        wf  >= PROPFIRM_GATES["wf_pct"]),
        ("P(EV≤0) ≤ 0.05",   p   <= PROPFIRM_GATES["p_ev"]),
    ]
    passed = [name for name, ok in gates if ok]
    failed = [name for name, ok in gates if not ok]
    n_pass = len(passed)

    if n_pass == 5:
        verdict = "PROPFIRM_PASS"
    elif n_pass >= 4:
        verdict = "RESEARCH_PASS"
    elif n_pass >= 3:
        verdict = "IMPROVE"
    else:
        verdict = "WEAK"

    return verdict, failed


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Iter 06 — Constant Dollar Risk Sizing ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features...")
    feats = build_opening_features(engine.rth)
    log.info(f"Features: {len(feats)}  |  VWAP ok: {feats['vwap_ok'].sum()}")

    # Sanity check: show opening range distribution
    vf = feats[feats["vwap_ok"]]["rng"]
    log.info(f"Opening range (VWAP-filtered): "
             f"p10={vf.quantile(0.1):.1f}  p50={vf.median():.1f}  "
             f"p90={vf.quantile(0.9):.1f}  max={vf.max():.1f}")

    VARIANTS = {
        "6a": dict(target_risk=300.0, gap_thresh=None,   max_contr=MAX_CONTRACTS),
        "6b": dict(target_risk=300.0, gap_thresh=0.012,  max_contr=MAX_CONTRACTS),
        "6c": dict(target_risk=300.0, gap_thresh=0.012,  max_contr=1.0),
        "6d": dict(target_risk=200.0, gap_thresh=0.012,  max_contr=MAX_CONTRACTS),
        "6e": dict(target_risk=400.0, gap_thresh=0.012,  max_contr=MAX_CONTRACTS),
    }

    n_test       = N_TESTS_START
    all_results  = []
    best_sharpe  = -np.inf
    best_variant = None
    best_tl      = None
    best_met     = None

    header_printed = False

    for var_id, cfg in VARIANTS.items():
        n_test += 1
        sigs = build_sized_signals(feats, **cfg)
        log.info(f"--- Variant {var_id}: {len(sigs)} signals, "
                 f"target_risk=${cfg['target_risk']}, gap={cfg['gap_thresh']}, "
                 f"max_c={cfg['max_contr']} ---")

        if len(sigs) < 20:
            log.warning(f"Too few signals — skipping {var_id}")
            continue

        tl, met = run_sized(engine, sigs)
        boot    = engine.bootstrap_ev(tl)
        wf      = walk_forward_sized(engine, **cfg)

        met["wf_pct_positive"] = wf.get("wf_pct_positive")
        met["wf_n_windows"]    = wf.get("n_windows")

        verdict, failed_gates = check_gates(met)

        sh   = met.get("sharpe_daily_hac")  or 0
        mdd  = met.get("max_dd_pct")        or 0
        mdd_acc = met.get("max_dd_account") or 0
        mdd_usd = met.get("max_dd_usd")     or 0
        pf   = met.get("profit_factor")     or 0
        n    = met.get("n_trades",  0)
        wfp  = met.get("wf_pct_positive")   or 0
        p_ev = boot.get("p_ev_zero")        or 1.0
        cavg = met.get("contr_avg")         or 1.0
        wday = met.get("worst_day_usd")     or 0

        result = {
            "iteration":       f"iter_{var_id}",
            "n_tests":         n_test,
            "description":     (
                f"Const-risk ${cfg['target_risk']:.0f}"
                + (f" gap≤{cfg['gap_thresh']*100:.1f}%" if cfg['gap_thresh'] else "")
                + (f" maxC={cfg['max_contr']}"           if cfg['max_contr'] < 2.0 else "")
            ),
            **met,
            **boot,
            "verdict": verdict,
        }
        append_result(result)
        all_results.append(result)

        if not header_printed:
            print("\n" + "=" * 110)
            print(f"{'Variant':<26} {'Sh':>7} {'MaxDD%':>8} {'MaxDD$':>8} "
                  f"{'PF':>6} {'WF%':>6} {'N':>5} {'P(EV≤0)':>8} "
                  f"{'C_avg':>6} {'WorstDay':>9} {'Verdict'}")
            print("-" * 110)
            header_printed = True

        dd_pf = mdd_acc * 100   # as % of $50K account
        print(f"  iter_{var_id:<22} {sh:>+7.3f} {mdd*100:>7.1f}% {mdd_usd:>8.0f} "
              f"{pf:>6.3f} {wfp:>5.1f}% {n:>5} {p_ev:>8.3f} "
              f"{cavg:>6.2f} {wday:>9.1f}  {verdict}")

        if failed_gates:
            print(f"    ✗ Failed: {', '.join(failed_gates)}")
        else:
            print(f"    ✓ ALL PROPFIRM GATES PASSED")

        print_contract_dist(tl, f"iter_{var_id}")

        if sh > best_sharpe:
            best_sharpe  = sh
            best_variant = var_id
            best_tl      = tl
            best_met     = met

    # ──────────────────────────────────────────────────────────────────
    # Full comparison table
    # ──────────────────────────────────────────────────────────────────
    print_comparison_table(load_results())

    # ──────────────────────────────────────────────────────────────────
    # STOP condition check
    # ──────────────────────────────────────────────────────────────────
    r_6b = next((r for r in all_results if r.get("iteration") == "iter_6b"), None)
    if r_6b:
        sh_6b  = r_6b.get("sharpe_daily_hac") or 0
        mdd_6b = r_6b.get("max_dd_pct") or 0
        if sh_6b < 0.6 or mdd_6b < -0.251:   # worse than A$400+B1.2%
            print("\nSTOP: iter_6b underperforms iter_05 best (A$400+B1.2%).")
            print("Constant sizing is not improving the strategy — re-evaluate approach.")

    # ──────────────────────────────────────────────────────────────────
    # Final verdict
    # ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"ITER 06 FINAL — Best variant: iter_{best_variant}")
    print("=" * 80)

    if best_met:
        sh   = best_met.get("sharpe_daily_hac") or 0
        mdd  = best_met.get("max_dd_pct") or 0
        mdd_acc = best_met.get("max_dd_account") or 0
        mdd_usd = best_met.get("max_dd_usd") or 0
        pf   = best_met.get("profit_factor") or 0
        n    = best_met.get("n_trades", 0)
        wfp  = best_met.get("wf_pct_positive") or 0
        p_ev_r = next((r.get("p_ev_zero", 1) for r in all_results
                       if r.get("iteration") == f"iter_{best_variant}"), 1.0)

        print(f"  Sharpe={sh:.3f}  MaxDD={mdd*100:.1f}%  "
              f"MaxDD_$50K={mdd_acc*100:.1f}%  MaxDD_usd=${mdd_usd:.0f}")
        print(f"  PF={pf:.3f}  WF={wfp:.0f}%  N={n}  P(EV≤0)={p_ev_r:.3f}")
        print()

        verdict, failed = check_gates(best_met)

        if verdict == "PROPFIRM_PASS":
            print("  DECISION: PROPFIRM PASS")
            print("  Ready for paper trading. Commit and deploy.")
            print("  Strategy: Opening momentum + VWAP filter + constant-risk sizing")
            print(f"  Config: target_risk=${VARIANTS[best_variant]['target_risk']:.0f}, "
                  f"gap_thresh={VARIANTS[best_variant].get('gap_thresh','None')}, "
                  f"max_contracts={VARIANTS[best_variant]['max_contr']}")
        elif verdict == "RESEARCH_PASS":
            mdd_rem = abs(mdd_acc * 100) - 10.0
            print(f"  DECISION: RESEARCH PASS (4/5 gates)")
            print(f"  MaxDD still {mdd_acc*100:.1f}% vs -10% gate (gap: {mdd_rem:.1f}pp).")
            print(f"  Paper trade at HALF target risk (${VARIANTS[best_variant]['target_risk']/2:.0f}/trade).")
            print(f"  → MaxDD estimate: ~{mdd_acc*100/2:.1f}% at half size.")
            print(f"  Failed gate(s): {', '.join(failed)}")
        else:
            print(f"  DECISION: {verdict} — {', '.join(failed)} still failing.")
            print("  Design iter_07 targeting the dominant remaining failure mode.")

    print(f"\nn_tests: {N_TESTS_START} → {n_test}")
    print("DO NOT COMMIT until review.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_06 failed")
        sys.exit(1)
