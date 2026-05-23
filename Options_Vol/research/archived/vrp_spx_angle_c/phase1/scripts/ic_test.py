#!/usr/bin/env python3
"""
Phase 1 IC Feasibility Test — SPX Variance Risk Premium
Angle C: VIX z-score conditional selling (z > 1.0, pre-committed threshold)

Outcome  : Variance swap P&L proxy  Outcome[t] = VIX[t]^2 - RV_fwd[t]^2
           RV_fwd[t] = sqrt(252 * mean(log_ret²[t+1..t+30])) * 100
Signal   : VIX_z[t-1]  (strict T-1 lag; EMA90/EWMSD90 normalization)
HAC      : Newey-West lag-30 (30-day overlapping outcome → structural autocorr)
IC gate  : t_HAC > 3.5  (global n_tests ~320, BHY-FDR compromise)
Threshold: z > 1.0  (pre-committed, no multi-threshold scan)
"""
import calendar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from io import StringIO
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import rankdata

np.random.seed(42)

# ── paths -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── constants (pre-committed, no scan) -------------------------------------
SIGNAL_THRESHOLD = 1.0
HAC_LAGS         = 30
GATE_T_HAC       = 3.5
GATE_VRP_VOLPTS  = 2.0
GATE_EVENTS_YR   = 30


# ── data fetch (query1.finance.yahoo.com only) -----------------------------

def _unix_ts(year: int, month: int, day: int) -> int:
    return int(calendar.timegm(datetime(year, month, day).timetuple()))


def _fetch_v8(symbol: str, start_year: int = 1990, end_year: int = 2026,
              cache_path: Optional[str] = None) -> pd.DataFrame:
    """Fetch daily close via Yahoo Finance v8 chart API (no crumb required)."""
    if cache_path and os.path.exists(cache_path):
        print(f"  [cache] {os.path.basename(cache_path)}")
        df = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
        return df

    p1 = _unix_ts(start_year, 1, 1)
    p2 = _unix_ts(end_year, 12, 31)
    sym_enc = urllib.parse.quote(symbol)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym_enc}"
        f"?interval=1d&period1={p1}&period2={p2}"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"STOP: HTTP {e.code} fetching {symbol} from query1.finance.yahoo.com")
        sys.exit(1)
    except Exception as e:
        print(f"STOP: Network error fetching {symbol}: {e}")
        sys.exit(1)

    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes     = result["indicators"]["quote"][0]["close"]

    dates = [datetime.utcfromtimestamp(t).date() for t in timestamps]
    df = pd.DataFrame({"Date": dates, symbol: closes})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").dropna()

    if cache_path:
        df.to_csv(cache_path)
        print(f"  [fetched & cached] {os.path.basename(cache_path)}")
    return df


# ── IC helpers --------------------------------------------------------------

def spearman_ic_hac(
    signal: np.ndarray, outcome: np.ndarray, maxlags: int
) -> tuple[float, float, float]:
    """Rank-OLS with HAC(maxlags) → (Spearman IC, t_stat, p_val)."""
    mask = ~(np.isnan(signal) | np.isnan(outcome))
    s = signal[mask].astype(float)
    y = outcome[mask].astype(float)
    n = len(s)
    if n < 20:
        return np.nan, np.nan, np.nan

    lags = min(maxlags, n // 3)
    sr = rankdata(s); yr = rankdata(y)
    sr = (sr - sr.mean()) / sr.std()
    yr = (yr - yr.mean()) / yr.std()

    model = sm.OLS(yr, sm.add_constant(sr)).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True}
    )
    return float(model.params[1]), float(model.tvalues[1]), float(model.pvalues[1])


# ── main -------------------------------------------------------------------

def main() -> dict:
    print("=" * 65)
    print("  Phase 1 IC Test — SPX VRP Angle C (z > 1.0, pre-committed)")
    print("=" * 65)

    # 1. DATA ----------------------------------------------------------------
    print("\n[1] Data fetch / cache ...")
    vix_raw = _fetch_v8(
        "^VIX", cache_path=os.path.join(DATA_DIR, "vix_daily.csv")
    )
    spx_raw = _fetch_v8(
        "^GSPC", cache_path=os.path.join(DATA_DIR, "spx_daily.csv")
    )

    df = pd.concat([vix_raw, spx_raw], axis=1).dropna()
    df.columns = ["VIX", "SPX"]
    df = df.sort_index()
    print(f"  Range: {df.index[0].date()} → {df.index[-1].date()}  ({len(df):,} days)")

    # 2. FEATURE ENGINEERING -------------------------------------------------
    print("\n[2] Computing features ...")

    df["log_ret"] = np.log(df["SPX"] / df["SPX"].shift(1))

    # Backward RV (annualized %, 30-day window)
    df["RV_back"] = df["log_ret"].rolling(30).apply(
        lambda x: np.sqrt(252.0 * np.mean(x ** 2)) * 100, raw=True
    )

    # Forward RV: at time t, uses log_ret[t+1 .. t+30]
    # rolling(30) at t+30 covers [t+1..t+30]; shift(-30) maps that value to t
    df["RV_fwd"] = df["log_ret"].rolling(30).apply(
        lambda x: np.sqrt(252.0 * np.mean(x ** 2)) * 100, raw=True
    ).shift(-30)

    # VRP raw (vol points) — used only for pre-flight gate
    df["VRP_raw"] = df["VIX"] - df["RV_fwd"]

    # Variance swap P&L proxy (variance points; positive = seller profitable)
    df["Outcome"] = df["VIX"] ** 2 - df["RV_fwd"] ** 2

    # VIX z-score
    df["EMA90"]   = df["VIX"].ewm(span=90, adjust=False).mean()
    df["EWMSD90"] = df["VIX"].ewm(span=90, adjust=False).std()
    df["VIX_z"]   = (df["VIX"] - df["EMA90"]) / df["EWMSD90"]

    # Signal at T-1 (strict lag)
    df["Signal"] = df["VIX_z"].shift(1)

    # Post-warmup cutoff (EWM needs ~1 year of VIX; cutoff 2000-01-01)
    df_clean = df.dropna(subset=["Signal", "Outcome", "VRP_raw"]).copy()
    df_clean = df_clean[df_clean.index >= "2000-01-01"]
    print(f"  Clean rows (post-2000 EWM warmup): {len(df_clean):,}")

    # Sub-period masks
    sp_masks: dict[str, pd.Series] = {
        "2010-2015": (df_clean.index >= "2010-01-01") & (df_clean.index < "2016-01-01"),
        "2015-2020": (df_clean.index >= "2015-01-01") & (df_clean.index < "2020-01-01"),
        "2020-2025": (df_clean.index >= "2020-01-01") & (df_clean.index <= "2025-12-31"),
    }

    # Conditional mask (pre-committed threshold)
    cond_mask: pd.Series = df_clean["Signal"] > SIGNAL_THRESHOLD

    results: dict = {}

    # 3. PRE-FLIGHT: VRP MAGNITUDE -------------------------------------------
    print("\n[3] Pre-flight gate — VRP magnitude (VIX − RV_fwd, vol points)")
    vrp_by_period: dict = {}
    for label, mask in sp_masks.items():
        sub = df_clean.loc[mask, "VRP_raw"].dropna()
        m   = float(sub.mean())
        pct = float((sub > 0).mean() * 100)
        vrp_by_period[label] = {"mean": round(m, 3), "pct_positive": round(pct, 1), "n": len(sub)}
        print(f"  {label}: mean = {m:+.2f} vol pts  ({pct:.1f}% positive,  n={len(sub):,})")

    gate_vrp_val  = vrp_by_period["2020-2025"]["mean"]
    gate_vrp_pass = gate_vrp_val >= GATE_VRP_VOLPTS
    print(f"\n  GATE VRP (2020-2025 ≥ {GATE_VRP_VOLPTS}): "
          f"{'PASS' if gate_vrp_pass else 'FAIL'}  ({gate_vrp_val:.2f})")

    if not gate_vrp_pass:
        print("\n  Pre-flight FAIL → archive without IC test.")
        results.update({
            "verdict": "FAIL",
            "fail_reason": f"VRP_2020-2025 = {gate_vrp_val:.2f} < {GATE_VRP_VOLPTS}",
            "vrp_by_period": vrp_by_period,
        })
        _save_json(results, os.path.join(BASE_DIR, "phase1_results.json"))
        return results

    results["vrp_by_period"]  = vrp_by_period
    results["gate_vrp_val"]   = gate_vrp_val
    results["gate_vrp_pass"]  = gate_vrp_pass

    # 4. IC UNCONDITIONAL ----------------------------------------------------
    print("\n[4] IC unconditional (all clean dates, 2000-present)")
    ic_u, t_u, p_u = spearman_ic_hac(
        df_clean["Signal"].values, df_clean["Outcome"].values, HAC_LAGS
    )
    n_u = len(df_clean.dropna(subset=["Signal", "Outcome"]))
    print(f"  Spearman IC = {ic_u:.4f}  |  HAC({HAC_LAGS}) t = {t_u:.3f}  |  p = {p_u:.4f}  |  N = {n_u:,}")
    results["ic_unconditional"] = {
        "ic": round(ic_u, 4), "t_hac": round(t_u, 3), "p": round(p_u, 4), "n": n_u
    }

    # 5. IC CONDITIONAL z > 1.0 ---------------------------------------------
    print(f"\n[5] IC conditional (Signal > {SIGNAL_THRESHOLD})")
    sub_c = df_clean.loc[cond_mask].dropna(subset=["Signal", "Outcome"])
    n_c   = len(sub_c)
    ic_c, t_c, p_c = spearman_ic_hac(
        sub_c["Signal"].values, sub_c["Outcome"].values, HAC_LAGS
    )
    mean_out_cond = float(sub_c["Outcome"].mean())
    print(f"  Spearman IC = {ic_c:.4f}  |  HAC({HAC_LAGS}) t = {t_c:.3f}  |  p = {p_c:.4f}  |  N = {n_c:,}")
    print(f"  Mean Outcome (cond)  = {mean_out_cond:+.2f} variance pts")

    # Robustness: monthly non-overlapping sub-sample
    sub_c_mo = sub_c.resample("ME").first().dropna(subset=["Signal", "Outcome"])
    n_mo = len(sub_c_mo)
    ic_mo = t_mo = np.nan
    if n_mo >= 15:
        ic_mo, t_mo, _ = spearman_ic_hac(
            sub_c_mo["Signal"].values, sub_c_mo["Outcome"].values, maxlags=1
        )
        print(f"  Robustness (monthly non-overlap, HAC(1)): IC={ic_mo:.4f}, t={t_mo:.3f}, N_months={n_mo}")

    results["ic_conditional"] = {
        "threshold":     SIGNAL_THRESHOLD,
        "ic":            round(ic_c, 4),
        "t_hac":         round(t_c, 3),
        "p":             round(p_c, 4),
        "n":             n_c,
        "mean_outcome":  round(mean_out_cond, 3),
        "monthly_ic":    round(float(ic_mo), 4) if not np.isnan(ic_mo) else None,
        "monthly_t_hac": round(float(t_mo), 3) if not np.isnan(t_mo) else None,
        "n_monthly":     n_mo,
    }

    # 6. SUB-PERIOD STABILITY ------------------------------------------------
    print("\n[6] Sub-period stability (conditional z > 1.0 within each sub-period)")
    sp_results: dict = {}
    for label, mask in sp_masks.items():
        sub_sp = df_clean.loc[mask & cond_mask].dropna(subset=["Signal", "Outcome"])
        n_sp   = len(sub_sp)
        if n_sp < 20:
            sp_results[label] = {"n": n_sp, "ic": None, "t": None, "mean_outcome": None}
            print(f"  {label}: N={n_sp} — insufficient (<20)")
            continue
        ic_sp, t_sp, _ = spearman_ic_hac(
            sub_sp["Signal"].values, sub_sp["Outcome"].values,
            maxlags=min(HAC_LAGS, n_sp // 4),
        )
        mean_out_sp = float(sub_sp["Outcome"].mean())
        sp_results[label] = {
            "n":            n_sp,
            "ic":           round(float(ic_sp), 4) if not np.isnan(ic_sp) else None,
            "t_hac":        round(float(t_sp), 3)  if not np.isnan(t_sp) else None,
            "mean_outcome": round(mean_out_sp, 3),
        }
        print(f"  {label}: N={n_sp:4d}  IC={ic_sp:+.4f}  t_HAC={t_sp:+.3f}  "
              f"mean_outcome={mean_out_sp:+.2f} var pts")
    results["subperiod_stability"] = sp_results

    # 7. EVENT COUNT ---------------------------------------------------------
    print(f"\n[7] Event count (Signal > {SIGNAL_THRESHOLD} per calendar year)")
    cond_days = df_clean.loc[cond_mask].copy()
    cond_days["Year"] = cond_days.index.year
    events_yr = cond_days.groupby("Year").size()
    mean_ev = float(events_yr.mean())
    min_ev  = int(events_yr.min())
    max_ev  = int(events_yr.max())
    print(f"  Mean = {mean_ev:.1f}/yr  |  Min = {min_ev}  |  Max = {max_ev}")
    # Print per-year table
    yr_table = "  " + "  ".join(f"{int(yr)}: {int(n)}" for yr, n in events_yr.items())
    print(yr_table)
    results["event_count"] = {
        "mean_per_year": round(mean_ev, 1),
        "min_per_year":  min_ev,
        "max_per_year":  max_ev,
        "by_year":       {int(k): int(v) for k, v in events_yr.items()},
    }

    # 8. VERDICT -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  VERDICT")
    print("=" * 65)

    gate_vrp_p  = gate_vrp_pass
    gate_sign_p = (ic_c is not None) and (not np.isnan(ic_c)) and (ic_c > 0)
    gate_t_p    = (t_c is not None) and (not np.isnan(t_c)) and (t_c > GATE_T_HAC)
    gate_ev_p   = mean_ev >= GATE_EVENTS_YR
    gate_stab_p = all(
        v["ic"] is not None and v["ic"] > 0
        for v in sp_results.values()
        if v["ic"] is not None
    )

    _g = lambda p: "PASS" if p else "FAIL"
    print(f"  [{_g(gate_vrp_p)}]  VRP 2020-2025 ≥ {GATE_VRP_VOLPTS} vol pts        ({gate_vrp_val:.2f})")
    print(f"  [{_g(gate_sign_p)}]  IC direction > 0                    (IC={ic_c:.4f})")
    print(f"  [{_g(gate_t_p)}]  HAC({HAC_LAGS}) t-stat > {GATE_T_HAC}            (t={t_c:.3f})")
    print(f"  [{_g(gate_ev_p)}]  Events/yr ≥ {GATE_EVENTS_YR}                    ({mean_ev:.1f}/yr)")
    print(f"  [{_g(gate_stab_p)}]  No sub-period sign reversal")

    overall = all([gate_vrp_p, gate_sign_p, gate_t_p, gate_ev_p, gate_stab_p])
    verdict = "PASS" if overall else "FAIL"
    print(f"\n  OVERALL: {verdict}")
    if overall:
        print("  → PASS — awaiting explicit chat validation for Phase 2.")
    else:
        gates_failed = [
            name for name, p in [
                ("VRP_magnitude", gate_vrp_p), ("IC_direction", gate_sign_p),
                ("IC_t_HAC", gate_t_p), ("events/yr", gate_ev_p),
                ("sign_stability", gate_stab_p)
            ] if not p
        ]
        print(f"  → FAIL gates: {gates_failed}")
        print("  → ARCHIVE options vol domain.")

    results.update({
        "gates": {
            "vrp_magnitude":  gate_vrp_p,
            "ic_direction":   gate_sign_p,
            "ic_t_hac":       gate_t_p,
            "event_count":    gate_ev_p,
            "sign_stability": gate_stab_p,
        },
        "verdict":           verdict,
        "n_tests_increment": 1,
        "data_range":        f"{df.index[0].date()} to {df.index[-1].date()}",
    })

    _save_json(results, os.path.join(BASE_DIR, "phase1_results.json"))
    return results


def _save_json(obj: dict, path: str) -> None:
    def _serial(o):
        if isinstance(o, (np.integer,)):  return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.ndarray,)):  return o.tolist()
        raise TypeError(f"Not serializable: {type(o)}")
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=_serial)
    print(f"\n  Results saved → {os.path.basename(path)}")


if __name__ == "__main__":
    main()
