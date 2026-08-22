"""A.1 consistency check: Ross-Hook(independent replication) vs TSMOM-deployed (Cowork's comparator).
Pearson + Spearman, strict inner-join on date, with/without strictly-flat days. READ-ONLY."""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

warnings.filterwarnings("ignore")
ROOT = Path("<HOME>/Desktop/Algo_claude")
OUT = ROOT / "research/s076_replication/decorr_check"; OUT.mkdir(parents=True, exist_ok=True)
RH_PATH = ROOT / "research/s076_replication/results/mtm_deployable.csv"   # independent replication, deployable (idx+comm+crypto, ex-FX)
TS_PATH = ROOT / "data/ftmo_research/tsmom/chosen_returns.csv"            # Cowork comparator (phase2_3.py:46)

rh = pd.read_csv(RH_PATH, index_col=0, parse_dates=True)["ret"].rename("rosshook")  # daily MTM returns
ts = pd.read_csv(TS_PATH, index_col=0, parse_dates=True).iloc[:, 0].rename("tsmom")  # daily returns, col '0'
j = pd.concat([rh, ts], axis=1, join="inner").dropna()
both_active = j[(j["rosshook"].abs() > 1e-12) & (j["tsmom"].abs() > 1e-12)]


def pair(df):
    a, b = df["rosshook"].values, df["tsmom"].values
    return round(float(pearsonr(a, b)[0]), 4), round(float(spearmanr(a, b)[0]), 4)


p_all, s_all = pair(j)
p_act, s_act = pair(both_active)
# date-convention diagnostic: ±1-day shift on both-active set
shift_diag = {}
for sh in (-1, 1):
    js = pd.concat([rh.shift(sh), ts], axis=1, join="inner").dropna()
    js = js[(js["rosshook"].abs() > 1e-12) & (js["tsmom"].abs() > 1e-12)]
    shift_diag[sh] = round(float(pearsonr(js["rosshook"], js["tsmom"])[0]), 4) if len(js) > 30 else None

rows = [
    dict(metric="Pearson", all_common=p_all, both_active=p_act),
    dict(metric="Spearman", all_common=s_all, both_active=s_act),
    dict(metric="n_days", all_common=len(j), both_active=len(both_active)),
    dict(metric="window", all_common=f"{j.index.min().date()}..{j.index.max().date()}",
         both_active=f"{both_active.index.min().date()}..{both_active.index.max().date()}"),
    dict(metric="shift_diag_pearson(both_active)", all_common=f"rh-1d:{shift_diag[-1]}", both_active=f"rh+1d:{shift_diag[1]}"),
    dict(metric="rosshook_series", all_common=str(RH_PATH.relative_to(ROOT)), both_active="col=ret (deployable MTM, EET server-day)"),
    dict(metric="tsmom_series", all_common=str(TS_PATH.relative_to(ROOT)), both_active="col=0 (Cowork phase2_3.py:46)"),
]
pd.DataFrame(rows).to_csv(OUT / "decorr_check.csv", index=False)

cowork = 0.27
gap = abs(p_act - cowork)
verdict = (f"~0.25 CONFIRMED (A.1 sealed on real data): independent-replication Ross-Hook vs TSMOM-deployed "
           f"Pearson={p_act} / Spearman={s_act} (both-active n={len(both_active)}, {both_active.index.min().date()}.."
           f"{both_active.index.max().date()}) ≈ Cowork's +0.27.") if gap <= 0.07 else (
           f"MATERIAL GAP vs Cowork +0.27: our Pearson(both-active)={p_act}, Spearman={s_act} "
           f"(n={len(both_active)}). Δ={gap:.2f}. Hypothesis: "
           + ("date-convention offset (see shift_diag) — " if (shift_diag[-1] and abs(shift_diag[-1]) > abs(p_act) + 0.05)
              or (shift_diag[1] and abs(shift_diag[1]) > abs(p_act) + 0.05) else "")
           + "different Ross-Hook provenance (Cowork used ftmo_lab series) and/or window.")

md = f"""# A.1 decorrelation re-check — Ross Hook (independent replication) vs TSMOM-deployed

**Ross Hook** = `{RH_PATH.relative_to(ROOT)}` col `ret` — deployable MTM (indices+commodity+crypto, ex-FX),
independent replication, never through ftmo_lab; EET server-day daily returns.
**TSMOM deployed** = `{TS_PATH.relative_to(ROOT)}` col `0` — the exact series Cowork loaded (`session_cowork/phase2_3.py:46`).

| metric | all common days | both-active (no flat day either side) |
|---|---|---|
| Pearson | {p_all} | **{p_act}** |
| Spearman | {s_all} | **{s_act}** |
| n days | {len(j)} | {len(both_active)} |
| window | {j.index.min().date()}..{j.index.max().date()} | {both_active.index.min().date()}..{both_active.index.max().date()} |

Date-convention diagnostic (both-active, ±1-day shift of Ross Hook): rh−1d Pearson={shift_diag[-1]}, rh+1d={shift_diag[1]}
(same-date alignment {p_act} is {'the strongest → conventions match' if (not shift_diag[-1] or abs(shift_diag[-1])<=abs(p_act)+0.02) and (not shift_diag[1] or abs(shift_diag[1])<=abs(p_act)+0.02) else 'NOT the strongest → possible date offset, flagged'}).

**Verdict:** {verdict}

*Both series are daily returns (not prices); strict inner-join on date; "both-active" drops days strictly flat
on either side (no position) — the window comparable to Cowork's 2018-2026 TSMOM_PROXY overlap.*
"""
(OUT / "decorr_check.md").write_text(md)

print(f"RossHook(replication) col=ret  vs  TSMOM {TS_PATH.relative_to(ROOT)} col=0")
print(f"all-common : Pearson {p_all} | Spearman {s_all} | n={len(j)} | {j.index.min().date()}..{j.index.max().date()}")
print(f"both-active: Pearson {p_act} | Spearman {s_act} | n={len(both_active)} | {both_active.index.min().date()}..{both_active.index.max().date()}")
print(f"shift diag (both-active): rh-1d {shift_diag[-1]} | rh+1d {shift_diag[1]} (same-date={p_act})")
print("VERDICT:", verdict)
