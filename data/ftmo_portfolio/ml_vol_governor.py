"""ML-1 — Vol-predictive governor (pre-registered spec, frozen before results).

Target: |book return|_{t+1} proxy of next-day book vol.
Features (a priori, HAR-style + VIX): RV1=|r_t|, RV5, RV22 (book), VIX close_t.
Model: Ridge (alpha=1.0 fixed) on standardized features, log1p target.
Walk-forward: refit each Jan-01 using all data up to t (min 3y warmup, start 2016).
Mapping: vm_t+1 = clip( VM_BASE * (med_train_volhat / volhat_t+1), 1.3, 2.8 ).
No outcome-based tuning anywhere. Output: cache/sim_VM.parquet.
"""
import numpy as np
import pandas as pd
import config as C

VM_BASE = 2.0
LO, HI = 1.3, 2.8

# fixed-weight book proxy consistent with simulator weights
sl = pd.read_parquet(C.CACHE / "phase1c_sleeves.parquet")
orb = pd.read_parquet(C.CACHE / "orb_e7_R15.parquet")["R"]
book = (0.5 * sl["gold"].fillna(0) + 0.5 * sl["J1"].fillna(0)
        + 0.35 * sl["overnight"].fillna(0)
        + 0.0025 * orb.reindex(sl.index).fillna(0.0))
book = book.loc["2013-01-01":].dropna()

vix = pd.read_csv(C.PANELS / "vix.csv", index_col=0, parse_dates=True).iloc[:, 0]
vix = vix.reindex(book.index).ffill()

r = book
X = pd.DataFrame({
    "rv1": r.abs(),
    "rv5": r.rolling(5).std(),
    "rv22": r.rolling(22).std(),
    "vix": vix,
}).dropna()
y = r.abs().shift(-1).reindex(X.index)        # target: next-day |r|
X = X.iloc[:-1]; y = y.iloc[:-1]

from numpy.linalg import lstsq

def ridge_fit(Xtr, ytr, alpha=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    Z = (Xtr - mu) / sd
    Z = np.c_[np.ones(len(Z)), Z]
    A = Z.T @ Z + alpha * np.eye(Z.shape[1]); A[0, 0] -= alpha
    w = np.linalg.solve(A, Z.T @ np.log1p(ytr))
    return mu, sd, w

def ridge_pred(Xte, mu, sd, w):
    Z = (Xte - mu) / sd
    Z = np.c_[np.ones(len(Z)), Z]
    return np.expm1(Z @ w).clip(min=1e-5)

years = sorted(set(X.index.year))
vol_hat = pd.Series(np.nan, index=X.index)
med_train = pd.Series(np.nan, index=X.index)
for yr in years:
    if yr < 2016:
        continue
    tr = X.index.year < yr
    te = X.index.year == yr
    if tr.sum() < 700:
        continue
    mu, sd, w = ridge_fit(X[tr].values, y[tr].values)
    pred = ridge_pred(X[te].values, mu, sd, w)
    vol_hat[te] = pred
    med_train[te] = np.median(ridge_pred(X[tr].values, mu, sd, w))

# diagnostics (report-only)
m = vol_hat.notna()
ic = np.corrcoef(vol_hat[m], y[m])[0, 1]
naive = np.corrcoef(X.loc[m, "rv5"], y[m])[0, 1]
print(f"OOS corr(vol_hat, |r|+1) = {ic:.3f}  (naive RV5 baseline = {naive:.3f})  n={m.sum()}")

vm = (VM_BASE * (med_train / vol_hat)).clip(LO, HI)
# shift(1): vm computed from info at t applies to day t+1 positions; vol_hat already
# targets t+1 from features at t -> applies at t+1 directly. Pre-2016: VM_BASE.
VM = vm.shift(1).reindex(book.index).fillna(VM_BASE)
VM.to_frame("vm").to_parquet(C.CACHE / "sim_VM.parquet")
print("VM stats:", VM.describe(percentiles=[.1, .5, .9]).round(2).to_dict())
