"""
regime_conditional_pfunded.py — Modélise p(pass) conditionnel au régime de vol.

Hypothesis: a "vol regime" indicator at challenge start can predict p(pass).
The Cowork module reportedly achieves AUC 0.60 for regime classification —
we test the analog: tag each day with a vol indicator, simulate p(pass) for
challenges started in each regime bucket, and compare to today's actual regime.

Indicator: realized 20-day vol of NQ returns (proxy for the "vol regime").
Buckets: q1 (low vol) / q2-q3 (mid vol) / q4 (high vol).

For the WINNING strategy candidate (TBD by leviers 1+2+3), compute:
  - p(pass) when starting in each regime bucket
  - p(pass) "today" given the current regime (using last available data)

This gives an honest p(pass) RIGHT NOW — not blended over 16 years.

Inputs: trade log + daily R series (whichever leviers winning candidate).
Default candidate for now: baseline NQ (orb_baseline_nq_trades.parquet).
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES, load_instrument
from orb_baseline_v2 import trade_metrics
from nq_sim import simulate_2step_uncapped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def compute_vol_regime(daily_close: pd.Series, window: int = 20) -> pd.Series:
    """Realized vol of close-to-close returns over `window` days (annualized)."""
    rets = daily_close.pct_change()
    rv = rets.rolling(window, min_periods=int(window * 0.6)).std() * np.sqrt(252)
    return rv


def regime_bucket(rv: pd.Series) -> pd.Series:
    """Tertile (low/mid/high) regime bucket per date.

    Uses expanding-window terciles to avoid look-ahead.
    """
    out = pd.Series(index=rv.index, dtype="object")
    for i, ts in enumerate(rv.index):
        v = rv.iloc[i]
        if pd.isna(v):
            out.iloc[i] = None
            continue
        # use prior 252 days of rv values to compute terciles
        past = rv.iloc[max(0, i - 252): i].dropna()
        if len(past) < 60:
            out.iloc[i] = None
            continue
        q33 = past.quantile(0.33)
        q67 = past.quantile(0.67)
        if v <= q33:
            out.iloc[i] = "low"
        elif v <= q67:
            out.iloc[i] = "mid"
        else:
            out.iloc[i] = "high"
    return out


def conditional_p_funded(daily_R: pd.Series, regime_tag: pd.Series,
                          block_cap_pct: float = 0.005) -> pd.DataFrame:
    """Per-regime p(pass): use only START dates within each regime."""
    rows = []
    aligned = pd.concat([daily_R, regime_tag.rename("regime")], axis=1, join="inner")
    R_arr = aligned[daily_R.name if daily_R.name else 0].values \
        if daily_R.name in aligned.columns else aligned.iloc[:, 0].values
    R_arr = aligned.iloc[:, 0].values  # safer
    regimes = aligned["regime"].values

    # Use nq_sim with explicit start_indices per regime
    for r_name in ["low", "mid", "high"]:
        starts = np.where(regimes == r_name)[0]
        if len(starts) < 30:
            rows.append({"regime": r_name, "n_starts": len(starts)})
            continue
        out = simulate_2step_uncapped(
            pd.Series(R_arr, index=aligned.index),
            block_cap_pct=block_cap_pct,
            start_indices=starts.tolist(),
        )
        rows.append({
            "regime": r_name,
            "n_starts": int(len(starts)),
            "p_phase1_pct": round(out["p_phase1"] * 100, 2)
                if not pd.isna(out["p_phase1"]) else float("nan"),
            "p_funded_pct": round(out["p_funded_pct"], 2)
                if not pd.isna(out["p_funded_pct"]) else float("nan"),
            "n_resolved": out["n_resolved"],
            "censored_pct": round(out["censored_pct"], 1),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 110)
    print("REGIME-CONDITIONAL p(pass) — baseline NQ (will re-run on best candidate after L1/L2/L3)")
    print("=" * 110)

    # Use the saved baseline trade log
    tl_path = ROOT / "orb_baseline_nq_trades.parquet"
    if not tl_path.exists():
        log.info("Building baseline NQ trades (no filter, exit-at-close, cost 2 bp)...")
        sleeve = SLEEVES["NQ"]
        tl = build_orb_trades(sleeve, filter_spec={}, exit_spec={"kind": "at_close"},
                               cost_bps_rt=2.0)
        tl.to_parquet(tl_path)
    else:
        tl = pd.read_parquet(tl_path)
    log.info(f"  {len(tl)} trades, {tl.index.min()} -> {tl.index.max()}")

    # daily close of NQ (for vol regime)
    log.info("Loading NQ for vol regime...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    rv20 = compute_vol_regime(daily_close, window=20)
    log.info(f"  rv20 range: {rv20.min():.3f} → {rv20.max():.3f}")

    regime_tag = regime_bucket(rv20)
    log.info(f"  Regime tag counts: {regime_tag.value_counts().to_dict()}")

    # Build daily R series
    daily_R = build_daily_R_series(tl)
    daily_R.name = "R"

    print()
    print("=" * 110)
    print("p(pass) FTMO conditioned on VOL REGIME at challenge start")
    print("=" * 110)
    res = conditional_p_funded(daily_R, regime_tag)
    print(res.to_string(index=False))
    res.to_csv(ROOT / "regime_conditional_pfunded.csv", index=False)
    print()

    # Current regime
    print("=" * 110)
    print("REGIME ACTUEL (dernier rv20 disponible)")
    print("=" * 110)
    current_rv = rv20.dropna().iloc[-1]
    current_date = rv20.dropna().index[-1]
    # Compute current bucket using expanding terciles
    past = rv20.iloc[-253:-1].dropna()
    q33 = past.quantile(0.33)
    q67 = past.quantile(0.67)
    if current_rv <= q33:
        cur_bucket = "low"
    elif current_rv <= q67:
        cur_bucket = "mid"
    else:
        cur_bucket = "high"
    print(f"  Last close-to-close rv20 ann: {current_rv:.3f} ({current_date})")
    print(f"  Trailing 252d terciles: q33={q33:.3f}, q67={q67:.3f}")
    print(f"  Current regime: **{cur_bucket}**")
    print()

    # Honest p(pass) right now = p(pass) in the current regime
    cur_row = res[res["regime"] == cur_bucket]
    if len(cur_row) and not pd.isna(cur_row.iloc[0].get("p_funded_pct", float("nan"))):
        print(f"  Honest p(pass) today (regime={cur_bucket}): "
               f"{cur_row.iloc[0]['p_funded_pct']:.1f}%")
    else:
        print(f"  Honest p(pass) today: insufficient data for current regime")
