"""
Test A — Macro Cross-Asset Signal Feasibility
VIX/DXY/SPY/GLD composite score → BTC weekly return IC test.

Hypothesis (Liu & Tsyvinski 2021, BIS 2024):
  Crypto momentum performs better in risk-on macro environments.
  Composite score captures institutional flow via non-price inputs.

PASS criteria (both must hold):
  1. IC t-stat > 1.5  (full period, Pearson)
  2. |corr(macro_score, TSMOM_28d)| < 0.30  (must add information beyond TSMOM)

No backtest. IC test only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

START         = "2020-01-01"
END           = "2026-05-14"
SUB_START     = "2023-01-01"
ROLL_WIN      = 26        # weeks for rolling IC → ICIR
IC_TSTAT_PASS = 1.5
CORR_MAX      = 0.30


# ── Data ─────────────────────────────────────────────────────────────────────

def download_data() -> pd.DataFrame:
    import yfinance as yf
    tickers = ["SPY", "GLD", "DX-Y.NYB", "^VIX", "BTC-USD"]
    print(f"[macro] Downloading {tickers} ...")
    raw = yf.download(tickers, start=START, end=END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw
    close.index = pd.to_datetime(close.index)
    print(f"  {len(close)} rows | columns: {list(close.columns)}")
    missing = [t for t in tickers if t not in close.columns]
    if missing:
        print(f"  [WARNING] missing tickers: {missing}")
    return close


# ── Features ─────────────────────────────────────────────────────────────────

def build_macro_score(df: pd.DataFrame) -> pd.Series:
    """
    Composite macro risk-on/risk-off score. Positive = risk-on = favorable for crypto.
    All components use .shift(1) — no look-ahead.

    Sign convention:
      +spy_mom  : rising equities = risk appetite
      -dxy_mom  : falling USD = loose financial conditions
      -vix/30   : low absolute VIX = calm = risk-on
      -vix_chg  : falling VIX = improving sentiment
    GLD momentum computed as diagnostic but not included in composite.
    """
    def _safe_col(name: str) -> pd.Series | None:
        """Find column by name or partial match (e.g. '^VIX' → 'VIX', 'DX-Y.NYB' → 'DX')."""
        if name in df.columns:
            return df[name]
        for col in df.columns:
            if name.replace("^", "").replace("-", "").upper() in col.replace("-", "").replace("^", "").upper():
                return df[col]
        return None

    spy = _safe_col("SPY")
    gld = _safe_col("GLD")
    dxy = _safe_col("DX-Y.NYB")
    vix = _safe_col("^VIX")

    required = {"SPY": spy, "DX-Y.NYB": dxy, "^VIX": vix}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"Cannot build macro score — missing: {missing}")

    spy_mom   = (spy / spy.shift(21) - 1).shift(1)
    dxy_mom   = (dxy / dxy.shift(21) - 1).shift(1)
    vix_level = vix.shift(1)
    vix_chg   = (vix - vix.shift(6)).shift(1)

    if gld is not None:
        gld_mom = (gld / gld.shift(21) - 1).shift(1)
        print(f"  [features] GLD 1m mean={gld_mom.mean():+.4f}  std={gld_mom.std():.4f}  (diagnostic only)")

    score = spy_mom - dxy_mom - 0.1 * vix_level / 30 - vix_chg * 0.5
    score.name = "macro_score"

    print(f"  [features] score stats: mean={score.mean():+.4f}  std={score.std():.4f}  "
          f"non-NaN={score.notna().sum()}")
    return score


# ── IC metrics ────────────────────────────────────────────────────────────────

def ic_metrics(sig: pd.Series, out: pd.Series) -> dict:
    """
    Pearson IC, t-stat, and rolling ICIR.
    t-stat = IC × sqrt(N-2) / sqrt(1 - IC²)  (standard Fisher approx)
    ICIR   = mean(rolling_26w_IC) / std(rolling_26w_IC)
    """
    df = pd.DataFrame({"s": sig, "o": out}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, icir=np.nan, n=n)

    ic     = float(df["s"].corr(df["o"]))
    denom  = np.sqrt(max(1.0 - ic ** 2, 1e-12))
    t_stat = ic * np.sqrt(max(n - 2, 0)) / denom

    roll_ic = df["s"].rolling(ROLL_WIN).corr(df["o"])
    icir    = float(roll_ic.mean() / (roll_ic.std() + 1e-12))

    return dict(ic=ic, t_stat=t_stat, icir=icir, n=n)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 60)
    print("TEST A — MACRO CROSS-ASSET SIGNAL")
    print("=" * 60)

    close = download_data()

    # BTC daily log returns
    btc_col = "BTC-USD" if "BTC-USD" in close.columns else [c for c in close.columns if "BTC" in c][0]
    btc_log = np.log(close[btc_col] / close[btc_col].shift(1))

    # Macro composite score
    try:
        macro = build_macro_score(close)
    except ValueError as e:
        print(f"  ERROR: {e}")
        return {"verdict": "ERROR", "ic_full": np.nan, "t_stat": np.nan,
                "icir": np.nan, "ic_sub": np.nan, "tsmom_corr": np.nan}

    # ── Weekly alignment ──────────────────────────────────────
    # Signal: Friday-close macro score (known before next week opens)
    # Outcome: next calendar week's BTC log return sum
    macro_w = macro.resample("W-FRI").last()
    btc_w   = btc_log.resample("W-FRI").sum()
    outcome = btc_w.shift(-1)   # next week's BTC return

    # ── TSMOM 28d signal proxy for correlation test ───────────
    # Use raw cumulative return (proportional to binary or tanh signal)
    tsmom_proxy = btc_log.rolling(28).sum().shift(1)
    tsmom_w     = tsmom_proxy.resample("W-FRI").last()

    # ── IC — full period ──────────────────────────────────────
    m_full = ic_metrics(macro_w, outcome)
    print(f"\n  Full period ({START}–{END}):  N = {m_full['n']} weekly obs")
    print(f"  IC (Pearson)  : {m_full['ic']:+.4f}")
    print(f"  t-stat        : {m_full['t_stat']:+.3f}")
    print(f"  ICIR (26w)    : {m_full['icir']:+.3f}")

    # ── IC — sub-period 2023+ ─────────────────────────────────
    sub_mask = macro_w.index >= pd.Timestamp(SUB_START)
    m_sub    = ic_metrics(macro_w[sub_mask], outcome[sub_mask])
    print(f"\n  Sub-period ({SUB_START}–{END}):  N = {m_sub['n']} weekly obs")
    print(f"  IC (Pearson)  : {m_sub['ic']:+.4f}")
    print(f"  t-stat        : {m_sub['t_stat']:+.3f}")

    # ── TSMOM correlation ─────────────────────────────────────
    corr_df    = pd.DataFrame({"m": macro_w, "t": tsmom_w}).dropna()
    tsmom_corr = float(corr_df["m"].corr(corr_df["t"]))
    print(f"\n  Corr(macro_score, TSMOM_28d): {tsmom_corr:+.3f}  "
          f"(N={len(corr_df)})")

    # ── Component correlation breakdown ──────────────────────
    # (informational — understand which macro component drives TSMOM correlation)
    try:
        spy_col = "SPY" if "SPY" in close.columns else None
        if spy_col:
            spy_mom_w = ((close[spy_col] / close[spy_col].shift(21) - 1)
                         .shift(1).resample("W-FRI").last())
            df_comp = pd.DataFrame({"spy": spy_mom_w, "tsmom": tsmom_w}).dropna()
            spy_corr = float(df_comp["spy"].corr(df_comp["tsmom"]))
            print(f"  Corr(spy_mom,  TSMOM_28d): {spy_corr:+.3f}  "
                  f"(shows how much SPY momentum drives correlation)")
    except Exception:
        pass

    # ── Verdict ───────────────────────────────────────────────
    pass_ic   = (m_full["t_stat"] is not np.nan) and (m_full["t_stat"] > IC_TSTAT_PASS)
    pass_corr = abs(tsmom_corr) < CORR_MAX
    verdict   = "PASS" if (pass_ic and pass_corr) else "FAIL"

    print(f"\n  Gate 1 — IC t-stat > {IC_TSTAT_PASS}:  "
          f"{'✓' if pass_ic else '✗'}  ({m_full['t_stat']:.3f})")
    print(f"  Gate 2 — |corr| < {CORR_MAX}:       "
          f"{'✓' if pass_corr else '✗'}  ({abs(tsmom_corr):.3f})")
    print(f"\n  VERDICT (Test A): {verdict}")

    return {
        "ic_full":    m_full["ic"],
        "t_stat":     m_full["t_stat"],
        "icir":       m_full["icir"],
        "ic_sub":     m_sub["ic"],
        "tsmom_corr": tsmom_corr,
        "verdict":    verdict,
    }


if __name__ == "__main__":
    main()
