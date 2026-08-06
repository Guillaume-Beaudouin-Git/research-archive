"""Part 4 — is the kill robust?

(a) the short-side carry credit is a REGIME, not a property: how much of the
    last 13 years did the short leg actually earn carry?
(b) flat vs short: the book's long-only sleeves are long-OR-FLAT, and flat pays
    zero swap. Quantify what the alternative to the expensive long side really is.
(c) block bootstrap (Politis-Romano, never iid) on delta = two-sided - long-only.
(d) 5-fold expanding walk-forward on the sign of that delta.
(e) the 2023-2026 high-rate era on its own — the strongest form of the objection.
(f) DSR on the best two-sided cell, rf = 0, n_trials = 21.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import two_sided_battery as B

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN))
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials  # noqa: E402

PCACHE = MAIN / "data/ftmo_portfolio/cache"
TS = Path(os.environ.get(
    "TS_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/ts_cache",
))
OUT = Path(__file__).resolve().parent.parent
ANN = 252
RNG = np.random.default_rng(20260806)


def block_boot(x: np.ndarray, n: int = 5000, block: int = 21) -> tuple:
    T = len(x)
    nb = int(np.ceil(T / block))
    starts = RNG.integers(0, T - block, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :T]
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), \
        float((means > 0).mean())


def main():
    R = pd.read_parquet(TS / "daily_logret_swapclock.parquet").loc["2013":]
    sL = pd.read_parquet(PCACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(PCACHE / "panel_swapS.parquet")
    mult = pd.read_parquet(PCACHE / "panel_mult.parquet")

    # ---------- (a) short-carry regime ---------------------------------
    rows = []
    for s in B.INSTRUMENTS:
        ss = sS[s].loc["2013":].dropna()
        ll = sL[s].loc["2013":].dropna()
        pos_days = ss > 0
        first = ss[pos_days].index.min() if pos_days.any() else None
        rows.append(dict(
            symbol=s,
            pct_days_short_carry_positive=round(float(pos_days.mean()) * 100, 1),
            first_day_short_carry_positive=str(first.date()) if first is not None else "never",
            mean_short_carry_pct_yr_2013_2021=round(
                float(ss.loc[:"2021"].mean()) * 365 / 100, 3),
            mean_short_carry_pct_yr_2023_2026=round(
                float(ss.loc["2023":].mean()) * 365 / 100, 3),
            mean_long_carry_pct_yr_full=round(float(ll.mean()) * 365 / 100, 3),
            flat_carry_pct_yr=0.0,
        ))
    reg = pd.DataFrame(rows)
    reg.to_csv(OUT / "short_carry_regime.csv", index=False)

    # ---------- (b)-(f) ------------------------------------------------
    boot, wf, era, dsr_rows = [], [], [], []
    for sym in B.INSTRUMENTS:
        ret = R[sym].dropna()
        px = np.exp(ret.cumsum())
        n = mult[sym].reindex(ret.index).ffill().fillna(1.0)
        swl = sL[sym].reindex(ret.index).ffill() / 1e4 * n
        sws = sS[sym].reindex(ret.index).ffill() / 1e4 * n
        rt = B.RT_BPS[sym] / 1e4

        for rname in B.RULES:
            sig = B.build_signal(rname, px, ret).reindex(ret.index).fillna(0.0)
            base = sig.shift(1).fillna(0.0)

            def net(pos):
                carry = np.where(pos > 0, swl, np.where(pos < 0, sws, 0.0)) * pos.abs()
                tc = pos.diff().abs().fillna(pos.abs()) * rt
                return pos * ret + pd.Series(carry, index=ret.index) - tc

            n_two, n_long = net(base), net(base.clip(lower=0))
            d = (n_two - n_long).dropna()

            lo, hi, ppos = block_boot(d.to_numpy(), block=21)
            boot.append(dict(symbol=sym, rule=rname,
                             delta_pct_yr=round(float(d.mean()) * ANN * 100, 3),
                             ci95_lo_pct_yr=round(lo * ANN * 100, 3),
                             ci95_hi_pct_yr=round(hi * ANN * 100, 3),
                             p_delta_positive=round(ppos, 4),
                             ci_excludes_zero=bool(hi < 0 or lo > 0)))

            # 5-fold expanding walk-forward on the OOS sign of the delta
            cuts = np.linspace(0.4, 1.0, 6)
            folds = []
            for i in range(5):
                a = int(len(d) * cuts[i])
                b = int(len(d) * cuts[i + 1])
                folds.append(float(d.iloc[a:b].mean()) > 0)
            wf.append(dict(symbol=sym, rule=rname,
                           wf_folds_positive=int(sum(folds)), wf_folds=5,
                           wf_pct=round(100 * sum(folds) / 5, 1)))

            de = d.loc["2023":]
            era.append(dict(symbol=sym, rule=rname,
                            delta_2013_2022_pct_yr=round(
                                float(d.loc[:"2022"].mean()) * ANN * 100, 3),
                            delta_2023_2026_pct_yr=round(float(de.mean()) * ANN * 100, 3),
                            n_days_2023_2026=len(de)))

            sr = float(n_two.mean() / n_two.std() * np.sqrt(ANN)) if n_two.std() > 0 else np.nan
            dsr_rows.append(dict(symbol=sym, rule=rname, two_sided_sharpe=round(sr, 3)))

    pd.DataFrame(boot).to_csv(OUT / "delta_block_bootstrap.csv", index=False)
    pd.DataFrame(wf).to_csv(OUT / "delta_walkforward.csv", index=False)
    pd.DataFrame(era).to_csv(OUT / "delta_by_rate_era.csv", index=False)

    # ---- DSR on the single best two-sided cell (rf = 0, n_trials = 21)
    dd = pd.DataFrame(dsr_rows).sort_values("two_sided_sharpe", ascending=False)
    best = dd.iloc[0]
    sym, rname = best["symbol"], best["rule"]
    ret = R[sym].dropna(); px = np.exp(ret.cumsum())
    n = mult[sym].reindex(ret.index).ffill().fillna(1.0)
    swl = sL[sym].reindex(ret.index).ffill() / 1e4 * n
    sws = sS[sym].reindex(ret.index).ffill() / 1e4 * n
    base = B.build_signal(rname, px, ret).reindex(ret.index).fillna(0.0).shift(1).fillna(0.0)
    carry = np.where(base > 0, swl, np.where(base < 0, sws, 0.0)) * base.abs()
    nb = base * ret + pd.Series(carry, index=ret.index) - \
        base.diff().abs().fillna(base.abs()) * B.RT_BPS[sym] / 1e4
    std_sr = estimate_std_sr_trials(dd["two_sided_sharpe"].to_numpy(float),
                                    periods_per_year=ANN, n_obs=len(nb.dropna()))
    out = deflated_sharpe_ratio(nb.dropna(), n_trials=B.N_TRIALS,
                                periods_per_year=ANN, rf=0.0,
                                std_sr_trials=std_sr)
    pd.DataFrame([{"symbol": sym, "rule": rname, **{k: v for k, v in out.items()
                                                    if np.isscalar(v)}}]).to_csv(
        OUT / "dsr_best_two_sided.csv", index=False)

    print("=== (a) short-side carry credit is a REGIME ===")
    print(reg.to_string(index=False))
    print("\n=== (c) block bootstrap on delta (two-sided - long-only) ===")
    bt = pd.DataFrame(boot)
    print(bt.to_string(index=False))
    print(f"\ncells whose 95% CI excludes zero: {int(bt['ci_excludes_zero'].sum())}/{len(bt)}"
          f" (all on the NEGATIVE side: {int((bt['ci95_hi_pct_yr'] < 0).sum())})")
    print("\n=== (d) walk-forward, 5 expanding folds ===")
    w = pd.DataFrame(wf)
    print(f"median folds positive: {w['wf_folds_positive'].median()}/5 ; "
          f"cells with >=3/5: {int((w['wf_folds_positive'] >= 3).sum())}/{len(w)}")
    print(w.to_string(index=False))
    print("\n=== (e) high-rate era 2023-2026 on its own ===")
    e = pd.DataFrame(era)
    print(e.to_string(index=False))
    print(f"\ncells where two-sided wins in 2023-2026: "
          f"{int((e['delta_2023_2026_pct_yr'] > 0).sum())}/{len(e)}")
    print("\n=== (f) DSR, best two-sided cell, rf=0, n_trials=21 ===")
    print(f"{sym} / {rname}  sharpe={best['two_sided_sharpe']}")
    print({k: (round(v, 4) if isinstance(v, float) else v)
           for k, v in out.items() if np.isscalar(v)})


if __name__ == "__main__":
    main()
