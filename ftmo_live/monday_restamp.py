#!/usr/bin/env python3
"""monday_restamp.py — cron lundi ~13:00 UTC : re-stamp targets.json pour le GER40 17:35.

Problème : brain.py ne tourne pas le week-end et l'EA n'exporte market_export qu'à 21:45 Paris
→ pas d'export frais entre vendredi 21:45 et lundi 21:45 → brain ne peut régénérer. Au créneau
GER40 17:35 Paris (Do1735), les targets de vendredi ont ~67h → gate EA `age_h>26` → STALE → skip.

Or la donnée de vendredi est correcte (close vendredi = vrai T-1 d'un lundi) et le GER40 17:35
n'utilise AUCUN poids data (tgt[3]=on_w×scale×eq, on_w constante). Seuls l'horodatage figé et le
flag calendaire `ea_on_day=0` du vendredi déclenchent le rejet.

Ce composant ADDITIF réécrit, le lundi seulement, UNIQUEMENT :
  - ea_generated_at_paris  (now)        → satisfait le gate 26h de l'EA
  - ea_valid_for_date      (date lundi) → cohérence audit (non gaté EA)
  - ea_on_day              (0 → 1)      → lundi EST un jour ON (gate BAD_ONDAY)
  - ea_w_usdjpy            (→ 0.0)      → fail-closed J1  (amendement §0, 2026-07-13)
  - ea_w_xauusd            (→ 0.0)      → fail-closed or  (extension §0, option 2, 2026-07-14)
+ un bloc `restamp` (audit, ignoré par l'EA).

Fail-closed data-poids : le re-stamp rend les targets fraîches pour TOUT le lundi (y compris le
rebalance 22h05, même gate 26h). Si le brain échoue à 21h50, ce rebalance traderait sinon les poids
data de vendredi (J1 sous l'état de gate de vendredi → ~16× USD/JPY en zone ; l'or à l'aveugle).
Mettre à zéro les DEUX seuls poids data-dépendants → J1 et or à plat au cas dégradé ; seules les
jambes calendaires on_w (US100, GER40) sont tradées. Inerte au cas normal (le brain écrase toutes
les targets à 21h50, avant toute consommation de poids — les deux poids ne sont lus qu'à 22h05).
N'affecte pas le GER40 (leg 3 = on_w) ni ea_on_w.

Le reste (ea_on_w, sha, mode, bloc audit dont audit.j1_gate) est COPIÉ VERBATIM. Fail-safe : au
moindre doute, NE RÉÉCRIT RIEN (un GER40 skippé > un targets corrompu sur compte armé). Voir
MONDAY_RESTAMP_PREREG.md.

Usage:
  monday_restamp.py            # production (réécrit targets.json si conditions réunies)
  monday_restamp.py --dry-run  # affiche AVANT/APRÈS, n'écrit pas (test hors compte armé)
  monday_restamp.py --dry-run --targets <path>  # test sur une fixture
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import statefiles  # noqa: E402
from lib import spec as S  # noqa: E402

STALE_H = 26.0                 # miroir du gate EA (book_executor.mq5:870)
MAX_SOURCE_AGE_DAYS = 3        # vendredi→lundi = 3 j calendaires ; au-delà = brain muet trop longtemps
ON_WEEKDAYS = (0, 1)           # lundi, mardi (= engine.py:142 dayofweek ∈ {0,1})
RESTAMP_REASON = "monday_ger40_stale_targets"


def _log(msg: str) -> None:
    print(f"monday_restamp {statefiles.fmt_ts(statefiles.now_paris().replace(tzinfo=None))} {msg}")


def _decide(targets: dict, now: datetime, state: dict | None) -> tuple[bool, str]:
    """(doit_réécrire, raison). Fail-safe : False sur tout doute."""
    if now.weekday() != 0:
        return False, f"NO-OP: pas lundi (weekday={now.weekday()})"
    if now.weekday() not in ON_WEEKDAYS:
        return False, "NO-OP: lundi non-ON (incohérent, garde-fou)"
    if targets is None:
        return False, "REFUS: targets.json absent/illisible"
    if targets.get("schema") != statefiles.TARGETS_SCHEMA:
        return False, f"REFUS: schema inattendu ({targets.get('schema')!r})"
    try:
        spec_sha = S.spec_sha256()
    except Exception as e:  # loader/pin KO → ne pas réécrire à l'aveugle
        return False, f"REFUS: spec_sha256 indisponible ({e!r})"
    if targets.get("ea_spec_sha256") != spec_sha:
        return False, ("REFUS: ea_spec_sha256 != spec gelée "
                       f"({str(targets.get('ea_spec_sha256'))[:12]}… vs {spec_sha[:12]}…)")
    if state is not None:
        ph_state, ph_tgt = state.get("phase"), targets.get("ea_phase_hint")
        if ph_state is not None and ph_tgt is not None and str(ph_state) != str(ph_tgt):
            return False, f"REFUS: phase state={ph_state} != targets={ph_tgt}"
    try:
        age_h = statefiles.targets_age_h(targets, now)
    except Exception as e:
        return False, f"REFUS: ea_generated_at_paris illisible ({e!r})"
    if age_h <= STALE_H:
        return False, f"NO-OP: targets déjà fraîches (age {age_h:.1f}h ≤ {STALE_H}h)"
    try:
        vfd = datetime.strptime(targets["ea_valid_for_date"], "%Y-%m-%d").date()
    except Exception as e:
        return False, f"REFUS: ea_valid_for_date illisible ({e!r})"
    dd = (now.date() - vfd).days
    if dd < 1 or dd > MAX_SOURCE_AGE_DAYS:
        return False, (f"REFUS: ea_valid_for_date {vfd} à {dd} j (attendu 1..{MAX_SOURCE_AGE_DAYS}, "
                       "vendredi) — brain muet trop longtemps ou date future")
    return True, f"OK: réécriture (age {age_h:.1f}h, source {vfd} J-{dd})"


def _restamp(targets: dict, now: datetime) -> dict:
    """Copie verbatim + champs §3 + bloc audit `restamp`. Ne mute PAS l'original.

    §3 (amendement §0) : re-stampe ea_generated_at_paris / ea_valid_for_date / ea_on_day, ET met à
    ZÉRO les DEUX seuls poids data-dépendants ea_w_usdjpy + ea_w_xauusd (fail-closed : brain mort ⇒
    aucun poids data tradé à l'aveugle au rebalance 22h05). source_w_* lus sur l'ORIGINAL
    (`targets`), pas sur `out`. ea_on_w (poids calendaire US100/GER40, levier du fix GER40), sha,
    mode et le bloc audit (dont audit.j1_gate) restent verbatim, jamais mutés.
    """
    ts = statefiles.fmt_ts(now.replace(tzinfo=None))
    out = dict(targets)
    out["ea_generated_at_paris"] = ts
    out["ea_valid_for_date"] = str(now.date())
    out["ea_on_day"] = 1
    out["ea_w_usdjpy"] = 0.0                      # fail-closed J1 (§0)
    out["ea_w_xauusd"] = 0.0                      # fail-closed or (extension §0, option 2)
    out["restamp"] = dict(
        source_generated_at=targets.get("ea_generated_at_paris"),
        source_valid_for_date=targets.get("ea_valid_for_date"),
        source_w_usdjpy=targets.get("ea_w_usdjpy"),
        source_w_xauusd=targets.get("ea_w_xauusd"),
        failclosed=True,
        restamp_ts=ts,
        reason=RESTAMP_REASON)
    return out


def _diff(before: dict, after: dict) -> list[str]:
    keys = sorted(set(before) | set(after))
    return [f"  {k}: {before.get(k, '<absent>')!r} -> {after.get(k, '<absent>')!r}"
            for k in keys if before.get(k) != after.get(k)]


def run(dry_run: bool = False, targets_path: Path | None = None) -> int:
    now = statefiles.now_paris().replace(tzinfo=None)
    if targets_path is None:
        targets_path = statefiles.mt5_files_dir() / "targets.json"
        state = statefiles.read_state(statefiles.mt5_files_dir())
    else:
        state = None  # fixture de test : pas de state
    targets = statefiles.read_json(targets_path)

    do_write, reason = _decide(targets, now, state)
    _log(reason)
    if not do_write:
        return 0

    after = _restamp(targets, now)
    if dry_run:
        _log("DRY-RUN — diff AVANT/APRÈS (aucune écriture) :")
        for line in _diff(targets, after):
            print(line)
        return 0
    statefiles.atomic_write_json(targets_path, after)
    _log(f"ÉCRIT {targets_path} — ea_generated_at_paris={after['ea_generated_at_paris']} "
         f"ea_on_day=1 ea_w_usdjpy=0 ea_w_xauusd=0 (fail-closed data-poids) — on_w/sha/mode inchangés")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="affiche AVANT/APRÈS sans écrire")
    ap.add_argument("--targets", default=None,
                    help="chemin targets.json (test sur fixture ; défaut = MQL5/Files live)")
    a = ap.parse_args(argv)
    try:
        return run(dry_run=a.dry_run,
                   targets_path=Path(a.targets) if a.targets else None)
    except Exception as e:  # fail-safe absolu : jamais d'écriture sur exception
        _log(f"NO-OP (exception, aucune écriture) : {e!r}")
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    sys.exit(main())
