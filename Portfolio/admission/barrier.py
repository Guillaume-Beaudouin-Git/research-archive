"""
barrier.py — translate a Sharpe improvement into the metric that actually pays:
probability of passing a 2-phase propfirm challenge, and time to funded.

Sharpe is a means, not the objective. On a $10k FTMO-style account the objective
is a **first-passage** problem against three barriers:

    * profit target   +10% (phase 1) then +5% (phase 2), from phase start
    * daily stop      -5% intraday from the day's starting balance
    * static floor    -10% from the *initial* balance (FTMO is static, not
      trailing — see memory note ``ftmo_dd_model_static_2026-07``)

Two consequences that Sharpe alone hides and this module exposes:

1.  **Path, not moments.** Two books with identical Sharpe but different daily
    skew/kurtosis have materially different p(pass), because the daily -5% stop
    is a barrier on the *left tail of one day*, not on the annual distribution.
2.  **Flat time is expensive.** A book that is flat for long stretches burns
    calendar without approaching the target, so a sleeve that trades *only*
    when the rest of the book is idle raises p(pass) far more than its solo
    Sharpe suggests. That is exactly the diversifier the ratio gate rejects.

The engine is a plain daily-resolution Monte Carlo over historical or bootstrap
paths. It is deliberately independent of ``data/ftmo_portfolio`` so it can be
unit-tested; it is a *comparative* tool (Delta p between two books on the same
paths), not a replacement for the audited cleanroom funnel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

__all__ = ["BarrierConfig", "CampaignResult", "simulate_campaign", "pass_probability_delta"]


@dataclass(frozen=True)
class BarrierConfig:
    """
    FTMO-style 2-phase challenge barriers, expressed as fractions of the
    *initial* balance (static floor, per the live account model).

    Defaults are the FTMO $10k 2-step contract used by this project.
    """

    target_p1: float = 0.10
    target_p2: float = 0.05
    daily_stop: float = 0.05
    static_floor: float = 0.10
    min_days_p1: int = 4
    min_days_p2: int = 4
    max_days_p1: int = 0          # 0 = no time limit (FTMO removed it)
    max_days_p2: int = 0
    horizon_days: int = 260       # simulation cut-off per phase

    def __post_init__(self) -> None:
        for name in ("target_p1", "target_p2", "daily_stop", "static_floor"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass
class CampaignResult:
    """Aggregate outcome of a Monte Carlo campaign."""

    p_pass: float
    p_fail_floor: float
    p_fail_daily: float
    p_timeout: float
    median_days_to_funded: float
    mean_days_to_funded: float
    n_paths: int

    def as_dict(self) -> dict[str, float]:
        return {
            "p_pass": self.p_pass,
            "p_fail_floor": self.p_fail_floor,
            "p_fail_daily": self.p_fail_daily,
            "p_timeout": self.p_timeout,
            "median_days_to_funded": self.median_days_to_funded,
            "mean_days_to_funded": self.mean_days_to_funded,
            "n_paths": self.n_paths,
        }


def _run_phase(
    path: np.ndarray,
    start: int,
    target: float,
    cfg: BarrierConfig,
    min_days: int,
    max_days: int,
) -> tuple[str, int]:
    """
    Walk one phase from ``start``. Balance is expressed as a fraction of the
    initial balance (1.0 = start of the *challenge*, not of the phase).

    Returns ``(outcome, index_after)`` where outcome is
    ``"pass" | "floor" | "daily" | "timeout"``.

    The balance resets to 1.0 at the start of each phase: FTMO's Verification
    account starts fresh at the initial deposit, with the floor again measured
    from that deposit. Only the *calendar* carries over between phases.
    """
    n = len(path)
    bal = 1.0
    floor = 1.0 - cfg.static_floor
    phase_start_bal = 1.0
    goal = phase_start_bal + target
    traded = 0
    limit = max_days if max_days > 0 else cfg.horizon_days

    for k in range(limit):
        i = start + k
        if i >= n:
            return "timeout", i
        r = float(path[i])
        day_open = bal
        bal *= 1.0 + r
        if r != 0.0:
            traded += 1
        # daily stop: -5% of the day's opening balance
        if bal <= day_open * (1.0 - cfg.daily_stop):
            return "daily", i + 1
        # static floor: -10% of the initial balance
        if bal <= floor:
            return "floor", i + 1
        if bal >= goal and traded >= min_days:
            return "pass", i + 1
    return "timeout", start + limit


def simulate_campaign(
    daily_returns: Sequence[float] | pd.Series | np.ndarray,
    cfg: BarrierConfig | None = None,
    n_paths: int = 5000,
    mean_block: float = 10.0,
    seed: int = 0,
    scale: float = 1.0,
) -> CampaignResult:
    """
    Monte Carlo the 2-phase campaign on block-bootstrapped paths of the book's
    realised daily returns.

    Args:
        daily_returns: book daily returns *at the sizing actually deployed*.
        scale: leverage multiplier applied to the returns (the ``vm`` knob).
            Note this scales both edge and risk — it moves p(pass), never edge.
        mean_block: stationary-bootstrap mean block length (days). Block, not
            IID: daily returns of a trend/carry book cluster.

    Returns:
        :class:`CampaignResult`. ``p_pass`` is the probability of clearing
        *both* phases; ``median_days_to_funded`` is over passing paths only.
    """
    from Portfolio.admission.marginal import stationary_bootstrap_indices

    cfg = cfg or BarrierConfig()
    r = np.asarray(pd.Series(daily_returns).dropna().values, dtype=float) * float(scale)
    if r.size < 20:
        raise ValueError("need at least 20 daily observations to bootstrap a campaign")

    rng = np.random.default_rng(seed)
    horizon = 2 * cfg.horizon_days + 10
    outcomes = {"pass": 0, "floor": 0, "daily": 0, "timeout": 0}
    days: list[int] = []

    for _ in range(n_paths):
        reps = int(np.ceil(horizon / r.size)) + 1
        idx = np.concatenate(
            [stationary_bootstrap_indices(r.size, mean_block, rng) for _ in range(reps)]
        )[:horizon]
        path = r[idx]

        out1, i1 = _run_phase(path, 0, cfg.target_p1, cfg, cfg.min_days_p1, cfg.max_days_p1)
        if out1 != "pass":
            outcomes[out1] += 1
            continue
        out2, i2 = _run_phase(path, i1, cfg.target_p2, cfg, cfg.min_days_p2, cfg.max_days_p2)
        outcomes[out2 if out2 != "pass" else "pass"] += 1
        if out2 == "pass":
            days.append(i2)

    n = float(n_paths)
    return CampaignResult(
        p_pass=outcomes["pass"] / n,
        p_fail_floor=outcomes["floor"] / n,
        p_fail_daily=outcomes["daily"] / n,
        p_timeout=outcomes["timeout"] / n,
        median_days_to_funded=float(np.median(days)) if days else float("nan"),
        mean_days_to_funded=float(np.mean(days)) if days else float("nan"),
        n_paths=n_paths,
    )


def pass_probability_delta(
    book: pd.DataFrame | pd.Series,
    candidate: pd.Series | None,
    cfg: BarrierConfig | None = None,
    scheme: str = "erc",
    n_paths: int = 3000,
    mean_block: float = 10.0,
    seed: int = 0,
    scale: float = 1.0,
    normalize_vol: bool = True,
) -> dict[str, float]:
    """
    Delta p(pass) and Delta time-to-funded from adding ``candidate`` to ``book``.

    Both books are simulated on the **same** bootstrap seed so the comparison is
    paired: the difference is attributable to the sleeve, not to MC noise.

    This is the number to quote in an admission decision. A candidate can have a
    small Delta SR and a large Delta p(pass) when it fills the book's flat
    episodes — the barrier problem rewards *reaching the target sooner*, which a
    Sharpe ratio is blind to.

    ``normalize_vol=True`` (default) re-levers the combined book to the standalone
    book's realised volatility before simulating. Without it the comparison is
    confounded: ERC weights *de-lever* the incumbent (its weight drops from 1 to
    ~1/2), so a genuinely accretive sleeve can show a lower p(pass) purely
    because the account is now taking less risk. Re-levering is what the live
    ``vm`` multiplier does; keeping the risk budget fixed isolates the
    diversification effect, which is the quantity under test. Set it to False
    only when you want the effect of the sleeve *at unchanged gross exposure*.
    """
    from Portfolio.admission.marginal import _resolve_weights  # noqa: PLC0415

    cfg = cfg or BarrierConfig()
    book_df = book.to_frame("book") if isinstance(book, pd.Series) else book.copy()

    if candidate is None:
        base = book_df.dropna()
        w = _resolve_weights(base, scheme)  # type: ignore[arg-type]
        r0 = (base.values * w.values).sum(axis=1)
        res0 = simulate_campaign(r0, cfg, n_paths, mean_block, seed, scale)
        return {"p_pass_book": res0.p_pass, "delta_p_pass": 0.0,
                "median_days_book": res0.median_days_to_funded, "delta_median_days": 0.0}

    cand = candidate.rename(candidate.name or "candidate")
    joined = book_df.join(cand.to_frame(cand.name), how="inner").dropna()
    if joined.empty:
        raise ValueError("no overlapping dates between book and candidate")
    base_cols = list(book_df.columns)

    w0 = _resolve_weights(joined[base_cols], scheme)  # type: ignore[arg-type]
    r0 = (joined[base_cols].values * w0.values).sum(axis=1)
    w1 = _resolve_weights(joined, scheme)  # type: ignore[arg-type]
    r1 = (joined.values * w1.values).sum(axis=1)

    if normalize_vol:
        s0, s1 = float(np.std(r0, ddof=1)), float(np.std(r1, ddof=1))
        if s1 > 0:
            r1 = r1 * (s0 / s1)

    res0 = simulate_campaign(r0, cfg, n_paths, mean_block, seed, scale)
    res1 = simulate_campaign(r1, cfg, n_paths, mean_block, seed, scale)

    d_days = res1.median_days_to_funded - res0.median_days_to_funded
    return {
        "p_pass_book": res0.p_pass,
        "p_pass_combined": res1.p_pass,
        "delta_p_pass": res1.p_pass - res0.p_pass,
        "median_days_book": res0.median_days_to_funded,
        "median_days_combined": res1.median_days_to_funded,
        "delta_median_days": float(d_days),
        "p_fail_daily_book": res0.p_fail_daily,
        "p_fail_daily_combined": res1.p_fail_daily,
        "p_fail_floor_book": res0.p_fail_floor,
        "p_fail_floor_combined": res1.p_fail_floor,
    }
