"""
levier3_multi_index_basket.py — Multi-index ORB basket vs NQ alone.

Hypothesis: NQ baseline burns 77% of PnL in 2023+ (regime concentration).
Running the same ORB logic on multiple indices whose favourable regimes
don't perfectly overlap should smooth the regime concentration and lift
the blended p(pass).

Indices included (data range constraints):
  - NQ        : 2010-2026 (Databento futures)
  - US100     : 2020-2026 (m1_panel CFD, broker EET → ET)
  - US500     : 2020-2026 (m1_panel CFD)
  - US30      : 2020-2026 (m1_panel CFD)
  - US2000    : 2020-2026 (m1_panel CFD)
  - GER40     : 2020-2026 (CET cash session, 09:00-17:30 CET)

Methodology:
  1. Build 30-min ORB at-close for each sleeve (same logic, cost in bps).
  2. Per-sleeve metrics + p(pass) standalone.
  3. Pairwise correlation of daily R series.
  4. Equal-weighted basket daily R (sum across sleeves, scaled).
  5. Basket p(pass) FTMO vs NQ alone.
  6. Restricted to common window 2020-2026 (where all data overlap).

Outputs:
  - levier3_summary.csv (per-sleeve)
  - levier3_corr.csv (pairwise correlation)
  - levier3_basket.csv (basket diagnostic)
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES
from orb_baseline_v2 import trade_metrics, p_funded, REGIMES
from nq_sim import simulate_2step_uncapped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# Common window where all FTMO CFD indices have data
COMMON_LO = "2020-01-01"
COMMON_HI = "2026-05-29"


def run_sleeve(sym: str, cost_bps_rt: float, common_window: bool = True) -> tuple[dict, pd.DataFrame]:
    log.info(f"  Building {sym} ORB 30-min at-close (cost={cost_bps_rt} bp)...")
    sleeve = SLEEVES[sym]
    tl = build_orb_trades(sleeve, filter_spec={}, exit_spec={"kind": "at_close"},
                           cost_bps_rt=cost_bps_rt)
    if common_window:
        tl = tl.loc[COMMON_LO:COMMON_HI]
    if tl.empty:
        return {"symbol": sym, "n": 0}, tl
    m = trade_metrics(tl)
    pf = p_funded(tl)
    return {
        "symbol": sym,
        "cost_bps": cost_bps_rt,
        "n": m.get("n", 0),
        "mean_R": m.get("mean_R"),
        "std_R": m.get("std_R"),
        "hit_pct": m.get("hit_pct"),
        "skew": m.get("skew"),
        "sharpe_pt_ann": m.get("sharpe_per_trade_ann"),
        "long_mean_R": m.get("long_mean_R"),
        "short_mean_R": m.get("short_mean_R"),
        "p_phase1_pct": round(pf.get("p_phase1", 0.0) * 100, 2)
            if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan"),
        "p_funded_pct": round(pf.get("p_funded_pct", 0.0), 2)
            if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan"),
        "n_resolved": pf.get("n_resolved", 0),
    }, tl


def correlation_matrix(daily_R_dict: dict[str, pd.Series]) -> pd.DataFrame:
    df = pd.DataFrame(daily_R_dict)
    return df.corr(min_periods=30).round(3)


def basket_daily_R(daily_R_dict: dict[str, pd.Series], weights: dict | None = None) -> pd.Series:
    """Aggregate daily R across sleeves (equal-weight or custom).

    Daily R per sleeve = trade-day R if traded that day, else 0.
    Basket daily R = weighted sum across active sleeves.
    """
    df = pd.DataFrame(daily_R_dict).fillna(0.0)
    if weights is None:
        weights = {c: 1.0 / len(df.columns) for c in df.columns}
    weight_vec = pd.Series(weights)[df.columns]
    return df.dot(weight_vec.values)


def basket_p_funded(basket_R: pd.Series, block_cap_pct: float = 0.005) -> dict:
    return simulate_2step_uncapped(basket_R, block_cap_pct=block_cap_pct)


if __name__ == "__main__":
    print("=" * 110)
    print("LEVIER 3 — Multi-index basket vs NQ alone (cost = 2 bp RT for CFD; 1 bp for NQ futures)")
    print("Common window 2020-2026 for fair comparison")
    print("=" * 110)

    # Per-sleeve cost: NQ futures 1 bp, CFDs 2 bp default (already in sleeve)
    sleeve_costs = {
        "NQ": 1.0,        # futures retail
        "US100": 2.0,
        "US500": 2.0,
        "US30": 2.0,
        "US2000": 3.0,    # smaller cap, wider spreads
        "GER40": 1.5,
    }

    rows = []
    trade_logs = {}
    daily_R_dict = {}
    for sym, cost in sleeve_costs.items():
        try:
            row, tl = run_sleeve(sym, cost, common_window=True)
            rows.append(row)
            trade_logs[sym] = tl
            if not tl.empty:
                daily_R_dict[sym] = build_daily_R_series(tl).fillna(0.0)
        except Exception as e:
            log.warning(f"  Failed {sym}: {e}")
            rows.append({"symbol": sym, "n": 0, "error": str(e)})

    df = pd.DataFrame(rows)
    cols = ["symbol", "cost_bps", "n", "mean_R", "hit_pct", "skew",
            "long_mean_R", "short_mean_R", "sharpe_pt_ann",
            "p_phase1_pct", "p_funded_pct", "n_resolved"]
    print("\nPer-sleeve standalone results (2020-2026):")
    print(df[cols].to_string(index=False))
    df.to_csv(ROOT / "levier3_summary.csv", index=False)
    print()

    # Pairwise correlation
    print("=" * 110)
    print("CORRELATION — daily R series between sleeves")
    print("=" * 110)
    corr = correlation_matrix(daily_R_dict)
    print(corr.to_string())
    corr.to_csv(ROOT / "levier3_corr.csv")
    print()
    print(f"Mean off-diagonal correlation: {(corr.values[np.triu_indices_from(corr.values, k=1)]).mean():.3f}")
    print()

    # Basket aggregation
    print("=" * 110)
    print("BASKET — equal-weighted, sum of daily R across active sleeves")
    print("=" * 110)
    basket_R = basket_daily_R(daily_R_dict)
    print(f"  Basket length: {len(basket_R)} days")
    print(f"  Basket mean R (per-day): {basket_R.mean():.4f}")
    print(f"  Basket std R: {basket_R.std():.4f}")
    print(f"  Basket Sharpe daily ann: {basket_R.mean() / basket_R.std() * np.sqrt(252):.3f}")
    pf_basket = basket_p_funded(basket_R)
    print(f"\n  Basket p_phase1: {pf_basket['p_phase1']*100:.2f}%")
    print(f"  Basket p_funded: {pf_basket['p_funded_pct']:.2f}%")
    print(f"  Basket n_resolved: {pf_basket['n_resolved']}")
    print(f"  Basket censored: {pf_basket['censored_pct']:.1f}%")
    print()

    # Compare to NQ alone
    print("=" * 110)
    print("COMPARISON — basket vs NQ alone (2020-2026 window)")
    print("=" * 110)
    print(df[df["symbol"] == "NQ"][cols].to_string(index=False))
    print(f"\nBasket: p_phase1={pf_basket['p_phase1']*100:.2f}% p_funded={pf_basket['p_funded_pct']:.2f}%")
    print(f"NQ alone: p_phase1={df[df['symbol']=='NQ'].iloc[0]['p_phase1_pct']:.2f}% p_funded={df[df['symbol']=='NQ'].iloc[0]['p_funded_pct']:.2f}%")
    print()

    # Regime decomp on basket
    print("=" * 110)
    print("BASKET — regime decomposition")
    print("=" * 110)
    basket_R_indexed = basket_R.copy()
    for name, lo, hi in REGIMES:
        sub = basket_R_indexed.loc[lo:hi]
        if sub.empty or sub.dropna().empty:
            print(f"  {name}: n=0 (no data)")
            continue
        sub_nonan = sub.dropna()
        nz = sub_nonan[sub_nonan != 0]
        if len(nz) < 30:
            print(f"  {name}: insufficient data ({len(nz)} non-zero days)")
            continue
        m = nz.mean()
        s = nz.std()
        sh = m / s * np.sqrt(252) if s > 0 else float("nan")
        pf = basket_p_funded(sub_nonan)
        print(f"  {name}: n={len(nz):>4d} mean={m:+.4f} std={s:.4f} "
               f"sharpe={sh:+.2f} p_funded={pf['p_funded_pct']:.1f}% "
               f"n_resolved={pf['n_resolved']} censored={pf['censored_pct']:.1f}%")

    # Save basket series
    basket_R.to_frame("basket_R").to_csv(ROOT / "levier3_basket.csv")
