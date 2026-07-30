"""Step 0 (L53) — vehicle materiality matrix. Runs BEFORE any performance measure."""
from __future__ import annotations

import json

import pandas as pd

from common import (ACCOUNT_USD, COMMISSION_PER_SIDE, COMMISSION_TIERED, CONTRACTS,
                    NOTIONAL, OUT, REF_PX)

BREAKEVEN_BPS = {"MGC": None, "SIL": 5.3, "MCL": 3.5, "MZS": 2.0}
SLEEVE_OF = {"MGC": "GOLD", "SIL": "SILVER", "MCL": "WTI", "MZS": "SOYBEAN"}
# annualised vol of the sleeve at ~1.0x notional, from the source tear-sheets
SLEEVE_VOL_AT_1X = {"MGC": 0.068, "SIL": 0.092, "MCL": 0.081, "MZS": 0.096}
SLEEVE_MAXDD_AT_1X = {"MGC": -0.194, "SIL": -0.128, "MCL": -0.137, "MZS": -0.197}

rows = []
for code, c in CONTRACTS.items():
    notional = NOTIONAL[code]
    tick_bps = c["tick_val"] / notional * 1e4
    comm_bps = 2 * COMMISSION_PER_SIDE / notional * 1e4
    comm_bps_tiered = 2 * COMMISSION_TIERED / notional * 1e4
    rows.append(dict(
        contract=code, sleeve=SLEEVE_OF[code],
        size=f'{c["size"]} {c["unit"]}', ref_px=REF_PX[c["px_col"]],
        notional_usd=round(notional, 0),
        margin_usd=c["margin"],
        margin_pct_account=round(100 * c["margin"] / ACCOUNT_USD, 1),
        notional_x_account=round(notional / ACCOUNT_USD, 2),
        tick_bps=round(tick_bps, 3),
        comm_rt_bps=round(comm_bps, 3),
        rt_bps_base=round(tick_bps + comm_bps, 2),
        rt_bps_stress2tick=round(2 * tick_bps + comm_bps, 2),
        rt_bps_tiered=round(tick_bps + comm_bps_tiered, 2),
        breakeven_bps=BREAKEVEN_BPS[code],
        implied_sleeve_vol_1lot=round(100 * SLEEVE_VOL_AT_1X[code] * notional / ACCOUNT_USD, 1),
        implied_maxdd_1lot=round(100 * SLEEVE_MAXDD_AT_1X[code] * notional / ACCOUNT_USD, 1),
    ))

df = pd.DataFrame(rows)


def verdict(r):
    reasons = []
    if r.margin_pct_account > 35:
        reasons.append(f"M1 margin {r.margin_pct_account}% > 35%")
    if r.notional_x_account > 3.0:
        reasons.append(f"M2 granularity {r.notional_x_account}x > 3.0x")
    if r.breakeven_bps is not None and r.rt_bps_base > r.breakeven_bps:
        reasons.append(f"K4 cost base {r.rt_bps_base} > breakeven {r.breakeven_bps}")
    stress_flag = (r.breakeven_bps is not None and r.rt_bps_stress2tick > r.breakeven_bps
                   and r.rt_bps_base <= r.breakeven_bps)
    if reasons:
        return "REJECTED-step0", "; ".join(reasons)
    if stress_flag:
        return "SURVIVES-step0(stress-flagged)", f"stress {r.rt_bps_stress2tick} > breakeven {r.breakeven_bps}"
    return "SURVIVES-step0", ""


df[["verdict_step0", "reason"]] = df.apply(lambda r: pd.Series(verdict(r)), axis=1)

# PL reference (out of the overnight scope, reported for the Q1-seasonality block)
pl_notional = 50 * REF_PX["PL"]
pl = dict(contract="PL (ref, not overnight)", notional_usd=round(pl_notional),
          margin_usd=round(0.09 * pl_notional),
          margin_pct_account=round(100 * 0.09 * pl_notional / ACCOUNT_USD, 1),
          notional_x_account=round(pl_notional / ACCOUNT_USD, 2))

pd.set_option("display.width", 250, "display.max_columns", 50)
print(df.to_string(index=False))
print("\nPL reference:", pl)
print("\nAccount USD:", ACCOUNT_USD)

df.to_csv(OUT / "step0_vehicle_matrix.csv", index=False)
(OUT / "step0_pl_reference.json").write_text(json.dumps(pl, indent=2))
