"""Residual-risk-by-sleeve: where does the intra-bar low-check tail live, and does the gate
(J1-in-zone) cover it? Enrich bust events with dominant-sleeve x gate-zone(USDJPY>=160).
Also funded bust timing (life, banked withdrawals) to explain the VAL coincidence."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))
import engine as E
import engine_v22 as V
import config_v22 as C22
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "j1_suspend_study"))
import gate as G
sys.path.insert(0, str(HERE))
import lowcheck_engine as LC
TAB = HERE / "tables"; REC = HERE / "records"
LEGS = E.LEGS
t0 = time.time()

# gate-zone dates (USDJPY close >= 160, the non-causal actual-zone flag for attribution)
PX_JPY = pd.read_parquet(E.CACHE / "panel_px.parquet")["USDJPY"]
ZONE = set(PX_JPY.index[PX_JPY >= 160.0].normalize())


def zone_flag(dates):
    return pd.to_datetime(dates).normalize().isin(ZONE)


# ---- 1. challenge low-check bust events: sleeve x zone ----
print("=== CHALLENGE low-check busts: dominant sleeve x gate-zone ===")
for tag in ["swing_ON_low", "swing_OFF_low"]:
    ev = pd.read_csv(REC / f"events_{tag}.csv", parse_dates=["date"])
    ucols = [f"u_{l}" for l in LEGS]
    ev["dom"] = ev[ucols].idxmin(axis=1).str.replace("u_", "")
    ev["zone"] = zone_flag(ev["date"].values)
    tab = ev.groupby(["dom", "zone"]).size().unstack(fill_value=0)
    print(f"\n[{tag}] n={len(ev)}  in-zone={ev.zone.sum()} ({100*ev.zone.mean():.1f}%)")
    print(tab.to_string())

# ---- 2. funded low-check busts: attribution + timing (re-run ON with events) ----
print("\n=== FUNDED low-check busts: attribution + timing (gate ON) ===")
M = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
susp = G.suspend_causal(PX_JPY, 160.0, 155.0, 10)
mult = (~susp.reindex(M["dates_idx"]).fillna(False).to_numpy(bool)).astype(float)
wt = WT.copy(); wt[:, 1] = wt[:, 1] * mult
E.MRATE = np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS])
bL = np.array([C22.swap_bps(s, "long") for s in LEGS]); bS = np.array([C22.swap_bps(s, "short") for s in LEGS])
M["swL"] = np.tile(bL, (M["n"], 1)); M["swS"] = np.tile(bS, (M["n"], 1))
M["rt"] = M["rt"] + np.array([C22.comm_rt_bps(s) for s in LEGS])

for mode in ["low", "low_dom"]:
    events, extrs, busts = [], [], 0
    for w, lo, hi in C22.FUNDED_WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP):
            r = LC.run_funded(M, int(i0), wt, ON, C22.CFG_FUNDED, horizon=C22.FUNDED_HORIZON,
                              wd_every=C22.FUNDED_WD_EVERY, mode=mode, events=events)
            extrs.append(r["wd"] + r["residual"]); busts += r["busted"]
    ev = pd.DataFrame(events)
    ev["dom"] = ev[[f"u_{l}" for l in LEGS]].idxmin(axis=1).str.replace("u_", "")
    ev["zone"] = zone_flag(ev["date"].values)
    print(f"\n[funded ON {mode}] busts={busts}/191 ({100*busts/191:.0f}%)  "
          f"mean_extr=${np.mean(extrs):.0f}  bust in-zone={ev.zone.sum()}/{len(ev)}")
    print("  by dominant sleeve:", ev.dom.value_counts().to_dict())
    print(f"  bust timing: median life={ev.life.median():.0f}d  median banked wd=${ev.wd_banked.median():.0f} "
          f"(banked>0: {100*(ev.wd_banked>0).mean():.0f}% -> late busts keep payouts)")
    ev.to_csv(TAB / f"funded_busts_ON_{mode}.csv", index=False)

print(f"\n[{time.time()-t0:.0f}s] done")
