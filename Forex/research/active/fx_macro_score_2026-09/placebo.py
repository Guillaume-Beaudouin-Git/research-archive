"""
Matched placebo (mandatory per mission rules + L58/artefacts-construction 2026-08-21):
a slow exponential-decay kernel (half-life 90d) makes the resulting score HIGHLY
autocorrelated even if the underlying xi values are pure noise. That autocorrelation
alone, combined with any drift/trend in a specific FX pair's 2007-2025 sample, can
manufacture a significant-looking HAC t-stat with NOTHING to do with the actual
macro surprise content.

Placebo design: keep the EXACT same event calendar (dates, currencies, categories --
i.e. keep the decay kernel's autocorrelation structure identical) but permute the
xi (z-score) VALUES across events within each currency, breaking the true link
between the surprise's sign/magnitude and what actually happened economically.
Re-run the identical scoring + fixed-half-life pipeline N times; compare the
empirical (real-data) IC to this null distribution.
"""
import numpy as np
import pandas as pd
from build_scores import load_events, CCYS
from analysis import PAIRS, CATS_DEFAULT, hac_tstat, CACHE

N_PLACEBO = 200
HALF_LIFE = 90  # the value the walk-forward selected on real data for the flagged case
HORIZON = 20
XI_COL = "z"


def decayed_scores_fast(sub_by_cat_date, half_life_days, idx_full):
    lam = np.log(2) / half_life_days
    decay = np.exp(-lam)
    contrib = sub_by_cat_date.reindex(idx_full, fill_value=0.0).values
    out = np.zeros(len(contrib))
    running = 0.0
    for i in range(len(contrib)):
        running = running * decay + contrib[i]
        out[i] = running
    return pd.Series(out, index=idx_full)


def currency_daily_contrib(events, ccy, categories):
    sub = events[(events["Currency"] == ccy) & (events["category"].isin(categories))]
    daily_cat = sub.groupby(["date", "category"])[XI_COL].mean().unstack("category")
    return daily_cat.mean(axis=1, skipna=True).sort_index()


def run_once(events, pair, half_life, horizon):
    base, quote = PAIRS[pair]
    fx = pd.read_parquet(f"{CACHE}/{pair}_daily_ny17.parquet")
    fx.index = pd.to_datetime(fx.index)

    contribs = {}
    for ccy in (base, quote):
        contribs[ccy] = currency_daily_contrib(events, ccy, CATS_DEFAULT)

    idx_full = None
    for ccy in (base, quote):
        idx_full = contribs[ccy].index if idx_full is None else idx_full.union(contribs[ccy].index)
    idx_full = pd.date_range(idx_full.min(), idx_full.max(), freq="D")

    sb = decayed_scores_fast(contribs[base], half_life, idx_full)
    sq = decayed_scores_fast(contribs[quote], half_life, idx_full)
    pair_score = sb - sq

    s_aligned = pair_score.reindex(fx.index.union(pair_score.index)).sort_index().ffill()
    s_aligned = s_aligned.reindex(fx.index)
    s_lag1 = s_aligned.shift(1)

    fwd_ret = fx["close"].apply(np.log).diff(horizon).shift(-horizon)
    x = s_lag1.values
    y = fwd_ret.values
    m = ~np.isnan(x) & ~np.isnan(y)
    if m.sum() < 100:
        return np.nan
    return np.corrcoef(x[m], y[m])[0, 1]


if __name__ == "__main__":
    import sys
    pair = sys.argv[1] if len(sys.argv) > 1 else "AUDUSD"
    events = load_events()

    real_ic = run_once(events, pair, HALF_LIFE, HORIZON)
    print(f"REAL IC ({pair}, xi={XI_COL}, hl={HALF_LIFE}d, h={HORIZON}d): {real_ic:.5f}")

    rng = np.random.default_rng(42)
    null_ics = []
    base, quote = PAIRS[pair]
    for i in range(N_PLACEBO):
        ev = events.copy()
        for ccy in (base, quote):
            mask = ev["Currency"] == ccy
            vals = ev.loc[mask, XI_COL].values.copy()
            rng.shuffle(vals)
            ev.loc[mask, XI_COL] = vals
        ic = run_once(ev, pair, HALF_LIFE, HORIZON)
        null_ics.append(ic)
        if (i + 1) % 50 == 0:
            print(f"  ...{i+1}/{N_PLACEBO} placebo draws done")

    null_ics = np.array(null_ics)
    null_ics = null_ics[~np.isnan(null_ics)]
    p_two_sided = (np.abs(null_ics) >= np.abs(real_ic)).mean()
    print(f"\nPlacebo null (n={len(null_ics)}): mean={null_ics.mean():.5f} std={null_ics.std():.5f}")
    print(f"Placebo IC 2.5/97.5 pct: {np.percentile(null_ics,2.5):.5f} / {np.percentile(null_ics,97.5):.5f}")
    print(f"Real IC {real_ic:.5f} -> two-sided placebo p-value: {p_two_sided:.4f}")
    np.save(f"{CACHE}/placebo_null_{pair}.npy", null_ics)
