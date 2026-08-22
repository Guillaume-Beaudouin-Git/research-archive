"""Falsifier: is the ATH conditioner anything more than a lagged inverse-volatility proxy?

Near the high is mechanically a low-realised-volatility state, and the overnight index
premium is compensation for variance. So the measured "near ATH earns less" may be the
vol-scaling identity restated rather than a state effect. This is the L38 orthogonality
test applied to a conditioner: regress the leg return on the B0 dummy AND trailing
realised vol, and report what survives.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "outputs"

sys.path.insert(0, str(OVERLAY))
import build_book as B  # noqa: E402
import conditioner as C  # noqa: E402


def trailing_vol(sym: str, dates: pd.DatetimeIndex, win: int) -> pd.Series:
    """Annualised trailing realised vol of daily index returns, strictly at T-1."""
    c = C.daily_closes()[sym].dropna()
    v = np.log(c).diff().rolling(win).std() * np.sqrt(252.0)
    return v.reindex(v.index.union(dates)).ffill().reindex(dates).shift(1)


def hac(y, X, lags: int = 6):
    r = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return r


def main() -> None:
    OUT.mkdir(exist_ok=True)
    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])
    cond = pd.read_parquet(CACHE / "conditioners.parquet")
    legs = pd.read_parquet(CACHE / "leg_returns.parquet").reindex(dates)
    book = B.run_book(M, WT=B.mono_signals(dates)[0], ON=B.mono_signals(dates)[1],
                      cfg=B.CFG_MONO)
    on = np.isin(dates.dayofweek, [0, 1])

    objects = {
        "leg_US100_net": legs["US100_net_bps"],
        "leg_GER40_net": legs["GER40_net_bps"],
        "book_active_bps": (book["ret"] * 1e4).where(book["ret"] != 0.0),
    }
    volsrc = {"leg_US100_net": "US100", "leg_GER40_net": "GER40",
              "book_active_bps": "US100"}

    res = {}
    print("=== ORTHOGONALITY: does B0 survive controlling for trailing vol? ===")
    print(f"{'object':20s} {'cond':4s} {'win':>4s} {'b_alone':>9s} {'t':>7s} "
          f"{'b_ctrl':>9s} {'t':>7s} {'c_vol':>9s} {'t':>7s} {'corr(B0,vol)':>13s}")
    for oname, y0 in objects.items():
        for cc in ("C1", "C2"):
            dd = cond[f"{cc}_{volsrc[oname]}"]
            for win in (20, 60):
                v = trailing_vol(volsrc[oname], dates, win)
                j = pd.concat([y0.rename("y"), dd.rename("dd"), v.rename("v")],
                              axis=1)[on].dropna()
                if len(j) < 200:
                    continue
                f = (j["dd"] <= 0.01).astype(float)
                r1 = hac(j["y"].to_numpy(), f.to_numpy())
                X = np.column_stack([f.to_numpy(), j["v"].to_numpy()])
                r2 = hac(j["y"].to_numpy(), X)
                key = f"{oname}|{cc}|{win}"
                res[key] = dict(
                    n=int(len(j)),
                    b_alone=float(r1.params[1]), t_alone=float(r1.tvalues[1]),
                    b_ctrl=float(r2.params[1]), t_ctrl=float(r2.tvalues[1]),
                    c_vol=float(r2.params[2]), t_vol=float(r2.tvalues[2]),
                    corr_B0_vol=float(np.corrcoef(f, j["v"])[0, 1]),
                    shrink=float(1.0 - r2.params[1] / r1.params[1]) if r1.params[1] != 0 else np.nan,
                )
                x = res[key]
                print(f"{oname:20s} {cc:4s} {win:4d} {x['b_alone']:9.2f} {x['t_alone']:7.2f} "
                      f"{x['b_ctrl']:9.2f} {x['t_ctrl']:7.2f} {x['c_vol']:9.1f} "
                      f"{x['t_vol']:7.2f} {x['corr_B0_vol']:13.3f}")

    # horse race: trailing-vol quartiles vs ATH buckets, same object
    print("\n=== HORSE RACE: trailing-vol quartile vs ATH bucket (US100 net leg, bps) ===")
    v = trailing_vol("US100", dates, 20)
    j = pd.concat([legs["US100_net_bps"].rename("y"), cond["C1_US100"].rename("dd"),
                   v.rename("v")], axis=1)[on].dropna()
    q = pd.qcut(j["v"], 4, labels=["Q1_lowvol", "Q2", "Q3", "Q4_highvol"])
    vt = j.groupby(q, observed=True)["y"].agg(["count", "mean"])
    vt["t_HAC"] = [float(hac(j["y"][q == k].to_numpy(),
                             np.zeros(int((q == k).sum()))).tvalues[0])
                   if False else float(sm.OLS(j["y"][q == k].to_numpy(),
                                              np.ones(int((q == k).sum()))).fit(
                       cov_type="HAC", cov_kwds={"maxlags": 6}).tvalues[0])
                   for k in vt.index]
    print(vt.to_string(float_format=lambda x: f"{x:.2f}"))
    bt = j.groupby(C.bucketize(j["dd"]), observed=True)["y"].agg(["count", "mean"])
    print(bt.to_string(float_format=lambda x: f"{x:.2f}"))
    spread_vol = float(vt["mean"].iloc[-1] - vt["mean"].iloc[0])
    spread_ath = float(bt["mean"].iloc[-1] - bt["mean"].iloc[0])
    print(f"\nspread high-minus-low: trailing-vol quartiles = {spread_vol:.2f} bps | "
          f"ATH buckets = {spread_ath:.2f} bps")
    res["horse_race"] = dict(spread_vol_quartile=spread_vol, spread_ath_bucket=spread_ath,
                             vol_table=vt.to_dict(), ath_table=bt.to_dict())

    # Sharpe per bucket: is near-ATH worse per unit of risk, or merely smaller?
    print("\n=== PER-BUCKET DAILY SHARPE (annualised, net) ===")
    sh = {}
    for oname, y0 in objects.items():
        dd = cond[f"C1_{volsrc[oname]}"]
        j2 = pd.concat([y0.rename("y"), dd.rename("dd")], axis=1)
        j2 = (j2[on] if oname != "book_active_bps" else j2).dropna()
        g = j2.groupby(C.bucketize(j2["dd"]), observed=True)["y"]
        sh[oname] = {k: float(x.mean() / x.std(ddof=1) * np.sqrt(252.0))
                     for k, x in g if len(x) >= 20}
    print(pd.DataFrame(sh).to_string(float_format=lambda x: f"{x:.3f}"))
    res["sharpe_by_bucket"] = sh

    (OUT / "controls.json").write_text(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()
