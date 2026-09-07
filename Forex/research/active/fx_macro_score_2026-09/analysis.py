"""
Main analysis: pair scores -> IC (walk-forward lambda selection) -> Grinold decomposition
(IC, TC measured not assumed, BR measured not assumed) -> IJR gross/cost gate at 3 broker tiers.

Pre-registered grid (declared in build_scores.py docstring):
  xi in {sign, z, z_clip}
  half_life in {3,7,14,30,60,90} calendar days, selected in-fold (walk-forward), OOS-evaluated
  pairs in {EURUSD, USDJPY, AUDUSD}  (3 pre-registered pairs, not a 28-pair scan -> AMTP n_tests=9
  for the primary xi x pair grid; rates-included is a labeled secondary robustness check, not
  counted in the primary family)

Costs (round-trip, bps):
  Eightcap Raw ~0.75 bps (to verify -- flagged as UNVERIFIED assumption, not measured this session)
  FTMO 2.48 bps (measured, per CLAUDE.md / prior audits)
  IBKR IDEALPRO ~0.4-0.5 bps + $2 min/order (L57 fixed-cost-dominates-small-notional check)
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from build_scores import load_events, decayed_currency_scores, CCYS

CACHE = "<SCRATCH>"

XI_COLS = ["sign", "z", "z_clip"]
HALF_LIVES = [3, 7, 14, 30, 60, 90]
CATS_DEFAULT = ["Growth", "Inflation", "Employment", "Confidence"]  # Rates excluded by default
PAIRS = {"EURUSD": ("EUR", "USD"), "USDJPY": ("USD", "JPY"), "AUDUSD": ("AUD", "USD")}
HORIZONS = [1, 3, 5, 10, 20]
N_FOLDS = 5


def hac_tstat(x, y, lags=6):
    """HAC (Newey-West lag-6) t-stat of y ~ x (x standardized), matching CLAUDE.md convention."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 30:
        return np.nan, np.nan, len(d)
    X = sm.add_constant(d["x"].values)
    model = sm.OLS(d["y"].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return model.params[1], model.tvalues[1], len(d)


def block_bootstrap_ci(x, y, block=10, n_boot=2000, seed=0):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(d)
    if n < 30:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    xs, ys = d["x"].values, d["y"].values
    n_blocks = int(np.ceil(n / block))
    ics = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        c = np.corrcoef(xs[idx], ys[idx])[0, 1]
        if not np.isnan(c):
            ics.append(c)
    ics = np.array(ics)
    return np.percentile(ics, 2.5), np.percentile(ics, 97.5)


def build_pair_score_panel(events, base, quote, half_life, xi_col, categories):
    sb = decayed_currency_scores(events, base, xi_col, half_life, categories)
    sq = decayed_currency_scores(events, quote, xi_col, half_life, categories)
    idx = sb.index.union(sq.index)
    sb = sb.reindex(idx).ffill().fillna(0.0)
    sq = sq.reindex(idx).ffill().fillna(0.0)
    return (sb - sq).rename("pair_score")


def walk_forward_ic(pair_score, fx_daily, horizon, half_lives_grid=None):
    """5-fold expanding walk-forward. In each fold's TRAINING portion, pick the
    half-life (already baked into pair_score if a single half_life passed -- here
    we instead receive a dict {half_life: series} and select in-fold)."""
    pass  # see run_pair below (integrated directly for clarity/efficiency)


def run_pair(pair, events, xi_col, categories, label):
    base, quote = PAIRS[pair]
    fx = pd.read_parquet(f"{CACHE}/{pair}_daily_ny17.parquet")
    fx.index = pd.to_datetime(fx.index)

    # Precompute pair score for every half-life candidate once (align to fx dates,
    # signal known as of T-1 -> shift by 1 trading day relative to fx close)
    scores_by_hl = {}
    for hl in HALF_LIVES:
        s = build_pair_score_panel(events, base, quote, hl, xi_col, categories)
        s = s.reindex(fx.index.union(s.index)).sort_index()
        s = s.ffill()
        s_aligned = s.reindex(fx.index)  # score AS OF that trading day's close
        s_lag1 = s_aligned.shift(1)      # signal known at T-1, used to trade T (T-1/T rule)
        scores_by_hl[hl] = s_lag1

    n = len(fx)
    fold_bounds = np.linspace(0, n, N_FOLDS + 1).astype(int)
    results = []
    for h in HORIZONS:
        fwd_ret = fx["close"].apply(np.log).diff(h).shift(-h)  # forward h-day log return from T
        oos_x, oos_y, chosen_hls = [], [], []
        for f in range(N_FOLDS):
            test_start, test_end = fold_bounds[f], fold_bounds[f + 1]
            train_mask = np.zeros(n, dtype=bool)
            train_mask[:test_start] = True  # expanding window, train = everything before fold
            test_mask = np.zeros(n, dtype=bool)
            test_mask[test_start:test_end] = True
            if train_mask.sum() < 200 or test_mask.sum() < 20:
                continue
            # pick half-life maximizing |IC| on TRAIN only
            best_hl, best_ic = HALF_LIVES[0], -1
            for hl in HALF_LIVES:
                xt = scores_by_hl[hl].values[train_mask]
                yt = fwd_ret.values[train_mask]
                m = ~np.isnan(xt) & ~np.isnan(yt)
                if m.sum() < 100:
                    continue
                ic = np.corrcoef(xt[m], yt[m])[0, 1]
                if abs(ic) > abs(best_ic) or best_ic == -1:
                    best_ic, best_hl = ic, hl
            chosen_hls.append(best_hl)
            xte = scores_by_hl[best_hl].values[test_mask]
            yte = fwd_ret.values[test_mask]
            oos_x.append(xte)
            oos_y.append(yte)
        if not oos_x:
            continue
        X = np.concatenate(oos_x)
        Y = np.concatenate(oos_y)
        m = ~np.isnan(X) & ~np.isnan(Y)
        X, Y = X[m], Y[m]
        pooled_ic = np.corrcoef(X, Y)[0, 1] if len(X) > 30 else np.nan
        beta, tstat, nobs = hac_tstat(X, Y, lags=6)
        lo, hi = block_bootstrap_ci(X, Y, block=10, n_boot=1000)
        results.append({
            "pair": pair, "xi": xi_col, "label": label, "horizon": h,
            "n_oos": nobs, "IC_oos_pooled": pooled_ic, "HAC_t": tstat,
            "boot_ci_lo": lo, "boot_ci_hi": hi,
            "chosen_half_lives": chosen_hls,
        })
    return results


if __name__ == "__main__":
    events = load_events()
    all_results = []
    for pair in PAIRS:
        for xi_col in XI_COLS:
            res = run_pair(pair, events, xi_col, CATS_DEFAULT, label="primary_no_rates")
            all_results.extend(res)
    df = pd.DataFrame(all_results)
    df.to_csv(f"{CACHE}/ic_results_primary.csv", index=False)
    print(df.to_string())
