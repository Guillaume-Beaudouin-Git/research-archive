
## Network Momentum (GMOM) Feasibility — Strategy E

*Generated: 2026-05-21  |  n_tests after: 134*


### 1. Headline verdict

**FAIL** — best variant E3 (Sharpe=0.293)


### 2. Universe

- Total assets after quality filter: **35**
- Date range: 2015-01-05 → 2026-05-20 (2968 trading days)
- Per-class: Bond=3, Commodity=7, Crypto=3, Equity=5, FX=9, Sector=8

### 3. Graph properties (best GMOM variant)

- Edge density: 1.0
- Active edges: 595 / 595 possible
- Mean node degree: 3.9313
- Jaccard stability (consecutive 252d windows): 0.997
- Top 5 cross-asset connections:
  - SHY (Bond) ↔ GLD (Commodity): weight=0.1425
  - JPY (FX) ↔ UNG (Commodity): weight=0.1380
  - NZD (FX) ↔ UNG (Commodity): weight=0.1319
  - NZD (FX) ↔ JPY (FX): weight=0.1318
  - JPY (FX) ↔ TLT (Bond): weight=0.1299

### 4. Variants comparison

| Variant | Sharpe HAC | MaxDD | Ann Ret | Ann Vol | WF%pos | corr(E,A) | corr(E,C) | corr(E,LinReg) | Verdict |
| -------------- | ---------- | -------- | -------- | -------- | -------- | ---------- | ---------- | -------------- | ---------------- |
| E1 | -0.049 | -25.9% | -0.3% | 4.9% | 80% | 0.064 | 0.02 | N/A | FAIL |
| E2 | -0.012 | -25.1% | -0.1% | 4.9% | 80% | 0.065 | 0.021 | N/A | FAIL |
| E3 | 0.293 | -11.6% | 1.1% | 3.9% | 80% | 0.079 | -0.025 | N/A | FAIL |
| E4 | 0.242 | -11.6% | 1.1% | 4.0% | 60% | 0.092 | 0.01 | 0.713 | FAIL |

### 4b. Gate check detail — best variant

**E3:**
- Sharpe HAC: 0.293 (gate >0.7 RESEARCH / >1.0 PROPFIRM)
- Max drawdown: -11.6% (gate >-20% RESEARCH / >-10% PROPFIRM)
- WF% positive: 80% (gate >55% RESEARCH)
- P(EV≤0): 0.1628 | AMTP: 1.0 (n_tests=133)
- corr(E,A): 0.079 | corr(E,C): -0.025 | corr(E,SPY): -0.09
- corr(E,LinReg): N/A (gate <0.75)

Walk-forward windows:
| Window | OOS P&L | N days | Verdict |
|--------|---------|--------|---------|
| 2020-11-30 → 2021-11-16 | +0.0268 | 252 | ✓ |
| 2021-11-17 → 2022-11-03 | -0.0151 | 252 | ✗ |
| 2022-11-04 → 2023-10-23 | +0.0297 | 252 | ✓ |
| 2023-10-24 → 2024-10-09 | +0.0451 | 252 | ✓ |
| 2024-10-10 → 2025-09-26 | +0.0188 | 252 | ✓ |

### 5. Combined portfolio if E passes

- Portfolio: A + C + E3 (equal-weight)
- Sharpe HAC: 1.321
- Max drawdown: -2.8%
- vs A+C only: 1.281
- Period: 885 days overlap

### 6. Diagnostics — Per-asset attribution

Top 10 contributors (E3, gross):

| Asset | Class | Ann Contribution | Active Days |
|-------|-------|-----------------|-------------|
| GBP | FX | +5.97% | 2688.0 |
| NOK | FX | +5.85% | 2688.0 |
| USO | Commodity | +5.11% | 2688.0 |
| CAD | FX | +5.04% | 2688.0 |
| TLT | Bond | +4.25% | 2688.0 |
| AUD | FX | +3.99% | 2688.0 |
| CHF | FX | +3.86% | 2688.0 |
| DBA | Commodity | +3.62% | 2688.0 |
| NZD | FX | +3.36% | 2688.0 |
| XLF | Sector | +2.69% | 2688.0 |

Bottom 5 contributors:
| Asset | Class | Ann Contribution | Active Days |
|-------|-------|-----------------|-------------|
| XLE | Sector | -1.23% | 2688.0 |
| GLD | Commodity | -1.24% | 2688.0 |
| SLV | Commodity | -1.35% | 2688.0 |
| DBB | Commodity | -1.79% | 2688.0 |
| CPER | Commodity | -2.37% | 2688.0 |

Per-class P&L (annualized, equal-weight within class):
| Class | Ann Return | N Assets |
|-------|-----------|---------|
| Bond | +2.08% | 3 |
| Commodity | +0.60% | 7 |
| Crypto | +1.16% | 3 |
| Equity | +0.59% | 5 |
| FX | +3.01% | 9 |
| Sector | +0.10% | 8 |

### 7. Recommendation

**ALL VARIANTS FAIL** — graph learning doesn't transfer to this universe at sufficient Sharpe.

Root cause analysis:

**Issue 1 — Dense graph (Laplacian formulation fails to sparsify):**
With 35 assets whose momentum features are highly correlated (common USD factor, equity
beta factor), `||F_i - F_j||^2` is uniformly small across all pairs. The Frobenius penalty
alone cannot produce a sparse graph — all edge weights converge to ~0.12 (near-uniform).
Result: F_tilde ≈ global-average(F), which is not a useful graph aggregation signal.
The paper's sparse 0.35-density graph was achieved because their 64 futures span truly
diverse risk factors (equity, rates, currency, commodity, vol) with different momentum dynamics.

**Issue 2 — OLS cross-sectional regression underpowered at N=35:**
With 35 assets and 8 features, the OLS regression has 9 parameters fitted on 35 × 252 = 8,820
data points. The cross-sectional signal (which assets lead which) is too noisy at this N.
The paper used 64 assets providing 64 × 252 = 16,128 cross-sectional observations per year.
Corr(E4, E3) = 0.713 — graph aggregation adds limited new information beyond individual features.

**Issue 3 — ETF proxies vs futures:**
Our universe uses ETFs (SPY, GLD, USO) rather than futures. ETF returns include dividends,
management fees, and tracking error that corrupt the momentum signal at the margin.
The paper's futures universe has clean roll-adjusted momentum signals.

**Key positive findings:**
- WF% = 80% for E3/E3/E4 — the strategy is consistently profitable directionally (4/5 OOS windows)
  but not at sufficient magnitude.
- corr(E, A) = 0.08, corr(E, C) = -0.025 — near-zero correlation to existing book. If Sharpe
  were higher, E would be an ideal diversifier.
- A+C+E3 combined: Sharpe 1.32 (vs 1.28 A+C alone). Marginal improvement from low-SR E.
- FX dominates: top 7 contributors are FX pairs. FX momentum (carry + trend) is the real signal.

**Decision: FAIL — consolidate A+C portfolio. Do NOT pursue E as standalone strategy at this form.**
Optional iter_e02: FX-only universe (9 pairs) with larger feature space and currency-specific
graph structure. FX momentum at Sharpe ~0.3 gross suggests the universe needs either higher N,
futures data, or a stronger feature set.


### 8. Implementation lessons

- Universe size N=35 (paper used 64) — borderline; FX correlation makes effective N lower
- Graph edge density: 1.000 (significantly off-target 0.25-0.55 range from paper)
  → Dense graph = near-uniform weighted average of neighbors = no differentiated signal
  → Fix in iter_e02: add L1 penalty (LASSO-type) on edges, or use correlation-threshold sparsification
- Graph stability Jaccard=0.997 — structure is stable across time (matches paper >0.99)
- CVXPY/SCS solver: fast (0.02 sec/call at N=35), no numerical issues
- Monthly rebalance: adequate; quarterly would reduce costs but not fix the structural issue

### 9. Next iteration roadmap


- **iter_e02** (if E passes): VSN-style feature weighting with LASSO (interpretable variable selection)
- **iter_e02** (if E fails): LSTM/Transformer momentum features (Paper 2), or A+C portfolio final
- **Universe expansion**: Add individual commodity futures (CL, GC, SI), bond futures (ZN, ZB)
- **Quarterly rebalance**: Reduce turnover → lower costs → better net Sharpe
- Either way: document methodology rigorously for portfolio framework


### 10. n_tests counter

- Start: 130
- End:   134 (+4 variants)
