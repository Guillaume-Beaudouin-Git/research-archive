"""audit_bar_density.py — bar-density audit of every M1 instrument in data/deep_history_utc/.

Motivation: the US500 2018-01 -> 2021-09 hole was masked by stray bars (0-23 bars/day),
so existence-based coverage checks ("any bars present") reported "no outages". This audit
counts bars per trading day and flags any day below 50% of the instrument's median
(median over weekdays with >=1 bar), then classifies contiguous flagged windows:

    (a) holiday   -- known market holidays / half-days (computed US+EU calendar)
    (b) floor     -- source history floor / start-of-history ramp
    (d) structural-- sustained lower-bar regime with real sessions (e.g. Dukascopy
                     session-filtered backfill segment vs 24h MT5 segment) -- by design
    (c) ANOMALY   -- everything else; mean bars < 50/day => "hole (stray-masked)"

Outputs: data/tools/audit_report.md (+ .json sidecar for machine consumption, e.g.
MANIFEST regeneration). Read-only: never touches the data files.

Usage:
    /usr/bin/python3 data/tools/audit_bar_density.py
    /usr/bin/python3 data/tools/audit_bar_density.py --dir data/deep_history_utc \
        --md data/tools/audit_report.md --json data/tools/audit_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO / "data" / "deep_history_utc"
DEFAULT_MD = REPO / "data" / "tools" / "audit_report.md"
DEFAULT_JSON = REPO / "data" / "tools" / "audit_report.json"

FLAG_FRAC = 0.50          # flag day if bars < FLAG_FRAC * median_nonzero (per instrument)
HOLE_BARS = 50            # window mean below this => hard hole (stray-masked or empty)
STRUCT_MIN_DAYS = 20      # sustained low-but-real-session regime => structural
STRUCT_MIN_BARS = 200     # ...with at least this many bars/day on average
HOLIDAY_MAX_DAYS = 3      # holiday/half-day windows are short


# ------------------------------------------------------------------ holiday calendar
def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> list[date]:
    """US observance shift: Sat -> Fri, Sun -> Mon (return both actual and observed)."""
    if d.weekday() == 5:
        return [d, d - timedelta(days=1)]
    if d.weekday() == 6:
        return [d, d + timedelta(days=1)]
    return [d]


def holiday_set(y0: int, y1: int) -> set[date]:
    """US market holidays + common EU closures, +/-0 observance. Approximate by design:
    used only to classify SHORT low-density windows, never to alter data."""
    hs: set[date] = set()
    for y in range(y0, y1 + 1):
        e = _easter(y)
        fixed = [date(y, 1, 1), date(y, 7, 4), date(y, 12, 24), date(y, 12, 25),
                 date(y, 12, 26), date(y, 12, 31), date(y, 5, 1)]
        if y >= 2022:
            fixed.append(date(y, 6, 19))                       # Juneteenth (US markets 2022+)
        rules = [
            _nth_weekday(y, 1, 0, 3),                          # MLK
            _nth_weekday(y, 2, 0, 3),                          # Presidents Day
            _last_weekday(y, 5, 0),                            # Memorial Day
            _nth_weekday(y, 9, 0, 1),                          # Labor Day
            _nth_weekday(y, 11, 3, 4),                         # Thanksgiving
            _nth_weekday(y, 11, 3, 4) + timedelta(days=1),     # half-day Friday
            e - timedelta(days=2),                             # Good Friday
            e + timedelta(days=1),                             # Easter Monday
            e + timedelta(days=50),                            # Whit Monday (DE, some years)
        ]
        for d in fixed + rules:
            hs.update(_observed(d))
    return hs


# ------------------------------------------------------------------------ audit core
@dataclass
class Window:
    start: str
    end: str
    weekdays: int
    zero_days: int
    mean_bars: float
    klass: str
    note: str


def _classify(win_days: pd.DatetimeIndex, bars: np.ndarray, med: float,
              hist_start: pd.Timestamp, hols: set[date]) -> tuple[str, str]:
    n = len(win_days)
    mean_bars = float(bars.mean())
    touches_start = (win_days[0] - hist_start).days <= 7
    n_hol = sum(d.date() in hols for d in win_days)
    if touches_start:
        return "(b) floor", "start-of-history ramp"
    if n <= HOLIDAY_MAX_DAYS and n_hol > 0:
        return "(a) holiday", f"{n_hol}/{n} days on holiday calendar"
    if n >= STRUCT_MIN_DAYS and mean_bars >= STRUCT_MIN_BARS:
        return "(d) structural", "sustained lower-bar regime with real sessions (source segment)"
    if mean_bars < HOLE_BARS:
        return "(c) ANOMALY", "hole (zero/stray bars)"
    return "(c) ANOMALY", "low density, unexplained"


def audit_file(path: Path, hols: set[date]) -> dict:
    ts = pd.read_csv(path, usecols=["timestamp_utc"], dtype=str)["timestamp_utc"]
    day_counts = ts.str.slice(0, 10).value_counts()
    days = pd.to_datetime(day_counts.index, format="%Y.%m.%d")
    counts = pd.Series(day_counts.values, index=days).sort_index()

    full = pd.date_range(counts.index[0], counts.index[-1], freq="D")
    weekdays = full[full.dayofweek < 5]
    bars = counts.reindex(weekdays).fillna(0.0)

    nonzero_wd = bars[bars > 0]
    med = float(nonzero_wd.median())
    thr = FLAG_FRAC * med
    flagged = bars < thr

    windows: list[Window] = []
    if flagged.any():
        grp = (flagged != flagged.shift()).cumsum()
        for _, seg in bars[flagged].groupby(grp[flagged]):
            klass, note = _classify(seg.index, seg.values, med, counts.index[0], hols)
            windows.append(Window(
                start=str(seg.index[0].date()), end=str(seg.index[-1].date()),
                weekdays=len(seg), zero_days=int((seg == 0).sum()),
                mean_bars=round(float(seg.mean()), 1), klass=klass, note=note))

    yearly = bars[bars > 0].groupby(bars[bars > 0].index.year).median().astype(int)
    return {
        "instrument": path.stem.replace("_M1", ""),
        "file": path.name,
        "rows": int(len(ts)),
        "coverage": [str(counts.index[0].date()), str(counts.index[-1].date())],
        "trading_days_nonzero": int(len(nonzero_wd)),
        "median_bars_per_day": int(med),
        "flag_threshold": round(thr, 1),
        "flagged_days": int(flagged.sum()),
        "yearly_median_bars": {int(y): int(v) for y, v in yearly.items()},
        "windows": [asdict(w) for w in windows],
        "n_anomaly_windows": sum(w.klass.startswith("(c)") for w in windows),
    }


# ---------------------------------------------------------------------- report render
def render_md(results: list[dict], src_dir: Path) -> str:
    lines = [
        "# Bar-density audit — `" + str(src_dir.relative_to(REPO)) + "`",
        "",
        f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} by "
        f"`/usr/bin/python3 data/tools/audit_bar_density.py` (read-only).",
        f"**Rule:** flag day if bars < {FLAG_FRAC:.0%} of instrument median "
        f"(over weekdays with ≥1 bar); contiguous flagged runs classified "
        "(a) holiday / (b) floor / (d) structural segment / **(c) ANOMALY**.",
        "**Known by design:** US2000 absent from estate (Dukascopy floor 2018-08-08 > "
        "MT5 start 2018-01-23 — backfill impossible, class (b)).",
        "",
        "## Summary",
        "",
        "| instrument | coverage | median bars/d | flagged days | (c) anomaly windows | worst anomaly |",
        "|---|---|--:|--:|--:|---|",
    ]
    for r in sorted(results, key=lambda x: (-x["n_anomaly_windows"], x["instrument"])):
        anos = [w for w in r["windows"] if w["klass"].startswith("(c)")]
        worst = max(anos, key=lambda w: w["weekdays"]) if anos else None
        worst_s = (f"{worst['start']}→{worst['end']} ({worst['weekdays']} wd, "
                   f"{worst['mean_bars']} b/d)") if worst else "—"
        lines.append(f"| {r['instrument']} | {r['coverage'][0]}→{r['coverage'][1]} | "
                     f"{r['median_bars_per_day']} | {r['flagged_days']} | "
                     f"{r['n_anomaly_windows']} | {worst_s} |")
    lines.append("")
    for r in sorted(results, key=lambda x: x["instrument"]):
        lines += [f"## {r['instrument']}", "",
                  f"rows {r['rows']:,} · coverage {r['coverage'][0]} → {r['coverage'][1]} · "
                  f"median {r['median_bars_per_day']} bars/day · threshold {r['flag_threshold']} · "
                  f"flagged {r['flagged_days']} days", "",
                  "yearly median bars/day: " + ", ".join(
                      f"{y}: {v}" for y, v in r["yearly_median_bars"].items()), ""]
        wins = [w for w in r["windows"] if w["weekdays"] >= 2 or w["klass"].startswith("(c)")]
        singles_a = sum(1 for w in r["windows"] if w["weekdays"] == 1
                        and not w["klass"].startswith("(c)"))
        if wins:
            lines += ["| window | weekdays | zero | mean bars | class | note |", "|---|--:|--:|--:|---|---|"]
            lines += [f"| {w['start']} → {w['end']} | {w['weekdays']} | {w['zero_days']} | "
                      f"{w['mean_bars']} | {w['klass']} | {w['note']} |" for w in wins]
        if singles_a:
            lines.append(f"\n(+{singles_a} single-day holiday/floor flags not listed)")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEFAULT_DIR))
    ap.add_argument("--md", default=str(DEFAULT_MD))
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    a = ap.parse_args()
    src = Path(a.dir)
    files = sorted(p for p in src.glob("*_M1.csv") if p.suffixes == [".csv"])
    if not files:
        print(f"no *_M1.csv under {src}", file=sys.stderr)
        return 1
    hols = holiday_set(2000, 2027)
    results = []
    for p in files:
        r = audit_file(p, hols)
        results.append(r)
        print(f"{r['instrument']:8} median {r['median_bars_per_day']:>5} b/d  "
              f"flagged {r['flagged_days']:>4}  anomaly windows {r['n_anomaly_windows']}", flush=True)
    Path(a.md).write_text(render_md(results, src))
    Path(a.json).write_text(json.dumps(
        {"generated": str(pd.Timestamp.now()), "dir": str(src),
         "rule": f"day flagged if bars < {FLAG_FRAC} * median_nonzero", "results": results},
        indent=2))
    print(f"\nreport -> {a.md}\njson   -> {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
