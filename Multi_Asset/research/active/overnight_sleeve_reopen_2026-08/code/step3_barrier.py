"""Step 3 — first-passage against the REAL FTMO barriers, unlimited horizon.

Reuses the canonical engine (`PropFirms/ftmo/program_2026-06/ftmo_alpha_program/engine/
ftmo_first_passage.py`): its Politis-Romano stationary block sampler and its FTMO
constants. One thing the canonical `simulate_empirical_phase` cannot express is that
FTMO enforces the daily loss on EQUITY, i.e. on the intra-session excursion, not on the
close. We therefore carry a second, path-aligned array (`mae`) through the SAME
bootstrap index matrix, so the excursion and the close of a resampled session always
come from the same real session.

Three changes vs the June 2026 kill, and nothing else:
  * horizon UNLIMITED (FTMO has no max trading period — rules.md:28)
  * sleeve STANDALONE (the basket destroyed Sharpe: 1.096 vs 1.279 gold alone)
  * SIZE swept downward (sizing is not a strategy modification)
crossed with the two cost hypotheses (catalogue 3.50 bps vs measured 1.84 bps),
and run on the full sample AND on the post-2021 regime alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common_reopen import (COST_MEAS_BPS, COST_OLD_BPS, FTMO_DAILY, FTMO_MAX_DD,
                           FTMO_P1_TGT, FTMO_P2_TGT, MAIN, OUT, obs_per_year, sharpe,
                           vol_target)

sys.path.insert(0, str(MAIN / "PropFirms" / "ftmo" / "program_2026-06"
                       / "ftmo_alpha_program" / "engine"))
from ftmo_first_passage import _stationary_block_matrix  # noqa: E402

N_PATHS = 20_000
SEED = 42
BREAK = pd.Timestamp("2021-01-01")

path = pd.read_csv(OUT / "step2_gold_window_path.csv", index_col=0, parse_dates=True)


def sized(df: pd.DataFrame, mode: str, vm: float, cost_bps: float, cap: float = 3.0):
    """Account-level (return, excursion) per session for a given sizing policy.

    `vm` is notional/equity. `mode='vt'` applies the inherited causal vol-target
    multiplier (signal at T-1); `mode='fixed'` holds a constant notional.
    Cost is charged round-trip on the notional actually held, and is included in the
    excursion because the spread is paid on entry.
    """
    pos = vol_target(df["ret"], cap=cap) * vm if mode == "vt" else pd.Series(vm, index=df.index)
    ok = pos > 0
    c = pos * cost_bps * 1e-4
    return (pos * df["ret"] - c)[ok], (pos * df["mae"] - c)[ok]


def phase(ret: np.ndarray, mae: np.ndarray, target: float, seed: int,
          horizon: int, max_dd: float = FTMO_MAX_DD, daily: float = FTMO_DAILY):
    """One FTMO phase, unlimited horizon, equity-enforced daily floor.

    Absorbing events, evaluated in real-world order inside a session:
      1. intra-session: excursion breaches the daily floor, or drives cumulative
         equity through the static -10% floor  -> BREACH
      2. at the close: equity >= target -> PASS ; equity <= -10% -> BREACH
    """
    T = len(ret)
    rng = np.random.default_rng(seed)
    block = max(1.0, round(np.sqrt(T)))
    n_pass = n_daily = n_floor = n_timeout = 0
    days = []
    BATCH = 5_000
    for s0 in range(0, N_PATHS, BATCH):
        b = min(BATCH, N_PATHS - s0)
        idx = _stationary_block_matrix(T, b, horizon, block, rng)
        R, M = ret[idx], mae[idx]
        eq = np.cumsum(R, axis=1)
        eq_prev = eq - R                                   # equity at session open
        t_daily = np.where((M <= -daily).any(1), (M <= -daily).argmax(1), horizon + 10)
        intra_floor = (eq_prev + M) <= -max_dd
        t_ifl = np.where(intra_floor.any(1), intra_floor.argmax(1), horizon + 10)
        t_eodfl = np.where((eq <= -max_dd).any(1), (eq <= -max_dd).argmax(1), horizon + 10)
        t_pass = np.where((eq >= target).any(1), (eq >= target).argmax(1), horizon + 10)
        t_bad = np.minimum(np.minimum(t_daily, t_ifl), t_eodfl)
        won = (t_pass < t_bad) & (t_pass <= horizon)
        lost = (t_bad <= t_pass) & (t_bad <= horizon)
        n_pass += int(won.sum())
        n_daily += int(((t_daily <= t_ifl) & (t_daily <= t_eodfl) & lost).sum())
        n_floor += int((lost & ~((t_daily <= t_ifl) & (t_daily <= t_eodfl))).sum())
        n_timeout += int((~won & ~lost).sum())
        days.append(t_pass[won] + 1)
    d = np.concatenate(days) if days else np.array([])
    return dict(p_pass=n_pass / N_PATHS, p_daily=n_daily / N_PATHS,
                p_floor=n_floor / N_PATHS, p_timeout=n_timeout / N_PATHS,
                med_days=float(np.median(d)) if d.size else np.nan,
                p90_days=float(np.percentile(d, 90)) if d.size else np.nan)


def main():
  rows = []
  for sample, sub in (("full", path), ("post-2021", path[path.index >= BREAK])):
    for mode, cap in (("vt", 3.0), ("vt", 2.0), ("vt", 1.5), ("fixed", np.nan)):
        for cost_lab, cost in (("meas_1.84", COST_MEAS_BPS), ("old_3.50", COST_OLD_BPS)):
            for vm in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 14.0):
                r, m = sized(sub, mode, vm, cost, cap if mode == "vt" else 3.0)
                ra, ma = r.to_numpy(), m.to_numpy()
                horizon = len(ra)                       # unlimited: full resample length
                p1 = phase(ra, ma, FTMO_P1_TGT, SEED, horizon)
                p2 = phase(ra, ma, FTMO_P2_TGT, SEED + 1, horizon)
                pc = p1["p_pass"] * p2["p_pass"]
                se = np.sqrt(pc * (1 - pc) / N_PATHS)
                rows.append(dict(
                    sample=sample, sizing=f"{mode}{'' if mode=='fixed' else f'_cap{cap:g}'}",
                    cost=cost_lab, vm=vm,
                    SR_net=round(sharpe(r), 3),
                    vol_ann_pct=round(100 * ra.std(ddof=1) * np.sqrt(obs_per_year(r)), 1),
                    worst_sess_pct=round(100 * ra.min(), 1),
                    worst_mae_pct=round(100 * ma.min(), 1),
                    p1=round(p1["p_pass"], 4), p2=round(p2["p_pass"], 4),
                    p_comb=round(pc, 4), p_comb_ci95=f"[{max(0,pc-1.96*se):.3f},{min(1,pc+1.96*se):.3f}]",
                    med_sessions=(p1["med_days"] + p2["med_days"]
                                  if np.isfinite(p1["med_days"]) and np.isfinite(p2["med_days"]) else np.nan),
                    p90_sessions=(p1["p90_days"] + p2["p90_days"]
                                  if np.isfinite(p1["p90_days"]) and np.isfinite(p2["p90_days"]) else np.nan),
                    p1_death_daily=round(p1["p_daily"], 4), p1_death_floor=round(p1["p_floor"], 4),
                    p1_timeout=round(p1["p_timeout"], 4)))

  res = pd.DataFrame(rows)
  res.to_csv(OUT / "step3_barrier_sweep.csv", index=False)
  pd.set_option("display.width", 300, "display.max_columns", 40)
  for sample in ("full", "post-2021"):
      for cost in ("meas_1.84", "old_3.50"):
          d = res[(res["sample"] == sample) & (res["cost"] == cost) & (res.sizing == "vt_cap3")]
          print(f"\n=== {sample} | cost {cost} | vol-target cap 3 (inherited sizing policy) ===")
          print(d[["vm", "SR_net", "vol_ann_pct", "worst_mae_pct", "p1", "p2", "p_comb",
                   "med_sessions", "p90_sessions", "p1_death_daily", "p1_death_floor",
                   "p1_timeout"]].to_string(index=False))


if __name__ == "__main__":
    main()
