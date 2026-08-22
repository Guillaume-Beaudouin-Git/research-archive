"""Preuve d'équivalence clone instrumenté <-> engine_v22.run_funded, et
vérification que CFG_FUNDED_V28 == CFG_FUNDED_V24_SWING sur l'étage funded
(l'overlay leg_lev_cap est annoncé NO-OP en funded : on le mesure)."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(HERE))
import engine_v22 as V          # noqa: E402
import config_v22 as C22        # noqa: E402
import funded_instr as FI       # noqa: E402
E = V.E

t0 = time.time()
M = V.load_stack(orb_rt_bps="era")
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
print(f"stack [{time.time()-t0:.0f}s]", flush=True)

st = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP)
                     for _, lo, hi in C22.FUNDED_WINDOWS])
print("cohortes:", len(st))

for tag, vm in (("vm1.00", 1.0), ("vm0.85", 0.85)):
    cfg = dict(C22.CFG_FUNDED_V28, vm=vm)
    ok, bad, diffs = FI.check_equiv(M, WT, ON, cfg, st,
                                    horizon=C22.FUNDED_HORIZON,
                                    wd_every=C22.FUNDED_WD_EVERY)
    print(f"EQUIV {tag}: ok={ok} bad={bad}  [{time.time()-t0:.0f}s]", flush=True)
    if diffs:
        print(diffs[:3])

# --- V28 (leg_lev_cap) vs V24_SWING : no-op attendu en funded ---
for vm in (1.0, 1.2):
    a = [V.run_funded(M, int(i), WT, ON, dict(C22.CFG_FUNDED_V24_SWING, vm=vm),
                      horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
         for i in st]
    b = [V.run_funded(M, int(i), WT, ON, dict(C22.CFG_FUNDED_V28, vm=vm),
                      horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
         for i in st]
    da, db = pd.DataFrame(a), pd.DataFrame(b)
    same = all(np.allclose(da[k].astype(float), db[k].astype(float))
               for k in ("wd", "payouts", "life", "busted", "residual"))
    print(f"V28 == V24_SWING @ vm{vm}: {same} | bust {da.busted.mean():.3f} vs "
          f"{db.busted.mean():.3f} | wd {da.wd.mean():.0f} vs {db.wd.mean():.0f}",
          flush=True)

# --- marge : à quel vm le cap 60% mord-il en funded ? ---
rows = []
for vm in (0.6, 0.85, 1.0, 1.2):
    E.MARGIN_LOG.clear()
    cfg = dict(C22.CFG_FUNDED_V28, vm=vm, margin_log=True)
    for i in st[::4]:
        V.run_funded(M, int(i), WT, ON, cfg, horizon=C22.FUNDED_HORIZON,
                     wd_every=C22.FUNDED_WD_EVERY)
    ml = np.array(E.MARGIN_LOG)
    rows.append(dict(vm=vm, n=len(ml), p50=np.percentile(ml, 50),
                     p95=np.percentile(ml, 95), p99=np.percentile(ml, 99),
                     mx=ml.max(), bind=(ml > 0.60).mean()))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(HERE.parent / "out" / "margin_bind_funded.csv", index=False)
print(f"done [{time.time()-t0:.0f}s]")
