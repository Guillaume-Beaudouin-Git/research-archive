"""B1 — End-of-day price pressure and its reversal, at the INDEX level.

Mechanism (Baltussen, Da & Soebhag, SSRN 5039009): institutional volume concentrates
in the closing auction; the resulting non-informative price pressure reverses.
Published magnitude (0.24 %/day) is a CROSS-SECTIONAL long-short on single US stocks.
At the index level the idiosyncratic pressure largely nets out, so the prior is
"much smaller, possibly zero".  This module measures it.

Design invariants
  - Exchange clock with its own DST (L56): US -> America/New_York, GER40 -> Europe/Berlin.
  - Gate at GROSS, cost_rt = 0.  If it does not exist at zero cost it does not exist.
  - L25 two-sided with DISJOINT legs: legs are dispatched by the sign of the signal,
    never by negating the other leg.
  - L58: every leg is compared to the UNCONDITIONAL expectation of the SAME trade form
    on the SAME window.  A leg that is merely above/below zero proves nothing.
  - L59: delay+1 on ENTRY and on EXIT.  Entry = OPEN of the bar one full bar after the
    signal bar; exit = OPEN of a later bar.  No barrier fills anywhere.
  - Block bootstrap (Politis-Romano, circular, L=5 sessions).  Never iid.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./cache")
RNG = np.random.default_rng(20260801)
NBOOT = 2000
BLOCK = 5

# instrument -> (tz, cash_open_mod, cash_close_mod, first_year_with_postclose_data)
SPEC = {
    "US500": ("America/New_York", 9 * 60 + 30, 16 * 60, 2018),
    "US100": ("America/New_York", 9 * 60 + 30, 16 * 60, 2018),
    "US30":  ("America/New_York", 9 * 60 + 30, 16 * 60, 2018),
    "GER40": ("Europe/Berlin",    9 * 60,      17 * 60 + 30, 2014),
}
SIG_WINS = (15, 30, 60)
THETAS = (0.5, 1.0, 1.5)


def session_table(name: str) -> pd.DataFrame:
    """One row per session, columns = (field, minute-of-day) for the mods we need."""
    tz, om, cl, y0 = SPEC[name]
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    mod = idx.hour * 60 + idx.minute
    day = idx.normalize().tz_localize(None)

    need = sorted({cl - 61, cl - 31, cl - 16, cl - 1, cl, cl + 1,
                   cl + 11, cl + 31, cl + 61, om, om + 1, om + 31})
    keep = np.isin(mod, need)
    sub = pd.DataFrame({
        "day": day[keep], "mod": mod[keep],
        "open": df["open"].values[keep], "close": df["close"].values[keep],
        "high": df["high"].values[keep], "low": df["low"].values[keep],
    })
    sub = sub.drop_duplicates(subset=["day", "mod"], keep="last")
    tbl = sub.pivot(index="day", columns="mod", values=["open", "close", "high", "low"])
    tbl = tbl[tbl.index.year >= y0]
    # weekdays only; sessions must have a genuine cash session
    tbl = tbl[tbl.index.dayofweek < 5]
    return tbl


def build_panel(name: str) -> pd.DataFrame:
    """Daily panel: signal returns over the last K minutes, and forward hold returns."""
    tz, om, cl, y0 = SPEC[name]
    t = session_table(name)
    c = t["close"]
    o = t["open"]
    hi, lo = t["high"], t["low"]

    p = pd.DataFrame(index=t.index)
    # ---- signals: return of the last K minutes of the cash session (bps) -------
    for K in SIG_WINS:
        anchor = {15: cl - 16, 30: cl - 31, 60: cl - 61}[K]
        p[f"sig{K}"] = (c[cl - 1] / c[anchor] - 1.0) * 1e4

    # ---- entry price: OPEN of the bar one full bar after the signal bar (L59) --
    p["entry"] = o[cl + 1]
    # ---- exits: OPEN of a later bar (L59 on the exit too) ---------------------
    p["x10"] = o[cl + 11]
    p["x30"] = o[cl + 31]
    p["x60"] = o[cl + 61]
    # ---- overnight: OPEN of the bar one full bar after the next cash open ------
    nxt = o[om + 1].shift(-1)
    p["xON"] = nxt.values
    # next-day first 30 min (post-open continuation of the reversal)
    p["nd_a"] = o[om + 1].shift(-1).values
    p["nd_b"] = o[om + 31].shift(-1).values

    for k, col in [("H10", "x10"), ("H30", "x30"), ("H60", "x60"), ("HON", "xON")]:
        p[f"r_{k}"] = (p[col] / p["entry"] - 1.0) * 1e4
    p["r_ND30"] = (p["nd_b"] / p["nd_a"] - 1.0) * 1e4

    # ---- hygiene: zero-range share in signal window and at entry bar (L60) ----
    p["zr_sig"] = (hi[cl - 1] == lo[cl - 1]).astype(float)
    p["zr_entry"] = (hi[cl + 1] == lo[cl + 1]).astype(float)
    # ---- halt-gap share of the hold return (L56 corollary) --------------------
    p["gap_entry"] = (o[cl + 1] / c[cl] - 1.0) * 1e4
    p["year"] = p.index.year
    return p


# --------------------------------------------------------------------------- #
def block_boot_mean(x: np.ndarray, nboot: int = NBOOT, L: int = BLOCK) -> tuple:
    """Circular block bootstrap of the mean. Returns (lo95, hi95, p_two_sided)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return (np.nan, np.nan, np.nan)
    nb = int(np.ceil(n / L))
    starts = RNG.integers(0, n, size=(nboot, nb))
    offs = np.arange(L)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(nboot, -1)[:, :n] % n
    means = x[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return (lo, hi, min(p, 1.0))


def block_boot_paired(a: np.ndarray, mask: np.ndarray, nboot: int = NBOOT, L: int = BLOCK):
    """Bootstrap of mean(a[mask]) - mean(a) : conditional minus UNCONDITIONAL (L58).

    Resamples the whole daily panel jointly so the conditioning is re-drawn with it.
    """
    a = np.asarray(a, float)
    m = np.asarray(mask, bool)
    n = len(a)
    if m.sum() < 20:
        return (np.nan, np.nan, np.nan)
    nb = int(np.ceil(n / L))
    starts = RNG.integers(0, n, size=(nboot, nb))
    offs = np.arange(L)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(nboot, -1)[:, :n] % n
    A = a[idx]
    M = m[idx]
    cond = np.where(M, A, np.nan)
    with np.errstate(invalid="ignore"):
        d = np.nanmean(cond, axis=1) - A.mean(axis=1)
    d = d[np.isfinite(d)]
    if len(d) < 100:
        return (np.nan, np.nan, np.nan)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2 * min((d <= 0).mean(), (d >= 0).mean())
    return (lo, hi, min(p, 1.0))


def hac_t(x: np.ndarray, lags: int = 6) -> float:
    x = np.asarray(x, float)
    n = len(x)
    if n < 20:
        return np.nan
    e = x - x.mean()
    g0 = (e @ e) / n
    s = g0
    for l in range(1, lags + 1):
        if l >= n:
            break
        gl = (e[l:] @ e[:-l]) / n
        s += 2 * (1 - l / (lags + 1)) * gl
    if s <= 0:
        return np.nan
    return x.mean() / np.sqrt(s / n)


def run_cell(p: pd.DataFrame, sig: str, hold: str, theta: float) -> dict | None:
    d = p[[sig, hold, "year"]].dropna()
    if len(d) < 100:
        return None
    s = d[sig].values
    r = d[hold].values
    # z-score of the closing-pressure signal, trailing 250 sessions, strictly past
    ser = pd.Series(s)
    mu = ser.shift(1).rolling(250, min_periods=100).mean()
    sd = ser.shift(1).rolling(250, min_periods=100).std()
    z = ((ser - mu) / sd).values
    ok = np.isfinite(z)
    z, r, s = z[ok], r[ok], s[ok]
    yr = d["year"].values[ok]
    if len(r) < 100:
        return None

    up = z > theta      # closed strong UP  -> fade = SHORT
    dn = z < -theta     # closed strong DOWN -> fade = LONG
    if up.sum() < 25 or dn.sum() < 25:
        return None

    uncond = r.mean()                       # L58 baseline: same trade form, all days
    rL = r[dn]                              # long leg pnl = +r
    rS = -r[up]                             # short leg pnl = -r  (disjoint pool)
    both = np.concatenate([rL, rS])

    # conditional minus unconditional, per leg, block-bootstrapped jointly
    dL = block_boot_paired(r, dn)
    dU = block_boot_paired(r, up)           # short leg edge = -(cond_up - uncond)
    bB = block_boot_mean(both)

    yrs = pd.Series(np.concatenate([rL, rS])).groupby(
        pd.Series(np.concatenate([yr[dn], yr[up]]))).mean()

    return dict(
        sig=sig, hold=hold, theta=theta, n_days=len(r),
        uncond_bps=uncond, uncond_t=hac_t(r),
        nL=int(dn.sum()), mL=rL.mean(), tL=hac_t(rL),
        nS=int(up.sum()), mS=rS.mean(), tS=hac_t(rS),
        n_both=len(both), m_both=both.mean(), t_both=hac_t(both),
        boot_both_lo=bB[0], boot_both_hi=bB[1], boot_both_p=bB[2],
        # L58: excess over the unconditional expectation of the same trade form
        exL=rL.mean() - uncond, exL_lo=dL[0], exL_hi=dL[1], exL_p=dL[2],
        exS=-(r[up].mean() - uncond), exS_lo=(-dU[1] if np.isfinite(dU[1]) else np.nan),
        exS_hi=(-dU[0] if np.isfinite(dU[0]) else np.nan), exS_p=dU[2],
        yrs_pos=int((yrs > 0).sum()), yrs_tot=int(len(yrs)),
    )


if __name__ == "__main__":
    holds = ["r_H10", "r_H30", "r_H60", "r_HON", "r_ND30"]
    rows = []
    hyg = []
    for name in SPEC:
        p = build_panel(name)
        cov = {h: int(p[h].notna().sum()) for h in holds}
        hyg.append(dict(instr=name, n_sessions=len(p),
                        zr_sig_pct=100 * p["zr_sig"].mean(),
                        zr_entry_pct=100 * p["zr_entry"].mean(),
                        gap_entry_abs_bps=p["gap_entry"].abs().mean(), **cov))
        for sw in SIG_WINS:
            for h in holds:
                for th in THETAS:
                    st = run_cell(p, f"sig{sw}", h, th)
                    if st:
                        rows.append(dict(instr=name, **st))
    H = pd.DataFrame(hyg)
    R = pd.DataFrame(rows)
    H.to_csv(CACHE / "b1_hygiene.csv", index=False)
    R.to_csv(CACHE / "b1_cells.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print("=== hygiene ===")
    print(H.round(2).to_string(index=False))
    print(f"\n=== {len(R)} B1 cells ===")
    print(R[["instr", "sig", "hold", "theta", "n_days", "uncond_bps", "uncond_t",
             "nL", "mL", "tL", "nS", "mS", "tS", "m_both", "t_both", "boot_both_p",
             "exL", "exL_p", "exS", "exS_p", "yrs_pos", "yrs_tot"]].round(3).to_string(index=False))
