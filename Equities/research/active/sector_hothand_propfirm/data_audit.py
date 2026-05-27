"""
data_audit.py — Phase 0: audit OHLCV data quality for sector hot-hand strategy.

Fetches QQQ + 9 SPDR sector ETFs via data/cache.py (yfinance, daily, auto-adjust=True).
Outputs results/data_audit.md with per-ticker quality table.

Exit code:
    0 — all tickers OK (no flags)
    1 — at least one FLAG detected (stop, report before continuing)

Flags:
    - missing_pct > 5.0%
    - first valid date > 2001-01-01
"""

from __future__ import annotations

import sys
import os
from datetime import date, timedelta
from pathlib import Path
import textwrap

import numpy as np
import pandas as pd

# ─── path setup ─────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parents[4]   # Algo_claude/
sys.path.insert(0, str(_REPO))

from data.cache import get_cached_or_fetch     # noqa: E402

# ─── config ─────────────────────────────────────────────────────────────────
TICKERS = ["QQQ", "XLK", "XLE", "XLP", "XLU", "XLV", "XLF", "XLI", "XLB", "XLY"]
START   = "2000-01-01"
END     = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

FLAG_MISSING_PCT_THRESHOLD = 5.0
FLAG_START_DATE_THRESHOLD  = pd.Timestamp("2001-01-01")

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _full_calendar(start: str, end: str) -> pd.DatetimeIndex:
    """US trading calendar approximation: Mon-Fri excluding no specific holidays."""
    idx = pd.bdate_range(start=start, end=end, freq="B")
    return idx


def audit_ticker(ticker: str) -> dict:
    """Fetch and compute quality metrics for one ticker."""
    df = get_cached_or_fetch(
        ticker=ticker,
        start=START,
        end=END,
        interval="1d",
        source="yfinance",
        max_age_days=1.0,
    )

    if df.empty:
        return {
            "ticker":        ticker,
            "rows":          0,
            "first_valid":   None,
            "last_valid":    None,
            "missing_pct":   100.0,
            "gap_tail_pct":  None,
            "autocorr_lag1": None,
            "flag":          "EMPTY",
        }

    # Normalise column names
    df.columns = [c.lower() for c in df.columns]

    # yfinance auto_adjust=True: 'close' IS adjusted close
    # 'open' is split-adjusted but not dividend-adjusted in auto_adjust mode
    # We need both close (adj) and open for signal / fill logic
    close = df["close"].copy()
    open_ = df["open"].copy()

    # ── Missing % (vs business-day calendar) ──────────────────────────────
    cal = _full_calendar(START, END)
    n_cal = len(cal)
    # rows where close is NaN or the date is absent from the index
    df.index = pd.to_datetime(df.index).tz_localize(None)
    n_present = close.dropna().shape[0]
    missing_pct = round(100.0 * (n_cal - n_present) / n_cal, 3)

    # ── First / last valid dates ──────────────────────────────────────────
    close_nonan = close.dropna()
    first_valid = close_nonan.index[0]  if len(close_nonan) else None
    last_valid  = close_nonan.index[-1] if len(close_nonan) else None

    # ── Gap tail % ────────────────────────────────────────────────────────
    # |open_t - close_{t-1}| / close_{t-1} > 0.5%
    prev_close  = close.shift(1)
    gap_ret     = (open_ - prev_close).abs() / prev_close.abs()
    n_gaps      = (gap_ret > 0.005).sum()
    n_valid_obs = gap_ret.dropna().shape[0]
    gap_tail_pct = round(100.0 * n_gaps / n_valid_obs, 2) if n_valid_obs > 0 else None

    # ── Autocorrélation lag-1 des log-returns (sanity check) ──────────────
    log_ret = np.log(close / close.shift(1)).dropna()
    autocorr_lag1 = round(float(log_ret.autocorr(lag=1)), 4) if len(log_ret) > 10 else None

    # ── Flag logic ────────────────────────────────────────────────────────
    flags = []
    if missing_pct > FLAG_MISSING_PCT_THRESHOLD:
        flags.append(f"MISSING>{FLAG_MISSING_PCT_THRESHOLD}%")
    if first_valid is not None and first_valid > FLAG_START_DATE_THRESHOLD:
        flags.append(f"LATE_START({first_valid.date()})")

    return {
        "ticker":        ticker,
        "rows":          len(df),
        "first_valid":   first_valid.date() if first_valid is not None else None,
        "last_valid":    last_valid.date()  if last_valid  is not None else None,
        "missing_pct":   missing_pct,
        "gap_tail_pct":  gap_tail_pct,
        "autocorr_lag1": autocorr_lag1,
        "flag":          "; ".join(flags) if flags else "OK",
    }


# ─── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"Auditing {len(TICKERS)} tickers — {START} → {END}")
    records = []
    for ticker in TICKERS:
        print(f"  {ticker} ...", end=" ", flush=True)
        rec = audit_ticker(ticker)
        records.append(rec)
        print(rec["flag"])

    df_audit = pd.DataFrame(records)

    # ── Markdown report ───────────────────────────────────────────────────
    lines = [
        "# Phase 0 — Data Audit Report",
        "",
        f"**Run date:** {date.today()}  ",
        f"**Period fetched:** {START} → {END}  ",
        f"**Source:** yfinance daily (auto_adjust=True)  ",
        f"**Tickers:** {len(TICKERS)}",
        "",
        "## Quality table",
        "",
        "| Ticker | Rows | First valid | Last valid | Missing % | Gap-tail % | Autocorr(1) | Flag |",
        "|--------|------|-------------|------------|-----------|------------|-------------|------|",
    ]

    any_flag = False
    for rec in records:
        flag = rec["flag"]
        flag_cell = f"**{flag}**" if flag != "OK" else flag
        if flag != "OK":
            any_flag = True
        lines.append(
            f"| {rec['ticker']} "
            f"| {rec['rows']} "
            f"| {rec['first_valid']} "
            f"| {rec['last_valid']} "
            f"| {rec['missing_pct']} "
            f"| {rec['gap_tail_pct']} "
            f"| {rec['autocorr_lag1']} "
            f"| {flag_cell} |"
        )

    lines += [
        "",
        "## Metric definitions",
        "",
        "- **Missing %** : (biz-days in calendar − rows with valid close) / biz-days. "
          "Flag if > 5%.",
        "- **Gap-tail %** : fraction of trading days where |open_t − close_{t−1}| / close_{t−1} > 0.5%.",
        "- **Autocorr(1)** : lag-1 autocorrelation of daily log-returns (sanity; near 0 expected).",
        "- **Flag** : OK | MISSING>5% | LATE_START(date) | EMPTY",
        "",
        "## Verdict",
        "",
    ]

    if any_flag:
        flagged = [r["ticker"] for r in records if r["flag"] != "OK"]
        lines += [
            f"**STATUS: FLAG — {len(flagged)} ticker(s) triggered a flag: {', '.join(flagged)}**",
            "",
            "→ STOP. Report to researcher before proceeding to Phase 1.",
        ]
    else:
        lines += [
            "**STATUS: OK — all tickers pass quality gates.**",
            "",
            "→ Proceed to Phase 1 (baseline engine).",
        ]

    report = "\n".join(lines)
    out_path = RESULTS_DIR / "data_audit.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written → {out_path.relative_to(_REPO)}")

    if any_flag:
        flagged = [r["ticker"] for r in records if r["flag"] != "OK"]
        print(f"\n[STOP] Flags detected on: {', '.join(flagged)}")
        print("Do NOT proceed to Phase 1. Report the issue first.")
        return 1

    print("\n[OK] All tickers pass. Proceed to Phase 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
