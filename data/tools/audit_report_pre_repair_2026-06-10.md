# Bar-density audit — `data/deep_history_utc`

**Generated:** 2026-06-10 00:54 by `/usr/bin/python3 data/tools/audit_bar_density.py` (read-only).
**Rule:** flag day if bars < 50% of instrument median (over weekdays with ≥1 bar); contiguous flagged runs classified (a) holiday / (b) floor / (d) structural segment / **(c) ANOMALY**.
**Known by design:** US2000 absent from estate (Dukascopy floor 2018-08-08 > MT5 start 2018-01-23 — backfill impossible, class (b)).

## Summary

| instrument | coverage | median bars/d | flagged days | (c) anomaly windows | worst anomaly |
|---|---|--:|--:|--:|---|
| GER40 | 2013-09-30→2026-06-05 | 1151 | 898 | 58 | 2019-12-30→2021-12-28 (522 wd, 8.5 b/d) |
| OJUICE | 2017-10-20→2026-06-05 | 240 | 149 | 52 | 2024-05-29→2024-06-03 (4 wd, 72.0 b/d) |
| XAGUSD | 2003-08-08→2026-06-05 | 1320 | 463 | 43 | 2004-12-14→2005-01-03 (15 wd, 458.1 b/d) |
| UKOIL | 2010-12-02→2026-06-05 | 1233 | 251 | 37 | 2011-10-19→2012-01-19 (67 wd, 6.3 b/d) |
| USOIL | 2013-01-01→2026-06-05 | 1315 | 101 | 32 | 2014-06-09→2014-06-16 (6 wd, 232.5 b/d) |
| SUGAR | 2017-10-02→2026-06-05 | 492 | 106 | 21 | 2017-11-15→2017-11-16 (2 wd, 0.0 b/d) |
| US500 | 2012-01-16→2026-06-05 | 841 | 1344 | 20 | 2018-01-01→2021-09-13 (966 wd, 4.5 b/d) |
| COCOA | 2017-10-20→2026-06-05 | 476 | 132 | 12 | 2018-03-14→2018-05-07 (39 wd, 4.6 b/d) |
| COFFEE | 2017-12-04→2026-06-05 | 535 | 97 | 12 | 2018-02-05→2018-02-05 (1 wd, 207.0 b/d) |
| COPPER | 2012-03-02→2026-06-07 | 1228 | 72 | 11 | 2012-07-16→2012-07-16 (1 wd, 572.0 b/d) |
| AUDUSD | 2007-01-01→2026-06-05 | 1439 | 42 | 9 | 2007-10-18→2007-10-19 (2 wd, 650.5 b/d) |
| US100 | 2013-01-01→2026-06-05 | 898 | 1119 | 7 | 2018-01-01→2021-09-13 (966 wd, 4.5 b/d) |
| COTTON | 2017-10-20→2026-06-05 | 826 | 117 | 6 | 2019-02-28→2019-03-04 (3 wd, 1.7 b/d) |
| SOYBEAN | 2017-12-01→2026-06-05 | 867 | 143 | 5 | 2018-02-02→2018-02-05 (2 wd, 391.0 b/d) |
| US30 | 2013-09-30→2026-06-05 | 1318 | 92 | 5 | 2014-01-27→2014-02-07 (10 wd, 337.1 b/d) |
| DIESEL | 2017-12-26→2026-06-05 | 1144 | 37 | 3 | 2018-04-12→2018-04-17 (4 wd, 58.8 b/d) |
| EURGBP | 2007-01-01→2026-06-05 | 1440 | 26 | 1 | 2018-01-04→2018-01-08 (3 wd, 0.0 b/d) |
| NGAS | 2012-09-02→2026-06-05 | 1041 | 54 | 1 | 2016-10-19→2016-10-19 (1 wd, 371.0 b/d) |
| AUDJPY | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| EURJPY | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| EURUSD | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| GBPUSD | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| NZDUSD | 2007-01-01→2026-06-05 | 1438 | 22 | 0 | — |
| USDCAD | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| USDCHF | 2007-01-01→2026-06-05 | 1437 | 22 | 0 | — |
| USDJPY | 2007-01-01→2026-06-05 | 1440 | 21 | 0 | — |
| XAUUSD | 2007-01-01→2026-06-05 | 1371 | 51 | 0 | — |

## AUDJPY

rows 7,264,227 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1440, 2014: 1440, 2015: 1440, 2016: 1440, 2017: 1440, 2018: 1439, 2019: 1439, 2020: 1436, 2021: 1436, 2022: 1439, 2023: 1438, 2024: 1440, 2025: 1436, 2026: 1435


(+21 single-day holiday/floor flags not listed)

## AUDUSD

rows 7,125,523 · coverage 2007-01-01 → 2026-06-05 · median 1439 bars/day · threshold 719.5 · flagged 42 days

yearly median bars/day: 2007: 1238, 2008: 1365, 2009: 1392, 2010: 1418, 2011: 1440, 2012: 1440, 2013: 1439, 2014: 1437, 2015: 1440, 2016: 1440, 2017: 1440, 2018: 1440, 2019: 1440, 2020: 1439, 2021: 1439, 2022: 1439, 2023: 1438, 2024: 1440, 2025: 1434, 2026: 1434

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2007-04-20 → 2007-04-20 | 1 | 0 | 650.0 | (c) ANOMALY | low density, unexplained |
| 2007-05-18 → 2007-05-18 | 1 | 0 | 714.0 | (c) ANOMALY | low density, unexplained |
| 2007-05-25 → 2007-05-28 | 2 | 0 | 593.0 | (a) holiday | 1/2 days on holiday calendar |
| 2007-06-15 → 2007-06-15 | 1 | 0 | 684.0 | (c) ANOMALY | low density, unexplained |
| 2007-06-22 → 2007-06-22 | 1 | 0 | 701.0 | (c) ANOMALY | low density, unexplained |
| 2007-07-06 → 2007-07-06 | 1 | 0 | 659.0 | (c) ANOMALY | low density, unexplained |
| 2007-07-13 → 2007-07-13 | 1 | 0 | 707.0 | (c) ANOMALY | low density, unexplained |
| 2007-10-18 → 2007-10-19 | 2 | 0 | 650.5 | (c) ANOMALY | low density, unexplained |
| 2007-10-25 → 2007-10-25 | 1 | 0 | 633.0 | (c) ANOMALY | low density, unexplained |
| 2007-12-24 → 2007-12-26 | 3 | 1 | 159.3 | (a) holiday | 3/3 days on holiday calendar |
| 2007-12-31 → 2008-01-01 | 2 | 1 | 312.0 | (a) holiday | 2/2 days on holiday calendar |
| 2010-01-22 → 2010-01-22 | 1 | 0 | 251.0 | (c) ANOMALY | low density, unexplained |

(+25 single-day holiday/floor flags not listed)

## COCOA

rows 1,006,658 · coverage 2017-10-20 → 2026-06-05 · median 476 bars/day · threshold 238.0 · flagged 132 days

yearly median bars/day: 2017: 522, 2018: 486, 2019: 446, 2020: 491, 2021: 444, 2022: 443, 2023: 468, 2024: 518, 2025: 518, 2026: 515

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2018-03-09 → 2018-03-09 | 1 | 0 | 90.0 | (c) ANOMALY | low density, unexplained |
| 2018-03-14 → 2018-05-07 | 39 | 7 | 4.6 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-11 → 2019-03-11 | 1 | 0 | 94.0 | (c) ANOMALY | low density, unexplained |
| 2020-05-08 → 2020-05-08 | 1 | 0 | 81.0 | (c) ANOMALY | low density, unexplained |
| 2020-08-31 → 2020-08-31 | 1 | 0 | 218.0 | (c) ANOMALY | low density, unexplained |
| 2021-08-30 → 2021-08-30 | 1 | 0 | 183.0 | (c) ANOMALY | low density, unexplained |
| 2021-12-24 → 2021-12-27 | 2 | 1 | 104.5 | (a) holiday | 2/2 days on holiday calendar |
| 2022-01-03 → 2022-01-03 | 1 | 0 | 204.0 | (c) ANOMALY | low density, unexplained |
| 2022-03-28 → 2022-03-28 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-08-29 → 2022-08-29 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-08-26 → 2024-08-26 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-08-25 → 2025-08-25 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-05-04 → 2026-05-04 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |

(+80 single-day holiday/floor flags not listed)

## COFFEE

rows 1,108,493 · coverage 2017-12-04 → 2026-06-05 · median 535 bars/day · threshold 267.5 · flagged 97 days

yearly median bars/day: 2017: 564, 2018: 503, 2019: 480, 2020: 526, 2021: 532, 2022: 533, 2023: 535, 2024: 549, 2025: 552, 2026: 550

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2018-02-05 → 2018-02-05 | 1 | 0 | 207.0 | (c) ANOMALY | low density, unexplained |
| 2018-11-22 → 2018-11-26 | 3 | 2 | 64.7 | (a) holiday | 2/3 days on holiday calendar |
| 2019-03-04 → 2019-03-04 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-15 → 2019-03-15 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2020-05-08 → 2020-05-08 | 1 | 0 | 80.0 | (c) ANOMALY | low density, unexplained |
| 2020-08-31 → 2020-08-31 | 1 | 0 | 238.0 | (c) ANOMALY | low density, unexplained |
| 2021-08-30 → 2021-08-30 | 1 | 0 | 238.0 | (c) ANOMALY | low density, unexplained |
| 2021-12-24 → 2021-12-27 | 2 | 1 | 114.5 | (a) holiday | 2/2 days on holiday calendar |
| 2022-01-03 → 2022-01-03 | 1 | 0 | 238.0 | (c) ANOMALY | low density, unexplained |
| 2022-03-29 → 2022-03-29 | 1 | 0 | 205.0 | (c) ANOMALY | low density, unexplained |
| 2022-08-29 → 2022-08-29 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-01-15 → 2024-01-16 | 2 | 2 | 0.0 | (a) holiday | 1/2 days on holiday calendar |
| 2024-08-26 → 2024-08-26 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-08-25 → 2025-08-25 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-05-04 → 2026-05-04 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |

(+78 single-day holiday/floor flags not listed)

## COPPER

rows 4,325,524 · coverage 2012-03-02 → 2026-06-07 · median 1228 bars/day · threshold 614.0 · flagged 72 days

yearly median bars/day: 2012: 1041, 2013: 928, 2014: 768, 2015: 906, 2016: 1096, 2017: 1119, 2018: 1288, 2019: 1206, 2020: 1296, 2021: 1344, 2022: 1361, 2023: 1312, 2024: 1328, 2025: 1361, 2026: 1372

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2012-07-16 → 2012-07-16 | 1 | 0 | 572.0 | (c) ANOMALY | low density, unexplained |
| 2012-12-24 → 2012-12-26 | 3 | 1 | 331.7 | (a) holiday | 3/3 days on holiday calendar |
| 2012-12-31 → 2013-01-01 | 2 | 1 | 306.5 | (a) holiday | 2/2 days on holiday calendar |
| 2013-10-02 → 2013-10-02 | 1 | 0 | 5.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-12-24 → 2013-12-26 | 3 | 0 | 292.7 | (a) holiday | 3/3 days on holiday calendar |
| 2013-12-31 → 2014-01-02 | 3 | 1 | 378.7 | (a) holiday | 2/3 days on holiday calendar |
| 2014-02-21 → 2014-02-21 | 1 | 0 | 612.0 | (c) ANOMALY | low density, unexplained |
| 2014-04-18 → 2014-04-21 | 2 | 1 | 294.5 | (a) holiday | 2/2 days on holiday calendar |
| 2014-05-05 → 2014-05-05 | 1 | 0 | 610.0 | (c) ANOMALY | low density, unexplained |
| 2014-08-19 → 2014-08-19 | 1 | 0 | 581.0 | (c) ANOMALY | low density, unexplained |
| 2014-08-25 → 2014-08-25 | 1 | 0 | 483.0 | (c) ANOMALY | low density, unexplained |
| 2014-12-24 → 2014-12-26 | 3 | 2 | 183.0 | (a) holiday | 3/3 days on holiday calendar |
| 2015-01-01 → 2015-01-02 | 2 | 1 | 302.5 | (a) holiday | 1/2 days on holiday calendar |
| 2015-03-04 → 2015-03-04 | 1 | 0 | 450.0 | (c) ANOMALY | low density, unexplained |
| 2016-02-29 → 2016-02-29 | 1 | 0 | 1.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2016-08-31 → 2016-08-31 | 1 | 0 | 1.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2016-10-31 → 2016-10-31 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2016-11-14 → 2016-11-14 | 1 | 0 | 519.0 | (c) ANOMALY | low density, unexplained |

(+43 single-day holiday/floor flags not listed)

## COTTON

rows 1,758,811 · coverage 2017-10-20 → 2026-06-05 · median 826 bars/day · threshold 413.0 · flagged 117 days

yearly median bars/day: 2017: 579, 2018: 741, 2019: 756, 2020: 818, 2021: 828, 2022: 851, 2023: 889, 2024: 834, 2025: 851, 2026: 958

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2017-11-22 → 2017-11-24 | 3 | 2 | 73.3 | (a) holiday | 2/3 days on holiday calendar |
| 2017-12-25 → 2017-12-26 | 2 | 1 | 160.5 | (a) holiday | 2/2 days on holiday calendar |
| 2018-05-28 → 2018-05-29 | 2 | 1 | 63.5 | (a) holiday | 1/2 days on holiday calendar |
| 2018-11-22 → 2018-11-26 | 3 | 2 | 83.3 | (a) holiday | 2/3 days on holiday calendar |
| 2018-12-25 → 2018-12-26 | 2 | 1 | 184.5 | (a) holiday | 2/2 days on holiday calendar |
| 2019-02-28 → 2019-03-04 | 3 | 1 | 1.7 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-14 → 2019-03-15 | 2 | 2 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-11-28 → 2019-11-29 | 2 | 1 | 161.5 | (a) holiday | 2/2 days on holiday calendar |
| 2019-12-25 → 2019-12-26 | 2 | 1 | 185.5 | (a) holiday | 2/2 days on holiday calendar |
| 2020-11-26 → 2020-11-27 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2020-12-25 → 2020-12-28 | 2 | 1 | 182.0 | (a) holiday | 1/2 days on holiday calendar |
| 2021-05-03 → 2021-05-03 | 1 | 0 | 400.0 | (c) ANOMALY | low density, unexplained |
| 2021-11-25 → 2021-11-26 | 2 | 1 | 164.0 | (a) holiday | 2/2 days on holiday calendar |
| 2021-12-24 → 2021-12-27 | 2 | 1 | 144.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-01-03 → 2022-01-03 | 1 | 0 | 289.0 | (c) ANOMALY | low density, unexplained |
| 2022-04-15 → 2022-04-18 | 2 | 1 | 174.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-08-15 → 2022-08-15 | 1 | 0 | 3.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-11-24 → 2022-11-25 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-12-26 → 2022-12-27 | 2 | 1 | 198.5 | (a) holiday | 1/2 days on holiday calendar |
| 2023-07-04 → 2023-07-05 | 2 | 1 | 189.5 | (a) holiday | 1/2 days on holiday calendar |
| 2023-11-23 → 2023-11-24 | 2 | 1 | 134.0 | (a) holiday | 2/2 days on holiday calendar |
| 2023-12-25 → 2023-12-26 | 2 | 1 | 196.5 | (a) holiday | 2/2 days on holiday calendar |
| 2024-07-04 → 2024-07-05 | 2 | 1 | 189.0 | (a) holiday | 1/2 days on holiday calendar |
| 2024-11-28 → 2024-11-29 | 2 | 1 | 163.0 | (a) holiday | 2/2 days on holiday calendar |
| 2024-12-25 → 2024-12-26 | 2 | 1 | 197.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-04-03 → 2025-04-03 | 1 | 0 | 383.0 | (c) ANOMALY | low density, unexplained |
| 2025-07-04 → 2025-07-07 | 2 | 1 | 183.5 | (a) holiday | 1/2 days on holiday calendar |
| 2025-11-27 → 2025-11-28 | 2 | 1 | 149.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-12-25 → 2025-12-26 | 2 | 1 | 183.5 | (a) holiday | 2/2 days on holiday calendar |

(+60 single-day holiday/floor flags not listed)

## DIESEL

rows 2,434,631 · coverage 2017-12-26 → 2026-06-05 · median 1144 bars/day · threshold 572.0 · flagged 37 days

yearly median bars/day: 2017: 1132, 2018: 1195, 2019: 1194, 2020: 1193, 2021: 1059, 2022: 1178, 2023: 1137, 2024: 1108, 2025: 1093, 2026: 1228

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2018-04-12 → 2018-04-17 | 4 | 3 | 58.8 | (c) ANOMALY | low density, unexplained |
| 2018-06-11 → 2018-06-11 | 1 | 0 | 531.0 | (c) ANOMALY | low density, unexplained |
| 2018-12-24 → 2018-12-25 | 2 | 1 | 272.0 | (a) holiday | 2/2 days on holiday calendar |
| 2018-12-31 → 2019-01-01 | 2 | 1 | 250.5 | (a) holiday | 2/2 days on holiday calendar |
| 2020-08-31 → 2020-08-31 | 1 | 0 | 378.0 | (c) ANOMALY | low density, unexplained |
| 2023-12-25 → 2023-12-26 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2024-12-24 → 2024-12-25 | 2 | 1 | 244.5 | (a) holiday | 2/2 days on holiday calendar |
| 2024-12-31 → 2025-01-01 | 2 | 1 | 285.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-12-24 → 2025-12-25 | 2 | 1 | 269.5 | (a) holiday | 2/2 days on holiday calendar |

(+19 single-day holiday/floor flags not listed)

## EURGBP

rows 7,252,687 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 26 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1439, 2014: 1439, 2015: 1440, 2016: 1440, 2017: 1440, 2018: 1440, 2019: 1438, 2020: 1436, 2021: 1429, 2022: 1439, 2023: 1438, 2024: 1439, 2025: 1433, 2026: 1432

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2018-01-01 → 2018-01-02 | 2 | 2 | 0.0 | (a) holiday | 1/2 days on holiday calendar |
| 2018-01-04 → 2018-01-08 | 3 | 3 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2020-01-01 → 2020-01-02 | 2 | 1 | 59.0 | (a) holiday | 1/2 days on holiday calendar |

(+19 single-day holiday/floor flags not listed)

## EURJPY

rows 7,263,644 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1440, 2014: 1440, 2015: 1440, 2016: 1440, 2017: 1440, 2018: 1440, 2019: 1440, 2020: 1437, 2021: 1433, 2022: 1438, 2023: 1437, 2024: 1440, 2025: 1436, 2026: 1435


(+21 single-day holiday/floor flags not listed)

## EURUSD

rows 7,259,299 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1437, 2014: 1433, 2015: 1439, 2016: 1439, 2017: 1440, 2018: 1440, 2019: 1440, 2020: 1440, 2021: 1440, 2022: 1440, 2023: 1439, 2024: 1440, 2025: 1430, 2026: 1430


(+21 single-day holiday/floor flags not listed)

## GBPUSD

rows 7,260,253 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1438, 2014: 1439, 2015: 1440, 2016: 1440, 2017: 1440, 2018: 1440, 2019: 1439, 2020: 1439, 2021: 1428, 2022: 1439, 2023: 1437, 2024: 1440, 2025: 1432, 2026: 1432


(+21 single-day holiday/floor flags not listed)

## GER40

rows 2,834,721 · coverage 2013-09-30 → 2026-06-05 · median 1151 bars/day · threshold 575.5 · flagged 898 days

yearly median bars/day: 2013: 1260, 2014: 1317, 2015: 841, 2016: 840, 2017: 839, 2018: 1118, 2019: 1, 2020: 1, 2021: 23, 2022: 1342, 2023: 1348, 2024: 1344, 2025: 1354, 2026: 1360

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2013-09-30 → 2013-10-16 | 13 | 0 | 354.8 | (b) floor | start-of-history ramp |
| 2013-12-24 → 2013-12-26 | 3 | 0 | 99.7 | (a) holiday | 3/3 days on holiday calendar |
| 2013-12-31 → 2014-01-01 | 2 | 0 | 98.5 | (a) holiday | 2/2 days on holiday calendar |
| 2014-01-27 → 2014-02-06 | 9 | 0 | 510.9 | (c) ANOMALY | low density, unexplained |
| 2014-08-01 → 2014-08-01 | 1 | 0 | 537.0 | (c) ANOMALY | low density, unexplained |
| 2014-12-24 → 2014-12-26 | 3 | 3 | 0.0 | (a) holiday | 3/3 days on holiday calendar |
| 2014-12-31 → 2015-01-01 | 2 | 1 | 25.0 | (a) holiday | 2/2 days on holiday calendar |
| 2015-04-03 → 2015-04-06 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2015-12-24 → 2015-12-25 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2015-12-31 → 2016-01-01 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2016-03-25 → 2016-03-28 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2016-10-03 → 2016-10-03 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2017-04-14 → 2017-04-17 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2017-10-03 → 2017-10-03 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-01-01 → 2018-03-28 | 63 | 12 | 0.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-03-30 → 2018-05-31 | 45 | 9 | 1.4 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-10-03 → 2018-10-03 | 1 | 0 | 76.0 | (c) ANOMALY | low density, unexplained |
| 2018-12-17 → 2018-12-20 | 4 | 0 | 15.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-12-24 → 2018-12-27 | 4 | 2 | 15.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-12-31 → 2019-01-03 | 4 | 1 | 15.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-01-07 → 2019-01-10 | 4 | 0 | 14.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-01-14 → 2019-01-17 | 4 | 0 | 14.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-01-21 → 2019-01-24 | 4 | 0 | 13.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-01-28 → 2019-01-31 | 4 | 0 | 15.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-02-04 → 2019-02-07 | 4 | 0 | 15.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-02-11 → 2019-02-14 | 4 | 0 | 14.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-02-18 → 2019-02-21 | 4 | 0 | 13.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-02-25 → 2019-02-27 | 3 | 0 | 15.7 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-05 → 2019-03-07 | 3 | 0 | 11.3 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-11 → 2019-03-14 | 4 | 0 | 8.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-18 → 2019-03-21 | 4 | 0 | 13.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-03-25 → 2019-03-28 | 4 | 0 | 13.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-04-01 → 2019-04-04 | 4 | 0 | 12.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-04-08 → 2019-04-11 | 4 | 0 | 11.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-04-15 → 2019-04-17 | 3 | 0 | 9.3 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-04-23 → 2019-04-25 | 3 | 0 | 15.3 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-04-29 → 2019-05-02 | 4 | 1 | 9.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-05-06 → 2019-05-09 | 4 | 0 | 14.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-05-13 → 2019-05-16 | 4 | 0 | 11.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-05-20 → 2019-05-23 | 4 | 0 | 13.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-05-27 → 2019-05-30 | 4 | 0 | 12.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-06-03 → 2019-06-06 | 4 | 0 | 14.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-06-10 → 2019-06-13 | 4 | 0 | 12.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-06-17 → 2019-06-20 | 4 | 0 | 13.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-06-24 → 2019-06-27 | 4 | 0 | 8.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-07-01 → 2019-07-04 | 4 | 0 | 6.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-07-08 → 2019-07-11 | 4 | 0 | 9.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-07-15 → 2019-07-18 | 4 | 0 | 13.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-07-22 → 2019-07-25 | 4 | 0 | 8.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-07-29 → 2019-08-01 | 4 | 0 | 15.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-08-05 → 2019-08-08 | 4 | 0 | 15.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-09-12 → 2019-09-12 | 1 | 0 | 31.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-09-16 → 2019-09-19 | 4 | 0 | 10.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-09-23 → 2019-09-26 | 4 | 0 | 12.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-09-30 → 2019-10-03 | 4 | 0 | 11.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-10-07 → 2019-10-10 | 4 | 0 | 15.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-10-14 → 2019-10-17 | 4 | 0 | 12.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-10-21 → 2019-10-24 | 4 | 0 | 12.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-10-28 → 2019-10-31 | 4 | 0 | 9.2 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-11-04 → 2019-11-07 | 4 | 0 | 12.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-11-11 → 2019-11-14 | 4 | 0 | 10.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-11-18 → 2019-11-21 | 4 | 0 | 10.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-11-25 → 2019-11-28 | 4 | 0 | 8.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-02 → 2019-12-05 | 4 | 0 | 9.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-09 → 2019-12-12 | 4 | 0 | 15.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-16 → 2019-12-19 | 4 | 0 | 10.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-23 → 2019-12-26 | 4 | 0 | 8.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-30 → 2021-12-28 | 522 | 78 | 8.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-04-15 → 2022-04-18 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2023-04-07 → 2023-04-10 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2023-12-25 → 2023-12-26 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-04-18 → 2025-04-21 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-12-24 → 2025-12-26 | 3 | 3 | 0.0 | (a) holiday | 3/3 days on holiday calendar |
| 2025-12-31 → 2026-01-01 | 2 | 1 | 28.5 | (a) holiday | 2/2 days on holiday calendar |

(+16 single-day holiday/floor flags not listed)

## NGAS

rows 3,725,891 · coverage 2012-09-02 → 2026-06-05 · median 1041 bars/day · threshold 520.5 · flagged 54 days

yearly median bars/day: 2012: 929, 2013: 898, 2014: 936, 2015: 891, 2016: 964, 2017: 1007, 2018: 903, 2019: 966, 2020: 1157, 2021: 1111, 2022: 1245, 2023: 1123, 2024: 1051, 2025: 1172, 2026: 1200

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2013-12-24 → 2013-12-25 | 2 | 0 | 256.0 | (a) holiday | 2/2 days on holiday calendar |
| 2013-12-31 → 2014-01-01 | 2 | 0 | 253.5 | (a) holiday | 2/2 days on holiday calendar |
| 2014-12-25 → 2014-12-26 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2016-10-19 → 2016-10-19 | 1 | 0 | 371.0 | (c) ANOMALY | low density, unexplained |

(+47 single-day holiday/floor flags not listed)

## NZDUSD

rows 7,250,320 · coverage 2007-01-01 → 2026-06-05 · median 1438 bars/day · threshold 719.0 · flagged 22 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1438, 2013: 1438, 2014: 1439, 2015: 1439, 2016: 1438, 2017: 1439, 2018: 1437, 2019: 1438, 2020: 1432, 2021: 1423, 2022: 1438, 2023: 1438, 2024: 1439, 2025: 1435, 2026: 1432


(+22 single-day holiday/floor flags not listed)

## OJUICE

rows 511,864 · coverage 2017-10-20 → 2026-06-05 · median 240 bars/day · threshold 120.0 · flagged 149 days

yearly median bars/day: 2017: 185, 2018: 224, 2019: 257, 2020: 239, 2021: 228, 2022: 215, 2023: 237, 2024: 273, 2025: 271, 2026: 272

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2017-11-23 → 2017-11-24 | 2 | 1 | 42.0 | (a) holiday | 2/2 days on holiday calendar |
| 2018-12-03 → 2018-12-03 | 1 | 0 | 100.0 | (c) ANOMALY | low density, unexplained |
| 2019-01-17 → 2019-01-21 | 3 | 2 | 3.7 | (a) holiday | 1/3 days on holiday calendar |
| 2019-02-08 → 2019-02-08 | 1 | 0 | 115.0 | (c) ANOMALY | low density, unexplained |
| 2019-03-15 → 2019-03-15 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2021-12-30 → 2021-12-30 | 1 | 0 | 112.0 | (c) ANOMALY | low density, unexplained |
| 2022-01-14 → 2022-01-17 | 2 | 2 | 0.0 | (a) holiday | 1/2 days on holiday calendar |
| 2022-03-07 → 2022-03-07 | 1 | 0 | 58.0 | (c) ANOMALY | low density, unexplained |
| 2022-03-28 → 2022-03-29 | 2 | 1 | 17.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-04-13 → 2022-04-13 | 1 | 0 | 103.0 | (c) ANOMALY | low density, unexplained |
| 2022-10-18 → 2022-10-18 | 1 | 0 | 46.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-02-10 → 2023-02-10 | 1 | 0 | 41.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-07-21 → 2023-07-21 | 1 | 0 | 113.0 | (c) ANOMALY | low density, unexplained |
| 2023-08-02 → 2023-08-02 | 1 | 0 | 90.0 | (c) ANOMALY | low density, unexplained |
| 2023-08-15 → 2023-08-16 | 2 | 0 | 68.5 | (c) ANOMALY | low density, unexplained |
| 2023-09-08 → 2023-09-08 | 1 | 0 | 89.0 | (c) ANOMALY | low density, unexplained |
| 2023-10-05 → 2023-10-05 | 1 | 0 | 98.0 | (c) ANOMALY | low density, unexplained |
| 2023-11-01 → 2023-11-01 | 1 | 0 | 21.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-11-16 → 2023-11-16 | 1 | 0 | 80.0 | (c) ANOMALY | low density, unexplained |
| 2023-11-30 → 2023-11-30 | 1 | 0 | 37.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-12-20 → 2023-12-21 | 2 | 0 | 48.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-01-04 → 2024-01-04 | 1 | 0 | 84.0 | (c) ANOMALY | low density, unexplained |
| 2024-01-08 → 2024-01-08 | 1 | 0 | 82.0 | (c) ANOMALY | low density, unexplained |
| 2024-01-26 → 2024-01-29 | 2 | 0 | 70.0 | (c) ANOMALY | low density, unexplained |
| 2024-02-07 → 2024-02-07 | 1 | 0 | 33.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-02-09 → 2024-02-12 | 2 | 0 | 33.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-02-21 → 2024-02-21 | 1 | 0 | 74.0 | (c) ANOMALY | low density, unexplained |
| 2024-02-27 → 2024-02-28 | 2 | 0 | 57.5 | (c) ANOMALY | low density, unexplained |
| 2024-03-08 → 2024-03-08 | 1 | 0 | 21.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-03-18 → 2024-03-18 | 1 | 0 | 78.0 | (c) ANOMALY | low density, unexplained |
| 2024-04-05 → 2024-04-05 | 1 | 0 | 114.0 | (c) ANOMALY | low density, unexplained |
| 2024-04-09 → 2024-04-09 | 1 | 0 | 106.0 | (c) ANOMALY | low density, unexplained |
| 2024-04-11 → 2024-04-11 | 1 | 0 | 92.0 | (c) ANOMALY | low density, unexplained |
| 2024-04-16 → 2024-04-16 | 1 | 0 | 95.0 | (c) ANOMALY | low density, unexplained |
| 2024-05-09 → 2024-05-09 | 1 | 0 | 23.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-05-13 → 2024-05-13 | 1 | 0 | 93.0 | (c) ANOMALY | low density, unexplained |
| 2024-05-29 → 2024-06-03 | 4 | 0 | 72.0 | (c) ANOMALY | low density, unexplained |
| 2024-06-06 → 2024-06-06 | 1 | 0 | 9.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-12-20 → 2024-12-20 | 1 | 0 | 84.0 | (c) ANOMALY | low density, unexplained |
| 2025-04-11 → 2025-04-11 | 1 | 0 | 118.0 | (c) ANOMALY | low density, unexplained |
| 2025-05-22 → 2025-05-22 | 1 | 0 | 74.0 | (c) ANOMALY | low density, unexplained |
| 2025-07-04 → 2025-07-07 | 2 | 1 | 50.5 | (a) holiday | 1/2 days on holiday calendar |
| 2025-07-10 → 2025-07-11 | 2 | 1 | 9.5 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-07-31 → 2025-07-31 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-08-28 → 2025-08-28 | 1 | 0 | 114.0 | (c) ANOMALY | low density, unexplained |
| 2025-09-17 → 2025-09-17 | 1 | 0 | 104.0 | (c) ANOMALY | low density, unexplained |
| 2026-01-30 → 2026-01-30 | 1 | 0 | 10.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-02-09 → 2026-02-09 | 1 | 0 | 68.0 | (c) ANOMALY | low density, unexplained |
| 2026-02-11 → 2026-02-11 | 1 | 0 | 48.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-02-24 → 2026-02-24 | 1 | 0 | 41.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-03-03 → 2026-03-03 | 1 | 0 | 96.0 | (c) ANOMALY | low density, unexplained |
| 2026-03-18 → 2026-03-18 | 1 | 0 | 58.0 | (c) ANOMALY | low density, unexplained |
| 2026-03-24 → 2026-03-24 | 1 | 0 | 24.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-04-17 → 2026-04-17 | 1 | 0 | 45.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2026-05-08 → 2026-05-08 | 1 | 0 | 77.0 | (c) ANOMALY | low density, unexplained |
| 2026-05-14 → 2026-05-14 | 1 | 0 | 18.0 | (c) ANOMALY | hole (zero/stray bars) |

(+78 single-day holiday/floor flags not listed)

## SOYBEAN

rows 1,779,222 · coverage 2017-12-01 → 2026-06-05 · median 867 bars/day · threshold 433.5 · flagged 143 days

yearly median bars/day: 2017: 1024, 2018: 771, 2019: 819, 2020: 917, 2021: 929, 2022: 958, 2023: 901, 2024: 804, 2025: 759, 2026: 787

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2017-12-25 → 2018-01-29 | 26 | 4 | 216.3 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2018-02-02 → 2018-02-05 | 2 | 0 | 391.0 | (c) ANOMALY | low density, unexplained |
| 2018-02-09 → 2018-02-09 | 1 | 0 | 406.0 | (c) ANOMALY | low density, unexplained |
| 2018-02-15 → 2018-02-19 | 3 | 1 | 239.0 | (a) holiday | 1/3 days on holiday calendar |
| 2018-07-04 → 2018-07-05 | 2 | 1 | 135.5 | (a) holiday | 1/2 days on holiday calendar |
| 2018-11-22 → 2018-11-23 | 2 | 1 | 107.5 | (a) holiday | 2/2 days on holiday calendar |
| 2018-12-25 → 2018-12-26 | 2 | 1 | 142.0 | (a) holiday | 2/2 days on holiday calendar |
| 2019-01-01 → 2019-01-02 | 2 | 1 | 142.0 | (a) holiday | 1/2 days on holiday calendar |
| 2019-02-01 → 2019-02-01 | 1 | 0 | 238.0 | (c) ANOMALY | low density, unexplained |
| 2019-07-04 → 2019-07-05 | 2 | 1 | 141.0 | (a) holiday | 1/2 days on holiday calendar |
| 2019-11-28 → 2019-11-29 | 2 | 1 | 107.0 | (a) holiday | 2/2 days on holiday calendar |
| 2019-12-25 → 2019-12-26 | 2 | 1 | 143.5 | (a) holiday | 2/2 days on holiday calendar |
| 2020-01-01 → 2020-01-02 | 2 | 1 | 145.0 | (a) holiday | 1/2 days on holiday calendar |
| 2020-11-26 → 2020-11-27 | 2 | 1 | 96.0 | (a) holiday | 2/2 days on holiday calendar |
| 2020-12-25 → 2020-12-28 | 2 | 1 | 136.0 | (a) holiday | 1/2 days on holiday calendar |
| 2021-01-01 → 2021-01-04 | 2 | 1 | 137.0 | (a) holiday | 1/2 days on holiday calendar |
| 2021-07-05 → 2021-07-06 | 2 | 1 | 144.5 | (a) holiday | 1/2 days on holiday calendar |
| 2021-11-25 → 2021-11-26 | 2 | 1 | 106.0 | (a) holiday | 2/2 days on holiday calendar |
| 2021-12-24 → 2021-12-27 | 2 | 1 | 143.5 | (a) holiday | 2/2 days on holiday calendar |
| 2022-07-04 → 2022-07-05 | 2 | 1 | 144.5 | (a) holiday | 1/2 days on holiday calendar |
| 2022-11-24 → 2022-11-25 | 2 | 1 | 106.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-12-26 → 2022-12-27 | 2 | 1 | 144.5 | (a) holiday | 1/2 days on holiday calendar |
| 2023-01-02 → 2023-01-03 | 2 | 1 | 144.5 | (a) holiday | 1/2 days on holiday calendar |
| 2023-07-04 → 2023-07-05 | 2 | 1 | 144.5 | (a) holiday | 1/2 days on holiday calendar |
| 2023-11-23 → 2023-11-24 | 2 | 1 | 76.5 | (a) holiday | 2/2 days on holiday calendar |
| 2023-12-25 → 2023-12-26 | 2 | 1 | 143.5 | (a) holiday | 2/2 days on holiday calendar |
| 2024-01-01 → 2024-01-02 | 2 | 1 | 142.5 | (a) holiday | 1/2 days on holiday calendar |
| 2024-07-04 → 2024-07-05 | 2 | 2 | 0.0 | (a) holiday | 1/2 days on holiday calendar |
| 2024-11-28 → 2024-11-29 | 2 | 1 | 105.5 | (a) holiday | 2/2 days on holiday calendar |
| 2024-12-25 → 2024-12-26 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-01-01 → 2025-01-02 | 2 | 1 | 144.0 | (a) holiday | 1/2 days on holiday calendar |
| 2025-01-09 → 2025-01-09 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-09-29 → 2025-09-29 | 1 | 0 | 352.0 | (c) ANOMALY | low density, unexplained |
| 2025-11-27 → 2025-11-28 | 2 | 1 | 93.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-12-25 → 2025-12-26 | 2 | 1 | 121.0 | (a) holiday | 2/2 days on holiday calendar |
| 2026-01-01 → 2026-01-02 | 2 | 1 | 130.0 | (a) holiday | 1/2 days on holiday calendar |

(+50 single-day holiday/floor flags not listed)

## SUGAR

rows 1,047,541 · coverage 2017-10-02 → 2026-06-05 · median 492 bars/day · threshold 246.0 · flagged 106 days

yearly median bars/day: 2017: 435, 2018: 453, 2019: 430, 2020: 474, 2021: 488, 2022: 491, 2023: 519, 2024: 529, 2025: 519, 2026: 517

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2017-11-15 → 2017-11-16 | 2 | 2 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2017-12-22 → 2017-12-26 | 3 | 2 | 50.0 | (a) holiday | 2/3 days on holiday calendar |
| 2017-12-29 → 2018-01-01 | 2 | 1 | 70.5 | (a) holiday | 1/2 days on holiday calendar |
| 2018-03-30 → 2018-04-02 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2018-05-07 → 2018-05-07 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-08-27 → 2018-08-27 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2018-11-22 → 2018-11-26 | 3 | 1 | 64.3 | (a) holiday | 2/3 days on holiday calendar |
| 2018-12-24 → 2018-12-26 | 3 | 2 | 55.0 | (a) holiday | 3/3 days on holiday calendar |
| 2019-03-11 → 2019-03-11 | 1 | 0 | 185.0 | (c) ANOMALY | low density, unexplained |
| 2019-04-19 → 2019-04-22 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2019-05-06 → 2019-05-06 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-08-26 → 2019-08-26 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2019-12-24 → 2019-12-26 | 3 | 2 | 41.3 | (a) holiday | 3/3 days on holiday calendar |
| 2020-04-10 → 2020-04-13 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2020-05-08 → 2020-05-08 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2020-08-31 → 2020-08-31 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2020-12-24 → 2020-12-28 | 3 | 2 | 54.3 | (a) holiday | 2/3 days on holiday calendar |
| 2021-04-02 → 2021-04-05 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2021-05-03 → 2021-05-03 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2021-08-30 → 2021-08-30 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2021-12-24 → 2021-12-27 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-01-03 → 2022-01-03 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-04-15 → 2022-04-18 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2022-06-02 → 2022-06-03 | 2 | 2 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-06-20 → 2022-06-21 | 2 | 0 | 145.5 | (a) holiday | 1/2 days on holiday calendar |
| 2022-08-29 → 2022-08-29 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-09-19 → 2022-09-19 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2022-12-23 → 2022-12-27 | 3 | 2 | 67.7 | (a) holiday | 2/3 days on holiday calendar |
| 2023-04-07 → 2023-04-10 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2023-05-08 → 2023-05-08 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-08-28 → 2023-08-28 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2023-12-22 → 2023-12-26 | 3 | 2 | 69.7 | (a) holiday | 2/3 days on holiday calendar |
| 2024-03-29 → 2024-04-01 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2024-05-06 → 2024-05-06 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-08-26 → 2024-08-26 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2024-12-24 → 2024-12-26 | 3 | 2 | 67.3 | (a) holiday | 3/3 days on holiday calendar |
| 2025-04-18 → 2025-04-21 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2025-05-05 → 2025-05-05 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-08-25 → 2025-08-25 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2025-12-24 → 2025-12-26 | 3 | 2 | 56.7 | (a) holiday | 3/3 days on holiday calendar |
| 2026-04-03 → 2026-04-06 | 2 | 2 | 0.0 | (a) holiday | 2/2 days on holiday calendar |
| 2026-05-04 → 2026-05-04 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |

(+32 single-day holiday/floor flags not listed)

## UKOIL

rows 4,579,620 · coverage 2010-12-02 → 2026-06-05 · median 1233 bars/day · threshold 616.5 · flagged 251 days

yearly median bars/day: 2010: 1115, 2011: 1160, 2012: 1274, 2013: 970, 2014: 1177, 2015: 1168, 2016: 1177, 2017: 1122, 2018: 1234, 2019: 1237, 2020: 1249, 2021: 1254, 2022: 1260, 2023: 1251, 2024: 1240, 2025: 1239, 2026: 1260

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2011-10-19 → 2012-01-19 | 67 | 66 | 6.3 | (c) ANOMALY | hole (zero/stray bars) |
| 2012-02-15 → 2012-03-15 | 22 | 20 | 15.8 | (c) ANOMALY | hole (zero/stray bars) |
| 2012-05-17 → 2012-05-18 | 2 | 0 | 213.5 | (c) ANOMALY | low density, unexplained |
| 2012-06-15 → 2012-06-19 | 3 | 1 | 176.0 | (c) ANOMALY | low density, unexplained |
| 2012-07-17 → 2012-07-19 | 3 | 2 | 168.3 | (c) ANOMALY | low density, unexplained |
| 2012-08-17 → 2012-08-20 | 2 | 1 | 1.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2012-09-14 → 2012-09-20 | 5 | 3 | 98.8 | (c) ANOMALY | low density, unexplained |
| 2012-10-17 → 2012-10-19 | 3 | 2 | 106.3 | (c) ANOMALY | low density, unexplained |
| 2012-11-16 → 2012-11-16 | 1 | 0 | 8.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2012-12-17 → 2012-12-28 | 10 | 5 | 46.4 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-01-17 → 2013-01-31 | 11 | 8 | 1.4 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-02-14 → 2013-02-27 | 10 | 5 | 96.4 | (c) ANOMALY | low density, unexplained |
| 2013-03-11 → 2013-03-15 | 5 | 1 | 412.8 | (c) ANOMALY | low density, unexplained |
| 2013-03-19 → 2013-04-01 | 10 | 1 | 473.5 | (c) ANOMALY | low density, unexplained |
| 2013-04-12 → 2013-04-15 | 2 | 0 | 543.5 | (c) ANOMALY | low density, unexplained |
| 2013-04-18 → 2013-04-19 | 2 | 1 | 162.5 | (c) ANOMALY | low density, unexplained |
| 2013-04-24 → 2013-04-24 | 1 | 0 | 597.0 | (c) ANOMALY | low density, unexplained |
| 2013-05-02 → 2013-05-14 | 9 | 9 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-05-16 → 2013-05-22 | 5 | 2 | 125.6 | (c) ANOMALY | low density, unexplained |
| 2013-06-03 → 2013-06-03 | 1 | 0 | 425.0 | (c) ANOMALY | low density, unexplained |
| 2013-08-12 → 2013-08-12 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-08-26 → 2013-08-26 | 1 | 0 | 268.0 | (c) ANOMALY | low density, unexplained |
| 2013-09-30 → 2013-09-30 | 1 | 0 | 586.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-03 → 2013-10-03 | 1 | 0 | 382.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-14 → 2013-10-16 | 3 | 0 | 304.3 | (c) ANOMALY | low density, unexplained |
| 2013-11-06 → 2013-11-06 | 1 | 0 | 38.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-11-13 → 2013-11-14 | 2 | 0 | 372.5 | (c) ANOMALY | low density, unexplained |
| 2013-11-28 → 2013-11-29 | 2 | 0 | 471.0 | (a) holiday | 2/2 days on holiday calendar |
| 2013-12-04 → 2013-12-05 | 2 | 0 | 242.0 | (c) ANOMALY | low density, unexplained |
| 2013-12-13 → 2013-12-16 | 2 | 0 | 240.5 | (c) ANOMALY | low density, unexplained |
| 2013-12-23 → 2014-01-01 | 8 | 2 | 395.0 | (c) ANOMALY | low density, unexplained |
| 2014-01-15 → 2014-01-16 | 2 | 0 | 260.0 | (c) ANOMALY | low density, unexplained |
| 2014-01-27 → 2014-01-27 | 1 | 0 | 512.0 | (c) ANOMALY | low density, unexplained |
| 2014-02-03 → 2014-02-03 | 1 | 0 | 551.0 | (c) ANOMALY | low density, unexplained |
| 2014-02-06 → 2014-02-10 | 3 | 0 | 374.3 | (c) ANOMALY | low density, unexplained |
| 2014-02-12 → 2014-02-13 | 2 | 0 | 404.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-16 → 2014-07-16 | 1 | 0 | 473.0 | (c) ANOMALY | low density, unexplained |
| 2014-08-01 → 2014-08-01 | 1 | 0 | 612.0 | (c) ANOMALY | low density, unexplained |

(+42 single-day holiday/floor flags not listed)

## US100

rows 2,856,407 · coverage 2013-01-01 → 2026-06-05 · median 898 bars/day · threshold 449.0 · flagged 1119 days

yearly median bars/day: 2013: 1038, 2014: 1300, 2015: 841, 2016: 841, 2017: 833, 2018: 1, 2019: 1, 2020: 1, 2021: 23, 2022: 1365, 2023: 1365, 2024: 1365, 2025: 1365, 2026: 1365

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2013-01-01 → 2013-03-05 | 46 | 2 | 360.0 | (b) floor | start-of-history ramp |
| 2013-03-07 → 2013-05-21 | 54 | 6 | 327.3 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2013-05-24 → 2013-05-24 | 1 | 0 | 225.0 | (c) ANOMALY | low density, unexplained |
| 2013-08-26 → 2013-08-26 | 1 | 0 | 296.0 | (c) ANOMALY | low density, unexplained |
| 2013-09-30 → 2013-10-16 | 13 | 1 | 174.4 | (c) ANOMALY | low density, unexplained |
| 2013-10-18 → 2013-10-18 | 1 | 0 | 340.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-24 → 2013-10-25 | 2 | 0 | 123.5 | (c) ANOMALY | low density, unexplained |
| 2014-01-27 → 2014-02-06 | 9 | 0 | 309.6 | (c) ANOMALY | low density, unexplained |
| 2018-01-01 → 2021-09-13 | 966 | 167 | 4.5 | (c) ANOMALY | hole (zero/stray bars) |

(+26 single-day holiday/floor flags not listed)

## US30

rows 3,954,770 · coverage 2013-09-30 → 2026-06-05 · median 1318 bars/day · threshold 659.0 · flagged 92 days

yearly median bars/day: 2013: 1278, 2014: 1303, 2015: 841, 2016: 841, 2017: 835, 2018: 1312, 2019: 1314, 2020: 1366, 2021: 1380, 2022: 1365, 2023: 1363, 2024: 1363, 2025: 1365, 2026: 1365

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2013-09-30 → 2013-10-25 | 20 | 2 | 297.3 | (b) floor | start-of-history ramp |
| 2014-01-27 → 2014-02-07 | 10 | 1 | 337.1 | (c) ANOMALY | low density, unexplained |
| 2014-08-01 → 2014-08-01 | 1 | 0 | 493.0 | (c) ANOMALY | low density, unexplained |
| 2015-11-02 → 2015-11-02 | 1 | 0 | 646.0 | (c) ANOMALY | low density, unexplained |
| 2015-12-24 → 2015-12-25 | 2 | 1 | 322.0 | (a) holiday | 2/2 days on holiday calendar |
| 2015-12-31 → 2016-01-01 | 2 | 1 | 326.5 | (a) holiday | 2/2 days on holiday calendar |
| 2017-07-03 → 2017-07-04 | 2 | 0 | 612.5 | (a) holiday | 1/2 days on holiday calendar |
| 2017-11-23 → 2017-11-24 | 2 | 0 | 643.5 | (a) holiday | 2/2 days on holiday calendar |
| 2020-03-16 → 2020-03-16 | 1 | 0 | 497.0 | (c) ANOMALY | low density, unexplained |
| 2020-04-03 → 2020-04-03 | 1 | 0 | 607.0 | (c) ANOMALY | low density, unexplained |

(+50 single-day holiday/floor flags not listed)

## US500

rows 2,883,793 · coverage 2012-01-16 → 2026-06-05 · median 841 bars/day · threshold 420.5 · flagged 1344 days

yearly median bars/day: 2012: 395, 2013: 1012, 2014: 1217, 2015: 841, 2016: 841, 2017: 761, 2018: 1, 2019: 1, 2020: 1, 2021: 23, 2022: 1362, 2023: 1314, 2024: 1322, 2025: 1359, 2026: 1364

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2012-01-23 → 2012-02-17 | 20 | 0 | 393.0 | (b) floor | start-of-history ramp |
| 2012-02-21 → 2012-04-02 | 30 | 1 | 378.0 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2012-04-04 → 2012-05-25 | 38 | 0 | 384.8 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2012-05-29 → 2012-06-05 | 6 | 0 | 396.2 | (c) ANOMALY | low density, unexplained |
| 2012-06-07 → 2012-07-03 | 19 | 0 | 387.4 | (c) ANOMALY | low density, unexplained |
| 2012-07-05 → 2012-08-17 | 32 | 0 | 388.9 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2012-08-21 → 2012-08-31 | 9 | 0 | 394.6 | (c) ANOMALY | low density, unexplained |
| 2012-09-04 → 2012-09-05 | 2 | 0 | 395.5 | (c) ANOMALY | low density, unexplained |
| 2012-09-10 → 2012-10-26 | 35 | 0 | 393.8 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2012-10-31 → 2012-11-16 | 13 | 0 | 391.7 | (c) ANOMALY | low density, unexplained |
| 2012-11-20 → 2013-01-17 | 43 | 0 | 362.5 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2013-01-23 → 2013-02-18 | 19 | 0 | 384.4 | (c) ANOMALY | low density, unexplained |
| 2013-02-20 → 2013-03-05 | 10 | 0 | 369.0 | (c) ANOMALY | low density, unexplained |
| 2013-03-07 → 2013-04-05 | 22 | 2 | 357.3 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2013-04-09 → 2013-04-18 | 8 | 0 | 290.4 | (c) ANOMALY | low density, unexplained |
| 2013-04-22 → 2013-05-09 | 14 | 0 | 391.4 | (c) ANOMALY | low density, unexplained |
| 2013-05-13 → 2013-05-15 | 3 | 0 | 394.0 | (c) ANOMALY | low density, unexplained |
| 2013-05-17 → 2013-05-17 | 1 | 0 | 110.0 | (c) ANOMALY | low density, unexplained |
| 2013-05-22 → 2013-05-22 | 1 | 0 | 416.0 | (c) ANOMALY | low density, unexplained |
| 2013-05-24 → 2013-05-24 | 1 | 0 | 224.0 | (c) ANOMALY | low density, unexplained |
| 2013-08-26 → 2013-08-26 | 1 | 0 | 303.0 | (c) ANOMALY | low density, unexplained |
| 2013-09-30 → 2013-10-01 | 2 | 0 | 288.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-03 → 2013-10-14 | 8 | 1 | 306.1 | (c) ANOMALY | low density, unexplained |
| 2013-10-18 → 2013-10-18 | 1 | 0 | 333.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-24 → 2013-10-24 | 1 | 0 | 245.0 | (c) ANOMALY | low density, unexplained |
| 2014-01-23 → 2014-02-05 | 10 | 0 | 375.0 | (c) ANOMALY | low density, unexplained |
| 2018-01-01 → 2021-09-13 | 966 | 167 | 4.5 | (c) ANOMALY | hole (zero/stray bars) |

(+29 single-day holiday/floor flags not listed)

## USDCAD

rows 7,255,578 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1437, 2014: 1437, 2015: 1439, 2016: 1440, 2017: 1440, 2018: 1440, 2019: 1440, 2020: 1440, 2021: 1440, 2022: 1438, 2023: 1437, 2024: 1440, 2025: 1437, 2026: 1434


(+21 single-day holiday/floor flags not listed)

## USDCHF

rows 7,242,013 · coverage 2007-01-01 → 2026-06-05 · median 1437 bars/day · threshold 718.5 · flagged 22 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1438, 2014: 1438, 2015: 1424, 2016: 1434, 2017: 1435, 2018: 1433, 2019: 1435, 2020: 1425, 2021: 1412, 2022: 1437, 2023: 1436, 2024: 1439, 2025: 1433, 2026: 1432


(+22 single-day holiday/floor flags not listed)

## USDJPY

rows 7,256,114 · coverage 2007-01-01 → 2026-06-05 · median 1440 bars/day · threshold 720.0 · flagged 21 days

yearly median bars/day: 2007: 1440, 2008: 1440, 2009: 1440, 2010: 1440, 2011: 1440, 2012: 1440, 2013: 1438, 2014: 1437, 2015: 1438, 2016: 1439, 2017: 1439, 2018: 1440, 2019: 1440, 2020: 1440, 2021: 1440, 2022: 1439, 2023: 1438, 2024: 1440, 2025: 1436, 2026: 1435


(+21 single-day holiday/floor flags not listed)

## USOIL

rows 4,434,667 · coverage 2013-01-01 → 2026-06-05 · median 1315 bars/day · threshold 657.5 · flagged 101 days

yearly median bars/day: 2013: 1299, 2014: 1293, 2015: 1262, 2016: 1280, 2017: 1151, 2018: 1290, 2019: 1257, 2020: 1325, 2021: 1350, 2022: 1379, 2023: 1362, 2024: 1333, 2025: 1340, 2026: 1376

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2013-03-26 → 2013-03-26 | 1 | 0 | 643.0 | (c) ANOMALY | low density, unexplained |
| 2013-04-15 → 2013-04-15 | 1 | 0 | 654.0 | (c) ANOMALY | low density, unexplained |
| 2013-04-18 → 2013-04-19 | 2 | 1 | 165.0 | (c) ANOMALY | low density, unexplained |
| 2013-05-16 → 2013-05-22 | 5 | 2 | 138.6 | (c) ANOMALY | low density, unexplained |
| 2013-05-24 → 2013-05-24 | 1 | 0 | 223.0 | (c) ANOMALY | low density, unexplained |
| 2013-06-03 → 2013-06-03 | 1 | 0 | 515.0 | (c) ANOMALY | low density, unexplained |
| 2013-08-12 → 2013-08-12 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2013-08-26 → 2013-08-26 | 1 | 0 | 299.0 | (c) ANOMALY | low density, unexplained |
| 2013-09-23 → 2013-09-23 | 1 | 0 | 577.0 | (c) ANOMALY | low density, unexplained |
| 2013-09-30 → 2013-09-30 | 1 | 0 | 583.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-03 → 2013-10-03 | 1 | 0 | 387.0 | (c) ANOMALY | low density, unexplained |
| 2013-10-15 → 2013-10-16 | 2 | 0 | 159.5 | (c) ANOMALY | low density, unexplained |
| 2013-11-06 → 2013-11-06 | 1 | 0 | 157.0 | (c) ANOMALY | low density, unexplained |
| 2013-11-19 → 2013-11-20 | 2 | 0 | 379.0 | (c) ANOMALY | low density, unexplained |
| 2013-11-28 → 2013-11-29 | 2 | 0 | 496.5 | (a) holiday | 2/2 days on holiday calendar |
| 2013-12-04 → 2013-12-05 | 2 | 0 | 338.0 | (c) ANOMALY | low density, unexplained |
| 2013-12-13 → 2013-12-13 | 1 | 0 | 448.0 | (c) ANOMALY | low density, unexplained |
| 2013-12-18 → 2013-12-19 | 2 | 0 | 340.5 | (c) ANOMALY | low density, unexplained |
| 2013-12-24 → 2013-12-26 | 3 | 0 | 364.0 | (a) holiday | 3/3 days on holiday calendar |
| 2014-01-16 → 2014-01-21 | 4 | 0 | 389.8 | (c) ANOMALY | low density, unexplained |
| 2014-01-27 → 2014-01-27 | 1 | 0 | 529.0 | (c) ANOMALY | low density, unexplained |
| 2014-02-03 → 2014-02-03 | 1 | 0 | 584.0 | (c) ANOMALY | low density, unexplained |
| 2014-02-06 → 2014-02-10 | 3 | 0 | 370.3 | (c) ANOMALY | low density, unexplained |
| 2014-02-12 → 2014-02-12 | 1 | 0 | 420.0 | (c) ANOMALY | low density, unexplained |
| 2014-06-09 → 2014-06-16 | 6 | 3 | 232.5 | (c) ANOMALY | low density, unexplained |
| 2014-06-24 → 2014-06-24 | 1 | 1 | 0.0 | (c) ANOMALY | hole (zero/stray bars) |
| 2014-06-30 → 2014-06-30 | 1 | 0 | 508.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-07 → 2014-07-08 | 2 | 0 | 513.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-14 → 2014-07-16 | 3 | 0 | 333.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-21 → 2014-07-22 | 2 | 0 | 418.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-24 → 2014-07-24 | 1 | 0 | 531.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-29 → 2014-07-29 | 1 | 0 | 484.0 | (c) ANOMALY | low density, unexplained |
| 2014-07-31 → 2014-08-01 | 2 | 0 | 542.0 | (c) ANOMALY | low density, unexplained |
| 2014-09-25 → 2014-09-25 | 1 | 0 | 471.0 | (c) ANOMALY | low density, unexplained |

(+40 single-day holiday/floor flags not listed)

## XAGUSD

rows 7,290,493 · coverage 2003-08-08 → 2026-06-05 · median 1320 bars/day · threshold 660.0 · flagged 463 days

yearly median bars/day: 2003: 302, 2004: 534, 2005: 775, 2006: 933, 2007: 1116, 2008: 1255, 2009: 1276, 2010: 1346, 2011: 1401, 2012: 1405, 2013: 1353, 2014: 1332, 2015: 1376, 2016: 1357, 2017: 1285, 2018: 1311, 2019: 1302, 2020: 1371, 2021: 1367, 2022: 1364, 2023: 1358, 2024: 1373, 2025: 1375, 2026: 1375

| window | weekdays | zero | mean bars | class | note |
|---|--:|--:|--:|---|---|
| 2003-08-08 → 2004-03-08 | 152 | 0 | 316.9 | (b) floor | start-of-history ramp |
| 2004-03-10 → 2004-03-23 | 10 | 0 | 516.4 | (c) ANOMALY | low density, unexplained |
| 2004-03-25 → 2004-03-25 | 1 | 0 | 602.0 | (c) ANOMALY | low density, unexplained |
| 2004-03-29 → 2004-03-31 | 3 | 0 | 549.7 | (c) ANOMALY | low density, unexplained |
| 2004-04-02 → 2004-04-13 | 8 | 0 | 456.2 | (c) ANOMALY | low density, unexplained |
| 2004-04-16 → 2004-04-16 | 1 | 0 | 637.0 | (c) ANOMALY | low density, unexplained |
| 2004-04-22 → 2004-04-26 | 3 | 0 | 631.0 | (c) ANOMALY | low density, unexplained |
| 2004-04-28 → 2004-04-28 | 1 | 0 | 640.0 | (c) ANOMALY | low density, unexplained |
| 2004-04-30 → 2004-05-05 | 4 | 0 | 571.8 | (c) ANOMALY | low density, unexplained |
| 2004-05-13 → 2004-05-14 | 2 | 0 | 507.5 | (c) ANOMALY | low density, unexplained |
| 2004-05-18 → 2004-06-02 | 12 | 0 | 513.6 | (c) ANOMALY | low density, unexplained |
| 2004-06-04 → 2004-07-12 | 27 | 0 | 499.4 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2004-07-14 → 2004-09-06 | 39 | 0 | 522.6 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2004-09-10 → 2004-09-13 | 2 | 0 | 566.5 | (c) ANOMALY | low density, unexplained |
| 2004-09-15 → 2004-09-27 | 9 | 0 | 525.9 | (c) ANOMALY | low density, unexplained |
| 2004-09-29 → 2004-09-29 | 1 | 0 | 537.0 | (c) ANOMALY | low density, unexplained |
| 2004-10-01 → 2004-10-05 | 3 | 0 | 540.7 | (c) ANOMALY | low density, unexplained |
| 2004-10-08 → 2004-10-12 | 3 | 0 | 575.7 | (c) ANOMALY | low density, unexplained |
| 2004-10-15 → 2004-10-20 | 4 | 0 | 567.5 | (c) ANOMALY | low density, unexplained |
| 2004-10-22 → 2004-10-27 | 4 | 0 | 606.0 | (c) ANOMALY | low density, unexplained |
| 2004-10-29 → 2004-11-02 | 3 | 0 | 574.0 | (c) ANOMALY | low density, unexplained |
| 2004-11-04 → 2004-12-01 | 20 | 0 | 514.4 | (d) structural | sustained lower-bar regime with real sessions (source segment) |
| 2004-12-03 → 2004-12-07 | 3 | 0 | 575.7 | (c) ANOMALY | low density, unexplained |
| 2004-12-14 → 2005-01-03 | 15 | 0 | 458.1 | (c) ANOMALY | low density, unexplained |
| 2005-01-06 → 2005-01-06 | 1 | 0 | 568.0 | (c) ANOMALY | low density, unexplained |
| 2005-01-10 → 2005-01-18 | 7 | 0 | 484.9 | (c) ANOMALY | low density, unexplained |
| 2005-01-21 → 2005-01-21 | 1 | 0 | 587.0 | (c) ANOMALY | low density, unexplained |
| 2005-01-25 → 2005-01-28 | 4 | 0 | 608.8 | (c) ANOMALY | low density, unexplained |
| 2005-02-01 → 2005-02-02 | 2 | 0 | 587.5 | (c) ANOMALY | low density, unexplained |
| 2005-02-08 → 2005-02-11 | 4 | 0 | 559.5 | (c) ANOMALY | low density, unexplained |
| 2005-02-15 → 2005-02-15 | 1 | 0 | 582.0 | (c) ANOMALY | low density, unexplained |
| 2005-02-18 → 2005-02-21 | 2 | 0 | 489.5 | (a) holiday | 1/2 days on holiday calendar |
| 2005-03-07 → 2005-03-08 | 2 | 0 | 619.0 | (c) ANOMALY | low density, unexplained |
| 2005-03-16 → 2005-03-16 | 1 | 0 | 650.0 | (c) ANOMALY | low density, unexplained |
| 2005-03-18 → 2005-03-18 | 1 | 0 | 640.0 | (c) ANOMALY | low density, unexplained |
| 2005-03-25 → 2005-03-28 | 2 | 0 | 281.5 | (a) holiday | 2/2 days on holiday calendar |
| 2005-03-30 → 2005-03-30 | 1 | 0 | 644.0 | (c) ANOMALY | low density, unexplained |
| 2005-04-01 → 2005-04-06 | 4 | 0 | 613.2 | (c) ANOMALY | low density, unexplained |
| 2005-04-08 → 2005-04-11 | 2 | 0 | 597.5 | (c) ANOMALY | low density, unexplained |
| 2005-04-22 → 2005-04-22 | 1 | 0 | 507.0 | (c) ANOMALY | low density, unexplained |
| 2005-07-20 → 2005-07-20 | 1 | 0 | 625.0 | (c) ANOMALY | low density, unexplained |
| 2005-09-01 → 2005-09-01 | 1 | 0 | 654.0 | (c) ANOMALY | low density, unexplained |
| 2005-11-16 → 2005-11-16 | 1 | 0 | 514.0 | (c) ANOMALY | low density, unexplained |
| 2005-11-24 → 2005-11-25 | 2 | 0 | 431.0 | (a) holiday | 2/2 days on holiday calendar |
| 2005-12-23 → 2005-12-27 | 3 | 0 | 470.7 | (a) holiday | 2/3 days on holiday calendar |
| 2006-01-05 → 2006-01-05 | 1 | 0 | 547.0 | (c) ANOMALY | low density, unexplained |
| 2006-01-10 → 2006-01-11 | 2 | 0 | 569.5 | (c) ANOMALY | low density, unexplained |
| 2006-01-13 → 2006-01-16 | 2 | 0 | 536.0 | (a) holiday | 1/2 days on holiday calendar |
| 2006-02-24 → 2006-02-24 | 1 | 0 | 630.0 | (c) ANOMALY | low density, unexplained |
| 2006-03-06 → 2006-03-06 | 1 | 0 | 601.0 | (c) ANOMALY | low density, unexplained |
| 2006-03-14 → 2006-03-28 | 11 | 0 | 586.5 | (c) ANOMALY | low density, unexplained |
| 2006-05-19 → 2006-05-19 | 1 | 0 | 488.0 | (c) ANOMALY | low density, unexplained |
| 2006-07-03 → 2006-07-04 | 2 | 0 | 446.5 | (a) holiday | 1/2 days on holiday calendar |

(+68 single-day holiday/floor flags not listed)

## XAUUSD

rows 6,886,976 · coverage 2007-01-01 → 2026-06-05 · median 1371 bars/day · threshold 685.5 · flagged 51 days

yearly median bars/day: 2007: 1328, 2008: 1397, 2009: 1403, 2010: 1412, 2011: 1411, 2012: 1410, 2013: 1377, 2014: 1379, 2015: 1380, 2016: 1380, 2017: 1380, 2018: 1371, 2019: 1371, 2020: 1371, 2021: 1370, 2022: 1365, 2023: 1365, 2024: 1365, 2025: 1365, 2026: 1365


(+51 single-day holiday/floor flags not listed)
