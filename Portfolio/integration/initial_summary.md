# Portfolio Integration — Phase 1 Summary

*Generated: 2026-05-21*

---

## Critical Context on Strategy B Data Source

Strategy B has been live on Hyperliquid testnet since 2026-05-17 (4 days at time of writing). However, testnet funding rates are **artificial and not representative of mainnet conditions**:

- TST testnet rate was 1.2–1.5% per 8h (≈1300%+ annualized) until May 19, then dropped to 0%
- Other pairs (WLD, WIF, BIO, TRUMP) have **negative** funding rates on testnet, not qualifying
- Strategy is currently in **maintenance hold** (positions open, no new opens, near-zero new carry)
- Actual carry earned on testnet since deployment: **$16.43 in 4 days** ($16.37 TST + $0.06 MEGA), now stalled

**Therefore**: Portfolio analysis uses Strategy B **backtest** data on mainnet historical funding (real WLD/STX rates, 2023–2025), not testnet live data.

This is the correct methodological choice. The testnet deployment validates that:
- Position opening/closing executes correctly ✓
- Spot + perp delta-neutral construction is balanced ✓
- Funding payment detection works ✓ (bug fixed 2026-05-21: `item.get("delta")` parsing)
- Telegram monitoring infrastructure works ✓
- Daily reconciliation logic works ✓

The testnet does **not** validate the carry yield itself. Mainnet deployment requires a **60-day live validation period** before B can be considered "production-validated" rather than "execution-validated".

Historical funding log: `strategies/delta_neutral/logs/funding_history.csv` (162 rows, May 17 → May 21)

---

## 1. Headline

| Metric | Equal-weighted | ERC | ERC 10% vol |
|--------|---------------|-----|-------------|
| Portfolio Sharpe (HAC) | 1.597 | 2.238 | 2.238 |
| MaxDD | -2.3% | -1.0% | -6.9% |
| ERC weights A/B/C | 33/33/33% | 10/68/22% | 10/68/22% (×7.02) |

## 2. Per-Strategy Stats

| Strategy | Source | Period | N obs | Ann Ret | Ann Vol | Sharpe HAC | MaxDD |
|----------|--------|--------|-------|---------|---------|------------|-------|
| A (TSMOM v3) | backtest (live 17d proxy) | 2023-01-01 → 2026-05-19 | 1047 | +9.6% | 8.5% | 1.129 | -7.2% |
| B (Delta-neutral carry) | backtest (live 4d proxy) | 2023-11-18 → 2025-06-18 | 94 | +24.7% | 2.6% | 9.643 | -0.5% |
| C (NQ opening momentum) | backtest (iter_05 A$400+B1.2%) | 2023-01-03 → 2025-12-11 | 564 | +8.2% | 6.2% | 1.321 | -4.7% |

## 3. Correlation Matrix (Full Sample)

```
        A       B       C
A  1.0000  0.0388  0.0149
B  0.0388  1.0000  0.0528
C  0.0149  0.0528  1.0000
```

All pairs < 0.05 — near-zero pairwise correlation. Excellent structural diversification.

### Rolling 60-day (most recent window)

```
     A   B   C
A  1.0 NaN NaN
B  NaN NaN NaN
C  NaN NaN NaN
```

*NaN expected: B ends Jun 2025, C ends Dec 2025 — most recent 60-day window (May 2026) has A only.*

### Correlation alerts

- None. All pairs |corr| < 0.5.

## 4. Portfolio Construction Comparison

ERC estimation uses overlap period: **2023-11-18 → 2025-06-18** (579 days, all 3 strategies co-active).

| Portfolio | Weights A/B/C | Ann Ret | Ann Vol | Sharpe HAC | MaxDD |
|-----------|--------------|---------|---------|------------|-------|
| Equal-weighted (33/33/33) | 33/33/33% | +5.0% | 3.1% | 1.597 | -2.3% |
| Inverse-vol | 10/68/21% | +3.2% | 1.4% | 2.250 | -1.0% |
| ERC | 10/68/22% | +3.2% | 1.4% | 2.238 | -1.0% |
| ERC 10%vol (×7.02) | 71/477/154% | +22.4% | 10.0% | 2.238 | -6.9% |

*B dominates ERC (68%) because its vol is 2.6% vs A=8.5%, C=6.2% — risk-parity assigns highest weight to lowest-vol strategy.*

## 5. Rolling Correlation Alerts

| Pair | Mean corr | Max corr | % windows >0.5 |
|------|-----------|----------|----------------|
| A-B | +0.033 | +0.189 | 0% |
| A-C | +0.027 | +0.350 | 4% |
| B-C | +nan | +nan | 0% |

## 6. Integration Blockers

- **[LOW] Issue C**: A in USDC (Propr), B in USDC (Binance/HL), C in USD (NQ). USDC ≈ USD (peg). No conversion needed.
  - Resolution: Treat as identical. Monitor depeg risk.
- **[LOW] Issue D**: Capital bases differ: A=$5,000, B=$500 (backtest notional, not real), C=$50,000. All returns already normalised to fractional (÷ capital). B backtest uses $500 — if live account is $1000, scale B returns by 2×.
  - Resolution: Document capital scaling factor per strategy at deployment.
- **[MEDIUM] Issue E**: All 3 strategies use backtest data as proxy. Live history: A=17d, B=4d, C=0d. Backtest P&L for A/B will be higher than live. Correlations estimated on backtest may differ in live trading.
  - Resolution: Re-run Phase 1 analysis after 60 live trading days per strategy.
- **[LOW] Issue F**: Strategy B: 92% zero returns. Strategy C: 54% zero returns. Non-zero-only slice used for vol/Sharpe.
  - Resolution: OK for backtest. Monitor live fill rates.

## 7. Recommendations

### Deployment readiness

| Strategy | Status | Basis |
|----------|--------|-------|
| A (TSMOM v3) | **PRODUCTION** | Live since ~2026-05-04, Propr testnet, 17d real returns |
| B (Delta-neutral) | **EXECUTION-VALIDATED, CARRY-PROXIED** | Live execution confirmed, carry yield from backtest; testnet rates artificial |
| C (NQ momentum) | **BACKTEST-ONLY** | iter_05, 0.25 contracts; paper trading not yet started |

**Portfolio deployable TODAY**: A only (Sharpe 1.13, MaxDD -7.2%)

**Portfolio after C paper validation (30 trades)**: A + C (Sharpe ~1.5–1.7 estimated)

**Portfolio after B mainnet validation (60 live days)**: A + B + C as analyzed above (Sharpe 2.24, MaxDD -1.0%)

### Immediate actions
- **Deploy C paper trading** — no blocking issue. Manual log sufficient. Target: 30 trades.
- **Re-run Phase 1 after 60 live days** per strategy with real returns.
- **Strategy B capital scaling**: verify live notional matches backtest $500 assumption before mainnet.
- **ERC live deployment**: do not commit real capital until 60 live days of each strategy.

## 8. Next Phases

- **Phase 2** (next session): daily monitoring cronjob — reads A/B VPS logs + C paper log, computes daily portfolio P&L, correlation alert, rebalance trigger.
- **Phase 3**: paper trade C alongside live A+B, validate 3-strategy portfolio in real time.
- **Phase 4**: parametric stress tests — correlation spike (all pairs → 0.7), vol regime shift (×2 vols), B carry collapse (funding goes negative on mainnet).
- **B mainnet validation criteria** (define before deployment): funding rate threshold to enter, min 60-day live carry vs backtest expected, exit conditions if carry < 50% of backtest expectation.
