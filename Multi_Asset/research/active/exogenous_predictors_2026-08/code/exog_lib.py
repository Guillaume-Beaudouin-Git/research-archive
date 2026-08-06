"""Shared library: exogenous predictor panel + inference helpers.

READ-ONLY on every path under the main working dir. All session caches go to
EXOG_CACHE (session-private, never the repo).

Interpreter: /usr/bin/python3 (pandas 2.2.3 / numpy 2.0.2 / statsmodels 0.14.6).
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = "<HOME>/Desktop/Algo_claude"
CACHE = os.environ.get(
    "EXOG_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/exog_cache",
)
GROSSMAP = (
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/grossmap_cache"
)

# ---------------------------------------------------------------- costs / swap
# COST_AUDIT.md 2026-07-31 (measured, not catalogue) + mission brief.
COST_RT_BPS = {"XAUUSD": 1.84, "USDJPY": 1.50}
COST_RT_TAIL_BPS = {"XAUUSD": 3.88, "USDJPY": 3.00}
# Asymmetric overnight swap, bps per night, SIGNED (negative = you pay).
SWAP_BPS = {
    "XAUUSD": {"long": -1.518, "short": -0.336},
    "USDJPY": {"long": +0.060, "short": -1.267},
}

POST2021 = pd.Timestamp("2021-01-01")


# ------------------------------------------------------------------ price data
def load_daily_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Canonical daily px / rets panel used by the deployed book and both sleeve audits."""
    px = pd.read_parquet(f"{MAIN}/data/ftmo_portfolio/cache/panel_px.parquet")
    rets = pd.read_parquet(f"{MAIN}/data/ftmo_portfolio/cache/panel_rets.parquet")
    return px, rets


def load_h1(inst: str) -> pd.DataFrame:
    """True-UTC hourly bars built by gross_surface_map (read-only reuse)."""
    return pd.read_parquet(f"{GROSSMAP}/{inst}_H1.parquet")


# -------------------------------------------------------------- exogenous data
def _clean(d):
    """Sort ascending and drop duplicate index labels.

    Not cosmetic: the NAAIM cache is stored DESCENDING and carries 2 duplicate
    labels (2006-07-05 / 2006-07-12, two scrapes with different rounding), which
    makes a plain .reindex() raise. Applied to every exogenous input.
    """
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d


def _fred(name: str) -> pd.DataFrame:
    return _clean(pd.read_parquet(f"{MAIN}/data/raw/{name}.parquet"))


def build_exog_raw() -> pd.DataFrame:
    """Raw daily exogenous state, indexed by the date the observation REFERS TO.

    No shifting is applied here. Shifting to what was knowable at T-1 is done in
    build_exog_panel(), which is the only function callers should use.
    """
    # widest-coverage file for each series (see cache inventory)
    big = _fred("fred_BAMLH0A0_DGS3MO_DTWEXBGS_d06fce80fc")  # 2007-01-01 ->
    dtb3 = _fred("fred_DTB3_37358bdf84")["dtb3"]             # 2000-01-03 ->
    dgs3mo = _fred("fred_DGS3MO_16fc089f19")["dgs3mo"]       # 2003-01-01 ->
    t10y2y = _fred("fred_T10Y2Y_4b4c751920")["t10y2y"]       # 2003-01-01 ->
    dtwex = _fred("fred_DTWEXBGS_ff6045edaa")["dtwexbgs"]    # 2006-01-02 ->
    vix = _fred("fred_VIXCLS_14ec2ab193")["vixcls"]          # 2007-01-01 ->
    baml = big["bamlh0a0hym2"]                               # TRUNCATED, see inventory
    naaim = _clean(pd.read_parquet(f"{MAIN}/data/raw/http_naaim_exposure_xlsx_ffd686b1.parquet"))

    df = pd.DataFrame(
        {
            "dtb3": dtb3,
            "dgs3mo": dgs3mo,
            "t10y2y": t10y2y,
            "t10y3m": big["t10y3m"],
            "dtwexbgs": dtwex,
            "vix": vix,
            "baml_hy": baml,
        }
    ).sort_index()
    df["naaim"] = naaim["naaim_exposure"].reindex(df.index).ffill(limit=10)

    # JPY 3M interbank, MONTH-END observations -> forward-filled within the month
    fx3m = _clean(pd.read_csv(f"{MAIN}/data/panels/fx_rates_3m.csv", index_col=0, parse_dates=True))
    df["jpy3m"] = fx3m["JPY"].reindex(df.index).ffill(limit=45)
    df["usd3m_m"] = fx3m["USD"].reindex(df.index).ffill(limit=45)
    return df


def build_exog_panel(shift_days: int = 1) -> pd.DataFrame:
    """Exogenous predictors as they were KNOWABLE at the close of T-`shift_days`.

    Every transform (differences, z-scores, quantile ranks) is computed on the
    raw series and only THEN shifted, so no post-shift value can peek forward.
    Rolling statistics use trailing windows only.
    """
    r = build_exog_raw()
    out = pd.DataFrame(index=r.index)

    # E1 short rate momentum  (gold: opportunity cost; USDJPY: rate differential)
    out["E1_d_short_rate"] = r["dgs3mo"].diff(5)
    # E2 curve slope level
    out["E2_slope"] = r["t10y2y"]
    # E3 curve slope change
    out["E3_d_slope"] = r["t10y2y"].diff(20)
    # E4 dollar momentum  (flagged: near-tautological for gold, L38)
    out["E4_d_dollar"] = np.log(r["dtwexbgs"]).diff(5) * 1e4
    # E5 risk appetite
    out["E5_d_vix"] = r["vix"].diff(5)
    out["E5b_vix_level"] = r["vix"]
    # E6 US-JPY 3M differential (USDJPY only; monthly source)
    out["E6_us_jpy_diff"] = r["usd3m_m"] - r["jpy3m"]
    out["E6b_d_us_jpy_diff"] = (r["usd3m_m"] - r["jpy3m"]).diff(21)
    # E7 equity manager exposure (weekly survey)
    out["E7_naaim"] = r["naaim"]
    # E8 credit spread -- retained only to DOCUMENT that the cache is unusable
    out["E8_baml_hy"] = r["baml_hy"]

    return out.shift(shift_days)


# Pre-registered mechanism signs: +1 means "high predictor -> instrument UP".
# Written BEFORE any measurement (see RESULTS.md section 2).
MECHANISM_SIGN = {
    "XAUUSD": {
        "E1_d_short_rate": -1,   # rising short rates raise the opportunity cost of a zero-coupon real asset
        "E2_slope": +1,          # steep curve = easing expected = lower future real rates
        "E3_d_slope": +1,        # steepening = same, in change form
        "E4_d_dollar": -1,       # gold is USD-denominated (FLAGGED near-tautological, L38)
        "E5_d_vix": +1,          # safe-haven bid
        "E5b_vix_level": +1,
        "E7_naaim": -1,          # high equity exposure = risk-on = no haven bid
    },
    "USDJPY": {
        "E1_d_short_rate": +1,   # widening US-JPY differential pulls USDJPY up (UIP failure / carry)
        "E2_slope": +1,
        "E3_d_slope": +1,
        "E4_d_dollar": +1,       # dollar strength IS USDJPY strength (FLAGGED tautological)
        "E5_d_vix": -1,          # risk-off unwinds the JPY funding leg -> USDJPY down
        "E5b_vix_level": -1,
        "E6_us_jpy_diff": +1,    # carry level
        "E6b_d_us_jpy_diff": +1,
        "E7_naaim": +1,
    },
}


# ------------------------------------------------------------------- inference
def hac_t(y: np.ndarray, lags: int = 6) -> tuple[float, float]:
    """(mean, HAC t-stat) of a series against zero. Newey-West lag-6."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if len(y) < 20:
        return (float(np.mean(y)) if len(y) else np.nan, np.nan)
    X = np.ones((len(y), 1))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0])


def matched_baseline(side: np.ndarray, r_all: np.ndarray) -> float:
    """L58 state-matched baseline.

    The baseline for a trade SHAPE is the unconditional expectation of that same
    shape, weighted by the side mix the state actually produces. A long-biased
    state must be compared against an unconditional LONG, not against zero.
    """
    side = np.asarray(side, dtype=float)
    m_all = float(np.nanmean(r_all))
    active = side[side != 0]
    if len(active) == 0:
        return np.nan
    return float(np.mean(active)) * m_all


def block_bootstrap_p(y: np.ndarray, block: int = 10, n_boot: int = 5000,
                      seed: int = 7) -> float:
    """Two-sided p-value for mean(y) != 0 under a circular block bootstrap."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 30:
        return np.nan
    rng = np.random.default_rng(seed)
    obs = float(np.mean(y))
    yc = y - obs  # centre under H0
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    samp = yc[idx.reshape(n_boot, -1)[:, :n]]
    means = samp.mean(axis=1)
    return float((np.abs(means) >= abs(obs)).mean())


def walk_forward(dates: pd.DatetimeIndex, y: np.ndarray, n_folds: int = 5) -> dict:
    """Expanding-window walk-forward on the realised per-trade series.

    There is no parameter to fit here (signs are pre-registered), so the fold
    test is simply: is the mean positive in each out-of-sample fold?
    """
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(y)
    y, dates = y[ok], dates[ok]
    n = len(y)
    if n < n_folds * 20:
        return {"folds_pos": np.nan, "n_folds": 0, "fold_means": []}
    edges = np.linspace(0, n, n_folds + 1).astype(int)
    means = [float(np.mean(y[edges[i]:edges[i + 1]])) for i in range(n_folds)]
    return {
        "folds_pos": int(sum(m > 0 for m in means)),
        "n_folds": n_folds,
        "fold_means": [round(m, 3) for m in means],
    }


def summarise(name: str, dates, r_trade: np.ndarray, side: np.ndarray,
              r_uncond: np.ndarray, per_year: float) -> dict:
    """One row of the results table: gross, frequency, matched baseline, excess."""
    m = np.isfinite(r_trade) & (side != 0)
    y = r_trade[m]
    d = dates[m]
    gross, t_gross = hac_t(y)
    base = matched_baseline(side[np.isfinite(r_trade)], r_uncond)
    exc = y - base
    excess, t_exc = hac_t(exc)
    return {
        "name": name,
        "N": int(len(y)),
        "freq_per_year": round(len(y) / per_year, 1),
        "gross_bps": round(gross, 3),
        "t_gross": round(t_gross, 2),
        "baseline_bps": round(base, 3),
        "excess_bps": round(excess, 3),
        "t_excess": round(t_exc, 2),
        "_y": y,
        "_d": d,
    }
