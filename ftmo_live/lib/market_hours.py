"""Calendrier de session forex/CFD FTMO — fenêtre conservatrice en dur, UTC, datée.

Le heartbeat EA (state.json) est tick-dépendant : WriteState est throttlé M1 sur
TimeCurrent() (book_executor.mq5:1291), qui gèle dès que plus aucun symbole du
Market Watch ne tick. Silence STRUCTUREL observé : dernier write vendredi
2026-06-12 20:54:59.551 UTC = 23:54:59 serveur = dernier tick USDJPY avant la
clôture hebdo. Toute alerte/watchdog de fraîcheur DOIT être gatée par ce
calendrier (les écritures forcées — OnInit, SetError, fills — passent, elles).

Fenêtre OUVERTE conservatrice (marge aux bords contre les faux positifs de
reprise/clôture) :
  été   (serveur EEST = UTC+3, jusqu'au 2026-10-25) : dim 22:05 → ven 20:50 UTC
  hiver (serveur EET  = UTC+2, 2026-10-25 → 2027-03-28) : dim 23:05 → ven 21:50 UTC
Marché réel été : reprise dim ~21:55 UTC, clôture ven 20:55 UTC.
Seam DST Europe 25/10/2026 : géré par la table _ERAS (+1 h UTC sur les bornes).
Au-delà de la table (2027-03-28) : repli OUVERT — fail-safe : on préfère un faux
positif d'alerte à un vrai incident silencieux ; étendre la table avant ce seam.
"""
from datetime import date, datetime, time, timezone

# (fin d'ère EXCLUSIVE, décalage heures UTC ajouté aux bornes été)
_ERAS = [
    (date(2026, 10, 25), 0),   # été 2026
    (date(2027, 3, 28), 1),    # hiver 2026-27
]
_OPEN_SUN_H, _OPEN_SUN_M = 22, 5     # dimanche, été
_CLOSE_FRI_H, _CLOSE_FRI_M = 20, 50  # vendredi, été


def _shift_h(d: date) -> int:
    for end, shift in _ERAS:
        if d < end:
            return shift
    return -1


def fx_session_open(now: datetime) -> bool:
    """True si la session forex FTMO est ouverte (fenêtre conservatrice).

    `now` doit être timezone-aware (converti en UTC en interne).
    """
    if now.tzinfo is None:
        raise ValueError("fx_session_open exige un datetime timezone-aware")
    now = now.astimezone(timezone.utc)
    shift = _shift_h(now.date())
    if shift < 0:
        return True   # table épuisée — repli fail-safe, étendre _ERAS
    wd = now.weekday()   # lundi=0 … dimanche=6
    t = now.time()
    if wd <= 3:          # lundi-jeudi : ticks en continu (observé 02:11 serveur)
        return True
    if wd == 4:          # vendredi : jusqu'à la clôture, avec marge
        return t < time(_CLOSE_FRI_H + shift, _CLOSE_FRI_M)
    if wd == 5:          # samedi
        return False
    return t >= time(_OPEN_SUN_H + shift, _OPEN_SUN_M)   # dimanche : reprise
