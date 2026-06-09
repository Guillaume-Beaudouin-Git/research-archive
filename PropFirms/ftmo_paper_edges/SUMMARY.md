# Paper-Edge Harvest — Summary (FTMO universe, corrected methodology)

**Date:** 2026-06-08 · **Method (non-negotiable):** true-UTC verified, exchange-tz DST-correct,
standard per-bar / close-to-close MTM, honest FTMO costs, OOS split (hold-out 2025-26), **DSR at the
true trial count**, outer-resample CIs, monotone first-passage engine. All committed under `code/`.

## What was tested (documented edges, never cleanly tested by us before)

| Edge | Paper | Verdict | Why it dies |
|---|---|---|---|
| **1. Intraday momentum** (1st 30min → last 30min) | Gao-Han-Li-Zhou, JFE 2018 | **Dead** | Reversed post-publication; the reversal has only +0.30 gross Sharpe (DSR 0.31) and is **obliterated by realistic index cost** (3-5 bp RT → −1.7 to −3.1). 30-min move too small vs spread (L12 cost ceiling). |
| **2. FOMC cycle** (even-week equity premium) | Cieslak-Morse-Vissing, JF 2019 | **Dead** | **Decayed to zero out-of-sample** (2018-26 vs the paper's 1994-2016): long-even book full +0.01 / OOS −0.19, DSR 0.04; long/short −0.71. |
| **3. Overnight-gap fade** (overnight reverses intraday) | Lou-Polk-Skouras 2019 | **Dead** | Full-sample −0.18 (negative most years); OOS +1.18 is the **single 2025-26 favorable-window artifact**, DSR 0.006. |
| **Combined** (FOMC + fade, ρ=−0.04) | — | **No significant edge** | full Sharpe +0.13, OOS +0.49, **DSR 0.05-0.09 (fails)**. |

## End-to-end p(pass ≤ 3mo) of the combined book (outer-resample 90% CI)

| Firm | median | 90% CI | verdict |
|---|--:|--:|---|
| FTMO 2-step | 0.194 | [0.136, 0.265] | below 0.50 |
| Loose 1-step (static 10%DD, no daily) | 0.510 | [0.426, 0.576] | **straddles** 0.50 |
| Asymmetric Instant (9% tgt / 12% DD) | 0.567 | [0.479, 0.633] | **straddles** 0.50 |

## Conclusion

Combining documented academic edges, with corrected rigorous methodology, produces **no statistically
significant edge** (DSR ≈ 0.05) — the 4th independent confirmation that the FTMO-executable free-price
universe is arbitraged. The only reason the loose-firm p(pass) reaches a **median ~0.51-0.57** is the
**barrier geometry** (a loose / asymmetric 1-step firm passes ~0.5 at zero edge), *not* alpha — and the
CI **straddles** 0.50, so it is **not a confident skill-based pass**.

**This is EV-campaign territory, not a hero-attempt:** on a cheap-fee loose-barrier firm the median
attempt is ~coin-flip-favorable; run several, optimize `p·payout − fee`. A *confident* > 0.50 by skill
still requires a genuinely new (non-price) data edge — which, four independent harvests in, the free
price/calendar universe does not provide.

*Committed runners: `code/edge_intraday_momentum.py`, `code/edge1_reversal_audit.py`,
`code/edge_fomc_cycle.py`, `code/edge_overnight_fade.py`, `code/run_combine.py`. Firm params are 2026
archetypes — verify exact current rules + funded-phase economics before any purchase.*
