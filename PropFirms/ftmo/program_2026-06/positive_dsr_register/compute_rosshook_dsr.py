"""
compute_rosshook_dsr.py — ONE DSR computation on the EXISTING Ross Hook replication series.
Reuses repo-root dsr.py VERBATIM (Bailey-LdP probabilistic DSR ∈[0,1]). No new backtest, no re-run,
no parameter search — N program-wide stays 108. READ-ONLY except this script + the json/register it writes.

Series: research/s076_replication/results/mtm_deployable.csv col `ret` (deployable MTM daily, real data).
Convention: periods_per_year=252 (matches the s076 replication's Sharpe 0.44); rf=0.0 PRIMARY because the
series is a 0.5%-risk-sized strategy P&L (not a cash-alternative asset) — using dsr.py's default rf=0.02
would drive the Sharpe negative purely from the low-leverage sizing (~0.9%/yr P&L < 2% cash), a sizing
artifact, not the edge. rf=0.02 reported as a caveat.
N=1  = honest primary (pre-specified single test; _expected_max_sr returns SR*=0 -> standard PSR).
N=108 = conservative program-wide floor (std_sr_trials = 0.845, the program's frozen Gate-0 noise SE;
        also reported at the dsr.py default std_sr=1.0).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(REPO))
from dsr import deflated_sharpe_ratio, _expected_max_sr  # noqa: E402  (verbatim)

PPY = 252
STD_SR_PROGRAM = 0.845   # funnel/register frozen Gate-0 noise SE (annualized SR units)
ser = pd.read_csv(REPO / "research/s076_replication/results/mtm_deployable.csv",
                  index_col=0, parse_dates=True)["ret"]


def block(returns: np.ndarray, label: str) -> dict:
    out = {"window": label, "T_obs": int(len(returns))}
    for rf in (0.0, 0.02):
        d1 = deflated_sharpe_ratio(returns, n_trials=1, periods_per_year=PPY, rf=rf)         # SR*=0
        d108 = deflated_sharpe_ratio(returns, n_trials=108, periods_per_year=PPY, rf=rf,
                                     mean_sr_trials=0.0, std_sr_trials=STD_SR_PROGRAM)
        d108_def = deflated_sharpe_ratio(returns, n_trials=108, periods_per_year=PPY, rf=rf,
                                         mean_sr_trials=0.0, std_sr_trials=1.0)
        tag = "rf0" if rf == 0.0 else "rf0.02"
        out[tag] = {
            "sharpe_ann": round(d1["sharpe"], 4),
            "skew": round(d1["skewness"], 4), "excess_kurtosis": round(d1["excess_kurtosis"], 2),
            "DSR_N1": round(d1["dsr"], 4), "SRstar_N1": round(d1["sr_benchmark"], 4),
            "DSR_N108_std0.845": round(d108["dsr"], 4), "SRstar_N108_std0.845": round(d108["sr_benchmark"], 3),
            "DSR_N108_std1.0": round(d108_def["dsr"], 4), "SRstar_N108_std1.0": round(d108_def["sr_benchmark"], 3),
        }
    return out


res = {
    "series": "research/s076_replication/results/mtm_deployable.csv :: ret",
    "engine": "dsr.py (repo root) deflated_sharpe_ratio — Bailey-LdP probabilistic DSR in [0,1]",
    "convention": "PPY=252; rf=0 PRIMARY (0.5%-risk strategy P&L, matches replication Sharpe 0.44); "
                  "rf=0.02 caveat (default; sizing-confounded). N=1 -> SR*=0 (pre-specified single test); "
                  "N=108 std_sr_trials=0.845 (program noise SE) + std_sr=1.0 (dsr.py default).",
    "full": block(ser.dropna().to_numpy(), "full 2007-2026"),
    "oos_2016": block(ser[ser.index >= "2016-01-01"].dropna().to_numpy(), "OOS >=2016"),
}
json.dump(res, open(REPO / "research/positive_dsr_register/rosshook_dsr.json", "w"), indent=2)

for w in ("full", "oos_2016"):
    b = res[w]; r0 = b["rf0"]
    print(f"\n[{b['window']}] T={b['T_obs']} | rf=0: SR_ann={r0['sharpe_ann']} skew={r0['skew']} exkurt={r0['excess_kurtosis']}")
    print(f"   DSR(N=1, SR*={r0['SRstar_N1']})        = {r0['DSR_N1']}   {'CLEARS' if r0['DSR_N1']>0.5 else 'fails'} 0.5")
    print(f"   DSR(N=108, SR*={r0['SRstar_N108_std0.845']} @std0.845) = {r0['DSR_N108_std0.845']}   {'CLEARS' if r0['DSR_N108_std0.845']>0.5 else 'fails'} 0.5  (std1.0 SR*={r0['SRstar_N108_std1.0']} -> DSR {r0['DSR_N108_std1.0']})")
    print(f"   [caveat rf=0.02]: SR_ann={b['rf0.02']['sharpe_ann']} -> DSR(N=1)={b['rf0.02']['DSR_N1']}, DSR(N=108)={b['rf0.02']['DSR_N108_std0.845']}")
print(f"\njson -> research/positive_dsr_register/rosshook_dsr.json")
