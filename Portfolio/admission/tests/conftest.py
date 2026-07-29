"""
Pytest configuration for Portfolio.admission tests.

The default suite must stay fast enough that it is actually run (< 60s); a test
suite that is skipped protects nothing. Statistical tests that need a large
number of Monte Carlo paths purely to tighten their own standard error are
marked ``slow`` and excluded unless ``--runslow`` is passed:

    /usr/bin/python3 -m pytest Portfolio/admission -q              # fast
    /usr/bin/python3 -m pytest Portfolio/admission -q --runslow    # everything
"""
from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run high-path Monte Carlo convergence tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "slow: high-path Monte Carlo; excluded unless --runslow"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--runslow"):
        return
    skip = pytest.mark.skip(reason="needs --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
