"""
STRATEGY — Gold Asian-Session Drift, swap-aware   [production spec, self-contained]

Background / correction: an earlier version of this file held gold long across the
broker rollover (window 22:00->06:00 UTC, "ON_22_8") and looked excellent on price
alone (net Sharpe 1.85). It is NOT tradable: holding XAUUSD long overnight pays the
financing swap (~ -66 / lot / night ~= -3.3 bp at $2000), which is most of the edge.
With the swap charged, ON_22_8 collapses to net Sharpe ~0.46. This is the repo's
lesson L30/L36 (the overnight swap pre-kills any held premium) — the "overnight
drift" is largely the carry the broker bills you for.

RECOMMENDED, swap-free variant — `ASIA_23_8`:
  long XAUUSD over 23:00 -> 07:00 UTC, i.e. ENTERING AFTER the 21:00-22:00 UTC
  rollover and EXITING before the next one -> the position is never held across a
  rollover, so NO swap is charged (spread cost only). Captures the early-Asian drift
  while sitting out the rollover hour. Vol-targeted (avg leverage ~1.05x), one round
  trip per day.

Validated (XAUUSD M1 true-UTC, 2007-2026, swap = 0, spread cost only):
  spread 1.0 bp : Sharpe 1.38 (OOS 1.27)
  spread 1.5 bp : Sharpe 1.18 (OOS 1.07)   <- meets Sharpe>1 (full & OOS)
  spread 2.0 bp : Sharpe 0.98 (OOS 0.88)
  Deflated Sharpe 0.92 (90 trials) | HAC t 3.9 | walk-forward 5/5 | maxDD -15.6%.

TWO HARD CONDITIONS for viability:
  1. broker rollover at <= 22:00 UTC (so the 23:00 entry is post-rollover and the
     trade is swap-free). If the rollover actually hits 23:00, the long swap applies
     and the edge dies (Sharpe -0.34). VERIFY YOUR BROKER'S ROLLOVER TIME.
  2. effective round-trip spread <= ~1.5 bp (achievable in the liquid Asian session
     with limit orders; a market order at retail ~2 bp leaves Sharpe ~0.9).

Audited (audit_code.py / risk_audit.py / stress_mc.py — see reports/gold_strategy_risk_audit.md):
  * NO look-ahead (causal VT; edge survives without VT at Sharpe 0.98);
  * it is ALPHA, not gold beta — regressed on buy&hold gold: beta 0.012, R^2 0.001,
    alpha +2.95 bp/day (HAC t 4.8); positive in 17/20 years incl. the 2013-15 bear;
  * Monte-Carlo (2000 paths): Sharpe median 1.10, 5th pct 0.71, P(SR>1)=66%;
    robust to dropping the 20 best days (Sharpe 0.82).
THREE fragilities gate deployment:
  1. enter at 23:00 UTC TO THE HOUR — the edge is the first post-rollover hour;
     a 1h-late entry collapses Sharpe to 0.37 (exit 06:00-07:00 is forgiving);
  2. long drawdowns — max -19% but up to ~4.8 years underwater (Calmar 0.39);
  3. spread <= ~1.5 bp AND confirmed swap-free rollover (incl. Wednesday triple-swap).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Recommended swap-free config. (ON_22_8 = start 22 / 8h is the swap-KILLED reference.)
PARAMS = dict(window_start_utc=23, window_hours=8, vt_lookback=20, max_leverage=3.0,
              spread_bps_round_trip=1.5, swap_bps_per_night=0.0)  # swap 0 IF rollover <= 22:00


def overnight_returns(h1: pd.DataFrame) -> pd.Series:
    """Per-day log return of the window, indexed by entry date. `h1`: hourly OHLC,
    tz-naive UTC index."""
    lr = np.log(h1["close"] / h1["close"].shift(1))
    hours = [(PARAMS["window_start_utc"] + i) % 24 for i in range(PARAMS["window_hours"])]
    aday = (lr.index - pd.Timedelta(hours=PARAMS["window_start_utc"])).normalize()
    df = pd.DataFrame({"lr": lr, "aday": aday, "hour": lr.index.hour}).dropna()
    df = df[df["hour"].isin(hours)]
    grp = df.groupby("aday")["lr"]
    # COMPLETE windows only: never trade a day missing any of the window hours
    # (weekends, holidays, data gaps). Verified in risk_audit.py to be the right call.
    return grp.sum()[grp.count() == PARAMS["window_hours"]]


def vol_target_scale(overnight: pd.Series) -> pd.Series:
    """Causal vol-target multiplier (trailing-median realised vol / trailing vol, capped)."""
    rv = overnight.rolling(PARAMS["vt_lookback"], min_periods=PARAMS["vt_lookback"]).std().shift(1)
    target = rv.expanding(min_periods=PARAMS["vt_lookback"]).median()
    return (target / rv).clip(upper=PARAMS["max_leverage"]).fillna(0.0)


def positions(h1: pd.DataFrame) -> pd.Series:
    """Daily long exposure to apply over the next window (>= 0)."""
    return vol_target_scale(overnight_returns(h1)).rename("position")


def backtest(h1: pd.DataFrame, spread_bps: float | None = None,
             swap_bps: float | None = None) -> pd.DataFrame:
    """Daily net return series. spread = round-trip; swap = per-night IF held across
    the rollover (0 for the recommended swap-free config)."""
    sp = PARAMS["spread_bps_round_trip"] if spread_bps is None else spread_bps
    sw = PARAMS["swap_bps_per_night"] if swap_bps is None else swap_bps
    onr = overnight_returns(h1)
    pos = vol_target_scale(onr)
    gross = pos * onr
    net = gross - pos.abs() * ((sp + sw) * 1e-4)
    return pd.DataFrame({"window_ret": onr, "position": pos, "gross": gross, "net": net}).dropna()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine import data, stats as S

    h1 = data.load_h1("XAUUSD")
    for sp in (1.0, 1.5, 2.0):
        net = backtest(h1, spread_bps=sp, swap_bps=0.0)["net"].to_numpy()
        print(f"ASIA_23_8 swap-free, spread {sp}bp: Sharpe {S.sharpe_ratio(net, 252):.2f} | "
              f"DSR {S.deflated_sharpe_ratio(net, 90, periods_per_year=252)['dsr']:.2f} | "
              f"mean {net.mean()*1e4:.2f} bp/day")
