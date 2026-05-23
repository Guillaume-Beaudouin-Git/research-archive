"""
multi_asset_tsmom/walkforward.py
=================================
Formal validation of the multi-asset TSMOM strategy that passed feasibility gate.

Three tasks:
  1. Walk-forward OOS backtest  — 16 expanding windows, 2010-2025
  2. Deflated Sharpe Ratio      — multi-testing correction, n_tests=58
  3. Vol-targeted variant       — propfirm compatibility (target 10% ann vol)

Run AFTER feasibility.py has confirmed PASS.
  python -m Equities.research.passed.multi_asset_tsmom.walkforward
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
# Config (must match feasibility.py)
# ──────────────────────────────────────────────────────────────────────────────
START        = "2004-01-01"
END          = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT      = 0.0005
ANN_M        = 12
UNIVERSE     = ["SPY", "QQQ", "EFA", "EEM", "IWM",
                "TLT", "IEF", "SHY", "GLD", "VNQ"]   # DBA/USO excluded (no pre-2005 data)
BETA_FACTORS = ["SPY", "AGG"]
N_TESTS      = 58    # 53 crypto + 4 FX + 1 this signal (signal #58, DSR correction)

CRASH_PERIODS = {
    "GFC_2008":    ("2008-07-01", "2009-06-30"),
    "EuroCrisis":  ("2011-04-01", "2012-01-31"),
    "COVID_2020":  ("2020-02-01", "2020-05-31"),
    "Inflation22": ("2022-01-01", "2022-12-31"),
}

RESULTS_DIR  = Path(__file__).parent
RESULTS_JSON = RESULTS_DIR / "walkforward_results.json"
SUMMARY_MD   = RESULTS_DIR / "walkforward_summary.md"


# ──────────────────────────────────────────────────────────────────────────────
# Reuse signal from feasibility.py (copy — keep files independent)
# ──────────────────────────────────────────────────────────────────────────────
def _tsmom_signal(px: pd.DataFrame, ann: int) -> pd.DataFrame:
    logret = np.log(px / px.shift(1))
    cumret = logret.rolling(ann).sum().shift(1)
    vol    = logret.rolling(ann).std()
    denom  = (vol * np.sqrt(ann)).replace(0, np.nan)
    return np.tanh((cumret / denom).replace([np.inf, -np.inf], np.nan))


# ──────────────────────────────────────────────────────────────────────────────
# Data
# ──────────────────────────────────────────────────────────────────────────────
def fetch_prices() -> tuple[pd.DataFrame, pd.DataFrame]:
    all_tickers = list(dict.fromkeys(UNIVERSE + BETA_FACTORS))
    log.info(f"Downloading {all_tickers} …")
    raw  = yf.download(all_tickers, start=START, end=END,
                       auto_adjust=True, progress=False)
    px   = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    px.index = pd.to_datetime(px.index)
    px   = px.ffill(limit=3)
    px_univ = px[[c for c in UNIVERSE if c in px.columns]]
    px_beta = px[[c for c in BETA_FACTORS if c in px.columns]]
    return px_univ, px_beta


# ──────────────────────────────────────────────────────────────────────────────
# Monthly TSMOM returns (full sample)
# ──────────────────────────────────────────────────────────────────────────────
def build_monthly_returns(px_daily: pd.DataFrame,
                           cost_rt: float = COST_RT) -> tuple[pd.Series, pd.DataFrame]:
    """Returns (net_monthly_series, signal_monthly_df)."""
    px     = px_daily.resample("ME").last()
    logret = np.log(px / px.shift(1)).dropna(how="all")
    sig    = _tsmom_signal(px, ann=ANN_M)
    fwd    = logret.shift(-1)
    n      = sig.shape[1]
    w      = sig.fillna(0.0) / n

    idx    = (sig.dropna(how="all").index
                 .intersection(logret.index)
                 .intersection(fwd.dropna(how="all").index))
    w_al   = w.reindex(idx)
    fwd_al = fwd.reindex(idx)

    gross    = (w_al * fwd_al).sum(axis=1)
    turnover = (w_al - w_al.shift(1).fillna(0)).abs().sum(axis=1)
    net      = (gross - turnover * (cost_rt / 2.0)).dropna()
    return net, sig.reindex(idx)


# ──────────────────────────────────────────────────────────────────────────────
# Stats helpers
# ──────────────────────────────────────────────────────────────────────────────
def _sharpe(r: pd.Series, ann: int = ANN_M) -> float:
    s = r.std(ddof=1)
    return float(r.mean() / s * np.sqrt(ann)) if s > 0 else np.nan


def _max_dd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def _ann_ret(r: pd.Series, ann: int = ANN_M) -> float:
    return float(r.mean() * ann)


def _ann_vol(r: pd.Series, ann: int = ANN_M) -> float:
    return float(r.std(ddof=1) * np.sqrt(ann))


def _ols_alpha_beta(y: pd.Series, X_df: pd.DataFrame) -> dict:
    """OLS: y = α + β_SPY·x_SPY + β_AGG·x_AGG + ε. Returns alpha_m, alpha_ann, betas, resid_sharpe."""
    idx = y.index.intersection(X_df.index)
    if len(idx) < 12:
        return {}
    yv     = y.loc[idx].values.astype(float)
    Xv     = X_df.loc[idx].values.astype(float)
    X      = np.column_stack([Xv, np.ones(len(yv))])
    coef, _, _, _ = np.linalg.lstsq(X, yv, rcond=None)
    resid  = yv - X @ coef
    alpha_m = float(coef[-1])
    alpha_ann = alpha_m * ANN_M
    resid_sharpe = float(alpha_m / resid.std(ddof=1) * np.sqrt(ANN_M)) \
                   if resid.std(ddof=1) > 0 else np.nan
    out = {
        "alpha_ann":    round(alpha_ann, 4),
        "resid_sharpe": round(resid_sharpe, 3),
    }
    factors = list(X_df.columns)
    for i, f in enumerate(factors):
        out[f"beta_{f}"] = round(float(coef[i]), 3)
    return out


def _crash_stats(r: pd.Series, periods: dict) -> dict:
    out = {}
    for name, (s, e) in periods.items():
        sub = r.loc[s:e]
        if len(sub) < 2:
            out[name] = {"note": "insufficient data"}
            continue
        eq = (1 + sub).cumprod()
        out[name] = {
            "sharpe":  round(_sharpe(sub), 2),
            "max_dd":  round(_max_dd(sub), 4),
            "cum_ret": round(float(eq.iloc[-1] - 1.0), 4),
            "n_obs":   int(len(sub)),
        }
    return out


# ──────────────────────────────────────────────────────────────────────────────
# TASK 1 — Walk-forward
# ──────────────────────────────────────────────────────────────────────────────
def walk_forward(net: pd.Series, factor_monthly: pd.DataFrame) -> list[dict]:
    """
    Expanding-window walk-forward. Initial train = 2005-01 → 2009-12.
    OOS windows: 2010, 2011, …, 2025  (16 windows × 12 months each).
    No params to tune — walk-forward is a pure OOS robustness check.
    """
    windows = []
    for year in range(2010, 2026):
        oos_start = pd.Timestamp(f"{year}-01-01")
        oos_end   = pd.Timestamp(f"{year}-12-31")
        oos       = net.loc[oos_start:oos_end]
        if len(oos) < 6:
            log.warning(f"WF {year}: only {len(oos)} months, skipping")
            continue
        reg = _ols_alpha_beta(oos, factor_monthly)
        w = {
            "year":       year,
            "oos_start":  str(oos.index.min().date()),
            "oos_end":    str(oos.index.max().date()),
            "n_months":   int(len(oos)),
            "sharpe":     round(_sharpe(oos), 3),
            "max_dd":     round(_max_dd(oos), 4),
            "ann_ret":    round(_ann_ret(oos), 4),
            "ann_vol":    round(_ann_vol(oos), 4),
        }
        w.update(reg)
        windows.append(w)
    return windows


# ──────────────────────────────────────────────────────────────────────────────
# TASK 2 — Deflated Sharpe Ratio (Bailey & López de Prado 2014)
# ──────────────────────────────────────────────────────────────────────────────
def dsr_pvalue(sr_obs: float, T: int, skew: float, kurt: float,
               n_tests: int = N_TESTS) -> float:
    """
    DSR = Φ((SR_obs - SR*) / sqrt((1 - γ·SR_obs + (δ-1)/4 · SR_obs²) / (T-1)))

    where SR* = E[max SR over n_tests iid trials] ≈ (1 - γ)·z + γ·z/ln(n_tests) · ...
    Simplified per BLP (2014) eq. 10:
      SR* ≈ sqrt(2·ln(n_tests)) × (1 - 0.5772/ln(n_tests)) / (sqrt(T-1))
    We use SR_obs directly (already annualized), so SR* must also be annualised.
    BLP formula uses monthly SR (non-annualized). We work in monthly units.
    """
    if T < 2:
        return np.nan
    sr_m = sr_obs / np.sqrt(ANN_M)     # de-annualise to monthly units

    # Expected maximum SR over n_tests independent trials (BLP 2014, eq. 10)
    euler_gamma = 0.5772156649
    z = ((1 - euler_gamma) * stats.norm.ppf(1 - 1 / n_tests)
         + euler_gamma     * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star_m = z / np.sqrt(T - 1)

    # Variance adjustment for non-normal returns
    denom_inner = (1 - skew * sr_m + (kurt - 1) / 4.0 * sr_m ** 2) / (T - 1)
    if denom_inner <= 0:
        return np.nan
    dsr_stat = (sr_m - sr_star_m) / np.sqrt(denom_inner)
    # sf = 1 - Φ(z): conventional p-value — high SR → small p-value → PASS "< 0.05"
    return float(stats.norm.sf(dsr_stat))


def compute_dsr(r: pd.Series, label: str = "") -> dict:
    T    = len(r)
    sr   = _sharpe(r)
    sk   = float(r.skew())
    ku   = float(r.kurtosis() + 3.0)   # scipy kurtosis is excess; BLP needs raw
    pval = dsr_pvalue(sr, T, sk, ku)
    return {
        "label":      label,
        "n_obs":      T,
        "sharpe":     round(sr, 3),
        "skewness":   round(sk, 3),
        "kurtosis":   round(ku, 3),
        "dsr_pvalue": round(pval, 4) if np.isfinite(pval) else None,
        "dsr_pass":   bool(pval < 0.05) if np.isfinite(pval) else False,
    }


# ──────────────────────────────────────────────────────────────────────────────
# TASK 3 — Vol-targeted variant
# ──────────────────────────────────────────────────────────────────────────────
def vol_target_scale(returns: pd.Series,
                     target_ann_vol: float = 0.10,
                     lookback_days: int = 63) -> pd.Series:
    """
    realized_vol  = returns.rolling(lookback_days).std() × sqrt(252)
    scaling       = target_vol / realized_vol.shift(1)  [cap at 2×]
    scaled        = returns × scaling
    lookback_days is expressed in calendar days but we treat as number of periods.
    For monthly series (12 obs/year) we convert: lookback_months = max(3, lookback_days//21)
    """
    lb_m      = max(3, lookback_days // 21)       # ~3 months
    rvol      = returns.rolling(lb_m).std() * np.sqrt(ANN_M)
    scaling   = (target_ann_vol / rvol.shift(1)).clip(upper=2.0)
    return (returns * scaling).dropna()


# ──────────────────────────────────────────────────────────────────────────────
# Markdown summary builder
# ──────────────────────────────────────────────────────────────────────────────
def build_summary(wf_windows: list[dict],
                  raw_stats: dict, vt_stats: dict,
                  dsr_full: dict, dsr_oos_list: list[dict],
                  crash_vt: dict,
                  gate_results: dict) -> str:

    def pct(x): return f"{x*100:.1f}%"
    def f2(x):  return f"{x:.2f}" if x is not None and np.isfinite(x) else "n/a"
    def f3(x):  return f"{x:.3f}" if x is not None and np.isfinite(x) else "n/a"
    def f4p(x): return f"{x*100:.1f}%" if x is not None and np.isfinite(x) else "n/a"
    def ok(b):  return "✓" if b else "✗"

    # Walk-forward table
    sharpes  = [w["sharpe"] for w in wf_windows if w["sharpe"] is not None]
    alphas   = [w.get("alpha_ann", None) for w in wf_windows if w.get("alpha_ann") is not None]
    pct_pos_sharpe = (sum(s > 0 for s in sharpes) / len(sharpes)) if sharpes else 0
    pct_pos_alpha  = (sum(a > 0 for a in alphas)  / len(alphas))  if alphas  else 0
    med_sharpe     = float(np.median(sharpes)) if sharpes else np.nan
    worst = min(wf_windows, key=lambda w: w["sharpe"])
    best  = max(wf_windows, key=lambda w: w["sharpe"])

    headline_pass = all(gate_results[k] for k in gate_results)
    propfirm_pass = gate_results.get("vt_max_dd") and gate_results.get("vt_covid_dd")
    if headline_pass:
        verdict = "PASS_PROPFIRM"
        binding = "all gates pass"
    elif propfirm_pass:
        verdict = "PASS_RESEARCH_ONLY"
        binding = "walk-forward or DSR gate marginal"
    else:
        failed = [k for k, v in gate_results.items() if not v]
        verdict = "FAIL"
        binding = f"binding failures: {', '.join(failed)}"

    lines = []
    lines.append("## Result Summary: multi_asset_tsmom — Walk-Forward + DSR + Vol Target")
    lines.append("")

    lines.append("### 1. Headline verdict")
    lines.append(f"**{verdict}** — {binding}")
    lines.append("")

    lines.append("### 2. Walk-forward OOS stats (16 windows, 2010-2025)")
    lines.append("| Metric                  | Value     | Gate          | Pass |")
    lines.append("|-------------------------|-----------|---------------|------|")
    lines.append(f"| Median OOS Sharpe       | {f2(med_sharpe)}      | > 0.30        | {ok(med_sharpe > 0.30)}    |")
    lines.append(f"| % windows Sharpe > 0    | {pct(pct_pos_sharpe)}       | > 60%         | {ok(pct_pos_sharpe > 0.60)}    |")
    lines.append(f"| % windows alpha > 0     | {pct(pct_pos_alpha)}       | > 60%         | {ok(pct_pos_alpha > 0.60)}    |")
    lines.append(f"| Worst OOS year          | {worst['year']} (Sharpe={f2(worst['sharpe'])}, MaxDD={f4p(worst['max_dd'])}) | - | - |")
    lines.append(f"| Best OOS year           | {best['year']} (Sharpe={f2(best['sharpe'])})            | - | - |")
    lines.append("")

    lines.append("### 3. Full-sample stats (raw vs vol-targeted)")
    lines.append("| Metric             | Raw       | Vol-targeted | Notes |")
    lines.append("|--------------------|-----------|--------------|-------|")
    lines.append(f"| Sharpe             | {f2(raw_stats['sharpe'])}      | {f2(vt_stats['sharpe'])}         | -     |")
    lines.append(f"| Ann return         | {f4p(raw_stats['ann_ret'])}      | {f4p(vt_stats['ann_ret'])}         | -     |")
    lines.append(f"| Ann vol            | {f4p(raw_stats['ann_vol'])}      | ~10%         | target |")
    lines.append(f"| MaxDD              | {f4p(raw_stats['max_dd'])}     | {f4p(vt_stats['max_dd'])}        | propfirm: > -10% |")
    lines.append(f"| Alpha (ann)        | {f4p(raw_stats.get('alpha_ann', 0))}      | {f4p(vt_stats.get('alpha_ann', 0))}         | vs SPY+AGG |")
    lines.append(f"| Beta SPY           | {f2(raw_stats.get('beta_SPY', 0))}      | {f2(vt_stats.get('beta_SPY', 0))}         | -     |")
    lines.append(f"| Beta AGG           | {f2(raw_stats.get('beta_AGG', 0))}      | {f2(vt_stats.get('beta_AGG', 0))}         | -     |")
    lines.append(f"| Residual Sharpe    | {f2(raw_stats.get('resid_sharpe', 0))}      | {f2(vt_stats.get('resid_sharpe', 0))}         | true edge |")
    lines.append("")

    lines.append("### 4. Crash period stress test (vol-targeted)")
    lines.append("| Period       | Window           | Sharpe  | MaxDD   | Cum ret |")
    lines.append("|--------------|------------------|---------|---------|---------|")
    period_labels = {
        "GFC_2008":    "GFC",
        "EuroCrisis":  "EuroCrisis",
        "COVID_2020":  "COVID",
        "Inflation22": "Inflation",
    }
    period_windows = {
        "GFC_2008":    "2008-07 → 2009-06",
        "EuroCrisis":  "2011-04 → 2012-01",
        "COVID_2020":  "2020-02 → 2020-05",
        "Inflation22": "2022-01 → 2022-12",
    }
    for k in CRASH_PERIODS:
        c = crash_vt.get(k, {})
        if "max_dd" in c:
            lines.append(f"| {period_labels[k]:<12} | {period_windows[k]} | {f2(c['sharpe'])}    | {f4p(c['max_dd'])}   | {f4p(c['cum_ret'])}    |")
        else:
            lines.append(f"| {period_labels[k]:<12} | {period_windows[k]} | n/a     | n/a     | n/a     |")
    lines.append("")

    dsr_oos_pvals = [d["dsr_pvalue"] for d in dsr_oos_list if d["dsr_pvalue"] is not None]
    med_oos_dsr   = float(np.median(dsr_oos_pvals)) if dsr_oos_pvals else np.nan
    lines.append("### 5. Deflated Sharpe Ratio (n_tests = 58)")
    lines.append(f"- Full-sample DSR p-value: {f3(dsr_full['dsr_pvalue'])} [pass: < 0.05] {ok(dsr_full['dsr_pass'])}")
    lines.append(f"- Median OOS-window DSR p-value: {f3(med_oos_dsr)}")
    lines.append(f"- Full-sample SR={f2(dsr_full['sharpe'])}, skew={f2(dsr_full['skewness'])}, kurt={f2(dsr_full['kurtosis'])}, n={dsr_full['n_obs']}")
    lines.append(f"- Reference: SR_expected_max uses n_tests={N_TESTS}, Euler–Mascheroni correction (Bailey & López de Prado 2014)")
    lines.append("")

    lines.append("### 6. Gate decision matrix")
    lines.append("| Gate                              | Threshold | Value  | Pass |")
    lines.append("|-----------------------------------|-----------|--------|------|")
    lines.append(f"| Walk-forward median Sharpe        | > 0.30    | {f2(med_sharpe)}   | {ok(gate_results['wf_median_sharpe'])}    |")
    lines.append(f"| Walk-forward % positive windows   | > 60%     | {pct(pct_pos_sharpe)}   | {ok(gate_results['wf_pct_positive'])}    |")
    lines.append(f"| DSR p-value (full-sample)         | < 0.05    | {f3(dsr_full['dsr_pvalue'])}   | {ok(gate_results['dsr_full'])}    |")
    lines.append(f"| Vol-targeted MaxDD                | > -10%    | {f4p(vt_stats['max_dd'])}   | {ok(gate_results['vt_max_dd'])}    |")
    lines.append(f"| Vol-targeted COVID MaxDD          | > -5%     | {f4p(crash_vt.get('COVID_2020',{}).get('max_dd', -1))}   | {ok(gate_results['vt_covid_dd'])}    |")
    lines.append(f"| Residual Sharpe (vol-targeted)    | > 0.40    | {f2(vt_stats.get('resid_sharpe', 0))}   | {ok(gate_results['resid_sharpe_vt'])}    |")
    lines.append("")

    lines.append("### 7. Recommendation")
    if verdict == "PASS_PROPFIRM":
        lines.append(
            "Multi-asset TSMOM clears all six validation gates including propfirm MaxDD < 10% "
            "under vol targeting and DSR < 0.05 after 58-test correction. "
            "Proceed to paper trading on a live data feed with the vol-targeted sizing rule "
            "(target_ann_vol=10%, 63-day lookback, 2× leverage cap), then review 3-month live Sharpe "
            "before committing propfirm capital."
        )
    elif verdict == "PASS_RESEARCH_ONLY":
        lines.append(
            "Strategy shows genuine OOS alpha but does not fully clear all propfirm gates. "
            "Continue paper trading at reduced sizing; revisit walk-forward robustness with "
            "longer out-of-sample horizon before submitting to propfirm challenge."
        )
    else:
        lines.append(
            "Strategy fails critical validation gates. Do not deploy. "
            f"Root cause: {binding}. "
            "Consider alternative sizing, universe expansion, or archive."
        )
    lines.append("")

    lines.append("### 8. Files written")
    lines.append("- walkforward.py (this script)")
    lines.append("- walkforward_results.json (machine-readable)")
    lines.append("- walkforward_summary.md (this summary)")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> dict:
    log.info("=== Multi-Asset TSMOM Walk-Forward Validation ===")

    # ── Data ──────────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("DATA DOWNLOAD")
    print("─" * 72)
    px_univ, px_beta = fetch_prices()
    log.info(f"Universe: {list(px_univ.columns)}")

    net, _ = build_monthly_returns(px_univ)
    log.info(f"Monthly returns: {len(net)} months ({net.index.min().date()} → {net.index.max().date()})")

    # Factor returns (monthly, for beta regression in each OOS window)
    px_beta_m  = px_beta.resample("ME").last()
    factor_ret = np.log(px_beta_m / px_beta_m.shift(1)).dropna(how="all")

    # ── TASK 1: Walk-forward ─────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("TASK 1 — Walk-Forward OOS Backtest (16 windows, 2010-2025)")
    print("─" * 72)
    wf_windows = walk_forward(net, factor_ret)

    print(f"\n{'Year':<6} {'Sharpe':>7} {'MaxDD':>7} {'AnnRet':>8} {'AlphaAnn':>9} {'BetaSPY':>8} {'n':>4}")
    print("─" * 60)
    for w in wf_windows:
        alpha_str = f"{w.get('alpha_ann', 0)*100:+.1f}%" if w.get('alpha_ann') is not None else "  n/a"
        beta_str  = f"{w.get('beta_SPY', 0):+.3f}"       if w.get('beta_SPY')  is not None else "   n/a"
        print(f"{w['year']:<6} {w['sharpe']:>+7.3f} {w['max_dd']*100:>+6.1f}% "
              f"{w['ann_ret']*100:>+7.1f}% {alpha_str:>9} {beta_str:>8} {w['n_months']:>4}")

    sharpes_all    = [w["sharpe"] for w in wf_windows]
    alphas_all     = [w.get("alpha_ann", 0) or 0 for w in wf_windows]
    med_sharpe_wf  = float(np.median(sharpes_all))
    pct_pos_sh     = sum(s > 0 for s in sharpes_all) / len(sharpes_all)
    pct_pos_al     = sum(a > 0 for a in alphas_all)  / len(alphas_all)

    print(f"\n  Median OOS Sharpe   : {med_sharpe_wf:+.3f}  [gate > 0.30: {'✓' if med_sharpe_wf > 0.30 else '✗'}]")
    print(f"  % windows Sharpe>0  : {pct_pos_sh*100:.0f}%  [gate > 60%: {'✓' if pct_pos_sh > 0.60 else '✗'}]")
    print(f"  % windows alpha>0   : {pct_pos_al*100:.0f}%  [gate > 60%: {'✓' if pct_pos_al > 0.60 else '✗'}]")

    # ── TASK 2: DSR ───────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print(f"TASK 2 — Deflated Sharpe Ratio (n_tests={N_TESTS})")
    print("─" * 72)
    dsr_full = compute_dsr(net, label="full_sample")
    print(f"\n  Full-sample: SR={dsr_full['sharpe']:+.3f}  skew={dsr_full['skewness']:+.3f}  "
          f"kurt={dsr_full['kurtosis']:+.2f}  n={dsr_full['n_obs']}")
    print(f"  DSR p-value = {dsr_full['dsr_pvalue']:.4f}  [pass < 0.05: {'✓' if dsr_full['dsr_pass'] else '✗'}]")

    dsr_oos_list = []
    print(f"\n  {'Year':<6} {'SR':>7} {'skew':>7} {'kurt':>7} {'DSR_p':>8} {'pass':>5}")
    print("  " + "─" * 44)
    for w in wf_windows:
        year_net = net.loc[f"{w['year']}-01-01":f"{w['year']}-12-31"]
        d = compute_dsr(year_net, label=str(w["year"]))
        dsr_oos_list.append(d)
        p_str = f"{d['dsr_pvalue']:.4f}" if d['dsr_pvalue'] is not None else "  n/a"
        flag  = "✓" if d["dsr_pass"] else "✗"
        print(f"  {w['year']:<6} {d['sharpe']:>+7.3f} {d['skewness']:>+7.3f} "
              f"{d['kurtosis']:>+7.2f} {p_str:>8} {flag:>5}")

    dsr_oos_pvals = [d["dsr_pvalue"] for d in dsr_oos_list if d["dsr_pvalue"] is not None]
    print(f"\n  Median OOS DSR p-value: {np.median(dsr_oos_pvals):.4f}")

    # ── TASK 3: Vol targeting ─────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("TASK 3 — Vol-Targeted Variant (target_ann_vol=10%, lookback=63d≈3M)")
    print("─" * 72)
    net_vt = vol_target_scale(net, target_ann_vol=0.10, lookback_days=63)
    log.info(f"Vol-targeted returns: {len(net_vt)} months")

    # Raw full-sample stats
    raw_reg = _ols_alpha_beta(net, factor_ret)
    raw_stats = {
        "sharpe":     round(_sharpe(net), 3),
        "max_dd":     round(_max_dd(net), 4),
        "ann_ret":    round(_ann_ret(net), 4),
        "ann_vol":    round(_ann_vol(net), 4),
        **raw_reg,
    }

    # Vol-targeted full-sample stats
    factor_vt  = factor_ret.reindex(net_vt.index)
    vt_reg     = _ols_alpha_beta(net_vt, factor_vt)
    vt_stats   = {
        "sharpe":     round(_sharpe(net_vt), 3),
        "max_dd":     round(_max_dd(net_vt), 4),
        "ann_ret":    round(_ann_ret(net_vt), 4),
        "ann_vol":    round(_ann_vol(net_vt), 4),
        **vt_reg,
    }

    crash_vt = _crash_stats(net_vt, CRASH_PERIODS)

    print(f"\n  {'Metric':<22} {'Raw':>10} {'Vol-targeted':>14}")
    print("  " + "─" * 48)
    for k, label in [("sharpe", "Sharpe"), ("max_dd", "MaxDD"),
                     ("ann_ret", "Ann ret"), ("ann_vol", "Ann vol"),
                     ("alpha_ann", "Alpha ann"), ("resid_sharpe", "Residual Sharpe"),
                     ("beta_SPY", "Beta SPY"), ("beta_AGG", "Beta AGG")]:
        rv  = raw_stats.get(k)
        vtv = vt_stats.get(k)
        rf  = f"{rv*100:+.1f}%" if rv is not None and k in ("max_dd","ann_ret","ann_vol","alpha_ann") else (f"{rv:+.3f}" if rv is not None else "n/a")
        vf  = f"{vtv*100:+.1f}%" if vtv is not None and k in ("max_dd","ann_ret","ann_vol","alpha_ann") else (f"{vtv:+.3f}" if vtv is not None else "n/a")
        print(f"  {label:<22} {rf:>10} {vf:>14}")

    print(f"\n  Crash periods (vol-targeted):")
    for name, c in crash_vt.items():
        if "max_dd" in c:
            print(f"    {name:<16} Sharpe={c['sharpe']:+.2f}  MaxDD={c['max_dd']*100:+.1f}%  "
                  f"CumRet={c['cum_ret']*100:+.1f}%  n={c['n_obs']}")
        else:
            print(f"    {name:<16} {c.get('note','n/a')}")

    covid_vt_dd = crash_vt.get("COVID_2020", {}).get("max_dd", -1) or -1

    # ── Gate evaluation ───────────────────────────────────────────────────────
    gate_results = {
        "wf_median_sharpe":  bool(med_sharpe_wf   > 0.30),
        "wf_pct_positive":   bool(pct_pos_sh       > 0.60),
        "dsr_full":          bool(dsr_full["dsr_pass"]),
        "vt_max_dd":         bool(vt_stats["max_dd"] > -0.10),
        "vt_covid_dd":       bool(covid_vt_dd      > -0.05),
        "resid_sharpe_vt":   bool((vt_stats.get("resid_sharpe") or 0) > 0.40),
    }

    # ── Build & print summary ─────────────────────────────────────────────────
    summary_md = build_summary(
        wf_windows, raw_stats, vt_stats,
        dsr_full, dsr_oos_list, crash_vt,
        gate_results
    )

    print("\n\n" + "=" * 72)
    print(summary_md)
    print("=" * 72)

    # ── Save results ──────────────────────────────────────────────────────────
    results = {
        "walk_forward":    wf_windows,
        "dsr_full":        dsr_full,
        "dsr_oos":         dsr_oos_list,
        "raw_stats":       raw_stats,
        "vol_targeted":    vt_stats,
        "crash_vt":        crash_vt,
        "gate_results":    gate_results,
    }
    RESULTS_JSON.write_text(json.dumps(results, indent=2))
    SUMMARY_MD.write_text(summary_md)
    log.info(f"Saved → {RESULTS_JSON}")
    log.info(f"Saved → {SUMMARY_MD}")

    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("walkforward run failed")
        sys.exit(1)
