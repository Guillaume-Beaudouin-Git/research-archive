"""
Handler for regime-filter hypotheses on the Strategy A TSMOM signal.

Approach (daily-level, reuses backtest_wf infrastructure):
  A regime filter is an OVERLAY: it multiplies the existing TSMOM signal by a
  0/1 mask derived from a market-regime classifier. We test three a-priori
  (NON-optimised) regime definitions so there is no threshold look-ahead:

      vol_low  : trade only when BTC realised vol (28d) is below a FIXED level
      trend_up : trade only when BTC is above its 100d moving average
      combined : both conditions simultaneously

  Because the regime mask is computed INSIDE the signal_func, walk_forward_backtest
  recomputes it per-fold on data up to the fold end — no forward leakage.

Constitutional guard (L15):
  "Regime overlays on high-Sharpe strategies (SR>1.0) produce sub-threshold lift.
   Only valuable for SR<0.7 strategies with conditional DD clustering."
  Strategy A baseline SR ~1.33. The handler measures the baseline SR and, if
  SR>1.0, states explicitly that any lift is expected to be marginal — while
  still running the test to prove or refute it on data.

Gates mirror SkipMonthHandler:
  Level A : per-regime full-sample Sharpe vs baseline; delta_SR>0.1 AND paired
            bootstrap p(delta<=0)<0.05. PLUS the L15 advisory.
  Level B : walk-forward + stationary bootstrap + DSR (global n_tests) on the
            regime variants that survive A. Regime recomputed in-fold.
  Level C : adjacent-asset / shuffle-null / OOS-decade sanity checks + a
            regime-stability check (switch frequency must be low: a filter that
            flips daily just churns costs).

Out of scope -> REQUIRES_HUMAN:
  - HMM / ML-classifier regimes (need in-fold model fitting; not a fixed rule).
  - Non-Strategy-A targets (NQ / FX) — different data, separate handler.
  - Import failure of the research stack.
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from .base import HypothesisHandler
from ..data.loaders import (
    STRATEGY_A_FULL_UNIVERSE,
    load_strategy_a_universe,
    split_universe,
)
from ..stats.backtest_wf import compute_pnl, vol_target_positions, walk_forward_backtest
from ..stats.bootstrap import bootstrap_pnl_difference, stationary_bootstrap_sharpe
from ..stats.dsr import compute_sharpe_stats, deflated_sharpe_ratio
from ..stats.sanity_checks import (
    adjacent_asset_replication,
    oos_decade_check,
    shuffle_null_test,
)

_N_TESTS_GLOBAL: int = 274

# Regime definitions tested (fixed a-priori parameters; NOT optimised).
_REGIMES: list[str] = ["vol_low", "trend_up", "combined"]

# A-priori thresholds. Chosen from economic priors, not fitted to the sample.
_VOL_LOOKBACK = 28           # realised-vol window (matches Strategy A)
_VOL_ANNUAL_THRESHOLD = 0.80  # BTC ann. realised vol below 80% = "calm" regime
_TREND_MA = 100              # 100-day MA for the trend filter

# Classification patterns.
_REGIME_PATTERNS: list[str] = [
    r"regime.adaptive",
    r"regime.detect",
    r"detect.{0,10}regime",
    r"regime.filter",
    r"regime.{0,15}signal",
    r"regimes?\b",
    r"market regime",
    r"hidden markov|markov switching|\bHMM\b",
    r"VIX threshold",
    r"VIX.{0,10}filter",
    r"vol.{0,12}regime|regime.{0,12}vol",
    r"trend.{0,10}filter|trend.?following.{0,10}filter",
    r"risk.?on.?risk.?off|risk on / risk off",
    r"bull.{0,5}bear.{0,10}filter",
    r"only trade.{0,20}when",
    r"conditional on.{0,20}regime",
]

# Patterns that force REQUIRES_HUMAN even if regime-classified.
_HMM_PATTERNS: list[str] = [
    r"hidden markov",
    r"markov switching",
    r"HMM\b",
    r"neural|LSTM|transformer|random forest|XGBoost|gradient boost",
    r"unsupervised|k.?means|cluster",
]
# Strategy-A scope markers (else REQUIRES_HUMAN: other assets need other data).
_NON_A_PATTERNS: list[str] = [
    r"\bNQ\b", r"nasdaq", r"S&P|SPX|ES future",
    r"\bFX\b|forex|EUR.?USD|currency",
    r"equit(y|ies)\b", r"treasury|bond\b",
]


class RegimeFilterHandler(HypothesisHandler):
    """Regime-overlay tester on the Strategy A TSMOM signal (daily-level)."""

    universe_tickers: list[str] = STRATEGY_A_FULL_UNIVERSE

    # ----------------------------------------------------------------- #
    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        try:
            text = open(promising_md_path, encoding="utf-8").read()
        except OSError:
            return False
        return any(re.search(p, text, re.IGNORECASE) for p in _REGIME_PATTERNS)

    # ----------------------------------------------------------------- #
    def __init__(self, promising_md_path: str) -> None:
        super().__init__(promising_md_path)
        self._prices: pd.DataFrame | None = None
        self._text: str = ""

    def _read(self) -> str:
        if not self._text:
            try:
                self._text = open(self.promising_md_path, encoding="utf-8").read()
            except OSError:
                self._text = ""
        return self._text

    def _get_prices(self) -> pd.DataFrame:
        if self._prices is None:
            self._prices = load_strategy_a_universe(
                start="2018-01-01",
                end=str(date.today()),
                tickers=self.universe_tickers,
            )
        return self._prices

    # ----------------------------------------------------------------- #
    # Signal + regime overlay
    # ----------------------------------------------------------------- #
    @staticmethod
    def _tsmom_signal(prices: pd.DataFrame, lookback: int = 28) -> pd.DataFrame:
        """Strategy A baseline TSMOM (skip=0), same formula as SkipMonthHandler."""
        log_ret = np.log(prices / prices.shift(1))
        cum_ret = log_ret.rolling(lookback).sum()
        vol_l = log_ret.rolling(lookback).std() * np.sqrt(lookback)
        sig = np.tanh(cum_ret / (vol_l + 1e-8)).clip(lower=0.0)
        sig[cum_ret.isna()] = np.nan
        return sig

    @staticmethod
    def _regime_mask(prices: pd.DataFrame, regime: str) -> pd.DataFrame:
        """
        Build a 0/1 regime mask (date x asset), aligned to prices.

        The regime is driven by BTC (the crypto market beta) and broadcast to all
        assets — a market-wide risk-on/off switch, not a per-asset one. All stats
        use only past data (rolling / shift) so the mask is causal.
        """
        if "BTC-USD" in prices.columns:
            btc = prices["BTC-USD"]
        else:
            # Fallback: equal-weight basket as market proxy.
            btc = prices.mean(axis=1)

        log_ret_btc = np.log(btc / btc.shift(1))

        if regime == "vol_low":
            realised = log_ret_btc.rolling(_VOL_LOOKBACK).std() * np.sqrt(365)
            cond = (realised < _VOL_ANNUAL_THRESHOLD)
        elif regime == "trend_up":
            ma = btc.rolling(_TREND_MA).mean()
            cond = (btc > ma)
        elif regime == "combined":
            realised = log_ret_btc.rolling(_VOL_LOOKBACK).std() * np.sqrt(365)
            ma = btc.rolling(_TREND_MA).mean()
            cond = (realised < _VOL_ANNUAL_THRESHOLD) & (btc > ma)
        else:
            cond = pd.Series(True, index=prices.index)

        mask_1d = cond.astype(float)  # 1.0 in-regime, 0.0 out
        # Broadcast the market-wide mask across every asset column.
        mask = pd.DataFrame(
            np.repeat(mask_1d.values[:, None], prices.shape[1], axis=1),
            index=prices.index,
            columns=prices.columns,
        )
        return mask

    def _signal_with_regime(self, prices: pd.DataFrame, regime: str) -> pd.DataFrame:
        """TSMOM signal gated by the regime mask (overlay)."""
        base = self._tsmom_signal(prices)
        if regime == "baseline":
            return base
        mask = self._regime_mask(prices, regime)
        return base * mask

    @staticmethod
    def _switch_frequency(prices: pd.DataFrame, mask_1d: pd.Series) -> float:
        """Fraction of days on which the regime flips (proxy for churn cost)."""
        m = mask_1d.dropna()
        if len(m) < 2:
            return float("nan")
        return float((m.diff().abs() > 0).mean())

    # ----------------------------------------------------------------- #
    # L15 advisory
    # ----------------------------------------------------------------- #
    def _l15_advisory(self, baseline_sharpe: float) -> str:
        if np.isnan(baseline_sharpe):
            return "Baseline SR could not be computed; L15 advisory not applicable."
        if baseline_sharpe > 1.0:
            return (
                f"L15 WARNING: baseline SR={baseline_sharpe:.2f} > 1.0. Regime overlays "
                "on high-Sharpe strategies historically produce sub-threshold lift. "
                "A positive delta here should be treated with extra scepticism and is "
                "unlikely to justify the added complexity unless DD clustering improves "
                "materially."
            )
        if baseline_sharpe < 0.7:
            return (
                f"L15: baseline SR={baseline_sharpe:.2f} < 0.7 — this is the regime where "
                "overlays CAN add value if DD clustering is conditional. Worth testing."
            )
        return (
            f"L15: baseline SR={baseline_sharpe:.2f} in the 0.7-1.0 grey zone. Lift "
            "possible but modest; judge on DD reduction, not Sharpe alone."
        )

    # ----------------------------------------------------------------- #
    # Level A
    # ----------------------------------------------------------------- #
    def run_level_A(self) -> dict:
        text = self._read()

        # HMM / ML regime → REQUIRES_HUMAN (need in-fold model fitting).
        if any(re.search(p, text, re.IGNORECASE) for p in _HMM_PATTERNS):
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "REGIME_FILTER",
                "reason": (
                    "Regime defined via HMM / ML classifier. Requires a model fitted "
                    "strictly in-sample within each WF fold (no look-ahead); the fixed-"
                    "threshold overlay path does not apply. Manual implementation needed."
                ),
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        # Non-Strategy-A target → REQUIRES_HUMAN (different data).
        if any(re.search(p, text, re.IGNORECASE) for p in _NON_A_PATTERNS):
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "REGIME_FILTER",
                "reason": (
                    "Regime hypothesis targets a non-Strategy-A asset (NQ / FX / equity / "
                    "bond). This handler only overlays regimes on the crypto TSMOM signal. "
                    "Manual analysis required for other asset classes."
                ),
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        prices = self._get_prices()

        # Baseline + each regime, full-sample P&L.
        variant_pnl: dict[str, pd.Series] = {}
        variant_metrics: dict[str, dict] = {}

        for name in ["baseline"] + _REGIMES:
            sig = self._signal_with_regime(prices, name)
            pos = vol_target_positions(sig, prices, vol_target_annual=0.10)
            pnl_df = compute_pnl(pos, prices, cost_per_side=0.00085)
            pnl_port = pnl_df.sum(axis=1).dropna()
            if len(pnl_port) < 30 or pnl_port.std() == 0:
                sharpe = np.nan
            else:
                sharpe = float((pnl_port.mean() / pnl_port.std()) * np.sqrt(252))
            variant_pnl[name] = pnl_port
            variant_metrics[name] = {"sharpe": sharpe, "n_days": len(pnl_port)}

        baseline_sharpe = variant_metrics["baseline"]["sharpe"]
        l15 = self._l15_advisory(baseline_sharpe)

        # Delta-Sharpe gate per regime.
        surviving: list[str] = []
        gate: dict[str, dict] = {}
        for name in _REGIMES:
            v = variant_metrics[name]["sharpe"]
            delta = (v - baseline_sharpe) if not np.isnan(v) else np.nan
            boot = bootstrap_pnl_difference(
                variant_pnl["baseline"], variant_pnl[name], n_resamples=500
            )
            p_val = boot["p_value_le_zero"]
            if np.isnan(delta) or delta <= 0.1:
                verdict = "FAIL_DELTA"
            elif p_val >= 0.05:
                verdict = "FAIL_BOOTSTRAP"
            else:
                verdict = "PASS"
            gate[name] = {
                "sharpe_variant": float(v) if not np.isnan(v) else np.nan,
                "delta_sharpe": float(delta) if not np.isnan(delta) else np.nan,
                "bootstrap_p_le_zero": float(p_val),
                "verdict": verdict,
            }
            if verdict == "PASS":
                surviving.append(name)

        result = {
            "verdict": "PASS" if surviving else "FAIL",
            "category": "REGIME_FILTER",
            "variants": variant_metrics,
            "baseline_sharpe": float(baseline_sharpe) if not np.isnan(baseline_sharpe) else np.nan,
            "gate_results": gate,
            "surviving_variants": surviving,
            "l15_advisory": l15,
            "pass": len(surviving) > 0,
        }
        self.results["level_A"] = result
        return result

    # ----------------------------------------------------------------- #
    # Level B
    # ----------------------------------------------------------------- #
    def run_level_B(self) -> dict:
        la = self.results.get("level_A", {})
        if la.get("verdict") == "REQUIRES_HUMAN" or not la.get("pass"):
            result = {"pass": False, "skipped": True,
                      "reason": "Level A REQUIRES_HUMAN or no surviving regime"}
            self.results["level_B"] = result
            return result

        prices = self._get_prices()
        candidates = la.get("surviving_variants", [])
        per_variant: dict[str, dict] = {}

        for name in candidates:
            def make_fn(rname: str):
                def signal_func(p: pd.DataFrame) -> pd.DataFrame:
                    return self._signal_with_regime(p, rname)
                return signal_func

            try:
                wf = walk_forward_backtest(make_fn(name), prices)
            except Exception as exc:
                per_variant[name] = {"error": str(exc), "pass": False}
                continue

            pnl_oos = wf["pnl_oos"]
            if isinstance(pnl_oos, pd.DataFrame):
                pnl_oos = pnl_oos.sum(axis=1)
            pnl_oos = pnl_oos.dropna()

            boot = stationary_bootstrap_sharpe(pnl_oos, n_resamples=500)
            sr_stats = compute_sharpe_stats(pnl_oos)
            dsr_global = deflated_sharpe_ratio(
                sr_stats["sharpe"], sr_stats["n_observations"],
                sr_stats["skewness"], sr_stats["kurtosis"],
                n_trials=_N_TESTS_GLOBAL,
            )
            per_variant[name] = {
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

        passing = [n for n, v in per_variant.items() if v.get("pass")]
        best = max(candidates, key=lambda n: per_variant[n].get("wf_sharpe_mean", -999)) \
            if candidates else None
        result = {
            "per_variant": per_variant,
            "best_variant": best,
            "surviving_variants": passing,
            "pass": len(passing) > 0,
        }
        self.results["level_B"] = result
        return result

    # ----------------------------------------------------------------- #
    # Level C
    # ----------------------------------------------------------------- #
    def run_level_C(self) -> dict:
        lb = self.results.get("level_B", {})
        if lb.get("skipped") or not lb.get("pass"):
            result = {"pass": False, "skipped": True, "reason": "Level B not PASS"}
            self.results["level_C"] = result
            return result

        prices_full = self._get_prices()
        best = lb.get("best_variant", "baseline")

        def best_fn(p: pd.DataFrame) -> pd.DataFrame:
            return self._signal_with_regime(p, best)

        _CORE = ["BTC-USD", "ETH-USD", "SOL-USD"]
        _EXT = [t for t in prices_full.columns if t not in _CORE]
        try:
            prices_main, prices_adj = split_universe(prices_full, _CORE, _EXT)
        except Exception:
            prices_main, prices_adj = prices_full, pd.DataFrame()

        if prices_adj.empty or prices_adj.shape[1] < 2:
            check_adjacent = {"sharpe_main": np.nan, "sharpe_adjacent": np.nan,
                              "correlation": np.nan, "verdict": "FAIL",
                              "note": "adjacent data unavailable"}
        else:
            check_adjacent = adjacent_asset_replication(best_fn, prices_main, prices_adj)

        check_shuffle = shuffle_null_test(best_fn, prices_full, n_shuffles=50)
        check_decade = oos_decade_check(best_fn, prices_full, cutoff_date="2023-01-01")

        # Regime-stability check: the mask must not flip too often (cost churn).
        mask_1d = self._regime_mask(prices_full, best).iloc[:, 0]
        switch_freq = self._switch_frequency(prices_full, mask_1d)
        in_regime_frac = float(mask_1d.dropna().mean())
        # Stable if it switches on < 10% of days AND trades at least 20% of the time.
        stability_ok = (
            not np.isnan(switch_freq) and switch_freq < 0.10 and in_regime_frac >= 0.20
        )

        n_pass = sum([
            check_adjacent["verdict"] == "PASS",
            check_shuffle["verdict"] == "PASS",
            check_decade["verdict"] == "PASS",
            stability_ok,
        ])
        result = {
            "best_variant": best,
            "adjacent_asset": check_adjacent,
            "shuffle_null": check_shuffle,
            "oos_decade": check_decade,
            "regime_switch_frequency": switch_freq,
            "in_regime_fraction": in_regime_frac,
            "regime_stability_pass": bool(stability_ok),
            "n_pass": n_pass,
            "pass": n_pass >= 3,  # 3 of 4 (added stability check)
        }
        self.results["level_C"] = result
        return result

    # ----------------------------------------------------------------- #
    # Report
    # ----------------------------------------------------------------- #
    def generate_report(self) -> str:
        src = self.promising_md_path.split("/")[-1]
        run_date = str(date.today())
        la = self.results.get("level_A", {})
        lb = self.results.get("level_B", {})
        lc = self.results.get("level_C", {})

        is_rh = la.get("verdict") == "REQUIRES_HUMAN"
        if is_rh:
            overall = "REQUIRES_HUMAN"
        elif not la.get("pass"):
            overall = "FAIL"
        elif not lb.get("pass"):
            overall = "FAIL"
        elif not lc.get("pass"):
            overall = "CONDITIONAL_PASS"
        else:
            overall = "PASS"

        L: list[str] = [
            "# Feasibility Report: Regime Filter Handler (Strategy A)",
            "",
            f"**Date**: {run_date}",
            f"**Source**: `{src}`",
            "**Handler**: RegimeFilterHandler",
            "**Category**: REGIME_FILTER",
            f"**Overall Verdict**: **{overall}**",
            "",
            "---",
            "",
            "## Niveau A — Regime Overlay Gate",
            "",
        ]

        if is_rh:
            L += ["**Verdict**: REQUIRES_HUMAN", f"**Reason**: {la.get('reason', '—')}"]
        elif la:
            L += [
                "**Gate**: per-regime Sharpe > baseline + 0.1 AND paired bootstrap p(Δ≤0) < 0.05",
                f"**Regimes tested (fixed a-priori thresholds)**: {', '.join(_REGIMES)}",
                f"  - vol_low: BTC ann. realised vol (28d) < {_VOL_ANNUAL_THRESHOLD:.0%}",
                f"  - trend_up: BTC > {_TREND_MA}d MA",
                "  - combined: both",
                "",
                "**Full-sample Sharpe (vol-targeted, costs 0.17% RT):**",
                "",
                "| Variant | Sharpe | n_days |",
                "|---------|--------|--------|",
            ]
            for name, v in la.get("variants", {}).items():
                tag = " ← baseline" if name == "baseline" else ""
                sr = v.get("sharpe", np.nan)
                L.append(f"| {name}{tag} | {sr:.3f} | {v.get('n_days', 0)} |")
            L += [
                "",
                "**Delta-Sharpe gates (vs baseline):**",
                "",
                "| Regime | Sharpe | ΔSharpe | Bootstrap p(Δ≤0) | Verdict |",
                "|--------|--------|---------|------------------|---------|",
            ]
            for name, g in la.get("gate_results", {}).items():
                L.append(
                    f"| {name} | {g.get('sharpe_variant', np.nan):.3f} "
                    f"| {g.get('delta_sharpe', np.nan):+.3f} "
                    f"| {g.get('bootstrap_p_le_zero', np.nan):.3f} "
                    f"| {g.get('verdict', '—')} |"
                )
            L += [
                "",
                f"> {la.get('l15_advisory', '')}",
                "",
                f"**Level A Verdict**: {'✅ PASS' if la.get('pass') else '❌ FAIL'} "
                f"— Surviving: {la.get('surviving_variants', [])}",
            ]

        L += ["", "---", "", "## Niveau B — Walk-Forward + DSR", ""]
        if lb and not lb.get("skipped"):
            L += [
                "| Regime | Sharpe_OOS | Pct_pos | MaxDD | Boot p≤0 | DSR_global | Verdict |",
                "|--------|------------|---------|-------|----------|------------|---------|",
            ]
            for name, v in lb.get("per_variant", {}).items():
                if "error" in v:
                    L.append(f"| {name} | ERROR | — | — | — | — | FAIL |")
                    continue
                L.append(
                    f"| {name} | {v.get('wf_sharpe_mean', np.nan):.3f} "
                    f"| {v.get('wf_pct_positive', np.nan):.0%} "
                    f"| {v.get('wf_max_dd', np.nan):.1%} "
                    f"| {v.get('bootstrap_p_le_zero', np.nan):.3f} "
                    f"| {v.get('dsr_global', np.nan):.3f} "
                    f"| {v.get('dsr_verdict', '—')} |"
                )
            L += ["", f"**Level B Verdict**: {'✅ PASS' if lb.get('pass') else '❌ FAIL'}"]
        elif is_rh:
            L.append("*(Level B skipped — REQUIRES_HUMAN)*")
        else:
            L.append("*(Level B skipped — Level A FAIL)*")

        L += ["", "---", "", "## Niveau C — Sanity + Regime Stability", ""]
        if lc and not lc.get("skipped"):
            adj = lc.get("adjacent_asset", {})
            shuf = lc.get("shuffle_null", {})
            dec = lc.get("oos_decade", {})
            L += [
                f"**Best regime**: {lc.get('best_variant', '—')}",
                "",
                "| Check | Key Metric | Verdict |",
                "|-------|-----------|---------|",
                f"| Adjacent asset | SR_main={adj.get('sharpe_main', np.nan):.3f} / "
                f"SR_adj={adj.get('sharpe_adjacent', np.nan):.3f} | {adj.get('verdict', '—')} |",
                f"| Shuffle null | pct={shuf.get('percentile_real', np.nan):.2f} | {shuf.get('verdict', '—')} |",
                f"| OOS decade | SR_pre={dec.get('sharpe_pre', np.nan):.3f} / "
                f"SR_post={dec.get('sharpe_post', np.nan):.3f} | {dec.get('verdict', '—')} |",
                f"| Regime stability | switch={lc.get('regime_switch_frequency', np.nan):.1%}/day, "
                f"in-regime={lc.get('in_regime_fraction', np.nan):.0%} | "
                f"{'PASS' if lc.get('regime_stability_pass') else 'FAIL'} |",
                "",
                f"**Level C Verdict**: {'✅ PASS' if lc.get('pass') else '❌ FAIL'} "
                f"({lc.get('n_pass', 0)}/4 checks passed)",
            ]
        elif is_rh:
            L.append("*(Level C skipped — REQUIRES_HUMAN)*")
        else:
            L.append("*(Level C skipped — Level B FAIL)*")

        L += ["", "---", "", "## Recommendation", ""]
        if is_rh:
            L.append(f"**REQUIRES_HUMAN** — {la.get('reason', '')}")
        elif overall == "PASS":
            best = lb.get("best_variant", "—")
            L.append(
                f"Regime overlay '{best}' passes all gates AND survives the L15 scepticism "
                "(lift is real on OOS + DSR). Counts as one modification toward the L10 cap "
                "of 3 on Strategy A. Validate on the propfirm account before incrementing n_tests. "
                "Re-read the L15 advisory above before committing."
            )
        elif overall == "CONDITIONAL_PASS":
            L.append(
                "Passes A+B but fails sanity/stability. Most likely the regime switches too "
                "often (cost churn) or fails OOS-decade. Inspect before promoting."
            )
        else:
            L.append(
                "No regime overlay beats the Strategy A baseline at matched leverage with "
                "bootstrap significance. Consistent with L15: regime overlays on a SR>1.0 "
                "strategy produce sub-threshold lift. Do not modify Strategy A. No n_tests "
                "increment needed beyond logging this as a tested-and-rejected family."
            )

        L += ["", "---", f"*Generated by RegimeFilterHandler · n_tests_global={_N_TESTS_GLOBAL}*"]
        return "\n".join(L)
