"""
carry_ic.py — B/L37 IC gate. Carry/backwardation proxy WITHOUT term structure.

PROXY (stated honestly): with no nearby-vs-deferred and no spot for energy/ags on disk, the only
defensible carry measure is the REALIZED ROLL YIELD = trailing-63d [rolling-ETF return − front-month-
price return], annualised. A rolling ETF (USO/UNG/CPER) bleeds in contango and gains in backwardation
vs the front price → its out/under-performance IS the realized roll yield (carry state). LIMITATIONS:
(a) BACKWARD-looking (assumes carry persistence), not the live curve slope; (b) ETF-fee/tracking
confounded; (c) ETFs start 2015 (GLD 2018); (d) metals' physical ETFs (GLD/SLV) have ~no roll →
financing-contango only (wrong regime for the backwardation alpha). Causal: signal lagged 1d.
"""
from __future__ import annotations
import glob, os
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
import statsmodels.api as sm

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).parent
CACHE = HERE / "usoil_daily.parquet"

def yf(tkr):
    fs = sorted(glob.glob(str(ROOT / f"data/raw/yf_{tkr}_1d_*.parquet")), key=os.path.getmtime)
    if not fs:
        return None
    best = max(fs, key=lambda f: len(pd.read_parquet(f)))     # pick the longest-history file
    d = pd.read_parquet(best)
    col = [c for c in d.columns if c.lower() in ("close", "adj close", "adjclose")]
    s = (d[col[0]] if col else d.iloc[:, 0]).copy()
    s.index = pd.to_datetime(d.index)
    return s[~s.index.duplicated()].dropna().sort_index()

def usoil_daily():
    if CACHE.exists():
        return pd.read_parquet(CACHE)["close"]
    p = ROOT / "data/deep_history_utc/USOIL_M1.csv"
    df = pd.read_csv(p, usecols=["timestamp_utc", "close"], dtype={"close": "float32"})
    d = df["timestamp_utc"].str.slice(0, 10)
    daily = df.groupby(d)["close"].last()
    daily.index = pd.to_datetime(daily.index, format="%Y.%m.%d")
    daily = daily.rename("close").sort_index()
    daily.to_frame().to_parquet(CACHE)
    return daily

def hac_t(y, x, maxlags=25):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 100 or np.std(x) < 1e-12:
        return np.nan, len(x)
    X = sm.add_constant((x - x.mean()) / x.std())
    r = sm.OLS((y - y.mean()) / (y.std() + 1e-12), X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return float(r.tvalues[1]), len(x)


def main():
    # front-month price, rolling/physical ETF
    pairs = {
        "oil":    (usoil_daily(),      yf("USO"),  "rolling"),
        "natgas": (yf("NG=F"),          yf("UNG"),  "rolling"),
        "copper": (yf("HG=F"),          yf("CPER"), "rolling"),
        "silver": (yf("SI=F"),          yf("SLV"),  "physical(metal)"),
        "gold":   (yf("GC=F"),          yf("GLD"),  "physical(metal)"),
    }
    W = 63                                    # carry window (the one structural param)
    HZS = [1, 21]                             # forward target horizons
    rows, panel = [], {}
    for name, (front, etf, kind) in pairs.items():
        if front is None or etf is None:
            print(f"{name}: MISSING data"); continue
        al = pd.concat([np.log(front).rename("f"), np.log(etf).rename("e")], axis=1).dropna()
        carry = ((al.e - al.e.shift(W)) - (al.f - al.f.shift(W))) * (252.0 / W)   # ann. realized roll yield
        sig = carry.shift(1)                                                       # causal: known at T-1
        etf_lv = etf.reindex(al.index)
        for h in HZS:
            tgt = etf_lv.pct_change(h).shift(-h)
            df = pd.concat([sig.rename("s"), tgt.rename("y")], axis=1).dropna()
            if len(df) < 200:
                continue
            sp = spearmanr(df.s, df.y)[0]; pe = pearsonr(df.s, df.y)[0]
            t, n = hac_t(df.y.values, df.s.values, maxlags=max(25, h + 5))
            per_yr = df.groupby(df.index.year).apply(
                lambda g: np.sign(pearsonr(g.s, g.y)[0]) if len(g) > 30 and g.s.std() > 0 else np.nan)
            yp, yn = int((per_yr > 0).sum()), int((per_yr < 0).sum())
            rows.append(dict(commodity=name, kind=kind, horizon=h, N=n,
                             spearman=round(float(sp), 4), pearson=round(float(pe), 4),
                             HAC_t=round(float(t), 2), yrs_pos=yp, yrs_neg=yn))
            if h == 21:
                panel[name] = df.assign(commodity=name)
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))

    # pooled cross-sectional / panel IC (rolling-ETF energy+industrials = where carry varies)
    print("\n=== POOLED panel IC (h=21, all 5) and ENERGY/INDUSTRIAL-only (oil+natgas+copper) ===")
    for label, keys in [("ALL5", list(panel)), ("ROLLING3", [k for k in panel if pairs[k][2] == "rolling"])]:
        if not all(k in panel for k in keys):
            continue
        big = pd.concat([panel[k] for k in keys])
        sp = spearmanr(big.s, big.y)[0]; pe = pearsonr(big.s, big.y)[0]
        t, n = hac_t(big.y.values, big.s.values, maxlags=30)
        # 2020 tail split (L31)
        b20 = big[big.index.year == 2020]; bex = big[big.index.year != 2020]
        pe20 = pearsonr(b20.s, b20.y)[0] if len(b20) > 50 else np.nan
        peex = pearsonr(bex.s, bex.y)[0] if len(bex) > 50 else np.nan
        print(f"  {label:9s} N={n} Spearman={sp:+.4f} Pearson={pe:+.4f} HAC_t={t:+.2f} | "
              f"2020 Pearson={pe20:+.4f} ex-2020 Pearson={peex:+.4f}")

    res.to_json(HERE / "carry_ic_results.json", orient="records", indent=2)
    n_variants = len(rows) + 2
    best = res.iloc[res["HAC_t"].abs().idxmax()]
    print(f"\nvariants tried = {n_variants} (per-inst×horizon + 2 pooled) | strongest |HAC t| = "
          f"{best['commodity']}.{best['horizon']}d t={best['HAC_t']} (kind={best['kind']})")
    print(f"GATE needs |HAC t|>2.5 deflated for {n_variants} variants (~|t|>3.0 Bonferroni) AND survive 2020 tail.")
    print("DONE")


if __name__ == "__main__":
    main()
