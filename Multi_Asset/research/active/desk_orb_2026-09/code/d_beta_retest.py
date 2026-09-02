"""Question D — re-tester (pas reprendre) l'objection 'long-only sur indice haussier = beta'.

regime_diagnostic_2026-09 a deja teste orb (ALL, combine) ~ bh_us100 en ANNUEL (n=14, beta=-0.014,
R2=0.000). Ce module refait le test INDEPENDAMMENT, restreint a la jambe qui porte l'objection
(LONG SEULE, puisque c'est elle qui serait "juste du beta deguise" si on choisit la cellule
long-only de la matrice de decision), a DEUX frequences :
  (i) annuel (reproduction methodologique, n=14, pour comparer directement au chiffre cite)
  (ii) quotidien vol-targete (L38 : regresser sur un buy-and-hold VOL-TARGETE, pas brut) --
       plus de puissance (n~2000+ jours RTH), sur la jambe LONG seule et sur la jambe SHORT
       seule pour symetrie.

Benchmark BH : rendement RTH open->close du NQ (databento, 1min), meme session que l'ORB.
Vol-targeting : realized vol rolling 20j, cible = vol moyenne de la serie (L38 convention).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import load_ledger, net_R, SPREAD_NATIVE_BPS

NQ_PATH = "<HOME>/Desktop/Algo_claude/data/raw/NQ_1min_databento_2010-2026.parquet"
OUT = __file__.replace("code/d_beta_retest.py", "out")


def build_daily_bh():
    df = pd.read_parquet(NQ_PATH, columns=["open", "close", "is_rth"])
    rth = df[df["is_rth"]].copy()
    rth["date"] = rth.index.tz_convert("America/New_York").date
    daily = rth.groupby("date").agg(open=("open", "first"), close=("close", "last"))
    daily.index = pd.to_datetime(daily.index)
    daily["ret"] = daily["close"] / daily["open"] - 1.0
    return daily


def hac_beta(y: np.ndarray, x: np.ndarray, lags: int = 6):
    X = sm.add_constant(x)
    model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    alpha, beta = model.params[0], model.params[1]
    t_alpha, t_beta = model.tvalues[0], model.tvalues[1]
    r2 = model.rsquared
    return alpha, t_alpha, beta, t_beta, r2, model.nobs


def main():
    ledger = load_ledger()
    ledger["r_net"] = net_R(ledger, SPREAD_NATIVE_BPS)
    daily_bh = build_daily_bh()

    # -----------------------------------------------------------------
    # (i) ANNUAL reproduction, LONG-only and SHORT-only, vs raw bh_us100 annual return
    #     (same construction as regime_diagnostic_2026-09 sec 3.1 point 2, but per-leg)
    # -----------------------------------------------------------------
    ledger["year"] = ledger.index.year
    daily_bh["year"] = daily_bh.index.year
    bh_annual = daily_bh.groupby("year")["ret"].apply(lambda r: (1 + r).prod() - 1)

    rows = []
    for leg_name, mask in [("LONG", ledger["direction"] == 1), ("SHORT", ledger["direction"] == -1),
                            ("ALL", slice(None))]:
        sub = ledger[mask] if leg_name != "ALL" else ledger
        annual_orb = sub.groupby("year")["r_net"].sum()
        common_years = annual_orb.index.intersection(bh_annual.index)
        y = annual_orb.loc[common_years].values
        x = bh_annual.loc[common_years].values
        alpha, t_a, beta, t_b, r2, n = hac_beta(y, x)
        rows.append({"leg": leg_name, "freq": "annual", "n": n, "alpha": alpha, "t_alpha": t_a,
                     "beta": beta, "t_beta": t_b, "r2": r2})
        print(f"[annual] {leg_name:5s} n={n:.0f} alpha={alpha:+.4f}(t={t_a:+.2f}) "
              f"beta={beta:+.4f}(t={t_b:+.2f}) R2={r2:.4f}")

    # -----------------------------------------------------------------
    # (ii) DAILY, vol-targeted BH, LONG-only and SHORT-only, full sample + 2022-2026 subsample
    # -----------------------------------------------------------------
    realized_vol = daily_bh["ret"].rolling(20, min_periods=20).std()
    target_vol = daily_bh["ret"].std()  # full-sample vol as the target (L38 convention: comparable scale)
    daily_bh["ret_vt"] = daily_bh["ret"] / realized_vol.replace(0, np.nan) * target_vol
    daily_bh["ret_vt"] = daily_bh["ret_vt"].clip(-daily_bh["ret_vt"].abs().quantile(0.995),
                                                   daily_bh["ret_vt"].abs().quantile(0.995))

    for window_name, sub_ledger in [("full", ledger), ("2022_2026", ledger.loc["2022-01-01":])]:
        for leg_name, mask in [("LONG", sub_ledger["direction"] == 1),
                                ("SHORT", sub_ledger["direction"] == -1)]:
            sub = sub_ledger[mask]
            merged = sub[["r_net"]].join(daily_bh[["ret_vt"]], how="inner").dropna()
            if len(merged) < 30:
                continue
            alpha, t_a, beta, t_b, r2, n = hac_beta(
                merged["r_net"].values, merged["ret_vt"].values
            )
            rows.append({"leg": leg_name, "freq": f"daily_{window_name}", "n": n,
                         "alpha": alpha, "t_alpha": t_a, "beta": beta, "t_beta": t_b, "r2": r2})
            print(f"[daily/{window_name:9s}] {leg_name:5s} n={n:.0f} alpha={alpha:+.4f}(t={t_a:+.2f}) "
                  f"beta={beta:+.4f}(t={t_b:+.2f}) R2={r2:.4f}")

    pd.DataFrame(rows).to_csv(f"{OUT}/d_beta_orthogonality.csv", index=False)


if __name__ == "__main__":
    main()
