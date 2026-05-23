"""
Handler for calendar-based skip-month / seasonal anomaly hypotheses.
Classifies hypotheses that involve monthly or seasonal return patterns
(e.g. January effect, sell-in-May, month-of-year momentum skips).
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from .base import HypothesisHandler
from ..data.loaders import (
    STRATEGY_A_ADJACENT,
    STRATEGY_A_CORE,
    load_strategy_a_universe,
    split_universe,
)
from ..stats.backtest_wf import walk_forward_backtest
from ..stats.bootstrap import stationary_bootstrap_sharpe
from ..stats.dsr import compute_sharpe_stats, deflated_sharpe_ratio
from ..stats.ic_check import cross_sectional_ic, hac_t_stat, level_A_gate
from ..stats.sanity_checks import (
    adjacent_asset_replication,
    oos_decade_check,
    shuffle_null_test,
)

# Number of trials in this research session (AMTP denominator for DSR).
# Equals current Algo_claude n_tests from CLAUDE.md.
_N_TESTS_GLOBAL: int = 274

# Classify keywords (case-insensitive)
_SKIP_KEYWORDS = [
    r"skip.month", r"skip month", r"jegadeesh", r"last.month.*return",
    r"month.*reversal", r"short.term.*reversal",
]
_MOMENTUM_KEYWORDS = [r"momentum", r"tsmom", r"trend.follow"]


class SkipMonthHandler(HypothesisHandler):
    """Handler for skip-month / short-term reversal hypotheses on the TSMOM signal."""

    skip_variants: list[int] = [0, 5, 21]  # 0=baseline, 5=week skip, 21=month skip
    universe_tickers: list[str] = STRATEGY_A_CORE

    # ── Classification ─────────────────────────────────────────────────────────

    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        """
        Return True if .md mentions skip-month terminology AND momentum.

        Matches 'skip month', 'skip-month', 'Jegadeesh', 'last month returns',
        'month reversal', or 'short-term reversal', AND separately 'momentum' /
        'tsmom' / 'trend follow'. Case-insensitive.
        """
        try:
            text = open(promising_md_path, encoding="utf-8").read()
        except OSError:
            return False
        has_skip = any(re.search(kw, text, re.IGNORECASE) for kw in _SKIP_KEYWORDS)
        has_mom = any(re.search(kw, text, re.IGNORECASE) for kw in _MOMENTUM_KEYWORDS)
        return has_skip and has_mom

    # ── Initialisation ─────────────────────────────────────────────────────────

    def __init__(self, promising_md_path: str) -> None:
        super().__init__(promising_md_path)
        self._prices: pd.DataFrame | None = None  # lazy-loaded cache

    def _get_prices(self) -> pd.DataFrame:
        """Load and cache Strategy A core prices (BTC, ETH, SOL)."""
        if self._prices is None:
            self._prices = load_strategy_a_universe(
                start="2018-01-01",
                end=str(date.today()),
                tickers=self.universe_tickers,
            )
        return self._prices

    # ── Signal computation ─────────────────────────────────────────────────────

    def _compute_signal_with_skip(
        self,
        prices: pd.DataFrame,
        skip: int = 0,
        lookback: int = 28,
    ) -> pd.DataFrame:
        """
        TSMOM signal variant with skip-month convention.

        Parameters
        ----------
        prices : pd.DataFrame
            date × asset closing prices.
        skip : int
            Number of most-recent days to exclude from the lookback window.
            skip=0 → standard (cum_ret[t-lookback : t-1] after execution lag).
            skip=21 → Jegadeesh-Titman classic (skip last month before lookback).
        lookback : int
            Momentum window in calendar days (default 28, matching Strategy A).

        Returns
        -------
        pd.DataFrame
            Signal in [0, 1). No execution lag applied here; vol_target_positions
            will apply the additional shift(1). Net window: [t-lookback-skip : t-1-skip].
        """
        log_returns = np.log(prices / prices.shift(1))
        # shift(skip): skip the `skip` most-recent days before the execution lag
        cum_return = log_returns.rolling(lookback).sum().shift(skip)
        vol_L = log_returns.rolling(lookback).std().shift(skip) * np.sqrt(lookback)
        signal = np.tanh(cum_return / (vol_L + 1e-8)).clip(lower=0.0)
        signal[cum_return.isna()] = np.nan
        return signal

    # ── Level A — IC Feasibility ───────────────────────────────────────────────

    def run_level_A(self) -> dict:
        """
        Compare IC across skip variants vs baseline (skip=0).

        For each skip in skip_variants, computes Spearman cross-sectional IC
        against 7-day forward returns, HAC t-stat, and runs level_A_gate vs baseline.

        Returns
        -------
        dict
            variants : dict[int, dict] — IC metrics per skip value
            surviving_variants : list[int] — skips where level_A_gate PASSed
            pass  : bool — True if at least one variant PASSes
        """
        prices = self._get_prices()
        log_returns = np.log(prices / prices.shift(1))

        # 7-day forward returns at time t = return from t+1 to t+7 (1-day execution lag)
        forward_7d = log_returns.rolling(7).sum().shift(-7)

        ic_per_variant: dict[int, dict] = {}
        for skip in self.skip_variants:
            sig = self._compute_signal_with_skip(prices, skip=skip)
            # min_assets=2: BTC/ETH/SOL universe has only 3 assets
            ic_series = cross_sectional_ic(sig, forward_7d, min_assets=2)
            t_hac, p_hac = hac_t_stat(ic_series)
            ic_per_variant[skip] = {
                "mean_ic": float(ic_series.mean()),
                "t_hac": float(t_hac) if not np.isnan(t_hac) else np.nan,
                "p_hac": float(p_hac) if not np.isnan(p_hac) else np.nan,
                "n_dates": int(ic_series.notna().sum()),
                "ic_series": ic_series,
            }

        # level_A_gate: compare each non-baseline variant against skip=0
        baseline_sig = self._compute_signal_with_skip(prices, skip=0)
        surviving: list[int] = []
        gate_results: dict[int, dict] = {}
        for skip in self.skip_variants[1:]:  # skip skip=0 (it's the baseline)
            variant_sig = self._compute_signal_with_skip(prices, skip=skip)
            # min_assets=2, min sample=30 (small 3-asset universe)
            gate = level_A_gate(
                baseline_sig, variant_sig, forward_7d,
                ic_threshold=0.005, min_assets=2,
            )
            gate_results[skip] = gate
            if gate["verdict"] == "PASS":
                surviving.append(skip)

        overall_pass = len(surviving) > 0
        result = {
            "variants": {k: {k2: v2 for k2, v2 in v.items() if k2 != "ic_series"}
                         for k, v in ic_per_variant.items()},
            "gate_results": {k: {k2: v2 for k2, v2 in v.items()
                                  if k2 not in ("ic_baseline", "ic_variant", "delta_ic")}
                              for k, v in gate_results.items()},
            "surviving_variants": surviving,
            "pass": overall_pass,
        }
        self.results["level_A"] = result
        return result

    # ── Level B — Walk-Forward Backtest ────────────────────────────────────────

    def run_level_B(self) -> dict:
        """
        Walk-forward backtest + bootstrap + DSR for variants surviving Level A.

        Uses n_trials=len(skip_variants) for the local DSR and n_trials_global
        for the full AMTP-corrected DSR.

        Returns
        -------
        dict
            per_variant: dict[int, dict] — WF + bootstrap + DSR metrics
            best_variant: int — skip with highest OOS Sharpe
            pass: bool — True if at least one variant achieves DSR > 0.95
        """
        prices = self._get_prices()
        level_a = self.results.get("level_A", {})
        candidates = level_a.get("surviving_variants", self.skip_variants)
        if not candidates:
            candidates = self.skip_variants  # run all if none survived A (shouldn't happen)

        per_variant: dict[int, dict] = {}
        for skip in candidates:
            def make_signal_func(s: int):
                def signal_func(p: pd.DataFrame) -> pd.DataFrame:
                    return self._compute_signal_with_skip(p, skip=s)
                return signal_func

            try:
                wf = walk_forward_backtest(make_signal_func(skip), prices)
            except Exception as exc:
                per_variant[skip] = {"error": str(exc), "pass": False}
                continue

            pnl_oos = wf["pnl_oos"].sum(axis=1) if isinstance(wf["pnl_oos"], pd.DataFrame) \
                else wf["pnl_oos"]
            pnl_oos_port = pnl_oos.dropna()

            boot = stationary_bootstrap_sharpe(pnl_oos_port, n_resamples=500)
            sr_stats = compute_sharpe_stats(pnl_oos_port)
            # DSR with local trial count (variants tested here) and global n_tests
            dsr_local = deflated_sharpe_ratio(
                sr_stats["sharpe"], sr_stats["n_observations"],
                sr_stats["skewness"], sr_stats["kurtosis"],
                n_trials=len(self.skip_variants),
            )
            dsr_global = deflated_sharpe_ratio(
                sr_stats["sharpe"], sr_stats["n_observations"],
                sr_stats["skewness"], sr_stats["kurtosis"],
                n_trials=_N_TESTS_GLOBAL,
            )

            per_variant[skip] = {
                "wf_sharpe_mean": wf["aggregate"]["sharpe_mean"],
                "wf_pct_positive": wf["aggregate"]["sharpe_pct_positive"],
                "wf_max_dd": wf["aggregate"]["max_dd_worst"],
                "bootstrap_ci_95": boot["sharpe_ci_95"],
                "bootstrap_p_le_zero": boot["p_value_sharpe_le_zero"],
                "dsr_local": dsr_local["dsr"],
                "dsr_global": dsr_global["dsr"],
                "dsr_threshold": dsr_global["sharpe_threshold"],
                "dsr_verdict": dsr_global["verdict"],
                "per_fold": wf["per_fold"],
                "pass": dsr_global["verdict"] == "PASS",
            }

        passing = [s for s, v in per_variant.items() if v.get("pass", False)]
        best = max(
            candidates,
            key=lambda s: per_variant[s].get("wf_sharpe_mean", -999),
        ) if candidates else None

        result = {
            "per_variant": per_variant,
            "best_variant": best,
            "surviving_variants": passing,
            "pass": len(passing) > 0,
        }
        self.results["level_B"] = result
        return result

    # ── Level C — Sanity Checks ────────────────────────────────────────────────

    def run_level_C(self) -> dict:
        """
        Sanity checks on the best variant from Level B.

        Runs: adjacent-asset replication (on ADA/AVAX/DOT/LINK/MATIC),
        shuffle null test (50 shuffles), and OOS decade check (cutoff 2023-01-01).
        Verdict PASS if at least 2 of 3 checks pass.

        Returns
        -------
        dict
            adjacent_asset, shuffle_null, oos_decade: individual check dicts.
            n_pass: int (0–3), pass: bool (≥ 2/3).
        """
        prices_core = self._get_prices()
        level_b = self.results.get("level_B", {})
        best_skip = level_b.get("best_variant", 0)

        def best_signal_func(p: pd.DataFrame) -> pd.DataFrame:
            return self._compute_signal_with_skip(p, skip=best_skip)

        # Adjacent assets: load separately (may fail on some tickers)
        try:
            prices_all = load_strategy_a_universe(
                start="2018-01-01",
                end=str(date.today()),
                tickers=self.universe_tickers + STRATEGY_A_ADJACENT,
            )
            prices_main, prices_adj = split_universe(
                prices_all, self.universe_tickers, STRATEGY_A_ADJACENT
            )
        except Exception:
            prices_main = prices_core
            prices_adj = pd.DataFrame()

        # --- Check 1: adjacent asset replication ---
        if prices_adj.empty or prices_adj.shape[1] < 2:
            check_adjacent = {
                "sharpe_main": np.nan, "sharpe_adjacent": np.nan,
                "correlation": np.nan, "verdict": "FAIL", "note": "adjacent data unavailable",
            }
        else:
            check_adjacent = adjacent_asset_replication(
                best_signal_func, prices_main, prices_adj
            )

        # --- Check 2: shuffle null test ---
        check_shuffle = shuffle_null_test(best_signal_func, prices_core, n_shuffles=50)

        # --- Check 3: OOS decade check ---
        check_decade = oos_decade_check(
            best_signal_func, prices_core, cutoff_date="2023-01-01"
        )

        verdicts = [
            check_adjacent["verdict"] == "PASS",
            check_shuffle["verdict"] == "PASS",
            check_decade["verdict"] == "PASS",
        ]
        n_pass = sum(verdicts)

        result = {
            "best_variant_skip": best_skip,
            "adjacent_asset": check_adjacent,
            "shuffle_null": check_shuffle,
            "oos_decade": check_decade,
            "n_pass": n_pass,
            "pass": n_pass >= 2,
        }
        self.results["level_C"] = result
        return result

    # ── Report ─────────────────────────────────────────────────────────────────

    def generate_report(self) -> str:
        """
        Generate a markdown feasibility report summarising all three levels.

        Returns
        -------
        str
            Full markdown text of the report.
        """
        source_name = self.promising_md_path.split("/")[-1]
        run_date = str(date.today())

        # Determine overall verdict
        level_a = self.results.get("level_A", {})
        level_b = self.results.get("level_B", {})
        level_c = self.results.get("level_C", {})

        if not level_a.get("pass", False):
            overall = "FAIL"
            recommendation = (
                "Do NOT modify Strategy A signal. "
                "Skip-month IC improvement is non-significant on crypto TSMOM (24/7 markets). "
                "The current 28-day window ending at t-1 remains appropriate. "
                "This FAIL is a useful null result confirming no microstructure bias in crypto. "
                "No n_tests increment required if hypothesis was pre-registered."
            )
        elif not level_b.get("pass", False):
            overall = "FAIL"
            recommendation = (
                "IC test borderline PASS but backtest DSR FAIL. "
                "Skip-month adjustment does not survive multiple-testing correction. "
                "Do not deploy as Strategy A modification."
            )
        elif not level_c.get("pass", False):
            overall = "CONDITIONAL_PASS"
            recommendation = (
                "Strategy passes IC and WF gates but fails sanity checks. "
                "Investigate which check failed before deploying. "
                "Consider paper-trading for 60 days to accumulate live IC evidence."
            )
        else:
            overall = "PASS"
            best = level_b.get("best_variant", 0)
            recommendation = (
                f"Skip={best} variant passes all three levels. "
                f"Counts as modification #1 of Strategy A (max 3). "
                f"Validate on Strategy A propfirm account before incrementing n_tests."
            )

        lines: list[str] = [
            f"# Feasibility Report: Skip-Month Hypothesis",
            f"",
            f"**Date**: {run_date}",
            f"**Source**: `{source_name}`",
            f"**Handler**: SkipMonthHandler",
            f"**Universe**: {', '.join(self.universe_tickers)}",
            f"**Overall Verdict**: **{overall}**",
            f"",
            f"---",
            f"",
            f"## Niveau A — IC Feasibility Gate",
            f"",
        ]

        if level_a:
            lines.append("| Skip | Mean IC | t_HAC | n_dates |")
            lines.append("|------|---------|-------|---------|")
            for skip, v in level_a.get("variants", {}).items():
                lines.append(
                    f"| skip={skip} | {v['mean_ic']:.4f} | "
                    f"{v['t_hac']:.3f} | {v['n_dates']} |"
                )
            lines.append("")
            lines.append("**Delta-IC gates (vs baseline skip=0):**")
            lines.append("")
            lines.append("| Skip | delta_IC | t_HAC(delta) | Verdict |")
            lines.append("|------|----------|--------------|---------|")
            for skip, g in level_a.get("gate_results", {}).items():
                lines.append(
                    f"| skip={skip} | {g['delta_ic_mean']:.4f} | "
                    f"{g['t_hac']:.3f} | {g['verdict']} |"
                )
            lines.append("")
            lines.append(
                f"**Level A Verdict**: {'✅ PASS' if level_a.get('pass') else '❌ FAIL'} "
                f"— Surviving variants: {level_a.get('surviving_variants', [])}"
            )
        else:
            lines.append("*(Level A not run)*")

        lines += ["", "---", "", "## Niveau B — Walk-Forward Backtest", ""]

        if level_b:
            lines.append("| Skip | Sharpe_OOS | Pct_positive | MaxDD | Bootstrap p≤0 | DSR_global | Verdict |")
            lines.append("|------|------------|-------------|-------|--------------|------------|---------|")
            for skip, v in level_b.get("per_variant", {}).items():
                if "error" in v:
                    lines.append(f"| skip={skip} | ERROR | — | — | — | — | FAIL |")
                    continue
                ci = v.get("bootstrap_ci_95", (np.nan, np.nan))
                lines.append(
                    f"| skip={skip} "
                    f"| {v.get('wf_sharpe_mean', np.nan):.3f} "
                    f"| {v.get('wf_pct_positive', np.nan):.0%} "
                    f"| {v.get('wf_max_dd', np.nan):.1%} "
                    f"| {v.get('bootstrap_p_le_zero', np.nan):.3f} "
                    f"| {v.get('dsr_global', np.nan):.3f} "
                    f"| {v.get('dsr_verdict', '—')} |"
                )
            lines.append("")
            # Per-fold detail for best variant
            best = level_b.get("best_variant")
            if best is not None and best in level_b.get("per_variant", {}):
                lines.append(f"**Per-fold detail (skip={best}):**")
                lines.append("")
                lines.append("| Fold | Start | End | Sharpe | MaxDD |")
                lines.append("|------|-------|-----|--------|-------|")
                for f in level_b["per_variant"][best].get("per_fold", []):
                    lines.append(
                        f"| {f['fold']} | {f['start']} | {f['end']} "
                        f"| {f['sharpe']:.3f} | {f['max_dd']:.1%} |"
                    )
            lines.append("")
            lines.append(
                f"**Level B Verdict**: {'✅ PASS' if level_b.get('pass') else '❌ FAIL'} "
                f"(DSR threshold ≈ {next(iter(level_b.get('per_variant', {}).values()), {}).get('dsr_threshold', '—'):.2f} "
                f"at n_trials={_N_TESTS_GLOBAL})"
            )
        else:
            lines.append("*(Level B not run — Level A FAIL)*")

        lines += ["", "---", "", "## Niveau C — Sanity Checks", ""]

        if level_c:
            adj = level_c.get("adjacent_asset", {})
            shuf = level_c.get("shuffle_null", {})
            dec = level_c.get("oos_decade", {})
            lines += [
                f"**Best variant tested**: skip={level_c.get('best_variant_skip', '—')}",
                "",
                "| Check | Key Metric | Verdict |",
                "|-------|-----------|---------|",
                f"| Adjacent asset | SR_main={adj.get('sharpe_main', np.nan):.3f} "
                f"/ SR_adj={adj.get('sharpe_adjacent', np.nan):.3f} | {adj.get('verdict', '—')} |",
                f"| Shuffle null | percentile={shuf.get('percentile_real', np.nan):.2f} "
                f"(SR_real={shuf.get('sharpe_real', np.nan):.3f} "
                f"vs shuffled μ={shuf.get('sharpe_shuffle_mean', np.nan):.3f}) | {shuf.get('verdict', '—')} |",
                f"| OOS decade | SR_pre={dec.get('sharpe_pre', np.nan):.3f} "
                f"/ SR_post={dec.get('sharpe_post', np.nan):.3f} | {dec.get('verdict', '—')} |",
                "",
                f"**Level C Verdict**: {'✅ PASS' if level_c.get('pass') else '❌ FAIL'} "
                f"({level_c.get('n_pass', 0)}/3 checks passed)",
            ]
        else:
            lines.append("*(Level C not run — Level B FAIL)*")

        lines += [
            "",
            "---",
            "",
            "## Recommendation",
            "",
            recommendation,
            "",
            f"---",
            f"*Generated by SkipMonthHandler · n_tests_global={_N_TESTS_GLOBAL}*",
        ]

        return "\n".join(lines)
