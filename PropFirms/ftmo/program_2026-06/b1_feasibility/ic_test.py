"""
ic_test.py — B1 IC gate. Causal IC of FINRA short-volume (J+1) vs NQ overnight (close->open) return.

Causality: FINRA session-date e short ratio is a FULL-DAY total, finalised after close_e (published
evening/next-morning). The earliest close at which it is known is close_{e+1}. So it can only predict an
overnight that starts at or after close_{e+1} -> target = ov_bps into session e+2. Hence predictor[d] =
signal[d-2 sessions] (lag>=2 is the minimum causal lag; lag1 would be look-ahead and is NOT used).
ov_bps[d] = overnight gap close_{d-1} -> open_d (the swap-free NQ-futures axis). Two-sided (report sign).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
import statsmodels.api as sm

HERE = Path(__file__).parent
ROOT = Path("<HOME>/Desktop/Algo_claude")
NDX = ["AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","TSLA","AVGO","COST","NFLX","ADBE","AMD",
       "PEP","CSCO","TMUS","INTC","CMCSA","TXN","QCOM","AMAT","INTU","HON","AMGN","ISRG","BKNG","MU",
       "ADI","LRCX","REGN","VRTX","PANW","KLAC","SNPS","CDNS","MRVL","ORLY","CRWD","ABNB","FTNT",
       "ADP","MELI","CTAS","PYPL","MDLZ","PDD","MAR","CEG","ROP","NXPI"]


def hac_t(y, x, maxlags=5):
    """HAC (Newey-West) t-stat of slope in y ~ x (both finite, aligned)."""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 60 or x.std() < 1e-12:
        return np.nan, np.nan, len(x)
    X = sm.add_constant((x - x.mean()) / x.std())
    res = sm.OLS((y - y.mean()) / y.std(), X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return float(res.params[1]), float(res.tvalues[1]), len(x)


def main():
    sv = pd.read_parquet(HERE / "finra_shortvol_universe.parquet")
    sv["date"] = pd.to_datetime(sv["date"])
    piv_s = sv.pivot_table(index="date", columns="symbol", values="short_vol", aggfunc="sum")
    piv_t = sv.pivot_table(index="date", columns="symbol", values="total_vol", aggfunc="sum")

    # signals (short-volume RATIO), causal by construction (ratio of the session's own volumes)
    sig = {}
    sig["QQQ_sr"] = (piv_s["QQQ"] / piv_t["QQQ"]).rename("QQQ_sr")                  # zero-survivorship
    ndx_in = [c for c in NDX if c in piv_s.columns]
    sig["NDXagg_sr"] = (piv_s[ndx_in].sum(1) / piv_t[ndx_in].sum(1)).rename("NDXagg_sr")  # survivorship-flagged
    # leveraged/inverse ETF short ratios as a directional-flow proxy (zero-survivorship)
    if "SQQQ" in piv_s.columns and "TQQQ" in piv_s.columns:
        sig["TQQQ_sr"] = (piv_s["TQQQ"] / piv_t["TQQQ"]).rename("TQQQ_sr")
        sig["SQQQ_sr"] = (piv_s["SQQQ"] / piv_t["SQQQ"]).rename("SQQQ_sr")

    # NQ overnight target
    nq = pd.read_parquet(ROOT / "data/overnight_research/nq_rth_daily.parquet")
    ov = nq["ov_bps"].copy(); ov.index = pd.to_datetime(ov.index)

    # common trading calendar (NQ overnight dates that also have a signal history)
    print(f"signal dates {piv_s.index.min().date()}..{piv_s.index.max().date()} ({len(piv_s)}) | "
          f"NQ ov dates {ov.index.min().date()}..{ov.index.max().date()} ({len(ov)})\n")

    results = []
    LAGS = [2, 3]            # lag2 = minimum causal; lag3 = robustness. (lag1 = look-ahead, excluded)
    for name, s in sig.items():
        s = s.reindex(ov.index)                      # align to NQ overnight calendar
        for kind, base in [("level", s), ("chg", s.diff())]:
            for lag in LAGS:
                pred = base.shift(lag)               # predictor known >= lag sessions before the overnight
                df = pd.concat([pred.rename("p"), ov.rename("y")], axis=1).dropna()
                if len(df) < 200:
                    continue
                sp_ic, sp_p = spearmanr(df.p, df.y)
                pe_ic, _ = pearsonr(df.p, df.y)
                slope, t, n = hac_t(df.y.values, df.p.values)
                per_yr = df.groupby(df.index.year).apply(
                    lambda g: round(pearsonr(g.p, g.y)[0], 3) if len(g) > 20 and g.p.std() > 0 else np.nan)
                yrs_pos = int((per_yr > 0).sum()); yrs_neg = int((per_yr < 0).sum())
                n_per_yr = int(df.groupby(df.index.year).size().median())
                results.append(dict(signal=f"{name}.{kind}", lag=lag, N=n, N_per_yr=n_per_yr,
                                    spearman_IC=round(float(sp_ic), 4), pearson_IC=round(float(pe_ic), 4),
                                    HAC_t=round(float(t), 2), yrs_pos=yrs_pos, yrs_neg=yrs_neg,
                                    per_yr=per_yr.dropna().to_dict()))
    res = pd.DataFrame(results).sort_values("HAC_t", key=lambda c: c.abs(), ascending=False).reset_index(drop=True)
    cols = ["signal", "lag", "N", "N_per_yr", "spearman_IC", "pearson_IC", "HAC_t", "yrs_pos", "yrs_neg"]
    print(res[cols].to_string(index=False))
    res.to_json(HERE / "ic_results.json", orient="records", indent=2)

    # GATE: |HAC t| > 2.5 AND N_per_yr >= 50 AND sign-stable (>=70% years same sign), causal lag>=2
    res["passes"] = (res["HAC_t"].abs() > 2.5) & (res["N_per_yr"] >= 50) & \
                    (res[["yrs_pos", "yrs_neg"]].max(1) / (res.yrs_pos + res.yrs_neg) >= 0.70)
    winners = res[res["passes"]]
    print(f"\nGATE (|HACt|>2.5 & N/yr>=50 & >=70% sign-stable, causal lag>=2): "
          f"{'PASS — ' + str(winners['signal'].tolist()) if len(winners) else 'FAIL (no causal signal clears)'}")
    best = res.iloc[0]
    print(f"strongest causal signal: {best['signal']} lag{best['lag']} | HAC t={best['HAC_t']} "
          f"Spearman IC={best['spearman_IC']} N/yr={best['N_per_yr']} yrs +/-={best['yrs_pos']}/{best['yrs_neg']}")
    print("DONE")


if __name__ == "__main__":
    main()
