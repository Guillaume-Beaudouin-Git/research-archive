"""A1 — Diversified Multi-Horizon TSMOM (FROZEN spec, mission 2026-06-05).

Single-pass engine. Reproducible: numpy seed = 42 for RandomSign 500 seeds.

Pipeline (canonical MOP/HOP monthly rebalance):
- Universe: ~24 yfinance continuous futures (4 classes), drop <8y.
- Daily returns from Close; ex-ante per-instr vol = rolling_std(63d) × √252, lagged 1 d.
- Signal (FROZEN): S_i = mean(sign(cumret_21), sign(cumret_63), sign(cumret_252)),
  evaluated at the last business day of month t-1.
- Per-instrument pre-scale position: p_i = S_i × (sigma_target_inst / sigma_i).
- Portfolio vol target (2nd stage, MONTHLY): scale to 10% ann. realized port vol
  using a 63-business-day rolling std of the "pre-scaled" port returns, lagged
  1 day, sampled at month-end.
- Position held CONSTANT through month t. Scale fixed at start of month.
- Cost: 1.5 bps RT × |Δposition_notional| at monthly rebal only.

Ablations:
- BuyHold: S_i ≡ +1.
- RandomSign: S_i ∈ {-1,+1} iid per instrument per month, 500 seeds.

Outputs:
- outputs/mtf/a1_returns.parquet (monthly net returns: TSMOM, BH, RS_mean)
- outputs/mtf/a1_per_market_stats.parquet (per-instrument Sharpe, t-stat)
- outputs/mtf/a1_diagnostics.json (cross-checks, distributions)
- outputs/mtf/a1_rs_distribution.parquet (Sharpe per RS seed)
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

# ------------------------- constants -----------------------------
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "mtf_survey" / "raw"
OUT = ROOT / "outputs" / "mtf"
OUT.mkdir(parents=True, exist_ok=True)

UNIVERSE = {
    "equity": ["ES=F", "NQ=F", "YM=F", "RTY=F"],
    "bonds":  ["ZT=F", "ZF=F", "ZN=F", "ZB=F"],
    "fx":     ["6E=F", "6J=F", "6B=F", "6A=F", "6C=F", "6S=F"],
    "commod": ["CL=F", "NG=F", "GC=F", "SI=F", "HG=F",
               "ZC=F", "ZW=F", "ZS=F", "KC=F", "SB=F"],
}
ALL_TICKERS = [t for v in UNIVERSE.values() for t in v]
TICKER_TO_CLASS = {t: c for c, ts in UNIVERSE.items() for t in ts}

# FROZEN spec parameters
VOL_WIN = 63
HORIZONS = [21, 63, 252]
SIGMA_TARGET_INST = 0.10 / np.sqrt(len(ALL_TICKERS))
PORT_VOL_TARGET = 0.10
PORT_VOL_WIN = 63
COST_BPS_RT = 1.5
MIN_YEARS_REQUIRED = 8
RS_SEEDS = 500
SEED = 42
MIN_ACTIVE_FRAC = 0.5  # warmup gate: need >= 50% of universe with valid sigma & signal
WARMUP_BUFFER_BD = 63  # plus 63 business days of valid port-vol data before counting P&L


# ------------------------- IO ------------------------------------
def _clean_outlier_ticks(close: pd.Series, high: pd.Series, low: pd.Series,
                         max_daily_abs_ret: float = 0.30) -> tuple[pd.Series, int]:
    """Filter clearly broken closes (data errors) before computing returns.

    Heuristic: if |ret| > max_daily_abs_ret AND Close is not in [Low/2, High*2]
    (i.e. close is wildly inconsistent with intraday range), replace Close
    with the previous close. This is data cleaning — yfinance is known to
    occasionally emit decimal-misplaced ticks on older futures contracts
    (cf. 6J=F on 2001-12-17 where Close=0.000783 vs Low=0.00782).
    """
    s = close.copy()
    n_fixes = 0
    # First pass: clip closes that fall outside [Low/2, High*2]
    bad_range = (s < low.where(low.notna(), s) * 0.5) | (s > high.where(high.notna(), s) * 2.0)
    if bad_range.any():
        s = s.where(~bad_range, np.nan)
        n_fixes += int(bad_range.sum())
    s = s.ffill()
    # Second pass: if a daily return still exceeds threshold AND the corresponding
    # next-day return is roughly its inverse (round-trip pattern), neutralize the
    # outlier by ffill from the prior close.
    r = s.pct_change()
    suspicious = r.abs() > max_daily_abs_ret
    if suspicious.any():
        idx = s.index
        for i, is_bad in enumerate(suspicious.values):
            if not is_bad or i == 0:
                continue
            # If next day's return is the rough inverse (round-trip), it's a tick error
            if i + 1 < len(idx):
                next_r = r.iloc[i + 1]
                if pd.notna(next_r) and pd.notna(r.iloc[i]) and (r.iloc[i] * next_r < -0.5):
                    s.iloc[i] = s.iloc[i - 1]
                    n_fixes += 1
    return s, n_fixes


def load_close(ticker: str) -> pd.Series:
    p = RAW / f"prices_{ticker.replace('=', '_').replace('/', '_')}.parquet"
    if not p.exists():
        return pd.Series(dtype=float, name=ticker)
    df = pd.read_parquet(p)
    cols = {c.lower(): c for c in df.columns}
    if "close" not in cols:
        return pd.Series(dtype=float, name=ticker)
    close = df[cols["close"]].astype(float)
    high = df[cols.get("high", cols["close"])].astype(float) if "high" in cols else close
    low = df[cols.get("low", cols["close"])].astype(float) if "low" in cols else close
    close = close[~close.index.duplicated(keep="last")].sort_index()
    high = high.reindex(close.index)
    low = low.reindex(close.index)
    close_clean, n_fixes = _clean_outlier_ticks(close, high, low)
    if n_fixes > 0:
        print(f"  [clean] {ticker}: replaced {n_fixes} outlier tick(s)")
    s = close_clean.rename(ticker).dropna()
    return s


def load_panel() -> tuple[pd.DataFrame, dict]:
    series, excluded = [], {}
    for t in ALL_TICKERS:
        s = load_close(t)
        if s.empty:
            excluded[t] = "no_data"
            continue
        years = (s.index.max() - s.index.min()).days / 365.25
        if years < MIN_YEARS_REQUIRED:
            excluded[t] = f"only_{years:.1f}y"
            continue
        series.append(s)
    panel = pd.concat(series, axis=1).sort_index()
    bd = pd.bdate_range(panel.index.min(), panel.index.max())
    panel = panel.reindex(bd)
    included = {t: {"start": str(panel[t].first_valid_index().date()),
                    "end":   str(panel[t].last_valid_index().date()),
                    "n":     int(panel[t].notna().sum()),
                    "class": TICKER_TO_CLASS[t]}
                for t in panel.columns}
    return panel, {"included": included, "excluded": excluded}


# ------------------------- signal & sizing -----------------------
def daily_returns(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.pct_change()


def vol_ex_ante_daily(rets: pd.DataFrame) -> pd.DataFrame:
    sd = rets.rolling(VOL_WIN, min_periods=VOL_WIN).std()
    return (sd * np.sqrt(252)).shift(1)


def signal_tsmom_daily(panel: pd.DataFrame) -> pd.DataFrame:
    """S_t = mean(sign(cumret_k_t)) for k ∈ {21,63,252}.

    pct_change(k) at day t uses close_t / close_{t-k} - 1, which is the cumulative
    return through close of day t. We will sample this at month-end-of-prev-month
    and apply to next month (the monthly shift below provides the L1 guarantee).
    """
    parts = []
    for k in HORIZONS:
        s_k = np.sign(panel.pct_change(k))
        parts.append(s_k)
    return sum(parts) / len(parts)


def to_month_end_grid(daily: pd.DataFrame, panel_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Sample at last business day of each month."""
    return daily.resample("BME").last()


# ------------------------- back-test core ------------------------
def build_monthly_positions(panel: pd.DataFrame,
                            rets: pd.DataFrame,
                            sigma_daily: pd.DataFrame,
                            S_daily: pd.DataFrame) -> pd.DataFrame:
    """Construct un-scaled monthly positions (one row per month-end).

    pos_inst_monthly[t] = position to hold during month t+1, computed at end of month t.
    """
    sigma_eom = sigma_daily.resample("BME").last()
    S_eom = S_daily.resample("BME").last()
    # Position computed from end-of-month info
    pos_eom = S_eom * (SIGMA_TARGET_INST / sigma_eom)
    # If a contract has no return data at this month-end, zero it (cannot trade)
    has_ret = rets.resample("BME").last().notna()
    pos_eom = pos_eom.where(has_ret, 0.0)
    pos_eom = pos_eom.fillna(0.0)
    return pos_eom


def daily_position_from_monthly(monthly_pos_eom: pd.DataFrame,
                                panel_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Apply position computed at end-of-month M starting first business day of M+1.

    Reindex pos_eom forward by one business day, then ffill onto daily grid.
    This guarantees L1 (no same-bar fill) without double-lagging.
    """
    pos_applied = monthly_pos_eom.copy()
    pos_applied.index = pos_applied.index + pd.offsets.BDay(1)
    return pos_applied.reindex(panel_index, method="ffill").fillna(0.0)


def realized_port_vol_monthly(daily_pos: pd.DataFrame,
                              rets: pd.DataFrame) -> pd.Series:
    """Compute trailing-63d realized port vol from PRE-SCALED port returns, sampled
    at month-end. Used by the 2nd-stage vol-target.
    """
    r_pre = (daily_pos * rets).sum(axis=1)
    sd = r_pre.rolling(PORT_VOL_WIN, min_periods=PORT_VOL_WIN).std() * np.sqrt(252)
    # Sample at month-end
    sd_eom = sd.resample("BME").last()
    return sd_eom


def vol_target_scale_monthly(sd_eom: pd.Series) -> pd.Series:
    """Scale = PORT_VOL_TARGET / realized vol (capped to avoid blow-ups)."""
    scale = (PORT_VOL_TARGET / sd_eom).replace([np.inf, -np.inf], np.nan)
    scale = scale.clip(upper=10.0)  # mild numerical safety; rarely triggers in practice
    return scale


def compute_effective_start(panel: pd.DataFrame,
                            rets: pd.DataFrame,
                            sigma_daily: pd.DataFrame,
                            S_daily: pd.DataFrame) -> pd.Timestamp:
    """First daily date when at least MIN_ACTIVE_FRAC of universe has both
    a valid sigma and a valid signal, plus WARMUP_BUFFER_BD more business days.
    """
    n_total = len(panel.columns)
    has_sig = (sigma_daily.notna() & S_daily.notna()).sum(axis=1)
    enough = (has_sig >= MIN_ACTIVE_FRAC * n_total)
    if not enough.any():
        return panel.index.max()
    first_ok = enough[enough].index[0]
    # Add WARMUP_BUFFER_BD business days
    pos = panel.index.get_loc(first_ok) if first_ok in panel.index else 0
    pos2 = min(pos + WARMUP_BUFFER_BD, len(panel.index) - 1)
    return panel.index[pos2]


def run_portfolio(panel: pd.DataFrame,
                  rets: pd.DataFrame,
                  sigma_daily: pd.DataFrame,
                  S_daily: pd.DataFrame,
                  effective_start: pd.Timestamp | None = None):
    """Returns:
       monthly_net : pd.Series of monthly net returns
       monthly_gross : pd.Series of monthly gross returns
       monthly_cost : pd.Series of monthly costs
       scaled_pos_monthly_eom : DataFrame, scaled positions at each month-end (applied next month)
    """
    pos_monthly_eom = build_monthly_positions(panel, rets, sigma_daily, S_daily)
    pos_daily_pre = daily_position_from_monthly(pos_monthly_eom, panel.index)

    # 2nd-stage: monthly vol-target scale, applied starting next BDay (consistent with pos lag)
    sd_eom = realized_port_vol_monthly(pos_daily_pre, rets)
    scale_eom = vol_target_scale_monthly(sd_eom)
    scale_eom_applied = scale_eom.copy()
    scale_eom_applied.index = scale_eom_applied.index + pd.offsets.BDay(1)
    scale_daily = scale_eom_applied.reindex(panel.index, method="ffill").fillna(0.0)

    scaled_pos_daily = pos_daily_pre.mul(scale_daily, axis=0)

    # Gross daily
    gross_daily = (scaled_pos_daily * rets).sum(axis=1)

    # Monthly aggregation
    gross_monthly = (1 + gross_daily.fillna(0)).resample("ME").prod() - 1

    # Cost: only at monthly rebal — |Δscaled_pos| at month-end
    scaled_pos_eom = scaled_pos_daily.resample("BME").last()
    # Position notional change between consecutive month-ends.
    # Δ is between "what we hold today" (just rebalanced) vs "what we held last month".
    dnotional = scaled_pos_eom.diff().abs().sum(axis=1).fillna(0.0)
    cost_per_rebal = dnotional * (COST_BPS_RT / 10_000.0)
    # Map BME index back to ME index for subtraction
    cost_monthly = cost_per_rebal.copy()
    cost_monthly.index = cost_monthly.index + pd.offsets.MonthEnd(0)
    cost_monthly = cost_monthly.reindex(gross_monthly.index).fillna(0.0)

    net_monthly = gross_monthly - cost_monthly

    # Truncate output to effective_start (warmup-period P&L is unreliable & is excluded)
    if effective_start is not None:
        # First month strictly AFTER effective_start
        net_monthly = net_monthly[net_monthly.index > effective_start]
        gross_monthly = gross_monthly[gross_monthly.index > effective_start]
        cost_monthly = cost_monthly[cost_monthly.index > effective_start]

    return {
        "monthly_net":   net_monthly,
        "monthly_gross": gross_monthly,
        "monthly_cost":  cost_monthly,
        "scaled_pos_eom": scaled_pos_eom,
        "scale_eom_applied": scale_eom_applied,
        "pos_monthly_eom_unscaled": pos_monthly_eom,
        "gross_daily": gross_daily,
        "scaled_pos_daily": scaled_pos_daily,
    }


# ------------------------- ablations -----------------------------
def run_tsmom(panel, rets, sigma_daily, effective_start=None):
    S = signal_tsmom_daily(panel)
    if effective_start is None:
        effective_start = compute_effective_start(panel, rets, sigma_daily, S)
    return run_portfolio(panel, rets, sigma_daily, S, effective_start), effective_start


def run_buyhold(panel, rets, sigma_daily, effective_start=None):
    # BH "signal" exists wherever sigma exists
    S = pd.DataFrame(np.where(sigma_daily.notna(), 1.0, np.nan),
                     index=panel.index, columns=panel.columns)
    if effective_start is None:
        effective_start = compute_effective_start(panel, rets, sigma_daily, S)
    return run_portfolio(panel, rets, sigma_daily, S, effective_start), effective_start


def run_randomsign_one(panel, rets, sigma_daily, rng, effective_start=None):
    """Single seed: random sign per (instrument, month-end)."""
    sigma_eom = sigma_daily.resample("BME").last()
    months_idx = sigma_eom.index
    signs = rng.choice([-1.0, 1.0], size=(len(months_idx), len(panel.columns)))
    S_eom = pd.DataFrame(signs, index=months_idx, columns=panel.columns)
    # Mask: only assign signs where sigma is valid (otherwise NaN)
    S_eom = S_eom.where(sigma_eom.notna(), np.nan)
    S_daily = S_eom.reindex(panel.index, method="ffill")
    return run_portfolio(panel, rets, sigma_daily, S_daily, effective_start)


def run_randomsign_suite(panel, rets, sigma_daily, n_seeds=RS_SEEDS, base_seed=SEED,
                         effective_start=None):
    rng = np.random.default_rng(base_seed)
    out = {}
    sharpes = []
    for i in range(n_seeds):
        res = run_randomsign_one(panel, rets, sigma_daily, rng, effective_start)
        s = res["monthly_net"]
        out[i] = s
        sharpes.append(sharpe_ann(s, ppy=12))
    df = pd.DataFrame(out)
    return df, np.array(sharpes)


# ------------------------- metrics -------------------------------
def sharpe_ann(daily: pd.Series, ppy: int = 252) -> float:
    x = daily.dropna()
    if x.std() == 0 or len(x) < 2:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(ppy))


def maxdd(daily: pd.Series) -> float:
    eq = (1 + daily.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


# ------------------------- main ----------------------------------
def main():
    print("=== A1 engine (v2 monthly-clean) ===", flush=True)
    panel, meta_panel = load_panel()
    print(f"Universe retained: {len(panel.columns)} instruments")
    rets = daily_returns(panel)
    sigma_daily = vol_ex_ante_daily(rets)

    print("Running TSMOM…", flush=True)
    res_tsmom, eff_start = run_tsmom(panel, rets, sigma_daily)
    print(f"Effective start (≥{int(MIN_ACTIVE_FRAC*100)}% active + {WARMUP_BUFFER_BD} BD): {eff_start.date()}")
    m_tsmom = res_tsmom["monthly_net"]

    print("Running BuyHold…", flush=True)
    res_bh, _ = run_buyhold(panel, rets, sigma_daily, effective_start=eff_start)
    m_bh = res_bh["monthly_net"]

    print(f"Running RandomSign × {RS_SEEDS}…", flush=True)
    rs_df, rs_sharpes = run_randomsign_suite(panel, rets, sigma_daily, effective_start=eff_start)
    m_rs_mean = rs_df.mean(axis=1)

    # Align all on common monthly index
    common = m_tsmom.dropna().index.intersection(m_bh.dropna().index)
    m_tsmom = m_tsmom.loc[common]
    m_bh = m_bh.loc[common]
    m_rs_mean = m_rs_mean.reindex(common)
    rs_df = rs_df.reindex(common)

    out_returns = pd.DataFrame({
        "TSMOM_net_monthly": m_tsmom,
        "BH_net_monthly":    m_bh,
        "RS_mean_net_monthly": m_rs_mean,
    })
    out_returns.to_parquet(OUT / "a1_returns.parquet")
    print(f"Saved {OUT/'a1_returns.parquet'}: {out_returns.shape}")
    rs_df.to_parquet(OUT / "a1_rs_seeds.parquet")
    pd.Series(rs_sharpes, name="rs_sharpe_ann").to_frame().to_parquet(OUT / "a1_rs_sharpes.parquet")

    # Per-market stats (TSMOM contributions; using scaled daily pos)
    print("Per-market TSMOM stats…", flush=True)
    scaled_pos_daily = res_tsmom["scaled_pos_daily"]
    per_market = {}
    for c in panel.columns:
        contrib_d = (scaled_pos_daily[c].fillna(0) * rets[c].fillna(0))
        contrib_m = ((1 + contrib_d).resample("ME").prod() - 1).reindex(common)
        try:
            x = contrib_m.dropna().values
            if len(x) > 12:
                X = np.ones_like(x)
                mod = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
                t_alpha = float(mod.tvalues[0])
                m_alpha = float(mod.params[0])
            else:
                t_alpha, m_alpha = float("nan"), float("nan")
        except Exception:
            t_alpha, m_alpha = float("nan"), float("nan")
        per_market[c] = {
            "class": TICKER_TO_CLASS[c],
            "sharpe_ann": sharpe_ann(contrib_m, ppy=12),
            "alpha_monthly": m_alpha,
            "t_HAC6": t_alpha,
            "n_months": int(contrib_m.notna().sum()),
        }
    per_market_df = pd.DataFrame(per_market).T
    per_market_df.to_parquet(OUT / "a1_per_market_stats.parquet")
    print(f"Saved {OUT/'a1_per_market_stats.parquet'}")

    # Cross-check vs AQR
    aqr_csv = RAW / "aqr_tsmom_sheet_TSMOM_factors.csv"
    aqr_df = pd.read_csv(aqr_csv, skiprows=11)
    aqr_df["DATE"] = pd.to_datetime(aqr_df["DATE"])
    aqr_df = aqr_df.set_index("DATE").sort_index()
    aqr_full = aqr_df["TSMOM"].astype(float).rename("AQR_TSMOM_monthly")
    aqr_eom = aqr_full.copy()
    aqr_eom.index = aqr_eom.index + pd.offsets.MonthEnd(0)
    m_tsmom_eom = m_tsmom.copy()
    m_tsmom_eom.index = m_tsmom_eom.index + pd.offsets.MonthEnd(0)
    joined = pd.concat([m_tsmom_eom.rename("us"), aqr_eom], axis=1).dropna()
    cross_check = {
        "n_months_overlap": int(joined.shape[0]),
        "overlap_start": str(joined.index.min().date()) if not joined.empty else None,
        "overlap_end":   str(joined.index.max().date()) if not joined.empty else None,
        "corr_us_vs_aqr": float(joined["us"].corr(joined["AQR_TSMOM_monthly"])) if not joined.empty else float("nan"),
        "us_sharpe_overlap_ann": sharpe_ann(joined["us"], ppy=12) if not joined.empty else float("nan"),
        "aqr_sharpe_overlap_ann": sharpe_ann(joined["AQR_TSMOM_monthly"], ppy=12) if not joined.empty else float("nan"),
    }
    print("Cross-check vs AQR:", cross_check)

    diag = {
        "spec": {
            "vol_win": VOL_WIN,
            "horizons": HORIZONS,
            "sigma_target_inst_per_asset": SIGMA_TARGET_INST,
            "port_vol_target": PORT_VOL_TARGET,
            "port_vol_win": PORT_VOL_WIN,
            "cost_bps_rt": COST_BPS_RT,
            "min_years_required": MIN_YEARS_REQUIRED,
            "rs_seeds": RS_SEEDS,
            "seed": SEED,
        },
        "panel_meta": meta_panel,
        "tsmom": {
            "sharpe_ann": sharpe_ann(m_tsmom, ppy=12),
            "maxdd": maxdd(m_tsmom),
            "mean_monthly": float(m_tsmom.mean()),
            "std_monthly": float(m_tsmom.std()),
            "skew": float(m_tsmom.skew()),
            "kurt": float(m_tsmom.kurt()),
            "worst_month": float(m_tsmom.min()),
            "best_month": float(m_tsmom.max()),
            "n_months": int(m_tsmom.shape[0]),
        },
        "buyhold": {
            "sharpe_ann": sharpe_ann(m_bh, ppy=12),
            "maxdd": maxdd(m_bh),
            "mean_monthly": float(m_bh.mean()),
            "std_monthly": float(m_bh.std()),
        },
        "randomsign": {
            "n_seeds": RS_SEEDS,
            "mean_sharpe": float(rs_sharpes.mean()),
            "std_sharpe":  float(rs_sharpes.std()),
            "p05_sharpe":  float(np.percentile(rs_sharpes, 5)),
            "p95_sharpe":  float(np.percentile(rs_sharpes, 95)),
        },
        "cross_check_aqr": cross_check,
    }
    with open(OUT / "a1_diagnostics.json", "w") as f:
        json.dump(diag, f, indent=2, default=str)
    print(f"Saved {OUT/'a1_diagnostics.json'}")
    print("=== DONE ===")


if __name__ == "__main__":
    main()
