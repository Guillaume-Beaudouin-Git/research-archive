"""
FTMO two-stage Monte-Carlo over SYNTHETIC strategy profiles (characterisation study).
Clean re-implementation of the canonical rules (cross-checked vs Portfolio/risk/
propfirm_canonical.py): account 10k; daily barrier 500 mobile (midnight balance - 500,
intraday); static floor 9,000; challenge target 11,000 within 63 trading days, >=4 days.
The daily barrier is checked against the INTRADAY low (it is an intraday constraint).
"""
from __future__ import annotations
import numpy as np

INIT, DAILY, FLOOR, TARGET = 10_000.0, 500.0, 9_000.0, 11_000.0


def _innov(rng, n, nu):
    if nu is None or not np.isfinite(nu):
        return rng.standard_normal(n)
    return rng.standard_t(nu, size=n) / np.sqrt(nu / (nu - 2.0))  # unit variance


def _daily_params(sr_ann, sigma_ann, presence):
    p = max(float(presence), 1e-9)
    sd = sigma_ann / np.sqrt(252.0)        # overall daily std
    mu_d = sr_ann * sigma_ann / 252.0      # overall daily mean
    return p, mu_d / p, sd / np.sqrt(p)    # presence, active-day mean, active-day std


def simulate(sr_ann, sigma_ann, presence=1.0, nu=np.inf, m=1.5, stage="funded",
             extract=True, N=20000, seed=0, T=None, min_days=4):
    """Returns dict of metrics for the given profile. stage in {challenge, funded}."""
    if T is None:
        T = 63 if stage == "challenge" else 252
    rng = np.random.default_rng(seed)
    p, ma, sa = _daily_params(sr_ann, sigma_ann, presence)
    bal = np.full(N, INIT); alive = np.ones(N, bool); passed = np.zeros(N, bool)
    extracted = np.zeros(N); peak = np.full(N, INIT); maxdd = np.zeros(N)
    bust_daily = np.zeros(N, bool); bust_floor = np.zeros(N, bool)
    for d in range(T):
        trade = alive & (~passed)
        act = (rng.random(N) < p) & trade
        z = _innov(rng, N, nu); w = np.abs(rng.standard_normal(N))
        r = np.where(act, ma + sa * z, 0.0)
        L = np.where(act, np.minimum(0.0, r) - sa * m * w, 0.0)   # intraday low return vs midnight
        mid = bal
        low = mid * (1.0 + L)
        daily_breach = (mid - low) > DAILY
        floor_breach = low < FLOOR
        bust = trade & (daily_breach | floor_breach)
        bust_daily |= bust & daily_breach
        bust_floor |= bust & floor_breach & (~daily_breach)
        alive = alive & ~bust
        newbal = mid * (1.0 + r)
        bal = np.where(alive & trade, newbal, bal)
        peak = np.maximum(peak, bal)
        maxdd = np.maximum(maxdd, (peak - bal) / peak)
        if stage == "challenge":
            passed |= alive & (~passed) & (bal >= TARGET) & (d + 1 >= min_days)
        elif extract:
            ex = np.where(alive & (bal > INIT), bal - INIT, 0.0)
            extracted += ex
            bal = np.where(alive & (bal > INIT), INIT, bal)
    if stage == "challenge":
        return dict(p_pass=float(passed.mean()))
    nb = max(int((~alive).sum()), 1)
    return dict(p_survive=float(alive.mean()),
                E_extracted=float(extracted.mean()),
                cum_maxdd=float(np.median(maxdd)),
                bust_daily_share=float(bust_daily.sum() / nb),
                bust_floor_share=float(bust_floor.sum() / nb))


def simulate_book_plus(sr_c, sig_c, p_c, rho_tail, sr_b=0.9, sig_b=0.09,
                       nu=5.0, m=1.5, N=20000, seed=0, T=252):
    """Funded survival of (book + candidate). Book calibrated to rase the floor; the
    candidate's worst days co-occur with the book's with probability rho_tail."""
    rng = np.random.default_rng(seed)
    pb, mab, sab = _daily_params(sr_b, sig_b, 1.0)
    pc, mac, sac = _daily_params(sr_c, sig_c, p_c)
    bal = np.full(N, INIT); alive = np.ones(N, bool); extracted = np.zeros(N)
    for d in range(T):
        zb = _innov(rng, N, nu); rb = mab + sab * zb
        actc = rng.random(N) < pc
        zc = _innov(rng, N, nu)
        # tail co-occurrence: with prob rho_tail, force candidate's sign to match the book's bad day
        co = (rng.random(N) < rho_tail) & (rb < 0)
        zc = np.where(co, -np.abs(zc), zc)
        rc = np.where(actc, mac + sac * zc, 0.0)
        r = 0.5 * rb + 0.5 * rc                     # equal-risk-ish blend
        wb = np.abs(rng.standard_normal(N)); wc = np.abs(rng.standard_normal(N))
        Lb = np.minimum(0.0, rb) - sab * m * wb
        Lc = np.where(actc, np.minimum(0.0, rc) - sac * m * wc, 0.0)
        L = 0.5 * Lb + 0.5 * Lc
        mid = bal; low = mid * (1.0 + L)
        bust = alive & (((mid - low) > DAILY) | (low < FLOOR))
        alive = alive & ~bust
        bal = np.where(alive, mid * (1.0 + r), bal)
        ex = np.where(alive & (bal > INIT), bal - INIT, 0.0)
        extracted += ex
        bal = np.where(alive & (bal > INIT), INIT, bal)
    return dict(p_survive=float(alive.mean()), E_extracted=float(extracted.mean()))


if __name__ == "__main__":
    # cross-check vs the book's stated behaviour
    print("=== cross-check: challenge p_pass needs HIGH vol (speed); funded busts ~all daily ===")
    for sig in (0.05, 0.10, 0.20, 0.35, 0.50):
        c = simulate(1.0, sig, stage="challenge", seed=1)
        print(f"  challenge SR1.0 vol{int(sig*100):>2}% : p_pass {c['p_pass']:.2f}")
    f = simulate(1.0, 0.10, stage="funded", seed=1)
    print(f"  funded SR1.0 vol10% : p_survive {f['p_survive']:.2f} | bust daily {f['bust_daily_share']:.0%} / floor {f['bust_floor_share']:.0%} | E[extr] ${f['E_extracted']:.0f}")
