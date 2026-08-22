"""
lever_b_conditional_oof.py — Lever B: conditional sizing (vol regime, DoW, events).

NOWCAST CONSTRAINT — every conditioning variable uses info STRICTLY ≤ t.

Base config: V2+E7 (Lever A winner).
Sizing scaled per day by factor based on conditioning variable.

Candidates:
  Vol regime (trailing 20d realized vol):
    B01_vol_neutral   : all regimes 0.5%
    B02_vol_pro       : low=0.7, mid=0.5, high=0.7
    B03_vol_counter   : low=0.4, mid=0.7, high=0.5
    B04_vol_high_only : low=0.3, mid=0.3, high=0.7
    B05_vol_avoid_mid : low=0.6, mid=0.0 (skip), high=0.6

  Day-of-week (0=Mon, 4=Fri):
    B10_dow_baseline    : all 0.5
    B11_drop_friday     : Fri=0
    B12_drop_monday     : Mon=0
    B13_boost_wed_thu   : Wed/Thu=0.7
    B14_drop_mon_fri    : Mon/Fri=0

  Event days (FOMC/NFP/CPI from economic_calendar.csv 2020+):
    B20_events_baseline : 0.5
    B21_drop_events     : event days → 0
    B22_half_events     : event days → 0.25
    B23_double_events   : event days → 0.7

  (Note: event calendar covers 2020-2026 only → events pre-2020 = unknown,
   treated as non-event days. Pre-2020 effect is just nominal sizing.)

For each candidate, run OOF held + WF selection.
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
from nq_sim_v3 import simulate_2step_v3
from oof_framework import build_fold_boundaries, WF_FOLD_END_DATES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CAL_PATH = ROOT.parents[1] / "panels" / "economic_calendar.csv"

V2_E7_FILTER = {"kind": "pct", "min_pct": 0.001}
V2_E7_EXIT = {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}
COST_BPS = 2.0


# ---------------------------------------------------------------------------
# Conditioning variable builders (NOWCAST)
# ---------------------------------------------------------------------------

def compute_vol_tag(daily_close: pd.Series, window: int = 20) -> pd.Series:
    """Expanding-window tercile vol regime tag. NOWCAST (info ≤ t)."""
    rets = daily_close.pct_change()
    rv = rets.rolling(window, min_periods=int(window * 0.6)).std() * np.sqrt(252)
    tag = pd.Series(index=rv.index, dtype="object")
    for i in range(len(rv)):
        v = rv.iloc[i]
        if pd.isna(v):
            tag.iloc[i] = None
            continue
        past = rv.iloc[max(0, i - 252): i].dropna()
        if len(past) < 60:
            tag.iloc[i] = None
            continue
        q33 = past.quantile(0.33)
        q67 = past.quantile(0.67)
        if v <= q33:
            tag.iloc[i] = "low"
        elif v <= q67:
            tag.iloc[i] = "mid"
        else:
            tag.iloc[i] = "high"
    return tag


def compute_dow(idx: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(idx.dayofweek, index=idx, dtype=int)


def compute_event_flag(idx: pd.DatetimeIndex) -> pd.Series:
    """Flag = True if day is in economic_calendar.csv (FOMC/NFP/CPI events)."""
    if not CAL_PATH.exists():
        return pd.Series(False, index=idx)
    cal = pd.read_csv(CAL_PATH)
    cal["date"] = pd.to_datetime(cal["date"])
    cal_days = set(cal["date"].dt.normalize())
    flag = pd.Series(
        [pd.Timestamp(d).normalize() in cal_days for d in idx],
        index=idx, dtype=bool,
    )
    return flag


# ---------------------------------------------------------------------------
# Sizing rule application
# ---------------------------------------------------------------------------

def vol_regime_sizing(daily_R: pd.Series, vol_tag: pd.Series,
                       sizes: dict[str, float]) -> pd.Series:
    """Scale daily_R by per-regime factor. Sizes is dict {low/mid/high: factor}."""
    factor = vol_tag.map(sizes).fillna(1.0).reindex(daily_R.index).fillna(1.0)
    return daily_R * factor.values


def dow_sizing(daily_R: pd.Series, dow: pd.Series,
                sizes: dict[int, float]) -> pd.Series:
    """Scale daily_R by per-DoW factor."""
    factor = dow.map(sizes).fillna(1.0).reindex(daily_R.index).fillna(1.0)
    return daily_R * factor.values


def event_sizing(daily_R: pd.Series, event_flag: pd.Series,
                  event_factor: float = 0.0, non_event_factor: float = 1.0) -> pd.Series:
    """Scale event days by event_factor, others by non_event_factor."""
    factor = event_flag.map({True: event_factor, False: non_event_factor})\
        .reindex(daily_R.index).fillna(non_event_factor)
    return daily_R * factor.values


# ---------------------------------------------------------------------------
# Candidate configs
# ---------------------------------------------------------------------------

def _vol_sizing_factory(low: float, mid: float, high: float, base: float = 0.005):
    """Return a (factor_dict_per_regime) where factor scales the BASE block_cap."""
    return {"low": low / base, "mid": mid / base, "high": high / base}


VOL_CONFIGS = {
    "B01_vol_neutral":   _vol_sizing_factory(0.005, 0.005, 0.005),  # = 1.0 everywhere
    "B02_vol_pro":       _vol_sizing_factory(0.007, 0.005, 0.007),
    "B03_vol_counter":   _vol_sizing_factory(0.004, 0.007, 0.005),
    "B04_vol_high_only": _vol_sizing_factory(0.003, 0.003, 0.007),
    "B05_vol_avoid_mid": _vol_sizing_factory(0.006, 0.0,   0.006),
    "B06_vol_low_heavy": _vol_sizing_factory(0.007, 0.005, 0.004),
    "B07_vol_avoid_mid_strong": _vol_sizing_factory(0.007, 0.0, 0.007),
}

DOW_CONFIGS = {
    "B10_dow_baseline":  {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0},
    "B11_drop_friday":   {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.0},
    "B12_drop_monday":   {0: 0.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0},
    "B13_boost_wed_thu": {0: 0.7, 1: 0.7, 2: 1.4, 3: 1.4, 4: 0.7},
    "B14_drop_mon_fri":  {0: 0.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.0},
    "B15_only_tue_wed":  {0: 0.0, 1: 1.5, 2: 1.5, 3: 0.0, 4: 0.0},
}

EVENT_CONFIGS = {
    "B20_events_neutral":  (1.0, 1.0),
    "B21_drop_events":     (0.0, 1.0),
    "B22_half_events":     (0.5, 1.0),
    "B23_boost_events":    (1.4, 1.0),
}


def eval_pfunded_scaled(scaled_R: pd.Series, start_indices: np.ndarray | None = None,
                          block_cap_pct: float = 0.005) -> dict:
    si = start_indices.tolist() if start_indices is not None else None
    return simulate_2step_v3(scaled_R, block_cap_p1=block_cap_pct, block_cap_p2=block_cap_pct,
                              start_indices=si)


if __name__ == "__main__":
    print("=" * 110)
    print("LEVER B — Conditional sizing OOF on V2+E7")
    print("=" * 110)

    # Build V2+E7 daily R series
    log.info("Building V2+E7 daily R series on NQ...")
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec=V2_E7_FILTER, exit_spec=V2_E7_EXIT,
                           cost_bps_rt=COST_BPS)
    daily_R = build_daily_R_series(tl)
    log.info(f"  {len(daily_R)} days")

    # Build conditioning variables
    log.info("Building conditioning variables...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    vol_tag = vol_tag.reindex(daily_R.index)
    log.info(f"  Vol tag counts: {vol_tag.value_counts(dropna=False).to_dict()}")
    dow = compute_dow(daily_R.index)
    event_flag = compute_event_flag(daily_R.index)
    log.info(f"  Event days: {event_flag.sum()} / {len(daily_R)}")

    boundaries = build_fold_boundaries(daily_R, WF_FOLD_END_DATES)
    test_start_first = boundaries[0][1]
    test_end_last = boundaries[-1][2]
    test_starts_all = np.arange(test_start_first, test_end_last)

    # Evaluate each candidate
    rows = []
    daily_R_scaled_per_config: dict[str, pd.Series] = {}

    log.info("Evaluating vol-regime sizings...")
    for name, sizes in VOL_CONFIGS.items():
        scaled = vol_regime_sizing(daily_R, vol_tag, sizes)
        daily_R_scaled_per_config[name] = scaled
        is_res = eval_pfunded_scaled(scaled)
        oof_res = eval_pfunded_scaled(scaled, start_indices=test_starts_all)
        rows.append({
            "config": name,
            "type": "vol",
            "in_sample_p_funded_pct": round(is_res["p_funded_pct"], 2)
                if not pd.isna(is_res["p_funded_pct"]) else float("nan"),
            "oof_p_funded_pct": round(oof_res["p_funded_pct"], 2)
                if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
            "oof_n_resolved": oof_res["n_resolved"],
            "oof_n_funded": oof_res["n_funded"],
        })

    log.info("Evaluating DoW sizings...")
    for name, sizes in DOW_CONFIGS.items():
        scaled = dow_sizing(daily_R, dow, sizes)
        daily_R_scaled_per_config[name] = scaled
        is_res = eval_pfunded_scaled(scaled)
        oof_res = eval_pfunded_scaled(scaled, start_indices=test_starts_all)
        rows.append({
            "config": name,
            "type": "dow",
            "in_sample_p_funded_pct": round(is_res["p_funded_pct"], 2)
                if not pd.isna(is_res["p_funded_pct"]) else float("nan"),
            "oof_p_funded_pct": round(oof_res["p_funded_pct"], 2)
                if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
            "oof_n_resolved": oof_res["n_resolved"],
            "oof_n_funded": oof_res["n_funded"],
        })

    log.info("Evaluating event-day sizings...")
    for name, (ev_f, nev_f) in EVENT_CONFIGS.items():
        scaled = event_sizing(daily_R, event_flag, ev_f, nev_f)
        daily_R_scaled_per_config[name] = scaled
        is_res = eval_pfunded_scaled(scaled)
        oof_res = eval_pfunded_scaled(scaled, start_indices=test_starts_all)
        rows.append({
            "config": name,
            "type": "event",
            "in_sample_p_funded_pct": round(is_res["p_funded_pct"], 2)
                if not pd.isna(is_res["p_funded_pct"]) else float("nan"),
            "oof_p_funded_pct": round(oof_res["p_funded_pct"], 2)
                if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
            "oof_n_resolved": oof_res["n_resolved"],
            "oof_n_funded": oof_res["n_funded"],
        })

    df = pd.DataFrame(rows)
    df["delta_oof_vs_is"] = df["oof_p_funded_pct"] - df["in_sample_p_funded_pct"]
    df_sorted = df.sort_values("oof_p_funded_pct", ascending=False)
    print()
    print("=" * 110)
    print("RANKED BY OOF HELD — all Lever B configs")
    print("=" * 110)
    print(df_sorted.to_string(index=False))
    df.to_csv(ROOT / "lever_b_summary.csv", index=False)

    # WF selection across all Lever B configs
    print()
    print("=" * 110)
    print("WALK-FORWARD SELECTION across all Lever B configs")
    print("=" * 110)
    fold_records = []
    total_resolved = 0
    total_funded = 0
    for fold_idx, (tr_end, ts_start, ts_end, tr_date, te_date) in enumerate(boundaries):
        train_starts = np.arange(0, tr_end)
        train_p = {}
        for name, scaled in daily_R_scaled_per_config.items():
            res = eval_pfunded_scaled(scaled, start_indices=train_starts)
            train_p[name] = {
                "p_funded": res["p_funded"] if not pd.isna(res["p_funded"]) else -1,
                "p_phase1": res["p_phase1"] if not pd.isna(res["p_phase1"]) else -1,
                "n_resolved": res["n_resolved"],
            }
        ranked = sorted(
            train_p.items(),
            key=lambda kv: (
                kv[1]["p_funded"] if kv[1]["n_resolved"] >= 100 else -100,
                kv[1]["p_phase1"],
            ),
            reverse=True,
        )
        best_name = ranked[0][0]
        test_starts = np.arange(ts_start, ts_end)
        res_test = eval_pfunded_scaled(daily_R_scaled_per_config[best_name],
                                        start_indices=test_starts)
        fold_records.append({
            "fold_idx": fold_idx,
            "train_end": tr_date,
            "test_end": te_date,
            "best_config": best_name,
            "train_p_funded_pct": round(train_p[best_name]["p_funded"] * 100, 2)
                if train_p[best_name]["p_funded"] > -1 else float("nan"),
            "train_n_resolved": train_p[best_name]["n_resolved"],
            "test_p_funded_pct": round(res_test["p_funded_pct"], 2)
                if not pd.isna(res_test["p_funded_pct"]) else float("nan"),
            "test_n_resolved": res_test["n_resolved"],
            "test_n_funded": res_test["n_funded"],
            "test_censored_pct": round(res_test["censored_pct"], 1),
        })
        total_resolved += res_test["n_resolved"]
        total_funded += res_test["n_funded"]
    fold_df = pd.DataFrame(fold_records)
    print(fold_df.to_string(index=False))
    fold_df.to_csv(ROOT / "lever_b_wf_selected.csv", index=False)
    wf_oof = (total_funded / total_resolved * 100) if total_resolved > 0 else float("nan")
    print()
    print(f"  WF-selection OOF p_funded: {wf_oof:.2f}% ({total_funded}/{total_resolved})")

    # Summary
    print()
    print("=" * 110)
    print("LEVER B SUMMARY")
    print("=" * 110)
    baseline_row = df[df["config"] == "B01_vol_neutral"].iloc[0]
    best_held = df_sorted.iloc[0]
    print(f"  Baseline (B01 neutral)         : in-sample={baseline_row['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={baseline_row['oof_p_funded_pct']:5.2f}%")
    print(f"  Best held config ({best_held['config']}): in-sample={best_held['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={best_held['oof_p_funded_pct']:5.2f}% "
           f"(Δ vs baseline: +{best_held['oof_p_funded_pct'] - baseline_row['oof_p_funded_pct']:.2f}pp)")
    print(f"  WF-selected OOF: {wf_oof:.2f}% "
           f"(Δ vs baseline: +{wf_oof - baseline_row['oof_p_funded_pct']:.2f}pp)")
