# Zero-Copy Semantic Contagion: In-Memory Streaming for Cross-Asset News Propagation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.05733
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e0bb5a90c3bcc625cd2cc06ee28e3e6a

## Summary
A heterogeneous Rust-Python streaming architecture propagates news-driven information across related equities in near real-time, parsing records in ~100 nanoseconds and scanning a target equity universe in ~1.2 microseconds. A multivariate Neural ODE captures cross-company attention patterns as a continuous-time graph updated with each text record. The architecture is zero-copy and in-memory, designed for incrementally consistent latent graph updates.

## Why it might be useful
The sector_hothand_propfirm strategy uses price momentum; cross-sector news contagion could add a 1-3 bar prediction horizon before price momentum fully adjusts. The Neural ODE latent graph approach also addresses the archived Network Momentum GMOM failure (failed N<35): the news-based graph would be sparse and dynamic rather than a dense static correlation matrix. Prototype in Python-only (skip Rust layer) after the sector_hothand audit clears; yfinance for prices, financial news APIs for text.

## Extracted content
The authors report parsing latency of $\sim$100 ns per record and equity universe scan of $\sim$1.2 $\mu$s via a zero-copy Rust edge.

## Action proposed
TEST_LATER

Prototype Python-only cross-sector news contagion for sector_hothand after t_HAC=10.38 audit; skip Rust, use yfinance + public news API.
