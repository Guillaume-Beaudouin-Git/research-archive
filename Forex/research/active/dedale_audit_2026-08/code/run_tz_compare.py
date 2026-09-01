"""AUDIT: baseline (naive UTC resample) vs tzfix (broker-local EET/EEST DST-aware resample for
H4/D1 TDI + weekly pivots) on the CONFIRMED 8-filter config, 8-pair universe, primary window.

Delta n_tests = 0: reproduction audit, not a new market hypothesis.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CFG = Path("<HOME>/Desktop/Algo_claude/Forex/research/active/dedale_config_2026-08/code")
ENG = Path("<HOME>/Desktop/Algo_claude/Forex/research/active/dedale_strategy_2026-08/code")
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(CFG)); sys.path.insert(0, str(ENG))

import dedale_engine as de  # noqa: E402
import intrabar_engine as base_eng  # noqa: E402 (baseline, unmodified)
import intrabar_engine_tzfix as tz_eng  # noqa: E402 (audit variant)

de.PAIR_CCY.update({"EURJPY": ("EUR", "JPY"), "EURGBP": ("EUR", "GBP"), "GBPJPY": ("GBP", "JPY")})
PAIRS = ["EURGBP", "EURJPY", "EURUSD", "GBPJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]

CONFIRMED = {(3, "CROSS"), (3, "TREND"), (4, "TREND"),
             (0, "ANGLE"), (1, "ANGLE"), (2, "ANGLE"), (3, "ANGLE"), (4, "ANGLE")}

START = pd.Timestamp("2018-01-05", tz="UTC")
END = pd.Timestamp("2024-07-29", tz="UTC")
TARGET = dict(n=648, wr=63.58, rr=0.719, total_pct=60.33)


def summarize(df: pd.DataFrame, label: str, n_pairs: int) -> dict:
    if df.empty:
        print(f"[{label}] NO TRADES")
        return {}
    n = len(df)
    wins = df["r_multiple"] > 0
    wr = wins.mean() * 100.0
    avg_win = df.loc[wins, "r_multiple"].mean()
    avg_loss = -df.loc[~wins, "r_multiple"].mean()
    rr = avg_win / avg_loss if avg_loss else np.nan
    # simple non-compounding total return at 1% risk/trade, no cost/swap (matches the "brut" fidelity
    # numbers already reported for the baseline, for apples-to-apples comparison)
    total_pct = (df["r_multiple"] * 1.0).sum()  # sum of R * 1% ~= approx additive return
    bal = np.cumprod(1.0 + df.sort_values("exit_time")["r_multiple"].values * 0.01)
    compounded_pct = (bal[-1] - 1.0) * 100.0
    row = dict(label=label, n=n, wr=wr, avg_win_R=avg_win, avg_loss_R=avg_loss, rr=rr,
               additive_pct=total_pct, compounded_pct=compounded_pct)
    print(f"--- {label} (n_pairs={n_pairs}) ---")
    for k, v in row.items():
        if k == "label":
            continue
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    return row


def run_all(engine_module, label: str) -> pd.DataFrame:
    frames = []
    for pair in PAIRS:
        t0 = time.time()
        df = engine_module.run_pair_intrabar(pair, CONFIRMED, start=START, end=END, verbose=False)
        frames.append(df)
        print(f"    [{label}/{pair}] {len(df)} trades ({time.time()-t0:.0f}s)", flush=True)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    print(f"TARGET (his numbers, 12 pairs): n={TARGET['n']} wr={TARGET['wr']} rr={TARGET['rr']} "
          f"total={TARGET['total_pct']}%")
    print("\n=== BASELINE (naive UTC resample, current repo state) ===")
    df_base = run_all(base_eng, "baseline")
    summarize(df_base, "BASELINE (8 pairs)", len(PAIRS))

    print("\n=== TZFIX (broker-local EET/EEST DST-aware H4/D1/weekly) ===")
    df_tz = run_all(tz_eng, "tzfix")
    summarize(df_tz, "TZFIX (8 pairs)", len(PAIRS))

    out_dir = HERE.parent
    df_base.to_csv(out_dir / "trades_baseline_8pairs.csv", index=False)
    df_tz.to_csv(out_dir / "trades_tzfix_8pairs.csv", index=False)
    print("\nWrote trades_baseline_8pairs.csv and trades_tzfix_8pairs.csv")
