"""
nq_reconcile_us100.py — reconcile NQ futures (Databento) vs US100 CFD (MT5 panel)
on 2022-2025 overlap.

Same underlying (Nasdaq-100), different instruments:
  - NQ futures: tz-aware UTC, with real volume, Globex 23h session
  - US100 CFD : tz-naive UTC (per m1_panel.parquet index name), no volume,
                broker-specific session

Tests:
  1. 1-min log-returns correlation on the common UTC-minute index
  2. Daily ORB range as % of daily-open correlation
     ORB defined here as the first 15-minute window after the US cash open
     (NQ: 09:30 ET; for US100 we use the same UTC time anchors, since both
     indices are calendar-aligned UTC)
  3. Mean ORB range comparison (level sanity)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
NQ_PARQUET = ROOT / "data" / "raw" / "NQ_1min_databento_2010-2026.parquet"
US100_PANEL = ROOT / "data" / "panels" / "m5_indices" / "m1_panel.parquet"
OUT_JSON = ROOT / "data" / "ftmo_research" / "output" / "nq_reconcile_us100.json"


def us_cash_open_utc(date_et: pd.Timestamp) -> pd.Timestamp:
    """For a given ET calendar date, return 09:30 ET in UTC."""
    et_dt = pd.Timestamp(year=date_et.year, month=date_et.month, day=date_et.day,
                         hour=9, minute=30, tz="US/Eastern")
    return et_dt.tz_convert("UTC").tz_localize(None)


def main() -> dict:
    print(f"Loading NQ futures: {NQ_PARQUET}")
    nq = pd.read_parquet(NQ_PARQUET)
    # Drop tz for direct UTC comparison
    nq_utc_idx = nq.index.tz_convert("UTC").tz_localize(None)
    nq = nq.set_index(nq_utc_idx)
    nq_close = nq["close"].astype("float64")
    nq_close = nq_close.loc["2022":"2025"]
    print(f"  NQ futures shape: {nq_close.shape}")

    print(f"Loading US100 CFD: {US100_PANEL}")
    pan = pd.read_parquet(US100_PANEL)
    us100 = pan["US100"]
    # Index already tz-naive UTC per name 'timestamp_utc'
    us100 = us100.dropna(subset=["close"])
    us100_close = us100["close"].astype("float64").loc["2022":"2025"]
    print(f"  US100 CFD shape:  {us100_close.shape}")

    # ── Test 1: 1-min returns correlation ─────────────────────────────────────
    common = nq_close.index.intersection(us100_close.index)
    print(f"Common 1-min UTC timestamps in 2022-2025: {len(common):,}")
    if len(common) < 10_000:
        print("WARN: few common minutes")

    rn = np.log(nq_close.loc[common]).diff().dropna()
    ru = np.log(us100_close.loc[common]).diff().dropna()
    idx2 = rn.index.intersection(ru.index)
    rn = rn.loc[idx2]
    ru = ru.loc[idx2]
    corr_1m = float(rn.corr(ru))
    # 5-min resample (less microstructure noise)
    rn5 = rn.resample("5min").sum()
    ru5 = ru.resample("5min").sum()
    common5 = rn5.dropna().index.intersection(ru5.dropna().index)
    corr_5m = float(rn5.loc[common5].corr(ru5.loc[common5]))
    print(f"  1-min log-returns corr: {corr_1m:.4f} (n={len(idx2):,})")
    print(f"  5-min log-returns corr: {corr_5m:.4f} (n={len(common5):,})")

    # ── Test 2: ORB range comparison ──────────────────────────────────────────
    # For each ET-date in overlap, compute high-low of 09:30→09:45 ET window,
    # as fraction of 09:30 ET open price.
    et_dates = pd.date_range("2022-01-03", "2025-12-31", freq="B")
    nq_or = []
    us_or = []
    days = []
    for d in et_dates:
        # 09:30 ET in UTC
        open_utc = us_cash_open_utc(d)
        win = pd.date_range(open_utc, open_utc + pd.Timedelta(minutes=14),
                            freq="1min")
        nq_slice = nq.reindex(win).dropna(how="all")
        us_slice = us100.reindex(win).dropna(how="all")
        if len(nq_slice) < 5 or len(us_slice) < 5:
            continue
        nq_open = nq_slice["close"].iloc[0]
        us_open = us_slice["close"].iloc[0]
        if nq_open <= 0 or us_open <= 0:
            continue
        nq_or.append((nq_slice["high"].max() - nq_slice["low"].min()) / nq_open)
        us_or.append((us_slice["high"].max() - us_slice["low"].min()) / us_open)
        days.append(d.date())

    nq_or = pd.Series(nq_or, index=pd.DatetimeIndex(days))
    us_or = pd.Series(us_or, index=pd.DatetimeIndex(days))
    common_d = nq_or.index.intersection(us_or.index)
    or_corr = float(nq_or.loc[common_d].corr(us_or.loc[common_d]))
    mean_nq = float(nq_or.loc[common_d].mean())
    mean_us = float(us_or.loc[common_d].mean())
    print(f"  ORB% daily corr:  {or_corr:.4f} (n={len(common_d)} days)")
    print(f"  Mean ORB% NQ futures: {mean_nq*100:.4f}%  "
          f"vs US100 CFD: {mean_us*100:.4f}%")

    # ── Verdict ───────────────────────────────────────────────────────────────
    if corr_5m >= 0.90 and or_corr >= 0.75:
        verdict = "MATCH"
    elif corr_5m >= 0.70 and or_corr >= 0.60:
        verdict = "PARTIAL_MATCH"
    else:
        verdict = "DIVERGENCE"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": "2022-01-03 → 2025-12-31",
        "n_common_minutes_2022_2025": int(len(idx2)),
        "n_orb_days": int(len(common_d)),
        "returns_corr_1min": corr_1m,
        "returns_corr_5min": corr_5m,
        "orb_pct_corr_daily": or_corr,
        "mean_orb_pct_nq_futures": mean_nq,
        "mean_orb_pct_us100_cfd": mean_us,
        "verdict": verdict,
        "comment": (
            "Verdict thresholds: MATCH if 5-min corr>=0.90 AND ORB corr>=0.75; "
            "PARTIAL_MATCH if 0.70/0.60; DIVERGENCE otherwise. "
            "Same underlying (Nasdaq-100), different products → expect strong "
            "but not perfect correlation due to CFD spread, broker-specific "
            "smoothing, and lack of volume on the CFD side."
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str))
    print()
    print("VERDICT:", verdict)
    print(f"Wrote: {OUT_JSON}")
    return result


if __name__ == "__main__":
    main()
