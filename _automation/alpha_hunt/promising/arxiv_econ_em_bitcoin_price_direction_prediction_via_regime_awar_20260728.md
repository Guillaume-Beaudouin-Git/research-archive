# Bitcoin Price Direction Prediction via Regime-Aware Multi-Modal Fusion of Social Sentiment and Technical Features

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.23370v1
**Captured**: 2026-07-28 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: c65d91a144657beb2c6eea4b18da61f8

## Summary
Proposes RAML, a regime-conditioned neural fusion model for hourly Bitcoin direction prediction that combines OHLCV technical features with Reddit /r/Bitcoin FinBERT sentiment, using a learnable gate that weights sentiment more heavily during high-volatility regimes (detected via rolling 24h realized vol) and price features more during calm regimes. Evaluated on 3,491 hourly observations (July 2024-September 2025) at 3h/6h horizons; RAML reaches macro-F1 of 0.5474/0.5513 and the best 3h AUC (0.5084), and an ablation shows removing the adaptive-fusion gate causes 6h recall to collapse (F1 drops to 0.14).

## Why it might be useful
Directly relevant to Strategy A — this is a regime-conditioned overlay on a crypto directional signal, exactly the class of modification L54 killed (a regime flag needs to predict the mean in the same direction as the variance, not just the variance). The reported macro-F1 of about 0.55 (barely above the 0.50 chance baseline for a binary classifier) is itself a live illustration of why the project's own regime-overlay attempt on the MONO book failed to beat a simple de-lever baseline: weak/near-chance directional skill dressed up with a sophisticated fusion architecture. Second link: the methodology toolkit's dir-accuracy >= 53% diagnostic for TSMOM — RAML's reported AUC (0.5084) and macro-F1 (0.5474) should be read against that same 53% floor; on this evidence the sentiment-fusion signal likely would not clear the project's own feasibility bar even before costs.

## Extracted content
Numeric claims (author's): "macro-F1 of 0.5474 (3h) and 0.5513 (6h), with the highest AUC at 3 hours (0.5084)"; ablation "recall collapse at 6 hours (F1: 0.14)" without the adaptive gate. No code/formulas reproduced.

## Action proposed
REFERENCE — the reported skill (AUC~0.51, F1~0.55) is too close to chance to clear this project's own dir-accuracy>=53% diagnostic bar; not worth testing without a materially stronger published result, but useful as a documented data point that Reddit-sentiment fusion does not obviously help (consistent with L17's earlier kill of sentiment-velocity signals).
