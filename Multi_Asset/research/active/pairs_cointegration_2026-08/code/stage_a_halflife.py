"""
Stage A — descriptive half-life survey over all C(19,2)=171 pairs.

DESCRIPTIVE (N0). Consumes no test. Reports every pair, no top-k selection.

Method, per pair, per non-overlapping formation window:
  1. inner-join M5 closes of the two legs (true-UTC bars)
  2. log prices; OLS  logA = a + b*logB + e   (b = static hedge ratio)
  3. OU on the residual, using ONLY within-session transitions
     (a transition is dropped when the timestamp gap != 5 min: overnight
     breaks, weekends and holidays are NOT mean-reversion observations)
         de_t = alpha + beta * e_{t-1} + eps ,  kappa = -beta ,  HL = ln2/kappa
  4. ADF on the residual (cointegration hold rate)
  5. sigma(residual) in bps -> amplitude for the K2 cost pre-flight

Also: HL at M5/M15/M30/H1 for the pre-registered Stage-B pairs. Microstructure
noise (bid-ask bounce) manufactures spurious fast mean reversion; if HL in TIME
units is stable across sampling frequencies the dynamics are real, if HL in BARS
is stable instead the "reversion" is noise.
"""
import os
import itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

M5 = "<SCRATCH>"
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/outputs"
os.makedirs(OUT, exist_ok=True)

UNIV = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
        "EURGBP", "EURJPY", "AUDJPY", "US500", "US100", "US30", "GER40",
        "XAUUSD", "XAGUSD", "COPPER", "UKOIL", "USOIL"]

STAGE_B = [
    ("UKOIL", "USOIL", "G1"),
    ("XAUUSD", "XAGUSD", "G2"),
    ("US500", "US100", "G3"), ("US500", "US30", "G3"), ("US100", "US30", "G3"),
    ("US500", "GER40", "G4"), ("US100", "GER40", "G4"), ("US30", "GER40", "G4"),
    ("EURUSD", "GBPUSD", "G5"), ("EURUSD", "EURGBP", "G5"), ("GBPUSD", "EURGBP", "G5"),
    ("USDJPY", "EURJPY", "G6"), ("USDJPY", "AUDJPY", "G6"), ("EURJPY", "AUDJPY", "G6"),
    ("AUDUSD", "NZDUSD", "G7"), ("AUDUSD", "USDCAD", "G7"),
    ("EURUSD", "EURJPY", "G8"), ("EURUSD", "USDCHF", "G8"),
]

START, END = "2014-01-01", "2026-06-05"
WIN_DAYS = 30          # formation window length (calendar days)
MIN_BARS = 1500        # minimum aligned bars in a window to use it


def load_panel(freq="5min"):
    cols = {}
    for s in UNIV:
        df = _read(s, ["close"]).loc[START:END]
        if freq != "5min":
            df = df.resample(freq).last().dropna()
        cols[s] = df["close"]
    return pd.DataFrame(cols)


def _read(sym, cols=None):
    """Schema-tolerant read. Two writers produced this cache with different
    names for the same deterministic content; every file was verified
    bit-exact against the raw M1 source before use."""
    import pyarrow.parquet as pq
    names = set(pq.read_schema(f"{M5}/{sym}_M5.parquet").names)
    ren = {}
    if "n_bars" in names:
        ren = {"n_bars": "n_m1", "n_zero_range": "zr_m1"}
    want = None
    if cols:
        inv = {v: k for k, v in ren.items()}
        want = [inv.get(c, c) for c in cols]
    df = pd.read_parquet(f"{M5}/{sym}_M5.parquet", columns=want)
    return df.rename(columns=ren)


def zero_range_report():
    """L60: fraction of zero-range M1 bars, per series per year."""
    rows = []
    for s in UNIV:
        df = _read(s, ["n_m1", "zr_m1", "high", "low"]).loc[START:END]
        for yr, sub in df.groupby(df.index.year):
            n = sub["n_m1"].sum()
            rows.append({"sym": s, "year": int(yr),
                         "zr_m1_frac": float(sub["zr_m1"].sum() / n) if n else np.nan,
                         "zr_m5_frac": float((sub["high"] == sub["low"]).mean())})
    return pd.DataFrame(rows)


def ou_halflife(resid: pd.Series, step_min: int):
    """OU half-life in MINUTES from within-session transitions only."""
    e = resid.values
    t = resid.index.values
    dt = (t[1:] - t[:-1]).astype("timedelta64[m]").astype(float)
    ok = dt == step_min
    if ok.sum() < 200:
        return np.nan, np.nan, int(ok.sum())
    x = e[:-1][ok]
    y = (e[1:] - e[:-1])[ok]
    xm, ym = x.mean(), y.mean()
    vx = ((x - xm) ** 2).sum()
    if vx <= 0:
        return np.nan, np.nan, int(ok.sum())
    beta = ((x - xm) * (y - ym)).sum() / vx
    kappa = -beta                      # per bar
    if kappa <= 0:
        return np.inf, kappa, int(ok.sum())
    return float(np.log(2) / kappa * step_min), float(kappa), int(ok.sum())


def survey_pair(a: pd.Series, b: pd.Series, step_min: int, do_adf=True):
    df = pd.concat([a.rename("A"), b.rename("B")], axis=1).dropna()
    if len(df) < MIN_BARS:
        return None
    la, lb = np.log(df["A"]), np.log(df["B"])
    out = []
    for _, w in df.groupby(pd.Grouper(freq=f"{WIN_DAYS}D")):
        if len(w) < MIN_BARS:
            continue
        i = w.index
        x, y = lb.loc[i].values, la.loc[i].values
        xm, ym = x.mean(), y.mean()
        vx = ((x - xm) ** 2).sum()
        if vx <= 0:
            continue
        beta = ((x - xm) * (y - ym)).sum() / vx
        resid = pd.Series(y - (ym - beta * xm) - beta * x, index=i)
        hl, kap, n = ou_halflife(resid, step_min)
        rec = {"t0": i[0], "n": n, "beta": float(beta),
               "hl_min": hl, "sigma_bps": float(resid.std() * 1e4)}
        if do_adf:
            try:
                rec["adf_p"] = float(adfuller(resid.values[::3], maxlag=12,
                                              autolag=None, regression="c")[1])
            except Exception:
                rec["adf_p"] = np.nan
        out.append(rec)
    if not out:
        return None
    w = pd.DataFrame(out)
    hl = w["hl_min"].replace(np.inf, np.nan)
    return {
        "n_windows": len(w),
        "hl_med_min": float(hl.median()),
        "hl_q25_min": float(hl.quantile(.25)),
        "hl_q75_min": float(hl.quantile(.75)),
        "hl_nonrev_frac": float(w["hl_min"].isin([np.inf]).mean() + hl.isna().mean()),
        "sigma_bps_med": float(w["sigma_bps"].median()),
        "beta_med": float(w["beta"].median()),
        "beta_iqr": float(w["beta"].quantile(.75) - w["beta"].quantile(.25)),
        "adf_hold_frac": float((w["adf_p"] < 0.05).mean()) if do_adf else np.nan,
        "kappa_stab": float(hl.quantile(.75) / hl.quantile(.25)) if hl.quantile(.25) > 0 else np.nan,
    }


if __name__ == "__main__":
    print("zero-range (L60) ...", flush=True)
    zr = zero_range_report()
    zr.to_csv(f"{OUT}/l60_zero_range.csv", index=False)
    bad = zr[zr["zr_m1_frac"] > 0.20]
    print(f"  series-years with >20% zero-range M1 bars: {len(bad)} / {len(zr)}")
    if len(bad):
        print(bad.to_string(index=False))

    print("\nloading M5 panel ...", flush=True)
    p5 = load_panel("5min")
    print(f"  panel {p5.shape}  {p5.index[0]} -> {p5.index[-1]}", flush=True)

    print("\nStage A: 171 pairs @ M5 ...", flush=True)
    rows = []
    for i, (x, y) in enumerate(itertools.combinations(UNIV, 2)):
        r = survey_pair(p5[x], p5[y], 5)
        if r is None:
            continue
        r.update({"A": x, "B": y})
        rows.append(r)
        if (i + 1) % 30 == 0:
            print(f"  {i+1}/171", flush=True)
    surv = pd.DataFrame(rows)
    grp = {(a, b): g for a, b, g in STAGE_B}
    surv["group"] = [grp.get((a, b), grp.get((b, a), "")) for a, b in zip(surv.A, surv.B)]
    surv = surv.sort_values("hl_med_min")
    surv.to_csv(f"{OUT}/stage_a_halflife_171.csv", index=False)
    print(f"\nwrote {OUT}/stage_a_halflife_171.csv  ({len(surv)} pairs)")

    print("\n--- 20 shortest half-lives (M5) ---")
    print(surv.head(20)[["A", "B", "group", "hl_med_min", "sigma_bps_med",
                         "adf_hold_frac", "n_windows"]].to_string(index=False))
    print("\n--- Stage-B pre-registered pairs ---")
    print(surv[surv.group != ""][["A", "B", "group", "hl_med_min", "hl_q25_min",
                                  "hl_q75_min", "sigma_bps_med", "beta_med",
                                  "beta_iqr", "adf_hold_frac"]].to_string(index=False))

    print("\nFrequency-stability check (noise falsification) ...", flush=True)
    freqs = [("5min", 5), ("15min", 15), ("30min", 30), ("60min", 60)]
    panels = {f: (p5 if f == "5min" else p5.resample(f).last().dropna(how="all"))
              for f, _ in freqs}
    fr = []
    for a, b, g in STAGE_B:
        rec = {"A": a, "B": b, "group": g}
        for f, sm in freqs:
            r = survey_pair(panels[f][a], panels[f][b], sm, do_adf=False)
            rec[f"hl_{f}"] = r["hl_med_min"] if r else np.nan
        fr.append(rec)
    freq_df = pd.DataFrame(fr)
    freq_df.to_csv(f"{OUT}/stage_a_freq_stability.csv", index=False)
    print(freq_df.to_string(index=False))
