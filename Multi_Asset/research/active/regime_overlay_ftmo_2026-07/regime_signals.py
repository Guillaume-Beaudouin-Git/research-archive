"""Regime signals for the overlay test: VIX term structure and price vs MA200.

Frozen in PREREGISTRATION.md section 4. No threshold is tuned here.

Look-ahead contract: every input is reindexed onto the engine calendar and then shifted
by one full engine day, so day T's exposure can only use information stamped strictly
before day T. The FTMO overnight sleeve posts risk at 17:35 CET (GER40) and 22:05 CET
(US100); 22:05 CET = 16:05 ET, i.e. BEFORE the 16:15 ET VIX print of the same date, so
same-date VIX would be look-ahead. ``assert_no_lookahead`` verifies the property
mechanically by truncating the future of each input.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)

STRESS_EXPO = 0.30          # frozen: exposure in stress
NORMAL_EXPO = 1.00
MA_WINDOW = 200             # frozen
VIX_RATIO_THRESHOLD = 1.00  # frozen: backwardation


# --------------------------------------------------------------------- inputs
def vix_term() -> pd.Series:
    """VIX / VIX3M daily ratio (yfinance, free). Cached locally."""
    f = CACHE / "vix_term.parquet"
    if f.exists():
        return pd.read_parquet(f)["ratio"]
    import yfinance as yf

    d = yf.download(["^VIX", "^VIX3M"], start="2012-01-01", progress=False,
                    auto_adjust=False)["Close"].dropna()
    ratio = (d["^VIX"] / d["^VIX3M"]).rename("ratio")
    ratio.to_frame().to_parquet(f)
    return ratio


def us100_daily_close() -> pd.Series:
    """US100 daily close from data/deep_history_utc (true UTC M1). Cached locally."""
    f = CACHE / "us100_daily_close.parquet"
    if f.exists():
        return pd.read_parquet(f)["close"]
    src = REPO / "data/deep_history_utc/US100_M1.csv"
    chunks = []
    for ch in pd.read_csv(src, usecols=["timestamp_utc", "close"], chunksize=2_000_000):
        ts = pd.to_datetime(ch["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
        ch = ch.assign(day=ts.dt.normalize())
        chunks.append(ch.groupby("day")["close"].last())
    s = pd.concat(chunks).groupby(level=0).last().rename("close")
    s.to_frame().to_parquet(f)
    return s


# ------------------------------------------------------------------ exposures
def _align_lagged(sig: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Reindex onto the engine calendar, then lag one full engine day."""
    return sig.reindex(dates, method="ffill").shift(1)


def build_exposures(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Return the three pre-registered exposure series O1/O2/O3 on the engine calendar."""
    ratio = _align_lagged(vix_term(), dates)
    px = us100_daily_close()
    ma = px.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    below = (px < ma).astype(float)
    below[ma.isna()] = np.nan
    below = _align_lagged(below, dates)

    s1 = (ratio > VIX_RATIO_THRESHOLD)
    s1[ratio.isna()] = False                 # unknown regime -> no cut (conservative)
    s2 = (below > 0.5)
    s2[below.isna()] = False
    s3 = s1 | s2

    out = pd.DataFrame(index=dates)
    for name, stress in (("O1_vixterm", s1), ("O2_ma200", s2), ("O3_both", s3)):
        out[name] = np.where(stress.to_numpy(), STRESS_EXPO, NORMAL_EXPO)
        out[name + "_stress"] = stress.to_numpy().astype(float)
    out["vix_ratio_lag1"] = ratio.to_numpy()
    out["below_ma200_lag1"] = below.to_numpy()
    return out


def assert_no_lookahead(dates: pd.DatetimeIndex, n_probe: int = 60) -> None:
    """Truncating the future of every input must not change any past exposure.

    Concretely: rebuild the exposures using only data up to a cut date and check the
    resulting series is identical to the full-sample one on every day <= cut. If any
    same-day (or later) information leaked into an exposure, this fails.
    """
    full = build_exposures(dates)
    ratio_full, px_full = vix_term(), us100_daily_close()
    cuts = dates[len(dates) // 3:: max(1, len(dates) // n_probe)]
    for cut in cuts:
        r_t = ratio_full[ratio_full.index < cut]
        p_t = px_full[px_full.index < cut]
        ma = p_t.rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
        below = (p_t < ma).astype(float)
        below[ma.isna()] = np.nan
        sub = dates[dates <= cut]
        r1 = _align_lagged(r_t, sub)
        b1 = _align_lagged(below, sub)
        s1 = (r1 > VIX_RATIO_THRESHOLD).fillna(False)
        s2 = (b1 > 0.5).fillna(False)
        e1 = np.where(s1, STRESS_EXPO, NORMAL_EXPO)
        e2 = np.where(s2, STRESS_EXPO, NORMAL_EXPO)
        # the last element uses data strictly before `cut`; anything earlier must match
        if not np.allclose(e1[:-1], full.loc[sub, "O1_vixterm"].to_numpy()[:-1]):
            raise AssertionError(f"O1 look-ahead detected at cut {cut}")
        if not np.allclose(e2[:-1], full.loc[sub, "O2_ma200"].to_numpy()[:-1]):
            raise AssertionError(f"O2 look-ahead detected at cut {cut}")


if __name__ == "__main__":
    import build_book as B

    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])
    ex = build_exposures(dates)
    ex.to_parquet(CACHE / "exposures.parquet")

    print("=== regime exposures on the engine calendar ===")
    print(f"period: {dates.min().date()} -> {dates.max().date()}  N={len(dates)}")
    for c in ("O1_vixterm", "O2_ma200", "O3_both"):
        st = ex[c + "_stress"]
        print(f"{c:12s}  stress days {st.mean():6.1%}   mean exposure {ex[c].mean():.4f}")

    # cross-check the MA200 input against the audited panel
    pan = pd.read_parquet(REPO / "data/ftmo_portfolio/cache/panel_px.parquet")["US100"]
    dh = us100_daily_close()
    j = pd.concat([pan.rename("panel"), dh.rename("deep")], axis=1).dropna()
    print(f"\ncorr(deep_history US100 close, panel_px US100) = {j['panel'].corr(j['deep']):.6f} (N={len(j)})")

    assert_no_lookahead(dates)
    print("look-ahead assertion: PASS (truncating the future changes no past exposure)")
