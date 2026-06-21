# Deep Learning for U.S. Aggregate Bond Index: Fractional Differencing + MLP/CNN

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.27977
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 1533e0fc3d99efacd26de9c6724243e6

## Summary
A forecasting study on the U.S. aggregate bond index using two neural architectures: MLPs on lagged returns with fractional differencing (López de Prado method, preserving memory while achieving stationarity), and CNNs on Gramian Angular Field image encodings. MLPs perform modestly on fractionally differenced series, while CNN-GAF models show consistently negative OOS R² across all three representations (levels, returns, fractional). The study establishes that bond index levels are unit-root, returns are covariance-stationary with ARCH effects, and the fractional differencing approach provides a middle ground. Overall conclusion: no deep learning architecture reliably beats a naive persistence benchmark on daily bond returns at short horizons.

## Why it might be useful
ZN Baltussen active research (`Futures/research/active/zn_baltussen/`) is studying bond futures momentum and has sigma estimation open. This paper directly validates that short-horizon DL forecasting of bond indices fails, which is useful context: if ZN momentum is real, it should manifest at monthly horizons (matching Baltussen's 12-month lookback), not daily. The fractional differencing methodology (LdP) is also relevant as a preprocessing step for any bond signal — our current HAC SE methodology applied to ZN would benefit from the fractional differencing treatment if bond returns show long memory. The CNN-GAF negative result is a clean N=1 falsification for that approach.

## Extracted content
"MLPs match the strong naive persistence benchmark on levels, collapse toward near-zero forecasts on returns, and achieve the strongest incremental performance on the fractionally differenced series, where moderate dependence remains but unit-root drift is attenuated. In contrast, CNN-GAF models deliver consistently negative out-of-sample R² across all three representations."

"The procedure of López de Prado" cited for fractional differencing.

No code or specific numeric performance claims in excerpt.

## Action proposed
REFERENCE

Useful negative result for ZN Baltussen short-horizon forecasting. Confirms that the bond momentum edge (if real) must come from longer horizons. No direct implementation path needed — already know we're targeting monthly-scale signals on ZN.
