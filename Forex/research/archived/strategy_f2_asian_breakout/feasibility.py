"""
Forex/research/active/strategy_f2_asian_breakout/feasibility.py
===============================================================
Strategy F2 — Asian Range Breakout feasibility engine.

Implements:
  - Asian range computation (22:00 UTC J-1 → 07:00 UTC J)
  - 6 mandatory filters (sweet-spot, news, D1 trend, weekday, BoJ gate, weekend gap)
  - Breakout entry: first M5 close outside range between 08:00-11:00 UTC
  - Trade management: SL=0.5×range, TP=0.9×range, time-stop 11:00 UTC
  - Vol-targeting: 20-day rolling σ per pair, 0.15% equity at risk per trade
  - Portfolio P&L: equal-weighted daily returns
  - H1 gate: Sharpe≥0.70, MaxDD≤-15%, PF≥1.25, N_trades≥400
  - H2 gate: sub-period Sharpe ≥ 0.50 (2020-21 / 2022-23 / 2024-25)
  - H3 gate: cross-pair correlation < 0.50
  - DSR computation: n_trials=282, Bailey-LdP 2014

Phased execution:
  Phase 1 (CANARY): GBPUSD 2024 only → 4 pytest tests + equity curve
  Phase 2 (FULL): 4 pairs × 2020-2025 → H1/H2/H3 + DSR → results.json

NOTE: Implementation pending STOP-POINT 2 validation (data_setup.py).
      Canary run pending STOP-POINT 2 explicit GO.
"""
# Implementation pending STOP-POINT 2 validation.
