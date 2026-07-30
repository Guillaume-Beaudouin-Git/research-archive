# PRE-REG H_B — Conditional long-convexity (straddle after vol compression)
Frozen 2026-07-16 before result. Growth gate. Mandate-ideal structure: bounded loss (premium), unbounded upside.

## Thesis / test
Long ATM straddle on a future when volatility is COMPRESSED (bottom quartile of trailing 1yr RV) profits
if realized vol subsequently EXPANDS by more than the VRP premium. Straddle P&L (held T=20d) reduces to:
  E[net] ∝ σ_RV_forward − k·σ_RV_entry   (k = IV/RV multiple ≈ VRP, tested at 1.0/1.1/1.2)
No option data needed for the first-order edge test (approximation; real smile/bid-ask deferred).

## Signal (frozen)
- Universe: liquid futures ES/NQ/CL/GC/HG/ZN/6E + NG (high vol-of-vol). RV_20 = 20d realized vol.
- Compression = RV_20 in bottom quartile of trailing 252d. Non-overlapping 20d holds.
- Entry: pay IV = k·RV_entry; hold 20d; payoff = |20d move|. Net = |move| − 0.8·IV·√(20/252).

## Gate (frozen kill-rules)
1. Net straddle EV > 0 at realistic k=1.15 (else theta bleed wins → dead).
2. Conditional (compression) must BEAT unconditional (always-buy) — else the signal adds nothing.
3. Skew ≥ 0 (expected strongly positive — bounded loss). Report.
4. Two-sided by construction (profits on up OR down moves) ✓ — verify not a directional proxy.
5. MC ruin (bounded per-trade loss → expect ~0) + growth frontier at ¼/½/full Kelly of premium budget.
Caveat: approximation ignores option bid-ask (WIDE on futures options, ~5-15% of premium) — a pass here
is provisional pending real option-price validation.
