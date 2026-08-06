"""Part 1 — the carry balance of a two-sided sleeve, exactly.

Decomposes the FTMO swap panel into
    swap_long_t  = -(r_t + m)
    swap_short_t = +(r_t - m)
with `m` an instrument-specific, side-independent markup and `r_t` the broker's
implied funding rate. Everything downstream (break-even short fraction, the
sign-flip threshold) follows from that decomposition.

Outputs
    swap_decomposition.csv     m, r_t by era, markup constancy check
    carry_vs_short_fraction.csv carry bill as a function of the short fraction
    breakeven_short_fraction.csv
    sign_flip_threshold.csv    mu* vs the measured drift
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
PCACHE = MAIN / "data/ftmo_portfolio/cache"
TS = Path(os.environ.get(
    "TS_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/ts_cache",
))
OUT = Path(__file__).resolve().parent.parent

BOOK = ["US100", "GER40", "XAUUSD", "USDJPY"]          # instruments actually traded
WIDE = ["US500", "US100", "US30", "GER40", "XAUUSD", "XAGUSD", "USDJPY",
        "EURUSD", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
        "EURGBP", "EURJPY", "AUDJPY", "UKOIL", "USOIL"]

# nights actually charged per year for a few holding policies
NIGHT_POLICIES = {
    "continuous (7 nights/wk, triple-day convention)": 365.0,
    "weeknights only, triple day avoided (4/wk)": 208.0,
    "book overnight sleeve (Mon+Tue nights)": 104.0,
}


def load_swaps():
    sL = pd.read_parquet(PCACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(PCACHE / "panel_swapS.parquet")
    mult = pd.read_parquet(PCACHE / "panel_mult.parquet")
    return sL, sS, mult


def decompose(sL, sS):
    markup = -(sL + sS) / 2.0     # paid on BOTH sides
    funding = (sS - sL) / 2.0     # cost of being long / credit for being short
    return markup, funding


def main():
    sL, sS, mult = load_swaps()
    markup, funding = decompose(sL, sS)
    sl13 = slice("2013-01-01", None)

    # ---------- 1. markup constancy -------------------------------------
    rows = []
    for s in WIDE:
        mk = markup[s].loc[sl13].dropna()
        fd = funding[s].loc[sl13].dropna()
        rows.append({
            "symbol": s,
            "markup_bps_night": round(float(mk.mean()), 4),
            "markup_std": round(float(mk.std()), 6),
            "markup_n_distinct_values": int(mk.round(6).nunique()),
            "markup_pct_yr_365n": round(float(mk.mean()) * 365 / 100, 3),
            "funding_bps_night_mean": round(float(fd.mean()), 4),
            "funding_bps_night_min": round(float(fd.min()), 4),
            "funding_bps_night_max": round(float(fd.max()), 4),
            "funding_n_distinct_values": int(fd.round(6).nunique()),
            "swap_long_2026": round(float(sL[s].loc["2026"].mean()), 4),
            "swap_short_2026": round(float(sS[s].loc["2026"].mean()), 4),
        })
    dec = pd.DataFrame(rows)
    dec.to_csv(OUT / "swap_decomposition.csv", index=False)

    # ---------- 2. carry bill vs short fraction -------------------------
    eras = {"ZIRP 2013-2021": slice("2013-01-01", "2021-12-31"),
            "hiking/high 2022-2026": slice("2022-01-01", None),
            "full 2013-2026": sl13}
    rows = []
    for s in WIDE:
        for ename, esl in eras.items():
            a, b = float(sL[s].loc[esl].mean()), float(sS[s].loc[esl].mean())
            for f in (0.0, 0.25, 0.50, 0.75, 1.0):
                c = (1 - f) * a + f * b
                rec = {"symbol": s, "era": ename, "short_fraction": f,
                       "carry_bps_per_night": round(c, 4)}
                for pname, n in NIGHT_POLICIES.items():
                    rec[f"pct_yr[{pname}]"] = round(c * n / 100, 3)
                rows.append(rec)
    pd.DataFrame(rows).to_csv(OUT / "carry_vs_short_fraction.csv", index=False)

    # ---------- 3. break-even short fraction ----------------------------
    rows = []
    for s in WIDE:
        for ename, esl in eras.items():
            a, b = float(sL[s].loc[esl].mean()), float(sS[s].loc[esl].mean())
            if b > 0:
                f = -a / (b - a)
                feasible, fstar = (f <= 1.0), round(f, 4)
            else:
                feasible, fstar = False, np.nan
            rows.append({
                "symbol": s, "era": ename,
                "swap_long": round(a, 4), "swap_short": round(b, 4),
                "differential_favouring_short": round(b - a, 4),
                "short_leg_carry_positive": bool(b > 0),
                "breakeven_short_fraction": fstar,
                "carry_neutrality_reachable": bool(feasible),
                "best_case_100pct_short_pct_yr_365n": round(b * 365 / 100, 3),
            })
    pd.DataFrame(rows).to_csv(OUT / "breakeven_short_fraction.csv", index=False)

    # ---------- 4. sign-flip threshold vs measured drift ----------------
    R = pd.read_parquet(TS / "daily_logret_swapclock.parquet")
    mult_d = mult.copy()
    rows = []
    for s in WIDE:
        if s not in R.columns:
            continue
        r = R[s].dropna().loc["2013":]
        n = mult_d[s].reindex(r.index).fillna(1.0)          # nights charged per bar
        fd = funding[s].reindex(r.index).ffill()
        # bps
        ret_bps = r * 1e4
        rf_bps = fd * n                                     # risk-free accrual per bar
        exc = ret_bps - rf_bps
        nn = len(r)
        rows.append({
            "symbol": s,
            "n_bars": nn,
            "nights_charged_per_yr": round(float(n.mean()) * 252, 1),
            "drift_bps_per_bar": round(float(ret_bps.mean()), 4),
            "drift_pct_yr": round(float(ret_bps.mean()) * 252 / 100, 2),
            "sign_flip_threshold_mu_star_bps": round(float(rf_bps.mean()), 4),
            "excess_drift_bps_per_bar": round(float(exc.mean()), 4),
            "excess_drift_pct_yr": round(float(exc.mean()) * 252 / 100, 2),
            "excess_drift_t": round(float(exc.mean() / exc.std() * np.sqrt(nn)), 3),
            "pct_bars_below_threshold": round(float((ret_bps < rf_bps).mean()) * 100, 2),
            # perfect-foresight value of the sign option, bps/bar
            "perfect_foresight_gain_bps_bar": round(float((2 * (rf_bps - ret_bps)).clip(lower=0).mean()), 3),
            "markup_paid_either_way_bps_bar": round(float((markup[s].reindex(r.index).ffill() * n).mean()), 4),
        })
    pd.DataFrame(rows).to_csv(OUT / "sign_flip_threshold.csv", index=False)

    print(dec.to_string(index=False))
    print()
    print(pd.read_csv(OUT / "sign_flip_threshold.csv").to_string(index=False))


if __name__ == "__main__":
    main()
