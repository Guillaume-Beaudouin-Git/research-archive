# Splice seam validation (T4)

**Generated:** 2026-06-10 02:04 by `/usr/bin/python3 data/tools/validate_splice_seams.py`
**Gate:** median daily |MT5−Duka| close diff ≤ 5.0 bps on the overlap, no ±60min tz-shift signature, monotonic, zero duplicate timestamps.

| symbol | status | overlap days | median bps | mean bps | max bps | tz-shift | dups | mono | seam step bps |
|---|---|--:|--:|--:|--:|---|--:|---|--:|
| US500 | **PASS** | 531 | 1.122 | 2.832 | 34.97 | no | 0 | True | 8.6 |
| US100 | **PASS** | 531 | 0.885 | 2.416 | 37.902 | no | 0 | True | 10.37 |
| GER40 | **PASS** | 428 | 1.295 | 2.331 | 41.779 | no | 0 | True | 14.21 |
| EURGBP | **PASS** | 461 | 0.362 | 0.687 | 11.868 | no | 0 | True | 0.94 |

## US500

dense MT5 start: 2021-09-14 00:00:00 · seam: {"boundary": "2021-09-14 00:00:00", "step_bps": 8.6, "gap_minutes": 1.0}

shift sensitivity (median bps): -60min: 6.784, +0min: 1.122, +60min: 6.104

bars/day around seam: {"2021-09-07": 1264, "2021-09-08": 1282, "2021-09-09": 1308, "2021-09-10": 1165, "2021-09-12": 112, "2021-09-13": 1307, "2021-09-14": 1155, "2021-09-15": 1311, "2021-09-16": 1317, "2021-09-17": 1239, "2021-09-19": 120, "2021-09-20": 1365, "2021-09-21": 1364}

## US100

dense MT5 start: 2021-09-14 00:00:00 · seam: {"boundary": "2021-09-14 00:00:00", "step_bps": 10.37, "gap_minutes": 1.0}

shift sensitivity (median bps): -60min: 8.708, +0min: 0.885, +60min: 7.389

bars/day around seam: {"2021-09-07": 1335, "2021-09-08": 1335, "2021-09-09": 1335, "2021-09-10": 1215, "2021-09-12": 120, "2021-09-13": 1335, "2021-09-14": 979, "2021-09-15": 1365, "2021-09-16": 1365, "2021-09-17": 1250, "2021-09-19": 120, "2021-09-20": 1365, "2021-09-21": 1365}

## GER40

dense MT5 start: 2021-12-28 00:00:00 · seam: {"boundary": "2021-12-28 00:00:00", "step_bps": 14.21, "gap_minutes": 2.0}

shift sensitivity (median bps): -60min: 8.154, +0min: 1.295, +60min: 4.817

bars/day around seam: {"2021-12-21": 1314, "2021-12-22": 1278, "2021-12-23": 1186, "2021-12-26": 58, "2021-12-27": 1218, "2021-12-28": 569, "2021-12-29": 1282, "2021-12-30": 1229, "2021-12-31": 1248, "2022-01-03": 1266, "2022-01-04": 1301}

## EURGBP

dense MT5 start: 2021-12-15 00:00:00 · seam: {"boundary": "2021-12-15 00:00:00", "step_bps": 0.94, "gap_minutes": 1.0}

shift sensitivity (median bps): -60min: 2.22, +0min: 0.362, +60min: 2.041

bars/day around seam: {"2021-12-08": 1440, "2021-12-09": 1436, "2021-12-10": 1320, "2021-12-12": 113, "2021-12-13": 1430, "2021-12-14": 1432, "2021-12-15": 1439, "2021-12-16": 1440, "2021-12-17": 1320, "2021-12-19": 120, "2021-12-20": 1440, "2021-12-21": 1440, "2021-12-22": 1439}
