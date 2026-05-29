"""
slip_analysis.py — Round-trip slippage analysis from VoieB_decisions.csv

Convention: adverse = positive
  slip_entry_bps = direction * (fill_entry - mid_signal) / mid_signal * 1e4
  slip_exit_bps  = -direction * (fill_exit  - mid_exit)  / mid_exit  * 1e4
  slip_rt_bps    = slip_entry_bps + slip_exit_bps

Viability gates (Sharpe sensitivity):
  median slip_rt ≤ 3 bp  → VIABLE
  3–5 bp                  → MARGINAL (Sharpe ~0.5–1.0, monitor closely)
  > 5 bp                  → NON VIABLE (archive)

Usage:
  /usr/bin/python3 slip_analysis.py [--csv PATH] [--fomc_csv PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS_DIR = Path(__file__).parent / "results"

GATE_VIABLE   = 3.0   # bp
GATE_MARGINAL = 5.0   # bp


# ── Data loading ──────────────────────────────────────────────────────────────

def load_decisions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"mid_signal", "fill_entry", "mid_exit", "fill_exit"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["direction", "mid_signal", "fill_entry", "mid_exit", "fill_exit",
                "spread_signal_bps", "lots", "leverage", "gap_bps",
                "pnl_points", "pnl_account_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    date_col = next((c for c in ["date_utc", "datetime_utc", "date"] if c in df.columns), None)
    if date_col:
        df["date_utc"] = pd.to_datetime(df[date_col], errors="coerce")

    df = df.dropna(subset=["mid_signal", "fill_entry", "mid_exit", "fill_exit"])
    df = df[(df["mid_signal"] > 0) & (df["mid_exit"] > 0)]
    return df


def compute_slippage(df: pd.DataFrame) -> pd.DataFrame:
    d = df["direction"].astype(float)
    df = df.copy()
    df["slip_entry_bps"] = d * (df["fill_entry"] - df["mid_signal"]) / df["mid_signal"] * 1e4
    df["slip_exit_bps"]  = -d * (df["fill_exit"]  - df["mid_exit"])  / df["mid_exit"]  * 1e4
    df["slip_rt_bps"]    = df["slip_entry_bps"] + df["slip_exit_bps"]
    return df


# ── Reporting ─────────────────────────────────────────────────────────────────

def verdict(median_rt: float) -> str:
    if median_rt <= GATE_VIABLE:
        return f"✅ VIABLE (median RT = {median_rt:.2f} bp ≤ {GATE_VIABLE:.0f} bp)"
    if median_rt <= GATE_MARGINAL:
        return (f"⚠️  MARGINAL (median RT = {median_rt:.2f} bp, {GATE_VIABLE:.0f}–{GATE_MARGINAL:.0f} bp "
                f"→ Sharpe ~0.5–1.0, monitor closely)")
    return (f"❌ NON VIABLE (median RT = {median_rt:.2f} bp > {GATE_MARGINAL:.0f} bp — archive)")


def print_stats(label: str, s: pd.Series) -> None:
    n = int(s.notna().sum())
    if n == 0:
        print(f"  {label:30s}  no data")
        return
    print(f"  {label:30s}  n={n:4d}  "
          f"mean={s.mean():+6.2f}  median={s.median():+6.2f}  "
          f"p90={s.quantile(.90):+6.2f}  p95={s.quantile(.95):+6.2f}  [bps]")


def run_analysis(csv_path: Path, fomc_path: Path | None = None) -> None:
    df_raw = load_decisions(csv_path)
    df = compute_slippage(df_raw)
    n = len(df)

    print("=" * 70)
    print("SLIP ANALYSIS — Voie B  (convention: adverse = positive)")
    print(f"CSV: {csv_path.name}  |  N trades: {n}")
    print("=" * 70)

    # ── Global ──
    print("\n[GLOBAL]")
    print_stats("slip_entry_bps",     df["slip_entry_bps"])
    print_stats("slip_exit_bps",      df["slip_exit_bps"])
    print_stats("slip_rt_bps",        df["slip_rt_bps"])
    if "spread_signal_bps" in df.columns and df["spread_signal_bps"].notna().any():
        print_stats("spread_signal_bps (IV.2)", df["spread_signal_bps"])

    med_rt = df["slip_rt_bps"].median()
    print(f"\n  ▶ {verdict(med_rt)}")

    # ── Per symbol ──
    if "symbol" in df.columns:
        print("\n[PER SYMBOL]")
        for sym, grp in df.groupby("symbol"):
            med_sym = grp["slip_rt_bps"].median()
            print(f"\n  {sym}")
            print_stats("  slip_entry_bps",  grp["slip_entry_bps"])
            print_stats("  slip_exit_bps",   grp["slip_exit_bps"])
            print_stats("  slip_rt_bps",     grp["slip_rt_bps"])
            print(f"    ▶ {verdict(med_sym)}")

    # ── Day of week ──
    if "date_utc" in df.columns and not df["date_utc"].isna().all():
        print("\n[BY DAY OF WEEK]")
        df["dow"] = df["date_utc"].dt.day_name()
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            grp = df[df["dow"] == day]
            if len(grp) == 0:
                continue
            print(f"  {day:12s}: n={len(grp):3d}  "
                  f"slip_rt median={grp['slip_rt_bps'].median():+.2f} bp  "
                  f"entry={grp['slip_entry_bps'].median():+.2f}  "
                  f"exit={grp['slip_exit_bps'].median():+.2f}")

    # ── FOMC/NFP ──
    if fomc_path is not None and fomc_path.exists() and "date_utc" in df.columns:
        fomc = pd.read_csv(fomc_path)
        fomc.columns = [c.strip().lower() for c in fomc.columns]
        date_col = next((c for c in fomc.columns if "date" in c), None)
        if date_col:
            fomc_dates = set(pd.to_datetime(fomc[date_col], errors="coerce").dt.date.dropna())
            df["is_fomc"] = df["date_utc"].dt.date.isin(fomc_dates)
            print("\n[FOMC / NFP DAYS]")
            for flag, label in [(True, "FOMC/NFP days"), (False, "Normal days")]:
                grp = df[df["is_fomc"] == flag]
                if len(grp) == 0:
                    continue
                print(f"\n  {label} (n={len(grp)})")
                print_stats("  slip_rt_bps", grp["slip_rt_bps"])
    elif fomc_path is None:
        print("\n  [FOMC/NFP] Pass --fomc_csv to flag high-impact macro days")

    # ── Exit reason breakdown ──
    if "exit_reason" in df.columns:
        print("\n[EXIT REASON]")
        for reason, grp in df.groupby("exit_reason"):
            print(f"  {reason:15s}: n={len(grp):3d}  "
                  f"slip_rt median={grp['slip_rt_bps'].median():+.2f} bp")

    # ── Save ──
    cols = ["date_utc", "symbol", "direction", "lots", "gap_bps",
            "slip_entry_bps", "slip_exit_bps", "slip_rt_bps"]
    for c in ["spread_signal_bps", "exit_reason", "pnl_points", "pnl_account_pct"]:
        if c in df.columns:
            cols.append(c)
    out = RESULTS_DIR / "slip_report.csv"
    out.parent.mkdir(exist_ok=True)
    df[cols].to_csv(out, index=False)
    print(f"\n  Report CSV → {out.relative_to(Path(__file__).parents[4])}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voie B slippage analysis")
    parser.add_argument("--csv", default=str(RESULTS_DIR / "voieb_test.csv"),
                        help="Path to VoieB_decisions.csv (default: results/voieb_test.csv)")
    parser.add_argument("--fomc_csv", default=None,
                        help="Optional CSV with FOMC/NFP event dates (column: date)")
    args = parser.parse_args()

    run_analysis(Path(args.csv), Path(args.fomc_csv) if args.fomc_csv else None)
