"""
Two independent null comparisons for the 396-cell grid (PREREGISTRATION.md §4 gate 3):

(a) Closed-form / Monte-Carlo max-order-statistic of N=396 iid N(0,1) draws — "if this
    grid were pure noise, how extreme would the single best |t| be expected to look."
(b) An empirical, matched-autocorrelation placebo: block-shuffle (Politis-Romano
    stationary bootstrap, mean block 20 bars) the actual (return, range) pairs of each
    instrument's own 15-min bar series to build a synthetic price path with the SAME
    local autocorrelation/vol-clustering but NO genuine temporal structure, then re-run
    the exact canonical cell (SMA20+z-score, CROSS entry, ATR-bracket 1:1 exit, H=8) on
    it, 25 draws/instrument. This directly answers "does my own engine manufacture
    t>2.5 out of shuffled noise with this instrument's own autocorrelation."
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataload as DL
import engine_lib as E
import run_grid as RG
from engine import indicators as ind

RNG = np.random.default_rng(20260821)
N_MC = 20000       # Monte Carlo draws for the iid max-order-statistic
N_PLACEBO = 25     # synthetic price draws per instrument


def simulate_iid_max(n_cells: int, n_mc: int = N_MC, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    draws = rng.standard_normal(size=(n_mc, n_cells))
    return np.abs(draws).max(axis=1)


def stationary_block_shuffle(r: np.ndarray, rng, mean_block: int = 20) -> np.ndarray:
    n = r.size
    p = 1.0 / mean_block
    out = np.empty(n, dtype=r.dtype)
    i = rng.integers(0, n)
    for k in range(n):
        out[k] = r[i]
        if rng.random() < p:
            i = rng.integers(0, n)
        else:
            i = i + 1 if i + 1 < n else 0
    return out


def synthetic_frame(df: pd.DataFrame, rng, mean_block: int = 100) -> pd.DataFrame:
    close = df["close"].to_numpy(float)
    open_ = df["open"].to_numpy(float)
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    n = len(close)
    logret = np.empty(n); logret[0] = 0.0
    logret[1:] = np.log(close[1:] / close[:-1])
    rel_range = np.empty(n)
    rel_range[0] = (high[0] - low[0]) / max(close[0], 1e-9)
    rel_range[1:] = (high[1:] - low[1:]) / close[:-1]
    # IMPORTANT: this is a SESSION-FILTERED array (only liquid-hour bars kept), so
    # logret at the FIRST bar of every session embeds the real overnight/weekend gap
    # (often much larger than an intra-session step). A flat shuffle of the whole
    # array relocates these fat-tailed gap returns to random MID-session positions,
    # manufacturing fake isolated jumps that trigger the z-score entry constantly and
    # never genuinely revert -> a large, spurious negative bias unrelated to any real
    # market mechanism (diagnosed empirically: block=20 and block=100 gave the same
    # ~-4/-5 mean t, ruling out a block-length resonance and pointing at this instead).
    # Fix: only shuffle the INTRA-session continuation returns among themselves; the
    # session-open gap return stays fixed at its true session and true magnitude.
    is_first = (df["session_date"] != df["session_date"].shift(1)).to_numpy()
    is_first[0] = True
    non_first = np.where(~is_first)[0]
    perm = stationary_block_shuffle(np.arange(non_first.size), rng, mean_block=mean_block)
    lr_s = logret.copy(); rr_s = rel_range.copy()
    lr_s[non_first] = logret[non_first][perm]
    rr_s[non_first] = rel_range[non_first][perm]
    lr_s[0] = 0.0
    close_s = close[0] * np.exp(np.cumsum(lr_s))
    open_s = np.empty(n); open_s[0] = open_[0]
    open_s[1:] = close_s[:-1]
    hi_s = np.maximum(open_s, close_s) + 0.5 * rr_s * np.r_[close[0], close_s[:-1]]
    lo_s = np.minimum(open_s, close_s) - 0.5 * rr_s * np.r_[close[0], close_s[:-1]]
    out = df.copy()
    out["open"] = open_s; out["high"] = hi_s; out["low"] = lo_s; out["close"] = close_s
    return out


def canonical_cell_t(df: pd.DataFrame, bpy: float, scale: pd.Series, cost: float, ne_cache: dict) -> float:
    close = df["close"]
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    dist = E.dist_zscore(close, 20)
    sl, tp = RG.cell_bracket_sym(atr20, 1.0, 1.0)
    res = RG.run_one(df, bpy, scale, cost, ne_cache, dist=dist, mode="signed", threshold=2.0,
                     entry="CROSS", sl_dist=sl, tp_dist=tp, max_hold=RG.H_BACKSTOP, meta={})
    return res.get("gross_t", float("nan"))


def main():
    t0 = time.time()
    grid = pd.read_csv(HERE / "grille_resultats.csv")
    real_t = grid["gross_t"].dropna().to_numpy()
    n_cells = len(real_t)

    mc_max = simulate_iid_max(n_cells)
    obs_max_abs = float(np.abs(real_t).max())
    p_iid = float((mc_max >= obs_max_abs).mean())
    exp_tail_iid = n_cells * 2 * (1 - 0.9938)  # P(|Z|>2.5) approx 0.0124 two-sided
    obs_tail_pos = int((real_t > 2.5).sum())
    obs_tail_neg = int((real_t < -2.5).sum())

    print(f"Real grid: n={n_cells}, mean(t)={real_t.mean():.3f}, median={np.median(real_t):.3f}, "
          f"max|t|={obs_max_abs:.3f}")
    print(f"iid-N(0,1) max-order-stat over {N_MC} MC draws of {n_cells} cells: "
          f"E[max|t|]={mc_max.mean():.3f}  P95={np.percentile(mc_max,95):.3f}  "
          f"P(max|t|>=observed)={p_iid:.4f}")
    print(f"tails: observed t>2.5 = {obs_tail_pos}, t<-2.5 = {obs_tail_neg}  "
          f"(iid-expected count each tail ~{n_cells*0.0062:.1f})")

    # empirical matched-autocorrelation placebo on the canonical cell, per instrument.
    # Two block lengths: 20 (== the signal's own SMA/ATR lookback -- a deliberate
    # diagnostic: a block length equal to the signal window can splice two unrelated
    # regimes together every ~20 bars and manufacture fake "extreme z-score" trigger
    # events at the seams, which is itself an informative pitfall to report) and 100
    # (>> the 20-bar signal window, so seams rarely fall inside a live rolling window --
    # the honest matched-autocorrelation null used for the headline comparison).
    real_canonical_t = {}
    canon_rows = grid[(grid["block"] == "2_entry_logic") & (grid["entry"] == "CROSS")]
    for _, row in canon_rows.iterrows():
        real_canonical_t[row["sym"]] = row["gross_t"]

    placebo_by_block = {}
    for mean_block in (20, 100):
        placebo_t = []
        per_sym = {}
        for sym in DL.ALL:
            df, bpy, scale, cost, ne_cache = RG.base_frame(sym, "15min")
            ts = []
            for d in range(N_PLACEBO):
                sym_seed = sum(ord(c) for c in sym) * 1000
                rng = np.random.default_rng(sym_seed + d + mean_block * 7919)
                synth = synthetic_frame(df, rng, mean_block=mean_block)
                synth_scale = E.vol_target_scale(synth, bars_per_year=bpy)
                t = canonical_cell_t(synth, bpy, synth_scale, cost, {})
                if not np.isnan(t):
                    ts.append(t)
            placebo_t.extend(ts)
            per_sym[sym] = dict(n=len(ts), mean=float(np.mean(ts)), sd=float(np.std(ts)),
                                max_abs=float(np.max(np.abs(ts))), pos_count=int((np.array(ts) > 0).sum()))
            print(f"  [block={mean_block}] placebo {sym}: n={len(ts)} mean_t={np.mean(ts):+.3f} "
                  f"sd={np.std(ts):.3f} max|t|={np.max(np.abs(ts)):.3f} pos/neg="
                  f"{per_sym[sym]['pos_count']}/{len(ts)-per_sym[sym]['pos_count']}  "
                  f"(real canonical t = {real_canonical_t.get(sym):+.3f})", flush=True)
        placebo_t = np.array(placebo_t)
        placebo_by_block[mean_block] = dict(
            per_symbol=per_sym, all_t=placebo_t.tolist(),
            mean=float(placebo_t.mean()), sd=float(placebo_t.std()),
            max_abs=float(np.abs(placebo_t).max()),
            frac_abs_gt_2_5=float((np.abs(placebo_t) > 2.5).mean()),
            pos_count=int((placebo_t > 0).sum()), n=int(placebo_t.size))

    out = {
        "n_cells_real": n_cells,
        "real_t_mean": float(real_t.mean()), "real_t_median": float(np.median(real_t)),
        "real_max_abs_t": obs_max_abs,
        "iid_mc_draws": N_MC, "iid_max_mean": float(mc_max.mean()),
        "iid_max_p95": float(np.percentile(mc_max, 95)),
        "iid_p_value_of_observed_max": p_iid,
        "iid_expected_tail_count_each_side": float(n_cells * 0.0062),
        "observed_tail_pos_gt_2_5": obs_tail_pos, "observed_tail_neg_lt_minus_2_5": obs_tail_neg,
        "placebo_by_block_length": placebo_by_block,
        "real_canonical_t_by_symbol": {k: float(v) for k, v in real_canonical_t.items()},
    }
    (HERE / "placebo_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nSaved placebo_results.json ({time.time()-t0:.1f}s)")
    summary = {k: v for k, v in out.items() if k != "placebo_by_block_length"}
    summary["placebo_block20_mean"] = placebo_by_block[20]["mean"]
    summary["placebo_block20_frac_gt2.5"] = placebo_by_block[20]["frac_abs_gt_2_5"]
    summary["placebo_block100_mean"] = placebo_by_block[100]["mean"]
    summary["placebo_block100_frac_gt2.5"] = placebo_by_block[100]["frac_abs_gt_2_5"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
