"""ftmo_live.lib — exécution live du book CHALLENGE v2.2 (spec gelée).

Politique de décision : IMPORTE le code path des 462 cohortes (v22/engine_v22.py +
audit_v2_independent/cleanroom/engine.py + v22/ea/brain.py loader) — jamais de
réimplémentation. Toute constante vient de spec_v22.yaml via le loader épinglé.

Note de chemin : le brief nomme `audit_stack.load_audited()` ; ce module importe
`config.py` dont les chemins pointent sur le sandbox cloud mort
(/sessions/keen-clever-clarke). Le code path effectivement exécuté pour les 462
cohortes (run_battery.py) est engine_v22.load_stack + cleanroom build_signals —
c'est celui-ci qui est importé. Voir README.md §Architecture.
"""
import sys
from pathlib import Path

LIVE_ROOT = Path(__file__).resolve().parents[1]          # ftmo_live/
REPO = LIVE_ROOT.parent                                   # Algo_claude/
PKG = REPO / "data" / "ftmo_portfolio"
V22 = PKG / "v22"
CLEANROOM = PKG / "audit_v2_independent" / "cleanroom"
EA_DIR = V22 / "ea"
RUNTIME = LIVE_ROOT / "runtime"                           # gitignored
LIVE_CACHE = RUNTIME / "cache_live"

# Baseline pins (étendus 79c6912 — chaîne de gel EA ; mqh re-pinné v2.2.1 recost)
PIN_COMMITS = {
    "v22_contract": "605f4a426da3eac4f5a2644bca774a07f1e5f754",
    "v22_residuals": "4e1bac5cf6486fcd0070876d47dd2dcdc7a8f539",
    # v2.8 : commit de gel du yaml v2.2.2 (ancien v2.2.1: 87b6cd4080e2b1c9e666c6b9dd15680ce29a7e1e)
    "v22_spec_yaml": "ad403cefb7f8af9285acb1bdd424d0601080c5b5",
    "v22_ea_build": "79c6912a9639db1c08ac8c5449536bb293ce5a49",
}
# v2.2.2 (lot EA v2.8) : ancien mqh v2.2.1 = 2fc65503ef666d52… ; v2.2 = 1d83454602560c09…
PIN_MQH_SHA256 = "d8d3dcb1ad88ec6bf2338ef88c4710d8595d5a0e9f1ca847d9e0ab0c8fe0388b"

for _p in (str(V22), str(CLEANROOM)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
