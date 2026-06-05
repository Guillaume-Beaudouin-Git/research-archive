# When the Scaffold Stays On: AI, Practice Style, and Screening in Skill Formation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.06253v1
**Captured**: 2026-06-05 08:02 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: ae9fa41029091ffafde992e6415e6e44

## Summary
The paper investigates whether generative AI tools erode "frontier skill" — the highest-level ability achieved without AI assistance — in elite programming competitions. Using behavioral signatures extracted from Codeforces histories (more first-attempt acceptances, fewer retries as a proxy for AI-assisted practice), the authors track how AI adoption affects rated performance across cohorts. Among participants not selected by AI-prohibited competitions (ICPC/IOI), stronger AI-usage signatures predict smaller subsequent skill gains. Within the AI-prohibited ICPC cohort, however, the same AI-style practice signature predicts better non-AI-aided scores. The central finding: whether AI substitutes for or accelerates genuine skill development depends entirely on whether an institutional screening mechanism selects the user population.

## Why it might be useful
The propfirm evaluation structure in Algo_claude (PROPFIRM_PASS: Sharpe>1.0, MaxDD<-10%, WF>60%) functions as a "type-separating institution" in precisely the sense the paper defines — it screens for genuine edge vs. luck in unproctored backtesting. The paper's concern about "substitute-users" vs. "complement-users" maps directly onto the risk of LLM-assisted research producing overfitted strategies that pass backtest but fail live, which is why L20 (DSR mandatory for n_mod≥2) and AMTP exist as hard gates. Concretely, the paper reinforces the current practice of treating any strategy with n_mod>5 as requiring a walk-forward penalty even if the in-sample Sharpe looks strong — the propfirm evaluation is the "proctored exam", not the backtest. No executable test follows from this paper; the value is methodological validation of the existing screening architecture.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

The paper provides conceptual validation for the propfirm-as-type-separator framing and the necessity of DSR/AMTP corrections. No direct trading test available from the excerpt. The L1 "metrics" match likely triggered on the word "rating" in the abstract, which is not a financial metric — note this for potential L0 filter refinement.
