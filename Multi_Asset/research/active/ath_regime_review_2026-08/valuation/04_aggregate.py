"""Index-level aggregation: coverage, cap-weighted vs median multiples,
concentration, earnings yield vs 10y rates.

METHOD NOTES (these are choices, and they change the numbers)

1. Dual-class de-duplication. Yahoo's `marketCap` is the WHOLE-COMPANY cap
   for every listed class, while `sharesOutstanding` is per-listed-class.
   Verified: cap_calc/marketCap == 1.000 for 118/142 tickers; the 24
   exceptions are exactly the known multi-class names (GOOG/GOOGL,
   MRK.DE, HEN3.DE, VOW3.DE, PAH3.DE, META, ...). Summing `marketCap`
   over both Alphabet lines would book Alphabet twice, so GOOG is dropped
   and GOOGL kept as the single Alphabet line.

2. Aggregate ("cap-weighted") ratios are computed as
        aggregate P/X  =  sum(cap_i) / sum(X_i)
   NOT as sum(w_i * (P/X)_i). The second is an arithmetic mean of ratios;
   it is dominated by whichever constituent has the smallest denominator
   and is not a portfolio-level multiple. The first is what "the index
   trades at" means.

3. Per-name earnings are rebuilt as
        E_i = (trailingEps_i / price_i) * marketCap_i
   rather than marketCap_i / trailingPE_i. Identical when trailingPE > 0,
   but it also carries LOSS-MAKING names (trailingPE is NaN for them,
   which would silently drop their negative earnings and flatter the
   index earnings yield).

4. Weights are FULL-COMPANY market cap. The published index weights are
   float-adjusted and capped (NDX caps the largest name at 24%; DAX at
   15%). So the concentration numbers here are the raw economic cap
   share, which is an UPPER bound on the official index weight for the
   very largest names.

Outputs: constituents_{NDX,DAX}.csv (deliverable), coverage.csv,
         aggregates.json
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

# Fields whose coverage we report constituent-by-constituent.
REPORT_FIELDS = {
    "marketCap": "Market cap",
    "trailingPE": "P/E trailing",
    "forwardPE": "P/E forward (analyst consensus)",
    "priceToSalesTrailing12Months": "P/S trailing",
    "enterpriseToEbitda": "EV/EBITDA",
    "priceToBook": "Price/Book",
    "profitMargins": "Net margin",
    "revenueGrowth": "Revenue growth (Yahoo, YoY qtr)",
    "earningsGrowth": "Earnings growth (Yahoo, YoY qtr)",
    "rev_cagr_stmt": "Revenue CAGR (annual stmt, computed)",
    "eps_cagr_stmt": "Diluted-EPS CAGR (annual stmt, computed)",
    "netdebt_ebitda": "Net debt / EBITDA",
}

DROP_DUP = {"GOOG"}  # Alphabet second listing; GOOGL retained


def build(idx: str) -> pd.DataFrame:
    d = pd.read_csv(CACHE / "fundamentals_raw.csv")
    d = d[d["index"] == idx].copy()
    d = d[~d.ticker.isin(DROP_DUP)]

    meta_f = CACHE / ("constituents_ndx.csv" if idx == "NDX" else "constituents_dax.csv")
    meta = pd.read_csv(meta_f)
    d = d.merge(meta, on="ticker", how="left", suffixes=("", "_meta"))

    d["price"] = d.currentPrice.fillna(d.regularMarketPrice).fillna(d.previousClose)
    cap = d["marketCap"]

    # --- rebuilt fundamentals in quote currency ---
    d["earnings_ttm"] = d.trailingEps / d.price * cap
    d["earnings_fwd"] = d.forwardEps / d.price * cap
    d["sales_ttm"] = cap / d.priceToSalesTrailing12Months
    d["book_value"] = cap / d.priceToBook
    d["ebitda_use"] = d.ebitda.fillna(d.ebitda_stmt)
    d["ev_use"] = d.enterpriseValue
    d["net_debt"] = d.totalDebt.fillna(d.total_debt_bs) - d.totalCash.fillna(d.cash_bs)
    d["netdebt_ebitda"] = np.where(d.ebitda_use > 0, d.net_debt / d.ebitda_use, np.nan)
    d["earnings_yield_pct"] = d.trailingEps / d.price * 100
    d["weight_pct"] = cap / cap.sum() * 100
    return d.sort_values("marketCap", ascending=False).reset_index(drop=True)


def coverage(d: pd.DataFrame) -> pd.DataFrame:
    n = len(d)
    rows = []
    for f, label in REPORT_FIELDS.items():
        ok = d[f].notna() & np.isfinite(d[f].astype(float))
        cap_cov = d.loc[ok, "marketCap"].sum() / d["marketCap"].sum() * 100
        rows.append({"field": f, "label": label, "n_available": int(ok.sum()),
                     "n_total": n, "pct_names": ok.sum() / n * 100,
                     "pct_of_index_cap": cap_cov})
    return pd.DataFrame(rows)


def agg_ratio(d: pd.DataFrame, num: str, den: str, positive_only: bool = False) -> dict:
    cols = list(dict.fromkeys([num, den, "marketCap"]))  # num may BE marketCap
    x = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if positive_only:
        x = x[x[den] > 0]
    if x.empty:
        return {"aggregate": np.nan, "n": 0, "cap_cov_pct": 0.0}
    return {"aggregate": float(x[num].sum() / x[den].sum()),
            "n": int(len(x)),
            "cap_cov_pct": float(x.marketCap.sum() / d.marketCap.sum() * 100)}


def dist(d: pd.DataFrame, col: str, clip_neg: bool = False) -> dict:
    s = d[col].replace([np.inf, -np.inf], np.nan).dropna()
    if clip_neg:
        s = s[s > 0]
    if s.empty:
        return {"n": 0}
    w = d.loc[s.index, "marketCap"]
    return {"n": int(len(s)),
            "cap_cov_pct": float(w.sum() / d.marketCap.sum() * 100),
            "median": float(s.median()),
            "mean_equal_weight": float(s.mean()),
            "mean_cap_weighted": float((s * w).sum() / w.sum()),
            "p25": float(s.quantile(.25)), "p75": float(s.quantile(.75)),
            "min": float(s.min()), "max": float(s.max())}


def concentration(d: pd.DataFrame) -> dict:
    w = (d.marketCap / d.marketCap.sum()).sort_values(ascending=False)
    return {
        "n_constituents": int(len(w)),
        "top1_pct": float(w.iloc[0] * 100),
        "top5_pct": float(w.head(5).sum() * 100),
        "top10_pct": float(w.head(10).sum() * 100),
        "top20_pct": float(w.head(20).sum() * 100),
        "herfindahl": float((w ** 2).sum()),
        "hhi_effective_n": float(1.0 / (w ** 2).sum()),
        "top10_names": list(d.head(10).ticker),
        "top10_weights_pct": [round(float(x) * 100, 2) for x in w.head(10)],
        "total_cap": float(d.marketCap.sum()),
        "currency": d.currency.mode().iloc[0] if len(d.currency.mode()) else "?",
    }


def rates() -> dict:
    ust = pd.read_csv(CACHE / "ust_daily_treasury_yield_curve.csv")
    ustr = pd.read_csv(CACHE / "ust_daily_treasury_real_yield_curve.csv")
    ecb = pd.read_csv(CACHE / "ecb_ea_aaa_10y.csv")
    ecb = ecb[["TIME_PERIOD", "OBS_VALUE"]].dropna().sort_values("TIME_PERIOD")
    de = pd.read_csv(CACHE / "ecb_de_ltir.csv")
    de = de[["TIME_PERIOD", "OBS_VALUE"]].dropna().sort_values("TIME_PERIOD")
    return {
        "us10y_nominal_pct": float(ust.iloc[0]["10 Yr"]),
        "us10y_nominal_date": str(ust.iloc[0]["Date"]),
        "us10y_real_tips_pct": float(ustr.iloc[0]["10 YR"]),
        "us10y_real_date": str(ustr.iloc[0]["Date"]),
        "us10y_breakeven_pct": float(ust.iloc[0]["10 Yr"]) - float(ustr.iloc[0]["10 YR"]),
        "ea_aaa_10y_pct": float(ecb.iloc[-1].OBS_VALUE),
        "ea_aaa_10y_date": str(ecb.iloc[-1].TIME_PERIOD),
        "de10y_convergence_pct": float(de.iloc[-1].OBS_VALUE),
        "de10y_convergence_date": str(de.iloc[-1].TIME_PERIOD),
        "sources": {
            "us": "US Treasury daily par yield curve (home.treasury.gov), nominal + TIPS real",
            "ea": "ECB Data Portal YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y (euro-area AAA 10y spot)",
            "de": "ECB Data Portal IRS.M.DE.L.L40.CI.0000.EUR.N.Z (German 10y convergence rate, MONTHLY)",
        },
    }


if __name__ == "__main__":
    r = rates()
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "rates": r}

    for idx in ["NDX", "DAX"]:
        d = build(idx)
        cov = coverage(d)
        cov.insert(0, "index", idx)
        cov.to_csv(CACHE / f"coverage_{idx}.csv", index=False)

        keep = ["ticker", "shortName", "company", "sector", "currency", "price",
                "marketCap", "weight_pct", "trailingPE", "forwardPE",
                "priceToSalesTrailing12Months", "enterpriseToEbitda", "priceToBook",
                "profitMargins", "revenueGrowth", "earningsGrowth",
                "rev_cagr_stmt", "rev_cagr_nyears", "eps_cagr_stmt", "eps_cagr_nyears",
                "netdebt_ebitda", "earnings_yield_pct", "trailingEps", "forwardEps",
                "numberOfAnalystOpinions", "fetched_utc"]
        d.reindex(columns=keep).to_csv(HERE / f"constituents_{idx}.csv", index=False)

        agg = {
            "pe_trailing": agg_ratio(d, "marketCap", "earnings_ttm"),
            "pe_forward": agg_ratio(d, "marketCap", "earnings_fwd"),
            "ps_trailing": agg_ratio(d, "marketCap", "sales_ttm"),
            "pb": agg_ratio(d, "marketCap", "book_value"),
            "ev_ebitda": agg_ratio(d, "ev_use", "ebitda_use", positive_only=True),
            "netdebt_ebitda": agg_ratio(d, "net_debt", "ebitda_use", positive_only=True),
        }
        ey_agg = 1.0 / agg["pe_trailing"]["aggregate"] * 100
        ey_fwd = 1.0 / agg["pe_forward"]["aggregate"] * 100
        rate_nom = r["us10y_nominal_pct"] if idx == "NDX" else r["ea_aaa_10y_pct"]
        rate_real = r["us10y_real_tips_pct"] if idx == "NDX" else np.nan

        out[idx] = {
            "aggregate_ratios": agg,
            "distributions": {c: dist(d, c) for c in
                              ["trailingPE", "forwardPE",
                               "priceToSalesTrailing12Months", "enterpriseToEbitda",
                               "priceToBook", "profitMargins", "revenueGrowth",
                               "earningsGrowth", "rev_cagr_stmt", "eps_cagr_stmt",
                               "netdebt_ebitda", "earnings_yield_pct"]},
            "concentration": concentration(d),
            "earnings_yield": {
                "trailing_agg_pct": ey_agg,
                "forward_agg_pct": ey_fwd,
                "rate_nominal_10y_pct": rate_nom,
                "erp_nominal_trailing_pp": ey_agg - rate_nom,
                "erp_nominal_forward_pp": ey_fwd - rate_nom,
                "rate_real_10y_pct": rate_real,
                "erp_vs_real_trailing_pp": (ey_agg - rate_real
                                            if np.isfinite(rate_real) else None),
            },
            "n_loss_making": int((d.trailingEps < 0).sum()),
            "loss_making_cap_pct": float(
                d.loc[d.trailingEps < 0, "marketCap"].sum() / d.marketCap.sum() * 100),
        }
        print(f"\n===== {idx}  ({len(d)} lines, {d.currency.mode().iloc[0]}) =====")
        print(f"  agg P/E trail {agg['pe_trailing']['aggregate']:.1f}  "
              f"| median {out[idx]['distributions']['trailingPE']['median']:.1f}")
        print(f"  agg P/E fwd   {agg['pe_forward']['aggregate']:.1f}  "
              f"| median {out[idx]['distributions']['forwardPE']['median']:.1f}")
        print(f"  EY trail {ey_agg:.2f}%  vs 10y {rate_nom:.2f}%  "
              f"=> ERP {ey_agg - rate_nom:+.2f} pp")
        c = out[idx]["concentration"]
        print(f"  top5 {c['top5_pct']:.1f}%  top10 {c['top10_pct']:.1f}%  "
              f"HHI {c['herfindahl']:.4f} (eff. N {c['hhi_effective_n']:.1f})")
        print(f"  loss-making: {out[idx]['n_loss_making']} names, "
              f"{out[idx]['loss_making_cap_pct']:.1f}% of cap")

    (CACHE / "aggregates.json").write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote aggregates.json + constituents_*.csv + coverage_*.csv")
