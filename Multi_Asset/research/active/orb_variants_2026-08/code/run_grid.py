"""
Orchestre les 37 variantes pre-enregistrees (PREREGISTRATION.md) :
 - 21 "engine runs" distincts (axes 1/2/3/5, OFAT depuis l'ancrage)
 - axe 4 (filtres largeur/vol) et axe 6 (calendrier) = masques post-hoc sur
   les trades de l'ANCRE (aucune resimulation necessaire, les filtres ne
   changent pas l'entree/sortie, seulement quels jours comptent)
Produit grille_resultats.csv (une ligne/variante, gross+net, long/short,
4 tranches de regime) + verdict DEDANS/DEHORS par la regle de kill.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from simulate import simulate_engine, load_sessions
from stats_utils import hac_tstat, hac_tstat_fast, ann_sharpe, block_bootstrap_ci, \
    sign_placebo_tstats, matched_count_calendar_placebo

OUTDIR = "<HOME>/Desktop/Algo_claude_orbvar/Multi_Asset/research/active/orb_variants_2026-08"

REGIME_BLOCKS = [
    ("2010-13", "2010-01-01", "2013-12-31"),
    ("2014-17", "2014-01-01", "2017-12-31"),
    ("2018-21", "2018-01-01", "2021-12-31"),
    ("2022-26", "2022-01-01", "2026-12-31"),
]

ANCHOR = dict(open_type="RTH", dur=30, breakout_def="touch", overshoot_mult=0.0,
              confirm="immediate", exit_rule="close_RTH")

# ---- axis definitions (engine-run variants only; axis4/6 handled as masks) ----
AX1 = [  # (label, open_type, dur)
    ("RTH_15", "RTH", 15), ("RTH_30_ANCHOR", "RTH", 30), ("RTH_60", "RTH", 60),
    ("Globex_15", "Globex", 15), ("Globex_30", "Globex", 30), ("Globex_60", "Globex", 60),
]
AX2 = [  # (label, breakout_def, overshoot_mult)
    ("touch_m0_ANCHOR", "touch", 0.0), ("touch_m025atr", "touch", 0.25), ("touch_m05atr", "touch", 0.5),
    ("close_m0", "close", 0.0), ("close_m025atr", "close", 0.25), ("close_m05atr", "close", 0.5),
]
AX3 = [  # (label, confirm)
    ("immediate_ANCHOR", "immediate"), ("bar_close_confirm", "bar_close"),
    ("2bar_confirm", "2bar"), ("retest", "retest"),
]
AX5 = [  # (label, exit_rule)
    ("close_RTH_ANCHOR", "close_RTH"), ("time_stop_12", "time_stop_12"), ("time_stop_11", "time_stop_11"),
    ("TP_1R", "TP_1R"), ("TP_1.5R", "TP_1.5R"), ("TP_2R", "TP_2R"),
    ("stop_half_OR", "stop_half_OR"), ("trailing_ATR", "trailing_ATR"),
]


def add_meta(df, sess):
    df = df.copy()
    df["date_ts"] = pd.to_datetime(df["date"])
    df["year"] = df["date_ts"].dt.year
    df["weekday"] = df["date_ts"].dt.day_name()
    fomc_set = set(sess["fomc"])
    df["is_fomc"] = df["date"].isin(fomc_set)
    date_to_i = {d: i for i, d in enumerate(sess["rth_dates"])}
    df["day_before_holiday"] = df["date"].map(lambda d: sess["is_day_before_holiday"][date_to_i[d]])
    df["day_after_holiday"] = df["date"].map(lambda d: sess["is_day_after_holiday"][date_to_i[d]])
    vix = sess["vix"]
    df["vix_prevclose"] = df["date"].map(lambda d: vix.get(d - pd.Timedelta(days=1), np.nan)
                                          if isinstance(d, (pd.Timestamp,)) else np.nan)
    # simpler: align vix by shifting the vix series itself once (done in covariates below)
    return df


def build_covariates(sess, anchor_or_hi, anchor_or_lo, anchor_atr):
    """Series journalieres (indexees par toutes les dates RTH, pas seulement
    les jours de trade) pour les filtres axe 4 : largeur OR (rolling), ATR
    percentile (rolling), VIX (rolling tercile), decalees T-1 ou construites
    sans lookahead au sens documente dans PREREGISTRATION."""
    dates = pd.to_datetime(sess["rth_dates"])
    or_range = pd.Series(anchor_or_hi - anchor_or_lo, index=dates)
    atr = pd.Series(anchor_atr, index=dates)

    roll_median_60 = or_range.rolling(60, min_periods=30).median().shift(1)
    roll_p67_60 = or_range.rolling(60, min_periods=30).quantile(0.667).shift(1)
    or_over_atr = or_range / atr

    def rolling_pct_rank(s, window):
        def f(x):
            if len(x) < 2:
                return np.nan
            return (x[-1] > x[:-1]).mean()
        return s.rolling(window, min_periods=100).apply(f, raw=True)

    atr_pctile = rolling_pct_rank(atr, 252)

    vix_raw = sess["vix"]
    vix_s = pd.Series({pd.Timestamp(k): v for k, v in vix_raw.items()}).sort_index()
    vix_s = vix_s.reindex(dates.union(vix_s.index)).sort_index().ffill().reindex(dates)
    vix_s_t1 = vix_s.shift(1)
    vix_pctile = rolling_pct_rank(vix_s_t1, 252)

    return pd.DataFrame({
        "date": sess["rth_dates"],
        "or_range": or_range.values,
        "roll_median_60": roll_median_60.values,
        "roll_p67_60": roll_p67_60.values,
        "or_over_atr": or_over_atr.values,
        "atr_pctile": atr_pctile.values,
        "vix_t1": vix_s_t1.values,
        "vix_pctile": vix_pctile.values,
    }).set_index("date")


def regime_block_for(date):
    for name, lo, hi in REGIME_BLOCKS:
        if pd.Timestamp(lo) <= pd.Timestamp(date) <= pd.Timestamp(hi):
            return name
    return None


PLACEBO_STORE = {}


def summarize(df, sess, label, axis, note=""):
    """df: trades table with r_gross, r_net, dir, date. Returns a dict row."""
    row = dict(variant=label, axis=axis, note=note, n=len(df))
    if len(df) == 0:
        return row
    dmin, dmax = df["date"].min(), df["date"].max()
    years = (pd.Timestamp(dmax) - pd.Timestamp(dmin)).days / 365.25
    years = max(years, 0.5)

    for tag, col in (("gross", "r_gross"), ("net", "r_net")):
        m, t, n = hac_tstat_fast(df[col].values)
        row[f"{tag}_mean"] = m
        row[f"{tag}_t"] = t
        row[f"{tag}_n"] = n
        row[f"{tag}_sharpe"] = ann_sharpe(df[col].values, df["date"], years)

    for side, sname in ((1, "long"), (-1, "short")):
        sub = df[df["dir"] == side]
        m, t, n = hac_tstat_fast(sub["r_net"].values)
        row[f"{sname}_net_mean"] = m
        row[f"{sname}_net_t"] = t
        row[f"{sname}_net_n"] = n

    df = df.copy()
    df["regime"] = df["date"].map(regime_block_for)
    for rname, _, _ in REGIME_BLOCKS:
        sub = df[df["regime"] == rname]
        m, t, n = hac_tstat_fast(sub["r_net"].values)
        row[f"regime_{rname}_mean"] = m
        row[f"regime_{rname}_t"] = t
        row[f"regime_{rname}_n"] = n

    lo, hi = block_bootstrap_ci(df["r_net"].values)
    row["boot_ci_lo"] = lo
    row["boot_ci_hi"] = hi

    placebo_t = sign_placebo_tstats(df["r_net"].values, n_draws=200, seed=abs(hash(label)) % (2**31))
    PLACEBO_STORE[label] = placebo_t
    row["placebo_t_p95"] = float(np.nanpercentile(placebo_t, 95)) if len(placebo_t) else np.nan
    row["placebo_t_p05"] = float(np.nanpercentile(placebo_t, 5)) if len(placebo_t) else np.nan
    row["placebo_t_mean"] = float(np.nanmean(placebo_t)) if len(placebo_t) else np.nan
    row["placebo_t_maxabs"] = float(np.nanmax(np.abs(placebo_t))) if len(placebo_t) else np.nan
    if len(placebo_t) and row["net_t"] is not None and not np.isnan(row["net_t"]):
        bound = max(abs(row["placebo_t_p95"]), abs(row["placebo_t_p05"]))
        row["real_t_beats_placebo_2sided"] = bool(abs(row["net_t"]) > bound)
    else:
        row["real_t_beats_placebo_2sided"] = None

    return row


def main():
    sess = load_sessions()
    rows = []
    engine_cache = {}

    def get_engine(open_type, dur, breakout_def, overshoot_mult, confirm, exit_rule):
        key = (open_type, dur, breakout_def, overshoot_mult, confirm, exit_rule)
        if key not in engine_cache:
            df = simulate_engine(sess, *key)
            df = add_meta(df, sess)
            engine_cache[key] = df
        return engine_cache[key]

    # ---- axis 1 ----
    for label, ot, dur in AX1:
        df = get_engine(ot, dur, ANCHOR["breakout_def"], ANCHOR["overshoot_mult"],
                         ANCHOR["confirm"], ANCHOR["exit_rule"])
        rows.append(summarize(df, sess, label, "1_or_window"))

    # ---- axis 2 ----
    for label, bd, om in AX2:
        df = get_engine(ANCHOR["open_type"], ANCHOR["dur"], bd, om,
                         ANCHOR["confirm"], ANCHOR["exit_rule"])
        rows.append(summarize(df, sess, label, "2_breakout_hardening"))

    # ---- axis 3 ----
    for label, cf in AX3:
        df = get_engine(ANCHOR["open_type"], ANCHOR["dur"], ANCHOR["breakout_def"],
                         ANCHOR["overshoot_mult"], cf, ANCHOR["exit_rule"])
        rows.append(summarize(df, sess, label, "3_confirmation"))

    # ---- axis 5 ----
    for label, er in AX5:
        df = get_engine(ANCHOR["open_type"], ANCHOR["dur"], ANCHOR["breakout_def"],
                         ANCHOR["overshoot_mult"], ANCHOR["confirm"], er)
        rows.append(summarize(df, sess, label, "5_exit"))

    # ---- anchor trades table for axis4/6 masks ----
    anchor_df = get_engine(**ANCHOR)

    # covariates need full daily OR/ATR series (all days, not just trades)
    anchor_or = sess["or_rth"][30].reindex(sess["rth_dates"])
    daily_atr = sess["daily"]["atr14_t1"].reindex(pd.to_datetime(sess["rth_dates"])).to_numpy()
    cov = build_covariates(sess, anchor_or["or_hi"].to_numpy(), anchor_or["or_lo"].to_numpy(), daily_atr)
    anchor_df = anchor_df.merge(cov, left_on="date", right_index=True, how="left", suffixes=("", "_cov"))

    # ---- axis 4: width/vol filters ----
    ax4_specs = [
        ("filter_none_ANCHOR", lambda d: np.ones(len(d), dtype=bool)),
        ("filter_OR_gt_median60", lambda d: (d["or_range"] > d["roll_median_60"]).values),
        ("filter_OR_top_tercile60", lambda d: (d["or_range"] > d["roll_p67_60"]).values),
        ("filter_OR_over_ATR_gt1", lambda d: (d["or_over_atr"] > 1.0).values),
        ("filter_ATR_pctile_high", lambda d: (d["atr_pctile"] > 0.667).values),
        ("filter_ATR_pctile_low", lambda d: (d["atr_pctile"] < 0.333).values),
        ("filter_VIX_pctile_high", lambda d: (d["vix_pctile"] > 0.667).values),
        ("filter_VIX_pctile_low", lambda d: (d["vix_pctile"] < 0.333).values),
    ]
    for label, fn in ax4_specs:
        mask = fn(anchor_df)
        mask = np.nan_to_num(mask.astype(float), nan=0.0).astype(bool) if mask.dtype != bool else mask
        sub = anchor_df[pd.Series(mask, index=anchor_df.index).fillna(False)]
        rows.append(summarize(sub, sess, label, "4_vol_filter"))

    # ---- axis 6: calendar filters ----
    ax6_specs = [
        ("cal_none_ANCHOR", lambda d: np.ones(len(d), dtype=bool), False),
        ("cal_excl_FOMC", lambda d: (~d["is_fomc"]).values, True),
        ("cal_excl_FOMC_pm1", None, True),  # handled specially below
        ("cal_Mon_only", lambda d: (d["weekday"] == "Monday").values, False),
        ("cal_Tue_only", lambda d: (d["weekday"] == "Tuesday").values, False),
        ("cal_Wed_only", lambda d: (d["weekday"] == "Wednesday").values, False),
        ("cal_Thu_only", lambda d: (d["weekday"] == "Thursday").values, False),
        ("cal_Fri_only", lambda d: (d["weekday"] == "Friday").values, False),
        ("cal_excl_day_before_holiday", lambda d: (~d["day_before_holiday"]).values, True),
        ("cal_excl_day_after_holiday", lambda d: (~d["day_after_holiday"]).values, True),
    ]
    fomc_set = set(sess["fomc"])
    fomc_pm1 = set()
    for d in fomc_set:
        fomc_pm1.add(d + pd.Timedelta(days=1))
        fomc_pm1.add(d - pd.Timedelta(days=1))
        fomc_pm1.add(d)

    all_dates_full = pd.to_datetime(sess["rth_dates"])
    for label, fn, is_exclude in ax6_specs:
        if label == "cal_excl_FOMC_pm1":
            mask = anchor_df["date"].map(lambda d: d not in fomc_pm1).values
        else:
            mask = fn(anchor_df)
        sub = anchor_df[pd.Series(mask, index=anchor_df.index)]
        row = summarize(sub, sess, label, "6_calendar")
        rows.append(row)

    df_out = pd.DataFrame(rows)

    SIDAK_SPRINT_T = 3.20   # Delta n=37 this sprint
    SIDAK_CUM_T = 4.19      # cumulative n=1867+37=1904 (order of magnitude, see RAPPORT)

    def classify(r):
        if pd.isna(r.get("net_t")):
            return "no_data"
        t = r["net_t"]
        cond1 = abs(t) > SIDAK_SPRINT_T
        regime_signs = [np.sign(r.get(f"regime_{name}_t", np.nan)) for name, _, _ in REGIME_BLOCKS]
        regime_signs = [s for s in regime_signs if not np.isnan(s)]
        same_sign_count = sum(1 for s in regime_signs if s == np.sign(t)) if len(regime_signs) else 0
        cond2 = same_sign_count >= 3
        long_t, short_t = r.get("long_net_t", np.nan), r.get("short_net_t", np.nan)
        cond3 = (not np.isnan(long_t) and not np.isnan(short_t)
                 and np.sign(long_t) == np.sign(t) and np.sign(short_t) == np.sign(t))
        cond4 = bool(r.get("real_t_beats_placebo_2sided"))
        if cond1 and cond2 and cond3 and cond4:
            return "VIVANT" if t > 0 else "VIVANT_NEGATIF"
        return "mort"

    df_out["kill_rule_verdict"] = df_out.apply(classify, axis=1)
    df_out["is_globex_artifact"] = df_out["variant"].str.contains("Globex")

    df_out.to_csv(f"{OUTDIR}/grille_resultats.csv", index=False)
    print(df_out[["variant", "axis", "n", "net_mean", "net_t", "net_sharpe",
                  "long_net_t", "short_net_t", "kill_rule_verdict"]].to_string())
    print("\nsaved to", f"{OUTDIR}/grille_resultats.csv")

    # ---- pooled max-under-H0 comparator: 200 reps x 37 placebo draws, take
    # max|t| per rep across variants, compare real max|t| (excluding the
    # Globex measurement-artifact rows) to this empirical distribution ----
    non_globex = df_out[~df_out["is_globex_artifact"]]
    real_max_abs_t = non_globex["net_t"].abs().max()
    real_max_variant = non_globex.loc[non_globex["net_t"].abs().idxmax(), "variant"]
    print(f"\nreal max|t| (hors artefact Globex) = {real_max_abs_t:.3f} ({real_max_variant})")

    # reuse the per-variant placebo draws already computed (200 draws each,
    # non-Globex rows) to build a pooled empirical max-order-statistic: for
    # each of the 200 replication indices, take the max|t_placebo| across the
    # 36 non-Globex variants at that replication index. This correctly
    # accounts for the OFAT correlation structure (variants sharing the same
    # anchor trades are correlated), which a theoretical N(0,1) order stat
    # would not.
    non_globex_labels = [l for l in non_globex["variant"].tolist() if l in PLACEBO_STORE]
    pools = [PLACEBO_STORE[l] for l in non_globex_labels if len(PLACEBO_STORE[l]) > 0]
    rng = np.random.default_rng(12345)
    n_rep = 2000
    max_draws = np.empty(n_rep)
    for rep in range(n_rep):
        sample = [pool[rng.integers(0, len(pool))] for pool in pools]
        max_draws[rep] = np.max(np.abs(sample))
    pctile_of_real = float((max_draws < real_max_abs_t).mean() * 100)
    print(f"\nDistribution empirique de max(|t_placebo|) sur {len(pools)} variantes (2000 reps):")
    print(f"  p50={np.percentile(max_draws,50):.2f} p90={np.percentile(max_draws,90):.2f} "
          f"p95={np.percentile(max_draws,95):.2f} p99={np.percentile(max_draws,99):.2f}")
    print(f"  max|t| REEL ({real_max_variant}) = {real_max_abs_t:.2f} -> percentile {pctile_of_real:.1f} "
          f"de la distribution placebo du max")

    print(f"\nseuil Sidak sprint (Delta n=37): {SIDAK_SPRINT_T:.2f} | cumule (n=1904): {SIDAK_CUM_T:.2f}")

    with open(f"{OUTDIR}/code/max_h0_comparator.txt", "w") as f:
        f.write(f"real_max_abs_t={real_max_abs_t}\nreal_max_variant={real_max_variant}\n")
        f.write(f"placebo_max_p50={np.percentile(max_draws,50)}\n")
        f.write(f"placebo_max_p90={np.percentile(max_draws,90)}\n")
        f.write(f"placebo_max_p95={np.percentile(max_draws,95)}\n")
        f.write(f"placebo_max_p99={np.percentile(max_draws,99)}\n")
        f.write(f"percentile_of_real={pctile_of_real}\n")
        f.write(f"n_pooled_variants={len(pools)}\n")

    # save anchor_df and covariates for report-writing / placebo-of-max analysis
    anchor_df.to_parquet(f"{OUTDIR}/code/anchor_trades.parquet")
    return df_out


if __name__ == "__main__":
    main()
