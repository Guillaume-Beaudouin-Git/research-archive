#!/usr/bin/env python3
"""Register integrity check (session-close gate, fail-loud).

Verifies, for PropFirms/ftmo/program_2026-06/positive_dsr_register/REGISTER.md:
  1. every backtick-cited file path resolves on disk (consolidation aliases applied,
     historical citations are never rewritten) AND is git-tracked;
  2. the trial-count ledger chain is strictly monotonic and its increments reconcile.

Exit 0 = clean. Exit 1 = any failure (print findings). Run from repo root or anywhere.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "PropFirms/ftmo/program_2026-06/positive_dsr_register/REGISTER.md"
PROGRAM = REPO / "PropFirms/ftmo/program_2026-06"

# Consolidation aliases (P2 2026-06-10) — historical citations are NOT rewritten.
ALIASES = [
    ("data/ftmo_research/", "PropFirms/ftmo/program_2026-06/ftmo_research/"),
    ("data/oxfordstrat_109/", "Multi_Asset/research/archived/oxfordstrat_109_audit/"),
    ("research/", "PropFirms/ftmo/program_2026-06/"),
]

PATHLIKE = re.compile(r"`([^`\n]+)`")
EXTENSIONS = (".md", ".csv", ".py", ".json", ".parquet", ".txt", ".pdf")


def candidate_paths(token: str) -> list[Path]:
    t = token.strip()
    t = re.sub(r"::\w+$", "", t)          # `file.csv::ret` column refs
    t = re.sub(r":\d+(-\d+)?$", "", t)    # `file.md:16` line refs
    if not t or "…" in t or "{" in t or t.startswith("http") or " " in t:
        return []
    if "/" not in t:
        return []  # bare filenames = context-elided shorthand, not checkable citations
    if not t.endswith(EXTENSIONS) and not t.endswith("/"):
        return []
    cands = [REPO / t, PROGRAM / t, PROGRAM / "ftmo_research" / t]
    for old, new in ALIASES:
        if t.startswith(old):
            cands.append(REPO / (new + t[len(old):]))
    return cands


def is_tracked(p: Path) -> bool:
    r = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch",
                        str(p.relative_to(REPO))], capture_output=True)
    return r.returncode == 0


def check_paths(text: str) -> list[str]:
    failures = []
    seen: set[str] = set()
    for tok in PATHLIKE.findall(text):
        cands = candidate_paths(tok)
        if not cands or tok in seen:
            continue
        seen.add(tok)
        hit = next((c for c in cands if c.exists() and c.is_file()), None)
        dirhit = next((c for c in cands if c.exists() and c.is_dir()), None)
        if hit is None and dirhit is None:
            failures.append(f"MISSING  `{tok}` (tried {len(cands)} resolutions)")
        elif hit is not None and not is_tracked(hit):
            failures.append(f"UNTRACKED `{tok}` -> {hit.relative_to(REPO)}")
    return failures


def check_chain(text: str) -> list[str]:
    failures = []
    ledger = text.split("> **Trial-count ledger", 1)
    if len(ledger) < 2:
        return ["LEDGER block not found in REGISTER.md"]
    block = ledger[1].split("\n\n", 1)[0]
    base_m = re.search(r"N\s*=\s*(\d{2,4})\D*?:?\)?", block)
    arrows = [int(x) for x in re.findall(r"(?:→|->)\s*(?:\*\*)?N?\s*=?\s*(\d{2,4})", block)]
    deltas = [int(x) for x in re.findall(r"\+(\d+)\s", block)]
    if base_m is None or not arrows:
        return [f"LEDGER unparseable (base={base_m}, arrows={arrows})"]
    base = int(base_m.group(1))
    chain = [base] + arrows
    if any(b < a for a, b in zip(chain, chain[1:])):
        failures.append(f"N chain not monotonic: {chain}")
    if deltas and base + sum(deltas) != chain[-1]:
        failures.append(f"Deltas {deltas} do not reconcile {base} -> {chain[-1]}")
    print(f"ledger chain OK: {chain} (deltas {deltas})" if not failures else "")
    return failures


def main() -> int:
    if not REGISTER.exists():
        print(f"FAIL: {REGISTER} missing")
        return 1
    text = REGISTER.read_text()
    failures = check_paths(text) + check_chain(text)
    if failures:
        print(f"\nREGISTER INTEGRITY: {len(failures)} failure(s)")
        for f in failures:
            print("  -", f)
        return 1
    print("REGISTER INTEGRITY: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
