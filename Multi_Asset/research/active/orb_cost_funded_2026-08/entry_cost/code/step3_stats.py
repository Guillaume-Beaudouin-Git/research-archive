"""Volet A / étape 3 — statistiques, décompositions, série R re-pricée.

Devise commune (prereg §2) : points / bps / R, toujours avec N, t HAC lag-6 et IC
block-bootstrap stationnaire (Politis-Romano). iid interdit.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "out"

REGIMES = ["a_ideal", "b_stop_market", "b1_plus1tick", "c25_trav", "c50_trav",
           "c2_delay1_M1", "m5close_bardriven"]
MEAN_BLOCK = 20          # trades ; ~1 mois de trading ORB
N_BOOT = 10_000
CHUNK = 1_000            # reps par lot (contrôle de l'empreinte mémoire)
SEED = 20260812


def hac_t(x: np.ndarray, lags: int = 6) -> tuple[float, float, float]:
    """(moyenne, erreur-type HAC, t) pour la moyenne d'une série."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 10 or np.allclose(x.std(), 0.0):
        return float(x.mean()) if len(x) else np.nan, 0.0, np.nan
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.params[0]), float(m.bse[0]), float(m.tvalues[0])


def stationary_bootstrap_ci(x: np.ndarray, n_boot: int = N_BOOT,
                            block: int = MEAN_BLOCK,
                            seed: int = SEED, alpha: float = 0.05
                            ) -> tuple[float, float]:
    """IC percentile de la moyenne, block bootstrap CIRCULAIRE (Politis-Romano 1992).

    Blocs de longueur fixe `block`, tirés avec remise et enroulés circulairement :
    la dépendance sérielle intra-bloc est préservée. iid interdit (prereg §2).
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    off = np.arange(block, dtype=np.int32)
    means = np.empty(n_boot, dtype=float)
    done = 0
    while done < n_boot:
        b = min(CHUNK, n_boot - done)
        starts = rng.integers(0, n, size=(b, nb)).astype(np.int32)
        idx = (starts[:, :, None] + off[None, None, :]).reshape(b, nb * block) % n
        means[done:done + b] = x[idx[:, :n]].mean(axis=1)
        done += b
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def summarise(x: pd.Series, label: str, boot: bool = True) -> dict:
    v = x.dropna().values
    m, se, t = hac_t(v)
    lo, hi = stationary_bootstrap_ci(v) if boot else (np.nan, np.nan)
    return dict(serie=label, N=len(v), mean=m, se_hac6=se, t_hac6=t,
                ci95_lo=lo, ci95_hi=hi, std=float(np.std(v, ddof=1)) if len(v) > 1 else np.nan)


def main() -> None:
    d = pd.read_parquet(OUT / "step2_trades_enriched.parquet")
    n = len(d)
    print(f"N = {n}")

    # ---------------- 1. gap d'entrée -------------------------------------------
    gap_rows = []
    for lab, col in (("M1 (barre de déclenchement)", "open_beyond_pts"),
                     ("M5 (barre de déclenchement)", "m5_open_beyond_pts")):
        s = d[col]
        g = s[s > 1e-9]
        gap_rows.append(dict(
            granularite=lab, N=int(s.notna().sum()), n_gap=int((s > 1e-9).sum()),
            frac_gap=float((s > 1e-9).mean()),
            uncond_mean_pts=float(s.clip(lower=0).mean()),
            uncond_p50=float(s.clip(lower=0).quantile(.50)),
            uncond_p75=float(s.clip(lower=0).quantile(.75)),
            uncond_p90=float(s.clip(lower=0).quantile(.90)),
            uncond_p95=float(s.clip(lower=0).quantile(.95)),
            uncond_p99=float(s.clip(lower=0).quantile(.99)),
            uncond_max=float(s.max()),
            cond_mean_pts=float(g.mean()) if len(g) else np.nan,
            cond_p50=float(g.quantile(.50)) if len(g) else np.nan,
            cond_p75=float(g.quantile(.75)) if len(g) else np.nan,
            cond_p90=float(g.quantile(.90)) if len(g) else np.nan,
            cond_p95=float(g.quantile(.95)) if len(g) else np.nan,
            cond_max=float(g.max()) if len(g) else np.nan,
        ))
    gap = pd.DataFrame(gap_rows)
    gap.to_csv(OUT / "gap_distribution.csv", index=False)
    print("\n=== 1. GAP D'ENTRÉE ===")
    print(gap.to_string(index=False))

    # gap par année
    gy = d.groupby(d.index.year).agg(
        N=("open_beyond_pts", "size"),
        n_gap=("is_gap", "sum"),
        frac_gap=("is_gap", "mean"),
        mean_beyond_pts=("open_beyond_pts", lambda s: s.clip(lower=0).mean()),
        max_beyond_pts=("open_beyond_pts", "max"),
        median_bar_range_pts=("bar_range_pts", "median"),
        median_excursion_pts=("excursion_beyond_pts", "median"),
    )
    gy.index.name = "annee"
    gy.to_csv(OUT / "gap_by_year.csv")
    print("\n--- gap par année ---")
    print(gy.to_string())

    # ---------------- 2. coût par régime, 3 unités ------------------------------
    rows = []
    for r in REGIMES:
        for unit, col in (("points", f"cost_pts_{r}"), ("bps", f"cost_bps_{r}"),
                          ("R", f"cost_R_{r}")):
            s = summarise(d[col], f"{r}|{unit}", boot=(unit == "R"))
            s["regime"] = r
            s["unite"] = unit
            s["p50"] = float(d[col].quantile(.50))
            s["p90"] = float(d[col].quantile(.90))
            s["p99"] = float(d[col].quantile(.99))
            s["max"] = float(d[col].max())
            rows.append(s)
    cost = pd.DataFrame(rows)[
        ["regime", "unite", "N", "mean", "se_hac6", "t_hac6", "ci95_lo", "ci95_hi",
         "p50", "p90", "p99", "max"]]
    cost.to_csv(OUT / "entry_cost_by_regime.csv", index=False)
    print("\n=== 2. COÛT D'ENTRÉE PAR RÉGIME (3 unités) ===")
    print(cost.to_string(index=False))

    # ---------------- 3. R re-pricé ---------------------------------------------
    rows = []
    base = summarise(d["r_gross"], "r_gross (référence ledger)")
    base["regime"] = "reference"
    rows.append(base)
    for r in REGIMES:
        s = summarise(d[f"R_{r}"], f"R_{r}")
        s["regime"] = r
        rows.append(s)
        s2 = summarise(d[f"Radapt_{r}"], f"Radapt_{r}")
        s2["regime"] = r + " (sizing adaptatif)"
        rows.append(s2)
    rp = pd.DataFrame(rows)[["regime", "serie", "N", "mean", "se_hac6", "t_hac6",
                             "ci95_lo", "ci95_hi", "std"]]
    rp["sharpe_par_trade"] = rp["mean"] / rp["std"]
    rp.to_csv(OUT / "repriced_R_summary.csv", index=False)
    print("\n=== 3. R RE-PRICÉ ===")
    print(rp.to_string(index=False))

    # ---------------- 4. décompositions ------------------------------------------
    def breakdown(keys: pd.Series, name: str) -> pd.DataFrame:
        out = []
        for k, sub in d.groupby(keys):
            row = {name: k, "N": len(sub),
                   "frac_gap": float(sub["is_gap"].mean()),
                   "r_gross": float(sub["r_gross"].mean())}
            for r in ("b_stop_market", "b1_plus1tick", "c25_trav", "c50_trav"):
                row[f"cost_bps_{r}"] = float(sub[f"cost_bps_{r}"].mean())
                row[f"cost_R_{r}"] = float(sub[f"cost_R_{r}"].mean())
                row[f"R_{r}"] = float(sub[f"R_{r}"].mean())
            _, _, t = hac_t(sub["R_b1_plus1tick"].values)
            row["t_hac6_R_b1"] = t
            out.append(row)
        return pd.DataFrame(out)

    by_year = breakdown(d.index.year.to_series(index=d.index), "annee")
    by_year.to_csv(OUT / "breakdown_by_year.csv", index=False)
    print("\n=== 4a. PAR ANNÉE ===")
    print(by_year[["annee", "N", "frac_gap", "r_gross", "cost_bps_b_stop_market",
                   "cost_bps_c25_trav", "R_b1_plus1tick", "t_hac6_R_b1"]].to_string(index=False))

    by_reg = breakdown(d["regime_tag"], "regime_tag")
    by_reg.to_csv(OUT / "breakdown_by_regime_tag.csv", index=False)
    print("\n=== 4b. PAR REGIME_TAG ===")
    print(by_reg.to_string(index=False))

    by_out = breakdown(d["outcome"], "outcome")
    by_out.to_csv(OUT / "breakdown_by_outcome.csv", index=False)
    print("\n=== 4c. PAR OUTCOME ===")
    print(by_out.to_string(index=False))

    by_ttb = breakdown(pd.cut(d["ttb_5min"], [-1, 0, 1, 3, 8, 100],
                              labels=["ttb=0", "ttb=1", "ttb=2-3", "ttb=4-8", "ttb>8"]),
                       "ttb_bucket")
    by_ttb.to_csv(OUT / "breakdown_by_ttb.csv", index=False)
    print("\n=== 4d. PAR DÉLAI DE CASSURE ===")
    print(by_ttb[["ttb_bucket", "N", "frac_gap", "cost_bps_b_stop_market",
                  "cost_bps_c25_trav", "R_b1_plus1tick"]].to_string(index=False))

    # dérive temporelle du coût : régression du coût bps sur l'année
    yr = d.index.year.values.astype(float)
    for r in ("b_stop_market", "c25_trav"):
        y = d[f"cost_bps_{r}"].values
        m = sm.OLS(y, sm.add_constant(yr - yr.mean())).fit(
            cov_type="HAC", cov_kwds={"maxlags": 6})
        print(f"[dérive] cost_bps_{r} ~ annee : pente {m.params[1]:+.5f} bps/an "
              f"(t {m.tvalues[1]:+.2f})")

    # ---------------- 4bis. budget d'entrée : combien de ticks tuent l'ORB ? -----
    tick_R = 0.25 / d["risk_pts"]
    per_tick = float(tick_R.mean())
    be_ticks = float(d["r_gross"].mean() / per_tick)
    lad = []
    for k in range(0, 13):
        s = d["r_gross"] - k * tick_R
        m, se, t = hac_t(s.values)
        lo, hi = stationary_bootstrap_ci(s.values)
        lad.append(dict(ticks=k, points=k * 0.25,
                        cost_bps=float((k * 0.25 / d["level"] * 1e4).mean()),
                        cost_R=k * per_tick, N=len(s), mean_R=m, t_hac6=t,
                        ci95_lo=lo, ci95_hi=hi))
    lad = pd.DataFrame(lad)
    lad.to_csv(OUT / "entry_slippage_ladder.csv", index=False)
    print("\n=== 4bis. ÉCHELLE DE SLIPPAGE D'ENTRÉE ===")
    print(f"1 tick (0.25 pt) = {per_tick:.5f} R en moyenne ; "
          f"break-even du gross (+{d['r_gross'].mean():.4f} R) à {be_ticks:.2f} ticks "
          f"= {be_ticks*0.25:.2f} points d'entrée")
    print(lad.to_string(index=False))

    # ---------------- 5. série re-pricée pour le volet D -------------------------
    keep = ["direction", "level", "stop_eff", "exit_px", "outcome", "regime_tag",
            "ttb_5min", "risk_pts", "lev", "r_gross", "is_gap", "open_beyond_pts",
            "excursion_beyond_pts"]
    keep += [f"cost_pts_{r}" for r in REGIMES]
    keep += [f"cost_bps_{r}" for r in REGIMES]
    keep += [f"cost_R_{r}" for r in REGIMES]
    keep += [f"R_{r}" for r in REGIMES]
    keep += [f"Radapt_{r}" for r in REGIMES]
    ser = d[keep].copy()
    ser["R_entry_default"] = ser["R_b1_plus1tick"]     # défaut recommandé volet A
    ser.attrs = {}
    ser.to_parquet(OUT / "R_repriced_entry.parquet")
    print(f"\n[OUT] R_repriced_entry.parquet écrit — N={len(ser)}, "
          f"défaut R_entry_default = R_b1_plus1tick, mean {ser['R_entry_default'].mean():+.5f}")


if __name__ == "__main__":
    main()
