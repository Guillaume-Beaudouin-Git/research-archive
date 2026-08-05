"""Track 2 — geometry vs economy, on block-bootstrapped paths of the DEPLOYED book.

Independent of the cleanroom funnel and of Pace: `Portfolio/admission/barrier.py`'s
phase walker is IMPORTED unchanged and driven by a thin campaign loop that enforces a
CAMPAIGN wall (barrier.py only knows per-phase horizons).

Two books on the SAME paired bootstrap draws:
  real    : the deployed MONO book's realised daily returns
  placebo : the same series DEMEANED -> mean exactly 0, identical variance, identical
            block-persistence. Any p(pass) it shows at horizon W is pure GEOMETRY.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))   # repo root of THIS worktree

from Portfolio.admission.barrier import BarrierConfig, _run_phase        # noqa: E402
from Portfolio.admission.marginal import stationary_bootstrap_indices    # noqa: E402

import wall_lib as W                                                     # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "outputs"
TAB = Path(__file__).resolve().parent.parent / "tables"
TAB.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

WALLS = [65, 91, 130, 182, 270, 360]
TD_PER_CAL = 252.0 / 365.0
GAP_P12, GAP_RETRY = 3, 2          # trading days between phases / after a death
MEAN_BLOCK = 10.0
N_PATHS = 20_000

CFG_MONO = dict(
    vm=14.0, on_w=0.6, target=0.10, orb_risk=0.0, breaker=0.30, taper=0.02,
    glide=0.5, ab_buf=0.02, ab_days=5, margin_cap=0.60, mrate=W.E.MRATE_SWING,
    quantize=True, brk_mode="daily", brk_needs_pos=True,
)   # no "pace"/"max_cal" -> pace multiplier identically 1


def build_book() -> pd.Series:
    """Constant-risk daily return series of the deployed MONO book (no barriers)."""
    E = W.E
    M, WT, ON = W.init()
    n = M["n"]
    bal, pos, avg = E.INIT, np.zeros(4), np.full(4, np.nan)
    rets = np.zeros(n)
    for i in range(n):
        px_day, bounds = M["days"][i]
        cuts = [0] + list(bounds) + [len(px_day)]
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if b <= a:
                continue
            tgt, _ = E._target_for_segment(
                s, i, M, WT, ON, CFG_MONO, bal, pos, avg, px_day[a], 0, CFG_MONO["vm"])
            if tgt is not None:
                bal = E._trade_to(pos, avg, bal, tgt, px_day[a], M["rt"])
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq = bal + E._mtm(pos, avg, px_day[-1])
        rets[i] = eq / E.INIT - 1.0
        pos = pos * (E.INIT / eq)
        bal = E.INIT
    return pd.Series(rets, index=pd.DatetimeIndex(M["dates"]), name="ret")


def campaign(path: np.ndarray, budget_td: int, cfg: BarrierConfig):
    """Retry funnel against a CAMPAIGN trading-day budget. Returns (funded, td, attempts)."""
    i, attempts = 0, 0
    while i < budget_td:
        attempts += 1
        o1, i1 = _run_phase(path, i, cfg.target_p1, cfg, cfg.min_days_p1, budget_td - i)
        if o1 == "pass":
            j = i1 + GAP_P12
            if j >= budget_td:
                return False, budget_td, attempts
            o2, i2 = _run_phase(path, j, cfg.target_p2, cfg, cfg.min_days_p2, budget_td - j)
            if o2 == "pass":
                return True, i2, attempts
            if o2 == "timeout":
                return False, budget_td, attempts
            i = i2 + GAP_RETRY
        else:
            if o1 == "timeout":
                return False, budget_td, attempts
            i = i1 + GAP_RETRY
    return False, budget_td, attempts


def sweep(r: np.ndarray, tag: str, seed: int = 7) -> pd.DataFrame:
    cfg = BarrierConfig()
    rng = np.random.default_rng(seed)
    max_td = int(round(max(WALLS) * TD_PER_CAL)) + 20
    reps = int(np.ceil(max_td / r.size)) + 1
    rows = {w: {"f": [], "t": [], "a": []} for w in WALLS}
    for _ in range(N_PATHS):
        idx = np.concatenate(
            [stationary_bootstrap_indices(r.size, MEAN_BLOCK, rng) for _ in range(reps)]
        )[:max_td]
        path = r[idx]
        for w in WALLS:                       # SAME path for every wall -> paired in W too
            f, t, a = campaign(path, int(round(w * TD_PER_CAL)), cfg)
            rows[w]["f"].append(f); rows[w]["t"].append(t); rows[w]["a"].append(a)
    out = []
    for w in WALLS:
        f = np.array(rows[w]["f"]); t = np.array(rows[w]["t"], float); a = np.array(rows[w]["a"])
        tf = t[f] / TD_PER_CAL
        out.append(dict(book=tag, wall=w, p_pass=float(f.mean()),
                        median_days=float(np.median(tf)) if tf.size else np.nan,
                        p90_days=float(np.percentile(tf, 90)) if tf.size else np.nan,
                        mean_days_cycle=float(np.mean(np.where(f, t / TD_PER_CAL, w))),
                        avg_attempts=float(a.mean()), n_paths=N_PATHS))
    return pd.DataFrame(out)


if __name__ == "__main__":
    book = build_book()
    r = book.to_numpy(float)
    ann = np.sqrt(252.0)
    print(f"MONO book: n={len(r)} {book.index[0].date()}->{book.index[-1].date()} "
          f"active={float((r!=0).mean()):.3f} annret={r.mean()*252:.4f} "
          f"annvol={r.std(ddof=1)*ann:.4f} SR={r.mean()*252/(r.std(ddof=1)*ann):.3f} "
          f"skew={pd.Series(r[r!=0]).skew():.3f}")
    book.to_frame().to_csv(OUT / "book_mono_daily.csv")     # small text, no blob
    real = sweep(r, "real", seed=7)
    plac = sweep(r - r.mean(), "placebo_zero_mean", seed=7)  # paired draws
    tab = pd.concat([real, plac], ignore_index=True)
    tab.to_csv(TAB / "track2_bootstrap.csv", index=False)
    print(tab.to_string(float_format=lambda x: f"{x:.4f}"))
