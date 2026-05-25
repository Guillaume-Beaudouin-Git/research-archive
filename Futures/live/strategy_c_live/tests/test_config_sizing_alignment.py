"""Tests for config.py sizing alignment with sizing_policy.md."""
from Futures.live.strategy_c_live import config


def test_config_n_contracts_default_is_2():
    """Sizing decision per sizing_policy.md is 2 MNQ — must not regress."""
    assert config.N_CONTRACTS_DEFAULT == 2, (
        f"Expected 2 MNQ per sizing_policy.md, got {config.N_CONTRACTS_DEFAULT}"
    )


def test_n_contracts_alias_matches_default():
    """Legacy N_CONTRACTS alias must stay in sync with N_CONTRACTS_DEFAULT."""
    assert config.N_CONTRACTS == config.N_CONTRACTS_DEFAULT


def test_phase_contracts_all_equal_default():
    """All phases use same sizing until winner-cap feature implemented."""
    assert all(
        v == config.N_CONTRACTS_DEFAULT for v in config.PHASE_CONTRACTS.values()
    ), f"Phase mismatch: {config.PHASE_CONTRACTS}"


def test_guardrail_under_eval_dd():
    """Internal guardrail must be under Tradeify eval DD ($1,000) and not too tight."""
    assert config.GUARDRAIL_TRAILING_DD_USD < 1000
    assert config.GUARDRAIL_TRAILING_DD_USD >= 800
