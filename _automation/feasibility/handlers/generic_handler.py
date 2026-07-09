"""
Fallback handler for hypotheses not matched by any specialised handler.
Always classify() = True (last in HANDLER_REGISTRY).

Three categories (checked in order):
  NON_TESTABLE     : meta-framework / methodology change → REQUIRES_HUMAN
  COMPLEX          : ML / regime infrastructure required → REQUIRES_HUMAN
  TESTABLE_GENERIC : momentum-adjacent signal → generic 28d TSMOM baseline
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from .base import HypothesisHandler
from ..data.loaders import (
    PriceDataUnavailable,
    STRATEGY_A_FULL_UNIVERSE,
    load_strategy_a_universe,
    split_universe,
)
from ..stats.backtest_wf import compute_pnl, vol_target_positions, walk_forward_backtest
from ..stats.bootstrap import stationary_bootstrap_sharpe
from ..stats.dsr import compute_sharpe_stats, deflated_sharpe_ratio
from ..stats.sanity_checks import adjacent_asset_replication, oos_decade_check, shuffle_null_test

_N_TESTS_GLOBAL: int = 274

# Module-level price cache: all GenericHandler instances share the same universe
_PRICES_CACHE: pd.DataFrame | None = None

NON_TESTABLE_PATTERNS: list[str] = [
    r"stress.?test.{0,20}framework",
    r"effective.{0,10}number.{0,10}(?:of.{0,10})?test",
    r"backtests? lie",
    r"overfitting and parameter selection",
    r"backtest overfitting",
    r"data.?snooping",
    r"deflated sharpe.{0,30}recalibrat",
    r"AMTP.{0,30}correction",
    r"multiple.testing correction",
    r"conformal prediction",
    r"harmonic synthetic",
    r"synthetic control method",
    r"double.?descent",
    r"heavy tails and predictive ability",
    r"macroeconomic forecasting road test",
    r"monetary policy.*media spotlight",
    r"quantifying the risk.return tradeoff",
    r"self.normalized tests.*multistep",
    r"tweedie.s formula",
    r"agentic workflow",
    r"LLM.{0,20}regime label",
    r"ask hn.*algorithmic trading",
    r"yc w\d{2}.*search and feed",
    r"homepage",
    r"century without data.*reconstructing",
    r"a day is now what a decade",
    r"for the love of the game",
    r"research review.*prediction market",
    r"beyond the backtest.*algorithmic adv",
    r"how to break.*sentiment model",
    r"sentiment is not one signal",
    r"i paper traded.*strategies.*real",
    r"tradelock.*new site",
    r"quant mashup",
    r"the currency you didn.t choose",
    r"martyn tinsley",
    r"bad month for your strategy.*should you change",
    r"lazy prices.*lazy investors",
    r"100 club.*2000 tech vs.*ai",
]

COMPLEX_PATTERNS: list[str] = [
    r"hidden markov",
    r"markov switching",
    r"random forest",
    r"neural network",
    r"reinforcement learning",
    r"transformer",
    r"LightGBM|LGB\b",
    r"SAGA.{0,20}sequence.adaptive",
    r"deep learning",
    r"unsupervised learning",
    r"k.?means|PCA clustering",
    r"regime.adaptive",
    r"regime.{0,10}detect",
    r"implied volatility.{0,30}surface",
    r"volatility surface",
    r"vol surface",
    r"risk parity",
    r"tactical asset allocation|TAA\b",
    r"GTAA\b|global tactical",
    r"dual momentum.{0,30}ETF|dual momentum.{0,30}GTAA",
    r"commodity.{0,10}futures.{0,10}(?:since|returns|index)",
    r"cointegrat",
    r"statistical arbitrage",
    r"active.*dual momentum",
    r"equity.curve.{0,20}trend.follow|trend.follow.{0,20}equity.curve",
    r"curve trades.{0,20}macro",
    r"modeling asymmetric volatility",
    r"volatility risk premium",
    r"volatility derivatives.*VIX",
    r"prediction market.*who profit",
    r"attention factor.*connect.*crypto",
    r"dynamic capital allocation.*markov",
    r"emerging market.*reconstruct",
    r"active hedge.*EUR",
    r"risk.weight|risk.?weighted portfolio",
    r"integrating ai.*quantitative trading",
    r"retrospective simulation",
    r"beyond 60.?40",
    r"commodity portfolio.*2026",
    r"gold.{0,20}bond.*dual momentum|dual momentum.*gold",
]


class GenericHandler(HypothesisHandler):
    """Fallback for hypotheses not covered by specialised handlers."""

    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        return True

    def __init__(self, promising_md_path: str) -> None:
        super().__init__(promising_md_path)
        self._category: str | None = None

    def _get_prices(self) -> pd.DataFrame:
        global _PRICES_CACHE
        if _PRICES_CACHE is None:
            _PRICES_CACHE = load_strategy_a_universe(
                start="2018-01-01",
                end=str(date.today()),
                tickers=STRATEGY_A_FULL_UNIVERSE,
            )
        return _PRICES_CACHE

    def _categorize_hypothesis(self) -> tuple[str, list[str]]:
        """
        Read the .md and classify as NON_TESTABLE, COMPLEX, or TESTABLE_GENERIC.

        Returns (category, matched_patterns).
        """
        try:
            text = open(self.promising_md_path, encoding="utf-8").read()
        except OSError:
            return "NON_TESTABLE", ["file_read_error"]

        matched_non = [p for p in NON_TESTABLE_PATTERNS if re.search(p, text, re.IGNORECASE)]
        if matched_non:
            return "NON_TESTABLE", matched_non

        matched_complex = [p for p in COMPLEX_PATTERNS if re.search(p, text, re.IGNORECASE)]
        if matched_complex:
            return "COMPLEX", matched_complex

        return "TESTABLE_GENERIC", []

    def _generic_signal(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Standard 28-day TSMOM baseline (skip=0, same as Strategy A)."""
        log_ret = np.log(prices / prices.shift(1))
        cum_ret = log_ret.rolling(28).sum()
        vol_l = log_ret.rolling(28).std() * np.sqrt(28)
        sig = np.tanh(cum_ret / (vol_l + 1e-8)).clip(lower=0.0)
        sig[cum_ret.isna()] = np.nan
        return sig

    # ── Level A ────────────────────────────────────────────────────────────────

    def run_level_A(self) -> dict:
        """
        Categorise the hypothesis, then act:
          NON_TESTABLE / COMPLEX → REQUIRES_HUMAN (no price loading)
          TESTABLE_GENERIC → run generic 28d TSMOM baseline on 14-asset universe.
        Gate: baseline Sharpe > 0.3 (full sample, costs 0.17% RT).
        """
        category, matched = self._categorize_hypothesis()
        self._category = category

        if category in ("NON_TESTABLE", "COMPLEX"):
            reason = (
                "Meta-framework or methodology change — not a directly testable signal hypothesis."
                if category == "NON_TESTABLE"
                else "Requires ML/regime infrastructure not present in current pipeline."
            )
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": category,
                "reason": reason,
                "matched_patterns": matched,
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        # TESTABLE_GENERIC
        try:
            prices = self._get_prices()
            sig = self._generic_signal(prices)
            pos = vol_target_positions(sig, prices, vol_target_annual=0.10)
            pnl_df = compute_pnl(pos, prices, cost_per_side=0.00085)
            pnl_port = pnl_df.sum(axis=1).dropna()

            if len(pnl_port) < 30 or pnl_port.std() == 0:
                baseline_sharpe = np.nan
            else:
                baseline_sharpe = float((pnl_port.mean() / pnl_port.std()) * np.sqrt(252))
        except Exception as exc:
            # Distinguish a data outage (sandbox 403 / no cache) from a real
            # strategy failure — the orchestrator must not count the former as FAIL_A.
            result = {
                "verdict": "FAIL_GENERIC",
                "category": category,
                "baseline_sharpe": np.nan,
                "error": str(exc),
                "data_unavailable": isinstance(exc, PriceDataUnavailable),
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        passed = not np.isnan(baseline_sharpe) and baseline_sharpe > 0.3
        result = {
            "verdict": "PASS_GENERIC" if passed else "FAIL_GENERIC",
            "category": category,
            "baseline_sharpe": float(baseline_sharpe) if not np.isnan(baseline_sharpe) else np.nan,
            "n_days": len(pnl_port),
            "note": (
                "Generic 28d TSMOM baseline tested on full 14-asset Strategy A universe. "
                "Specific hypothesis variant not implemented — requires dedicated handler."
            ),
            "pass": passed,
        }
        self.results["level_A"] = result
        return result

    # ── Level B ────────────────────────────────────────────────────────────────

    def run_level_B(self) -> dict:
        """Walk-forward + DSR on generic baseline. Skipped if Level A = REQUIRES_HUMAN/FAIL."""
        level_a = self.results.get("level_A", {})
        if level_a.get("verdict") in ("REQUIRES_HUMAN", "FAIL_GENERIC"):
            result = {
                "pass": False,
                "skipped": True,
                "reason": "Level A did not produce a testable signal",
            }
            self.results["level_B"] = result
            return result

        prices = self._get_prices()
        try:
            wf = walk_forward_backtest(self._generic_signal, prices)
        except Exception as exc:
            result = {"pass": False, "error": str(exc)}
            self.results["level_B"] = result
            return result

        pnl_oos = wf["pnl_oos"]
        if isinstance(pnl_oos, pd.DataFrame):
            pnl_oos = pnl_oos.sum(axis=1)
        pnl_oos_port = pnl_oos.dropna()

        boot = stationary_bootstrap_sharpe(pnl_oos_port, n_resamples=500)
        sr_stats = compute_sharpe_stats(pnl_oos_port)
        dsr_global = deflated_sharpe_ratio(
            sr_stats["sharpe"], sr_stats["n_observations"],
            sr_stats["skewness"], sr_stats["kurtosis"],
            n_trials=_N_TESTS_GLOBAL,
        )

        result = {
            "wf_sharpe_mean": wf["aggregate"]["sharpe_mean"],
            "wf_pct_positive": wf["aggregate"]["sharpe_pct_positive"],
            "wf_max_dd": wf["aggregate"]["max_dd_worst"],
            "bootstrap_ci_95": boot["sharpe_ci_95"],
            "bootstrap_p_le_zero": boot["p_value_sharpe_le_zero"],
            "dsr_global": dsr_global["dsr"],
            "dsr_threshold": dsr_global["sharpe_threshold"],
            "dsr_verdict": dsr_global["verdict"],
            "per_fold": wf["per_fold"],
            "pass": dsr_global["verdict"] == "PASS",
        }
        self.results["level_B"] = result
        return result

    # ── Level C ────────────────────────────────────────────────────────────────

    def run_level_C(self) -> dict:
        """Sanity checks on generic baseline. Skipped if Level A = REQUIRES_HUMAN/FAIL."""
        level_a = self.results.get("level_A", {})
        if level_a.get("verdict") in ("REQUIRES_HUMAN", "FAIL_GENERIC"):
            result = {
                "pass": False,
                "skipped": True,
                "reason": "Level A did not produce a testable signal",
            }
            self.results["level_C"] = result
            return result

        prices_full = self._get_prices()
        _CORE = ["BTC-USD", "ETH-USD", "SOL-USD"]
        _EXTENDED = [t for t in prices_full.columns if t not in _CORE]

        try:
            prices_main, prices_adj = split_universe(prices_full, _CORE, _EXTENDED)
        except Exception:
            prices_main = prices_full
            prices_adj = pd.DataFrame()

        def sig_func(p: pd.DataFrame) -> pd.DataFrame:
            return self._generic_signal(p)

        if prices_adj.empty or prices_adj.shape[1] < 2:
            check_adjacent = {
                "sharpe_main": np.nan, "sharpe_adjacent": np.nan,
                "correlation": np.nan, "verdict": "FAIL",
                "note": "adjacent data unavailable",
            }
        else:
            check_adjacent = adjacent_asset_replication(sig_func, prices_main, prices_adj)

        check_shuffle = shuffle_null_test(sig_func, prices_full, n_shuffles=50)
        check_decade = oos_decade_check(sig_func, prices_full, cutoff_date="2023-01-01")

        n_pass = sum([
            check_adjacent["verdict"] == "PASS",
            check_shuffle["verdict"] == "PASS",
            check_decade["verdict"] == "PASS",
        ])

        result = {
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
        source_name = self.promising_md_path.split("/")[-1]
        run_date = str(date.today())
        level_a = self.results.get("level_A", {})
        level_b = self.results.get("level_B", {})
        level_c = self.results.get("level_C", {})

        verdict_a = level_a.get("verdict", "—")
        category = level_a.get("category", "UNKNOWN")
        is_rh = verdict_a == "REQUIRES_HUMAN"

        if is_rh:
            overall = "REQUIRES_HUMAN"
        elif not level_a.get("pass", False):
            overall = "FAIL"
        elif not level_b.get("pass", False):
            overall = "FAIL"
        elif not level_c.get("pass", False):
            overall = "CONDITIONAL_PASS"
        else:
            overall = "PASS"

        lines: list[str] = [
            "# Feasibility Report: Generic Handler",
            "",
            f"**Date**: {run_date}",
            f"**Source**: `{source_name}`",
            "**Handler**: GenericHandler",
            f"**Category**: {category}",
            f"**Overall Verdict**: **{overall}**",
            "",
            "---",
            "",
            "## Niveau A — Hypothesis Classification",
            "",
        ]

        if is_rh:
            matched = level_a.get("matched_patterns", [])
            if category == "NON_TESTABLE":
                handler_suggestion = (
                    "This is a **methodology / meta-framework** hypothesis. "
                    "Review manually to decide if it applies to an existing strategy. "
                    "No dedicated handler needed unless reformulated as a testable signal."
                )
            else:
                handler_suggestion = (
                    "This is a **complex model** hypothesis (ML / regime / multi-asset). "
                    "A dedicated handler would need to wrap the model in a `signal_func` "
                    "with proper train/predict splits within each WF fold to avoid look-ahead."
                )
            lines += [
                f"**Verdict**: REQUIRES_HUMAN",
                f"**Reason**: {level_a.get('reason', '—')}",
                "",
                "**Matched patterns**:",
                *[f"- `{p}`" for p in matched],
                "",
                f"**Recommended action**: {handler_suggestion}",
            ]
        elif level_a:
            bs = level_a.get("baseline_sharpe", np.nan)
            n_days = level_a.get("n_days", 0)
            bs_str = f"{bs:.3f}" if not np.isnan(bs) else "n/a"
            lines += [
                "**Category**: TESTABLE_GENERIC",
                "**Gate**: baseline Sharpe > 0.3 (generic 28d TSMOM, 14 assets, costs 0.17% RT)",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Baseline Sharpe (full sample) | {bs_str} |",
                f"| n_days | {n_days} |",
                "",
                f"*{level_a.get('note', '')}*",
                "",
                f"**Level A Verdict**: {'✅ PASS_GENERIC' if level_a.get('pass') else '❌ FAIL_GENERIC'}",
            ]
        else:
            lines.append("*(Level A not run)*")

        lines += ["", "---", "", "## Niveau B — Walk-Forward Backtest", ""]

        if level_b and not level_b.get("skipped"):
            lines += [
                "| Metric | Value |",
                "|--------|-------|",
                f"| Sharpe_OOS | {level_b.get('wf_sharpe_mean', np.nan):.3f} |",
                f"| Pct_positive | {level_b.get('wf_pct_positive', np.nan):.0%} |",
                f"| MaxDD | {level_b.get('wf_max_dd', np.nan):.1%} |",
                f"| Bootstrap p≤0 | {level_b.get('bootstrap_p_le_zero', np.nan):.3f} |",
                f"| DSR_global | {level_b.get('dsr_global', np.nan):.3f} |",
                f"| DSR_threshold | {level_b.get('dsr_threshold', np.nan):.3f} |",
                "",
                f"**Level B Verdict**: {'✅ PASS' if level_b.get('pass') else '❌ FAIL'}",
            ]
        elif is_rh:
            lines.append("*(Level B skipped — REQUIRES_HUMAN)*")
        else:
            lines.append("*(Level B not run — Level A FAIL)*")

        lines += ["", "---", "", "## Niveau C — Sanity Checks", ""]

        if level_c and not level_c.get("skipped"):
            adj = level_c.get("adjacent_asset", {})
            shuf = level_c.get("shuffle_null", {})
            dec = level_c.get("oos_decade", {})
            adj_main = adj.get("sharpe_main", np.nan)
            adj_adj = adj.get("sharpe_adjacent", np.nan)
            lines += [
                "| Check | Key Metric | Verdict |",
                "|-------|-----------|---------|",
                f"| Adjacent asset | SR_main={adj_main:.3f} / SR_adj={adj_adj:.3f} | {adj.get('verdict', '—')} |",
                f"| Shuffle null | percentile={shuf.get('percentile_real', np.nan):.2f} "
                f"(SR_real={shuf.get('sharpe_real', np.nan):.3f} "
                f"vs shuffled μ={shuf.get('sharpe_shuffle_mean', np.nan):.3f}) | {shuf.get('verdict', '—')} |",
                f"| OOS decade | SR_pre={dec.get('sharpe_pre', np.nan):.3f} "
                f"/ SR_post={dec.get('sharpe_post', np.nan):.3f} | {dec.get('verdict', '—')} |",
                "",
                f"**Level C Verdict**: {'✅ PASS' if level_c.get('pass') else '❌ FAIL'} "
                f"({level_c.get('n_pass', 0)}/3 checks passed)",
            ]
        elif is_rh:
            lines.append("*(Level C skipped — REQUIRES_HUMAN)*")
        else:
            lines.append("*(Level C not run)*")

        lines += ["", "---", "", "## Recommendation", ""]

        if is_rh:
            lines += [
                f"**REQUIRES_HUMAN** — {level_a.get('reason', '')}",
                "",
                handler_suggestion,
            ]
        elif overall == "PASS":
            lines.append(
                "Generic 28d TSMOM baseline passes all gates. "
                "Build a dedicated handler to test the specific hypothesis variant "
                "before claiming n_tests increment."
            )
        elif overall == "CONDITIONAL_PASS":
            lines.append(
                "Passes P&L and WF gates but fails ≥2/3 sanity checks. "
                "Investigate which check failed before building a dedicated handler."
            )
        else:
            lines.append(
                "Generic momentum baseline FAIL. "
                "The hypothesis likely does not translate to a momentum improvement "
                "on the Strategy A universe without a specialised implementation."
            )

        lines += [
            "",
            "---",
            f"*Generated by GenericHandler · n_tests_global={_N_TESTS_GLOBAL}*",
        ]

        return "\n".join(lines)
