#!/usr/bin/env python3
"""
Apply the n_tests reconciliation: remove the false FAIL_A verdicts (sandbox-403
data outages disguised as strategy failures) from the feasibility index + state.

SAFE BY DESIGN:
  - dry-run by default; writes nothing without --apply;
  - re-derives the target set from the index itself and RE-VERIFIES each target is
    a genuine data outage (empty results table / n_days < 30 / data-outage error)
    before removing — refuses to touch a FAIL_A that carries real metrics;
  - writes timestamped .bak_ copies of both JSON files before editing;
  - NEVER touches CLAUDE.md and NEVER edits n_tests (that stays a human decision).

Scope of removal (must ALL hold):
  - verdict == "FAIL_A"
  - handler in {GenericHandler, RegimeFilterHandler, SkipMonthHandler}
    (these use load_strategy_a_universe → the blocked crypto network path;
     ExitRuleHandler/NQ is a different root cause and is left untouched)
  - the report shows the data-outage signature.

Usage:
  python3 apply_reconciliation.py            # dry-run: prints what WOULD change
  python3 apply_reconciliation.py --apply    # perform the removal (with backups)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

_FEAS = Path(__file__).resolve().parents[1]  # _automation/feasibility
_ROOT = _FEAS.parents[1]                      # repo root
_INDEX = _FEAS / "tested" / "_index.json"
_STATE = _FEAS / "_state.json"

_CROSS_LOADER = {"GenericHandler", "RegimeFilterHandler", "SkipMonthHandler"}
_MIN_VALID_N_DAYS = 30
_DATA_MARKERS = ("No data loaded", "no price cache", "PriceDataUnavailable")


def _is_data_outage(report_path: str) -> bool | None:
    """True = data outage (safe to remove); False = real metrics; None = report missing."""
    p = _ROOT / report_path
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if any(m in text for m in _DATA_MARKERS):
        return True
    big_ints = [int(x) for x in re.findall(r"\|\s*(\d{3,6})\s*\|", text)]
    max_big = max(big_ints) if big_ints else 0
    return max_big < _MIN_VALID_N_DAYS


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()

    index = json.loads(_INDEX.read_text(encoding="utf-8"))
    state = json.loads(_STATE.read_text(encoding="utf-8"))
    hyps = index.get("tested_hypotheses", [])
    processed = state.get("processed_promising", {})

    targets, skipped_real, missing = [], [], []
    for h in hyps:
        if h.get("verdict") != "FAIL_A" or h.get("handler") not in _CROSS_LOADER:
            continue
        outage = _is_data_outage(h.get("report_path", ""))
        if outage is True:
            targets.append(h)
        elif outage is False:
            skipped_real.append(h)
        else:
            missing.append(h)

    target_srcs = {h["source_md"] for h in targets}
    state_keys = [s for s in target_srcs if s in processed]

    print(f"index tested_hypotheses      : {len(hyps)}")
    print(f"  → FAIL_A data-outage to remove: {len(targets)} entries "
          f"({len(target_srcs)} unique source_md)")
    print(f"  → crypto FAIL_A with real data (KEPT): {len(skipped_real)}")
    if missing:
        print(f"  → report missing, NOT touched: {len(missing)}")
    print(f"_state.processed_promising keys to remove: {len(state_keys)}")
    print(f"\nindex after : {len(hyps) - len(targets)} "
          f"(FAIL_A {sum(1 for h in hyps if h.get('verdict')=='FAIL_A') - len(targets)})")

    if not args.apply:
        print("\n[dry-run] no files written. Re-run with --apply to perform removal.")
        return 0

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    shutil.copy2(_INDEX, _INDEX.with_suffix(f".json.bak_{ts}"))
    shutil.copy2(_STATE, _STATE.with_suffix(f".json.bak_{ts}"))

    target_ids = {(h["source_md"], h["report_path"]) for h in targets}
    index["tested_hypotheses"] = [
        h for h in hyps if (h.get("source_md"), h.get("report_path")) not in target_ids
    ]
    for s in state_keys:
        processed.pop(s, None)
    state["processed_promising"] = processed
    state["reconciled_at"] = ts
    state["reconciled_removed"] = len(targets)

    _INDEX.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")
    _STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    print(f"\n[applied] removed {len(targets)} index entries + {len(state_keys)} state keys.")
    print(f"backups: {_INDEX.name}.bak_{ts}, {_STATE.name}.bak_{ts}")
    print("NOTE: n_tests in CLAUDE.md NOT modified — reconcile it manually per the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
