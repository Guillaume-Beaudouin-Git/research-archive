import sys, json
import pandas as pd, numpy as np, config as C, simulator as S, run_phase3 as R, audit_stack as A
VAL, FEE = 1453.0, 96.0
D = A.load_audited(); WT, ON = R.align(D)
BASE = dict(R.BASE, taper_buf=0.02, abandon_buf=0.02, abandon_days=5, max_cal_days=91,
            p2_mult=1.2, vol_mult=14.0, on_w=0.6, orb_risk=0.0025)
def run(tag, lo="2013-10-01", hi="2019-12-31", step=10, **over):
    cfg = dict(BASE); cfg.update(over)
    st = A.cohorts(D, lo, hi, step=step)
    res = [S.run_funnel(D,i0,WT,ON,cfg,wall_days=91,retries=True) for i0 in st]
    df = pd.DataFrame(res); p, att = df.funded.mean(), df.attempts.mean()
    ev = p*VAL - att*FEE
    print(f"{tag}: p={p:.3f} att={att:.2f} EV=${ev:+,.0f}", flush=True)
    return ev
if __name__ == "__main__":
    for spec in json.loads(sys.argv[1]):
        run(spec.pop("tag"), **spec)
