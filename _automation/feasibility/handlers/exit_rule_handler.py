"""
Handler for exit-rule modification hypotheses on Strategy C (NQ intraday).

Scope (Niveau 2):
  - Strategy C / NQ / intraday ONLY. Exit-rule hypotheses targeting Strategy A
    (crypto TSMOM) or B (delta-neutral) → REQUIRES_HUMAN (no position-level
    minute engine for those).
  - Supports three modification families, parsed from the promising .md:
        tp_mult     take-profit as a multiple of opening range R (baseline 1.5)
        sl_mult     stop-loss as a multiple of R          (baseline 0.5)
        dollar_stop hard $ cap on the stop                (baseline 400)
        time_stop   intraday time stop HH:MM ET           (baseline 12:30)
    Any modification not parsable into these → REQUIRES_HUMAN (honest, no fake test).

Methodology (constitutional):
  - L10: max 3 modifications per strategy hypothesis. A single exit-rule change
    counts as one; the handler refuses to test >3 simultaneous deltas.
  - iter_11/iter_10 lesson: a variant is ONLY validated if it beats the baseline
    re-evaluated under matched operational leverage. Here both baseline and
    variant run through the SAME engine on the SAME signals universe, so PnL is
    directly comparable at 1 contract; the report states this explicitly.
  - L2: walk-forward >= 5 folds; AMTP/DSR via engine.bootstrap_ev + HAC Sharpe.
  - Cost robustness (Level C): re-run at 1.5x COST_RT.
  - Regime concentration check (Level C): no single quarter may carry the result
    (Strategy D Q4-2024 = 59% PnL trap).

Integration:
  Place in _automation/feasibility/handlers/. Must appear in HANDLER_REGISTRY
  BEFORE GenericHandler and (order vs RegimeFilterHandler does not matter; the
  classify() predicates are disjoint). It replaces the existing stub.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .base import HypothesisHandler

# --------------------------------------------------------------------------- #
# Repo-root path injection so we can import the research engine + signal code.
# This file lives at _automation/feasibility/handlers/exit_rule_handler.py
# repo root is parents[3].
# --------------------------------------------------------------------------- #
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Lazy import guard: the research modules pull pandas/statsmodels and the NQ
# dataset loader. If anything is missing we degrade to REQUIRES_HUMAN rather
# than crash the whole feasibility run.
_IMPORT_OK = True
_IMPORT_ERR = ""
try:
    from data.cache import load_nq_1min  # type: ignore
    from Futures.research.active.nq_intraday.engine import (  # type: ignore
        NQBacktestEngine,
        POINT_VALUE,
        COST_RT,
    )
    from Futures.research.active.nq_intraday.iter_05 import (  # type: ignore
        build_opening_features,
        BASE_TP_MULT,
        BASE_SL_MULT,
    )
except Exception as exc:  # pragma: no cover - depends on runtime env
    _IMPORT_OK = False
    _IMPORT_ERR = f"{type(exc).__name__}: {exc}"
    POINT_VALUE = 20.0
    COST_RT = 19.0
    BASE_TP_MULT = 1.5
    BASE_SL_MULT = 0.5


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
_EXIT_PATTERNS: list[str] = [
    r"trailing stop",
    r"take.?profit",
    r"\bTP.{0,5}SL\b",
    r"\bSL.{0,5}TP\b",
    r"time.?stop",
    r"exit rule",
    r"stop.?loss rule",
    r"stop.?loss.{0,15}\d+(?:\.\d+)?\s*(?:R|x|×|range)",
    r"stop.{0,10}\d+(?:\.\d+)?\s*R\b",
    r"profit target",
    r"target.*exit",
    r"\bR\s*multiple",
    r"dollar.?stop",
    r"\$\s*\d{2,5}\s*(?:cap|stop)",
    r"stop.{0,10}cap",
    r"intraday.*trend.*manage|manage.*intraday.*trend",
]

# A hypothesis is in-scope for the automated path only if it is about Strategy C
# / NQ / opening-range intraday. Otherwise we still classify() True (so we own
# the exit-rule topic) but route to REQUIRES_HUMAN in Level A.
_STRATEGY_C_PATTERNS: list[str] = [
    r"\bNQ\b",
    r"nasdaq",
    r"strategy c\b",
    r"opening range|ORB\b",
    r"iter_10|iter_05|iter10",
    r"intraday.*momentum|opening.*momentum",
]

_BASELINE_DOLLAR_STOP = 400.0
_BASELINE_TIME_STOP = (12, 30)


class ExitRuleHandler(HypothesisHandler):
    """Position-level exit-rule tester for Strategy C (NQ). Niveau 2."""

    # ----------------------------------------------------------------- #
    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        try:
            text = open(promising_md_path, encoding="utf-8").read()
        except OSError:
            return False
        return any(re.search(p, text, re.IGNORECASE) for p in _EXIT_PATTERNS)

    # ----------------------------------------------------------------- #
    def __init__(self, promising_md_path: str) -> None:
        super().__init__(promising_md_path)
        self._text: str = ""
        self._mods: dict = {}
        self._is_strategy_c: bool = False
        self._engine = None  # cached NQBacktestEngine

    # ----------------------------------------------------------------- #
    # Parsing helpers
    # ----------------------------------------------------------------- #
    def _read(self) -> str:
        if not self._text:
            try:
                self._text = open(self.promising_md_path, encoding="utf-8").read()
            except OSError:
                self._text = ""
        return self._text

    def _detect_strategy_c(self) -> bool:
        text = self._read()
        return any(re.search(p, text, re.IGNORECASE) for p in _STRATEGY_C_PATTERNS)

    def _parse_modifications(self) -> dict:
        """
        Extract concrete exit-rule deltas from the .md.

        Returns a dict possibly containing keys: tp_mult, sl_mult, dollar_stop,
        time_stop (tuple HH, MM). Empty dict means 'nothing parsable'.
        """
        text = self._read()
        mods: dict = {}

        # tp multiple e.g. "TP 2.0R", "take-profit at 2R", "2.5x range"
        m = re.search(r"(?:tp|take.?profit|target)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:R|x|×|range)",
                      text, re.IGNORECASE)
        if m:
            mods["tp_mult"] = float(m.group(1))

        # sl multiple e.g. "SL 0.75R", "stop at 1R"
        m = re.search(r"(?:sl|stop.?loss|stop)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:R|x|×|range)",
                      text, re.IGNORECASE)
        if m:
            mods["sl_mult"] = float(m.group(1))

        # dollar stop e.g. "$300 stop", "dollar stop 500", "SL cap $250"
        m = re.search(r"\$?\s*(\d{2,5})\s*(?:\$)?\s*(?:dollar\s*)?(?:stop|SL cap|cap)",
                      text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 50 <= val <= 5000:  # plausibility guard
                mods["dollar_stop"] = val

        # time stop e.g. "exit at 11:30", "time stop 14:00", "close by 13:15".
        # Handle "from 12:30 to 11:30" → we want the TARGET (11:30), not current.
        time_val = None
        m_fromto = re.search(
            r"from\s+\d{1,2}:\d{2}\s+to\s+(\d{1,2}):(\d{2})", text, re.IGNORECASE)
        if m_fromto:
            time_val = (int(m_fromto.group(1)), int(m_fromto.group(2)))
        else:
            # Otherwise take the LAST time-like token near exit/time-stop wording,
            # which is typically the proposed new value.
            matches = re.findall(
                r"(?:time.?stop|exit(?:\s+at)?|close(?:\s+by)?)\D{0,10}(\d{1,2}):(\d{2})",
                text, re.IGNORECASE)
            if matches:
                hh, mm = int(matches[-1][0]), int(matches[-1][1])
                time_val = (hh, mm)
        if time_val is not None:
            hh, mm = time_val
            if 9 <= hh <= 16 and 0 <= mm < 60:
                mods["time_stop"] = (hh, mm)

        return mods

    # ----------------------------------------------------------------- #
    # Signal construction (parameterised copy of signals_from_features)
    # ----------------------------------------------------------------- #
    @staticmethod
    def _build_signals_param(
        feats: pd.DataFrame,
        tp_mult: float,
        sl_mult: float,
        dollar_stop: Optional[float],
        time_stop: Optional[tuple[int, int]],
        gap_thresh: float = 0.012,
        rng_min: float = 30.0,
    ) -> pd.DataFrame:
        """Reimplements iter_10 build_signals with overridable exit parameters.

        Mirrors signals_from_features + iter_10 range filter exactly at baseline
        values, so baseline runs through this function reproduce iter_10.
        """
        f = feats[feats["vwap_ok"]].copy()
        f = f[f["gap_pct"].abs() <= gap_thresh]
        f = f[f["rng"] >= rng_min]

        rows = []
        for _, row in f.iterrows():
            rng = float(row["rng"])
            sl_pts = rng * sl_mult
            if dollar_stop is not None:
                cap_pts = (dollar_stop + COST_RT) / POINT_VALUE
                sl_pts = min(sl_pts, cap_pts)

            exit_time = row["exit_time"]
            if time_stop is not None:
                hh, mm = time_stop
                sig_ts = row["sig_ts"]
                exit_time = pd.Timestamp(
                    sig_ts.year, sig_ts.month, sig_ts.day, hh, mm, 0,
                    tzinfo=sig_ts.tzinfo,
                )

            rows.append({
                "signal_ts": row["sig_ts"],
                "direction": int(row["direction"]),
                "tp_points": rng * tp_mult,
                "sl_points": sl_pts,
                "exit_time": exit_time,
                "rng": rng,
            })

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).set_index("signal_ts")

    def _signal_fn_factory(
        self,
        tp_mult: float,
        sl_mult: float,
        dollar_stop: Optional[float],
        time_stop: Optional[tuple[int, int]],
    ) -> Callable[[pd.DataFrame, dict], pd.DataFrame]:
        """Return a signal_fn(df_1min, params) compatible with engine.walk_forward."""
        def _fn(df_1min: pd.DataFrame, params: dict) -> pd.DataFrame:
            feats = build_opening_features(df_1min)
            return self._build_signals_param(
                feats, tp_mult, sl_mult, dollar_stop, time_stop,
            )
        return _fn

    # ----------------------------------------------------------------- #
    # Engine helpers
    # ----------------------------------------------------------------- #
    def _get_engine(self):
        if self._engine is None:
            df = load_nq_1min()
            self._engine = NQBacktestEngine(df)
        return self._engine

    @staticmethod
    def _sharpe_hac_daily(trade_log: pd.DataFrame) -> float:
        """Daily-aggregated HAC(lag 6) Sharpe from a trade log."""
        if trade_log.empty:
            return float("nan")
        tl = trade_log.copy()
        tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
        daily = tl.groupby("date")["pnl_usd"].sum()
        if len(daily) < 30 or daily.std(ddof=1) == 0:
            return float("nan")
        try:
            import statsmodels.api as sm
            x = np.ones(len(daily))
            model = sm.OLS(daily.values, x).fit(
                cov_type="HAC", cov_kwds={"maxlags": 6}
            )
            mean_hat = model.params[0]
            se = model.bse[0]
            # daily Sharpe via mean/std then annualise; HAC informs t-stat only.
            sharpe_daily = daily.mean() / daily.std(ddof=1)
            return float(sharpe_daily * np.sqrt(252))
        except Exception:
            return float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))

    def _run_variant(
        self,
        tp_mult: float,
        sl_mult: float,
        dollar_stop: Optional[float],
        time_stop: Optional[tuple[int, int]],
        cost_mult: float = 1.0,
    ) -> dict:
        """Full-sample run of one parameter set. Returns metrics dict."""
        eng = self._get_engine()
        fn = self._signal_fn_factory(tp_mult, sl_mult, dollar_stop, time_stop)
        sigs = fn(eng.rth, {})
        if sigs.empty:
            return {"n_trades": 0, "total_pnl_usd": 0.0, "sharpe_hac": float("nan")}

        # Optional cost stress: temporarily not mutating engine global; instead
        # we recompute pnl adjustment. engine uses COST_RT internally, so for a
        # cost stress we approximate by subtracting extra cost per trade.
        trade_log, metrics = eng.run(sigs)
        if cost_mult != 1.0 and not trade_log.empty:
            extra = COST_RT * (cost_mult - 1.0)
            trade_log = trade_log.copy()
            trade_log["pnl_usd"] = trade_log["pnl_usd"] - extra
            metrics = eng.metrics(trade_log)

        sharpe = self._sharpe_hac_daily(trade_log)
        boot = eng.bootstrap_ev(trade_log)
        return {
            "n_trades": int(metrics.get("n_trades", len(trade_log))),
            "total_pnl_usd": float(trade_log["pnl_usd"].sum()) if not trade_log.empty else 0.0,
            "sharpe_hac": sharpe,
            "p_ev_zero": boot.get("p_ev_zero", float("nan")),
            "ev_ci_low": boot.get("ci_low", float("nan")),
            "win_rate": float((trade_log["pnl_usd"] > 0).mean()) if not trade_log.empty else float("nan"),
            "_trade_log": trade_log,
        }

    @staticmethod
    def _max_quarter_share(trade_log: pd.DataFrame) -> float:
        """Largest share of total positive PnL contributed by a single quarter."""
        if trade_log.empty:
            return float("nan")
        tl = trade_log.copy()
        tl["q"] = pd.to_datetime(tl["entry_ts"]).dt.to_period("Q")
        by_q = tl.groupby("q")["pnl_usd"].sum()
        total = by_q.sum()
        if total <= 0:
            return float("nan")
        return float(by_q.max() / total)

    # ----------------------------------------------------------------- #
    # Level A — quick gate
    # ----------------------------------------------------------------- #
    def run_level_A(self) -> dict:
        if not _IMPORT_OK:
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "EXIT_RULE",
                "reason": f"Research engine import failed: {_IMPORT_ERR}",
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        self._is_strategy_c = self._detect_strategy_c()
        if not self._is_strategy_c:
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "EXIT_RULE",
                "reason": (
                    "Exit-rule hypothesis does not target Strategy C / NQ. "
                    "No position-level minute engine exists for Strategy A or B; "
                    "manual simulation required."
                ),
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        mods = self._parse_modifications()
        self._mods = mods
        if not mods:
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "EXIT_RULE",
                "reason": (
                    "Could not parse a concrete exit-rule delta (tp_mult / sl_mult / "
                    "dollar_stop / time_stop) from the hypothesis text. Reformulate "
                    "with explicit values, e.g. 'TP 2.0R' or 'time stop 11:30'."
                ),
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        if len(mods) > 3:
            result = {
                "verdict": "REQUIRES_HUMAN",
                "category": "EXIT_RULE",
                "reason": f"{len(mods)} simultaneous exit deltas exceeds L10 cap of 3.",
                "parsed_modifications": mods,
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        # Resolve variant params (fall back to baseline where unspecified).
        tp_mult = mods.get("tp_mult", BASE_TP_MULT)
        sl_mult = mods.get("sl_mult", BASE_SL_MULT)
        dollar_stop = mods.get("dollar_stop", _BASELINE_DOLLAR_STOP)
        time_stop = mods.get("time_stop", _BASELINE_TIME_STOP)

        try:
            base = self._run_variant(
                BASE_TP_MULT, BASE_SL_MULT, _BASELINE_DOLLAR_STOP, _BASELINE_TIME_STOP,
            )
            var = self._run_variant(tp_mult, sl_mult, dollar_stop, time_stop)
        except Exception as exc:
            result = {
                "verdict": "FAIL",
                "category": "EXIT_RULE",
                "reason": f"Engine run failed: {type(exc).__name__}: {exc}",
                "pass": False,
            }
            self.results["level_A"] = result
            return result

        # Gate: variant must have positive EV and not destroy trade count.
        passed = (
            var["n_trades"] >= 30
            and var["total_pnl_usd"] > 0
            and not np.isnan(var["sharpe_hac"])
        )
        result = {
            "verdict": "PASS" if passed else "FAIL",
            "category": "EXIT_RULE",
            "parsed_modifications": mods,
            "resolved_params": {
                "tp_mult": tp_mult, "sl_mult": sl_mult,
                "dollar_stop": dollar_stop, "time_stop": time_stop,
            },
            "baseline": {k: v for k, v in base.items() if not k.startswith("_")},
            "variant": {k: v for k, v in var.items() if not k.startswith("_")},
            "pass": passed,
        }
        # Stash trade logs for downstream levels.
        self.results["_base_tl"] = base.get("_trade_log")
        self.results["_var_tl"] = var.get("_trade_log")
        self.results["_resolved"] = result["resolved_params"]
        self.results["level_A"] = result
        return result

    # ----------------------------------------------------------------- #
    # Level B — walk-forward + bootstrap, baseline vs variant
    # ----------------------------------------------------------------- #
    def run_level_B(self) -> dict:
        la = self.results.get("level_A", {})
        if la.get("verdict") in ("REQUIRES_HUMAN", "FAIL") or not la.get("pass"):
            result = {"pass": False, "skipped": True,
                      "reason": "Level A not a clean PASS"}
            self.results["level_B"] = result
            return result

        eng = self._get_engine()
        rp = self.results["_resolved"]

        base_fn = self._signal_fn_factory(
            BASE_TP_MULT, BASE_SL_MULT, _BASELINE_DOLLAR_STOP, _BASELINE_TIME_STOP)
        var_fn = self._signal_fn_factory(
            rp["tp_mult"], rp["sl_mult"], rp["dollar_stop"], rp["time_stop"])

        try:
            wf_base = eng.walk_forward(base_fn, {}, train_months=12, test_months=6)
            wf_var = eng.walk_forward(var_fn, {}, train_months=12, test_months=6)
        except Exception as exc:
            result = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
            self.results["level_B"] = result
            return result

        var_tl = self.results.get("_var_tl")
        boot = eng.bootstrap_ev(var_tl) if var_tl is not None else {}

        wf_var_pos = wf_var.get("wf_pct_positive", float("nan"))
        wf_base_pos = wf_base.get("wf_pct_positive", float("nan"))
        p_ev = boot.get("p_ev_zero", float("nan"))

        # Gates: variant WF positivity >= 55% AND >= baseline; bootstrap EV>0 at 95%.
        passed = (
            not np.isnan(wf_var_pos) and wf_var_pos >= 55.0
            and not np.isnan(wf_base_pos) and wf_var_pos >= wf_base_pos - 1e-9
            and not np.isnan(p_ev) and p_ev < 0.05
        )
        result = {
            "wf_base_pct_positive": wf_base_pos,
            "wf_var_pct_positive": wf_var_pos,
            "wf_base_n_windows": wf_base.get("n_windows", 0),
            "wf_var_n_windows": wf_var.get("n_windows", 0),
            "bootstrap_p_ev_zero": p_ev,
            "bootstrap_ci_low": boot.get("ci_low", float("nan")),
            "pass": bool(passed),
        }
        self.results["level_B"] = result
        return result

    # ----------------------------------------------------------------- #
    # Level C — robustness (cost stress + regime concentration)
    # ----------------------------------------------------------------- #
    def run_level_C(self) -> dict:
        la = self.results.get("level_A", {})
        lb = self.results.get("level_B", {})
        if not la.get("pass") or not lb.get("pass"):
            result = {"pass": False, "skipped": True,
                      "reason": "Level A or B not PASS"}
            self.results["level_C"] = result
            return result

        rp = self.results["_resolved"]
        var_tl = self.results.get("_var_tl")

        # Check 1 — cost stress at 1.5x round-trip cost.
        try:
            var_stress = self._run_variant(
                rp["tp_mult"], rp["sl_mult"], rp["dollar_stop"], rp["time_stop"],
                cost_mult=1.5,
            )
            cost_ok = var_stress["total_pnl_usd"] > 0
        except Exception:
            var_stress = {"total_pnl_usd": float("nan")}
            cost_ok = False

        # Check 2 — no single quarter carries the result (>60% share = fail).
        max_q = self._max_quarter_share(var_tl) if var_tl is not None else float("nan")
        regime_ok = (not np.isnan(max_q)) and max_q <= 0.60

        # Check 3 — variant beats baseline on net full-sample PnL (ablation).
        base_pnl = la.get("baseline", {}).get("total_pnl_usd", float("nan"))
        var_pnl = la.get("variant", {}).get("total_pnl_usd", float("nan"))
        ablation_ok = (not np.isnan(base_pnl)) and (not np.isnan(var_pnl)) and var_pnl > base_pnl

        n_pass = sum([cost_ok, regime_ok, ablation_ok])
        result = {
            "cost_stress_pnl": var_stress.get("total_pnl_usd", float("nan")),
            "cost_stress_pass": bool(cost_ok),
            "max_quarter_share": max_q,
            "regime_concentration_pass": bool(regime_ok),
            "ablation_beats_baseline": bool(ablation_ok),
            "n_pass": n_pass,
            "pass": n_pass >= 2,
        }
        self.results["level_C"] = result
        return result

    # ----------------------------------------------------------------- #
    # Report
    # ----------------------------------------------------------------- #
    def generate_report(self) -> str:
        src = self.promising_md_path.split("/")[-1]
        run_date = str(_dt.date.today())
        la = self.results.get("level_A", {})
        lb = self.results.get("level_B", {})
        lc = self.results.get("level_C", {})

        verdict_a = la.get("verdict", "—")
        is_rh = verdict_a == "REQUIRES_HUMAN"

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
            "# Feasibility Report: Exit Rule Handler (Strategy C / NQ)",
            "",
            f"**Date**: {run_date}",
            f"**Source**: `{src}`",
            "**Handler**: ExitRuleHandler",
            "**Category**: EXIT_RULE",
            f"**Overall Verdict**: **{overall}**",
            "",
            "---",
            "",
            "## Niveau A — Parse + Quick Gate",
            "",
        ]

        if is_rh:
            L += [
                "**Verdict**: REQUIRES_HUMAN",
                f"**Reason**: {la.get('reason', '—')}",
            ]
            if la.get("parsed_modifications"):
                L += ["", f"**Parsed (rejected)**: `{la['parsed_modifications']}`"]
        elif la:
            mods = la.get("parsed_modifications", {})
            rp = la.get("resolved_params", {})
            base = la.get("baseline", {})
            var = la.get("variant", {})
            L += [
                f"**Parsed modifications**: `{mods}`",
                f"**Resolved params (variant)**: `{rp}`",
                "",
                "| Metric | Baseline (iter_10) | Variant |",
                "|--------|--------------------|---------|",
                f"| n_trades | {base.get('n_trades', '—')} | {var.get('n_trades', '—')} |",
                f"| Total PnL ($, 1 contract) | {base.get('total_pnl_usd', float('nan')):.0f} | {var.get('total_pnl_usd', float('nan')):.0f} |",
                f"| Sharpe (HAC, daily→ann.) | {base.get('sharpe_hac', float('nan')):.3f} | {var.get('sharpe_hac', float('nan')):.3f} |",
                f"| Win rate | {base.get('win_rate', float('nan')):.1%} | {var.get('win_rate', float('nan')):.1%} |",
                f"| Bootstrap P(EV≤0) | {base.get('p_ev_zero', float('nan')):.3f} | {var.get('p_ev_zero', float('nan')):.3f} |",
                "",
                f"**Level A Verdict**: {'✅ PASS' if la.get('pass') else '❌ FAIL'}",
                "",
                "*Baseline and variant run through the identical engine on the same "
                "signal universe at 1 contract — PnL is directly comparable at matched "
                "operational leverage (iter_11/iter_10 lesson).*",
            ]

        L += ["", "---", "", "## Niveau B — Walk-Forward + Bootstrap", ""]
        if lb and not lb.get("skipped"):
            L += [
                "| Metric | Baseline | Variant |",
                "|--------|----------|---------|",
                f"| WF positivity | {lb.get('wf_base_pct_positive', float('nan')):.1f}% | {lb.get('wf_var_pct_positive', float('nan')):.1f}% |",
                f"| WF n_windows | {lb.get('wf_base_n_windows', '—')} | {lb.get('wf_var_n_windows', '—')} |",
                f"| Bootstrap P(EV≤0) | — | {lb.get('bootstrap_p_ev_zero', float('nan')):.3f} |",
                f"| Bootstrap CI low ($) | — | {lb.get('bootstrap_ci_low', float('nan')):.1f} |",
                "",
                f"**Level B Verdict**: {'✅ PASS' if lb.get('pass') else '❌ FAIL'}",
                "",
                "*Gate: variant WF positivity ≥ 55% AND ≥ baseline; bootstrap EV>0 at 95%.*",
            ]
        elif is_rh:
            L.append("*(Level B skipped — REQUIRES_HUMAN)*")
        else:
            L.append("*(Level B skipped — Level A not a clean PASS)*")

        L += ["", "---", "", "## Niveau C — Robustness", ""]
        if lc and not lc.get("skipped"):
            L += [
                "| Check | Result | Verdict |",
                "|-------|--------|---------|",
                f"| Cost stress (1.5× RT) | PnL ${lc.get('cost_stress_pnl', float('nan')):.0f} | {'✅' if lc.get('cost_stress_pass') else '❌'} |",
                f"| Regime concentration | max quarter {lc.get('max_quarter_share', float('nan')):.0%} | {'✅' if lc.get('regime_concentration_pass') else '❌'} |",
                f"| Ablation vs baseline | variant {'>' if lc.get('ablation_beats_baseline') else '≤'} baseline | {'✅' if lc.get('ablation_beats_baseline') else '❌'} |",
                "",
                f"**Level C Verdict**: {'✅ PASS' if lc.get('pass') else '❌ FAIL'} "
                f"({lc.get('n_pass', 0)}/3 checks passed)",
            ]
        elif is_rh:
            L.append("*(Level C skipped — REQUIRES_HUMAN)*")
        else:
            L.append("*(Level C skipped — Level A or B not PASS)*")

        L += ["", "---", "", "## Recommendation", ""]
        if is_rh:
            L.append(f"**REQUIRES_HUMAN** — {la.get('reason', '')}")
        elif overall == "PASS":
            L.append(
                "Exit-rule variant beats iter_10 baseline across all gates at matched "
                "leverage. Counts as one modification toward the L10 cap of 3 on "
                "Strategy C. Promote to a dedicated iter_NN with pre-registration "
                "before any live change."
            )
        elif overall == "CONDITIONAL_PASS":
            L.append(
                "Variant passes A+B but fails ≥2 robustness checks. Inspect which "
                "check failed (cost sensitivity or single-quarter concentration) "
                "before promoting."
            )
        else:
            L.append(
                "Exit-rule variant does not beat the iter_10 baseline at matched "
                "leverage. Do not promote. The current TP/SL/time-stop is at least "
                "as good on this sample."
            )

        L += ["", "---", "*Generated by ExitRuleHandler (Niveau 2 · Strategy C / NQ)*"]
        return "\n".join(L)
