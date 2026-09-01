"""Utilitaires stats : HAC Newey-West lag-6, Sharpe annualise sqrt(n/an),
block bootstrap, placebo de direction."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

RF = 0.0  # rendements R deja excess-of-cost par construction (pas de RF a soustraire sur des R)


def hac_tstat(r):
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 10:
        return dict(n=n, mean=np.nan, t=np.nan, se=np.nan)
    X = np.ones((n, 1))
    model = sm.OLS(r, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return dict(n=n, mean=float(model.params[0]), t=float(model.tvalues[0]), se=float(model.bse[0]))


def ann_sharpe(r, dates, years_span):
    """Sharpe annualise via sqrt(n_trades_per_year) -- PAS sqrt(252) (L47)."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 2 or years_span <= 0:
        return np.nan
    mu, sd = r.mean(), r.std(ddof=1)
    if sd == 0:
        return np.nan
    trades_per_year = n / years_span
    return (mu / sd) * np.sqrt(trades_per_year)


def block_bootstrap_ci(r, block=20, n_boot=2000, seed=0):
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < block * 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    starts_max = n - block
    for b in range(n_boot):
        idx_starts = rng.integers(0, starts_max, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in idx_starts])[:n]
        means[b] = sample.mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def hac_tstat_fast(r, lag=6):
    """HAC Newey-West (Bartlett kernel) manuel, pour la boucle placebo
    (statsmodels OLS est ~15-20ms/appel, trop lent pour 50 tirages x 37
    variantes x plusieurs axes). Verifie egal a statsmodels a 1e-6 pres
    sur le run d'ancrage (voir validate_fast_hac.py)."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 10:
        return np.nan, np.nan, n
    mean = r.mean()
    e = r - mean
    gamma0 = np.dot(e, e) / n
    s = gamma0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1)
        gk = np.dot(e[k:], e[:-k]) / n
        s += 2 * w * gk
    nw_var_of_mean = s / n
    if nw_var_of_mean <= 0:
        return mean, np.nan, n
    se = np.sqrt(nw_var_of_mean)
    return mean, mean / se, n


def sign_placebo_tstats(r, n_draws=50, seed=0, lag=6):
    """Placebo de SIGNE (pas de direction re-simulee) : conserve la magnitude
    |r| de chaque trade reel, retire le signe (attribue par la cassure reelle)
    et le retire a pile-ou-face. Sous H0 'la cassure ne predit rien, seule
    l'exposition au NQ compte', la moyenne reelle (qui peut porter un biais
    long structurel si le NQ a fait +1555%) doit ressembler a cette
    distribution. Retourne le tableau des t places (une valeur par tirage)."""
    r = np.asarray(r, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 10:
        return np.array([])
    mag = np.abs(r)
    rng = np.random.default_rng(seed)
    out = np.empty(n_draws)
    for d in range(n_draws):
        signs = rng.integers(0, 2, size=n) * 2 - 1
        rp = signs * mag
        _, t, _ = hac_tstat_fast(rp, lag=lag)
        out[d] = t
    return out


def matched_count_calendar_placebo(full_daily_r, chosen_mask, n_draws=500, seed=0, lag=6,
                                    exclude=False):
    """Placebo calendaire apparie en COMPTE (style L49) : tire n_draws fois un
    sous-ensemble aleatoire de meme taille que chosen_mask.sum() parmi
    full_daily_r, calcule la stat (moyenne) a chaque tirage. Si exclude=True,
    la stat comparee est celle du complement (les jours GARDES apres
    exclusion), sinon celle du sous-ensemble choisi lui-meme (jours filtres
    IN)."""
    full_daily_r = np.asarray(full_daily_r, dtype=float)
    valid = ~np.isnan(full_daily_r)
    pool = full_daily_r[valid]
    n_pool = len(pool)
    k = int(chosen_mask.sum())
    if k == 0 or k >= n_pool:
        return np.array([])
    rng = np.random.default_rng(seed)
    out = np.empty(n_draws)
    idx_all = np.arange(n_pool)
    for d in range(n_draws):
        picked = rng.choice(idx_all, size=k, replace=False)
        if exclude:
            keep = np.setdiff1d(idx_all, picked, assume_unique=False)
            sample = pool[keep]
        else:
            sample = pool[picked]
        out[d] = sample.mean() if len(sample) > 0 else np.nan
    return out
