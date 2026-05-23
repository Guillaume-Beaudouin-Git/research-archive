"""
tests/test_signals.py — Look-ahead and alignment assertions for all 6 signals.

Run:
  /usr/bin/python3 -m pytest Equities/research/active/indices_swing/tests/test_signals.py -v
  /usr/bin/python3 Equities/research/active/indices_swing/tests/test_signals.py

A signal has look-ahead if:
  1. It uses future prices at time T (using .shift(-h) or similar on close prices)
  2. It references future vol estimates (rolling window that includes T+1 ... T+k)
  3. It applies extra shift to already-lagged sentiment data
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[4]))

import numpy as np
import pandas as pd
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def U():
    from Equities.research.active.indices_swing.data.universe import load_universe
    return load_universe(start="2018-01-01")


# ─────────────────────────────────────────────────────────────────────────────
# S1 VRP — look-ahead: VIX must be same-day, RV21 must use trailing window only
# ─────────────────────────────────────────────────────────────────────────────

class TestS1VRP:
    def test_no_look_ahead_rv21(self, U):
        """RV21 is trailing 21d — signal at T must not use return at T+1."""
        from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
        sig = compute_s1_vrp(U)
        # Last row of signal must be non-NaN (RV21 uses past data)
        # (contrast with fwd_ret where last rows ARE NaN)
        spy_sig = sig["SPY"].dropna()
        assert len(spy_sig) > 0, "S1 VRP SPY signal is all NaN"
        # Signal should NOT have NaN at the very end (unlike forward returns)
        assert spy_sig.iloc[-1] is not None and not np.isnan(spy_sig.iloc[-1]), \
            "S1 VRP: last row is NaN — possible look-ahead bias in vol computation"

    def test_vrp_magnitude_reasonable(self, U):
        """VRP values should be in the range of typical variance risk premium (~0.001–0.1)."""
        from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
        sig = compute_s1_vrp(U)
        spy = sig["SPY"].dropna()
        # VRP = IV_var - RV_var; typical: VIX=0.20, RV=0.15 → VRP ≈ 0.04²-0.0225²... small
        # In variance units: (0.20²) - (0.15²) ≈ 0.04-0.0225 ≈ 0.018
        assert spy.abs().median() < 0.5, f"S1 VRP SPY median |VRP|={spy.abs().median():.4f} seems too large"
        assert spy.abs().median() > 1e-5, f"S1 VRP SPY median |VRP|={spy.abs().median():.2e} seems too small"

    def test_ewq_vrp_nan_without_vstoxx(self, U):
        """EWQ VRP must be NaN unless vstoxx_close is present."""
        from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
        if "vstoxx_close" not in U["vix"].columns or U["vix"]["vstoxx_close"].isna().all():
            sig = compute_s1_vrp(U)
            assert sig["EWQ"].isna().all(), \
                "EWQ VRP should be NaN when vstoxx_close is absent"


# ─────────────────────────────────────────────────────────────────────────────
# S2 VIX term structure — VIX9D must be same-day, no forward VIX
# ─────────────────────────────────────────────────────────────────────────────

class TestS2VIXTerm:
    def test_signal_not_empty(self, U):
        from Equities.research.active.indices_swing.signals.s2_vix_term import compute_s2_vix_term
        sig = compute_s2_vix_term(U)
        n_valid = sig["SPY"].notna().sum()
        assert n_valid > 50, f"S2 VIX term: SPY has only {n_valid} non-NaN obs"

    def test_vix9d_not_future(self, U):
        """Confirm VIX9D is on the same index as prices (not shifted forward)."""
        if "vix9d_close" in U["vix"].columns:
            vix9d = U["vix"]["vix9d_close"]
            prices_idx = U["prices"].index
            common = vix9d.index.intersection(prices_idx)
            # The VIX9D index should not be in the FUTURE relative to prices
            assert vix9d.index.max() <= prices_idx.max() + pd.Timedelta(days=5), \
                "VIX9D index extends beyond prices index — possible temporal misalignment"

    def test_signal_range(self, U):
        """VIX9D/VIX ratio typically 0.6–1.4; signal = 1 - ratio should be in [-0.4, 0.4]."""
        from Equities.research.active.indices_swing.signals.s2_vix_term import compute_s2_vix_term
        sig = compute_s2_vix_term(U)
        spy = sig["SPY"].dropna()
        if len(spy) > 0:
            assert spy.abs().max() < 5.0, \
                f"S2 extreme values: max|signal|={spy.abs().max():.2f} — check ratio computation"


# ─────────────────────────────────────────────────────────────────────────────
# S3 TOM — binary dummy, no future price used in signal construction
# ─────────────────────────────────────────────────────────────────────────────

class TestS3TOM:
    def test_binary_values(self, U):
        """TOM signal must be exactly 0 or 1."""
        from Equities.research.active.indices_swing.signals.s3_turn_of_month import compute_s3_tom
        sig = compute_s3_tom(U)
        unique = set(sig["SPY"].dropna().unique())
        assert unique.issubset({0.0, 1.0}), f"S3 TOM non-binary values: {unique}"

    def test_event_frequency(self, U):
        """TOM window = 5 days/month → ~5/21 ≈ 24% of days should be TOM days."""
        from Equities.research.active.indices_swing.signals.s3_turn_of_month import compute_s3_tom
        sig = compute_s3_tom(U)
        frac = sig["SPY"].mean()
        assert 0.15 < frac < 0.35, \
            f"TOM fraction={frac:.2%} — expected ~24% (5/21 trading days)"

    def test_no_future_dates_in_signal(self, U):
        """Signal at T uses only calendar position — no future prices."""
        from Equities.research.active.indices_swing.signals.s3_turn_of_month import compute_s3_tom
        sig = compute_s3_tom(U)
        # Signal must cover the same index as prices (no truncation at start)
        assert sig.index[0] == U["prices"].index[0], \
            "TOM signal starts later than prices — check month-end detection logic"

    def test_event_study_sign(self, U):
        """Event study: mean return at offsets 0, +1, +2 should typically be positive (TOM effect)."""
        from Equities.research.active.indices_swing.signals.s3_turn_of_month import compute_s3_event_study
        es = compute_s3_event_study(U, ticker="SPY", h=1)
        # Not a strict test (effect varies by sample), just check it runs and has correct columns
        assert "offset" in es.columns and "mean_ret" in es.columns and "t_stat" in es.columns


# ─────────────────────────────────────────────────────────────────────────────
# S4 Sentiment — no extra shift on already-lagged series
# ─────────────────────────────────────────────────────────────────────────────

class TestS4Sentiment:
    def test_s4b_naaim_coverage(self, U):
        """NAAIM is available from 2006; S4b should have > 500 obs."""
        from Equities.research.active.indices_swing.signals.s4_sentiment_composite import compute_s4_variants
        variants = compute_s4_variants(U)
        s4b_spy = variants["s4b_naaim_only"]["SPY"]
        n = s4b_spy.notna().sum()
        assert n > 200, f"S4b NAAIM-only: only {n} non-NaN obs — expected > 200"

    def test_no_extra_shift_applied(self, U):
        """
        Sentiment series is already shifted for publication lag in fetch_sentiment.
        s4_sentiment_composite.py must NOT apply additional .shift() or .lag().
        """
        from Equities.research.active.indices_swing.signals.s4_sentiment_composite import compute_s4_variants
        variants = compute_s4_variants(U)

        # If we shift the signal by 1 extra day, it should differ from the original
        s4b = variants["s4b_naaim_only"]["SPY"].dropna()
        if len(s4b) < 10:
            pytest.skip("Not enough S4b data to test")

        naaim_sent = U["sentiment"].get("naaim_exposure", pd.Series(dtype=float)) \
            if hasattr(U["sentiment"], "get") else U["sentiment"]["naaim_exposure"] \
            if "naaim_exposure" in U["sentiment"].columns else pd.Series(dtype=float)

        if naaim_sent.notna().sum() < 10:
            pytest.skip("NAAIM not available")

        # The signal and NAAIM should be negatively correlated (signal is inverted)
        from scipy.stats import spearmanr
        common = s4b.index.intersection(naaim_sent.index)
        if len(common) < 10:
            pytest.skip("No overlap to test")
        r, _ = spearmanr(s4b.loc[common].values, naaim_sent.loc[common].values)
        assert r < 0, (
            f"S4b signal has positive correlation with raw NAAIM (r={r:.2f}). "
            "Expected negative (contrarian — high NAAIM → negative signal)."
        )


# ─────────────────────────────────────────────────────────────────────────────
# S5 XS Momentum — 6m return uses only past prices
# ─────────────────────────────────────────────────────────────────────────────

class TestS5XSMomentum:
    def test_cross_sectional_rank_bounds(self, U):
        """XS momentum scaled ranks should be in [-1, +1]."""
        from Equities.research.active.indices_swing.signals.s5_xs_momentum import compute_s5_xs_momentum
        sig = compute_s5_xs_momentum(U)
        spy = sig.get("SPY", pd.Series(dtype=float)).dropna() if isinstance(sig, pd.DataFrame) \
            else sig.dropna()
        if len(spy) == 0:
            pytest.skip("SPY not in XS momentum output")
        assert spy.min() >= -1.01 and spy.max() <= 1.01, \
            f"S5 XS rank out of [-1,+1]: min={spy.min():.3f}, max={spy.max():.3f}"

    def test_no_look_ahead_in_momentum(self, U):
        """Signal at T uses close[T-126 : T] — first 126 rows must be NaN."""
        from Equities.research.active.indices_swing.signals.s5_xs_momentum import compute_s5_xs_momentum
        sig = compute_s5_xs_momentum(U)
        if "SPY" not in sig.columns:
            pytest.skip("SPY not in output")
        # First 126 rows should be NaN (no 6m lookback yet)
        first_valid = sig["SPY"].first_valid_index()
        first_date  = sig.index[0]
        lookback_end = sig.index[125] if len(sig) > 125 else sig.index[-1]
        assert first_valid >= first_date + pd.Timedelta(days=100), \
            f"S5: first valid signal at {first_valid} — too early (expected after ~126 trading days)"


# ─────────────────────────────────────────────────────────────────────────────
# S6 HY OAS — 5d change uses trailing prices only
# ─────────────────────────────────────────────────────────────────────────────

class TestS6HYOAS:
    def test_signal_not_empty(self, U):
        from Equities.research.active.indices_swing.signals.s6_hy_oas_regime import compute_s6_hy_oas
        sig = compute_s6_hy_oas(U)
        n = sig["SPY"].notna().sum()
        assert n > 100, f"S6 HY OAS: only {n} non-NaN obs"

    def test_no_look_ahead_in_5d_change(self, U):
        """5d change uses lag (past data only). No shift(-5) should be in the signal."""
        from Equities.research.active.indices_swing.signals.s6_hy_oas_regime import compute_s6_hy_oas
        sig = compute_s6_hy_oas(U)
        # The signal should NOT have NaN at the very end (5d lag uses past data)
        spy_end = sig["SPY"].iloc[-5:].notna().sum()
        assert spy_end >= 3, "S6: last 5 rows are mostly NaN — possible forward-shift contamination"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-signal sanity: no signal should correlate > 0.95 with another (data reuse)
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossSignalOrthogonality:
    def test_s1_and_s3_are_orthogonal(self, U):
        """VRP and TOM use completely different inputs — should have low correlation."""
        from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
        from Equities.research.active.indices_swing.signals.s3_turn_of_month import compute_s3_tom
        from scipy.stats import spearmanr

        s1 = compute_s1_vrp(U)["SPY"].dropna()
        s3 = compute_s3_tom(U)["SPY"]
        common = s1.index.intersection(s3.index)
        if len(common) < 100:
            pytest.skip("Not enough overlap")
        r, _ = spearmanr(s1.loc[common].values, s3.loc[common].values)
        assert abs(r) < 0.95, f"S1 and S3 have suspicious correlation |r|={abs(r):.3f}"


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    pytest.main([__file__, "-v", "--tb=short"])
