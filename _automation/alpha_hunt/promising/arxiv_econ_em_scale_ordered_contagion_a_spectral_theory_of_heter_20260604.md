# Scale-Ordered Contagion: Spectral Framework for Cross-Market Information Speed and Shock Propagation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.04113v1
**Captured**: 2026-06-04 06:06 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 9b3eda75be41cbbc28f6aad8c53e14c2

## Summary
The paper formalizes how the relative speed at which two financial markets absorb new information determines the temporal structure of shock propagation between them. Built on the HACI framework (Heterogeneous Agents Contagion vs. Interdependence), the authors derive a spectral estimator that recovers each market's adaptation speed from return data, then test three joint predictions on G20 equity markets from 2006 to 2026. The core prediction — that the slower market in a pair sets the horizon at which contagion peaks — is supported (p=0.042). The directional symmetry prediction holds for all 28 market pairs (no statistically significant asymmetry). The strength-asymmetry prediction trends in the expected direction but does not reach significance. India and China are identified as the slowest information adapters; developed markets cannot be distinguished at daily resolution.

## Why it might be useful
The "adaptation speed" estimator in this paper shares conceptual ground with the untested "BTC cross-exchange lead-lag Coinbase→Binance" idea in CLAUDE.md (Shu 2023), where the premise is that one venue processes price-relevant information faster and the other adjusts with a lag. This paper provides a principled spectral framework for estimating those speeds from cross-correlation structure across multiple lags — more theoretically grounded than naive rolling correlation. However, the scale mismatch is large: the paper operates at daily/weekly frequency on equity indices, whereas BTC lead-lag would require intraday (minute-level) resolution, and the spectral method would need revalidation at that frequency. No active strategy (A/B/C) is directly addressed: the contagion angle is orthogonal to TSMOM (A), carry (B), and NQ momentum (C). The methodology is also distinct from the archived multi-asset TSMOM (Sharpe 0.21) and network momentum (GMOM, Sharpe 0.293), both of which failed on other grounds. Most useful as a reference if the BTC cross-exchange lead-lag hypothesis is ever prioritized for development.

## Extracted content
Specific numeric claims: horizon-ordering prediction holds at p=0.042; symmetry prediction holds for all 28 G20 market pairs (p>0.05, i.e., no statistically significant departure from symmetry); strength-asymmetry prediction is in the predicted direction but not statistically significant. India and China identified as the slowest adapters; fastest developed markets cannot be separated at daily granularity. The authors note: "we report them honestly" — an explicit acknowledgment that mixed results are presented without cherry-picking. No Sharpe, MaxDD, or portfolio performance figures (not a trading strategy paper).

## Action proposed
REFERENCE — The daily equity market scope and G20-level aggregation do not map to the intraday crypto/futures universe that Algo_claude operates in. File for future reference if the BTC cross-exchange lead-lag hypothesis (currently listed as "untested — requires multi-venue WebSocket") moves into active research.
