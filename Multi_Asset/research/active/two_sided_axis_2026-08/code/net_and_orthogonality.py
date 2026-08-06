"""Part 3 — net after REAL carry (per leg, per direction), and L38.

For every (instrument, rule) the same signal is run under three sign policies:
  LONG_ONLY   sig.clip(lower=0)      what the book does today
  TWO_SIDED   sig                    the axis under test
  SHORT_ONLY  sig.clip(upper=0)

Carry is charged per bar as swap_long_t or swap_short_t depending on the sign
actually held, times the contractual triple-day multiplier. RT cost is charged
on |position change|.

L38: each policy is regressed on a vol-targeted buy-and-hold of the SAME
instrument. R^2 > 30% => it is beta timing, not a sleeve.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

import two_sided_battery as B

MAIN = Path("<HOME>/Desktop/Algo_claude")
PCACHE = MAIN / "data/ftmo_portfolio/cache"
TS = Path(os.environ.get(
    "TS_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/ts_cache",
))
OUT = Path(__file__).resolve().parent.parent
ANN = 252


def vol_target_bh(ret: pd.Series, target: float = 0.10, win: int = 60) -> pd.Series:
    rv = (ret.rolling(win).std() * np.sqrt(ANN)).shift(1).clip(lower=1e-4)
    return ret * (target / rv).clip(upper=5.0)


def l38(strat: pd.Series, bh: pd.Series) -> dict:
    d = pd.concat([strat, bh], axis=1).dropna()
    d.columns = ["s", "b"]
    if len(d) < 100 or d["b"].std() == 0:
        return dict(beta=np.nan, alpha_t=np.nan, r2=np.nan)
    m = sm.OLS(d["s"], sm.add_constant(d["b"])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 6})
    return dict(beta=round(float(m.params.iloc[1]), 4),
                alpha_bps=round(float(m.params.iloc[0]) * 1e4, 4),
                alpha_t=round(float(m.tvalues.iloc[0]), 3),
                r2=round(float(m.rsquared) * 100, 2))


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def main():
    R = pd.read_parquet(TS / "daily_logret_swapclock.parquet").loc["2013":]
    sL = pd.read_parquet(PCACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(PCACHE / "panel_swapS.parquet")
    mult = pd.read_parquet(PCACHE / "panel_mult.parquet")

    rows, l38rows = [], []
    for sym in B.INSTRUMENTS:
        ret = R[sym].dropna()
        px = np.exp(ret.cumsum())
        bh = vol_target_bh(ret)
        n = mult[sym].reindex(ret.index).ffill().fillna(1.0)
        swl = sL[sym].reindex(ret.index).ffill() / 1e4 * n
        sws = sS[sym].reindex(ret.index).ffill() / 1e4 * n
        rt = B.RT_BPS[sym] / 1e4

        for rname in B.RULES:
            sig = B.build_signal(rname, px, ret).reindex(ret.index).fillna(0.0)
            base = sig.shift(1).fillna(0.0)
            policies = {"LONG_ONLY": base.clip(lower=0),
                        "TWO_SIDED": base,
                        "SHORT_ONLY": base.clip(upper=0)}
            net_by_pol = {}
            for pname, pos in policies.items():
                gross = pos * ret
                carry = np.where(pos > 0, swl, np.where(pos < 0, sws, 0.0)) * pos.abs()
                tc = pos.diff().abs().fillna(pos.abs()) * rt
                net = gross + pd.Series(carry, index=ret.index) - tc
                net_by_pol[pname] = net
                rows.append(dict(
                    symbol=sym, rule=rname, policy=pname,
                    time_in_market=round(float((pos != 0).mean()), 4),
                    short_fraction_of_held=round(
                        float((pos < 0).sum() / max((pos != 0).sum(), 1)), 4),
                    gross_pct_yr=round(float(gross.mean()) * ANN * 100, 3),
                    carry_pct_yr=round(float(np.mean(carry)) * ANN * 100, 3),
                    tcost_pct_yr=round(-float(tc.mean()) * ANN * 100, 3),
                    net_pct_yr=round(float(net.mean()) * ANN * 100, 3),
                    net_sharpe=round(sharpe(net), 3),
                ))
                l38rows.append(dict(symbol=sym, rule=rname, policy=pname,
                                    **l38(net, bh)))
            d = net_by_pol["TWO_SIDED"] - net_by_pol["LONG_ONLY"]
            rows.append(dict(
                symbol=sym, rule=rname, policy="DELTA_two_sided_minus_long_only",
                net_pct_yr=round(float(d.mean()) * ANN * 100, 3),
                net_sharpe=round(sharpe(d), 3),
                delta_t_hac=round(B.hac_t(d.dropna().to_numpy()), 3),
            ))

    res = pd.DataFrame(rows)
    orth = pd.DataFrame(l38rows)
    res.to_csv(OUT / "net_by_sign_policy.csv", index=False)
    orth.to_csv(OUT / "l38_orthogonality.csv", index=False)

    dl = res[res["policy"] == "DELTA_two_sided_minus_long_only"]
    print("=== going two-sided vs staying long-only, net of REAL carry ===")
    print(dl[["symbol", "rule", "net_pct_yr", "delta_t_hac"]].to_string(index=False))
    print(f"\ntwo-sided beats long-only in {int((dl['net_pct_yr'] > 0).sum())}"
          f" / {len(dl)} cells; median delta {dl['net_pct_yr'].median():.2f} %/yr")

    print("\n=== carry bill actually paid, by policy (%/yr) ===")
    piv = res[res["policy"].isin(["LONG_ONLY", "TWO_SIDED", "SHORT_ONLY"])]
    print(piv.pivot_table(index=["symbol", "rule"], columns="policy",
                          values="carry_pct_yr").round(2).to_string())

    print("\n=== L38 on the 3 cells that passed the L58-adjusted gate ===")
    keep = [("XAUUSD", "R1_tsmom_blend_dz34"), ("XAUUSD", "R2_mom12_1_dz2pct"),
            ("USDJPY", "R2_mom12_1_dz2pct")]
    m = orth[orth.set_index(["symbol", "rule"]).index.isin(keep)]
    print(m.to_string(index=False))

    print("\n=== SHORT_ONLY: net and beta-loading, all cells ===")
    so = res[res["policy"] == "SHORT_ONLY"][["symbol", "rule", "gross_pct_yr",
                                             "carry_pct_yr", "net_pct_yr", "net_sharpe"]]
    print(so.to_string(index=False))


if __name__ == "__main__":
    main()
