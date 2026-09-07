import numpy as np, pandas as pd
from build_scores import load_events
from analysis import PAIRS, CATS_DEFAULT, CACHE, HALF_LIVES, N_FOLDS
from placebo import currency_daily_contrib, decayed_scores_fast, XI_COL

events = load_events()
pair="AUDUSD"; base,quote = PAIRS[pair]
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
fwd_ret = fx["close"].apply(np.log).diff(20).shift(-20)

for f in range(N_FOLDS):
    test_start, test_end = fold_bounds[f], fold_bounds[f+1]
    train_mask = np.zeros(n, dtype=bool); train_mask[:test_start]=True
    test_mask = np.zeros(n, dtype=bool); test_mask[test_start:test_end]=True
    if train_mask.sum()<200 or test_mask.sum()<20: continue
    best_hl, best_ic = HALF_LIVES[0], -1
    for hl in HALF_LIVES:
        xt = scores_by_hl[hl].values[train_mask]; yt = fwd_ret.values[train_mask]
        m = np.isfinite(xt)&np.isfinite(yt)
        if m.sum()<100: continue
        ic = np.corrcoef(xt[m], yt[m])[0,1]
        if np.isnan(ic): continue
        if best_ic==-1 or abs(ic)>abs(best_ic): best_ic, best_hl = ic, hl
    xte = scores_by_hl[best_hl].values[test_mask]; yte = fwd_ret.values[test_mask]
    m = np.isfinite(xte)&np.isfinite(yte)
    ic_test = np.corrcoef(xte[m], yte[m])[0,1]
    d0, d1 = fx.index[test_start], fx.index[min(test_end,n)-1]
    print(f"fold {f}: dates {d0.date()} -> {d1.date()}, n_test={m.sum()}, chosen_hl={best_hl}, train_IC={best_ic:.4f}, OOS_test_IC={ic_test:.4f}")
