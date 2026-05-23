"""
propfirm_analysis.py — Task 1: Propfirm Compatibility Analysis (Fixed DD Rules)
=================================================================================
Strategy C iter_10: A$400 + B1.2% + rng≥30pt (346 trades, Sharpe 1.52)

Propfirm rules (FIXED, not trailing):
  max_dd_total   = 10% of initial balance (fixed from start)
  max_dd_daily   = 5%  of initial balance per calendar day
  profit_target  = 10% of initial balance (phase 1)
  time_limit     = none

/MNQ specs:
  Point value: $2/pt per /MNQ (vs $20/pt for NQ)
  Cost/RT:     $2.15/MNQ ($0.90 commission + $1.25 slippage)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.propfirm_analysis
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

STRATEGY_GAP   = 0.012
STRATEGY_STOP  = 400.0
RNG_MIN        = 30.0

# /MNQ specs
MNQ_POINT_VALUE = 2.0           # $2/pt per /MNQ
MNQ_COST_RT     = 2.15          # $2.15/RT per /MNQ

# NQ (1 full contract) to /MNQ scaling factor
# 1 NQ = 5 /MNQ from a dollar perspective ($20/pt ÷ $2/pt × some factor)
# Actually: 1 NQ ≡ 10 /MNQ by contract specification
# NQ point value $20, MNQ point value $2 → 10 MNQ = 1 NQ
NQ_TO_MNQ = 10.0                # 10 /MNQ = 1 NQ

# Backtest trade log uses 1 NQ contract with $19 RT cost
NQ_COST_RT  = 19.0
NQ_PV       = 20.0

ACCOUNT_SIZES = [50_000, 100_000]
MNQ_SIZES     = [5, 10, 15, 20]

MC_PATHS      = 10_000
MC_DAYS       = 60
MC_SEED       = 42

DD_TOTAL_PCT  = 0.10    # 10% max total DD
DD_DAILY_PCT  = 0.05    # 5%  max daily loss
TARGET_PCT    = 0.10    # 10% profit target


# ─────────────────────────────────────────────────────────────────────────────
# Scale NQ P&L to /MNQ sizing
# ─────────────────────────────────────────────────────────────────────────────

def scale_pnl(nq_pnl_usd: float, mnq_contracts: int) -> float:
    """
    Scale 1-contract NQ P&L to /MNQ sizing.

    1-NQ-contract-equivalent pnl (USD) × (mnq_contracts / NQ_TO_MNQ)
    Then subtract extra cost because /MNQ has different cost per contract:
      NQ trade cost = $19 RT already included in nq_pnl_usd
      MNQ equivalent cost = MNQ_COST_RT × mnq_contracts

    net_pnl = nq_pts × MNQ_PV × mnq_contracts - MNQ_COST_RT × mnq_contracts

    We back out from nq_pnl_usd:
      nq_pnl_usd = nq_pts × NQ_PV - NQ_COST_RT
      nq_pts = (nq_pnl_usd + NQ_COST_RT) / NQ_PV

    Then:
      mnq_pnl = nq_pts × MNQ_PV × mnq_contracts - MNQ_COST_RT × mnq_contracts
    """
    nq_pts = (nq_pnl_usd + NQ_COST_RT) / NQ_PV
    return nq_pts * MNQ_POINT_VALUE * mnq_contracts - MNQ_COST_RT * mnq_contracts


def build_daily_pnl(trade_log: pd.DataFrame, mnq_contracts: int) -> pd.Series:
    """Build daily P&L series scaled to mnq_contracts, including zero-trade days."""
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    tl["pnl_mnq"] = tl["pnl_usd"].apply(lambda x: scale_pnl(x, mnq_contracts))

    daily_trade = tl.groupby("date")["pnl_mnq"].sum()

    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max(), freq="C", holidays=[])
    daily = daily_trade.reindex(pd.DatetimeIndex(all_dates).normalize(), fill_value=0.0)
    return daily


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Fixed DD metrics
# ─────────────────────────────────────────────────────────────────────────────

def fixed_dd_metrics(daily: pd.Series, account: float) -> dict:
    """Compute fixed DD metrics from initial balance = 0 (not account value)."""
    cum = daily.cumsum()   # P&L from 0

    # Max drawdown from initial balance (peak-to-trough of cumulative P&L)
    # Fixed DD: measured from the START (0), floor = -account × DD_TOTAL_PCT
    running_max = cum.cummax()
    dd_series   = cum - running_max   # always ≤ 0
    max_dd_usd  = float(dd_series.min())  # most negative value
    max_dd_pct  = -max_dd_usd / account  # fraction of account (positive = bad)

    # Max single-day loss
    worst_day_usd = float(daily.min())
    worst_day_pct = -worst_day_usd / account

    # Days where daily loss > 5% of account
    bad_days = daily[daily < -DD_DAILY_PCT * account]

    return {
        "max_dd_usd":    round(max_dd_usd, 2),
        "max_dd_pct":    round(max_dd_pct * 100, 2),
        "worst_day_usd": round(worst_day_usd, 2),
        "worst_day_pct": round(worst_day_pct * 100, 2),
        "n_bad_days":    len(bad_days),
        "bad_days":      bad_days,
        "busted_hist":   max_dd_usd < -DD_TOTAL_PCT * account,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Bootstrap simulation
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_sim(daily: pd.Series, account: float) -> dict:
    """Monte Carlo: 10,000 paths × 60 trading days with replacement."""
    pnl_arr  = daily.values.astype(float)
    rng_gen  = np.random.default_rng(MC_SEED)

    dd_limit    = account * DD_TOTAL_PCT
    daily_limit = account * DD_DAILY_PCT
    target      = account * TARGET_PCT

    n_bust      = 0
    n_daily_vio = 0
    n_target    = 0
    days_to_target = []
    terminal_pnl   = []

    for _ in range(MC_PATHS):
        path = rng_gen.choice(pnl_arr, size=MC_DAYS, replace=True)

        cumulative  = 0.0
        peak        = 0.0
        bust        = False
        daily_hit   = False
        target_hit  = False
        target_day  = None

        for day_i, day_pnl in enumerate(path):
            cumulative += day_pnl
            if cumulative > peak:
                peak = cumulative

            # Fixed DD: measured from start (0), not from peak
            # FIXED means: if cumulative ever drops below -dd_limit, bust
            if cumulative <= -dd_limit:
                bust = True
                break

            # Daily loss check
            if day_pnl < -daily_limit:
                daily_hit = True

            # Profit target
            if not target_hit and cumulative >= target:
                target_hit = True
                target_day = day_i + 1

        terminal_pnl.append(cumulative)

        if bust:
            n_bust += 1
        if daily_hit:
            n_daily_vio += 1
        if target_hit:
            n_target += 1
            days_to_target.append(target_day)

    p_bust      = n_bust      / MC_PATHS
    p_daily_vio = n_daily_vio / MC_PATHS
    p_target    = n_target    / MC_PATHS
    med_days    = float(np.median(days_to_target)) if days_to_target else np.nan

    term_arr = np.array(terminal_pnl)
    p5_terminal = float(np.percentile(term_arr, 5))

    return {
        "p_bust":       round(p_bust * 100, 1),
        "p_daily_vio":  round(p_daily_vio * 100, 1),
        "p_target":     round(p_target * 100, 1),
        "med_days":     round(med_days, 0) if np.isfinite(med_days) else 999,
        "p5_terminal":  round(p5_terminal, 0),
        "mean_monthly": round(float(daily.mean()) * 21, 0),  # ~21 trading days/month
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Daily loss deep dive
# ─────────────────────────────────────────────────────────────────────────────

def daily_loss_deepdive(trade_log: pd.DataFrame,
                         daily: pd.Series,
                         account: float,
                         mnq_contracts: int,
                         feats: pd.DataFrame) -> None:
    daily_limit = account * DD_DAILY_PCT

    print(f"\n  Daily loss limit: ${daily_limit:,.0f} (5% of ${account:,.0f})")
    print(f"\n  Maximum possible single-trade loss at {mnq_contracts} /MNQ:")

    # Dollar stop cap
    sl_cap_usd = 400.0   # per NQ contract
    sl_cap_pts = (sl_cap_usd + NQ_COST_RT) / NQ_PV    # pts covered by dollar stop
    # At MNQ sizing: worst loss = sl_cap_pts × MNQ_PV × mnq_contracts + costs
    worst_trade = sl_cap_pts * MNQ_POINT_VALUE * mnq_contracts + MNQ_COST_RT * mnq_contracts
    worst_trade_pct = worst_trade / account * 100

    print(f"    Dollar stop cap: ${sl_cap_usd:.0f}/NQ-contract")
    print(f"    Cap in pts: {sl_cap_pts:.2f} pts")
    print(f"    Worst MNQ loss: ${worst_trade:.0f} ({worst_trade_pct:.2f}% of account)")
    print(f"    Max 1 trade/day → this IS the daily max loss.")
    if worst_trade < daily_limit:
        print(f"    ✓ Structurally IMPOSSIBLE to breach 5% daily limit at this sizing.")
        print(f"      (${worst_trade:.0f} < ${daily_limit:.0f})")
    else:
        print(f"    ✗ Can breach 5% daily limit in a worst-case scenario.")
        print(f"      (${worst_trade:.0f} > ${daily_limit:.0f})")

    # Actual bad days in backtest
    bad_days = daily[daily < -daily_limit]
    print(f"\n  Bad days (daily loss > ${daily_limit:.0f}) in full backtest: {len(bad_days)}")
    if len(bad_days) > 0:
        tl = trade_log.copy()
        tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
        feats_map = feats.copy()
        feats_map["date"] = pd.to_datetime(feats_map["date"]).dt.normalize()
        feats_map = feats_map.set_index("date")

        for d, v in bad_days.items():
            d_naive = d.tz_localize(None) if hasattr(d, "tz_localize") and d.tzinfo is not None else d
            feat = feats_map.loc[d] if d in feats_map.index else None
            rng_str = f"{feat['rng']:.1f}pts" if feat is not None else "N/A"
            gap_str = f"{feat['gap_pct']*100:+.2f}%" if feat is not None and pd.notna(feat.get("gap_pct")) else "N/A"
            print(f"    {str(d.date())}: P&L=${v:+.0f} ({v/account*100:.2f}%)  "
                  f"range={rng_str}  gap={gap_str}")
    else:
        print("    None — daily loss limit structurally safe at this sizing.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 90)
    print("TASK 1 — PROPFIRM COMPATIBILITY ANALYSIS (iter_10, fixed DD rules)")
    print("=" * 90)
    print(f"  Rules: max_dd={DD_TOTAL_PCT*100:.0f}% total (fixed)  "
          f"| max_dd_daily={DD_DAILY_PCT*100:.0f}%  "
          f"| target={TARGET_PCT*100:.0f}%")
    print(f"  /MNQ: $2/pt, ${MNQ_COST_RT}/RT  |  10 /MNQ = 1 NQ")
    print(f"  Bootstrap: {MC_PATHS:,} paths × {MC_DAYS} trading days")

    # Load data + run iter_10
    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    feats_filtered = feats[feats["rng"] >= RNG_MIN].copy()
    sigs   = signals_from_features(feats_filtered, gap_thresh=STRATEGY_GAP,
                                    dollar_stop=STRATEGY_STOP)
    trade_log, met = engine.run(sigs)

    print(f"\n  iter_10 trade log: {len(trade_log)} trades  "
          f"[{pd.to_datetime(trade_log['entry_ts'].min()).date()} → "
          f"{pd.to_datetime(trade_log['entry_ts'].max()).date()}]")

    # ── STEPS 2+3: per (account, sizing) ──────────────────────────────────
    results = {}
    for mnq in MNQ_SIZES:
        daily = build_daily_pnl(trade_log, mnq)
        for acct in ACCOUNT_SIZES:
            key = (acct, mnq)
            dd  = fixed_dd_metrics(daily, acct)
            mc  = bootstrap_sim(daily, acct)
            results[key] = {"daily": daily, "dd": dd, "mc": mc, "mnq": mnq, "acct": acct}

    # ── STEP 4: Comparison table ───────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  STEP 4 — COMPARISON TABLE")
    print("=" * 90)

    hdr = (f"  {'Account':>8} {'Sizing':>8} {'E[monthly]':>12} {'MaxDD%':>8} "
           f"{'P(bust)':>8} {'P(day>5%)':>10} {'P(target)':>10} {'MedDays':>9} "
           f"{'Hist_OK':>8}")
    print(hdr)
    print(f"  {'-'*87}")

    for acct in ACCOUNT_SIZES:
        for mnq in MNQ_SIZES:
            r   = results[(acct, mnq)]
            dd  = r["dd"]
            mc  = r["mc"]
            ok  = "✓" if not dd["busted_hist"] else "✗"
            print(f"  ${acct:>7,} {mnq:>5}/MNQ "
                  f"${mc['mean_monthly']:>10,.0f} "
                  f"{dd['max_dd_pct']:>7.1f}% "
                  f"{mc['p_bust']:>7.1f}% "
                  f"{mc['p_daily_vio']:>9.1f}% "
                  f"{mc['p_target']:>9.1f}% "
                  f"{mc['med_days']:>8.0f} "
                  f"{ok:>7}")

    # ── STEP 5: Recommendation ────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  STEP 5 — RECOMMENDATION")
    print("=" * 90)
    print(f"\n  Criteria: P(bust)<10%  AND  P(daily>5%)<15%  AND  P(target,60d)>40%")
    print(f"            AND  max_dd_hist < 8% of account (2% buffer)")

    candidates = []
    for acct in ACCOUNT_SIZES:
        for mnq in MNQ_SIZES:
            r  = results[(acct, mnq)]
            dd = r["dd"]
            mc = r["mc"]
            c1 = mc["p_bust"]     < 10.0
            c2 = mc["p_daily_vio"] < 15.0
            c3 = mc["p_target"]   > 40.0
            c4 = dd["max_dd_pct"] < 8.0
            all_pass = c1 and c2 and c3 and c4
            candidates.append({
                "acct": acct, "mnq": mnq,
                "c1": c1, "c2": c2, "c3": c3, "c4": c4,
                "all_pass": all_pass,
                "p_target": mc["p_target"],
                "p_bust": mc["p_bust"],
                "p_daily_vio": mc["p_daily_vio"],
                "max_dd_pct": dd["max_dd_pct"],
                "mean_monthly": mc["mean_monthly"],
                "med_days": mc["med_days"],
            })

    print(f"\n  {'Account':>8} {'Sizing':>8} {'C1(bust)':>10} {'C2(daily)':>10} "
          f"{'C3(target)':>11} {'C4(dd<8%)':>10} {'PASS':>6}")
    print(f"  {'-'*65}")
    for c in candidates:
        mark = "ALL ✓" if c["all_pass"] else f"{'✓' if c['c1'] else '✗'+'✗'+'✗'+'✗'}"
        print(f"  ${c['acct']:>7,} {c['mnq']:>5}/MNQ "
              f"{'✓' if c['c1'] else '✗':>10} "
              f"{'✓' if c['c2'] else '✗':>10} "
              f"{'✓' if c['c3'] else '✗':>11} "
              f"{'✓' if c['c4'] else '✗':>10} "
              f"{'ALL ✓' if c['all_pass'] else '---':>6}")

    # Best passing config
    passing = [c for c in candidates if c["all_pass"]]
    if passing:
        best = max(passing, key=lambda x: x["p_target"])
    else:
        # Find closest: rank by number of criteria passed
        def score(c):
            return sum([c["c1"], c["c2"], c["c3"], c["c4"]])
        best_score = max(score(c) for c in candidates)
        best_subset = [c for c in candidates if score(c) == best_score]
        best = max(best_subset, key=lambda x: x["p_target"])
        print(f"\n  No configuration satisfies all 4 criteria.")
        print(f"  Closest: ${best['acct']:,} / {best['mnq']} /MNQ "
              f"(passed {best_score}/4 criteria)")
        print(f"  Binding constraint(s):")
        if not best["c1"]: print(f"    C1 FAIL: P(bust)={best['p_bust']:.1f}% ≥ 10%")
        if not best["c2"]: print(f"    C2 FAIL: P(daily>5%)={best['p_daily_vio']:.1f}% ≥ 15%")
        if not best["c3"]: print(f"    C3 FAIL: P(target)={best['p_target']:.1f}% ≤ 40%")
        if not best["c4"]: print(f"    C4 FAIL: max_dd={best['max_dd_pct']:.1f}% ≥ 8%")

    print(f"\n" + "─" * 90)
    if passing:
        print(f"  RECOMMENDED: ${best['acct']:,} account, {best['mnq']} /MNQ contracts")
    else:
        print(f"  BEST AVAILABLE: ${best['acct']:,} account, {best['mnq']} /MNQ contracts")
    print(f"  Expected monthly P&L: ${best['mean_monthly']:,.0f}")
    print(f"  P(bust): {best['p_bust']:.1f}%")
    print(f"  P(phase 1 pass in 60 days): {best['p_target']:.1f}%")
    print(f"  Median days to 10% target: {best['med_days']:.0f}")
    print(f"  Max DD in backtest: {best['max_dd_pct']:.1f}% of account")
    print("─" * 90)

    # ── STEP 6: Daily loss deep-dive for recommended config ───────────────
    print("\n" + "=" * 90)
    print(f"  STEP 6 — DAILY LOSS DEEP-DIVE: ${best['acct']:,} / {best['mnq']} /MNQ")
    print("=" * 90)

    best_daily = build_daily_pnl(trade_log, best["mnq"])
    daily_loss_deepdive(trade_log, best_daily, best["acct"], best["mnq"], feats_filtered)

    # Additional: P&L distribution summary
    print(f"\n  Daily P&L distribution ({best['mnq']} /MNQ, {len(best_daily)} trading days):")
    pnl_nz = best_daily[best_daily != 0]
    print(f"    All days  (N={len(best_daily)}): "
          f"mean=${best_daily.mean():.1f}  std=${best_daily.std():.1f}  "
          f"min=${best_daily.min():.1f}  max=${best_daily.max():.1f}")
    print(f"    Trade days(N={len(pnl_nz)}): "
          f"mean=${pnl_nz.mean():.1f}  std=${pnl_nz.std():.1f}  "
          f"min=${pnl_nz.min():.1f}  max=${pnl_nz.max():.1f}")

    # Monthly P&L table
    print(f"\n  Monthly P&L at {best['mnq']} /MNQ:")
    best_daily_copy = best_daily.copy()
    best_daily_copy.index = pd.to_datetime(best_daily_copy.index)
    monthly = best_daily_copy.resample("M").sum()
    for mo, pnl in monthly.items():
        print(f"    {mo.strftime('%Y-%m')}: ${pnl:+,.0f}")

    total_pnl = best_daily.sum()
    n_months  = len(monthly)
    print(f"    Total: ${total_pnl:+,.0f} over {n_months} months  "
          f"(avg ${total_pnl/n_months:+,.0f}/mo)")

    print("\n" + "=" * 90)
    print(f"  SUMMARY")
    print("=" * 90)
    if passing:
        print(f"  ✓ RECOMMENDED: ${best['acct']:,} / {best['mnq']} /MNQ")
        print(f"    All 4 propfirm criteria satisfied.")
    else:
        print(f"  ⚠  BEST AVAILABLE: ${best['acct']:,} / {best['mnq']} /MNQ")
        print(f"    Not all criteria satisfied — see binding constraints above.")
    print(f"  → Update N_CONTRACTS={best['mnq']} in config.py")
    print("=" * 90)

    return best


if __name__ == "__main__":
    main()
