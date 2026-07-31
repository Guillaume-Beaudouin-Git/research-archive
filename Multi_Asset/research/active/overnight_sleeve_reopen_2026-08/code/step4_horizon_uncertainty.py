"""Step 4 — (a) the horizon gradient the June kill assumed away, (b) parameter risk.

(a) FTMO has NO max trading period (rules.md:28). The June 2026 kill was run against a
    self-imposed 91-calendar-day wall (~65 sessions). We report p(pass) under per-phase
    caps of 65 / 130 / 260 sessions and unlimited, so the cost of the wall is explicit.

(b) The Monte-Carlo CI in step 3 is binomial noise on a FIXED historical series. It is
    NOT the uncertainty that matters: post-2021 the net drift is only t_HAC 1.41, so the
    series itself is uncertain. We therefore nest the simulation inside a Politis-Romano
    stationary block bootstrap OF THE HISTORY: each replicate is an alternative 5-year
    history drawn from the same process, and we report the spread of p(pass) across
    replicates. This is the honest interval.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common_reopen import (COST_MEAS_BPS, COST_OLD_BPS, FTMO_P1_TGT, FTMO_P2_TGT, MAIN,
                           OUT, vol_target)

sys.path.insert(0, str(MAIN / "PropFirms" / "ftmo" / "program_2026-06"
                       / "ftmo_alpha_program" / "engine"))
from ftmo_first_passage import _stationary_block_matrix  # noqa: E402
from step3_barrier import phase, sized  # noqa: E402
import step3_barrier as S3  # noqa: E402

BREAK = pd.Timestamp("2021-01-01")
path = pd.read_csv(OUT / "step2_gold_window_path.csv", index_col=0, parse_dates=True)
post = path[path.index >= BREAK]

# ── (a) horizon gradient ─────────────────────────────────────────────────────
S3.N_PATHS = 20_000
rows = []
for sample, sub in (("full", path), ("post-2021", post)):
    for cost_lab, cost in (("meas_1.84", COST_MEAS_BPS), ("old_3.50", COST_OLD_BPS)):
        for vm in (2.0, 3.0, 4.0, 5.0):
            r, m = sized(sub, "vt", vm, cost)
            ra, ma = r.to_numpy(), m.to_numpy()
            for cap_lab, H in (("65_sess(~91d,June wall)", 65), ("130_sess(~182d)", 130),
                               ("260_sess(~1y)", 260), ("unlimited", len(ra))):
                p1 = phase(ra, ma, FTMO_P1_TGT, 42, H)
                p2 = phase(ra, ma, FTMO_P2_TGT, 43, H)
                rows.append(dict(sample=sample, cost=cost_lab, vm=vm, horizon=cap_lab,
                                 p1=round(p1["p_pass"], 4), p2=round(p2["p_pass"], 4),
                                 p_comb=round(p1["p_pass"] * p2["p_pass"], 4),
                                 p1_timeout=round(p1["p_timeout"], 4)))
hz = pd.DataFrame(rows)
hz.to_csv(OUT / "step4_horizon_gradient.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30)
print("=== (a) cost of the self-imposed horizon wall (vol-target cap 3) ===")
print(hz.pivot_table(index=["sample", "cost", "vm"], columns="horizon",
                     values="p_comb").to_string())

# ── (b) parameter risk: bootstrap the HISTORY, then simulate ─────────────────
B, MC = 200, 2_000
S3.N_PATHS = MC
print(f"\n=== (b) parameter risk: {B} block-bootstrap histories x {MC} MC paths ===")
out = []
for sample, sub in (("post-2021", post), ("full", path)):
    T = len(sub)
    block = max(1.0, round(np.sqrt(T)))
    rng = np.random.default_rng(11)
    idx_all = _stationary_block_matrix(T, B, T, block, rng)
    for cost_lab, cost in (("meas_1.84", COST_MEAS_BPS), ("old_3.50", COST_OLD_BPS)):
        for vm in (2.0, 3.0, 4.0):
            pcs, srs = [], []
            for b in range(B):
                rep = sub.iloc[idx_all[b]].reset_index(drop=True)
                rep.index = pd.RangeIndex(len(rep))
                pos = vol_target(rep["ret"], cap=3.0) * vm
                ok = pos > 0
                c = pos * cost * 1e-4
                ra = (pos * rep["ret"] - c)[ok].to_numpy()
                ma = (pos * rep["mae"] - c)[ok].to_numpy()
                srs.append(ra.mean() / ra.std(ddof=1) * np.sqrt(252.3))
                p1 = phase(ra, ma, FTMO_P1_TGT, 1000 + b, len(ra))
                p2 = phase(ra, ma, FTMO_P2_TGT, 5000 + b, len(ra))
                pcs.append(p1["p_pass"] * p2["p_pass"])
            pcs, srs = np.array(pcs), np.array(srs)
            out.append(dict(sample=sample, cost=cost_lab, vm=vm,
                            SR_p05=round(np.percentile(srs, 5), 3),
                            SR_med=round(np.median(srs), 3),
                            SR_p95=round(np.percentile(srs, 95), 3),
                            SR_neg_frac=round(float((srs <= 0).mean()), 3),
                            p_comb_p05=round(np.percentile(pcs, 5), 3),
                            p_comb_med=round(np.median(pcs), 3),
                            p_comb_p95=round(np.percentile(pcs, 95), 3),
                            p_comb_below_25pct=round(float((pcs < 0.25).mean()), 3)))
            print(f"  {sample:10s} {cost_lab:10s} vm={vm:<4g} done")
pu = pd.DataFrame(out)
pu.to_csv(OUT / "step4_parameter_risk.csv", index=False)
print()
print(pu.to_string(index=False))
