"""What part of the "swap favours the short" is actually a SUBSIDY?

    swap_long_t  = -(r_t + mL)        r_t = benchmark policy rate (3M)
    swap_short_t = +(r_t - mS)        mL, mS = broker markups, per side

    differential in favour of short = swap_short - swap_long = 2*r_t + (mL - mS)

The 2*r_t term is NOT alpha: it is exactly the risk-free accrual a short
forgoes, and the long's drift already contains it. It cancels out of the sign
decision. Only (mL - mS) is a genuine subsidy for taking the short side.

This script computes mL and mS SEPARATELY from the raw measured MT5 snapshot
(spec_v22 `measured_specs`, read 2026-06-10) — the panel's constant markup is
an artefact of `costs.build_swap_model`, so it cannot be used to answer this.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
OUT = Path(__file__).resolve().parent.parent

# measured MT5 snapshot, spec_v22.yaml measured_specs (read_date 2026-06-10)
MEASURED = {
    "XAUUSD": dict(sL=-1.518, sS=-0.3358, bench="USD"),
    "USDJPY": dict(sL=+0.0599, sS=-1.2665, bench="USD-JPY"),
    "US100":  dict(sL=-2.1257, sS=+0.0917, bench="USD"),
    "GER40":  dict(sL=-1.564, sS=-0.1933, bench="EUR"),
}
ASOF = "2026-05-31"


def bench_rate(rates: pd.Series, key: str) -> float:
    if "-" in key:
        b, q = key.split("-")
        return float(rates[b] - rates[q])
    return float(rates[key])


def main():
    rates = pd.read_csv(MAIN / "data/panels/fx_rates_3m.csv",
                        index_col=0, parse_dates=True).ffill().loc[:ASOF].iloc[-1]

    rows = []
    for sym, d in MEASURED.items():
        r0 = bench_rate(rates, d["bench"])                # %/yr
        sL, sS = d["sL"], d["sS"]                         # bps/night
        mL = -sL * 365 / 100.0 - r0                       # %/yr, long-side markup
        mS = r0 - sS * 365 / 100.0                        # %/yr, short-side markup
        diff_bps = sS - sL                                # bps/night, favours short
        rate_part = 2 * r0 * 100 / 365                    # bps/night
        subsidy_bps = diff_bps - rate_part                # == (mL-mS)*100/365
        rows.append({
            "symbol": sym, "benchmark": d["bench"], "bench_rate_pct_yr": round(r0, 3),
            "swap_long_bps_night": sL, "swap_short_bps_night": sS,
            "markup_long_pct_yr": round(mL, 3),
            "markup_short_pct_yr": round(mS, 3),
            "markup_asymmetry_pct_yr_(mL-mS)": round(mL - mS, 3),
            "total_differential_bps_night": round(diff_bps, 4),
            "of_which_risk_free_bps_night": round(rate_part, 4),
            "of_which_TRUE_SUBSIDY_bps_night": round(subsidy_bps, 4),
            "true_subsidy_pct_yr_365n": round(subsidy_bps * 365 / 100, 3),
            "subsidy_share_of_differential_pct": round(100 * subsidy_bps / diff_bps, 1),
        })
    df = pd.DataFrame(rows)

    # ---- sign-flip threshold. BENCHMARK-FREE form:
    #      short beats long tonight  <=>  R_t < (sS - sL)/2 per night held.
    #      The rate/subsidy split below needs a benchmark and is only
    #      interpretable where that benchmark is unambiguous (see caveat col).
    sf = pd.read_csv(OUT / "sign_flip_threshold.csv").set_index("symbol")
    ext = []
    for _, row in df.iterrows():
        s = row["symbol"]
        if s not in sf.index:
            continue
        thr_bps = (row["swap_short_bps_night"] - row["swap_long_bps_night"]) / 2.0
        drift = float(sf.loc[s, "drift_pct_yr"])
        ext.append({
            "symbol": s,
            # benchmark-free
            "sign_flip_threshold_bps_night": round(thr_bps, 4),
            "sign_flip_threshold_pct_yr_365n": round(thr_bps * 365 / 100, 3),
            "measured_drift_pct_yr": drift,
            "drift_minus_threshold_pct_yr": round(drift - thr_bps * 365 / 100, 2),
            # benchmark-dependent split
            "of_which_cash_pct_yr": round(row["bench_rate_pct_yr"], 3),
            "of_which_true_subsidy_pct_yr": round(row["true_subsidy_pct_yr_365n"] / 2, 3),
            "benchmark_reliable": s in ("US100", "GER40"),
            "excess_drift_t_iid": float(sf.loc[s, "excess_drift_t"]),
            "uncond_short_minus_long_pct_yr": round(
                -2 * drift + (row["swap_short_bps_night"] - row["swap_long_bps_night"])
                * 365 / 100, 2),
        })
    ext = pd.DataFrame(ext)

    # ---- GER40 sensitivity: live billed swaps run +6.9% vs the frozen anchor
    billed = pd.read_csv(MAIN / "data/ftmo_portfolio/swaps_billed_live.csv")
    billed["bps"] = billed["swap_usd"] / billed["notional_usd"] * 1e4
    bill = billed.groupby("symbol")["bps"].agg(["mean", "std", "count"]).round(4)

    sens = []
    for scale in (1.00, 1.069, 1.15):
        sL, sS = MEASURED["GER40"]["sL"] * scale, MEASURED["GER40"]["sS"] * scale
        r0 = bench_rate(rates, "EUR")
        subsidy = (sS - sL) - 2 * r0 * 100 / 365
        sens.append({"scale_on_both_sides": scale,
                     "swap_long": round(sL, 4), "swap_short": round(sS, 4),
                     "true_subsidy_bps_night": round(subsidy, 4),
                     "true_subsidy_pct_yr_365n": round(subsidy * 365 / 100, 3)})
    sens = pd.DataFrame(sens)

    df.to_csv(OUT / "markup_asymmetry.csv", index=False)
    ext.to_csv(OUT / "sign_flip_hurdle.csv", index=False)
    sens.to_csv(OUT / "ger40_anchor_sensitivity.csv", index=False)

    print("=== markup decomposed by side (measured MT5 snapshot 2026-06-10) ===")
    print(df.to_string(index=False))
    print("\n=== the hurdle a short leg must clear ===")
    print(ext.to_string(index=False))
    print("\n=== live billed swaps, bps/night ===")
    print(bill.to_string())
    print("\n=== GER40 stale-anchor sensitivity ===")
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
