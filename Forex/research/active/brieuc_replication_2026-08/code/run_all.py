"""
run_all.py — orchestre la réplication complète : génère les trades des 5 EA
(naïf+corrigé, table SPECS.md), calcule R gross/net aux 3 barèmes de coût,
Sharpe (L47), walk-forward 5 folds, découpe de régime 4 ans, HAC lag-6,
block-bootstrap, placebo apparié, DSR (dsr.py).

CHECKPOINTED PAR INSTRUMENT (2026-08-28) : chaque instrument traité écrit
immédiatement son fichier de trades sur disque, et resultats.csv est
réécrit (état complet, DSR recalculé sur la famille des instruments déjà
traités) après CHAQUE instrument -- un run interrompu laisse un livrable
partiel exploitable, pas un run complet qui n'arrive jamais.
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib
import strategies as S
from dsr import DSRCalibrationWarning

warnings.filterwarnings("ignore", category=DSRCalibrationWarning)

OUT_DIR = Path(__file__).parent.parent
CKPT_DIR = OUT_DIR / "code" / "_checkpoints"
CKPT_DIR.mkdir(exist_ok=True)
LOAD_BUFFER_DAYS = 420

STRATS = {
    "LondonBreakout": S.london_breakout,
    "DailyBreakout": S.daily_breakout,
    "BollingerBands": S.bollinger_bands,
    "FVG": S.fvg,
    "MAcroisement": S.ma_croisement,
}


def process_instrument(instr: str, start_str: str) -> pd.DataFrame:
    ckpt = CKPT_DIR / f"trades_{instr}.parquet"
    if ckpt.exists():
        print(f"  [skip, checkpoint exists] {instr}", flush=True)
        return pd.read_parquet(ckpt)

    start = pd.Timestamp(start_str, tz="UTC")
    end = pd.Timestamp(lib.ANALYSIS_END, tz="UTC")
    load_start = (start - pd.Timedelta(days=LOAD_BUFFER_DAYS)).strftime("%Y-%m-%d")
    t0 = time.time()
    print(f"  loading {instr} from {load_start} ...", flush=True)
    m1 = lib.load_m1(instr, start=load_start, end=lib.ANALYSIS_END)
    print(f"  [{time.time()-t0:6.1f}s] {len(m1):,} M1 bars loaded", flush=True)

    trades = []
    for strat_name, fn in STRATS.items():
        if strat_name == "FVG" and instr not in lib.FVG_INSTRUMENTS:
            continue
        for version in ("naive", "corrected"):
            if strat_name == "DailyBreakout" and version == "naive":
                continue  # naive == corrected for the signal (SPECS.md §2)
            trds = fn(instr, version, m1, start, end)
            print(f"  [{time.time()-t0:6.1f}s] {strat_name:16s} {version:10s} "
                  f"-> {len(trds)} trades", flush=True)
            trades.extend(trds)

    df = pd.DataFrame(trades)
    df.to_parquet(ckpt)
    print(f"  [{time.time()-t0:6.1f}s] checkpoint written: {ckpt} ({len(df)} trades)", flush=True)
    return df


def compute_metrics(sub: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                     family_sharpes: list[float] | None, n_trials: int):
    sub = sub[sub["entry_time"].notna() & sub["exit_price"].notna()].copy()
    n = len(sub)
    n_years = (end - start).days / 365.25
    tpy = n / n_years if n_years > 0 else 0.0

    if n < 5:
        return dict(n_trades=n, trades_per_year=round(tpy, 2), n_years=round(n_years, 2))

    r_gross = np.array([lib.trade_r_multiple(e, x, s, side)
                         for e, x, s, side in zip(sub["entry_fill"], sub["exit_price"],
                                                    sub["sl0"], sub["side"])])
    r_gross = np.clip(r_gross, -1.5, None)

    out = dict(n_trades=n, trades_per_year=round(tpy, 2), n_years=round(n_years, 2),
               long_n=int((sub["side"] == "long").sum()), short_n=int((sub["side"] == "short").sum()),
               ambiguous_bar_frac=round(float(sub["ambiguous_bar"].mean()), 4),
               gap_entry_frac=round(float(sub["gap_entry"].mean()), 4),
               gap_exit_frac=round(float(sub["gap_exit"].mean()), 4),
               censored_frac=round(float((sub["exit_reason"] == "censored").mean()), 4),
               sharpe_gross=round(lib.annualized_sharpe(r_gross, tpy), 3),
               mean_r_gross=round(float(r_gross.mean()), 4))

    for tier_name, bps in lib.COST_TIERS.items():
        cost_r = np.array([lib.cost_in_r(e, s, bps) for e, s in zip(sub["entry_fill"], sub["sl0"])])
        r_net = r_gross - cost_r
        sharpe = lib.annualized_sharpe(r_net, tpy)
        t_hac = lib.hac_tstat(r_net, lag=6) if n >= 12 else float("nan")
        out[f"sharpe_{tier_name}"] = round(sharpe, 3)
        out[f"mean_r_{tier_name}"] = round(float(r_net.mean()), 4)
        out[f"hac_t_{tier_name}"] = round(t_hac, 3) if np.isfinite(t_hac) else None

        if tier_name == "eightcap_raw":
            for leg in ("long", "short"):
                mask = (sub["side"] == leg).values
                if mask.sum() >= 5:
                    out[f"sharpe_{leg}_eightcap"] = round(
                        lib.annualized_sharpe(r_net[mask], mask.sum() / n_years), 3)
                    out[f"mean_r_{leg}_eightcap"] = round(float(r_net[mask].mean()), 4)
                    out[f"n_{leg}"] = int(mask.sum())
                else:
                    out[f"sharpe_{leg}_eightcap"] = None
                    out[f"mean_r_{leg}_eightcap"] = None
                    out[f"n_{leg}"] = int(mask.sum())

            wf_df = sub.assign(_r_net=r_net)
            folds = lib.walk_forward_folds(wf_df, start, end, n_folds=5)
            fold_results = []
            for f in folds:
                if len(f) >= 3:
                    fold_results.append(float(f["_r_net"].mean()) > 0)
                else:
                    fold_results.append(None)
            valid = [x for x in fold_results if x is not None]
            out["wf_pct"] = round(sum(valid) / len(valid), 3) if valid else None
            out["wf_folds_valid"] = len(valid)
            out["wf_pattern"] = "WF:" + "".join(
                "1" if x else ("0" if x is not None else "-") for x in fold_results)

            regimes = lib.regime_4y_splits(wf_df, start, end)
            reg_str = ";".join(f"{k}:{v['_r_net'].mean():.4f}(n={len(v)})" for k, v in regimes.items())
            out["regime_4y"] = reg_str

            if n >= 20:
                means, sharpes = lib.block_bootstrap(r_net, block=20, n_boot=2000)
                out["boot_mean_ci_lo"] = round(float(np.percentile(means, 2.5)), 4)
                out["boot_mean_ci_hi"] = round(float(np.percentile(means, 97.5)), 4)
                out["boot_sharpe_ci_lo"] = round(float(np.percentile(sharpes, 2.5) * np.sqrt(tpy)), 3)
                out["boot_sharpe_ci_hi"] = round(float(np.percentile(sharpes, 97.5) * np.sqrt(tpy)), 3)
            else:
                out["boot_mean_ci_lo"] = out["boot_mean_ci_hi"] = None
                out["boot_sharpe_ci_lo"] = out["boot_sharpe_ci_hi"] = None

            r_abs = np.abs(r_gross)
            p_means, p_sharpes = lib.paired_placebo(r_abs, cost_r, n_draws=1000)
            pctl = float((p_sharpes < sharpe).mean())
            out["placebo_median_sharpe"] = round(float(np.median(p_sharpes) * np.sqrt(tpy)), 3)
            out["placebo_percentile_of_real"] = round(pctl, 3)

            fam = family_sharpes if family_sharpes else [sharpe]
            dsr_out = lib.dsr_report(r_net, fam, tpy, n_trials_override=n_trials)
            dsr_val = dsr_out.get("dsr", float("nan"))
            std_val = dsr_out.get("std_sr_trials", float("nan"))
            out["dsr"] = round(dsr_val, 4) if np.isfinite(dsr_val) else None
            out["dsr_std_sr_trials"] = round(std_val, 4) if np.isfinite(std_val) else None
            out["dsr_n_trials"] = dsr_out.get("n_trials")

    return out


def recompute_and_write_results(all_trades_df: pd.DataFrame):
    """Recompute every metrics row using the CURRENT family of instruments processed
    so far, and overwrite resultats.csv. Cheap (seconds), safe to call after every
    instrument so the deliverable is always the best available partial state."""
    grp_cols = ["strategy", "instrument", "version"]
    family_sharpes = []
    for (strat, instr, version), sub in all_trades_df.groupby(grp_cols):
        start = pd.Timestamp(lib.INSTRUMENTS[instr], tz="UTC")
        end = pd.Timestamp(lib.ANALYSIS_END, tz="UTC")
        sub2 = sub[sub["entry_time"].notna() & sub["exit_price"].notna()]
        if len(sub2) < 10:
            continue
        n_years = (end - start).days / 365.25
        tpy = len(sub2) / n_years
        r_gross = np.array([lib.trade_r_multiple(e, x, s, side)
                             for e, x, s, side in zip(sub2["entry_fill"], sub2["exit_price"],
                                                        sub2["sl0"], sub2["side"])])
        cost_r = np.array([lib.cost_in_r(e, s, lib.COST_TIERS["eightcap_raw"])
                            for e, s in zip(sub2["entry_fill"], sub2["sl0"])])
        r_net = r_gross - cost_r
        family_sharpes.append(lib.annualized_sharpe(r_net, tpy))
    n_trials_principal = len(family_sharpes)

    rows = []
    for (strat, instr, version), sub in all_trades_df.groupby(grp_cols):
        start = pd.Timestamp(lib.INSTRUMENTS[instr], tz="UTC")
        end = pd.Timestamp(lib.ANALYSIS_END, tz="UTC")
        metrics = compute_metrics(sub, start, end, family_sharpes, n_trials_principal)
        row = dict(strategy=strat, instrument=instr, version=version)
        row.update(metrics)
        rows.append(row)

    results = pd.DataFrame(rows).sort_values(["strategy", "instrument", "version"])
    out_csv = OUT_DIR / "resultats.csv"
    results.to_csv(out_csv, index=False)
    n_done = all_trades_df["instrument"].nunique()
    print(f"  -> resultats.csv rewritten ({len(results)} rows, {n_done} instruments done, "
          f"n_tests_principal={n_trials_principal})", flush=True)


def main():
    print("Building all trades, checkpointed per instrument ...", flush=True)
    all_dfs = []
    for instr, start_str in lib.INSTRUMENTS.items():
        print(f"[{time.strftime('%H:%M:%S')}] === {instr} ===", flush=True)
        df = process_instrument(instr, start_str)
        all_dfs.append(df)
        combined = pd.concat(all_dfs, ignore_index=True)
        combined.to_csv(OUT_DIR / "trades_detail.csv", index=False)
        recompute_and_write_results(combined)
    print("DONE.", flush=True)


if __name__ == "__main__":
    main()
