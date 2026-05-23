"""
Entry point for the feasibility pipeline.
Reads a promising/*.md hypothesis file, classifies it via the handler registry,
dispatches to the appropriate handler, and writes the result to tested/.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Ensure project root is on the path when run directly
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from _automation.feasibility.handlers import HANDLER_REGISTRY, GenericHandler

_FEASIBILITY_DIR = Path(__file__).parent
_PROMISING_DIR = _ROOT / "_automation" / "alpha_hunt" / "promising"
_TESTED_DIR = _FEASIBILITY_DIR / "tested"
_INDEX_JSON = _TESTED_DIR / "_index.json"
_STATE_JSON = _FEASIBILITY_DIR / "_state.json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _find_first_untested(index: dict) -> Path | None:
    """Return the first promising .md not already recorded in tested/_index.json."""
    tested_sources = {
        h["source_md"]
        for h in index.get("tested_hypotheses", [])
    }
    for md_path in sorted(_PROMISING_DIR.glob("*.md")):
        if md_path.name not in tested_sources:
            return md_path
    return None


def _slug_from_path(md_path: Path) -> str:
    """Derive a short slug from the promising .md filename."""
    stem = md_path.stem
    # Truncate at 60 chars so filenames stay manageable
    return stem[:60]


# ── Dispatch ───────────────────────────────────────────────────────────────────

def _dispatch_handler(md_path: Path):
    """Instantiate the first handler in HANDLER_REGISTRY whose classify() returns True."""
    for HandlerCls in HANDLER_REGISTRY:
        if HandlerCls.classify(str(md_path)):
            print(f"  → dispatched to: {HandlerCls.__name__}")
            return HandlerCls(str(md_path))
    # Fallback (GenericHandler always returns True so this should never be reached)
    print("  → dispatched to: GenericHandler (fallback)")
    return GenericHandler(str(md_path))


# ── Main ───────────────────────────────────────────────────────────────────────

def main(
    promising_md_path: str | None = None,
    output_dir: str | None = None,
) -> None:
    """
    Run the full feasibility pipeline on one promising hypothesis.

    Parameters
    ----------
    promising_md_path : str or None
        Path to the .md file to test. If None, auto-detects the first untested
        file in `_automation/alpha_hunt/promising/`.
    output_dir : str or None
        Directory where the report .md is written. Defaults to `tested/`.
    """
    index = _load_json(_INDEX_JSON)
    state = _load_json(_STATE_JSON)

    # ── 1. Resolve the promising file ─────────────────────────────────────────
    if promising_md_path is None:
        md_path = _find_first_untested(index)
        if md_path is None:
            print("All promising hypotheses have already been tested.")
            return
    else:
        md_path = Path(promising_md_path)
        if not md_path.exists():
            print(f"ERROR: file not found: {md_path}")
            return

    print(f"\n{'='*70}")
    print(f"Feasibility Pipeline — {date.today()}")
    print(f"{'='*70}")
    print(f"Hypothesis : {md_path.name}")

    # ── 2. Dispatch to handler ────────────────────────────────────────────────
    handler = _dispatch_handler(md_path)

    # ── 3. Level A ────────────────────────────────────────────────────────────
    print(f"\n[Level A] IC Feasibility …")
    try:
        result_a = handler.run_level_A()
    except Exception as exc:
        print(f"  ERROR in Level A: {exc}")
        result_a = {"pass": False, "error": str(exc)}
        handler.results["level_A"] = result_a

    _print_level_summary("A", result_a)

    if not result_a.get("pass", False):
        print("\n  ✗ Level A FAIL → stopping pipeline, writing partial report.")
        _write_report(handler, md_path, output_dir, index, state, stopped_at="A")
        return

    # ── 4. Level B ────────────────────────────────────────────────────────────
    print(f"\n[Level B] Walk-Forward Backtest + Bootstrap + DSR …")
    try:
        result_b = handler.run_level_B()
    except Exception as exc:
        print(f"  ERROR in Level B: {exc}")
        result_b = {"pass": False, "error": str(exc)}
        handler.results["level_B"] = result_b

    _print_level_summary("B", result_b)

    if not result_b.get("pass", False):
        print("\n  ✗ Level B FAIL → stopping pipeline, writing partial report.")
        _write_report(handler, md_path, output_dir, index, state, stopped_at="B")
        return

    # ── 5. Level C ────────────────────────────────────────────────────────────
    print(f"\n[Level C] Sanity Checks …")
    try:
        result_c = handler.run_level_C()
    except Exception as exc:
        print(f"  ERROR in Level C: {exc}")
        result_c = {"pass": False, "error": str(exc)}
        handler.results["level_C"] = result_c

    _print_level_summary("C", result_c)

    # ── 6. Write report ───────────────────────────────────────────────────────
    _write_report(handler, md_path, output_dir, index, state, stopped_at=None)


def _print_level_summary(level: str, result: dict) -> None:
    """Print a one-line verdict for a pipeline level."""
    passed = result.get("pass", False)
    icon = "✅" if passed else "❌"
    extra = ""
    if level == "A":
        surviving = result.get("surviving_variants", [])
        extra = f" surviving variants: {surviving}"
    elif level == "B":
        best = result.get("best_variant")
        pv = result.get("per_variant", {})
        if best is not None and best in pv:
            sr = pv[best].get("wf_sharpe_mean", "—")
            dsr = pv[best].get("dsr_global", "—")
            extra = f" best skip={best}: SR_oos={sr:.3f}, DSR={dsr:.4f}" if isinstance(sr, float) else ""
    elif level == "C":
        extra = f" {result.get('n_pass', 0)}/3 checks passed"
    print(f"  {icon} Level {level}: {'PASS' if passed else 'FAIL'}{extra}")


def _write_report(
    handler,
    md_path: Path,
    output_dir: str | None,
    index: dict,
    state: dict,
    stopped_at: str | None,
) -> None:
    """Write report .md to tested/, update _index.json and _state.json."""
    report_text = handler.generate_report()

    out_dir = Path(output_dir) if output_dir else _TESTED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = _slug_from_path(md_path)
    report_filename = f"{slug}_{date.today()}_report.md"
    report_path = out_dir / report_filename
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n  Report written → {report_path.relative_to(_ROOT)}")

    # Determine overall verdict from results
    level_a = handler.results.get("level_A", {})
    level_b = handler.results.get("level_B", {})
    level_c = handler.results.get("level_C", {})
    if stopped_at == "A":
        verdict = "FAIL_A"
    elif stopped_at == "B":
        verdict = "FAIL_B"
    elif not level_c.get("pass", False):
        verdict = "FAIL_C"
    else:
        verdict = "PASS"

    # Update index
    entry = {
        "source_md": md_path.name,
        "tested_date": str(date.today()),
        "handler": type(handler).__name__,
        "verdict": verdict,
        "report_path": str(report_path.relative_to(_ROOT)),
        "stopped_at": stopped_at,
    }
    if "tested_hypotheses" not in index:
        index["tested_hypotheses"] = []
    index["tested_hypotheses"].append(entry)
    _save_json(_INDEX_JSON, index)

    # Update state
    state["last_run"] = str(date.today())
    if "processed_promising" not in state:
        state["processed_promising"] = {}
    state["processed_promising"][md_path.name] = {
        "verdict": verdict,
        "report": str(report_path.relative_to(_ROOT)),
    }
    _save_json(_STATE_JSON, state)

    print(f"  Index updated → tested/_index.json")
    print(f"  State updated → _state.json")
    print(f"\n{'='*70}")
    print(f"Overall verdict: {verdict}")
    print(f"{'='*70}\n")

    # Print report header for quick inspection
    preview_lines = report_text.split("\n")[:30]
    print("--- Report preview (first 30 lines) ---")
    print("\n".join(preview_lines))
    print("---")


if __name__ == "__main__":
    # Optional: pass a specific .md path as CLI argument
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(promising_md_path=path_arg)
