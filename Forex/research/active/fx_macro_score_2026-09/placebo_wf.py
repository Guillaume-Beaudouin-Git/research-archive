"""
Placebo matched to the EXACT walk-forward half-life-selection procedure (not just a
fixed half-life) -- this is the correct apples-to-apples null for the flagged
AUDUSD / xi=z / horizon=20 result (pooled OOS IC -0.1766, HAC t -5.18), since the
half-life itself was selected in-sample on training folds each time.

Fewer draws than placebo.py (compute-heavier: full half-life grid x 5 folds per draw).
"""
import numpy as np
import pandas as pd
from build_scores import load_events
from analysis import PAIRS, CATS_DEFAULT, CACHE, HALF_LIVES, N_FOLDS, hac_tstat
from placebo import currency_daily_contrib, decayed_scores_fast, XI_COL

N_PLACEBO = 60
HORIZON = 20
PAIR = "AUDUSD"


def wf_pooled_ic(events, pair, horizon):
    base, quote = PAIRS[pair]
    fx = pd.read_parquet(f"{CACHE}/{pair}_daily_ny17.parquet")
    fx.index = pd.to_datetime(fx.index)

    scores_by_hl = {}
    for hl in HALF_LIVES:
        contribs = {ccy: currency_daily_contrib(events, ccy, CATS_DEFAULT) for ccy in (base, quote)}
        idx_full = None
        for ccy in (base, quote):
            idx_full = contribs[ccy].index if idx_full is None else idx_full.union(contribs[ccy].index)
        idx_full = pd.date_range(idx_full.min(), idx_full.max(), freq="D")
        sb = decayed_scores_fast(contribs[base], hl, idx_full)
        sq = decayed_scores_fast(contribs[quote], hl, idx_full)
        pair_score = (sb - sq)
        s_aligned = pair_score.reindex(fx.index.union(pair_score.index)).sort_index().ffill()
        s_aligned = s_aligned.reindex(fx.index)
        scores_by_hl[hl] = s_aligned.shift(1)

    n = len(fx)
    fold_bounds = np.linspace(0, n, N_FOLDS + 1).astype(int)
    fwd_ret = fx["close"].apply(np.log).diff(horizon).shift(-horizon)

    oos_x, oos_y = [], []
    for f in range(N_FOLDS):
        test_start, test_end = fold_bounds[f], fold_bounds[f + 1]
        train_mask = np.zeros(n, dtype=bool)
        train_mask[:test_start] = True
        test_mask = np.zeros(n, dtype=bool)
        test_mask[test_start:test_end] = True
        if train_mask.sum() < 200 or test_mask.sum() < 20:
            continue
        best_hl, best_ic = HALF_LIVES[0], -1
        for hl in HALF_LIVES:
            xt = scores_by_hl[hl].values[train_mask]
            yt = fwd_ret.values[train_mask]
            m = np.isfinite(xt) & np.isfinite(yt)
            if m.sum() < 100:
                continue
            ic = np.corrcoef(xt[m], yt[m])[0, 1]
            if np.isnan(ic):
                continue
            if best_ic == -1 or abs(ic) > abs(best_ic):
                best_ic, best_hl = ic, hl
        xte = scores_by_hl[best_hl].values[test_mask]
        yte = fwd_ret.values[test_mask]
        oos_x.append(xte)
        oos_y.append(yte)
    if not oos_x:
        return np.nan
    X = np.concatenate(oos_x)
    Y = np.concatenate(oos_y)
    m = np.isfinite(X) & np.isfinite(Y)
    X, Y = X[m], Y[m]
    if len(X) < 30:
        return np.nan
    return np.corrcoef(X, Y)[0, 1]


if __name__ == "__main__":
    events = load_events()
    real_ic = wf_pooled_ic(events, PAIR, HORIZON)
    print(f"REAL walk-forward pooled OOS IC ({PAIR}, xi={XI_COL}, h={HORIZON}): {real_ic:.5f}")

    rng = np.random.default_rng(7)
    base, quote = PAIRS[PAIR]
    null_ics = []
    for i in range(N_PLACEBO):
        ev = events.copy()
        for ccy in (base, quote):
            mask = ev["Currency"] == ccy
            vals = ev.loc[mask, XI_COL].values.copy()
            rng.shuffle(vals)
            ev.loc[mask, XI_COL] = vals
        ic = wf_pooled_ic(ev, PAIR, HORIZON)
        null_ics.append(ic)
        if (i + 1) % 10 == 0:
            print(f"  ...{i+1}/{N_PLACEBO}")

    null_ics = np.array(null_ics)
    null_ics = null_ics[~np.isnan(null_ics)]
    p_two_sided = (np.abs(null_ics) >= np.abs(real_ic)).mean()
    print(f"\nPlacebo (walk-forward-matched) null (n={len(null_ics)}): mean={null_ics.mean():.5f} std={null_ics.std():.5f}")
    print(f"Placebo IC 2.5/97.5 pct: {np.percentile(null_ics,2.5):.5f} / {np.percentile(null_ics,97.5):.5f}")
    print(f"Real IC {real_ic:.5f} -> two-sided placebo p-value: {p_two_sided:.4f}")
