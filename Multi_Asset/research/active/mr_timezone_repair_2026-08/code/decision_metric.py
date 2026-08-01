"""Decision metric for the only candidate with a positive gross: GER40 close fade.

p(pass) over the FTMO 2-phase contract and time-to-funded, NOT Sharpe.
Barriers: daily -5 % on intraday equity, STATIC floor -10 % of initial, no time limit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from Portfolio.admission.barrier import BarrierConfig, simulate_campaign  # noqa: E402

CACHE = Path(sys.argv[1])
CLOSE = 17 * 60 + 30
COST_RT_BPS = 1.8   # measured indices RT, cost_denominator_2026-07 (NOT the spread column)


def daily_sleeve(theta: float, cost: float) -> pd.Series:
    df = pd.read_parquet(CACHE / "GER40_M1.parquet")
    idx = df.index.tz_convert("Europe/Berlin")
    mod = idx.hour * 60 + idx.minute
    day = idx.normalize().tz_localize(None)
    need = [CLOSE - 31, CLOSE - 1, CLOSE + 1, CLOSE + 11]
    m = np.isin(mod, need)
    s = pd.DataFrame({"day": day[m], "mod": mod[m],
                      "open": df["open"].values[m], "close": df["close"].values[m]})
    s = s.drop_duplicates(["day", "mod"], keep="last")
    o = s.pivot(index="day", columns="mod", values="open")
    c = s.pivot(index="day", columns="mod", values="close")
    sig = (c[CLOSE - 1] / c[CLOSE - 31] - 1) * 1e4
    r = (o[CLOSE + 11] / o[CLOSE + 1] - 1) * 1e4
    d = pd.concat([sig.rename("s"), r.rename("r")], axis=1).dropna()
    z = ((d.s - d.s.shift(1).rolling(250, min_periods=100).mean())
         / d.s.shift(1).rolling(250, min_periods=100).std())
    pos = np.where(z > theta, -1.0, np.where(z < -theta, 1.0, 0.0))
    pnl = pos * d.r.values
    pnl = np.where(pos != 0, pnl - cost, 0.0)
    out = pd.Series(pnl / 1e4, index=d.index)
    return out[z.notna().values]


if __name__ == "__main__":
    cfg = BarrierConfig()
    for theta in (1.0, 1.5):
        for cost, tag in ((0.0, "GROSS"), (COST_RT_BPS, "net@1.8bps")):
            s = daily_sleeve(theta, cost)
            tr = (s != 0).sum()
            ann = s.mean() * 252
            sr = s.mean() / s.std() * np.sqrt(252) if s.std() > 0 else np.nan
            print(f"\ntheta={theta} {tag}: days={len(s)} trades={tr} "
                  f"({100*tr/len(s):.1f}% active, {100-100*tr/len(s):.1f}% FLAT) "
                  f"ann_ret={100*ann:.2f}% daily_SR={sr:.2f} "
                  f"worst_day={100*s.min():.2f}%")
            if tag != "net@1.8bps":
                continue
            for vm in (1, 10, 20, 40):
                res = simulate_campaign(s, cfg, n_paths=3000, mean_block=10.0,
                                        seed=7, scale=vm)
                print(f"   vm={vm:>3}: p(pass)={res.p_pass:.3f} "
                      f"median_days={res.median_days_to_funded:.0f} "
                      f"p_floor={res.p_fail_floor:.3f} p_daily={res.p_fail_daily:.3f} "
                      f"p_timeout={res.p_timeout:.3f}")
