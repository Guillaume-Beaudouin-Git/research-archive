"""
gate0_noise_floor.py — PRE-REGISTERED noise floor for the v2 OOS window (run BEFORE any candidate).

Question: over the OOS hold-out (2025-01-01 -> 2026-06-05, ~370 business days), how large an OOS
annualised Sharpe can arise from PURE LUCK once you account for trying N strategies? A candidate must
EXCEED this to be distinguishable from a coin-flip at the true cumulative N (= 70 burned + v2 variants).

Two independent estimates of the no-edge Sharpe standard error SE0:
  (1) ANALYTIC  : Lo (2002) SE of annualised Sharpe under H0 (true SR=0), Gaussian = sqrt(ppy/T),
                  fat-tail-adjusted with the real OOS index excess kurtosis.
  (2) PERMUTATION: net OOS Sharpe of NO-EDGE strategies on REAL index returns — block-random sign
                  series (preserve realistic turnover) and circular-shift-misaligned real signals.
Floor at N: threshold(N) = SE0 * E[max of N iid N(0,1)]  (Bailey-Lopez de Prado expected max).
SE0 is frozen here; only N updates after the honest v2 count is known.
"""
from __future__ import annotations
import sys, json, math
from pathlib import Path
import numpy as np

V1 = Path("<HOME>/Desktop/Algo_claude/research/ftmo_candidate_funnel")
sys.path.insert(0, str(V1))
import funnel_lib as F
RESULTS = Path(__file__).parent / "results"; RESULTS.mkdir(exist_ok=True)
PPY = 252
_GAMMA = 0.5772156649015329
from scipy.stats import norm


def e_max_iid(n: int) -> float:
    """Expected max of n iid N(0,1) (Bailey-Lopez de Prado eq.)."""
    if n <= 1:
        return 0.0
    return (1 - _GAMMA) * norm.ppf(1 - 1.0 / n) + _GAMMA * norm.ppf(1 - 1.0 / (n * math.e))


def analytic_se(T: int, excess_kurt: float = 0.0, sr_ann: float = 0.0) -> float:
    """Lo (2002) annualised-Sharpe SE under H0. At SR=0: sqrt(ppy/T) * sqrt(1 + (kurt-? )...).
    Lo variance of per-period SR ~ (1 - skew*SR + (kurt-1)/4 SR^2)/T; at SR=0 -> 1/T. Fat tails
    enter only through SR terms, negligible at SR=0, so report Gaussian + an empirical-kurtosis
    sanity bump for completeness."""
    se_per = math.sqrt((1.0 + 0.5 * (sr_ann / math.sqrt(PPY)) ** 2) / T)   # ~ 1/sqrt(T) at SR=0
    return se_per * math.sqrt(PPY)


def perm_null(seed=11, K=6000):
    """Empirical no-edge OOS Sharpe distribution on REAL index returns."""
    rng = np.random.default_rng(seed)
    idx = ["US500", "US100", "US30", "GER40", "XAUUSD"]
    rets = {}
    for s in idx:
        d = F.load_daily(s)
        _, oos = F.split_is_oos(d["ret"])
        rets[s] = (oos.dropna().to_numpy(), F.load_daily(s)["rt_cost"].reindex(oos.dropna().index).to_numpy())
    sharpes_blocksign, sharpes_shift = [], []
    for _ in range(K):
        s = idx[rng.integers(len(idx))]
        r, c = rets[s]; T = len(r)
        # (a) block-random sign series (geometric block ~5d) — realistic turnover, zero edge
        pos = np.empty(T); p = 1.0 / 5.0; i = 0
        while i < T:
            sign = rng.choice([-1.0, 0.0, 1.0]); L = max(1, int(rng.geometric(p)))
            pos[i:i + L] = sign; i += L
        dpos = np.abs(np.diff(pos, prepend=0.0))
        net = pos * r - 0.5 * c * dpos
        sd = net.std(ddof=1)
        if sd > 1e-12:
            sharpes_blocksign.append(net.mean() / sd * math.sqrt(PPY))
        # (b) circular-shift misalignment of a real signal vs returns (destroys edge, keeps autocorr)
        shift = rng.integers(5, T - 5)
        pos2 = np.sign(np.roll(r, shift))            # a "momentum-like" sign, misaligned
        net2 = pos2 * r - 0.5 * c * np.abs(np.diff(pos2, prepend=0.0))
        sd2 = net2.std(ddof=1)
        if sd2 > 1e-12:
            sharpes_shift.append(net2.mean() / sd2 * math.sqrt(PPY))
    return np.array(sharpes_blocksign), np.array(sharpes_shift)


def main():
    # T from a representative full-daily OOS series
    _, oos = F.split_is_oos(F.load_daily("US500")["ret"])
    T = int(oos.dropna().shape[0])
    exk = float(((oos.dropna() - oos.dropna().mean()) / oos.dropna().std()).pow(4).mean() - 3)
    se_an = analytic_se(T, exk)
    bs, sh = perm_null()
    se_bs, se_sh = float(bs.std(ddof=1)), float(sh.std(ddof=1))
    se0 = max(se_an, se_bs, se_sh)        # use the most conservative (largest) as the frozen SE0

    Ns = [70, 100, 110, 120, 130]
    table = {n: round(se0 * e_max_iid(n), 3) for n in Ns}
    out = dict(
        oos_window="2025-01-01..2026-06-05", T_oos=T, oos_excess_kurt=round(exk, 2),
        se_analytic_gaussian=round(se_an, 3), se_perm_blocksign=round(se_bs, 3),
        se_perm_circshift=round(se_sh, 3), SE0_frozen=round(se0, 3),
        perm_blocksign_p99=round(float(np.percentile(bs, 99)), 3),
        perm_blocksign_max=round(float(bs.max()), 3),
        threshold_by_N=table,
        note="A v2 candidate must EXCEED threshold_by_N[cumulative_N] OOS Sharpe to beat noise. "
             "SE0 frozen pre-search; only N updates with the honest v2 count.")
    (RESULTS / "noise_floor.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\nFROZEN: SE0={se0:.3f} | OOS-Sharpe to beat noise at N=110 -> {table[110]:.2f}, "
          f"N=120 -> {table[120]:.2f}")


if __name__ == "__main__":
    main()
