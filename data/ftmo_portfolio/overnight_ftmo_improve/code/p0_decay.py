"""PISTE 0 — edge vivant ou mourant? Decay test SILVER (post-2014) + SOYBEAN.
On the gross window edge (win_w): trailing-252 rolling Sharpe + 90% block-bootstrap CI,
Chow-style pre/post split (HAC t), recent-2y significance. DEAD per pre-registered rule:
post-split t_HAC < 1.5 OR recent-2y rolling-12m Sharpe 90% CI entirely <= 0."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overnight_series as OS
OUT = HERE.parent / "results"
ANN = 252.0


def hac_t(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 10 or x.std() == 0:
        return float("nan"), float("nan")
    m = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(m.params[0]), float(m.tvalues[0])


def sharpe(x):
    x = np.asarray(x, float)
    return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else float("nan")


def boot_sharpe_ci(x, block=10, nboot=2000, seed=0):
    x = np.asarray(x, float); n = len(x); rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block)); out = np.empty(nboot)
    for b in range(nboot):
        idx = np.concatenate([np.arange(s, s + block) % n for s in rng.integers(0, n, nb)])[:n]
        out[b] = sharpe(x[idx])
    return float(np.percentile(out, 5)), float(np.percentile(out, 95))


def analyse(name, split):
    d = OS.build(name, 2.0)
    w = d["win_w"]                          # gross window edge (winsorised log), per exit-date
    full_m, full_t = hac_t(w.values)
    pre = w[w.index < split]; post = w[w.index >= split]
    pre_m, pre_t = hac_t(pre.values); post_m, post_t = hac_t(post.values)
    # recent 2y (504 obs)
    rec = w.iloc[-504:]
    rec_m, rec_t = hac_t(rec.values)
    rec_lo, rec_hi = boot_sharpe_ci(rec.values)
    # trailing-12m rolling Sharpe path (last few values)
    roll = w.rolling(252).apply(lambda a: a.mean() / a.std() * np.sqrt(ANN) if a.std() > 0 else np.nan, raw=True)
    dead = (post_t < 1.5) or (rec_hi <= 0)
    r = dict(name=name, n=len(w), start=str(w.index.min().date()), end=str(w.index.max().date()),
             split=split, full_sharpe=round(sharpe(w.values), 2), full_bp=round(full_m * 1e4, 2), full_t=round(full_t, 2),
             pre_sharpe=round(sharpe(pre.values), 2), pre_t=round(pre_t, 2), pre_n=len(pre),
             post_sharpe=round(sharpe(post.values), 2), post_bp=round(post_m * 1e4, 2), post_t=round(post_t, 2), post_n=len(post),
             recent2y_sharpe=round(sharpe(rec.values), 2), recent2y_t=round(rec_t, 2),
             recent2y_sharpe_ci90=[round(rec_lo, 2), round(rec_hi, 2)],
             roll12m_last=round(float(roll.dropna().iloc[-1]), 2) if roll.notna().any() else None,
             roll12m_min_last3y=round(float(roll.iloc[-756:].min()), 2),
             VERDICT="MORT" if dead else "VIVANT")
    return r


def main():
    res = {}
    for nm, split in [("SILVER", "2020-01-01"), ("SOYBEAN", "2022-01-01")]:
        r = analyse(nm, split); res[nm] = r
        print(f"=== {nm} ({r['start']}->{r['end']}, n={r['n']}, split {split}) ===")
        print(f"  full: Sharpe {r['full_sharpe']}  {r['full_bp']:+}bp  t_HAC {r['full_t']}")
        print(f"  pre  ({r['pre_n']}): Sharpe {r['pre_sharpe']}  t {r['pre_t']}")
        print(f"  post ({r['post_n']}): Sharpe {r['post_sharpe']}  {r['post_bp']:+}bp  t_HAC {r['post_t']}")
        print(f"  recent 2y: Sharpe {r['recent2y_sharpe']}  t {r['recent2y_t']}  CI90 {r['recent2y_sharpe_ci90']}")
        print(f"  roll-12m last {r['roll12m_last']}  min last 3y {r['roll12m_min_last3y']}")
        print(f"  ==> VERDICT: {r['VERDICT']}\n")
    OUT.mkdir(exist_ok=True)
    (OUT / "p0_decay.json").write_text(json.dumps(res, indent=2))
    print("written p0_decay.json")


if __name__ == "__main__":
    main()
