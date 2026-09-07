"""
Triangular cross-rate coherence — main grid (preregistered, 18 cells).
Signal at T-1, trade at T. HAC lag-6. Placebo = circular-shift of same pipeline.

Data: parquet cache (shared, read-only) with true-UTC M1 OHLC.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import warnings
warnings.filterwarnings("ignore")

CACHE = "<SCRATCH>"

def load(pair):
    df = pd.read_parquet(f"{CACHE}/{pair}_M1.parquet")
    return df["close"]

print("Loading M1 series...")
pairs_needed = ["EURUSD", "USDJPY", "EURJPY", "AUDUSD", "AUDJPY", "EURGBP", "GBPUSD"]
m1 = {p: load(p) for p in pairs_needed}
for p, s in m1.items():
    print(p, s.shape, s.index.min(), s.index.max())

# gap/flat-bar audit (L60): fraction of M1 bars with zero return (stale print)
print("\n--- L60 flat-bar audit (M1, close==prev close) ---")
for p, s in m1.items():
    zero_frac = (s.diff() == 0).mean()
    print(f"{p}: flat-bar frac = {zero_frac:.4f}")

TRIANGLES = {
    "EUR-USD-JPY": dict(cross="EURJPY", m1="EURUSD", m2="USDJPY", op="mul"),
    "AUD-USD-JPY": dict(cross="AUDJPY", m1="AUDUSD", m2="USDJPY", op="mul"),
    "EUR-GBP-USD": dict(cross="EURGBP", m1="EURUSD", m2="GBPUSD", op="div"),
}
FREQS = {"5min": "5min", "15min": "15min", "60min": "60min"}
LOOKBACKS = [20, 60]

def resample(s, freq):
    return s.resample(freq).last().dropna()

def hac_ols(y, x, lags=6):
    X = sm.add_constant(np.asarray(x))
    model = sm.OLS(np.asarray(y), X, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return model.params[1], model.tvalues[1], model.bse[1], int(model.nobs)

results = []
cell_data = {}  # store aligned (dev_z, fwd_ret) for placebo + validation

for tri_name, spec in TRIANGLES.items():
    cross_m1 = m1[spec["cross"]]
    a_m1 = m1[spec["m1"]]
    b_m1 = m1[spec["m2"]]
    for freq_label, freq in FREQS.items():
        cross = resample(cross_m1, freq)
        a = resample(a_m1, freq)
        b = resample(b_m1, freq)
        idx = cross.index.intersection(a.index).intersection(b.index)
        cross, a, b = cross.loc[idx], a.loc[idx], b.loc[idx]
        if spec["op"] == "mul":
            synth = a * b
        else:
            synth = a / b
        deviation = np.log(cross) - np.log(synth)
        fwd_ret = np.log(cross).diff().shift(-1)  # return from T-1(close) to T(close), aligned to signal at T-1
        for lb in LOOKBACKS:
            roll_mean = deviation.rolling(lb).mean()
            roll_std = deviation.rolling(lb).std()
            dev_z = (deviation - roll_mean) / roll_std
            # signal at T-1 predicts fwd_ret which is return realized AT T (already shifted -1 = "next bar's return")
            sig = dev_z  # T-1 value
            target = fwd_ret  # value at same index T-1 already represents return T-1->T
            df = pd.DataFrame({"sig": sig, "target": target}).dropna()
            if len(df) < 500:
                print(f"SKIP {tri_name} {freq_label} lb={lb}: n={len(df)}")
                continue
            coef, t, se, n = hac_ols(df["target"].values, df["sig"].values)
            cell = dict(triangle=tri_name, freq=freq_label, lookback=lb,
                        coef_bps=coef*1e4, t_hac=t, n=n)
            results.append(cell)
            cell_data[(tri_name, freq_label, lb)] = df
            print(f"{tri_name:14s} {freq_label:6s} lb={lb:3d}  n={n:7d}  coef={coef*1e4:+.4f}bps  t_HAC={t:+.3f}")

res_df = pd.DataFrame(results)
res_df.to_csv("grid_results.csv", index=False)
print("\n=== GRID SUMMARY ===")
print(res_df[["triangle","freq","lookback","n","coef_bps","t_hac"]].to_string(index=False))
print(f"\nN cells = {len(res_df)}")
print(f"max |t| observed = {res_df['t_hac'].abs().max():.3f}")
print(f"expected max|t| under H0 (sqrt(2*ln(N))) = {np.sqrt(2*np.log(len(res_df))):.3f}")
print(f"cells with |t|>2.0: {(res_df['t_hac'].abs()>2.0).sum()} / {len(res_df)}")
print(f"cells with |t|>2.5: {(res_df['t_hac'].abs()>2.5).sum()} / {len(res_df)}")

import pickle
with open("cell_data.pkl", "wb") as f:
    pickle.dump(cell_data, f)
print("\nSaved grid_results.csv and cell_data.pkl")
