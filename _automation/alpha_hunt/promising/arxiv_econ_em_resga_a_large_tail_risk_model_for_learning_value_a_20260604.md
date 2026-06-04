# ReSGA: Large-Scale Joint VaR/ES Forecasting with Size-Enhanced Left-Side Momentum

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.04576v1
**Captured**: 2026-06-04 06:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 1187246f64749b484691a10349d8de1f

## Summary
The paper introduces ReSGA, a retrieval-augmented autoencoder with millions of parameters trained to jointly forecast Value-at-Risk and Expected Shortfall for individual equities. Using 153 firm-level characteristics on monthly US equity returns from 1926 to 2023, the model outperforms twelve econometric and ML baselines on out-of-sample loss and regulatory backtests. A systematic scaling study shows that gains stem primarily from data richness rather than model depth — an important distinction for practitioners who might try lightweight variants. The authors then construct long-short decile portfolios from tail forecasts using a "size-enhanced left-side momentum" strategy, generating economically significant excess returns. Transfer learning generalizes the learned representations to equity markets outside the US.

## Why it might be useful
The "size-enhanced left-side momentum" signal — ranking equities by their predicted worst-case loss rather than by mean return — is a distinct cross-sectional hypothesis from anything currently tested or archived in Algo_claude. The sector_hothand_propfirm research (Equities/research/active/sector_hothand_propfirm/) is currently under mandatory audit for a suspicious t-stat of 10.38 (see _audit/sector_hothand_audit_2026-05-30.md); if that audit finds the signal is spurious, a left-tail-momentum factor provides a theoretically grounded alternative with a risk-premium rationale (stocks with worse expected tail losses carry compensation). A simplified proxy is testable with free data: use rolling 5th-percentile returns or lower semi-deviation as the tail-risk rank instead of the full 153-characteristic model, apply it to a 70-100 stock universe from Tiingo/yfinance, and run it through the same walk-forward pipeline used for jt_momentum_cs. Concretely: pre-register a left-tail CS hypothesis only after the sector_hothand audit concludes — this avoids consuming n_test budget on a redundant angle if the existing active research is salvageable.

## Extracted content
The authors claim performance improvements are "primarily driven by data complexity rather than model complexity." Long-short decile portfolios using the "size-enhanced left-side momentum strategy" generate "significant economic gains." ReSGA "outperforms twelve econometric and machine learning competitors in terms of out-of-sample loss and statistical backtesting." Cross-market transfer learning exhibits "cross-market generalizability." No specific Sharpe ratio or MaxDD figures are reported in the abstract.

## Action proposed
TEST_LATER — The full 153-characteristic model is out of reach with free data sources, but a simplified left-tail momentum proxy (rolling lower semi-deviation on yfinance/Tiingo universe) is implementable. Block: execute only after the sector_hothand_propfirm audit completes and a decision is made on that active thread. Estimated implementation once unblocked: 0.5 day for signal extraction + standard WF pipeline reuse.
