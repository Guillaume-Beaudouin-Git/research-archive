"""
Portfolio.admission — sleeve admission on a MARGINAL criterion.

Replaces the legacy ratio gate ``SR(book + D) > 1.10 x SR(book)``, which asks a
candidate to be a *return amplifier* and therefore rejects *diversifiers* — the
mechanism that left the deployed FTMO book effectively mono-sleeve.

The correct question is marginal, not multiplicative:

    does adding the candidate raise the book Sharpe by more than estimation noise?

Public API
----------
marginal
    ``marginal_hurdle_sharpe``      closed-form infinitesimal hurdle  s_c > rho * s_b
    ``erc_hurdle_sharpe``           closed-form hurdle at 2-sleeve ERC weights
    ``erc_two_sleeve_sharpe``       SR_erc = (s_b + s_c) / sqrt(2 (1 + rho))
    ``erc_weights``                 inverse-vol (= ERC) weights, n sleeves
    ``hrp_weights``                 hierarchical risk parity weights
    ``portfolio_sharpe``            SR of a weighted book from a return panel
    ``delta_sharpe``                SR(book + candidate) - SR(book)
    ``calendar_sharpe``             active-window SR -> calendar SR
    ``conditional_sleeve_series``   build the calendar series of a gated sleeve
    ``stationary_bootstrap_indices`` Politis-Romano block resampler
    ``bootstrap_delta_sharpe``      block-bootstrap distribution of Delta SR
    ``admit``                       the gate itself -> AdmissionResult

barrier
    ``BarrierConfig``               FTMO-style static-floor / daily-stop barriers
    ``simulate_campaign``           2-phase first-passage Monte Carlo
    ``pass_probability_delta``      Delta p(pass) and Delta days-to-funded
"""

from Portfolio.admission.marginal import (  # noqa: F401
    AdmissionResult,
    admit,
    bootstrap_delta_sharpe,
    calendar_sharpe,
    conditional_sleeve_series,
    delta_sharpe,
    erc_hurdle_sharpe,
    erc_two_sleeve_sharpe,
    erc_weights,
    hrp_weights,
    marginal_hurdle_sharpe,
    portfolio_sharpe,
    stationary_bootstrap_indices,
)
from Portfolio.admission.barrier import (  # noqa: F401
    BarrierConfig,
    CampaignResult,
    pass_probability_delta,
    simulate_campaign,
)

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
    "BarrierConfig",
    "CampaignResult",
    "pass_probability_delta",
    "simulate_campaign",
]
