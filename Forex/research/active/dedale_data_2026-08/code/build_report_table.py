"""
build_report_table.py — lit certification/<PAIR>.json et imprime le tableau
markdown §2 de RAPPORT_DONNEES.md (à coller manuellement — on n'édite pas le
rapport par script pour garder le texte narratif sous contrôle humain).
"""
from __future__ import annotations

import json
from pathlib import Path

CERT_DIR = Path(__file__).parent.parent / "certification"


def fmt_row(sym: str, d: dict) -> str:
    if d.get("status") == "NO_RAW_DATA":
        return f"| {sym} | — | — | — | — | — | — | — | **AUCUNE DONNÉE** |"
    flat_by_year = d.get("flat_pct_by_year", {})
    max_flat_year = max(flat_by_year, key=lambda k: flat_by_year[k]) if flat_by_year else None
    max_flat_val = flat_by_year.get(max_flat_year) if max_flat_year else None
    cc = d.get("cross_check", {})
    cc_str = (f"{cc.get('median_bps')}/{cc.get('p95_bps')}"
              if "median_bps" in cc else cc.get("note", "n/a"))
    wc = d.get("weekday_coverage", {})
    gaps = d.get("gaps", {})
    period = f"{d.get('start','')[:10]} -> {d.get('end','')[:10]}"
    status = "OK" if (max_flat_val or 0) < 10 and wc.get("pct_missing", 0) < 5 else "A VERIFIER"
    return (f"| {sym} | {period} | {d.get('rows'):,} | M1 native | 0 min | "
            f"{max_flat_val}% ({max_flat_year}) | {gaps.get('n_illegit_gaps')} | "
            f"{cc_str} | {status} |")


def main() -> None:
    print("| Paire | Période | N barres | Granularité | Décalage fuseau | "
          "% flat max (année) | Trous illégitimes | Cross-check méd/p95 (bps) | Statut |")
    print("|---|---|---|---|---|---|---|---|---|")
    for pq in sorted(CERT_DIR.glob("*.json")):
        d = json.loads(pq.read_text())
        print(fmt_row(pq.stem, d))


if __name__ == "__main__":
    main()
