"""
Canonical cell (SMA20 z-score(2.0), CROSS entry, ATR-bracket 1:1xATR20, H=8, 15-min,
plain-bracket resolution -- NOT M1-resolved, PREREGISTRATION.md Sec2/6) on whichever
newly-fetched Asia/EU indices are available in `_cache/dukascopy_m5/` at run time.
Feasibility read only: 1 year (2024, and for JP225 only H1-2024 -- Dukascopy throughput in this
sandboxed environment did not allow more within the session's time budget) vs 13-19y for the 9
already-tested instruments.

JP225 clock: `dataload_asia.py`'s `_fix_paris_anchor_bug` (L52/L56 catch) corrects a real
timestamp bug in this study's own fetcher; a falsification test (winter-vs-summer peak-hour
stability) confirms the fix. The corrected profile is BIMODAL (TSE cash open ~00:00 UTC single
largest hour, AND a broader US-hours/Osaka-night-futures plateau 13:00-20:00 UTC capturing more
CUMULATIVE volume) -- genuinely different session structure from any Western index already
tested. Both candidate windows are run and reported, not silently collapsed to one.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "Multi_Asset" / "research" / "active" / "mr_intraday_grille_2026-08"))
sys.path.insert(0, str(REPO / "yt_strategy_replications"))

import engine_lib as E
from engine import indicators as ind

import dataload_asia as DA

H_BACKSTOP = 8


def bars_per_year(df):
    return float(df.groupby("session_date").size().median()) * 252.0


def run_cell(sym, years, session, tag):
    df, (st, en) = DA.build_15min(sym, years, session=session, tag=tag, force=True)
    close = df["close"]
    dist = E.dist_zscore(close, 20)
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    sl, tp = E.exit_atr_bracket(atr20, 1.0, 1.0)
    bpy = bars_per_year(df)
    scale = E.vol_target_scale(df, bars_per_year=bpy)
    cost = DA.COST_RT_BPS_PROXY[sym] / 1e4
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E.entry_cross(d, 2.0, "signed")
    ne = E.bars_to_session_end(df) <= H_BACKSTOP
    sig = E.signal_from_masks(long_m, short_m, ne)
    res = E.run_cell(df, sig, sl, tp, H_BACKSTOP, scale, cost, bpy, n_trials=1)
    res.update(dict(block=f"ASIA_canonical_M5resolved_{tag}", sym=sym, freq="15min(from M5)",
                   anchor="SMA", metric="ZSCORE", k=20, threshold=2.0, entry="CROSS",
                   exit="ATR_BRACKET_SYM_1_1_H8", session=f"{st}-{en}",
                   years=str(years), n_days=int(df['session_date'].nunique())))
    return res


def main():
    rows = []
    # JP225: only H1-2024 was fetched (see PREREGISTRATION.md); bimodal clock -> two windows
    if (HERE / "_cache" / "dukascopy_m5" / "JP225_2024_M5.parquet").exists():
        for tag, sess in (("tse_cash", ("00:00", "06:00")),
                         ("us_overlap", ("13:00", "20:00"))):
            t0 = time.time()
            res = run_cell("JP225", [2024], sess, tag)
            print(f"JP225 [{tag}] {sess}: n_trades={res['n_trades']} "
                  f"gross_t={res.get('gross_t'):.3f} ({time.time()-t0:.1f}s)")
            rows.append(res)
    else:
        print("JP225: no data")

    for sym in ("HK50", "AUS200", "UK100", "FRA40"):
        pq_check = HERE / "_cache" / "dukascopy_m5" / f"{sym}_2024_M5.parquet"
        if not pq_check.exists():
            print(f"{sym}: no data -- NOT COVERED this session (declared)")
            continue
        t0 = time.time()
        res = run_cell(sym, [2024], None, "auto")
        print(f"{sym}: n_trades={res['n_trades']} gross_t={res.get('gross_t'):.3f} "
              f"session={res['session']} ({time.time()-t0:.1f}s)")
        rows.append(res)

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(HERE / "grille_asia_new.csv", index=False)
        print(f"Wrote {len(out)} rows -> grille_asia_new.csv")
    else:
        print("No rows -- no Asia/EU data available.")


if __name__ == "__main__":
    main()
