"""Apply the marginal admission test to every harvested edge.

Stage 1 screens all candidates on Delta SR (ERC, block bootstrap, Sidak) and a
single-seed Delta p(pass). Stage 2 re-runs the shortlist with multiple Monte Carlo
seeds and a **circular-shift placebo** that isolates the part of the improvement
attributable to calendar alignment rather than to the sleeve's raw return.

Nothing here re-measures an edge. Every input series was produced by an earlier,
already-counted study; this is a different decision rule applied to the same
numbers, so it is N0 (non-deflating) per the project's trial accounting.

Engines are imported, never re-implemented:
``Portfolio.admission.marginal.admit`` and
``Portfolio.admission.barrier.pass_probability_delta``.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

WT = Path("<HOME>/Desktop/Algo_claude_marginal")
sys.path.insert(0, str(WT))
warnings.filterwarnings("ignore")

from Portfolio.admission import BarrierConfig, admit, pass_probability_delta  # noqa: E402

from harvest import beta_r2, build_factors, calendar_overlap, clipping_signature  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

# FTMO $10k 2-step, as confirmed by the account holder 2026-08-01:
# daily -5% of the day's opening equity, STATIC floor -10% of the initial balance,
# no time limit (the 91-day wall was self-imposed).
CFG = BarrierConfig(target_p1=0.10, target_p2=0.05, daily_stop=0.05,
                    static_floor=0.10, max_days_p1=0, max_days_p2=0)

MIN_OVERLAP = 250          # project convention before a Sharpe is usable
N_PATHS_S1 = 1200
N_PATHS_S2 = 2000
N_BOOT = 800
MEAN_BLOCK = 10.0
SEEDS_S2 = (0, 1, 2)
SHIFTS = (211, 433, 619, 877)   # coprime-ish offsets for the placebo


def calendar_series(cand: pd.Series, book_index: pd.DatetimeIndex) -> pd.Series | None:
    """Candidate on the book's calendar, flat (0.0) where it does not trade.

    Restricted to the candidate's own data span first: outside it the sleeve has no
    history, which is not the same statement as "it was flat", and padding it would
    manufacture calendar the sleeve never lived through.
    """
    lo = max(cand.index.min(), book_index.min())
    hi = min(cand.index.max(), book_index.max())
    idx = book_index[(book_index >= lo) & (book_index <= hi)]
    if len(idx) < MIN_OVERLAP:
        return None
    return cand.reindex(idx).fillna(0.0).rename(cand.name)


def barrier_delta(book: pd.Series, cand: pd.Series, seed: int, n_paths: int) -> dict:
    return pass_probability_delta(
        book.to_frame("book"), cand, cfg=CFG, scheme="erc",
        n_paths=n_paths, mean_block=MEAN_BLOCK, seed=seed, normalize_vol=True,
    )


def main(stage: int = 0) -> None:
    d = pd.read_pickle(CACHE / "panel.pkl")
    book: pd.Series = d["book"]
    series: dict[str, pd.Series] = d["series"]
    factors = build_factors()
    man = pd.read_csv(HERE / "harvest_manifest.csv").set_index("name")

    rows = []
    names = sorted(series)
    if stage == 2:
        names = []
    n_trials = len(names)
    for i, nm in enumerate(names, 1):
        cal = calendar_series(series[nm], book.index)
        if cal is None:
            rows.append(dict(name=nm, status="NO_OVERLAP"))
            print(f"[{i}/{n_trials}] {nm}: NO_OVERLAP")
            continue
        bk = book.reindex(cal.index)
        try:
            a = admit(bk.to_frame("book"), cal, scheme="erc", periods_per_year=252.0,
                      alpha=0.05, n_trials=n_trials, n_boot=N_BOOT,
                      mean_block=MEAN_BLOCK, seed=0, min_obs=MIN_OVERLAP)
            b = barrier_delta(bk, cal, seed=0, n_paths=N_PATHS_S1)
        except Exception as e:  # noqa: BLE001
            rows.append(dict(name=nm, status=f"ERR:{type(e).__name__}"))
            print(f"[{i}/{n_trials}] {nm}: ERR {e}")
            continue
        row = dict(
            name=nm, status="OK",
            family=man.at[nm, "family"] if nm in man.index else "",
            cost=man.at[nm, "cost"] if nm in man.index else "",
            n_obs=a.n_obs, sr_cand=a.candidate_sharpe, rho=a.rho,
            sr_book=a.sharpe_book, sr_comb=a.sharpe_combined, d_sr=a.delta_sharpe,
            marginal_hurdle=a.marginal_hurdle, erc_hurdle=a.erc_hurdle,
            p_boot=a.p_value, ci_lo=a.ci[0], ci_hi=a.ci[1],
            mde_dsr=a.detectable_delta_sharpe, alpha_eff=a.alpha_effective,
            sr_verdict=a.verdict,
            p_pass_book=b["p_pass_book"], p_pass_comb=b["p_pass_combined"],
            d_p_pass=b["delta_p_pass"], days_book=b["median_days_book"],
            days_comb=b["median_days_combined"], d_days=b["delta_median_days"],
            p_daily_book=b["p_fail_daily_book"], p_daily_comb=b["p_fail_daily_combined"],
            **calendar_overlap(bk, cal), **clipping_signature(cal),
            **beta_r2(cal, factors),
        )
        rows.append(row)
        print(f"[{i}/{n_trials}] {nm}: dSR={a.delta_sharpe:+.3f} ({a.verdict}) "
              f"rho={a.rho:+.3f} dP={b['delta_p_pass']:+.4f} dDays={b['delta_median_days']:+.1f}")

    if stage != 2:
        s1 = pd.DataFrame(rows)
        s1.to_csv(HERE / "stage1_all_candidates.csv", index=False)
        print(f"\nstage 1 done: {len(s1)} rows -> stage1_all_candidates.csv")
        if stage == 1:
            return
    s1 = pd.read_csv(HERE / "stage1_all_candidates.csv")

    # ── stage 2: shortlist gets seeds + circular-shift placebo ────────────────
    ok = s1[s1.status == "OK"].copy()
    short = ok.nlargest(12, "d_p_pass")["name"].tolist()
    rows2 = []
    for i, nm in enumerate(short, 1):
        cal = calendar_series(series[nm], book.index)
        bk = book.reindex(cal.index)
        real = [barrier_delta(bk, cal, seed=s, n_paths=N_PATHS_S2) for s in SEEDS_S2]
        dp = np.array([r["delta_p_pass"] for r in real])
        dd = np.array([r["delta_median_days"] for r in real])
        # placebo: same sleeve, same marginal distribution and autocorrelation,
        # alignment with the book destroyed by a circular shift.
        pl = []
        v = cal.to_numpy()
        for k in SHIFTS:
            shifted = pd.Series(np.roll(v, k), index=cal.index, name=cal.name)
            pl.append(barrier_delta(bk, shifted, seed=0, n_paths=N_PATHS_S2)["delta_p_pass"])
        pl = np.array(pl)
        rows2.append(dict(
            name=nm, d_p_mean=dp.mean(), d_p_sd=dp.std(ddof=1),
            d_p_se=dp.std(ddof=1) / np.sqrt(len(dp)),
            d_p_lo=dp.mean() - 1.96 * dp.std(ddof=1) / np.sqrt(len(dp)),
            d_p_hi=dp.mean() + 1.96 * dp.std(ddof=1) / np.sqrt(len(dp)),
            mde_d_p=1.645 * dp.std(ddof=1) / np.sqrt(len(dp)),
            d_days_mean=dd.mean(), d_days_sd=dd.std(ddof=1),
            placebo_mean=pl.mean(), placebo_max=pl.max(),
            excess_vs_placebo=dp.mean() - pl.mean(),
            beats_placebo=bool(dp.mean() > pl.max()),
        ))
        print(f"[S2 {i}/{len(short)}] {nm}: dP={dp.mean():+.4f}+-{dp.std(ddof=1):.4f} "
              f"placebo={pl.mean():+.4f} (max {pl.max():+.4f})")

    pd.DataFrame(rows2).to_csv(HERE / "stage2_shortlist.csv", index=False)
    print("stage 2 done -> stage2_shortlist.csv")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
