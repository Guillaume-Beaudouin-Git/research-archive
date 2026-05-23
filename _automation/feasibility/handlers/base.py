"""
Abstract base class for all feasibility pipeline handlers.
Subclasses must implement classify(), run_level_A/B/C(), and generate_report().
"""
from abc import ABC, abstractmethod
from typing import ClassVar


class HypothesisHandler(ABC):
    """Base handler: classifies a promising hypothesis, then runs 3-level feasibility gates."""

    def __init__(self, promising_md_path: str) -> None:
        self.promising_md_path = promising_md_path
        self.results: dict = {}

    @classmethod
    @abstractmethod
    def classify(cls, promising_md_path: str) -> bool:
        """Return True if this handler is competent to test the hypothesis at promising_md_path."""
        ...

    @abstractmethod
    def run_level_A(self) -> dict:
        """
        Niveau A — IC feasibility gate.
        Returns {"pass": bool, "metrics": {"ic": float, "t_hac": float, "n_events_yr": int, "corr_A": float}}.
        """
        ...

    @abstractmethod
    def run_level_B(self) -> dict:
        """
        Niveau B — Walk-forward backtest + block bootstrap + DSR.
        Returns {"pass": bool, "metrics": {"sharpe_oos": float, "maxdd": float, "wf_positivity": float, "dsr": float, "bootstrap_pval": float}}.
        """
        ...

    @abstractmethod
    def run_level_C(self) -> dict:
        """
        Niveau C — Sanity checks (adjacent asset, shuffle null, OOS decade).
        Returns {"pass": bool, "checks": {"adjacent_asset": bool, "shuffle_null": bool, "oos_decade": bool}}.
        """
        ...

    @abstractmethod
    def generate_report(self) -> str:
        """Return the final markdown report summarising all levels, gates, and conclusion."""
        ...
