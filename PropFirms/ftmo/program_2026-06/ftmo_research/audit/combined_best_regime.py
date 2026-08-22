"""
combined_best_regime.py — Combine best Levier 1 (V2 bps_10) + Levier 2 (E3 tp_2R)
and compute regime-conditional p(pass).

Steps:
  1. Build the "best combined" config: bps_10 filter + tp_2R exit on NQ.
  2. Full sample 2010-2026 + regime decomp.
  3. Vol-regime conditional p(pass): tag each day by 20d realized vol tercile,
     compute p(pass) for challenges started in each bucket.
  4. Identify the current regime (last available date) → "honest p(pass) today".
  5. Compare combos:
     - baseline (V0 + E0 + NQ alone)
     - V2 (best filter)
     - E3 (best exit)
     - V2 + E3 (combined best)
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
from orb_baseline_v2 import trade_metrics, p_funded, REGIMES
from nq_sim import simulate_2step_uncapped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


COMBOS = {
    "baseline":  {"filter": {}, "exit": {"kind": "at_close"}},
    "V2_bps10":  {"filter": {"kind": "pct", "min_pct": 0.001}, "exit": {"kind": "at_close"}},
    "E3_tp2R":   {"filter": {}, "exit": {"kind": "tp_R", "tp_R": 2.0}},
    "V2+E3":     {"filter": {"kind": "pct", "min_pct": 0.001},
                  "exit": {"kind": "tp_R", "tp_R": 2.0}},
    "V2+E7":     {"filter": {"kind": "pct", "min_pct": 0.001},
                  "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}},
}


def run_combo(name: str, cfg: dict, cost_bps: float = 2.0) -> tuple[dict, pd.DataFrame]:
    log.info(f"  Combo: {name}")
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec=cfg["filter"], exit_spec=cfg["exit"],
                           cost_bps_rt=cost_bps)
    m = trade_metrics(tl)
    pf = p_funded(tl)
    return {
        "combo": name,
        "n": m.get("n", 0),
        "mean_R": m.get("mean_R"),
        "hit_pct": m.get("hit_pct"),
        "skew": m.get("skew"),
        "long_mean_R": m.get("long_mean_R"),
        "short_mean_R": m.get("short_mean_R"),
        "sharpe_pt_ann": m.get("sharpe_per_trade_ann"),
        "p_phase1_pct": round(pf.get("p_phase1", 0.0) * 100, 2)
            if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan"),
        "p_funded_pct": round(pf.get("p_funded_pct", 0.0), 2)
            if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan"),
        "n_resolved": pf.get("n_resolved", 0),
        "censored_pct": round(pf.get("censored_pct", 0.0), 1),
    }, tl


def vol_regime_tag(daily_close: pd.Series, window: int = 20) -> pd.Series:
    """Tercile vol regime by expanding-window calibration."""
    rets = daily_close.pct_change()
    rv = rets.rolling(window, min_periods=int(window * 0.6)).std() * np.sqrt(252)
    out = pd.Series(index=rv.index, dtype="object")
    for i, ts in enumerate(rv.index):
        v = rv.iloc[i]
        if pd.isna(v):
            out.iloc[i] = None
            continue
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
    return out, rv


def conditional_p_funded(daily_R: pd.Series, regime_tag: pd.Series,
                          block_cap_pct: float = 0.005) -> pd.DataFrame:
    rows = []
    aligned = pd.concat([daily_R.rename("R"), regime_tag.rename("regime")],
                         axis=1, join="inner")
    R_series = aligned["R"]
    regimes = aligned["regime"].values
    for r_name in ["low", "mid", "high"]:
        starts = np.where(regimes == r_name)[0]
        if len(starts) < 30:
            rows.append({"regime": r_name, "n_starts": len(starts)})
            continue
        out = simulate_2step_uncapped(
            R_series.reset_index(drop=True), block_cap_pct=block_cap_pct,
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
    cost_bps = 2.0
    print("=" * 100)
    print(f"COMBINED BEST CONFIG — NQ 30-min ORB, cost = {cost_bps} bp RT")
    print("=" * 100)

    # Run each combo
    rows = []
    trade_logs = {}
    for name, cfg in COMBOS.items():
        row, tl = run_combo(name, cfg, cost_bps)
        rows.append(row)
        trade_logs[name] = tl
    df = pd.DataFrame(rows)
    print("\nSummary:")
    print(df.to_string(index=False))
    df.to_csv(ROOT / "combined_best_summary.csv", index=False)
    print()

    # Pick best by p_funded
    best_name = df.sort_values("p_funded_pct", ascending=False).iloc[0]["combo"]
    best_tl = trade_logs[best_name]
    log.info(f"  Best combo: {best_name}")

    # === Regime decomposition for best combo ===
    print("=" * 100)
    print(f"REGIME DECOMPOSITION — {best_name}")
    print("=" * 100)
    from orb_baseline_v2 import regime_metrics_and_pfunded
    reg = regime_metrics_and_pfunded(best_tl)
    print(reg[["block", "n", "long_n", "short_n", "mean_R", "long_mean_R",
                "short_mean_R", "hit_pct", "skew", "n_resolved",
                "p_phase1_pct", "p_funded_pct"]].to_string(index=False))
    reg.to_csv(ROOT / f"combined_best_{best_name}_regime.csv", index=False)
    print()

    # === Vol-regime conditional p(pass) ===
    print("=" * 100)
    print(f"VOL-REGIME CONDITIONAL p(pass) — {best_name}")
    print("=" * 100)
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    regime_tag, rv = vol_regime_tag(daily_close, window=20)
    log.info(f"  rv20 range: {rv.min():.3f} → {rv.max():.3f}")
    log.info(f"  Regime counts: {regime_tag.value_counts().to_dict()}")

    daily_R = build_daily_R_series(best_tl)
    daily_R.name = "R"

    # Align regime_tag to daily_R index
    regime_tag_aligned = regime_tag.reindex(daily_R.index, method="ffill")

    res = conditional_p_funded(daily_R, regime_tag_aligned)
    print(res.to_string(index=False))
    res.to_csv(ROOT / f"combined_best_{best_name}_regime_cond.csv", index=False)

    # Identify current regime
    print()
    print("=" * 100)
    print("REGIME ACTUEL (dernier rv20)")
    print("=" * 100)
    cur_rv = rv.dropna().iloc[-1]
    cur_date = rv.dropna().index[-1]
    past = rv.iloc[-253:-1].dropna()
    q33 = past.quantile(0.33)
    q67 = past.quantile(0.67)
    if cur_rv <= q33:
        cur_bucket = "low"
    elif cur_rv <= q67:
        cur_bucket = "mid"
    else:
        cur_bucket = "high"
    print(f"  Date: {cur_date}")
    print(f"  rv20 ann: {cur_rv:.3f}")
    print(f"  Trailing 252d terciles: q33={q33:.3f}, q67={q67:.3f}")
    print(f"  Current regime: **{cur_bucket}**")
    print()

    cur_p_funded = res[res["regime"] == cur_bucket]
    if len(cur_p_funded) and not pd.isna(cur_p_funded.iloc[0].get("p_funded_pct", float("nan"))):
        print(f"  Honest p(pass) today (regime={cur_bucket}): "
               f"**{cur_p_funded.iloc[0]['p_funded_pct']:.1f}%**")
    else:
        print(f"  Honest p(pass) today: insufficient resolved attempts")
