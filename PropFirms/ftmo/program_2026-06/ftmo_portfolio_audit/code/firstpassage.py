"""
firstpassage.py — INDEPENDENT FTMO 2-step first-passage Monte-Carlo (audit Gate 0).

Clean-room. Does NOT import engine/ftmo_first_passage.py.

FTMO 10k 2-step: P1 +10% target, P2 +5% target; both phases -10% static max-DD (from each
phase's start) + -5% daily-loss floor; min 4 trading days/phase; FTMO has NO time limit
(the "<=H months" is self-imposed). Additive cumulative returns (matches author convention).

Two engines:
  A) PRIMARY (correct): sequential two-phase to terminal, recording total trading days to
     finish BOTH phases. p(pass<=H) = P(pass both AND days1+days2 <= H). Monotone in H by
     construction -> resolves the report's monotonicity violation.
  B) REPLICATION: author's method = p1(<=H) * p2(<=H), two independent single-phase sims per
     horizon (independent RNG). Used to reproduce the non-monotonicity and to expose that the
     true bootstrap SE >> the delta-method binomial SE the report implies.

CIs: (i) delta-method binomial (what the report's engine returns); (ii) HONEST multi-seed
empirical SD across independent block-bootstrap replications; (iii) outer block-resample of
the data series (captures short-sample estimation uncertainty).
"""
from __future__ import annotations
import numpy as np

MAXDD, DAILY, P1, P2, MINDAYS = 0.10, 0.05, 0.10, 0.05, 4


def _block_idx(T, n, length, block, rng):
    p = 1.0 / max(1.0, block)
    restart = rng.random((n, length)) < p
    restart[:, 0] = True
    starts = rng.integers(0, T, size=(n, length))
    idx = np.empty((n, length), dtype=np.int64)
    idx[:, 0] = starts[:, 0]
    for t in range(1, length):
        idx[:, t] = np.where(restart[:, t], starts[:, t], (idx[:, t - 1] + 1) % T)
    return idx


def _phase(R, target, min_days=MINDAYS):
    """R: (n,cap) daily returns. Returns (passed bool[n], day_to_pass int[n], BIG if not)."""
    n, cap = R.shape
    BIG = cap + 10
    eq = np.cumsum(R, axis=1)
    cols = np.arange(cap)
    t_floor = np.where((R <= -DAILY).any(1), (R <= -DAILY).argmax(1), BIG)
    t_dd = np.where((eq <= -MAXDD).any(1), (eq <= -MAXDD).argmax(1), BIG)
    tgt_ok = (eq >= target) & (cols[None, :] >= (min_days - 1))
    t_tgt = np.where(tgt_ok.any(1), tgt_ok.argmax(1), BIG)
    passed = (t_tgt < t_floor) & (t_tgt < t_dd) & (t_tgt < BIG)
    days = np.where(passed, t_tgt + 1, BIG)
    return passed, days


def _draw(series, n, cap, rng):
    T = len(series)
    block = max(2.0, round(np.sqrt(T)))
    return series[_block_idx(T, n, cap, block, rng)]


def cdf_sequential(series, lev, horizons, n_paths=20000, cap=378, seed=0):
    """Correct monotone CDF: total days to clear BOTH phases (fresh draw per phase)."""
    rng = np.random.default_rng(seed)
    s = np.asarray(series, float) * lev
    p1_pass, d1 = _phase(_draw(s, n_paths, cap, rng), P1)
    p2_pass, d2 = _phase(_draw(s, n_paths, cap, rng), P2)
    both = p1_pass & p2_pass
    total = np.where(both, d1 + d2, 10 ** 9)
    out = {}
    for H in horizons:
        key = "terminal" if H is None else H
        out[key] = float((both & (total <= (cap * 2 if H is None else H))).mean())
    out["_terminal_passboth"] = float(both.mean())
    out["_median_days_passers"] = float(np.median(total[both])) if both.any() else None
    return out


def cdf_sequential_ci(series, lev, horizons, n_paths=20000, cap=378, n_seeds=10):
    """Multi-seed mean +/- empirical SD + 90% CI (honest MC uncertainty)."""
    keys = ["terminal" if H is None else H for H in horizons]
    vals = {k: [] for k in keys}
    for sd in range(n_seeds):
        r = cdf_sequential(series, lev, horizons, n_paths, cap, seed=1000 + sd)
        for k in keys:
            vals[k].append(r[k])
    res = {}
    for k in keys:
        a = np.array(vals[k])
        res[k] = {"mean": float(a.mean()), "sd": float(a.std(ddof=1)),
                  "ci90": [float(np.percentile(a, 5)), float(np.percentile(a, 95))],
                  "delta_se": float(np.sqrt(a.mean() * (1 - a.mean()) / n_paths))}
    return res


def author_perphase_product(series, lev, H, n_paths=20000, seed=42):
    """Replicate engine: p_combined = p1(<=H) * p2(<=H), independent single-phase sims."""
    s = np.asarray(series, float) * lev
    rng1 = np.random.default_rng(seed)
    rng2 = np.random.default_rng(seed + 1)
    p1, _ = _phase(_draw(s, n_paths, H, rng1), P1)
    p2, _ = _phase(_draw(s, n_paths, H, rng2), P2)
    p1m, p2m = p1.mean(), p2.mean()
    pc = p1m * p2m
    se1 = np.sqrt(p1m * (1 - p1m) / n_paths)
    se2 = np.sqrt(p2m * (1 - p2m) / n_paths)
    se = np.sqrt((p2m * se1) ** 2 + (p1m * se2) ** 2)
    return {"p_combined": float(pc), "p1": float(p1m), "p2": float(p2m),
            "delta_se": float(se)}


def author_multiseed(series, lev, H, n_paths=20000, n_seeds=20):
    """Author method across many INDEPENDENT seeds -> honest empirical SD vs delta_se."""
    ps = [author_perphase_product(series, lev, H, n_paths, seed=10 * k + 1)["p_combined"]
          for k in range(n_seeds)]
    a = np.array(ps)
    return {"mean": float(a.mean()), "empirical_sd": float(a.std(ddof=1)),
            "delta_se": float(np.sqrt(a.mean() * (1 - a.mean()) / n_paths)),
            "ci90": [float(np.percentile(a, 5)), float(np.percentile(a, 95))]}


def outer_resample_ci(series, lev, H, n_outer=40, n_paths=8000, cap=378, engine="seq"):
    """Outer block-resample of the DATA series -> captures short-sample estimation uncertainty."""
    s = np.asarray(series, float)
    T = len(s)
    block = max(2.0, round(np.sqrt(T)))
    rng = np.random.default_rng(7)
    out = []
    for b in range(n_outer):
        idx = _block_idx(T, 1, T, block, rng)[0]
        alt = s[idx]
        if engine == "seq":
            out.append(cdf_sequential(alt, lev, [H], n_paths, cap, seed=b)[H])
        else:
            out.append(author_perphase_product(alt, lev, H, n_paths, seed=b)["p_combined"])
    a = np.array(out)
    return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)),
            "ci90": [float(np.percentile(a, 5)), float(np.percentile(a, 95))]}
