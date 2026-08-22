# v2 SHORTLIST — survivors (binding gate: DSR > 0.5 on OOS at cumulative N = 97)

Output (2). Cumulative N = **97** (70 burned + 27 v2). DSR deflated with the Gate-0 frozen noise SE (SE0 = 0.845), so **DSR>0.5 ⇔ OOS Sharpe beats the pre-registered noise floor (2.13)**.

## ⛔ Result: **EMPTY. 0 DSR-certified survivors; 0 candidates beat the noise floor.**

Max OOS Sharpe across all 27 v2 candidates = **1.50** (vs floor **2.13**). Per the brief — *fewer than 5 clear → output fewer; zero clear → say so* — the shortlist is **empty**, and the noise floor was **not breached**.

### Near-misses (best OOS performers — all NON-survivors, shown for transparency + the requested correlation matrix)
| id | space | Sharpe IS | Sharpe OOS | OOS 95% CI | exk OOS | yrs+ | DSR | honest kill |
|---|---|--:|--:|--:|--:|--:|--:|---|
| A.xsmom_idxgold_k60 | A (RV) | **−0.46** | 1.50 | ±0.83 | 4.7 | 4/20 | 0.21 | OOS-luck (IS negative, only 4/20 yrs+, 2024 −0.37); + **FTMO-non-compliant** (corr-index L/S hedge) |
| B.tsmom_trendstr0.5 | B | +0.55 | 1.26 | ±0.83 | 3.5 | 14/20 | 0.10 | the **already-known sub-threshold TSMOM** leaking through a loose filter (θ=0.5 barely conditions) — not new |
| B.tsmom100_trendstr1 | B | +0.20 | 0.74 | ±0.83 | 33.6 | 12/20 | 0.03 | conditioning gives no lift (L15); exkurt 34 |
| B.tsmom_dow_TWT | B | +0.03 | 0.72 | ±0.83 | 2.7 | 12/20 | 0.02 | OOS-luck (IS ≈ 0) |
| A.xsmom_idxgold_k20 | A (RV) | −0.32 | 0.65 | ±0.83 | 4.3 | 6/20 | 0.03 | OOS-luck, non-compliant |
| B.tsmom_monthend | B | +0.15 | 0.30 | ±0.83 | 14.3 | 10/20 | 0.004 | settlement-window conditioning kills the signal, no edge left |

*(OOS 95% CI ≈ ±1.96·SE0 ≈ ±0.83 — every near-miss's Sharpe is within one noise-CI of zero.)* Of the 5 candidates with OOS Sharpe > 0.5, **only 1 also has IS Sharpe > 0.3** — and that one is the pre-existing sub-threshold trend premium, not a new edge.

### Mutual correlation — top-6 near-misses (full-sample daily, business days)
```
                       xsmom60  trendstr05  trendstr1  dow_TWT  xsmom20  monthend
A.xsmom_idxgold_k60      1.00      0.14       0.15      0.06     0.48     0.09
B.tsmom_trendstr0.5      0.14      1.00       0.55      0.63     0.08     0.46
B.tsmom100_trendstr1     0.15      0.55       1.00      0.37     0.11     0.25
B.tsmom_dow_TWT          0.06      0.63       0.37      1.00    -0.01     0.40
A.xsmom_idxgold_k20      0.48      0.08       0.11     -0.01     1.00     0.04
B.tsmom_monthend         0.09      0.46       0.25      0.40     0.04     1.00
```
### Tail / stress correlation (worst-decile days of the equal-weight book)
```
                       xsmom60  trendstr05  trendstr1  dow_TWT  xsmom20  monthend
A.xsmom_idxgold_k60      1.00     -0.35      -0.18     -0.44     0.60    -0.19
B.tsmom_trendstr0.5     -0.35      1.00       0.46      0.51    -0.35     0.34
B.tsmom100_trendstr1    -0.18      0.46       1.00      0.23    -0.18     0.04
B.tsmom_dow_TWT         -0.44      0.51       0.23      1.00    -0.43     0.31
A.xsmom_idxgold_k20      0.60     -0.35      -0.18     -0.43     1.00    -0.23
B.tsmom_monthend        -0.19      0.34       0.04      0.31    -0.23     1.00
```
The structure is just two things again — an **index x-sec momentum cluster** (xsmom20≈xsmom60) and the **TSMOM-conditioning cluster** (trendstr/dow/monthend) — decorrelated from each other (ρ≈0.1, tail ρ≈−0.4). But **neither is a survivor**: the x-sec cluster is OOS-luck + non-compliant, the TSMOM cluster is the known sub-threshold premium. A decorrelated *pair of non-edges* is not a sleeve. No selection is made.

**Bottom line:** v2 produced **no survivor** and **no candidate within a noise-CI of the floor**. See `VERDICT` in `README.md`.
