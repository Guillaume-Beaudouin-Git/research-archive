"""Step 2: dose-response curve. GROSS only (cost_rt=0)."""
import numpy as np, pandas as pd, statsmodels.api as sm

OUT = "<SCRATCH>"
SYMS = ["US500", "US100", "US30", "GER40", "XAUUSD"]
ABS_BINS = [0, 50, 100, 200, 500, np.inf]
ABS_LAB = ["<50", "50-100", "100-200", "200-500", ">=500"]
rng = np.random.default_rng(20260803)


def thac(x, lag=6):
    x = np.asarray(x, float)
    if len(x) < 15:
        return np.nan
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(m.tvalues[0])


def stat_boot(x, n=2000, mean_block=5):
    """Politis-Romano stationary bootstrap CI on the mean."""
    x = np.asarray(x, float); T = len(x)
    if T < 15:
        return (np.nan, np.nan)
    p = 1.0 / mean_block
    means = np.empty(n)
    for i in range(n):
        idx = np.empty(T, int); j = rng.integers(T)
        for t in range(T):
            idx[t] = j
            j = rng.integers(T) if rng.random() < p else (j + 1) % T
        means[i] = x[idx].mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def placebo_p95(side, r, n=400):
    """Circular-shift placebo: preserves the autocorrelation of `side`."""
    T = len(side)
    if T < 15:
        return np.nan
    out = np.empty(n)
    for i in range(n):
        out[i] = (np.roll(side, rng.integers(1, T)) * r).mean()
    return float(np.percentile(out, 95))


def cells(df, label_col, labels, sym, scheme):
    rows = []
    for lab in labels:
        s = df[df[label_col] == lab]
        if len(s) == 0:
            continue
        g = (np.sign(s["R_day"]) * s["r_win"]).values
        lo, hi = stat_boot(g)
        rows.append(dict(
            sym=sym, scheme=scheme, bin=lab, n=len(s),
            absR=float(s["R_day"].abs().mean()),
            gross=float(g.mean()), t_hac=thac(g), ci_lo=lo, ci_hi=hi,
            sigma=float(g.std(ddof=1)), mu_sig=float(g.mean() / g.std(ddof=1)),
            uncond=float(s["r_win"].mean()),          # L58 baseline, same bin, same trade form
            plac_p95=placebo_p95(np.sign(s["R_day"]).values, s["r_win"].values),
            n_up=int((s["R_day"] > 0).sum()), n_dn=int((s["R_day"] < 0).sum()),
            leg_up=float(s.loc[s["R_day"] > 0, "r_win"].mean()),
            leg_dn=float(-s.loc[s["R_day"] < 0, "r_win"].mean()),
            t_up=thac(s.loc[s["R_day"] > 0, "r_win"].values),
            t_dn=thac(-s.loc[s["R_day"] < 0, "r_win"].values),
            gross_early=float((np.sign(s["R_day"]) * s["r_win_early"]).mean()),
        ))
    return rows


all_rows, zr_rows = [], []
for sym in SYMS:
    df = pd.read_parquet(f"{OUT}/{sym}_daily.parquet")
    zr = pd.read_parquet(f"{OUT}/{sym}_zerorange.parquet")
    zr_rows.append(zr["zero_range_share"].rename(sym))
    a = df["R_day"].abs()
    df["qbin"] = pd.qcut(a, 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    df["abin"] = pd.cut(a, ABS_BINS, labels=ABS_LAB, right=False)
    all_rows += cells(df, "qbin", ["Q1", "Q2", "Q3", "Q4", "Q5"], sym, "quintile")
    all_rows += cells(df, "abin", ABS_LAB, sym, "absolute")

res = pd.DataFrame(all_rows)
res.to_csv(f"{OUT}/dose_results.csv", index=False)
pd.concat(zr_rows, axis=1).to_csv(f"{OUT}/zero_range.csv")

pd.set_option("display.width", 250, "display.max_rows", 300)
for scheme in ["quintile", "absolute"]:
    print(f"\n===== {scheme.upper()} =====")
    print(res[res.scheme == scheme][
        ["sym", "bin", "n", "absR", "gross", "t_hac", "ci_lo", "ci_hi",
         "mu_sig", "uncond", "plac_p95", "leg_up", "t_up", "leg_dn", "t_dn", "gross_early"]
    ].to_string(index=False, float_format=lambda v: f"{v:8.2f}"))
print("\n===== ZERO-RANGE SHARE IN TRADE WINDOW (L60) =====")
print(pd.concat(zr_rows, axis=1).to_string(float_format=lambda v: f"{v:6.3f}"))
