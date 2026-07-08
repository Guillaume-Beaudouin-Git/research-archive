# Revision Risk in Real-Time Macroeconomic Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.05882v1
**Captured**: 2026-07-08 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: e5ef08db424181e9451b8a3902b660c8

## Summary
Macro series like GDP are released, then repeatedly revised, so a forecaster's uncertainty about the "true" later value is not the same object as their uncertainty about the first print. The paper decomposes later-outcome forecast MSE into preliminary-forecast risk, revision risk, and their covariance, and shows in SPF data that first-release-to-180-day revisions account for 8.3% of later-outcome MSE for real-activity targets versus 3.6% for inflation targets. Because later-outcome errors are scarce in real time, the authors show the later-outcome uncertainty is only partially identified (a Frechet-Makarov bound), and propose transport-based methods to calibrate real-time uncertainty statements — with no single "best" method dominating out-of-sample; the right choice depends on coverage and stability diagnostics.

## Why it might be useful
This is a direct, quantified illustration of the repo's Hard Rule #1 ("Signal at T-1, trade at T. No exceptions.") and the look-ahead-bias risk it exists to prevent: if any future strategy conditions on a released macro series (GDP, inflation, employment), backtesting against the *revised* historical series rather than the *as-first-released, point-in-time* series silently injects information unavailable to a live signal — this paper puts a number on that leak (8.3% of later-outcome MSE from revisions alone for real-activity data). No current active or archived strategy (A/B/C, Commodities XS, Strategy D) uses point-in-time macro releases as a signal input, so there is nothing to test today, but it is a concrete pre-registration checkpoint to cite if a macro-surprise strategy is ever proposed. It also reinforces the methodology toolkit's out-of-sample discipline generally: the paper's own headline result is that no transport/calibration method dominates OOS — method choice must be validated per-series via coverage/stability checks, the same walk-forward ethos (≥5 folds, never a single split) already mandated in CLAUDE.md.

## Extracted content
The paper reports one specific numeric claim: first-release-to-~180-day revisions account for 8.3% of later-outcome MSE across real-activity targets, versus 3.6% across inflation targets, in SPF (Survey of Professional Forecasters) data. No code or formulas are given in the excerpt beyond the qualitative description of the Frechet-Makarov partial-identification set.

## Action proposed
REFERENCE
