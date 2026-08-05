"""If cohorts group, WHY — and is the state observable at T-1?

L38 (beta orthogonality): regress the cohort outcome on a vol-targeted buy-and-hold
of the sleeve's primary assets (US100 + GER40) over the SAME window. R^2 > 30 %
means the "regime" is index beta, and must be named that.

L54 (mean vs variance): a state that predicts the VARIANCE but not the MEAN cannot
make a timing rule. Both R^2 are reported side by side.

Ex-ante: only states knowable strictly BEFORE the start date are tested, in terciles,
with block-bootstrap CIs and the deflation bar sqrt(2 ln k) — the same protocol as
`attribution_timing` P3, so the numbers are comparable to it.

usage: mechanism.py <vm> [H]
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

import cc_lib as C

VM = sys.argv[1] if len(sys.argv) > 1 else "10"
H = int(sys.argv[2]) if len(sys.argv) > 2 else 56
CACHE = C.Path("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/cache")

real = pd.read_csv(C.OUT / f"real_vm{VM}.csv", parse_dates=["start_date"])
sd = pd.DatetimeIndex(real["start_date"])
lab = np.where(real["cal_days"].to_numpy() <= H, real["out"].to_numpy(), "not_reached")
y = (lab == "pass").astype(float)
n = len(y)
BLK = C.L.block_for_horizon(H)

# ------------------------------------------------------- index book, daily CET
px = pd.concat({k: pd.read_parquet(CACHE / f"{k}_daily_cet.parquet")["close"]
                for k in ("US100", "GER40")}, axis=1).dropna()
ret = np.log(px).diff()
book = ret.mean(axis=1)                       # equal-weight long index book
rv = book.rolling(60).std() * np.sqrt(252)
vt = (book / rv.shift(1)).clip(-1, 1) * 0.10   # vol-targeted to 10 % ann., T-1 scaling
vt = vt.dropna()


def win(d0, days, s):
    """Sum of `s` over the calendar window [d0, d0+days]."""
    return s.loc[(s.index > d0) & (s.index <= d0 + pd.Timedelta(days=days))]


fwd_vt = np.array([win(d, H, vt).sum() for d in sd])            # contemporaneous
fwd_rv = np.array([win(d, H, book).std() * np.sqrt(252) for d in sd])
# strictly pre-start states
prv = np.array([rv.reindex(rv.index[rv.index < d]).iloc[-1] if (rv.index < d).any()
                else np.nan for d in sd])
pm60 = np.array([book.loc[book.index < d].tail(60).sum() for d in sd])
pm252 = np.array([book.loc[book.index < d].tail(252).sum() for d in sd])
cum = np.log(px.mean(axis=1))
pdd = np.array([(cum.loc[cum.index < d].tail(252).iloc[-1]
                 - cum.loc[cum.index < d].tail(252).max())
                if (cum.index < d).sum() > 10 else np.nan for d in sd])


def ols(yv, xv, name):
    m = np.isfinite(yv) & np.isfinite(xv)
    X = sm.add_constant(xv[m])
    r = sm.OLS(yv[m], X).fit(cov_type="HAC", cov_kwds={"maxlags": BLK})
    return dict(model=name, n=int(m.sum()), beta=float(r.params[1]),
                t_hac=float(r.tvalues[1]), r2=float(r.rsquared))


rows = [
    ols(y, fwd_vt, "L38  pass ~ vol-targeted index B&H over the SAME window"),
    ols(y, fwd_rv, "L38b pass ~ realized index vol over the SAME window"),
    ols(fwd_vt, prv, "L54 MEAN     index return over window ~ rv60 at T-1"),
    ols(fwd_vt ** 2, prv, "L54 VARIANCE index return^2   over window ~ rv60 at T-1"),
    ols(fwd_rv, prv, "L54 VARIANCE realized vol over window ~ rv60 at T-1"),
    ols(y, prv, "exante pass ~ rv60 at T-1"),
    ols(y, pm60, "exante pass ~ 60d index momentum at T-1"),
    ols(y, pm252, "exante pass ~ 252d index momentum at T-1"),
    ols(y, pdd, "exante pass ~ drawdown from 252d high at T-1"),
]
reg = pd.DataFrame(rows)
reg.to_csv(C.TAB / f"mechanism_reg_vm{VM}_H{H}.csv", index=False)
print(reg.round(4).to_string(index=False))


# ---------------------------------------------------- tercile buckets, ex ante
def bb(yv, block, n_boot=4000, seed=3):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(yv) / block))
    idx = ((np.arange(block)[None, :] +
            rng.integers(0, len(yv), size=(n_boot, nb))[:, :, None]) % len(yv)
           ).reshape(n_boot, -1)[:, :len(yv)]
    s = yv[idx].mean(axis=1)
    return float(np.quantile(s, .025)), float(np.quantile(s, .975)), float(s.std(ddof=1))


PRED = {"rv60_T-1": prv, "mom60_T-1": pm60, "mom252_T-1": pm252, "dd252_T-1": pdd}
buck, k_tests = [], 0
for nm, xv in PRED.items():
    m = np.isfinite(xv)
    q = pd.qcut(pd.Series(xv[m]), 3, labels=["low", "mid", "high"])
    for lv in ("low", "mid", "high"):
        sel = np.zeros(n, bool)
        sel[np.flatnonzero(m)[(q == lv).to_numpy()]] = True
        yy = y[sel]
        lo, hi, sdv = bb(yy, max(2, BLK))
        buck.append(dict(pred=nm, bucket=lv, n=int(sel.sum()), p=float(yy.mean()),
                         ci_lo=lo, ci_hi=hi, sd=sdv))
        k_tests += 1
b = pd.DataFrame(buck)
b["z"] = (b.p - y.mean()) / b.sd
b["bar"] = np.sqrt(2 * np.log(k_tests))
b["survives"] = b.z.abs() > b.bar
b["mde80_pt"] = 100 * 2.802 * b.sd
b.to_csv(C.TAB / f"mechanism_buckets_vm{VM}_H{H}.csv", index=False)
print(f"\n--- ex-ante tercile buckets, k={k_tests}, deflation bar "
      f"{np.sqrt(2*np.log(k_tests)):.2f}, overall p={y.mean():.3f} ---")
print(b.round(4).to_string(index=False))
