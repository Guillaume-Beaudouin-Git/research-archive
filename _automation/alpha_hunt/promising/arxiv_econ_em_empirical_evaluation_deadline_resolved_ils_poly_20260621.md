# Empirical Evaluation of Deadline-Resolved Insider Trading Detection on Polymarket

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.02286
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 16b2e06a3a97fc40852e8eba1622d500

## Summary
This paper evaluates the ILS-dl (Information Leakage Score with deadline resolution) for detecting insider trading on Polymarket prediction market contracts. Applied to 23 documented insider events in the 2026 US-Iran conflict cluster, the score correctly flags 19 at p<0.05 with no false positives on a matched control sample. The score peaks 6-12 hours before the event deadline, consistent with the insider information advantage window. The evaluation anchors on the ForesightFlow Insider Cases inventory as ground truth.

## Why it might be useful
Prediction market insider detection methodology has no direct application to the current strategy set (A, B, D, Commodities XS, ZN Baltussen). However, the information leakage score methodology—detecting abnormal price movements in the 6-12 hours before an event resolution—is structurally similar to the pre-FOMC drift signal noted in L42: "Pre-FOMC drift is real on equity indices, post-event REVERSAL is the wrong direction." A comparable information leakage window exists for FOMC announcements. The 6-12 hour pre-event window identified here could inform timing for a pre-FOMC equity index overlay, particularly for the ZN Baltussen bond momentum strategy where FOMC regime drives rate dynamics. However, the Polymarket domain and the prediction market specifics limit direct transferability.

## Extracted content
Specific numeric claims: 23 documented insider events, 19/23 correctly flagged at p<0.05, zero false positives on matched control sample, score peaks 6-12 hours before event deadline.

## Action proposed
REFERENCE

Prediction market domain; no direct trading application. Pre-event information window concept is noted in L42 for equity FOMC drift but existing evidence base is already stronger.
