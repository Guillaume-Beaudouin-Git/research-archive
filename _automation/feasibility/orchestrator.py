"""
Entry point for the feasibility pipeline.
Reads promising/*.md hypothesis files, classifies via the handler registry,
dispatches to the appropriate handler, and writes results to tested/.

Usage:
  python3 orchestrator.py                  # batch: process all untested .md files
  python3 orchestrator.py <path>           # single: process one .md file
  python3 orchestrator.py --single <path>  # single (explicit flag)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from _automation.feasibility.data.loaders import PriceDataUnavailable
from _automation.feasibility.handlers import HANDLER_REGISTRY, GenericHandler

_FEASIBILITY_DIR = Path(__file__).parent
_PROMISING_DIR = _ROOT / "_automation" / "alpha_hunt" / "promising"
_TESTED_DIR = _FEASIBILITY_DIR / "tested"
_INDEX_JSON = _TESTED_DIR / "_index.json"
_STATE_JSON = _FEASIBILITY_DIR / "_state.json"

# Anti-false-verdict guardrail: a backtest that ran on < this many days of data
# did not actually run. Below this, a "FAIL_A" is a DATA_UNAVAILABLE in disguise
# (sandbox 403 blocking the price fetch), NOT a strategy failure. n_tests is the
# DSR denominator — it must never be incremented by a data outage.
_MIN_VALID_N_DAYS: int = 30

# Substrings in a Level-A error that unambiguously mean "no data", not "bad strategy".
_DATA_UNAVAILABLE_MARKERS: tuple[str, ...] = (
    "no price cache and live fetch blocked",
    "No data loaded for tickers",
    "PriceDataUnavailable",
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _already_tested(index: dict) -> set[str]:
    """Return set of .md filenames already recorded in tested/_index.json."""
    return {h["source_md"] for h in index.get("tested_hypotheses", [])}


def _find_untested(index: dict) -> list[Path]:
    """Return all promising .md files not yet in tested/_index.json, sorted."""
    done = _already_tested(index)
    return sorted(
        md for md in _PROMISING_DIR.glob("*.md")
        if md.name not in done
    )


def _slug_from_path(md_path: Path) -> str:
    return md_path.stem[:60]


# ── Anti-false-verdict guardrail ─────────────────────────────────────────────────

def _collect_n_days(obj) -> list[int]:
    """Recursively gather every ``n_days`` value found in a results structure."""
    found: list[int] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "n_days" and isinstance(val, (int, float)):
                found.append(int(val))
            else:
                found.extend(_collect_n_days(val))
    elif isinstance(obj, list):
        for val in obj:
            found.extend(_collect_n_days(val))
    return found


def _is_data_unavailable(handler) -> bool:
    """
    True when Level A could NOT run a real backtest because price data was absent
    (sandbox 403), rather than because the strategy failed on real data.

    Detection (any of):
      - an explicit ``data_unavailable`` marker on any level result;
      - a Level-A error string matching a known data-outage marker;
      - a recorded ``n_days`` that is below the minimum a real run always exceeds
        (the Strategy A universe spans 2018→today ⇒ thousands of days when present).
    """
    results = getattr(handler, "results", {}) or {}
    for level in results.values():
        if isinstance(level, dict) and level.get("data_unavailable"):
            return True

    err = str(results.get("level_A", {}).get("error", ""))
    if any(marker in err for marker in _DATA_UNAVAILABLE_MARKERS):
        return True

    n_days_vals = _collect_n_days(results)
    if n_days_vals:
        return max(n_days_vals) < _MIN_VALID_N_DAYS
    return False


# ── Dispatch ───────────────────────────────────────────────────────────────────

def _dispatch_handler(md_path: Path):
    for HandlerCls in HANDLER_REGISTRY:
        if HandlerCls.classify(str(md_path)):
            return HandlerCls.__name__, HandlerCls(str(md_path))
    return "GenericHandler", GenericHandler(str(md_path))


# ── Single-file pipeline ───────────────────────────────────────────────────────

def _run_one(md_path: Path, output_dir: Path, index: dict, state: dict) -> str:
    """
    Run the full feasibility pipeline on one .md file.
    Returns the final verdict string (PASS / FAIL_A / FAIL_B / FAIL_C /
    REQUIRES_HUMAN / CONDITIONAL_PASS).
    """
    print(f"\n{'='*70}")
    print(f"Feasibility Pipeline — {date.today()}")
    print(f"{'='*70}")
    print(f"Hypothesis : {md_path.name}")

    handler_name, handler = _dispatch_handler(md_path)
    print(f"  → dispatched to: {handler_name}")

    # ── Level A ───────────────────────────────────────────────────────────────
    print(f"\n[Level A] Feasibility gate …")
    try:
        result_a = handler.run_level_A()
    except PriceDataUnavailable as exc:
        print(f"  DATA UNAVAILABLE in Level A: {exc}")
        result_a = {"pass": False, "error": str(exc), "data_unavailable": True}
        handler.results["level_A"] = result_a
    except Exception as exc:
        print(f"  ERROR in Level A: {exc}")
        result_a = {"pass": False, "error": str(exc)}
        handler.results["level_A"] = result_a

    verdict_a = result_a.get("verdict", "")
    is_requires_human = verdict_a == "REQUIRES_HUMAN"
    _print_level_A_summary(result_a)

    if is_requires_human:
        print(f"\n  ⚠  Level A → REQUIRES_HUMAN (stopping pipeline)")
        return _write_report(handler, md_path, output_dir, index, state, stopped_at="A")

    if not result_a.get("pass", False):
        print(f"\n  ✗  Level A FAIL → stopping pipeline")
        return _write_report(handler, md_path, output_dir, index, state, stopped_at="A")

    # ── Level B ───────────────────────────────────────────────────────────────
    print(f"\n[Level B] Walk-Forward Backtest + Bootstrap + DSR …")
    try:
        result_b = handler.run_level_B()
    except Exception as exc:
        print(f"  ERROR in Level B: {exc}")
        result_b = {"pass": False, "error": str(exc)}
        handler.results["level_B"] = result_b

    _print_level_B_summary(result_b)

    if not result_b.get("pass", False):
        print(f"\n  ✗  Level B FAIL → stopping pipeline")
        return _write_report(handler, md_path, output_dir, index, state, stopped_at="B")

    # ── Level C ───────────────────────────────────────────────────────────────
    print(f"\n[Level C] Sanity Checks …")
    try:
        result_c = handler.run_level_C()
    except Exception as exc:
        print(f"  ERROR in Level C: {exc}")
        result_c = {"pass": False, "error": str(exc)}
        handler.results["level_C"] = result_c

    _print_level_C_summary(result_c)

    return _write_report(handler, md_path, output_dir, index, state, stopped_at=None)


def _print_level_A_summary(result: dict) -> None:
    verdict = result.get("verdict", "")
    if verdict == "REQUIRES_HUMAN":
        category = result.get("category", "—")
        print(f"  ⚠  Level A: REQUIRES_HUMAN (category={category})")
    elif result.get("pass"):
        surviving = result.get("surviving_variants", [])
        bs = result.get("baseline_sharpe", result.get("baseline_sharpe"))
        extra = f" surviving={surviving}" if surviving else (
            f" Sharpe={bs:.3f}" if isinstance(bs, float) else ""
        )
        print(f"  ✅ Level A: PASS{extra}")
    else:
        print(f"  ❌ Level A: FAIL (verdict={verdict})")


def _print_level_B_summary(result: dict) -> None:
    if result.get("skipped"):
        print(f"  ⏭  Level B: SKIPPED")
        return
    passed = result.get("pass", False)
    icon = "✅" if passed else "❌"
    # Handle both SkipMonthHandler dict and GenericHandler dict
    sr = result.get("wf_sharpe_mean")
    dsr = result.get("dsr_global")
    extra = ""
    if sr is not None and isinstance(sr, float):
        extra = f" SR_oos={sr:.3f}"
    if dsr is not None and isinstance(dsr, float):
        extra += f", DSR={dsr:.4f}"
    # SkipMonthHandler has per_variant/best_variant
    best = result.get("best_variant")
    pv = result.get("per_variant", {})
    if best is not None and best in pv:
        v = pv[best]
        sr2 = v.get("wf_sharpe_mean")
        dsr2 = v.get("dsr_global")
        if isinstance(sr2, float):
            extra = f" best skip={best}: SR_oos={sr2:.3f}, DSR={dsr2:.4f}"
    print(f"  {icon} Level B: {'PASS' if passed else 'FAIL'}{extra}")


def _print_level_C_summary(result: dict) -> None:
    if result.get("skipped"):
        print(f"  ⏭  Level C: SKIPPED")
        return
    passed = result.get("pass", False)
    icon = "✅" if passed else "❌"
    n_pass = result.get("n_pass", 0)
    print(f"  {icon} Level C: {'PASS' if passed else 'FAIL'} ({n_pass}/3 checks)")


def _record_data_unavailable(handler, md_path: Path, state: dict) -> str:
    """
    Record a DATA_UNAVAILABLE outcome WITHOUT counting it as a tested hypothesis.

    Deliberately does NOT touch tested/_index.json and does NOT add the file to
    ``processed_promising`` — so ``_find_untested`` re-picks it up on the next run
    (once the price cache is present) and n_tests is never inflated by a data outage.
    The event is logged under a separate ``data_unavailable`` state key for visibility.
    """
    err = str(handler.results.get("level_A", {}).get("error", "price data unavailable"))
    print(f"\n  ⚠  DATA_UNAVAILABLE — not counted as a test (will retry once cache exists)")
    print(f"     reason: {err}")

    bucket = state.setdefault("data_unavailable", {})
    bucket[md_path.name] = {
        "last_seen": str(date.today()),
        "handler": type(handler).__name__,
        "reason": err,
    }
    state["last_run"] = str(date.today())
    _save_json(_STATE_JSON, state)

    print(f"  {'='*68}")
    print(f"  Verdict: DATA_UNAVAILABLE (n_tests unchanged)")
    return "DATA_UNAVAILABLE"


def _write_report(
    handler,
    md_path: Path,
    output_dir: Path,
    index: dict,
    state: dict,
    stopped_at: str | None,
) -> str:
    """Write report, update index + state, return verdict string."""
    # Determine verdict
    level_a = handler.results.get("level_A", {})
    level_b = handler.results.get("level_B", {})
    level_c = handler.results.get("level_C", {})

    if level_a.get("verdict") == "REQUIRES_HUMAN":
        verdict = "REQUIRES_HUMAN"
    elif stopped_at == "A":
        # GUARDRAIL: a Level-A failure with no real data is DATA_UNAVAILABLE, not
        # FAIL_A. It must NOT be recorded as a tested hypothesis (n_tests stays exact)
        # and must be left untested so it is retried once the price cache exists.
        verdict = "DATA_UNAVAILABLE" if _is_data_unavailable(handler) else "FAIL_A"
    elif stopped_at == "B":
        verdict = "FAIL_B"
    elif not level_c.get("pass", False):
        verdict = "FAIL_C"
    else:
        verdict = "PASS"

    if verdict == "DATA_UNAVAILABLE":
        return _record_data_unavailable(handler, md_path, state)

    report_text = handler.generate_report()
    output_dir.mkdir(parents=True, exist_ok=True)

    slug = _slug_from_path(md_path)
    report_filename = f"{slug}_{date.today()}_report.md"
    report_path = output_dir / report_filename
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n  Report → {report_path.relative_to(_ROOT)}")

    # Update index
    if "tested_hypotheses" not in index:
        index["tested_hypotheses"] = []
    index["tested_hypotheses"].append({
        "source_md": md_path.name,
        "tested_date": str(date.today()),
        "handler": type(handler).__name__,
        "verdict": verdict,
        "report_path": str(report_path.relative_to(_ROOT)),
        "stopped_at": stopped_at,
    })
    _save_json(_INDEX_JSON, index)

    # Update state
    state["last_run"] = str(date.today())
    state.setdefault("processed_promising", {})[md_path.name] = {
        "verdict": verdict,
        "report": str(report_path.relative_to(_ROOT)),
    }
    _save_json(_STATE_JSON, state)

    print(f"  {'='*68}")
    print(f"  Verdict: {verdict}")
    return verdict


# ── Batch mode ─────────────────────────────────────────────────────────────────

def _print_batch_summary(results: list[tuple[str, str]]) -> None:
    """Print final summary after batch run."""
    from collections import Counter

    counts: Counter = Counter(v for _, v in results)
    total = len(results)

    print(f"\n{'='*70}")
    print(f"BATCH SUMMARY — {date.today()}")
    print(f"{'='*70}")
    print(f"Total processed : {total}")
    print(f"  PASS           : {counts.get('PASS', 0)}")
    print(f"  CONDITIONAL    : {counts.get('CONDITIONAL_PASS', 0)}")
    print(f"  FAIL_A         : {counts.get('FAIL_A', 0)}")
    print(f"  FAIL_B         : {counts.get('FAIL_B', 0)}")
    print(f"  FAIL_C         : {counts.get('FAIL_C', 0)}")
    print(f"  REQUIRES_HUMAN : {counts.get('REQUIRES_HUMAN', 0)}")
    print(f"  DATA_UNAVAIL   : {counts.get('DATA_UNAVAILABLE', 0)}")
    print(f"{'='*70}")

    passes = [(name, v) for name, v in results if v == "PASS"]
    if passes:
        print(f"\nTop PASS files:")
        for name, _ in passes[:3]:
            print(f"  ✅ {name}")

    rh = [(name, v) for name, v in results if v == "REQUIRES_HUMAN"]
    if rh:
        print(f"\nSample REQUIRES_HUMAN (first 3):")
        for name, _ in rh[:3]:
            print(f"  ⚠  {name}")
    print(f"{'='*70}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main(
    promising_md_path: str | None = None,
    output_dir: str | None = None,
) -> None:
    """
    Run the feasibility pipeline.

    Single mode (promising_md_path given): process one file.
    Batch mode (no path): process all untested files in alpha_hunt/promising/.
    """
    index = _load_json(_INDEX_JSON)
    state = _load_json(_STATE_JSON)
    out_dir = Path(output_dir) if output_dir else _TESTED_DIR

    if promising_md_path is not None:
        # Single mode
        md_path = Path(promising_md_path)
        if not md_path.exists():
            print(f"ERROR: file not found: {md_path}")
            return
        _run_one(md_path, out_dir, index, state)
        return

    # Batch mode
    untested = _find_untested(index)
    if not untested:
        print("All promising hypotheses have already been tested.")
        return

    print(f"Batch mode: {len(untested)} file(s) to process")
    results: list[tuple[str, str]] = []

    for md_path in untested:
        verdict = _run_one(md_path, out_dir, index, state)
        results.append((md_path.name, verdict))
        # Reload index/state to avoid stale data in multi-file run
        index = _load_json(_INDEX_JSON)
        state = _load_json(_STATE_JSON)

    _print_batch_summary(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feasibility pipeline")
    parser.add_argument(
        "promising_md_path", nargs="?",
        help="Path to a single promising .md file (batch mode if omitted)",
    )
    parser.add_argument(
        "--single", metavar="PATH",
        help="Process only this .md file (alternative to positional arg)",
    )
    args = parser.parse_args()
    path = args.promising_md_path or args.single
    main(promising_md_path=path)
