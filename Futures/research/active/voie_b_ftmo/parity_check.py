"""
parity_check.py — Compare EA trades vs Python backtest (ftmo_voie_b.py).

Two input formats are auto-detected:

  --mt5_csv  (Strategy Tester)  MT5 Results → Save As CSV
             Expected columns: Date, Time, Symbol, Type, Lots, Price, Profit

  --mt5_csv  (Live decision log)  VoieB_decisions.csv written by EA
             Expected columns: datetime_utc, dst_h, gap_US500_bp … direction,
             leverage, lots_US500 … decision

Python reference: results/ftmo_voie_b_returns.csv (Date, ret)

Gates:
  direction concordance ≥ 95%
  sizing concordance    ≥ 90% (lot correlation; tolerates MT5 rounding)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
RESULTS_DIR = Path(__file__).parent / "results"
REF_RETURNS  = RESULTS_DIR / "ftmo_voie_b_returns.csv"

GATE_DIR_PCT  = 0.95
GATE_SIZE_PCT = 0.90


def _is_decision_log(df: pd.DataFrame) -> bool:
    """Return True if CSV looks like VoieB_decisions.csv (EA live log)."""
    return ("date_utc" in df.columns or "datetime_utc" in df.columns
            or ("direction" in df.columns and "decision" in df.columns))


def load_mt5_trades(csv_path: Path) -> pd.DataFrame:
    """
    Parse MT5 Strategy Tester CSV export OR EA decision log.
    Returns one row per day with: date, direction, total_lots (US500 proxy).
    """
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = [c.strip().lower() for c in df.columns]

    if _is_decision_log(df):
        return _load_decision_log(df)

    # ── MT5 Strategy Tester format ──
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["direction"] = df["type"].str.lower().map({"buy": 1, "sell": -1}).fillna(0).astype(int)
    df["lots"]      = pd.to_numeric(df.get("lots", 0), errors="coerce").fillna(0)
    df = df[df["direction"] != 0]
    return df


def _load_decision_log(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse EA VoieB_decisions.csv (live / demo log).
    Supports v1.20+ (date_utc, lots per symbol) and legacy (datetime_utc, lots_US500).
    Keeps only rows where a signal fired (direction != 0).
    """
    date_col = next((c for c in ["date_utc", "datetime_utc", "date"] if c in df.columns), None)
    df["date"] = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    df = df.dropna(subset=["date"])

    if "direction" in df.columns:
        df["direction"] = pd.to_numeric(df["direction"], errors="coerce").fillna(0).astype(int)
    else:
        df["direction"] = df["decision"].str.lower().map(
            {"long": 1, "short": -1, "no-signal": 0}).fillna(0).astype(int)

    # v1.20+: plain "lots" column; legacy: "lots_us500" or per-symbol columns
    if "lots" in df.columns:
        lots_col = "lots"
    else:
        lots_col = next((c for c in df.columns if "lots_us500" in c.lower()), None)
    df["lots"] = pd.to_numeric(df[lots_col], errors="coerce").fillna(0) if lots_col else 0.0

    df = df[df["direction"] != 0].copy()
    return df


def aggregate_daily(mt5: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate MT5 trades to daily level:
      - direction: sign of net lots (long-biased or short-biased)
      - total_lots
    """
    mt5["date_only"] = mt5["date"].dt.date
    grp = mt5.groupby("date_only").agg(
        net_lots=("lots", lambda x: (x * mt5.loc[x.index, "direction"]).sum()),
    ).reset_index()
    grp["direction_mt5"] = np.sign(grp["net_lots"]).astype(int)
    grp["total_lots_mt5"] = grp["net_lots"].abs()
    grp["date_only"] = pd.to_datetime(grp["date_only"])
    return grp.set_index("date_only")


def load_python_ref(path: Path) -> pd.DataFrame:
    """Load Python backtest daily returns. Active days = ret != 0."""
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    df.columns = ["ret"]
    df["direction_py"] = np.sign(df["ret"]).astype(int)
    df["active_py"] = df["ret"] != 0.0
    return df


def run_parity(mt5_path: Path) -> dict:
    py_ref = load_python_ref(REF_RETURNS)
    mt5    = load_mt5_trades(mt5_path)
    mt5_d  = aggregate_daily(mt5)

    # common active dates
    common = py_ref.index.intersection(mt5_d.index)
    py_common  = py_ref.loc[common]
    mt5_common = mt5_d.loc[common]

    active_mask = py_common["active_py"] | (mt5_common["direction_mt5"] != 0)
    n_active = active_mask.sum()

    if n_active == 0:
        print("ERROR: no active days in common range.")
        return {}

    py_dir  = py_common.loc[active_mask, "direction_py"]
    mt5_dir = mt5_common.loc[active_mask, "direction_mt5"]

    dir_match = (py_dir == mt5_dir).sum()
    dir_pct   = dir_match / n_active

    # sizing concordance: ratio lots within [0.75, 1.25] treated as OK
    # (python returns don't carry lot info — use correlation of absolute returns as proxy)
    py_abs  = py_common.loc[active_mask, "ret"].abs()
    # MT5 total lots as proxy (normalized)
    mt5_lots = mt5_common.loc[active_mask, "total_lots_mt5"]
    mt5_lots_n = (mt5_lots / mt5_lots.mean()) if mt5_lots.mean() > 0 else mt5_lots
    py_abs_n   = (py_abs   / py_abs.mean())   if py_abs.mean()  > 0 else py_abs
    sizing_corr = float(py_abs_n.corr(mt5_lots_n)) if len(py_abs_n) > 5 else 0.0

    result = {
        "n_common_dates":         len(common),
        "n_active_days":          int(n_active),
        "direction_match":        int(dir_match),
        "direction_concordance":  round(dir_pct, 4),
        "sizing_corr_proxy":      round(sizing_corr, 4),
        "gate_direction_pass":    dir_pct >= GATE_DIR_PCT,
        "gate_sizing_pass":       sizing_corr >= GATE_SIZE_PCT,
        "overall_pass":           dir_pct >= GATE_DIR_PCT and sizing_corr >= GATE_SIZE_PCT,
    }

    # print report
    print("=" * 60)
    print("PARITY REPORT — Voie B EA ↔ Python backtest")
    print("=" * 60)
    print(f"Common date range   : {common[0].date()} → {common[-1].date()}")
    print(f"Active days         : {n_active}")
    print(f"Direction match     : {dir_match}/{n_active} = {dir_pct:.1%}  (gate ≥{GATE_DIR_PCT:.0%})",
          "✅ PASS" if result["gate_direction_pass"] else "❌ FAIL")
    print(f"Sizing corr (proxy) : {sizing_corr:.3f}               (gate ≥{GATE_SIZE_PCT:.0%})",
          "✅ PASS" if result["gate_sizing_pass"] else "❌ FAIL")
    print("-" * 60)
    print("OVERALL:", "✅ PASS — déploiement autorisé" if result["overall_pass"]
          else "❌ FAIL — itérer avant déploiement VPS")
    print("=" * 60)

    # save csv
    out = pd.DataFrame({
        "direction_py":   py_dir,
        "direction_mt5":  mt5_dir,
        "match":          py_dir == mt5_dir,
        "ret_py":         py_common.loc[active_mask, "ret"],
        "lots_mt5":       mt5_lots,
    })
    out_path = RESULTS_DIR / "parity_report.csv"
    out.to_csv(out_path)
    print(f"Trade-level CSV → {out_path.relative_to(Path(__file__).parents[4])}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mt5_csv", required=True,
                        help="Path to MT5 Strategy Tester Results CSV export")
    args = parser.parse_args()
    r = run_parity(Path(args.mt5_csv))
    sys.exit(0 if r.get("overall_pass") else 1)
