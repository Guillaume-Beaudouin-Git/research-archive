"""Step 1 — vehicle + data-quality gates, BEFORE any performance claim (L53, L56, L60).

Three questions, each of which can end the study on its own:

  V1  Does the FTMO CFD actually QUOTE the Globex reopen window? (this is what killed
      soybean: the broker never quotes the CBOT reopen -> the edge is unreachable)
  V2  Is the FTMO daily-loss reset (00:00 Europe/Prague) aligned with the window start?
      The two clocks are DST-locked to different calendars, so they drift apart for a
      few weeks a year; a window straddling the reset splits across two FTMO days.
  V3  L60 — what fraction of bars are settlement prints (zero range / stale close)?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common_reopen import (FTMO_M5, H1_CACHE, OUT, REOPEN_ET, WINDOW_HOURS,
                           eu_dst, load_m1, reopen_utc_hour, us_dst)

rows = []


# ── V1 ───────────────────────────────────────────────────────────────────────
# FTMO-Demo feed (data/ftmo_portfolio/cache/XAUUSD_m5_close.parquet, Europe/Prague).
# Provenance: MEMORY mt5_data_provenance_2026-06 — this IS the broker feed we would
# trade, not a third-party reconstruction.
m5 = pd.read_parquet(FTMO_M5)
idx_utc = m5.index.tz_convert("UTC").tz_localize(None)
m5 = m5.set_index(idx_utc).sort_index()
m5 = m5[m5.index >= "2007-01-01"]

days = pd.DatetimeIndex(m5.index.normalize().unique())
rh = pd.Series(reopen_utc_hour(days), index=days)
dst = pd.Series(us_dst(days), index=days)

hour = m5.index.hour
day = m5.index.normalize()
want = rh.reindex(day).to_numpy()
is_dst = dst.reindex(day).to_numpy()

# five-minute slots present in the reopen hour, per season
for season, mask_season in (("US_standard(win)", ~is_dst), ("US_DST(summer)", is_dst)):
    sub_days = days[dst.reindex(days).to_numpy() == (season == "US_DST(summer)")]
    n_days = len(sub_days)
    at_reopen = m5[(hour == want) & mask_season]
    halt_hour = np.where(is_dst, 21, 22)      # 17:00-18:00 ET settlement pause
    at_halt = m5[(hour == halt_hour) & mask_season]
    rows.append(dict(check="V1_bar_availability", season=season, n_sessions=n_days,
                     slots_reopen_hour=len(at_reopen),
                     slots_per_session_reopen=round(len(at_reopen) / max(n_days, 1), 2),
                     slots_halt_hour=len(at_halt),
                     slots_per_session_halt=round(len(at_halt) / max(n_days, 1), 2)))

# The decisive count. Denominator = the sessions the sleeve ACTUALLY TRADES in the
# research series (Sun-Thu evenings ET, holidays already dropped); numerator = those with
# an FTMO print inside the first 15 min of the reopen hour. This answers the only question
# that matters: "could this trade have been executed on the FTMO account?"
traded = pd.read_csv(OUT / "step2_gold_window_path.csv", index_col=0,
                     parse_dates=True).index                      # ET session dates
first15 = m5[(hour == want) & (m5.index.minute < 15)]
# map an FTMO print back to its ET session date (the reopen hour belongs to date D in ET)
ftmo_sess = pd.DatetimeIndex(first15.index.normalize().unique())
hit = traded.isin(ftmo_sess)
rows.append(dict(check="V1_traded_sessions_with_FTMO_print_in_first_15min",
                 season="all", n_sessions=len(traded),
                 slots_reopen_hour=int(hit.sum()),
                 slots_per_session_reopen=round(float(hit.mean()), 4),
                 slots_halt_hour=np.nan, slots_per_session_halt=np.nan))

# ── V2 ───────────────────────────────────────────────────────────────────────
# FTMO daily floor resets at 00:00 Prague = 23:00 UTC (CET) / 22:00 UTC (CEST).
# Window starts 23:00 UTC (US standard) / 22:00 UTC (US DST).
reset_utc = np.where(eu_dst(days), 22, 23)
win_start = reopen_utc_hour(days)
aligned = reset_utc == win_start
mis = days[~aligned]
rows.append(dict(check="V2_dll_reset_alignment", season="all", n_sessions=len(days),
                 slots_reopen_hour=int(aligned.sum()),
                 slots_per_session_reopen=round(float(aligned.mean()), 4),
                 slots_halt_hour=int((~aligned).sum()), slots_per_session_halt=np.nan))

# ── V3 ── L60 zero-range / stale-print control ───────────────────────────────
h1 = pd.read_parquet(H1_CACHE)
zr = float((h1["high"] == h1["low"]).mean())
h1_win = h1[h1.index.hour.isin([21, 22, 23, 0, 1, 2, 3, 4, 5, 6])]
zr_win = float((h1_win["high"] == h1_win["low"]).mean())

m1 = load_m1()
stale = float((m1["close"].diff() == 0).mean())
m1_hour = m1["ts"].dt.hour
m1_rh = pd.Series(reopen_utc_hour(m1["ts"].dt.normalize()), index=m1.index)
in_reopen = m1_hour.to_numpy() == m1_rh.to_numpy()
stale_reopen = float((m1.loc[in_reopen, "close"].diff() == 0).mean())
rows.append(dict(check="V3_zero_range_L60", season="H1_all", n_sessions=len(h1),
                 slots_reopen_hour=np.nan, slots_per_session_reopen=round(zr, 5),
                 slots_halt_hour=np.nan, slots_per_session_halt=round(zr_win, 5)))
rows.append(dict(check="V3_stale_M1_close", season="M1_all/M1_reopen_hour",
                 n_sessions=len(m1), slots_reopen_hour=np.nan,
                 slots_per_session_reopen=round(stale, 5),
                 slots_halt_hour=np.nan, slots_per_session_halt=round(stale_reopen, 5)))

df = pd.DataFrame(rows)
df.to_csv(OUT / "step1_vehicle_gates.csv", index=False)
print(df.to_string(index=False))
