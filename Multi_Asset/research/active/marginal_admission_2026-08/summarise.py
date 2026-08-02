"""Assemble the decision table.

Ranking is by Delta p(pass), then Delta duration, as the brief requires. The
*verdict*, however, cannot be read off Delta p(pass) alone, and the null control in
``null_control.py`` is the reason:

    a zero-mean, zero-edge series with 10-day serial persistence buys
    Delta p(pass) = +0.149 on this book.

So "Delta p(pass) > 0" is not evidence of anything. Two bands are therefore carried:

* **iid null band** (``gauss_zero`` / ``flat_filler``, p95 ~ +0.02) — the floor for a
  candidate with little serial dependence.
* **own-shift placebo** (stage 2) — the candidate's own series circularly shifted, so
  its mean, its marginal distribution and its autocorrelation are all preserved and
  only its alignment with the book is destroyed. This is the per-candidate,
  autocorrelation-matched band, and it is the one that decides.

Three-valued vocabulary:
  PASS          Delta p(pass) above the candidate's own shift-placebo maximum, with
                the paired-seed interval clearing the placebo mean.
  UNDERPOWERED  positive but inside the placebo distribution or inside the seed noise.
  REJECTED      at or below the iid null band.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def autocorr(s: pd.Series, lags: int = 10) -> float:
    """Mean absolute autocorrelation over lags 1..k — the quantity the null control
    showed to drive Delta p(pass) independently of any edge."""
    x = s.dropna().to_numpy()
    x = x - x.mean()
    d = float((x * x).sum())
    if d == 0:
        return np.nan
    return float(np.mean([abs((x[k:] * x[:-k]).sum() / d) for k in range(1, lags + 1)]))


def main() -> None:
    s1 = pd.read_csv(HERE / "stage1_all_candidates.csv")
    s2 = pd.read_csv(HERE / "stage2_shortlist.csv")
    nul = pd.read_csv(HERE / "null_control.csv")
    panel = pd.read_pickle(HERE / "cache" / "panel.pkl")

    iid_band = float(nul.set_index("variant").loc[["gauss_zero", "flat_filler"], "d_p_p95"].max())
    block_null = float(nul.set_index("variant").loc["gauss_block", "d_p_mean"])
    ok = s1[s1.status == "OK"].copy()
    ok["ac10"] = ok["name"].map(lambda n: autocorr(panel["series"][n]))
    ok = ok.merge(s2, on="name", how="left")

    def verdict(r):
        dp = r["d_p_mean"] if np.isfinite(r.get("d_p_mean", np.nan)) else r["d_p_pass"]
        if dp <= iid_band:
            return "REJECTED"
        if not np.isfinite(r.get("placebo_max", np.nan)):
            return "UNDERPOWERED"      # never reached stage 2 -> no matched band
        if dp > r["placebo_max"] and r["d_p_lo"] > r["placebo_mean"]:
            return "PASS"
        return "UNDERPOWERED"

    ok["d_p_final"] = np.where(ok["d_p_mean"].notna(), ok["d_p_mean"], ok["d_p_pass"])
    ok["verdict"] = ok.apply(verdict, axis=1)
    ok = ok.sort_values(["d_p_final", "d_days"], ascending=[False, True])

    cols = ["name", "family", "cost", "n_obs", "sr_cand", "rho", "fill_rate", "ac10",
            "d_sr", "sr_verdict", "mde_dsr", "ci_lo", "ci_hi", "p_boot", "alpha_eff",
            "d_p_final", "d_p_sd", "mde_d_p", "placebo_mean", "placebo_max",
            "excess_vs_placebo", "d_days", "d_days_mean",
            "p_pass_book", "p_pass_comb", "days_book", "days_comb",
            "p_daily_book", "p_daily_comb", "clip_flag", "tail_ratio",
            "r2_BH_US500", "r2_BH_XAUUSD", "r2_BH_USDJPY", "verdict"]
    ok[[c for c in cols if c in ok.columns]].round(5).to_csv(HERE / "decision_table.csv", index=False)

    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(f"candidates evaluated  : {len(ok)}")
    print(f"iid null band (p95)   : {iid_band:+.4f}")
    print(f"block null (zero edge): {block_null:+.4f}   <- Delta p(pass) buyable with no edge")
    print(f"book alone            : p(pass) {ok['p_pass_book'].iloc[0]:.4f}, "
          f"median {ok['days_book'].iloc[0]:.0f} d, "
          f"{ok['p_daily_book'].iloc[0]:.1%} of failures on the daily stop")
    print("\n" + ok["verdict"].value_counts().to_string())

    show = ["name", "family", "sr_cand", "rho", "fill_rate", "ac10", "d_sr",
            "d_p_final", "d_p_sd", "placebo_mean", "placebo_max", "d_days", "verdict"]
    print("\n=== TOP 15 by Delta p(pass) ===")
    print(ok[show].head(15).round(4).to_string(index=False))
    print("\n=== BOTTOM 6 ===")
    print(ok[show].tail(6).round(4).to_string(index=False))

    print("\n=== criterion disagreement ===")
    print(f"  Delta SR <= 0 but Delta p(pass) > iid band : "
          f"{int(((ok.d_sr <= 0) & (ok.d_p_final > iid_band)).sum())} / {len(ok)}")
    print(f"  Delta SR >  0 but Delta p(pass) <= band    : "
          f"{int(((ok.d_sr > 0) & (ok.d_p_final <= iid_band)).sum())} / {len(ok)}")
    print(f"  Sharpe gate PASS (Sidak, n={int(ok.alpha_eff.notna().sum())} trials) : "
          f"{int((ok.sr_verdict == 'PASS').sum())}")
    print(f"  corr(ac10, Delta p) = {ok[['ac10', 'd_p_final']].corr().iloc[0, 1]:+.3f}")

    print("\n=== winsorisation contrast (same edge, tails clipped vs raw) ===")
    w = ok[ok.name.isin(["ovn_GOLD_fut", "ovn_GOLD_winsorised"])]
    print(w[["name", "sr_cand", "d_sr", "d_p_final", "d_days", "tail_ratio"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
