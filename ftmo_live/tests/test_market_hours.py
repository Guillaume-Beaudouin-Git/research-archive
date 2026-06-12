"""Calendrier session forex (fenêtre conservatrice UTC, table datée seam DST)."""
from datetime import datetime, timezone

import pytest

from lib.market_hours import fx_session_open


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.mark.parametrize("dt,expected", [
    (_utc(2026, 6, 12, 20, 0), True),     # vendredi 20:00 UTC — ouvert
    (_utc(2026, 6, 12, 21, 30), False),   # vendredi 21:30 UTC — fermé (clôture 20:50)
    (_utc(2026, 6, 13, 12, 0), False),    # samedi — fermé
    (_utc(2026, 6, 14, 22, 30), True),    # dimanche 22:30 UTC — ouvert (reprise 22:05)
    (_utc(2026, 6, 15, 3, 0), True),      # lundi — ouvert
    (_utc(2026, 6, 14, 21, 30), False),   # dimanche 21:30 UTC — encore fermé (marge)
    (_utc(2026, 6, 12, 20, 54), False),   # vendredi 20:54 — déjà fermé (marge 20:50)
    (_utc(2026, 10, 30, 21, 30), True),   # hiver (post-seam 25/10) : ven 21:30 < 21:50
    (_utc(2026, 10, 30, 22, 0), False),   # hiver : vendredi 22:00 — fermé
    (_utc(2026, 11, 1, 22, 30), False),   # hiver : dimanche 22:30 < 23:05 — fermé
])
def test_fx_session_open(dt, expected):
    assert fx_session_open(dt) is expected


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        fx_session_open(datetime(2026, 6, 12, 20, 0))


def test_beyond_table_fails_open():
    assert fx_session_open(_utc(2027, 6, 5, 12, 0)) is True   # samedi, mais repli OUVERT
