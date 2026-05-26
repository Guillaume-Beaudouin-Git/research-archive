"""
Round Number Stop-Loss Cascade — Phase 1.5 IC Feasibility
PRESPEC frozen: 2026-05-23. This script implements Section 2-5 of PRESPEC.md exactly.
"""

from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

# ── constants (frozen, per PRESPEC.md) ────────────────────────────────────────
PIP = 0.0001
LEVEL_SPACING = 50        # pips
DENSITY_GATE = 200
GAP_THRESHOLD_MIN = 10    # bars with gap > 10 min to prev = weekend/holiday
GAP_TOLERANCE_FWD = 3     # minutes: max slippage when looking up forward close
HORIZONS: dict[str, int] = {"1min": 1, "5min": 5, "15min": 15, "30min": 30, "60min": 60}
HAC_LAGS = 6

SLUG = Path(__file__).parent
RAW_DIR = SLUG.parents[3] / "data" / "raw"
OUT_JSON = SLUG / "results_ic.json"
OUT_MD   = SLUG / "_ic_feasibility.md"

PAIRS = ["EURUSD", "GBPUSD"]


# ── helpers ────────────────────────────────────────────────────────────────────

def load_parquet(pair: str) -> pd.DataFrame:
    p = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
    df = pd.read_parquet(p, columns=["open", "high", "low", "close", "volume"])
    df.index = pd.to_datetime(df.index, utc=True)
    df.sort_index(inplace=True)
    return df


def generate_levels(df: pd.DataFrame) -> np.ndarray:
    lo_pips = int(np.floor(df["close"].min() / PIP))
    hi_pips = int(np.ceil(df["close"].max() / PIP))
    level_lo = (lo_pips // LEVEL_SPACING) * LEVEL_SPACING
    level_hi = ((hi_pips // LEVEL_SPACING) + 1) * LEVEL_SPACING
    levels_pips = np.arange(level_lo, level_hi + 1, LEVEL_SPACING)
    levels = levels_pips * PIP
    return levels


def find_breaches(df: pd.DataFrame, levels: np.ndarray) -> pd.DataFrame:
    """
    Close-through breach detection (PRESPEC Section 2).
    Excludes gap bars (weekend/holiday) and resolves collisions by keeping
    the level closest to prev_close (PRESPEC Section 2, collision rule).
    """
    close = df["close"].values
    ts_arr = df.index
    # Use microseconds for gap detection (index may be datetime64[us])
    ts_us = df.index.values.astype("datetime64[us]").astype(np.int64)

    # gap detection: diff in minutes to previous bar
    diffs_min = np.empty(len(df), dtype=float)
    diffs_min[0] = 999.0  # first bar always excluded (no prev bar)
    diffs_min[1:] = (ts_us[1:] - ts_us[:-1]) / 1e6 / 60

    is_gap = diffs_min > GAP_THRESHOLD_MIN

    prev_close = np.empty_like(close)
    prev_close[0] = np.nan
    prev_close[1:] = close[:-1]

    valid = ~is_gap & ~np.isnan(prev_close)

    events: list[dict] = []
    for level in levels:
        up_mask = valid & (close > level) & (prev_close <= level)
        dn_mask = valid & (close < level) & (prev_close >= level)

        for i in np.where(up_mask)[0]:
            events.append({
                "bar_idx": i,
                "timestamp": ts_arr[i],
                "level": level,
                "signal": 1,
                "entry_price": close[i],
                "dist_to_prev": abs(level - prev_close[i]),
                "is_00": round(level / PIP) % 100 == 0,
            })
        for i in np.where(dn_mask)[0]:
            events.append({
                "bar_idx": i,
                "timestamp": ts_arr[i],
                "level": level,
                "signal": -1,
                "entry_price": close[i],
                "dist_to_prev": abs(level - prev_close[i]),
                "is_00": round(level / PIP) % 100 == 0,
            })

    if not events:
        return pd.DataFrame()

    ev = pd.DataFrame(events)
    # Collision: same bar → keep level closest to prev_close (first crossed)
    ev = (
        ev.sort_values(["bar_idx", "dist_to_prev"])
          .groupby("bar_idx", sort=False)
          .first()
          .reset_index()
    )
    ev.sort_values("bar_idx", inplace=True)
    return ev


def compute_forward_returns(df: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    ts_arr = df.index.values  # numpy datetime64 (may be us or ns resolution)
    close_arr = df["close"].values

    # Normalise to microseconds for consistent int64 searchsorted
    ts_us = ts_arr.astype("datetime64[us]").astype(np.int64)  # microseconds since epoch

    for h_label, h_min in HORIZONS.items():
        target_ts = ev["timestamp"] + pd.Timedelta(minutes=h_min)
        # tz-aware Series.astype(int64) gives nanoseconds; divide by 1000 → microseconds to match ts_us
        target_us = target_ts.astype(np.int64).values // 1000

        fut_i = np.searchsorted(ts_us, target_us, side="left")
        fut_i = np.clip(fut_i, 0, len(ts_arr) - 1)

        actual_ts_us = ts_us[fut_i]
        gap_min = (actual_ts_us - target_us) / 1e6 / 60

        raw_ret = np.where(
            gap_min <= GAP_TOLERANCE_FWD,
            (close_arr[fut_i] - ev["entry_price"].values) / ev["entry_price"].values,
            np.nan,
        )
        ev[f"raw_ret_{h_label}"] = raw_ret
        ev[f"signed_ret_{h_label}"] = raw_ret * ev["signal"].values

    return ev


def hac_tstat(y: np.ndarray, x: np.ndarray, lag: int = HAC_LAGS) -> float:
    mask = ~np.isnan(y) & ~np.isnan(x)
    y2, x2 = y[mask], x[mask]
    if len(y2) < 20:
        return np.nan
    X = sm.add_constant(x2.astype(float))
    res = sm.OLS(y2.astype(float), X).fit(
        cov_type="HAC", cov_kwds={"maxlags": lag}
    )
    return float(res.tvalues[1])


def run_ic(ev: pd.DataFrame) -> dict:
    results: dict = {}
    for h_label in HORIZONS:
        raw_col = f"raw_ret_{h_label}"
        sig_col = "signal"
        sret_col = f"signed_ret_{h_label}"

        sub = ev[[sig_col, raw_col, sret_col]].dropna()
        n = len(sub)
        if n < 30:
            results[h_label] = {"n": n, "gate": "FAIL_N"}
            continue

        sig_v  = sub[sig_col].values.astype(float)
        ret_v  = sub[raw_col].values.astype(float)
        sret_v = sub[sret_col].values.astype(float)

        ic, _ = stats.spearmanr(sig_v, ret_v)
        t_hac  = hac_tstat(ret_v, sig_v)
        mean_sret_pips = float(np.nanmean(sret_v) / PIP)
        hit_rate = float(np.mean(sret_v > 0))

        if ic > 0 and t_hac > 1.65:
            gate = "PASS"
        elif ic > 0 and t_hac > 1.0:
            gate = "WEAK"
        elif ic > 0:
            gate = "WEAK_LOW"
        else:
            gate = "FAIL"

        results[h_label] = {
            "n": int(n),
            "ic_spearman": round(float(ic), 4),
            "t_hac_nw6": round(float(t_hac), 3),
            "mean_sret_pips": round(mean_sret_pips, 4),
            "hit_rate": round(hit_rate, 4),
            "gate": gate,
        }
    return results


def per_year_ic(ev: pd.DataFrame, h_label: str) -> list[dict]:
    raw_col  = f"raw_ret_{h_label}"
    sret_col = f"signed_ret_{h_label}"
    ev2 = ev.copy()
    ev2["year"] = ev2["timestamp"].dt.year
    rows = []
    for yr, grp in ev2.groupby("year"):
        sub = grp[["signal", raw_col, sret_col]].dropna()
        n = len(sub)
        if n < 10:
            rows.append({"year": int(yr), "n": n, "ic": None, "t_hac": None, "hit_rate": None})
            continue
        ic, _ = stats.spearmanr(sub["signal"].values, sub[raw_col].values)
        t_hac = hac_tstat(sub[raw_col].values, sub["signal"].values)
        hit   = float(np.mean(sub[sret_col].values > 0))
        rows.append({
            "year": int(yr),
            "n": int(n),
            "ic": round(float(ic), 4),
            "t_hac": round(float(t_hac), 3),
            "hit_rate": round(hit, 4),
        })
    return rows


def overall_gate(ic_results: dict) -> str:
    n_pass = sum(1 for v in ic_results.values() if v.get("gate") == "PASS")
    n_weak = sum(1 for v in ic_results.values() if "WEAK" in v.get("gate", ""))
    if n_pass >= 2:
        return "PASS"
    if n_pass == 1 or n_weak >= 2:
        return "WEAK"
    return "FAIL"


# ── density check ──────────────────────────────────────────────────────────────

def density_report(ev: pd.DataFrame, pair: str) -> dict:
    n_total = len(ev)
    n_up    = int((ev["signal"] == 1).sum())
    n_dn    = int((ev["signal"] == -1).sum())
    n_00    = int(ev["is_00"].sum())
    n_50    = int((~ev["is_00"]).sum())
    ev2 = ev.copy()
    ev2["year"] = ev2["timestamp"].dt.year
    by_year = ev2.groupby("year").size().to_dict()
    by_year = {int(k): int(v) for k, v in by_year.items()}
    gate = "PASS" if n_total >= DENSITY_GATE else "FAIL"
    return {
        "pair": pair,
        "n_breach_total": n_total,
        "n_breach_up": n_up,
        "n_breach_down": n_dn,
        "n_breach_00": n_00,
        "n_breach_50": n_50,
        "by_year": by_year,
        "density_gate": gate,
    }


# ── main ───────────────────────────────────────────────────────────────────────

def run_pair(pair: str, skip_if_eurusd_ic_negative: bool = False) -> dict | None:
    print(f"\n{'='*60}")
    print(f"  {pair}")
    print(f"{'='*60}")

    df = load_parquet(pair)
    print(f"  Loaded: {len(df):,} bars  {df.index[0]} → {df.index[-1]}")

    levels = generate_levels(df)
    print(f"  Levels: {len(levels)} active (spacing {LEVEL_SPACING} pips)")
    print(f"  Level range: {levels[0]:.4f} → {levels[-1]:.4f}")

    ev = find_breaches(df, levels)
    dens = density_report(ev, pair)

    print(f"\n  DENSITY CHECK")
    print(f"  N_breach_total = {dens['n_breach_total']}  "
          f"(UP={dens['n_breach_up']}, DN={dens['n_breach_down']})")
    print(f"  N_breach_.XX00 = {dens['n_breach_00']}  "
          f"N_breach_.XX50 = {dens['n_breach_50']}")
    print(f"  By year: {dens['by_year']}")
    print(f"  Gate N >= {DENSITY_GATE}: {dens['density_gate']}")

    if dens["density_gate"] == "FAIL":
        print(f"\n  ⛔ DENSITY GATE FAIL — stopping {pair}")
        return {"density": dens, "ic": None, "gate": "FAIL_DENSITY"}

    ev = compute_forward_returns(df, ev)
    ic_res = run_ic(ev)

    print(f"\n  IC RESULTS")
    print(f"  {'Horizon':<8} {'N':>5} {'IC':>8} {'t_HAC':>7} {'mean_sret':>12} {'hit%':>7} {'Gate'}")
    print(f"  {'-'*65}")
    for h, r in ic_res.items():
        if "ic_spearman" in r:
            print(f"  {h:<8} {r['n']:>5} {r['ic_spearman']:>8.4f} {r['t_hac_nw6']:>7.3f} "
                  f"{r['mean_sret_pips']:>12.4f} {r['hit_rate']*100:>6.1f}%  {r['gate']}")
        else:
            print(f"  {h:<8} {'FAIL_N':>35}")

    gate = overall_gate(ic_res)
    print(f"\n  Overall gate: {gate}")

    # per-year breakdown for horizons with IC > 0
    per_year: dict[str, list] = {}
    for h, r in ic_res.items():
        if r.get("ic_spearman", -999) > 0:
            py = per_year_ic(ev, h)
            per_year[h] = py
            print(f"\n  Per-year [{h}]:")
            print(f"  {'Year':<6} {'N':>5} {'IC':>8} {'t_HAC':>7} {'hit%':>7}")
            print(f"  {'-'*40}")
            for row in py:
                ic_s  = f"{row['ic']:.4f}"   if row["ic"]   is not None else "  N/A  "
                t_s   = f"{row['t_hac']:.3f}" if row["t_hac"] is not None else "  N/A "
                hit_s = f"{row['hit_rate']*100:.1f}%" if row["hit_rate"] is not None else "  N/A"
                print(f"  {row['year']:<6} {row['n']:>5} {ic_s:>8} {t_s:>7} {hit_s:>7}")

    return {
        "density": dens,
        "ic": ic_res,
        "per_year": per_year,
        "gate": gate,
    }


def main() -> None:
    all_results: dict[str, dict] = {}

    # EUR/USD first (mandatory)
    eur_res = run_pair("EURUSD")
    all_results["EURUSD"] = eur_res

    eur_gate = eur_res.get("gate", "FAIL")

    # GBP/USD only if EUR/USD IC direction positive (any horizon IC > 0)
    eur_ic = eur_res.get("ic") or {}
    any_positive = any(v.get("ic_spearman", -999) > 0 for v in eur_ic.values())

    if any_positive:
        print(f"\n  EUR/USD IC > 0 on ≥1 horizon — proceeding to GBP/USD (+5 n_tests)")
        gbp_res = run_pair("GBPUSD")
        all_results["GBPUSD"] = gbp_res
    else:
        print(f"\n  EUR/USD IC ≤ 0 on all horizons — GBP/USD skipped per PRESPEC Section 6")
        all_results["GBPUSD"] = {"skipped": True, "reason": "EURUSD IC <= 0 all horizons"}

    # write JSON
    with open(OUT_JSON, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results written: {OUT_JSON}")

    write_md(all_results)
    print(f"  Feasibility report: {OUT_MD}")


def write_md(results: dict) -> None:
    lines = [
        "# IC Feasibility — Round Number Stop-Loss Cascade",
        "",
        f"**Date:** 2026-05-23  ",
        f"**PRESPEC frozen:** 2026-05-23  ",
        f"**N_tests consumed:** +5 EUR/USD IC horizons"
        + (" + 5 GBP/USD IC horizons" if results.get("GBPUSD") and not results["GBPUSD"].get("skipped") else ""),
        "",
        "---",
        "",
    ]

    for pair, res in results.items():
        lines.append(f"## {pair}")
        lines.append("")

        if res.get("skipped"):
            lines.append(f"**Skipped:** {res.get('reason', '')}")
            lines.append("")
            continue

        dens = res.get("density", {})
        lines += [
            "### Density Check",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| N_breach_total | {dens.get('n_breach_total', 'N/A')} |",
            f"| N_breach_UP | {dens.get('n_breach_up', 'N/A')} |",
            f"| N_breach_DOWN | {dens.get('n_breach_down', 'N/A')} |",
            f"| N_breach_.XX00 | {dens.get('n_breach_00', 'N/A')} |",
            f"| N_breach_.XX50 | {dens.get('n_breach_50', 'N/A')} |",
            f"| Gate N ≥ 200 | **{dens.get('density_gate', 'N/A')}** |",
            "",
        ]

        by_year = dens.get("by_year", {})
        if by_year:
            lines.append(f"By year: " + " | ".join(f"{y}: {n}" for y, n in sorted(by_year.items())))
            lines.append("")

        if res.get("gate") == "FAIL_DENSITY":
            lines.append("**⛔ DENSITY GATE FAIL — IC not run.**")
            lines.append("")
            continue

        ic = res.get("ic", {})
        lines += [
            "### IC Results",
            "",
            "| Horizon | N | IC_spearman | t_HAC_NW6 | mean_sret (pips) | hit% | Gate |",
            "|---------|---|-------------|-----------|-----------------|------|------|",
        ]
        for h, r in ic.items():
            if "ic_spearman" in r:
                lines.append(
                    f"| {h} | {r['n']} | {r['ic_spearman']:.4f} | {r['t_hac_nw6']:.3f} "
                    f"| {r['mean_sret_pips']:.4f} | {r['hit_rate']*100:.1f}% | **{r['gate']}** |"
                )
            else:
                lines.append(f"| {h} | — | — | — | — | — | {r.get('gate', 'N/A')} |")

        lines.append("")

        gate = res.get("gate", "N/A")
        lines.append(f"**Overall gate: {gate}**")
        lines.append("")

        per_year = res.get("per_year", {})
        for h, rows in per_year.items():
            lines += [
                f"### Per-year breakdown — {h}",
                "",
                "| Year | N | IC | t_HAC | hit% |",
                "|------|---|----|-------|------|",
            ]
            for row in rows:
                ic_s  = f"{row['ic']:.4f}"   if row["ic"]   is not None else "N/A"
                t_s   = f"{row['t_hac']:.3f}" if row["t_hac"] is not None else "N/A"
                hit_s = f"{row['hit_rate']*100:.1f}%" if row["hit_rate"] is not None else "N/A"
                lines.append(f"| {row['year']} | {row['n']} | {ic_s} | {t_s} | {hit_s} |")
            lines.append("")

    lines += [
        "---",
        "",
        "## Gate Verdict Summary",
        "",
        "| Pair | Density | Overall IC Gate |",
        "|------|---------|----------------|",
    ]
    for pair, res in results.items():
        if res.get("skipped"):
            lines.append(f"| {pair} | SKIPPED | SKIPPED |")
        else:
            dens_g = res.get("density", {}).get("density_gate", "N/A")
            ic_g   = res.get("gate", "N/A")
            lines.append(f"| {pair} | {dens_g} | **{ic_g}** |")

    lines += [
        "",
        "---",
        "",
        "## n_tests Accounting",
        "",
        f"| Step | Tests | Cumul |",
        f"|------|-------|-------|",
        f"| Baseline (ORB v1 archived) | — | 170 |",
        f"| EUR/USD IC: 5 horizons | +5 | 175 |",
    ]

    gbp = results.get("GBPUSD", {})
    if not gbp.get("skipped"):
        lines.append(f"| GBP/USD IC: 5 horizons | +5 | 180 |")
    else:
        lines.append(f"| GBP/USD: SKIPPED (EUR/USD IC ≤ 0) | +0 | 175 |")

    lines += ["", "---", "", "*Generated by ic_round_number.py — PRESPEC.md locked.*"]

    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
