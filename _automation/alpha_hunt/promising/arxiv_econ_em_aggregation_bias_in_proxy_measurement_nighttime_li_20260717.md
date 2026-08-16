# Aggregation Bias in Proxy Measurement: Nighttime Lights and Local Economic Activity

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.14825v1
**Captured**: 2026-07-17 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: befb540728c4affba737fea849eb18b3

## Summary
Develops a reverse-regression framework for when a high-resolution proxy signal (here, satellite nighttime-lights imagery) aggregated up to administrative-unit level can recover the unobserved local economic activity it is meant to proxy for. Decomposes the predictive elasticity into an elementary elasticity, a reverse-regression attenuation term, and a spatial-aggregation term driven by unit size/within-unit dispersion, showing aggregation systematically pulls the elasticity toward one; validated on nighttime-lights-vs-GDP across five countries, with local calibration holding mainly in richer contexts.

## Why it might be useful
No direct data-source tie — Algo_claude does not currently use nighttime-lights or other satellite proxies. The transferable point is methodological and echoes L52/L56 directly: this paper formalizes the exact failure mode those lessons discovered empirically (aggregating a high-resolution signal to a coarser unit systematically distorts the measured relationship, here proven as a general "pulls elasticity toward one" bias) — worth citing as the general-case theory behind the project's own hard-won, dataset-specific discoveries (ZN session aggregation, gold/silver hourly gap aggregation) next time a new data source with a resolution mismatch is evaluated.

## Extracted content
No code. Formula stated qualitatively (elasticity decomposition into elementary + reverse-regression-attenuation + spatial-aggregation terms) — not reproduced numerically for a specific case in the excerpt.

## Action proposed
REFERENCE.
