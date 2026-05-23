"""
multi_asset_tsmom/feasibility.py
==================================
Replication of Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" — JFE
on 12 liquid ETFs as futures proxies.

Literature
----------
MOP (2012): 58 futures (equity, bond, FX, commodity), 1985-2009, Sharpe ~0.74.
Key finding: TSMOM profits are explained by each asset's OWN time-series
predictability, NOT cross-sectional ranking against other assets.
Individual positions can be long OR short independent of the universe average.

Why ETFs instead of futures
---------------------------
Adjusted close from yfinance gives a clean continuous series. Roll costs are
absorbed into ETF expense ratios (0.05-0.20%/yr — negligible for monthly signals).
Known understatement: ETF TSMOM uses less leverage than futures. Reported
Sharpe is conservative relative to a fully-leveraged futures implementation.

Universe (12 ETFs, all live since 2004-2005)
---------------------------------------------
Equity indices: SPY, QQQ, EFA, EEM, IWM
Fixed income:   TLT, IEF, SHY
Commodities:    GLD, USO, DBA
Real assets:    VNQ

Signal (MOP eq. 1)
------------------
  tsmom[i,T] = tanh( cumret_12M[i,T] / (vol_12M[i,T] × sqrt(12)) )

Alignment convention (verified via synthetic test BEFORE real data):
  cumret_12M[i,T] = sum of logret[i, T-12 to T-1]   (skip current month T)
  vol_12M[i,T]    = std  of logret[i, T-12 to T  ]   (include current month T)
  forward return  = logret[i, T+1]                    (next month's return)
  → signal at T uses info through end-of-T, predicts T+1

Sizing: w[i,T] = tsmom[i,T] / n_assets  (gross leverage ≤ 1)
Cost: 5 bps RT

Beta decomposition (monthly only)
----------------------------------
  r_net = α + β_SPY × r_SPY + β_AGG × r_AGG + ε
  Residual Sharpe = (α / σ(ε)) × sqrt(12) — true edge after passive beta.

Gates
-----
  PASS: residual_sharpe > 0.5  AND  COVID_MaxDD > -0.15  AND  avg_pairwise_corr < 0.40
  WEAK: residual_sharpe 0.3-0.5  OR  any two of three gates pass
  SKIP: residual_sharpe < 0.3
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
START        = "2004-01-01"          # 12M warmup → live signal from 2005-01
END          = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT      = 0.0005                # 5 bps RT
ANN_M        = 12
ANN_W        = 52
RESULTS_PATH = Path(__file__).parent / "results.json"

UNIVERSE = ["SPY", "QQQ", "EFA", "EEM", "IWM",
            "TLT", "IEF", "SHY",
            "GLD", "USO", "DBA",
            "VNQ"]
N = len(UNIVERSE)

BETA_FACTORS = ["SPY", "AGG"]        # AGG: iShares Core US Aggregate Bond ETF

CRASH_PERIODS = {
    "GFC_2008":    ("2008-07-01", "2009-06-30"),
    "EuroCrisis":  ("2011-04-01", "2012-01-31"),
    "COVID_2020":  ("2020-02-01", "2020-05-31"),
    "Inflation22": ("2022-01-01", "2022-12-31"),
}


# ──────────────────────────────────────────────────────────────────────────────
# Core signal — used by BOTH real data and synthetic test
# ──────────────────────────────────────────────────────────────────────────────
def _tsmom_signal(px: pd.DataFrame, ann: int) -> pd.DataFrame:
    """
    tanh( cumret / (vol × sqrt(ann)) )

    cumret[T] = rolling(ann).sum().shift(1) of log-returns
              = sum of log-returns from T-ann to T-1  (skip current period)
    vol[T]    = rolling(ann).std() of log-returns
              = std  of log-returns from T-ann to T   (include current period)

    Both use data available at end of period T.
    Forward return = logret[T+1] (next period, computed in caller).
    """
    logret = np.log(px / px.shift(1))
    cumret = logret.rolling(ann).sum().shift(1)      # skip current period
    vol    = logret.rolling(ann).std()               # include current period
    denom  = (vol * np.sqrt(ann)).replace(0, np.nan)
    return np.tanh((cumret / denom).replace([np.inf, -np.inf], np.nan))


# ──────────────────────────────────────────────────────────────────────────────
# STEP 0 — Synthetic alignment test
# ──────────────────────────────────────────────────────────────────────────────
def _cs_ic_series(signal: pd.DataFrame, fwd_ret: pd.DataFrame) -> pd.Series:
    """Cross-sectional Spearman IC at each time step."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig, ret = signal[common], fwd_ret[common]
    out = {}
    for t in sig.index.intersection(ret.index):
        s = sig.loc[t].astype(float)
        r = ret.loc[t].astype(float)
        m = s.notna() & r.notna()
        if m.sum() < 3:
            continue
        rho, _ = stats.spearmanr(s[m].values, r[m].values)
        if np.isfinite(rho):
            out[t] = rho
    return pd.Series(out).sort_index()


def ic_summary(ic: pd.Series, label: str = "") -> dict:
    n = len(ic)
    mean, sd = ic.mean(), ic.std(ddof=1)
    t = mean / (sd / np.sqrt(n)) if sd > 0 and n > 1 else np.nan
    p = f"{label}_" if label else ""
    return {
        f"{p}ic_mean":    float(mean),
        f"{p}ic_std":     float(sd),
        f"{p}ic_tstat":   float(t),
        f"{p}ic_n":       int(n),
        f"{p}ic_pct_pos": float((ic > 0).mean()),
    }


def synthetic_alignment_test() -> bool:
    """
    Plant a known momentum edge (AR(1) with rho=0.50) on 25 synthetic assets
    over 400 months and verify IC is positive and t > 2.

    AR(1): r_t = 0.50 * r_{t-1} + ε_t
    Expected IC: positive (sum of past 12 returns predicts next return via rho).
    If IC ≤ 0 or t ≤ 2 → signal alignment is WRONG → abort real-data run.
    """
    np.random.seed(42)
    n_assets, n_months = 25, 400
    rho, sigma = 0.50, 0.04

    logrets = np.zeros((n_months, n_assets))
    for j in range(n_assets):
        for t in range(1, n_months):
            logrets[t, j] = rho * logrets[t - 1, j] + np.random.randn() * sigma

    dates  = pd.date_range("2000-01-31", periods=n_months, freq="ME")
    ret_df = pd.DataFrame(logrets, index=dates,
                          columns=[f"S{i:02d}" for i in range(n_assets)])
    px_df  = np.exp(ret_df.cumsum())          # log(P) = cumulative sum of log-returns

    sig     = _tsmom_signal(px_df, ann=ANN_M)
    fwd_ret = ret_df.shift(-1)                # fwd_ret[T] = logret[T+1]

    ic     = _cs_ic_series(sig, fwd_ret)
    stats_ = ic_summary(ic)

    passed = stats_["ic_tstat"] > 2.0 and stats_["ic_mean"] > 0
    icon   = "✓ PASS" if passed else "✗ FAIL — alignment bug!"
    print(f"  AR(1) rho={rho}  n_assets={n_assets}  n_periods={n_months}")
    print(f"  IC_mean={stats_['ic_mean']:+.4f}  "
          f"IC_std={stats_['ic_std']:.4f}  "
          f"t={stats_['ic_tstat']:+.2f}  → {icon}")
    return passed


# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — Data download
# ──────────────────────────────────────────────────────────────────────────────
def fetch_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    log.info(f"Downloading {tickers} …")
    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False)
    px  = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    px.index = pd.to_datetime(px.index)
    # Require data from at least 2005 (12M warmup period)
    warmup_date = pd.Timestamp("2005-06-01")
    ok = [c for c in px.columns
          if px[c].first_valid_index() is not None
          and pd.Timestamp(px[c].first_valid_index()) <= warmup_date]
    dropped = set(px.columns) - set(ok)
    if dropped:
        log.warning(f"Dropped (no data before 2005-06): {sorted(dropped)}")
    return px[ok].ffill(limit=3)


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2/3 — TSMOM backtest (monthly OR weekly)
# ──────────────────────────────────────────────────────────────────────────────
def run_tsmom(px_daily: pd.DataFrame, freq: str,
              cost_rt: float = COST_RT) -> tuple[pd.Series, pd.DataFrame, dict]:
    """
    Run full TSMOM backtest at the requested frequency.
    Returns (net_returns_series, signal_df, stats_dict).
    """
    ann    = ANN_M if freq == "monthly" else ANN_W
    resamp = "ME" if freq == "monthly" else "W-FRI"
    px     = px_daily.resample(resamp).last()
    logret = np.log(px / px.shift(1)).dropna(how="all")

    sig     = _tsmom_signal(px, ann=ann)
    fwd_ret = logret.shift(-1)                       # fwd_ret[T] = logret[T+1]

    n   = sig.shape[1]
    w   = sig.fillna(0.0) / n                        # w ∈ [-1/n, 1/n], gross lev ≤ 1

    # Align all on the same index (drop first warmup rows & last NaN fwd_ret)
    idx     = (sig.dropna(how="all")
                   .index.intersection(logret.index)
                   .intersection(fwd_ret.dropna(how="all").index))
    w_al    = w.reindex(idx)
    fwd_al  = fwd_ret.reindex(idx)
    sig_al  = sig.reindex(idx)

    gross    = (w_al * fwd_al).sum(axis=1)
    turnover = (w_al - w_al.shift(1).fillna(0)).abs().sum(axis=1)
    net      = (gross - turnover * (cost_rt / 2.0)).dropna()

    equity  = (1 + net).cumprod()
    max_dd  = float((equity / equity.cummax() - 1.0).min())
    sharpe  = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else np.nan
    ann_ret = float(net.mean() * ann)

    # IC
    ic      = _cs_ic_series(sig_al, fwd_al)
    ic_st   = ic_summary(ic)

    log.info(f"[{freq}] Sharpe={sharpe:.3f}  MaxDD={max_dd:.3f}  "
             f"IC_mean={ic_st['ic_mean']:+.4f}  t={ic_st['ic_tstat']:+.2f}  "
             f"n_assets={n}  n_periods={len(net)}")

    bt = {
        "sharpe":        sharpe,
        "max_dd":        max_dd,
        "ann_ret":       ann_ret,
        "avg_gross_lev": float(w_al.abs().sum(axis=1).mean()),
        "avg_turnover":  float(turnover.mean()),
        "n_assets":      n,
        **ic_st,
    }
    return net, sig_al, bt


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — Beta decomposition
# ──────────────────────────────────────────────────────────────────────────────
def beta_decomposition(net: pd.Series, factor_px: pd.DataFrame,
                        ann: int = ANN_M) -> dict:
    """
    OLS: net_ret = α + β_SPY·r_SPY + β_AGG·r_AGG + ε

    Computes:
      alpha (annualised), t(alpha)
      beta_SPY, t(beta_SPY)
      beta_AGG, t(beta_AGG)
      R²
      residual_sharpe = (α / std(ε)) × sqrt(ann)
        — the TRUE edge after stripping passive equity + bond beta
    """
    fret    = np.log(factor_px / factor_px.shift(1)).dropna(how="all")
    idx     = net.index.intersection(fret.index)
    if len(idx) < 24:
        return {"note": "insufficient overlap for regression (<24 months)"}

    y       = net.loc[idx].values.astype(float)
    factors = [c for c in ["SPY", "AGG"] if c in fret.columns]
    X_raw   = fret.loc[idx, factors].values.astype(float)
    X       = np.column_stack([X_raw, np.ones(len(y))])    # [f1, f2, const]

    coef, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    fitted  = X @ coef
    resid   = y - fitted

    n, k    = len(y), X.shape[1]
    ss_tot  = float(((y - y.mean()) ** 2).sum())
    ss_res  = float((resid ** 2).sum())
    r2      = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    mse     = ss_res / max(n - k, 1)
    XtX_inv = np.linalg.inv(X.T @ X)
    se      = np.sqrt(np.maximum(np.diag(mse * XtX_inv), 0))
    t_vals  = coef / np.where(se > 0, se, np.nan)

    alpha_m      = float(coef[-1])
    alpha_ann    = alpha_m * ann
    resid_sharpe = float((alpha_m / resid.std(ddof=1)) * np.sqrt(ann)) \
                   if resid.std(ddof=1) > 0 else np.nan

    out = {
        "alpha_ann":    round(alpha_ann, 4),
        "alpha_t":      round(float(t_vals[-1]), 2),
        "r2":           round(r2, 4),
        "resid_sharpe": round(resid_sharpe, 3),
        "n_months":     int(n),
    }
    for i, f in enumerate(factors):
        out[f"beta_{f}"]   = round(float(coef[i]), 3)
        out[f"beta_{f}_t"] = round(float(t_vals[i]), 2)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — Crash period stats
# ──────────────────────────────────────────────────────────────────────────────
def crash_stats(net: pd.Series, periods: dict, ann: int) -> dict:
    out = {}
    for name, (s, e) in periods.items():
        sub = net.loc[s:e]
        if len(sub) < 2:
            out[name] = {"note": "insufficient data"}
            continue
        eq = (1 + sub).cumprod()
        out[name] = {
            "period":  f"{s} → {e}",
            "sharpe":  round(float(sub.mean() / sub.std(ddof=1) * np.sqrt(ann)), 2)
                       if sub.std(ddof=1) > 0 else np.nan,
            "max_dd":  round(float((eq / eq.cummax() - 1.0).min()), 4),
            "cum_ret": round(float(eq.iloc[-1] - 1.0), 4),
            "n_obs":   int(len(sub)),
        }
    return out


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6 — Rolling pairwise correlation of TSMOM signals
# ──────────────────────────────────────────────────────────────────────────────
def rolling_signal_corr(sig: pd.DataFrame, window: int = 12) -> dict:
    """
    For each pair of assets, compute rolling `window`-period Pearson
    correlation of their TSMOM signals (positions). Reports:
      mean_rolling_corr : average of per-pair mean rolling correlations
      max_rolling_corr  : average of per-pair max rolling correlations
      n_pairs           : N*(N-1)/2
    """
    cols = sig.dropna(how="all").columns.tolist()
    n    = len(cols)
    means, maxs = [], []
    for i in range(n):
        for j in range(i + 1, n):
            rc = (sig[cols[i]].rolling(window)
                              .corr(sig[cols[j]])
                              .dropna())
            if len(rc) > 0:
                means.append(float(rc.mean()))
                maxs.append(float(rc.max()))
    avg_mean = float(np.mean(means)) if means else np.nan
    avg_max  = float(np.mean(maxs))  if maxs  else np.nan
    return {
        "n_pairs":            n * (n - 1) // 2,
        "window":             window,
        "mean_rolling_corr":  round(avg_mean, 3),
        "max_rolling_corr":   round(avg_max, 3),
        "diversified":        avg_mean < 0.40,
    }


def full_period_corr_table(px: pd.DataFrame) -> pd.DataFrame:
    """Full-period Pearson correlation of monthly log-returns."""
    lr = np.log(px / px.shift(1)).dropna(how="all")
    return lr.corr().round(2)


# ──────────────────────────────────────────────────────────────────────────────
# Gate
# ──────────────────────────────────────────────────────────────────────────────
def _gate(resid_sharpe: float, covid_dd: float, avg_corr: float) -> str:
    a = resid_sharpe > 0.50
    b = covid_dd     > -0.15
    c = avg_corr     < 0.40
    if a and b and c:
        return "PASS"
    if resid_sharpe > 0.30 or (b and c):
        return "WEAK"
    return "SKIP"


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> dict:
    log.info("=== Multi-Asset TSMOM Feasibility (Moskowitz 2012 replication) ===")

    # ── 0. Alignment test ────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 0 — Synthetic AR(1) Alignment Test")
    print("─" * 72)
    if not synthetic_alignment_test():
        log.error("Synthetic alignment test FAILED. Signal alignment is broken. Aborting.")
        sys.exit(1)

    # ── 1. Download data ──────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 1 — Data Download")
    print("─" * 72)
    all_tickers = list(dict.fromkeys(UNIVERSE + BETA_FACTORS))
    px_raw   = fetch_prices(all_tickers, START, END)
    px_univ  = px_raw[[c for c in UNIVERSE if c in px_raw.columns]]
    px_beta  = px_raw[[c for c in BETA_FACTORS if c in px_raw.columns]]
    log.info(f"Universe: {list(px_univ.columns)}  ({px_univ.shape[1]} assets)")
    log.info(f"Beta factors: {list(px_beta.columns)}")

    # ── 2. Monthly TSMOM ─────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 2 — Monthly TSMOM (primary, 12M lookback)")
    print("─" * 72)
    net_m, sig_m, bt_m = run_tsmom(px_univ, freq="monthly")
    crash_m = crash_stats(net_m, CRASH_PERIODS, ann=ANN_M)

    # ── 3. Weekly TSMOM ──────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 3 — Weekly TSMOM (parallel, 52W lookback)")
    print("─" * 72)
    net_w, sig_w, bt_w = run_tsmom(px_univ, freq="weekly")
    crash_w = crash_stats(net_w, CRASH_PERIODS, ann=ANN_W)

    # ── 4. Beta decomposition (monthly) ──────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 4 — Beta Decomposition (OLS: net ~ SPY + AGG)")
    print("─" * 72)
    px_beta_m = px_beta.resample("ME").last()
    beta_m    = beta_decomposition(net_m, px_beta_m, ann=ANN_M)
    resid_sharpe = beta_m.get("resid_sharpe", 0.0) or 0.0

    for k, v in beta_m.items():
        print(f"  {k:<20} {v}")

    # ── 5. Rolling correlation (signals) ─────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 5 — Rolling Pairwise Correlation of TSMOM Signals (12M window)")
    print("─" * 72)
    roll_corr = rolling_signal_corr(sig_m, window=12)
    for k, v in roll_corr.items():
        print(f"  {k:<28} {v}")

    # Full-period correlation table
    print("\n  Full-period log-return correlation matrix (monthly):")
    px_m_for_corr = px_univ.resample("ME").last()
    corr_tbl      = full_period_corr_table(px_m_for_corr)
    # Print compact version: header + rows
    cols_abbr = [c[:4] for c in corr_tbl.columns]
    header    = "      " + " ".join(f"{c:>5}" for c in cols_abbr)
    print(f"  {header}")
    for r in corr_tbl.index:
        row_vals = " ".join(f"{corr_tbl.loc[r, c]:>5.2f}" for c in corr_tbl.columns)
        print(f"  {r[:4]:<4}  {row_vals}")

    # ── 6. Gate evaluation ───────────────────────────────────────────────────
    covid_dd_m = crash_m.get("COVID_2020", {}).get("max_dd", 0.0) or 0.0
    avg_corr   = roll_corr["mean_rolling_corr"]
    gate_m     = _gate(resid_sharpe, covid_dd_m, avg_corr)

    covid_dd_w  = crash_w.get("COVID_2020", {}).get("max_dd", 0.0) or 0.0
    gate_w      = "PASS" if (bt_w["sharpe"] > 0.5 and covid_dd_w > -0.15) else \
                  ("WEAK" if bt_w["sharpe"] > 0.3 else "SKIP")

    # ── Build results ─────────────────────────────────────────────────────────
    results = {
        "monthly": {
            "signal":       "tsmom_12M_monthly",
            "universe":     f"{px_univ.shape[1]} ETFs",
            "freq":         "monthly",
            "cost_rt":      COST_RT,
            "period_start": str(net_m.index.min().date()),
            "period_end":   str(net_m.index.max().date()),
            **bt_m,
            "crashes":      crash_m,
            "beta":         beta_m,
            "gate":         gate_m,
        },
        "weekly": {
            "signal":       "tsmom_52W_weekly",
            "universe":     f"{px_univ.shape[1]} ETFs",
            "freq":         "weekly",
            "cost_rt":      COST_RT,
            "period_start": str(net_w.index.min().date()),
            "period_end":   str(net_w.index.max().date()),
            **bt_w,
            "crashes":      crash_w,
            "gate":         gate_w,
        },
        "rolling_correlation": roll_corr,
    }

    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    # ── Pretty print results ──────────────────────────────────────────────────
    for freq_label, r in (("MONTHLY TSMOM — 12M lookback (primary)", results["monthly"]),
                          ("WEEKLY TSMOM  — 52W lookback (parallel)", results["weekly"])):
        print("\n" + "=" * 72)
        print(freq_label)
        print("=" * 72)
        scalar_keys = [k for k in r if k not in ("crashes", "beta")]
        for k in scalar_keys:
            v = r[k]
            fmt = f"{v:+.4f}" if isinstance(v, float) else str(v)
            print(f"  {k:<24} {fmt}")
        if "crashes" in r:
            print(f"  {'crash_periods':<24}")
            for cn, cv in r["crashes"].items():
                if "max_dd" in cv:
                    print(f"    {cn:<16} MaxDD={cv['max_dd']:+.3f}  "
                          f"CumRet={cv['cum_ret']:+.3f}  Sharpe={cv['sharpe']:+.2f}  "
                          f"n={cv['n_obs']}")
        if "beta" in r:
            print(f"  {'beta_decomposition':<24}")
            for bk, bv in r["beta"].items():
                fmt = f"{bv:+.4f}" if isinstance(bv, float) else str(bv)
                print(f"    {bk:<20} {fmt}")

    print("\n" + "=" * 72)
    print("GATE EVALUATION (monthly, three criteria)")
    print("=" * 72)
    a_ok = resid_sharpe > 0.50
    b_ok = covid_dd_m   > -0.15
    c_ok = avg_corr     < 0.40
    print(f"  Residual Sharpe (α/σ_ε):   {resid_sharpe:+.3f}  "
          f"[gate > 0.50]  {'✓' if a_ok else '✗'}")
    print(f"  COVID 2020 MaxDD:           {covid_dd_m:+.3f}  "
          f"[gate > -0.15] {'✓' if b_ok else '✗'}")
    print(f"  Avg pairwise rolling corr:  {avg_corr:+.3f}  "
          f"[gate < 0.40]  {'✓' if c_ok else '✗'}")
    print(f"\n  ─── MONTHLY GATE: {gate_m}")
    print(f"  ─── WEEKLY  GATE: {gate_w}")
    print("=" * 72)
    print(f"\nResults saved → {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("feasibility run failed")
        sys.exit(1)
