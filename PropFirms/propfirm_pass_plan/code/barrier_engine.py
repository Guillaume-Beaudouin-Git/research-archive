"""
barrier_engine.py — monotone, multi-barrier first-passage MC for propfirm challenges.
Committed runner (WS-A). Handles: 1/2-step, static vs trailing-EOD max-DD, optional hard
daily-loss floor, min trading days, optional consistency rule. Monotone in horizon T by
construction (sequential total-time budget). Self-validated vs the logistic closed form.

Barrier semantics
-----------------
- static DD     : breach if equity-in-phase <= -maxdd (from phase start).
- trailing-EOD  : floor = min(0, running_max_EOD_equity_in_phase - maxdd); breach if equity <= floor
                  (locks at breakeven once you're up maxdd — Topstep-style).
- daily floor   : 'hard' => a single day <= -daily breaches; 'soft'/None => no effect on pass.
- consistency   : a pass is valid only if best single-day profit <= frac * cumulative profit.
All returns are fractions of the initial balance; `daily` is the (already vol-targeted) strategy
series, scaled by leverage L at call time.
"""
from __future__ import annotations
import numpy as np


def block_bootstrap(daily: np.ndarray, npaths: int, T: int, block: float, rng) -> np.ndarray:
    n = len(daily); idx = np.empty((npaths, T), dtype=np.int64); p = 1.0 / max(1.0, block)
    idx[:, 0] = rng.integers(0, n, npaths)
    for t in range(1, T):
        cont = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(rng.random(npaths) < p, rng.integers(0, n, npaths), cont)
    return idx


def sim_challenge(daily, L, firm, T, npaths=8000, block=5, seed=0):
    """firm: dict with steps, targets(list), maxdd, daily, dd_type{'static','trailing'},
    daily_type{'hard','soft'}, min_days, consistency(frac or None). Returns p_pass (monotone in T)."""
    rng = np.random.default_rng(seed)
    R = daily[block_bootstrap(daily, npaths, T, block, rng)] * L
    steps = firm["steps"]; targets = firm["targets"]; maxdd = firm["maxdd"]; daily_lim = firm["daily"]
    dd_type = firm["dd_type"]; daily_type = firm.get("daily_type", "hard"); min_days = firm.get("min_days", 0)
    cons = firm.get("consistency", None)
    phase = np.zeros(npaths, dtype=np.int64)          # 0..steps-1
    eqp = np.zeros(npaths); peak = np.zeros(npaths); dip = np.zeros(npaths, dtype=np.int64)
    best_day = np.full(npaths, -1e9); done = np.zeros(npaths, bool); passed = np.zeros(npaths, bool)
    for t in range(T):
        r = R[:, t]; act = ~done
        # hard daily floor
        if daily_type == "hard" and daily_lim is not None:
            bd = act & (r <= -daily_lim); done |= bd; act = ~done
        eqp = np.where(act, eqp + r, eqp)
        dip = np.where(act, dip + 1, dip)
        best_day = np.where(act, np.maximum(best_day, r), best_day)
        # max-DD breach
        if dd_type == "trailing":
            peak = np.where(act, np.maximum(peak, eqp), peak)
            floor = np.minimum(0.0, peak - maxdd)
        else:
            floor = -maxdd
        bdd = act & (eqp <= floor); done |= bdd; act = ~done
        # target hit (respect min days)
        tgt = np.array([targets[min(p, len(targets) - 1)] for p in phase])
        ok_days = dip >= min_days
        hit = act & ok_days & (eqp >= tgt)
        if cons is not None:                          # consistency: best day <= frac * total profit
            hit = hit & (best_day <= cons * np.maximum(eqp, 1e-9))
        # advance phase or pass
        last = phase >= (steps - 1)
        adv = hit & (~last)
        phase = np.where(adv, phase + 1, phase)
        eqp = np.where(adv, 0.0, eqp); peak = np.where(adv, 0.0, peak)
        dip = np.where(adv, 0, dip); best_day = np.where(adv, -1e9, best_day)
        fin = hit & last; passed |= fin; done |= fin
    return float(passed.mean())


def best_p(daily, firm, T, Ls=(1.5, 2, 2.5, 3, 3.5, 4, 5), npaths=8000, seed=0):
    res = [(sim_challenge(daily, L, firm, T, npaths, seed=seed), L) for L in Ls]
    p, L = max(res); return p, L


def outer_ci(daily, firm, T, nout=24, Ls=(2, 2.5, 3, 3.5, 4), npaths=4000):
    vals = []
    base = np.random.default_rng(7)
    for o in range(nout):
        idx = block_bootstrap(daily, 1, len(daily), 20, np.random.default_rng(1000 + o))[0]
        vals.append(best_p(daily[idx], firm, T, Ls, npaths, seed=o)[0])
    return float(np.percentile(vals, 5)), float(np.percentile(vals, 50)), float(np.percentile(vals, 95))


# ── synthetic strategy-shape generator (Student-t, target ann-Sharpe / excess-kurt / skew) ──
def synth_shape(ann_sharpe, kurt=4.0, skew=-0.3, sigma_d=0.008, n=1200, seed=0):
    rng = np.random.default_rng(seed)
    nu = 6.0 / max(kurt, 0.1) + 4.0                  # t dof from target excess kurt (approx)
    x = rng.standard_t(df=nu, size=n)
    x = x / x.std()
    x = x + skew * (x**2 - 1) * 0.15                  # mild skew injection
    x = x / x.std()
    mu_d = ann_sharpe / np.sqrt(252) * sigma_d
    return mu_d + sigma_d * (x - x.mean())


if __name__ == "__main__":
    # SELF-CHECK: symmetric static one-phase vs logistic 1/(1+e^{-2 Sd n}); no daily floor; min_days 0.
    print("self-check: monotone engine vs logistic closed form (symmetric static, 1-step)", flush=True)
    for ann in (0.0, 0.8, 1.5):
        d = synth_shape(ann, kurt=0.01, skew=0.0, n=3000, seed=1)   # near-Gaussian
        sd = d.mean() / d.std(); n_units = 0.10 / d.std()           # barrier 10% in vol units (L=1)
        logit = 1.0 / (1.0 + np.exp(-2.0 * sd * n_units))
        firm = dict(steps=1, targets=[0.10], maxdd=0.10, daily=None, dd_type="static",
                    daily_type="soft", min_days=0, consistency=None)
        mc = sim_challenge(d, 1.0, firm, T=750, npaths=6000, seed=2)
        print(f"  annSharpe {ann:.1f}: logistic={logit:.3f}  MC(T=750)={mc:.3f}  diff={mc-logit:+.3f}", flush=True)
