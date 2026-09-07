"""
Diagnostics on the strong 18/18 grid result — is this a real signal or a
non-synchronous-trading (stale-print) artifact of resampling three
independently-quoted instruments?

Tests:
(A) Flat-bar fraction at RESAMPLED frequency per leg (does the "last close"
    often just repeat a stale print?).
(B) Gap test: does predictability survive skipping one full bar
    (predict T+1->T+2 from deviation at T-1)? Real info decays gradually;
    stale-print artifacts should collapse almost to zero after one re-sync.
(C) Decomposition: does deviation_z(T-1) predict the OTHER two legs'
    forward returns too, or only the cross leg?
(D) TWAP construction: rebuild deviation using the bin MEAN of M1 closes
    instead of the last print, and re-run HAC OLS on best/worst cells.
"""
import numpy as np
import pandas as pd
import warnings
from fasthac import fast_hac_ols
warnings.filterwarnings("ignore")

CACHE = "<SCRATCH>"

def load(pair):
    return pd.read_parquet(f"{CACHE}/{pair}_M1.parquet")["close"]

pairs_needed = ["EURUSD", "USDJPY", "EURJPY", "AUDUSD", "AUDJPY", "EURGBP", "GBPUSD"]
m1 = {p: load(p) for p in pairs_needed}

TRIANGLES = {
    "EUR-USD-JPY": dict(cross="EURJPY", m1="EURUSD", m2="USDJPY", op="mul"),
    "AUD-USD-JPY": dict(cross="AUDJPY", m1="AUDUSD", m2="USDJPY", op="mul"),
    "EUR-GBP-USD": dict(cross="EURGBP", m1="EURUSD", m2="GBPUSD", op="div"),
}
FREQS = {"5min": "5min", "15min": "15min", "60min": "60min"}

def resample_last(s, freq):
    return s.resample(freq).last().dropna()

def resample_mean(s, freq):
    return s.resample(freq).mean().dropna()

print("=== (A) Flat-bar fraction at RESAMPLED frequency (last print repeats prev bar) ===")
for p in pairs_needed:
    row = [p]
    for freq_label, freq in FREQS.items():
        r = resample_last(m1[p], freq)
        flat = (r.diff() == 0).mean()
        row.append(f"{freq_label}={flat:.4f}")
    print(" ".join(row))

def hac_ols(y, x, lags=6):
    mask = ~(np.isnan(y) | np.isnan(x))
    b, t, se, n = fast_hac_ols(y[mask], x[mask], lags=lags)
    return b, t, n

print("\n=== (B) Gap test + (C) decomposition + (D) TWAP, per triangle at 15min lb=20 ===")
LB = 20
FREQ_LABEL, FREQ = "15min", "15min"

for tri_name, spec in TRIANGLES.items():
    cross_m1, a_m1, b_m1 = m1[spec["cross"]], m1[spec["m1"]], m1[spec["m2"]]

    for construction in ["last", "mean"]:
        rs = resample_last if construction == "last" else resample_mean
        cross = rs(cross_m1, FREQ); a = rs(a_m1, FREQ); b = rs(b_m1, FREQ)
        idx = cross.index.intersection(a.index).intersection(b.index)
        cross, a, b = cross.loc[idx], a.loc[idx], b.loc[idx]
        synth = a * b if spec["op"] == "mul" else a / b
        deviation = np.log(cross) - np.log(synth)
        dev_z = (deviation - deviation.rolling(LB).mean()) / deviation.rolling(LB).std()

        log_cross, log_a, log_b = np.log(cross), np.log(a), np.log(b)
        fwd_cross = log_cross.diff().shift(-1)
        fwd_a = log_a.diff().shift(-1)
        fwd_b = log_b.diff().shift(-1)
        # gap test: skip one bar -> predict the NEXT-NEXT bar's return
        fwd_cross_gap = log_cross.diff().shift(-2) - log_cross.diff().shift(-1)  # return from T to T+1 (one bar later, one bar skipped)
        # more precisely: return realized between T and T+1, using signal at T-1 (skipping T-1->T)
        fwd_cross_gap = (log_cross.shift(-2) - log_cross.shift(-1))

        for label, target in [("fwd_cross (T-1->T)", fwd_cross),
                               ("fwd_cross GAP (T->T+1, skip 1 bar)", fwd_cross_gap),
                               ("fwd_major1", fwd_a),
                               ("fwd_major2", fwd_b)]:
            df = pd.DataFrame({"sig": dev_z, "target": target}).dropna()
            if len(df) < 500:
                continue
            coef, t, n = hac_ols(df["target"].values, df["sig"].values)
            print(f"{tri_name:14s} constr={construction:4s} {label:35s} n={n:7d} coef={coef*1e4:+8.4f}bps t_HAC={t:+8.3f}")
    print()
