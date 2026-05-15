"""
Test C — Macro signal with lag correction + position scaler evaluation.

Root cause from Test A: VIX change fires the same week as the crash,
not the week before. Tests:
  1. Lag the composite by 1 and 2 weeks.
  2. Isolate each component at lag 1 to find what (if anything) leads.
  3. Quick BTC-only equity curve: macro as binary position scaler on C1.

No backtest for the standalone signal — IC test + scaler delta only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

START        = "2020-01-01"
END          = "2026-05-14"
OOS_START    = "2023-01-01"
SCALER_START = "2021-01-01"
ROLL_WIN     = 26
VOL_TARGET   = 0.18
TRADING_DAYS = 365


# ── Data + features ───────────────────────────────────────────────────────────

def _download() -> pd.DataFrame:
    import yfinance as yf
    tickers = ["SPY", "GLD", "DX-Y.NYB", "^VIX", "BTC-USD"]
    raw = yf.download(tickers, start=START, end=END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw["Close"]
    raw.index = pd.to_datetime(raw.index)
    return raw


def _components(df: pd.DataFrame) -> dict[str, pd.Series]:
    """
    Return each macro component (daily, shift(1)) and the composite.
    Sign convention: positive = risk-on.
    """
    spy = df["SPY"]
    dxy = df["DX-Y.NYB"]
    vix = df["^VIX"]

    spy_mom   = (spy / spy.shift(21) - 1).shift(1)
    dxy_mom   = (dxy / dxy.shift(21) - 1).shift(1)
    vix_level = vix.shift(1)
    vix_chg   = (vix - vix.shift(6)).shift(1)

    composite = spy_mom - dxy_mom - 0.1 * vix_level / 30 - vix_chg * 0.5
    composite.name = "composite"

    return {
        "composite": composite,
        "spy_mom":   spy_mom,
        "dxy_mom":   dxy_mom,
        "vix_level": vix_level,
        "vix_chg":   vix_chg,
    }


# ── IC metrics ────────────────────────────────────────────────────────────────

def _ic(sig: pd.Series, out: pd.Series) -> dict:
    df = pd.DataFrame({"s": sig, "o": out}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, icir=np.nan, n=n)
    ic     = float(df["s"].corr(df["o"]))
    t_stat = ic * np.sqrt(max(n - 2, 0)) / np.sqrt(max(1 - ic**2, 1e-12))
    roll   = df["s"].rolling(ROLL_WIN).corr(df["o"])
    icir   = float(roll.mean() / (roll.std() + 1e-12))
    return dict(ic=ic, t_stat=t_stat, icir=icir, n=n)


# ── Position scaler ───────────────────────────────────────────────────────────

def _c1_position(btc_log: pd.Series) -> pd.Series:
    """Reproduce C1 BTC-only position (weekly Monday-locked)."""
    cum   = btc_log.rolling(28).sum().shift(1)
    vol_L = btc_log.rolling(28).std().shift(1).replace(0, np.nan) * np.sqrt(28)
    sig   = np.tanh((cum / vol_L).fillna(0.0)).clip(lower=0.0)
    sig[cum.isna()] = np.nan
    sig = sig.fillna(0.0)

    rv = (btc_log.rolling(20).std().shift(1) * np.sqrt(TRADING_DAYS)
          ).replace(0, np.nan).ffill().fillna(VOL_TARGET)
    vs = (VOL_TARGET / rv).clip(0.1, 2.0)

    raw = sig * vs
    is_mon = raw.index.dayofweek == 0
    locked = raw.copy()
    locked[~is_mon] = np.nan
    return locked.ffill().fillna(0.0)


def run_scaler(btc_log: pd.Series, macro_score: pd.Series) -> dict:
    """
    Binary position scaler: 100% if macro_score > 0, else 40%.
    Macro score is forward-filled from Friday to following Friday.
    Returns Sharpe delta (scaled − plain).
    """
    pos_c1 = _c1_position(btc_log)

    # Weekly macro → forward-fill to daily (Friday score applies Mon–Thu next week)
    macro_w     = macro_score.resample("W-FRI").last()
    macro_daily = macro_w.reindex(btc_log.index).ffill().fillna(0.0)
    scale_vals  = np.where(macro_daily > 0, 1.0, 0.4)
    pos_scaled  = pos_c1 * scale_vals

    arith    = np.exp(btc_log) - 1
    pnl_c1   = pos_c1.shift(1).fillna(0.0)   * arith
    pnl_sc   = pos_scaled.shift(1).fillna(0.0) * arith

    def _sharpe(s: pd.Series) -> float:
        s = s[SCALER_START:]
        return float(s.mean() / s.std() * np.sqrt(TRADING_DAYS)) if s.std() > 0 else np.nan

    def _mdd(s: pd.Series) -> float:
        s = s[SCALER_START:]
        eq = (1 + s).cumprod()
        return float((eq / eq.cummax() - 1).min())

    sh_c1 = _sharpe(pnl_c1)
    sh_sc = _sharpe(pnl_sc)
    return {"sharpe_c1": sh_c1, "sharpe_scaled": sh_sc,
            "delta": sh_sc - sh_c1,
            "mdd_c1": _mdd(pnl_c1), "mdd_scaled": _mdd(pnl_sc)}


# ── Main ─────────────────────────────────────────────────────────────────────

def main(preloaded: pd.DataFrame | None = None) -> dict:
    print("=" * 60)
    print("TEST C — MACRO LAGGED + POSITION SCALER")
    print("=" * 60)

    df  = preloaded if preloaded is not None else _download()
    btc_col = "BTC-USD" if "BTC-USD" in df.columns else [c for c in df.columns if "BTC" in c][0]
    btc_log = np.log(df[btc_col] / df[btc_col].shift(1))

    comps     = _components(df)
    composite = comps["composite"]

    btc_w   = btc_log.resample("W-FRI").sum()
    outcome = btc_w.shift(-1)

    tsmom_proxy = btc_log.rolling(28).sum().shift(1)
    tsmom_w     = tsmom_proxy.resample("W-FRI").last()
    comp_w      = composite.resample("W-FRI").last()

    # ── 1. Composite lag 0 / 1 / 2 ───────────────────────────
    print("\n  COMPOSITE LAG ANALYSIS  (lag 0 already in Test A)")
    print("  " + "─" * 55)
    lag_results: dict[str, dict] = {}
    for lag in [0, 1, 2]:
        lagged = comp_w.shift(lag)
        m      = _ic(lagged, outcome)
        dc     = pd.DataFrame({"l": lagged, "t": tsmom_w}).dropna()
        corr   = float(dc["l"].corr(dc["t"]))
        print(f"  lag {lag}w: IC={m['ic']:+.4f}  t={m['t_stat']:+.3f}  "
              f"ICIR={m['icir']:+.3f}  corr_TSMOM={corr:+.3f}  N={m['n']}")
        lag_results[f"lag{lag}"] = {**m, "tsmom_corr": corr}

    # ── 2. Component isolation (lag 1) ────────────────────────
    print("\n  INDIVIDUAL COMPONENTS — LAG 1")
    print("  " + "─" * 55)
    comp_stats: dict[str, dict] = {}
    for name, series in comps.items():
        if name == "composite":
            continue
        w  = series.resample("W-FRI").last().shift(1)
        m  = _ic(w, outcome)
        dc = pd.DataFrame({"l": w, "t": tsmom_w}).dropna()
        corr = float(dc["l"].corr(dc["t"]))
        print(f"  {name:<15}: IC={m['ic']:+.4f}  t={m['t_stat']:+.3f}  "
              f"ICIR={m['icir']:+.3f}  corr={corr:+.3f}  N={m['n']}")
        comp_stats[name] = {**m, "tsmom_corr": corr}

    best_name = max(comp_stats, key=lambda k: abs(comp_stats[k].get("t_stat") or 0))
    best_comp = comp_stats[best_name]
    print(f"\n  Best component: {best_name}  "
          f"|t-stat|={abs(best_comp['t_stat']):.3f}  "
          f"corr={best_comp['tsmom_corr']:+.3f}")

    # ── 3. Position scaler equity curve ──────────────────────
    print(f"\n  POSITION SCALER  (BTC only, {SCALER_START}–{END})")
    print("  " + "─" * 55)
    print("  Rule: macro_score > 0 → 100% position; ≤ 0 → 40% position")
    sc = run_scaler(btc_log, composite)
    print(f"  C1 BTC Sharpe    : {sc['sharpe_c1']:+.3f}  MaxDD: {sc['mdd_c1']:.1%}")
    print(f"  C1 + macro scale : {sc['sharpe_scaled']:+.3f}  MaxDD: {sc['mdd_scaled']:.1%}")
    print(f"  Δ Sharpe         : {sc['delta']:+.3f}  "
          f"({'HELPS ✓' if sc['delta'] > 0 else 'HURTS ✗'})")

    # Determine if any lag passes IC gate
    best_lag_key = max(lag_results, key=lambda k: lag_results[k].get("t_stat") or 0)
    best_lag = lag_results[best_lag_key]
    any_pass = best_lag.get("t_stat", 0) > 1.5 and abs(best_lag.get("tsmom_corr", 1)) < 0.30
    comp_pass = best_comp.get("t_stat", 0) > 1.5 and abs(best_comp.get("tsmom_corr", 1)) < 0.30

    return {
        "lag0":       lag_results["lag0"],
        "lag1":       lag_results["lag1"],
        "lag2":       lag_results["lag2"],
        "best_comp":  {**best_comp, "name": best_name},
        "scaler":     sc,
        "any_lag_pass":  any_pass,
        "comp_pass":     comp_pass,
    }


if __name__ == "__main__":
    main()
