"""L56 falsification test, run BEFORE the map: which clock is the map's clock?

For each instrument, build the mean-|hourly-return| profile (24 points)
separately over DST-winter months and DST-summer months, once indexed by UTC
hour and once by exchange-local hour. If the intraday structure is anchored to
the exchange clock, the winter/summer profiles agree in LOCAL and disagree in
UTC. If the reverse, the exchange clock chosen in build_map.CLOCKS is wrong.

Free, zero-cost, no trade form involved.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from build_map import CACHE, CLASS, CLOCKS, INSTRUMENTS, SPLIT

WINTER = {11, 12, 1, 2}
SUMMER = {5, 6, 7, 8}


def profile(idx_hour: np.ndarray, absret: np.ndarray, month: np.ndarray, months: set) -> np.ndarray:
    m = np.isin(month, list(months))
    out = np.full(24, np.nan)
    for h in range(24):
        sel = m & (idx_hour == h)
        if sel.sum() >= 50:
            out[h] = absret[sel].mean()
    return out


def corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 12:
        return float("nan")
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def main() -> None:
    rows = []
    for inst in INSTRUMENTS:
        df = pd.read_parquet(f"{CACHE}/{inst}_H1.parquet")
        df = df[df.index >= SPLIT]
        r = np.abs(np.log(df["close"]).diff()).to_numpy() * 1e4
        tz, _ = CLOCKS[inst]
        loc = df.index.tz_localize("UTC").tz_convert(tz)
        uh, lh, mo = df.index.hour.to_numpy(), loc.hour.to_numpy(), df.index.month.to_numpy()
        ok = np.isfinite(r)
        cu = corr(profile(uh[ok], r[ok], mo[ok], WINTER), profile(uh[ok], r[ok], mo[ok], SUMMER))
        cl = corr(profile(lh[ok], r[ok], mo[ok], WINTER), profile(lh[ok], r[ok], mo[ok], SUMMER))
        rows.append(dict(instrument=inst, cls=CLASS[inst], exchange_tz=tz,
                         corr_winter_summer_UTC=cu, corr_winter_summer_LOCAL=cl,
                         local_wins=bool(cl > cu)))
        print(f"{inst:8s} {tz:18s} UTC {cu:+.3f}   LOCAL {cl:+.3f}   "
              f"{'LOCAL' if cl > cu else 'UTC'} wins", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv("../clock_falsification.csv", index=False)
    print(f"\nLOCAL clock wins on {out['local_wins'].sum()}/{len(out)} instruments")


if __name__ == "__main__":
    main()
