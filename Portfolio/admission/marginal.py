"""
marginal.py — marginal (diversification-aware) sleeve admission criterion.

Why the legacy gate is wrong
----------------------------
``CLAUDE.md`` gated new sleeves on ``SR(book + D) > 1.10 x SR(book)``. That is a
*ratio* gate on the whole book, so it prices a candidate purely by how much
return it adds per unit of book risk. A diversifier adds little return and a lot
of covariance relief; the ratio gate cannot see the second term.

Worked counter-example (the canonical one for this repo):
    book sleeve  s_b = 0.90,   candidate  s_c = 0.50,   rho = 0.0
    ERC 2-sleeve combination  ->  SR = (0.90 + 0.50) / sqrt(2) = 0.990
    legacy gate needs  SR > 1.10 x 0.90 = 0.990  ->  REJECT (by a hair)
yet the candidate lifted the book from 0.90 to 0.99, i.e. +10.0% — the rejection
is an artefact of comparing an ERC *portfolio* to a *single-sleeve* baseline
under a threshold calibrated on nothing.

The correct criterion is the classic marginal one. For a book ``b`` and a small
allocation ``x`` to candidate ``c``:

    d/dx [ SR(b + x c) ] |_{x=0} > 0    <=>    s_c > rho * s_b

so a candidate only has to beat ``rho * s_b``, not ``0.10 * s_b`` of extra book
return. With ``rho <= 0`` *any* positive-Sharpe sleeve is accretive. This module
implements that criterion at the weights actually used (ERC or HRP), plus the
estimation-uncertainty test that stops a noise-level Delta SR from passing.

Conventions
-----------
* All series are **daily excess** returns (project hard rule: excess vs cash).
* ``periods_per_year`` defaults to 252; use 365 for crypto/calendar sleeves.
* Sharpe ratios are annualised.
* Resampling is **block** bootstrap (Politis-Romano stationary bootstrap).
  IID resampling is forbidden by project methodology when trades cluster.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "AdmissionResult",
    "admit",
    "bootstrap_delta_sharpe",
    "calendar_sharpe",
    "conditional_sleeve_series",
    "delta_sharpe",
    "erc_hurdle_sharpe",
    "erc_two_sleeve_sharpe",
    "erc_weights",
    "hrp_weights",
    "marginal_hurdle_sharpe",
    "portfolio_sharpe",
    "stationary_bootstrap_indices",
]

WeightScheme = Literal["erc", "hrp", "equal"]


# ─────────────────────────────────────────────────────────────────────────────
# Closed forms
# ─────────────────────────────────────────────────────────────────────────────

def marginal_hurdle_sharpe(book_sharpe: float, rho: float) -> float:
    """
    Minimum annualised Sharpe a candidate needs to be *marginally* accretive.

    Derivation. With p = b + x c, mu_p = mu_b + x mu_c and
    sigma_p^2 = sigma_b^2 + 2 x rho sigma_b sigma_c + x^2 sigma_c^2,

        d(mu_p / sigma_p)/dx |_{x=0}
            = (mu_c sigma_b - mu_b rho sigma_c) / sigma_b^2

    which is positive iff ``mu_c / sigma_c > rho * mu_b / sigma_b``, i.e.

        s_c > rho * s_b

    Note the hurdle is *independent of the candidate's volatility*: a tiny,
    low-vol, weakly-correlated sleeve is accretive on the same terms as a large
    one — only the size of the improvement scales with weight.

    Args:
        book_sharpe: annualised Sharpe of the current book.
        rho: correlation of candidate daily returns with book daily returns.

    Returns:
        Hurdle Sharpe. Non-positive hurdle means any positive-Sharpe candidate
        is accretive at the margin.
    """
    return float(rho) * float(book_sharpe)


def erc_two_sleeve_sharpe(s_book: float, s_cand: float, rho: float) -> float:
    """
    Exact Sharpe of a 2-sleeve equal-risk-contribution book.

    At ERC with two assets the risk-parity weights are inverse-vol, so each leg
    contributes the same vol budget ``h = w_i sigma_i``. Then
    ``mu_p = h (s_b + s_c)`` and ``sigma_p = h sqrt(2 (1 + rho))``, hence

        SR_erc = (s_b + s_c) / sqrt(2 (1 + rho))

    Volatilities cancel exactly — at ERC only the Sharpes and the correlation
    matter. This is the formula the legacy 2.31 anchor was implicitly using.

    Raises:
        ValueError: if ``rho <= -1`` (degenerate, infinite Sharpe).
    """
    if rho <= -1.0:
        raise ValueError("rho must be > -1 (rho = -1 gives a riskless combination)")
    return float(s_book + s_cand) / float(np.sqrt(2.0 * (1.0 + rho)))


def erc_hurdle_sharpe(book_sharpe: float, rho: float) -> float:
    """
    Minimum candidate Sharpe that is accretive at *ERC* (finite, not marginal)
    weights in a 2-sleeve book.

    Solve ``(s_b + s_c) / sqrt(2 (1 + rho)) > s_b``:

        s_c > s_b * ( sqrt(2 (1 + rho)) - 1 )

    This is strictly harder than the infinitesimal hurdle ``rho * s_b`` because
    ERC forces a large allocation to the candidate rather than an optimally
    small one. Report both: the marginal hurdle says "is it worth any money at
    all", the ERC hurdle says "is it worth an equal risk share".
    """
    if rho <= -1.0:
        raise ValueError("rho must be > -1")
    return float(book_sharpe) * float(np.sqrt(2.0 * (1.0 + rho)) - 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Weights
# ─────────────────────────────────────────────────────────────────────────────

def erc_weights(returns: pd.DataFrame) -> pd.Series:
    """
    Inverse-volatility (naive equal-risk-contribution) weights.

    Exact ERC only for the 2-asset case or a constant-correlation matrix; used
    here because it is the convention the existing book documents ("ERC
    risk-units 50/50") and because it is estimation-robust (no covariance
    inversion).
    """
    vol = returns.std(ddof=1)
    if (vol <= 0).any():
        raise ValueError(f"zero-variance sleeve(s): {list(vol[vol <= 0].index)}")
    w = 1.0 / vol
    return w / w.sum()


def _correl_distance(corr: pd.DataFrame) -> pd.DataFrame:
    return ((1.0 - corr) / 2.0).clip(lower=0.0) ** 0.5


def hrp_weights(returns: pd.DataFrame) -> pd.Series:
    """
    Hierarchical Risk Parity weights (Lopez de Prado 2016).

    Single-linkage tree on the correlation distance, quasi-diagonalisation, then
    recursive inverse-variance bisection. Falls back to inverse-vol for n < 3.
    """
    n = returns.shape[1]
    if n < 3:
        return erc_weights(returns)

    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    corr = returns.corr()
    dist = _correl_distance(corr)
    link = linkage(squareform(dist.values, checks=False), method="single")
    order = [returns.columns[i] for i in leaves_list(link)]

    cov = returns.cov()

    def _ivp(items: Sequence[str]) -> np.ndarray:
        iv = 1.0 / np.diag(cov.loc[items, items].values)
        return iv / iv.sum()

    def _cluster_var(items: Sequence[str]) -> float:
        w = _ivp(items)
        return float(w @ cov.loc[items, items].values @ w)

    weights = pd.Series(1.0, index=order)
    clusters: list[list[str]] = [list(order)]
    while clusters:
        nxt: list[list[str]] = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            mid = len(cl) // 2
            left, right = cl[:mid], cl[mid:]
            vl, vr = _cluster_var(left), _cluster_var(right)
            alpha = 1.0 - vl / (vl + vr)
            weights[left] *= alpha
            weights[right] *= 1.0 - alpha
            nxt += [left, right]
        clusters = nxt
    return weights.reindex(returns.columns) / weights.sum()


def _resolve_weights(returns: pd.DataFrame, scheme: WeightScheme) -> pd.Series:
    if scheme == "erc":
        return erc_weights(returns)
    if scheme == "hrp":
        return hrp_weights(returns)
    if scheme == "equal":
        return pd.Series(1.0 / returns.shape[1], index=returns.columns)
    raise ValueError(f"unknown weight scheme: {scheme!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Sharpe on realised panels
# ─────────────────────────────────────────────────────────────────────────────

def _annualised_sharpe(x: np.ndarray, periods_per_year: float) -> float:
    x = np.asarray(x, dtype=float)
    sd = x.std(ddof=1)
    if sd <= 0 or not np.isfinite(sd):
        return 0.0
    return float(x.mean() / sd * np.sqrt(periods_per_year))


def _fast_panel_sharpe(panel: np.ndarray, scheme: WeightScheme, sqrt_ppy: float) -> float:
    """
    Annualised Sharpe of an inverse-vol ("erc") or equal-weight panel, on raw
    numpy. Used only inside the bootstrap loop, where building a DataFrame per
    resample dominates the runtime. Weights are re-estimated on every resample,
    exactly as the pandas path does — the estimation noise in the weights is
    part of what the bootstrap is measuring.
    """
    if scheme == "equal":
        w = np.full(panel.shape[1], 1.0 / panel.shape[1])
    else:  # "erc" -> inverse volatility
        sd = panel.std(axis=0, ddof=1)
        if not np.all(sd > 0):
            return 0.0
        w = 1.0 / sd
        w /= w.sum()
    r = panel @ w
    s = r.std(ddof=1)
    return 0.0 if s <= 0 else float(r.mean() / s * sqrt_ppy)


def portfolio_sharpe(
    returns: pd.DataFrame,
    weights: pd.Series | None = None,
    scheme: WeightScheme = "erc",
    periods_per_year: float = 252.0,
) -> float:
    """
    Annualised Sharpe of the weighted combination of sleeve return columns.

    Rows with any missing sleeve are dropped: a NaN means "this sleeve has no
    history here", and silently treating it as a flat day would understate the
    sleeve's volatility and inflate its Sharpe.
    """
    returns = returns.dropna()
    if returns.empty:
        raise ValueError("empty return panel")
    w = weights if weights is not None else _resolve_weights(returns, scheme)
    w = w.reindex(returns.columns).astype(float)
    return _annualised_sharpe((returns.values * w.values).sum(axis=1), periods_per_year)


def delta_sharpe(
    book: pd.DataFrame | pd.Series,
    candidate: pd.Series,
    scheme: WeightScheme = "erc",
    periods_per_year: float = 252.0,
) -> float:
    """
    ``SR(book + candidate)`` minus ``SR(book)``, both at ``scheme`` weights, on
    the common (inner-joined) date index so the comparison is like for like.

    Restricting the baseline to the overlap matters: comparing a full-history
    book Sharpe against a short-history combined Sharpe is the single most
    common way a diversification test lies in either direction.
    """
    book_df = book.to_frame("book") if isinstance(book, pd.Series) else book.copy()
    cand = candidate.rename(candidate.name or "candidate")
    joined = book_df.join(cand.to_frame(cand.name), how="inner").dropna()
    if joined.empty:
        raise ValueError("no overlapping dates between book and candidate")
    base = joined[book_df.columns]
    return (
        portfolio_sharpe(joined, scheme=scheme, periods_per_year=periods_per_year)
        - portfolio_sharpe(base, scheme=scheme, periods_per_year=periods_per_year)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Conditionally-active sleeves
# ─────────────────────────────────────────────────────────────────────────────

def calendar_sharpe(active_sharpe: float, active_fraction: float) -> float:
    """
    Convert an *active-window* Sharpe into the **calendar** Sharpe that the
    portfolio actually experiences.

    A sleeve that is flat outside its window has, over the full calendar,
    ``mu_cal = a mu_act`` and ``sigma_cal^2 = a sigma_act^2 + a(1-a) mu_act^2``.
    The second term is second-order for daily returns, so

        s_cal ~= sqrt(a) * s_act

    This is the number that must be fed to the hurdle. Quoting a gated sleeve's
    active-window Sharpe against a full-calendar book Sharpe overstates it by
    ``1/sqrt(a)`` — 2.8x for a sleeve live 13% of the time.

    The compensation is that the *correlation* of a complementarily-gated sleeve
    with the book is <= 0 by construction (see
    :func:`conditional_sleeve_series`), so the hurdle it must clear is <= 0 too.
    """
    a = float(active_fraction)
    if not 0.0 < a <= 1.0:
        raise ValueError("active_fraction must be in (0, 1]")
    return float(active_sharpe) * float(np.sqrt(a))


def conditional_sleeve_series(
    active_returns: pd.Series,
    calendar_index: pd.Index,
    fill: float = 0.0,
) -> pd.Series:
    """
    Expand an active-window return series onto the full calendar, padding the
    inactive days with ``fill`` (0.0 = flat, no position, no cost).

    Use this — not the raw active series — for every correlation, Delta SR and
    barrier computation involving a gated sleeve.
    """
    return active_returns.reindex(calendar_index).fillna(fill).rename(active_returns.name)


# ─────────────────────────────────────────────────────────────────────────────
# Estimation uncertainty — stationary (block) bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def stationary_bootstrap_indices(
    n: int,
    mean_block: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Politis-Romano stationary bootstrap index draw.

    Blocks have geometric length with mean ``mean_block`` and wrap around the
    sample, which preserves short-range serial dependence (the reason IID
    resampling is banned here) while keeping the resample stationary.

    Vectorised: block lengths and starts are drawn in bulk and expanded with
    ``repeat``, so cost is O(n) in numpy rather than O(n) in the interpreter.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    p = 1.0 / max(float(mean_block), 1.0)

    # Draw generously (geometric mean = 1/p), top up in the rare short case.
    n_blocks = int(n * p) + 8
    lens = rng.geometric(p, n_blocks)
    while lens.sum() < n:
        lens = np.concatenate([lens, rng.geometric(p, n_blocks)])

    keep = int(np.searchsorted(np.cumsum(lens), n)) + 1
    lens = lens[:keep]
    starts = rng.integers(0, n, keep)

    total = int(lens.sum())
    block_start = np.repeat(np.cumsum(lens) - lens, lens)
    offsets = np.arange(total, dtype=np.int64) - block_start
    return ((np.repeat(starts, lens) + offsets) % n)[:n].astype(np.int64)


def bootstrap_delta_sharpe(
    book: pd.DataFrame | pd.Series,
    candidate: pd.Series,
    scheme: WeightScheme = "erc",
    periods_per_year: float = 252.0,
    n_boot: int = 2000,
    mean_block: float = 10.0,
    seed: int = 0,
) -> np.ndarray:
    """
    Block-bootstrap distribution of ``Delta SR``.

    The book and the candidate are resampled **jointly** (same row indices) so
    that the resample preserves their cross-sectional dependence — resampling
    them independently would destroy exactly the quantity under test.
    """
    book_df = book.to_frame("book") if isinstance(book, pd.Series) else book.copy()
    cand = candidate.rename(candidate.name or "candidate")
    joined = book_df.join(cand.to_frame(cand.name), how="inner").dropna()
    if joined.empty:
        raise ValueError("no overlapping dates between book and candidate")

    base_cols = list(book_df.columns)
    rng = np.random.default_rng(seed)
    n = len(joined)
    out = np.empty(n_boot, dtype=float)

    if scheme == "hrp":  # needs the clustering path, no numpy shortcut
        for i in range(n_boot):
            smp = joined.iloc[stationary_bootstrap_indices(n, mean_block, rng)]
            out[i] = (
                portfolio_sharpe(smp, scheme=scheme, periods_per_year=periods_per_year)
                - portfolio_sharpe(smp[base_cols], scheme=scheme,
                                   periods_per_year=periods_per_year)
            )
        return out

    vals = joined.values.astype(float)
    base_mask = np.array([c in set(base_cols) for c in joined.columns])
    sqrt_ppy = float(np.sqrt(periods_per_year))
    for i in range(n_boot):
        smp = vals[stationary_bootstrap_indices(n, mean_block, rng)]
        out[i] = (
            _fast_panel_sharpe(smp, scheme, sqrt_ppy)
            - _fast_panel_sharpe(smp[:, base_mask], scheme, sqrt_ppy)
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The gate
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AdmissionResult:
    """Outcome of :func:`admit`. ``verdict`` is PASS / MARGINAL / FAIL."""

    verdict: str
    delta_sharpe: float
    sharpe_book: float
    sharpe_combined: float
    candidate_sharpe: float
    rho: float
    marginal_hurdle: float
    erc_hurdle: float
    p_value: float
    ci: tuple[float, float]
    detectable_delta_sharpe: float
    n_obs: int
    n_trials: int
    alpha_effective: float
    weights: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover - formatting only
        lines = [
            f"verdict           : {self.verdict}",
            f"Delta SR          : {self.delta_sharpe:+.4f}  "
            f"({self.sharpe_book:.3f} -> {self.sharpe_combined:.3f})",
            f"candidate SR      : {self.candidate_sharpe:.3f}   rho = {self.rho:+.3f}",
            f"hurdle (marginal) : {self.marginal_hurdle:+.3f}",
            f"hurdle (at ERC)   : {self.erc_hurdle:+.3f}",
            f"block-bootstrap   : p = {self.p_value:.4f}  "
            f"CI95 = [{self.ci[0]:+.3f}, {self.ci[1]:+.3f}]  n = {self.n_obs}",
            f"min detectable dSR: {self.detectable_delta_sharpe:.3f} at this sample size",
            f"alpha (Sidak, {self.n_trials} trials) = {self.alpha_effective:.4f}",
        ]
        return "\n".join(lines + [f"  - {n}" for n in self.notes])


def admit(
    book: pd.DataFrame | pd.Series,
    candidate: pd.Series,
    scheme: WeightScheme = "erc",
    periods_per_year: float = 252.0,
    alpha: float = 0.05,
    n_trials: int = 1,
    n_boot: int = 2000,
    mean_block: float = 10.0,
    seed: int = 0,
    min_obs: int = 250,
) -> AdmissionResult:
    """
    Marginal admission gate.

    A candidate is ADMITTED when both hold:

    1. ``Delta SR > 0`` at the weights actually used (ERC or HRP), measured on
       the overlapping sample for both book and book+candidate;
    2. that improvement survives estimation noise: the one-sided block-bootstrap
       p-value for ``Delta SR <= 0`` is below the multiple-testing-adjusted
       level ``alpha_eff = 1 - (1 - alpha)^(1/n_trials)`` (Sidak).

    ``MARGINAL`` is returned when ``Delta SR > 0`` but the noise test fails —
    a positive point estimate inside the noise band is *not* a PASS; it is a
    reason to collect more observations, not to allocate.

    Args:
        book: existing book — a DataFrame of sleeve returns (weights are then
            recomputed with the candidate included) or a single combined Series.
        candidate: candidate sleeve daily excess returns. For a gated sleeve,
            pass the **calendar** series (see :func:`conditional_sleeve_series`).
        n_trials: number of candidates tested in the campaign, for the Sidak
            correction. Never leave at 1 when screening a family.
        min_obs: below this overlap length the result is flagged in ``notes``;
            the project convention is N >= 250 daily observations before a
            Sharpe estimate is treated as usable.
    """
    book_df = book.to_frame("book") if isinstance(book, pd.Series) else book.copy()
    cand = candidate.rename(candidate.name or "candidate")
    joined = book_df.join(cand.to_frame(cand.name), how="inner").dropna()
    if joined.empty:
        raise ValueError("no overlapping dates between book and candidate")

    base_cols = list(book_df.columns)
    cand_col = cand.name
    n_obs = len(joined)

    w_base = _resolve_weights(joined[base_cols], scheme)
    book_series = (joined[base_cols].values * w_base.values).sum(axis=1)
    sr_book = _annualised_sharpe(book_series, periods_per_year)

    w_full = _resolve_weights(joined, scheme)
    sr_comb = portfolio_sharpe(joined, weights=w_full, periods_per_year=periods_per_year)

    d_sr = sr_comb - sr_book
    sr_cand = _annualised_sharpe(joined[cand_col].values, periods_per_year)
    rho = float(np.corrcoef(book_series, joined[cand_col].values)[0, 1])

    boot = bootstrap_delta_sharpe(
        joined[base_cols], joined[cand_col], scheme=scheme,
        periods_per_year=periods_per_year, n_boot=n_boot,
        mean_block=mean_block, seed=seed,
    )
    # One-sided bootstrap p-value for H0: Delta SR <= 0.
    p_value = float((boot <= 0.0).mean()) if d_sr > 0 else 1.0
    lo, hi = (float(x) for x in np.percentile(boot, [2.5, 97.5]))
    # Minimum Delta SR this sample could certify one-sided at 95%.
    detectable = 1.645 * float(boot.std(ddof=1))

    alpha_eff = 1.0 - (1.0 - alpha) ** (1.0 / max(int(n_trials), 1))

    notes: list[str] = []
    if 0.0 < d_sr < detectable:
        notes.append(
            f"UNDERPOWERED: Delta SR = {d_sr:+.3f} but this sample can only certify "
            f"{detectable:.3f}. The point estimate is not evidence — extend the sample "
            "or decide on Delta p(pass) instead."
        )
    if n_obs < min_obs:
        notes.append(
            f"overlap n={n_obs} < {min_obs} — Sharpe SE is roughly "
            f"{np.sqrt((1 + (sr_comb / np.sqrt(periods_per_year)) ** 2 / 2) / n_obs) * np.sqrt(periods_per_year):.2f}; "
            "treat every figure as indicative only"
        )
    if rho <= 0:
        notes.append("rho <= 0: hurdle is non-positive, any positive-SR candidate is accretive at the margin")
    if sr_cand < erc_hurdle_sharpe(sr_book, rho) and d_sr > 0:
        notes.append("candidate is below the ERC hurdle but Delta SR > 0 — check weights, do not force ERC")
    if (joined[cand_col] == 0).mean() > 0.5:
        notes.append(
            f"candidate flat on {(joined[cand_col] == 0).mean():.0%} of calendar days — "
            "conditionally-active sleeve; confirm the series passed is the CALENDAR series"
        )

    if d_sr <= 0:
        verdict = "FAIL"
    elif p_value <= alpha_eff:
        verdict = "PASS"
    else:
        verdict = "MARGINAL"

    return AdmissionResult(
        verdict=verdict,
        delta_sharpe=float(d_sr),
        sharpe_book=float(sr_book),
        sharpe_combined=float(sr_comb),
        candidate_sharpe=float(sr_cand),
        rho=rho,
        marginal_hurdle=marginal_hurdle_sharpe(sr_book, rho),
        erc_hurdle=erc_hurdle_sharpe(sr_book, rho),
        p_value=p_value,
        ci=(lo, hi),
        detectable_delta_sharpe=detectable,
        n_obs=n_obs,
        n_trials=int(n_trials),
        alpha_effective=float(alpha_eff),
        weights={str(k): float(v) for k, v in w_full.items()},
        notes=notes,
    )
