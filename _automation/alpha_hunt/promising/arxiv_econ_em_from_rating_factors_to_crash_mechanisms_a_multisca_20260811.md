# From Rating Factors to Crash Mechanisms: A Multiscale Causal DAG Framework Linking Motor Insurance and Road Safety

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.09441v1
**Captured**: 2026-08-11 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9302591dd29a600c64e8b2eaf9520661

## Summary
Proposes a multiscale causal-DAG framework to reconcile second-to-minute-scale crash mechanisms with annual motor-insurance claims data, distinguishing a crash-occurrence layer, an observation layer (rating variables to latent exposure), and a claims-administration layer. Shows via a French auto-insurance dataset that a raw age-group claim-frequency relativity of 3.39x shrinks to 1.24x once conditioning on bonus-malus history, illustrating how aggregated annual data can mask or distort the underlying causal mechanism.

## Why it might be useful
No direct tie to any Algo_claude asset class or strategy — this is an insurance-actuarial application. The one transferable point is the core warning itself: a coefficient estimated at one aggregation scale (annual claims) can look causal while the underlying generating process operates at a wholly different scale (seconds/minutes) — structurally the same trap as L56 (a session-clock effect measured in the wrong timezone looks different at different resolutions) and L52 (a daily bar silently aggregates a whole overnight session). Filed as a conceptual cross-check, not a test candidate.

## Extracted content
Numeric claims (author's): claim-frequency relativity "3.388 after vehicle/geographic adjustment" versus "1.235 after conditioning on... bonus-malus categories." No code/formulas in the excerpt.

## Action proposed
REFERENCE.
