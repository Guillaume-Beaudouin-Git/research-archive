"""
orb_baseline_v2.py — Baseline 30-min ORB NQ v2 + p(pass) FTMO + regime decomp.

Confirm the brief's "~80% p_funded in 2024-26, ~42% blended 16y" claim,
then provide baseline reference numbers for the 3 leviers.

Methodology:
  - Reuse orb_baseline.build_orb_trades for trade generation (cost in bps, same-bar exec).
  - Reuse nq_sim.simulate_2step_uncapped for FTMO p_funded.
  - Sliding-window simulation: for each calendar start, run P1 then P2,
    aggregate p_funded over resolved attempts (CENSORED excluded).
  - Regime buckets: 2010-12, 2013-15, 2016-18, 2019-21, 2022-23, 2024-26.
  - block_cap_pct = risk per trade = 0.5% (v2 standard).

Also runs cost stress: 1bp / 2bp / 3bp / 5bp.

Output: orb_baseline_v2_output.txt + per-block CSVs.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES
from nq_sim import simulate_2step_uncapped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# 6 regime buckets — split 2022-23 vs 2024-26 to highlight the "favourable regime"
REGIMES = [
    ("2010-2012", "2010-06-01", "2013-01-01"),
    ("2013-2015", "2013-01-01", "2016-01-01"),
    ("2016-2018", "2016-01-01", "2019-01-01"),
    ("2019-2021", "2019-01-01", "2022-01-01"),
    ("2022-2023", "2022-01-01", "2024-01-01"),
    ("2024-2026", "2024-01-01", "2027-01-01"),
]


def trade_metrics(tl: pd.DataFrame) -> dict:
    if tl.empty:
        return {"n": 0}
    r = tl["r_realised"].dropna().values
    n = len(r)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "mean_R": round(float(np.mean(r)), 4),
        "std_R": round(float(np.std(r, ddof=1)), 4),
        "hit_pct": round(float((r > 0).mean()) * 100, 2),
        "skew": round(float(stats.skew(r)), 3),
        "kurt": round(float(stats.kurtosis(r)), 3),
        "median_R": round(float(np.median(r)), 4),
        "best_R": round(float(np.max(r)), 3),
        "worst_R": round(float(np.min(r)), 3),
        "win_loss_ratio": round(float(np.mean(r[r > 0]) / abs(np.mean(r[r <= 0]))), 3)
            if (r > 0).any() and (r <= 0).any() else float("nan"),
        "sharpe_per_trade_ann": round(float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(252)), 3)
            if np.std(r, ddof=1) > 0 else float("nan"),
        "long_n": int((tl["direction"] == 1).sum()),
        "long_mean_R": round(float(tl[tl["direction"] == 1]["r_realised"].mean()), 4)
            if (tl["direction"] == 1).any() else float("nan"),
        "short_n": int((tl["direction"] == -1).sum()),
        "short_mean_R": round(float(tl[tl["direction"] == -1]["r_realised"].mean()), 4)
            if (tl["direction"] == -1).any() else float("nan"),
    }


def p_funded(tl: pd.DataFrame, block_cap_pct: float = 0.005) -> dict:
    """Run sliding-window FTMO 2-step on the trade log."""
    if tl.empty:
        return {"p_funded_pct": 0.0, "n_resolved": 0}
    daily_R = build_daily_R_series(tl)
    if daily_R.dropna().empty:
        return {"p_funded_pct": 0.0, "n_resolved": 0}
    out = simulate_2step_uncapped(daily_R, block_cap_pct=block_cap_pct)
    return out


def regime_metrics_and_pfunded(tl: pd.DataFrame, regimes=REGIMES) -> pd.DataFrame:
    rows = []
    for name, lo, hi in regimes:
        sub = tl.loc[lo:hi].copy() if not tl.empty else tl
        m = trade_metrics(sub)
        pf = p_funded(sub)
        m["block"] = name
        m["p_funded_pct"] = round(pf.get("p_funded_pct", 0.0), 2) if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan")
        m["p_phase1_pct"] = round(pf.get("p_phase1", 0.0) * 100, 2) if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan")
        m["n_resolved"] = pf.get("n_resolved", 0)
        m["censored_pct"] = round(pf.get("censored_pct", 0.0), 1)
        rows.append(m)
    return pd.DataFrame(rows)


def annual_metrics(tl: pd.DataFrame) -> pd.DataFrame:
    if tl.empty:
        return pd.DataFrame()
    rows = []
    years = sorted(set(tl.index.year))
    for y in years:
        sub = tl[tl.index.year == y]
        m = trade_metrics(sub)
        m["year"] = y
        m["total_R"] = round(float(sub["r_realised"].sum()), 2)
        rows.append(m)
    return pd.DataFrame(rows)


def stress_costs(sleeve, costs_bps: list[float], exit_spec: dict | None = None) -> pd.DataFrame:
    rows = []
    for c in costs_bps:
        tl = build_orb_trades(sleeve, filter_spec={}, exit_spec=exit_spec, cost_bps_rt=c)
        m = trade_metrics(tl)
        pf = p_funded(tl)
        m["cost_bps"] = c
        m["p_funded_pct"] = round(pf.get("p_funded_pct", 0.0), 2) if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan")
        m["p_phase1_pct"] = round(pf.get("p_phase1", 0.0) * 100, 2) if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan")
        m["n_resolved"] = pf.get("n_resolved", 0)
        rows.append(m)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 100)
    print("BASELINE NQ 30-min ORB — exit-at-close, exec same-bar, cost in bps")
    print("=" * 100)
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec={}, exit_spec={"kind": "at_close"},
                           cost_bps_rt=1.0)
    m = trade_metrics(tl)
    print(f"\nFull sample (2010-2026), cost = 1 bp RT:")
    for k, v in m.items():
        print(f"  {k:25s}: {v}")

    pf = p_funded(tl)
    print(f"\nFTMO 2-step uncapped (block_cap_pct=0.005, P1=+10%/-5%/-10%, P2=+5%/-5%/-10%):")
    for k, v in pf.items():
        print(f"  {k:25s}: {v}")
    print()

    print("=" * 100)
    print("REGIME DECOMPOSITION (6 buckets)")
    print("=" * 100)
    reg_df = regime_metrics_and_pfunded(tl)
    print(reg_df[["block", "n", "long_n", "short_n", "mean_R", "long_mean_R",
                   "short_mean_R", "hit_pct", "skew",
                   "n_resolved", "p_phase1_pct", "p_funded_pct",
                   "censored_pct"]].to_string(index=False))
    reg_df.to_csv(ROOT / "orb_baseline_v2_regime.csv", index=False)
    print()

    print("=" * 100)
    print("ANNUAL BREAKDOWN")
    print("=" * 100)
    ann_df = annual_metrics(tl)
    print(ann_df[["year", "n", "long_n", "short_n", "mean_R", "long_mean_R",
                   "short_mean_R", "hit_pct", "total_R"]].to_string(index=False))
    ann_df.to_csv(ROOT / "orb_baseline_v2_annual.csv", index=False)
    print()

    print("=" * 100)
    print("COST STRESS (bps RT)")
    print("=" * 100)
    stress = stress_costs(sleeve, [0.5, 1.0, 2.0, 3.0, 5.0])
    print(stress[["cost_bps", "n", "mean_R", "hit_pct", "long_mean_R",
                   "short_mean_R", "p_phase1_pct", "p_funded_pct"]].to_string(index=False))
    stress.to_csv(ROOT / "orb_baseline_v2_stress.csv", index=False)

    # Save the trade log
    tl.to_parquet(ROOT / "orb_baseline_nq_trades.parquet")
    print(f"\nSaved trades → orb_baseline_nq_trades.parquet")
