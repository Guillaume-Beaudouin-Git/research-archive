"""Step 3: formal dose-slope test + L54 mean-vs-variance decomposition."""
import numpy as np, pandas as pd, statsmodels.api as sm

OUT = "<SCRATCH>"
SYMS = ["US500", "US100", "US30", "GER40", "XAUUSD"]

rows = []
for sym in SYMS:
    df = pd.read_parquet(f"{OUT}/{sym}_daily.parquet")
    a = df["R_day"].abs().values
    g = (np.sign(df["R_day"]) * df["r_win"]).values
    # dose slope: gross_i = alpha + beta * |R_day|_i   (beta in bps of gross per bp of dose)
    X = sm.add_constant(a)
    m = sm.OLS(g, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    # L54: does dose predict the MEAN or only the VARIANCE?
    mv = sm.OLS(np.abs(g), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    rows.append(dict(
        sym=sym, n=len(df),
        slope_mean=m.params[1] * 100, t_slope=m.tvalues[1],      # per +100bp of dose
        slope_absg=mv.params[1] * 100, t_absg=mv.tvalues[1],
        r2_mean=m.rsquared, r2_absg=mv.rsquared,
    ))

t = pd.DataFrame(rows)
print("=== DOSE SLOPE: gross ~ a + b*|R_day|  (b rescaled per +100 bps of dose) ===")
print(t.to_string(index=False, float_format=lambda v: f"{v:9.4f}"))

print("\n=== SIGMA BY BIN (L54: dose drives variance, not mean) ===")
r = pd.read_csv(f"{OUT}/dose_results.csv")
q = r[r.scheme == "quintile"].pivot(index="bin", columns="sym", values="sigma")
mu = r[r.scheme == "quintile"].pivot(index="bin", columns="sym", values="gross")
ms = r[r.scheme == "quintile"].pivot(index="bin", columns="sym", values="mu_sig")
print("sigma (bps):"); print(q.to_string(float_format=lambda v: f"{v:7.2f}"))
print("\nmu (bps):");   print(mu.to_string(float_format=lambda v: f"{v:7.2f}"))
print("\nmu/sigma:");   print(ms.to_string(float_format=lambda v: f"{v:7.3f}"))
print("\nsigma Q5/Q1 ratio:", (q.loc["Q5"] / q.loc["Q1"]).round(2).to_dict())
