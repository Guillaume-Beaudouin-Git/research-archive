"""
portfolio_state.py — PortfolioState data structure
====================================================
Central object tracking all strategies, positions, returns and capital allocation.

Next session will implement:
  (1) load_historical_returns_A() — read tsmom_v3 live log from Propr testnet
  (2) load_historical_returns_B() — read delta_neutral live log from Propr testnet
  (3) load_historical_returns_C() — use iter_05 A$400+B1.2% backtest as proxy until live
  (4) compute first portfolio Sharpe + correlation matrix
  (5) integrate with risk/sizing.py to compute ERC target weights
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StrategyConfig:
    """Static metadata for a strategy."""
    name: str                          # e.g. "A", "B", "C"
    description: str                   # short human-readable label
    asset_class: str                   # "crypto", "futures", "fx", etc.
    live: bool                         # True = live / paper trading
    target_weight: float               # current target capital weight (0-1)
    max_weight: float = 0.50           # hard cap on capital allocation
    corr_limit: float = 0.50           # alert if pairwise correlation exceeds this


@dataclass
class Position:
    """Open position for a strategy at a point in time."""
    strategy: str
    symbol: str
    direction: int                     # +1 long, -1 short
    size: float                        # in contracts or base units
    entry_price: float
    entry_time: pd.Timestamp
    unrealised_pnl: float = 0.0
    stop_price: Optional[float] = None
    tp_price: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio state
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioState:
    """
    Central state object for the multi-strategy portfolio.

    Usage (stub — full implementation next session):
        ps = PortfolioState(capital=50_000, target_vol=0.15)
        ps.add_strategy("A", config_A, returns_A)
        ps.add_strategy("B", config_B, returns_B)
        ps.add_strategy("C", config_C, returns_C)

        print(ps.portfolio_sharpe())
        print(ps.correlation_matrix())
        weights = ps.required_sizing()
    """

    def __init__(self, capital: float = 50_000, target_vol: float = 0.15):
        self.capital: float = capital
        self.target_vol: float = target_vol

        # Keyed by strategy name ("A", "B", "C")
        self.strategies: Dict[str, StrategyConfig] = {}
        self.live_positions: Dict[str, Position] = {}

        # daily_returns columns = strategy names, index = date
        self.historical_returns: pd.DataFrame = pd.DataFrame()

        # capital allocated per strategy ($)
        self.capital_allocation: Dict[str, float] = {}

    # ── Strategy management ───────────────────────────────────────────────────

    def add_strategy(self, name: str, config: StrategyConfig,
                     historical_returns: pd.Series) -> None:
        """
        Register a strategy and its historical daily returns.

        Args:
            name: strategy identifier ("A", "B", "C")
            config: StrategyConfig metadata
            historical_returns: pd.Series, index=date, values=daily $ P&L
                                (scaled to 1-contract or 1-unit, not yet capital-weighted)
        """
        self.strategies[name] = config
        col = historical_returns.rename(name)
        if self.historical_returns.empty:
            self.historical_returns = col.to_frame()
        else:
            self.historical_returns = self.historical_returns.join(col, how="outer")

        # Default allocation: equal weight
        n = len(self.strategies)
        for k in self.strategies:
            self.capital_allocation[k] = self.capital / n

    def update_position(self, position: Position) -> None:
        """Add or update an open position."""
        self.live_positions[position.strategy] = position

    def close_position(self, strategy: str) -> None:
        """Mark a strategy's position as closed."""
        self.live_positions.pop(strategy, None)

    # ── Analytics (stubs — implement next session) ────────────────────────────

    def correlation_matrix(self) -> pd.DataFrame:
        """
        Pairwise Pearson correlation of daily returns across strategies.

        Returns:
            DataFrame (n_strategies × n_strategies)

        TODO next session: implement rolling_correlation_matrix() from
        risk/correlation.py for time-varying view.
        """
        if self.historical_returns.empty or self.historical_returns.shape[1] < 2:
            return pd.DataFrame()
        return self.historical_returns.dropna(how="all").corr()

    def portfolio_sharpe(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Combined portfolio Sharpe using equal weights or supplied weights.

        Args:
            weights: dict of {strategy: weight} summing to 1.0. Default: equal.

        Returns:
            Annualised Sharpe (HAC if n >= 48, else simple).

        TODO next session: wire into risk/sizing.py ERC weights.
        """
        if self.historical_returns.empty:
            return float("nan")

        rets = self.historical_returns.dropna(how="all")
        strats = list(rets.columns)
        if not strats:
            return float("nan")

        if weights is None:
            w = {s: 1.0 / len(strats) for s in strats}
        else:
            w = weights

        # Capital-weighted daily portfolio P&L
        port_pnl = sum(rets[s] * w.get(s, 0.0) for s in strats if s in rets.columns)

        n = port_pnl.notna().sum()
        if n < 2:
            return float("nan")

        if n >= 48:
            try:
                import statsmodels.api as sm
                exog = sm.add_constant(np.ones(n))
                res  = sm.OLS(port_pnl.dropna().values, exog).fit(
                    cov_type="HAC", cov_kwds={"maxlags": 6}
                )
                lrv = float(res.cov_params()[1, 1]) * n
                lrv = max(lrv, 1e-12)
                return float(port_pnl.dropna().mean() / np.sqrt(lrv) * np.sqrt(252))
            except Exception:
                pass

        return float(port_pnl.mean() / port_pnl.std() * np.sqrt(252))

    def portfolio_maxdd(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Combined portfolio maximum drawdown (% of cumulative peak P&L).

        Returns:
            Negative float, e.g. -0.052 means -5.2%.
        """
        if self.historical_returns.empty:
            return float("nan")

        rets = self.historical_returns.dropna(how="all")
        strats = list(rets.columns)
        if not strats:
            return float("nan")

        if weights is None:
            w = {s: 1.0 / len(strats) for s in strats}
        else:
            w = weights

        port_pnl  = sum(rets[s] * w.get(s, 0.0) for s in strats if s in rets.columns)
        cum_pnl   = port_pnl.cumsum()
        running_max = cum_pnl.cummax()
        drawdown  = (cum_pnl - running_max) / running_max.abs().replace(0, np.nan)
        return float(drawdown.min())

    def required_sizing(self) -> Dict[str, float]:
        """
        Compute capital allocation weights using inverse-vol weighting
        as a simple baseline (ERC implemented next session in risk/sizing.py).

        Returns:
            dict {strategy: weight (0-1)}

        TODO next session: replace with ERC from risk/sizing.py.
        """
        if self.historical_returns.empty:
            return {}

        rets  = self.historical_returns.dropna(how="all")
        vols  = {s: float(rets[s].std()) for s in rets.columns if rets[s].std() > 0}
        if not vols:
            return {}

        inv_vol = {s: 1.0 / v for s, v in vols.items()}
        total   = sum(inv_vol.values())
        weights = {s: v / total for s, v in inv_vol.items()}

        # Apply max_weight cap
        for s, w in weights.items():
            cfg = self.strategies.get(s)
            if cfg and w > cfg.max_weight:
                weights[s] = cfg.max_weight

        # Re-normalise after cap
        total = sum(weights.values())
        return {s: w / total for s, w in weights.items()}

    def summary(self) -> str:
        """Human-readable portfolio summary."""
        lines = ["Portfolio Summary", "=" * 50]
        lines.append(f"  Capital: ${self.capital:,.0f}  |  Target vol: {self.target_vol:.0%}")
        lines.append(f"  Strategies: {list(self.strategies.keys())}")
        lines.append(f"  Returns coverage: {self.historical_returns.shape[0]} days")

        sh = self.portfolio_sharpe()
        md = self.portfolio_maxdd()
        lines.append(f"  Portfolio Sharpe (equal-wt): {sh:.3f}" if np.isfinite(sh) else
                     "  Portfolio Sharpe: N/A")
        lines.append(f"  Portfolio MaxDD  (equal-wt): {md*100:.1f}%" if np.isfinite(md) else
                     "  Portfolio MaxDD: N/A")

        corr = self.correlation_matrix()
        if not corr.empty:
            lines.append("\n  Correlation matrix:")
            lines.append(corr.round(3).to_string(col_space=8))

        w = self.required_sizing()
        if w:
            lines.append("\n  Inverse-vol sizing:")
            for s, wt in w.items():
                alloc = wt * self.capital
                lines.append(f"    {s}: {wt:.1%}  (${alloc:,.0f})")

        lines.append("\n  Live positions:")
        if self.live_positions:
            for s, pos in self.live_positions.items():
                lines.append(f"    {s}: {pos.symbol} dir={pos.direction:+d} "
                             f"size={pos.size} pnl=${pos.unrealised_pnl:+.0f}")
        else:
            lines.append("    (none)")

        return "\n".join(lines)
