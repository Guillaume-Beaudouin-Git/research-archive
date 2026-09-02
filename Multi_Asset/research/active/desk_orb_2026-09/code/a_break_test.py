"""Question A — le two-sided 2022-2026 est-il robuste, ou un artefact de decoupage choisi
apres avoir vu le resultat ?

Trois volets, tous sur la jambe SHORT nette de cout (0.962 bps RT natif, levier par trade) :
  1. Decoupages roulants (rolling + expanding-from-end) : combien de temps le "SHORT positif
     et > LONG" tient avant de redevenir indiscernable du bruit a cette taille d'echantillon.
  2. Date de rupture ESTIMEE (Bai-Perron 1-break, recherche par minimisation de SSE), pas imposee,
     + p-value empirique par bootstrap par blocs (le max-sur-candidats gonfle le taux de faux
     positifs -- on ne compare pas a une loi asymptotique, on rebootstrap la procedure entiere).
  3. CUSUM (somme cumulee des residus standardises) pour une lecture visuelle/quantitative
     independante du meme phenomene.

Tout en R net-of-cost (0.962 bps), HAC lag-6 pour les t rapportes hors recherche de rupture,
walk-forward deja fait ailleurs (orb_cost_funded_2026-08 RESULTS.md: 2/5 folds positifs) --
non reproduit ici, cite.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from common import load_ledger, net_R, hac_t, SPREAD_NATIVE_BPS

OUT = __file__.replace("code/a_break_test.py", "out")


def main():
    df = load_ledger()
    df["r_net"] = net_R(df, SPREAD_NATIVE_BPS)
    short = df[df["direction"] == -1][["r_net"]].copy()
    long_ = df[df["direction"] == 1][["r_net"]].copy()
    short = short.sort_index()
    long_ = long_.sort_index()

    # ---------------------------------------------------------------
    # 1. Sunset test: expanding window from the END backward.
    #    At each candidate start date, compute HAC t-stat of SHORT leg
    #    on [start, 2026-05-29], report also SHORT - LONG (paired by date? no -- pooled means).
    # ---------------------------------------------------------------
    candidate_years = list(range(2010, 2027))
    rows = []
    for y0 in candidate_years:
        start = pd.Timestamp(f"{y0}-01-01")
        sub_s = short.loc[short.index >= start, "r_net"]
        sub_l = long_.loc[long_.index >= start, "r_net"]
        if len(sub_s) < 20:
            continue
        m_s, se_s, t_s, n_s = hac_t(sub_s)
        m_l, se_l, t_l, n_l = hac_t(sub_l)
        rows.append({
            "start_year": y0, "n_short": n_s, "mean_short": m_s, "t_short": t_s,
            "n_long": n_l, "mean_long": m_l, "t_long": t_l,
            "short_minus_long": m_s - m_l,
        })
    sunset = pd.DataFrame(rows)
    sunset.to_csv(f"{OUT}/a1_sunset_expanding_from_end.csv", index=False)
    print("=== A1: expanding window from 2026-05-29 backward (SHORT leg) ===")
    print(sunset.to_string(index=False))

    # Also: rolling FIXED-length windows (2-year, non-overlapping-ish, stepped 6 months)
    # to show the whole time path, not just the end-anchored one.
    step = pd.DateOffset(months=6)
    win = pd.DateOffset(years=2)
    rows2 = []
    t0 = short.index.min()
    tmax = short.index.max()
    cur = t0
    while cur + win <= tmax + pd.DateOffset(days=1):
        sub = short.loc[(short.index >= cur) & (short.index < cur + win), "r_net"]
        if len(sub) >= 20:
            m, se, t, n = hac_t(sub)
            rows2.append({"window_start": cur, "window_end": cur + win, "n": n, "mean": m, "t": t})
        cur += step
    rolling2y = pd.DataFrame(rows2)
    rolling2y.to_csv(f"{OUT}/a1b_rolling_2y_short_leg.csv", index=False)
    print("\n=== A1b: rolling 2-year window (6m step), SHORT leg t-stat over time ===")
    print(rolling2y.to_string(index=False))

    # ---------------------------------------------------------------
    # 2. Bai-Perron single-break search on SHORT leg (trimmed 10%-90%),
    #    statistic = |t| of a two-sample mean-shift test at each candidate split,
    #    argmax = estimated break date (NOT imposed). Null via block-bootstrap
    #    of the max-stat itself (block=20 trades, preserves local structure,
    #    destroys the true split location -> gives the search-adjusted p-value).
    # ---------------------------------------------------------------
    x = short["r_net"].values
    dates = short.index
    n = len(x)
    lo, hi = int(0.10 * n), int(0.90 * n)

    def max_break_stat(vec: np.ndarray) -> tuple[float, int]:
        best_t, best_k = 0.0, lo
        # precompute cumulative sums for speed
        csum = np.cumsum(vec)
        csum2 = np.cumsum(vec ** 2)
        total_n = len(vec)
        for k in range(lo, hi):
            n1, n2 = k, total_n - k
            s1, s2 = csum[k - 1], csum[-1] - csum[k - 1]
            ss1, ss2 = csum2[k - 1], csum2[-1] - csum2[k - 1]
            m1, m2 = s1 / n1, s2 / n2
            v1 = ss1 / n1 - m1 ** 2
            v2 = ss2 / n2 - m2 ** 2
            se = np.sqrt(v1 / n1 + v2 / n2)
            if se <= 0 or not np.isfinite(se):
                continue
            t = abs((m1 - m2) / se)
            if t > best_t:
                best_t, best_k = t, k
        return best_t, best_k

    obs_t, obs_k = max_break_stat(x)
    obs_date = dates[obs_k]
    print(f"\n=== A2: Bai-Perron 1-break search on SHORT leg (trim 10-90%) ===")
    print(f"estimated break date = {obs_date.date()}  (index {obs_k}/{n})  |t|={obs_t:.3f}")
    mean_before = x[:obs_k].mean()
    mean_after = x[obs_k:].mean()
    print(f"mean before = {mean_before:+.4f} (n={obs_k})  mean after = {mean_after:+.4f} (n={n-obs_k})")

    # block bootstrap null: shuffle blocks of the SHORT series (destroys the true
    # break location while preserving local autocorrelation/heteroskedasticity),
    # recompute max_break_stat each time.
    rng = np.random.default_rng(7)
    block = 20
    n_boot = 500
    n_blocks = int(np.ceil(n / block))
    null_stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = []
        for _ in range(n_blocks):
            s = rng.integers(0, n)
            idx.extend([(s + k) % n for k in range(block)])
        idx = idx[:n]
        shuffled = x[idx]
        t_b, _ = max_break_stat(shuffled)
        null_stats[b] = t_b
    p_value = (null_stats >= obs_t).mean()
    print(f"bootstrap null (block=20, n_boot={n_boot}): p50={np.percentile(null_stats,50):.3f} "
          f"p90={np.percentile(null_stats,90):.3f} p95={np.percentile(null_stats,95):.3f} "
          f"p99={np.percentile(null_stats,99):.3f}")
    print(f"search-adjusted p-value of observed break (|t|={obs_t:.3f}) = {p_value:.4f}")

    pd.DataFrame({
        "obs_break_date": [obs_date], "obs_t": [obs_t], "mean_before": [mean_before],
        "mean_after": [mean_after], "n_before": [obs_k], "n_after": [n - obs_k],
        "null_p50": [np.percentile(null_stats, 50)], "null_p90": [np.percentile(null_stats, 90)],
        "null_p95": [np.percentile(null_stats, 95)], "null_p99": [np.percentile(null_stats, 99)],
        "search_adjusted_pvalue": [p_value],
    }).to_csv(f"{OUT}/a2_bai_perron_break.csv", index=False)

    # ---------------------------------------------------------------
    # 3. CUSUM of standardized residuals (mean-zero-under-H0 not assumed;
    #    center on full-sample mean, standard CUSUM stability check).
    # ---------------------------------------------------------------
    mu = x.mean()
    sigma = x.std(ddof=1)
    w = (x - mu) / sigma
    cusum = np.cumsum(w) / np.sqrt(n)
    # Brownian bridge 5% critical boundary (approx, Ploberger-Kramer style): 0.948 * sqrt(n) scaling
    # here already normalized by sqrt(n); standard boundary ~1.36 for the sup|W(t)| Kolmogorov bound
    boundary = 1.36
    max_abs_cusum = np.max(np.abs(cusum))
    crosses = max_abs_cusum > boundary
    print(f"\n=== A3: CUSUM stability, SHORT leg ===")
    print(f"max|CUSUM| = {max_abs_cusum:.3f} vs 5% boundary {boundary} -> "
          f"{'INSTABLE (rupture detectee)' if crosses else 'STABLE (pas de rupture au seuil 5%)'}")
    idx_max = int(np.argmax(np.abs(cusum)))
    print(f"date du max |CUSUM| = {dates[idx_max].date()}")

    pd.DataFrame({"date": dates, "cusum": cusum}).to_csv(f"{OUT}/a3_cusum_short_leg.csv", index=False)


if __name__ == "__main__":
    main()
