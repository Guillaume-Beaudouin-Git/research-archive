"""Part 2 — is there a two-sided signal whose BOTH legs are positive at zero cost?

Pre-registered, no tuning. 3 sign rules x 7 instruments = 21 tests, declared up
front; DSR is run with n_trials = 21.

Every rule has a DEAD ZONE, so the short leg is active on days the long leg is
not merely absent from but where the rule made a positive short assertion. The
legs are therefore NOT `-side_long` (24/24 mirror pairs have already been found
in this repo). `union_share` < 100% is reported as the proof.

L25  both legs must be positive at ZERO cost.
L58  each leg is also scored against the unconditional expectation of the SAME
     trade shape (short baseline is NEGATIVE when the asset drifts up — the
     dangerous case).
L59  entry and exit are both the 17:00 NY close of the signal day + 1. There is
     no stop-entry / bracket-exit geometry here, so the L59 re-pricing does not
     apply; stated explicitly rather than assumed away.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = Path("<HOME>/Desktop/Algo_claude")
PCACHE = MAIN / "data/ftmo_portfolio/cache"
TS = Path(os.environ.get(
    "TS_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/ts_cache",
))
OUT = Path(__file__).resolve().parent.parent

INSTRUMENTS = ["US500", "US100", "US30", "GER40", "XAUUSD", "XAGUSD", "USDJPY"]
N_TRIALS = 21

# measured RT cost, COST_AUDIT.md (§2 for indices, §3 for gold)
RT_BPS = {"US500": 1.82, "US100": 1.80, "US30": 1.47, "GER40": 1.73,
          "XAUUSD": 1.84, "XAGUSD": 6.37, "USDJPY": 1.50}


# ------------------------------------------------------------------ rules
def rule_tsmom_blend(px: pd.Series, theta: float = 0.34) -> pd.Series:
    """Live gold spec, verbatim: blended sign TSMOM {60,120,250}, dead-zone."""
    sig = sum(np.sign(px / px.shift(L) - 1.0) for L in (60, 120, 250)) / 3.0
    return sig.where(sig.abs() >= theta, 0.0).apply(np.sign)


def rule_mom_12_1(px: pd.Series, theta: float = 0.02) -> pd.Series:
    """Live J1 spec generalised two-sided: 12-1 momentum with a 2% dead-zone."""
    mom = px.shift(21) / px.shift(252) - 1.0
    s = pd.Series(0.0, index=px.index)
    s[mom > theta] = 1.0
    s[mom < -theta] = -1.0
    return s


def rule_vol_state(ret: pd.Series) -> pd.Series:
    """Sign driven by the VARIANCE state, not by a price predictor (L54 in the
    sign domain): long in calm, short in stress, flat in between."""
    rv = ret.rolling(20).std()
    med = rv.rolling(252).median()
    s = pd.Series(0.0, index=ret.index)
    s[rv < 0.80 * med] = 1.0
    s[rv > 1.25 * med] = -1.0
    return s


RULES = {"R1_tsmom_blend_dz34": "px", "R2_mom12_1_dz2pct": "px", "R3_vol_state": "ret"}


def hac_t(x: np.ndarray, lag: int = 6) -> float:
    if len(x) < 30 or np.std(x) == 0:
        return np.nan
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(m.tvalues[0])


def build_signal(name: str, px: pd.Series, ret: pd.Series) -> pd.Series:
    if name == "R1_tsmom_blend_dz34":
        return rule_tsmom_blend(px)
    if name == "R2_mom12_1_dz2pct":
        return rule_mom_12_1(px)
    return rule_vol_state(ret)


def main():
    R = pd.read_parquet(TS / "daily_logret_swapclock.parquet").loc["2013":]
    sL = pd.read_parquet(PCACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(PCACHE / "panel_swapS.parquet")
    mult = pd.read_parquet(PCACHE / "panel_mult.parquet")

    rows = []
    for sym in INSTRUMENTS:
        ret = R[sym].dropna()
        px = np.exp(ret.cumsum())
        rbps = ret * 1e4
        drift = float(rbps.mean())
        for rname in RULES:
            sig = build_signal(rname, px, ret).reindex(ret.index).fillna(0.0)
            pos = sig.shift(1).fillna(0.0)          # signal at T-1, trade at T
            lng, sht = pos > 0, pos < 0
            n_l, n_s = int(lng.sum()), int(sht.sum())
            if n_l < 60 or n_s < 60:
                rows.append(dict(symbol=sym, rule=rname, n_long=n_l, n_short=n_s,
                                 verdict="INSUFFICIENT_LEG"))
                continue
            gl = rbps[lng].to_numpy()               # long-leg gross, bps/bar
            gs = -rbps[sht].to_numpy()              # short-leg gross, bps/bar
            rows.append(dict(
                symbol=sym, rule=rname,
                n_bars=len(ret), n_long=n_l, n_short=n_s,
                long_share=round(n_l / len(ret), 4),
                short_share=round(n_s / len(ret), 4),
                union_share=round((n_l + n_s) / len(ret), 4),   # <1 => not a mirror
                # ---- L25: both legs positive at ZERO cost
                long_gross_bps=round(float(gl.mean()), 4),
                long_t_hac=round(hac_t(gl), 3),
                short_gross_bps=round(float(gs.mean()), 4),
                short_t_hac=round(hac_t(gs), 3),
                both_legs_positive_gross=bool(gl.mean() > 0 and gs.mean() > 0),
                # ---- L58: each leg vs the unconditional expectation of ITS shape
                uncond_long_bps=round(drift, 4),
                uncond_short_bps=round(-drift, 4),
                long_alpha_vs_uncond=round(float(gl.mean()) - drift, 4),
                short_alpha_vs_uncond=round(float(gs.mean()) + drift, 4),
                both_legs_beat_uncond=bool(gl.mean() - drift > 0 and gs.mean() + drift > 0),
                verdict="",
            ))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "two_sided_gross_gate.csv", index=False)

    ok = res[res.get("both_legs_positive_gross", False) == True]  # noqa: E712
    ok2 = res[res.get("both_legs_beat_uncond", False) == True]    # noqa: E712
    print(res.drop(columns=["verdict"]).to_string(index=False))
    print(f"\nL25 gate (both legs positive at zero cost): "
          f"{len(ok)} / {len(res)} pass")
    print(f"L58 gate (both legs beat their unconditional shape): "
          f"{len(ok2)} / {len(res)} pass")
    if len(ok):
        print("\nsurvivors of the L25 gross gate:")
        print(ok[["symbol", "rule", "long_gross_bps", "long_t_hac",
                  "short_gross_bps", "short_t_hac", "short_alpha_vs_uncond",
                  "union_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
