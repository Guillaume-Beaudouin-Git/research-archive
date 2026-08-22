"""
nq_seam_qa.py — Garde-fou de soudure pour NQ 1-min (2008-2021 historical
                + 2022-2025 Kaggle).

Cinq tests bloquants sur la fenêtre de chevauchement (cf. FETCH_NQ_2008_plan.md §4) :
    1. Alignement de fuseau via volume spike 09:30 ET
    2. Cohérence des returns 1-min (corr > 0.999)
    3. Sanité OHLC (0 violation)
    4. Reproduction d'une stat connue (mean ORB range, hit-rate iter_10)
    5. Bar-count par session RTH (>= 388 bars / 09:30-16:00 ET)

Sortie :
    - Rapport markdown
    - Exit code 0 (PASS) / 1 (FAIL)
    - Si PASS : génère NQ_1min_2008-2025_MERGED.parquet + sidecar JSON contenant
      seam_qa_status == "PASS", hash du rapport, etc.

Usage :
    /usr/bin/python3 nq_seam_qa.py \\
        --historical data/raw/NQ_1min_2008-XX-XX_2021-12-31.parquet \\
        --kaggle     data/raw/NQ_1min_2022-12-26_2025-12-11.parquet \\
        --overlap    2022-12-26:2023-12-31 \\
        --out        data/ftmo_research/output/nq_seam_qa_$(date +%F).md \\
        [--merged-out data/raw/NQ_1min_2008-2025_MERGED.parquet]

Pré-requis : les deux parquets en input doivent avoir :
    - Index DatetimeIndex tz-aware US/Eastern (cf. cache.py::load_nq_1min)
    - Colonnes : open, high, low, close, volume (vwap_rth/vwap_eth optionnel)

NB : ce script EST le garde-fou EURGBP appliqué au merge NQ. Si un test fail,
il ne produit PAS le parquet merged — c'est volontaire (loader refuse de servir
un merged sans QA PASS).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


# ── Seuils — modifiables si justifié (documenter ici)  ───────────────────────
TOL_VOLUME_SPIKE_MATCH_PCT = 0.98       # ≥ 98 % des jours match exact
TOL_VOLUME_SPIKE_MAX_LAG_MIN = 1        # ±1 min max sur les jours non exact
TOL_RETURN_CORR = 0.999
TOL_ORB_RANGE_PCT = 0.005               # 0.5 % d'écart sur mean ORB range
TOL_HITRATE_PP = 0.02                   # 2 percentage points sur hit-rate
SESSION_BAR_MIN = 388                   # 390 attendus, tolérance 2 manquants
SESSION_BAR_MAX = 391


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str
    metrics: dict = field(default_factory=dict)


def load_parquet_tz_et(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path.name}: index must be DatetimeIndex, got {type(df.index)}")
    if df.index.tz is None:
        raise ValueError(
            f"{path.name}: index must be tz-aware (US/Eastern). Use "
            "tz_localize('US/Eastern', ambiguous='infer') at ingestion."
        )
    if str(df.index.tz) != "US/Eastern":
        df.index = df.index.tz_convert("US/Eastern")
    df.sort_index(inplace=True)
    return df


def parse_overlap(s: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    a, b = s.split(":")
    return (pd.Timestamp(a, tz="US/Eastern"),
            pd.Timestamp(b, tz="US/Eastern"))


# ── Test 1 — volume spike 09:30 ET ────────────────────────────────────────────
def test_volume_spike_alignment(hist: pd.DataFrame, kag: pd.DataFrame,
                                start: pd.Timestamp, end: pd.Timestamp) -> TestResult:
    def daily_argmax_in_window(df: pd.DataFrame) -> pd.Series:
        s = df.loc[start:end]
        # Restrict to 09:25-09:35 ET
        in_win = (s.index.time >= pd.Timestamp("09:25").time()) & \
                 (s.index.time <= pd.Timestamp("09:35").time())
        s = s[in_win]
        if "volume" not in s.columns:
            raise ValueError("volume column required for spike test")
        # Group by date, find argmax of volume → minute-of-day
        s = s.assign(_d=s.index.date, _t=s.index.strftime("%H:%M"))
        idx = s.groupby("_d")["volume"].idxmax()
        out = pd.Series(idx.values, index=idx.index)
        return out.apply(lambda t: pd.Timestamp(t).strftime("%H:%M"))

    am_h = daily_argmax_in_window(hist)
    am_k = daily_argmax_in_window(kag)
    common = am_h.index.intersection(am_k.index)
    if len(common) == 0:
        return TestResult("volume_spike_alignment", False,
                          "no overlapping days in window", {"n_common": 0})

    match = (am_h.loc[common] == am_k.loc[common]).sum() / len(common)
    # Max lag in minutes
    def to_min(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    lag = (am_h.loc[common].apply(to_min) - am_k.loc[common].apply(to_min)).abs()
    max_lag = int(lag.max())

    passed = (match >= TOL_VOLUME_SPIKE_MATCH_PCT) and (max_lag <= TOL_VOLUME_SPIKE_MAX_LAG_MIN)
    return TestResult(
        "volume_spike_alignment", passed,
        f"match={match:.4f} (>={TOL_VOLUME_SPIKE_MATCH_PCT}), max_lag={max_lag}min "
        f"(<={TOL_VOLUME_SPIKE_MAX_LAG_MIN})",
        {"match_pct": float(match), "max_lag_min": max_lag, "n_common": len(common)},
    )


# ── Test 2 — returns corr ─────────────────────────────────────────────────────
def test_return_correlation(hist: pd.DataFrame, kag: pd.DataFrame,
                            start: pd.Timestamp, end: pd.Timestamp) -> TestResult:
    h = hist.loc[start:end, "close"].astype("float64")
    k = kag.loc[start:end, "close"].astype("float64")
    idx = h.index.intersection(k.index)
    if len(idx) < 100:
        return TestResult("return_correlation", False,
                          f"too few overlapping minutes: {len(idx)}",
                          {"n": len(idx)})
    rh = h.loc[idx].pct_change().dropna()
    rk = k.loc[idx].pct_change().dropna()
    idx2 = rh.index.intersection(rk.index)
    corr = float(rh.loc[idx2].corr(rk.loc[idx2]))
    passed = corr >= TOL_RETURN_CORR
    return TestResult(
        "return_correlation", passed,
        f"corr={corr:.6f} (>= {TOL_RETURN_CORR})",
        {"corr": corr, "n": len(idx2)},
    )


# ── Test 3 — OHLC sanity ──────────────────────────────────────────────────────
def test_ohlc_sanity(hist: pd.DataFrame) -> TestResult:
    o, h, l, c = hist["open"], hist["high"], hist["low"], hist["close"]
    v1 = ((h >= o) & (h >= c) & (h >= l)).sum() / len(hist)
    v2 = ((l <= o) & (l <= c) & (l <= h)).sum() / len(hist)
    v3 = (hist["volume"] >= 0).sum() / len(hist) if "volume" in hist.columns else 1.0
    passed = (v1 == 1.0) and (v2 == 1.0) and (v3 == 1.0)
    return TestResult(
        "ohlc_sanity", passed,
        f"high_ok={v1:.6f}, low_ok={v2:.6f}, vol_ok={v3:.6f} (all must be 1.0)",
        {"high_ok": float(v1), "low_ok": float(v2), "vol_ok": float(v3)},
    )


# ── Test 4 — reproduction d'une stat connue ───────────────────────────────────
def test_known_stat_reproduction(hist: pd.DataFrame, kag: pd.DataFrame,
                                 start: pd.Timestamp, end: pd.Timestamp) -> TestResult:
    """
    Compare mean ORB range (09:30→09:45 high-low) entre les deux sources sur le
    chevauchement. La reproduction du hit-rate iter_10 est OPTIONNELLE — elle
    nécessite d'avoir le signal iter_10 importable depuis le repo et un horizon
    suffisant dans le chevauchement.
    """
    def daily_orb_range(df: pd.DataFrame) -> pd.Series:
        s = df.loc[start:end]
        in_orb = (s.index.time >= pd.Timestamp("09:30").time()) & \
                 (s.index.time <  pd.Timestamp("09:45").time())
        s = s[in_orb]
        s = s.assign(_d=s.index.date)
        g = s.groupby("_d").agg(hi=("high", "max"), lo=("low", "min"))
        return (g["hi"] - g["lo"]).rename("orb_range")

    r_h = daily_orb_range(hist)
    r_k = daily_orb_range(kag)
    common = r_h.index.intersection(r_k.index)
    if len(common) == 0:
        return TestResult("known_stat_reproduction", False,
                          "no overlapping days", {"n": 0})

    mean_h = float(r_h.loc[common].mean())
    mean_k = float(r_k.loc[common].mean())
    rel_err = abs(mean_h - mean_k) / mean_k if mean_k > 0 else float("inf")
    passed = rel_err < TOL_ORB_RANGE_PCT
    return TestResult(
        "known_stat_reproduction", passed,
        f"mean_orb_range hist={mean_h:.4f} vs kaggle={mean_k:.4f}, "
        f"rel_err={rel_err:.5f} (< {TOL_ORB_RANGE_PCT})",
        {"mean_hist": mean_h, "mean_kaggle": mean_k, "rel_err": rel_err,
         "n_days": len(common)},
    )


# ── Test 5 — bar-count par session RTH ────────────────────────────────────────
def test_session_bar_count(hist: pd.DataFrame) -> TestResult:
    in_rth = (hist.index.time >= pd.Timestamp("09:30").time()) & \
             (hist.index.time <  pd.Timestamp("16:00").time())
    s = hist[in_rth]
    by_day = s.groupby(s.index.date).size()
    bad = by_day[(by_day < SESSION_BAR_MIN) | (by_day > SESSION_BAR_MAX)]
    # TODO: cross-check vs pandas_market_calendars.CMEEquity early-close days
    #       (Black Friday, Christmas Eve) — pre-filter them avant ce test pour
    #       éviter les faux positifs.
    n_bad = int(len(bad))
    n_total = int(len(by_day))
    passed = n_bad == 0
    return TestResult(
        "session_bar_count", passed,
        f"{n_bad}/{n_total} days outside [{SESSION_BAR_MIN}, {SESSION_BAR_MAX}] bars",
        {"n_bad": n_bad, "n_total": n_total,
         "worst_examples": [str(d) for d in bad.index[:10]]},
    )


# ── Orchestration ─────────────────────────────────────────────────────────────
def run_all_tests(hist_path: Path, kag_path: Path,
                  overlap: tuple[pd.Timestamp, pd.Timestamp]) -> list[TestResult]:
    hist = load_parquet_tz_et(hist_path)
    kag = load_parquet_tz_et(kag_path)
    start, end = overlap

    results = [
        test_volume_spike_alignment(hist, kag, start, end),
        test_return_correlation(hist, kag, start, end),
        test_ohlc_sanity(hist),
        test_known_stat_reproduction(hist, kag, start, end),
        test_session_bar_count(hist),
    ]
    return results


def write_report(results: list[TestResult], out: Path,
                 hist_path: Path, kag_path: Path,
                 overlap: tuple[pd.Timestamp, pd.Timestamp]) -> str:
    lines = []
    overall_pass = all(r.passed for r in results)
    status = "PASS" if overall_pass else "FAIL"

    lines.append(f"# NQ Seam QA Report — {status}")
    lines.append("")
    lines.append(f"- Generated : {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Historical: `{hist_path}`")
    lines.append(f"- Kaggle    : `{kag_path}`")
    lines.append(f"- Overlap   : {overlap[0].date()} → {overlap[1].date()}")
    lines.append("")
    lines.append("## Tests")
    for r in results:
        tag = "[PASS]" if r.passed else "[FAIL]"
        lines.append(f"### {tag} {r.name}")
        lines.append(r.detail)
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(r.metrics, indent=2))
        lines.append("```")
        lines.append("")

    lines.append(f"## Verdict : **{status}**")
    if not overall_pass:
        lines.append("")
        lines.append("ABORT MERGE. Diagnose chaque test FAIL ci-dessus avant de relancer.")
        lines.append("Le loader refuse de servir `source='merged'` tant que ce rapport "
                     "n'est pas PASS.")
    body = "\n".join(lines)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    return body


def write_merged_parquet(hist_path: Path, kag_path: Path,
                         merged_out: Path, report_md: str) -> dict:
    hist = load_parquet_tz_et(hist_path)
    kag = load_parquet_tz_et(kag_path)
    # Concat sans doublon. Si overlap → priorité Kaggle (référence connue).
    common = hist.index.intersection(kag.index)
    hist_clean = hist.drop(index=common) if len(common) else hist
    merged = pd.concat([hist_clean, kag]).sort_index()
    if not merged.index.is_unique:
        merged = merged[~merged.index.duplicated(keep="last")]
    merged_out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(merged_out, engine="pyarrow", compression="snappy")

    meta = {
        "source_historical": str(hist_path),
        "source_kaggle":     str(kag_path),
        "rows":              len(merged),
        "date_start":        merged.index[0].isoformat(),
        "date_end":          merged.index[-1].isoformat(),
        "n_overlap_dropped": int(len(common)),
        "seam_qa_status":    "PASS",
        "seam_qa_hash":      hashlib.sha256(report_md.encode()).hexdigest(),
        "created_at":        datetime.now(timezone.utc).isoformat(),
        "parquet_path":      str(merged_out),
    }
    meta_path = merged_out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--historical", required=True, type=Path)
    p.add_argument("--kaggle",     required=True, type=Path)
    p.add_argument("--overlap",    required=True, type=str,
                   help="YYYY-MM-DD:YYYY-MM-DD")
    p.add_argument("--out",        required=True, type=Path,
                   help="Markdown report output path")
    p.add_argument("--merged-out", required=False, type=Path,
                   help="If provided and all tests PASS, write merged parquet here")
    args = p.parse_args()

    overlap = parse_overlap(args.overlap)
    results = run_all_tests(args.historical, args.kaggle, overlap)
    report_md = write_report(results, args.out, args.historical, args.kaggle, overlap)
    overall_pass = all(r.passed for r in results)
    print(report_md)

    if overall_pass and args.merged_out:
        meta = write_merged_parquet(args.historical, args.kaggle,
                                    args.merged_out, report_md)
        print(f"\nMerged parquet written: {args.merged_out}")
        print(f"Metadata: {json.dumps(meta, indent=2)}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
