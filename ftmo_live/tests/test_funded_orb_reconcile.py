"""Régression 2026-08-24 — audit reconcile ORB funded.

Incident réel (compte <ACCOUNT_ID>, funded, 2026-08-21) : un trade réel du sleeve
funded ORB (magic MAGIC_FORB, fills `funded_orb_entry`/`funded_orb_exit`) a perdu
$23.37 alors que le modèle prédisait $0.00 pile. Cause : `lib/replay.py` ne
simulait QUE le micro-ORB challenge (`_micro_model`, gated sur `cfg["micro_orb"]`,
False en FUNDED) — le sleeve funded ORB (`cfg["orb_risk"]`, magic MAGIC_FORB)
n'était modélisé NULLE PART. Et `reconcile.py::_decompose` ne filtrait les fills
que sur `reason.startswith("micro")`, qui exclut `funded_orb_*` par construction.
Résultat : tout le PnL réel du sleeve funded ORB partait dans le résiduel
inexpliqué (compteur STOP à 3 jours consécutifs) au lieu d'être expliqué par
Δ_micro.

Ces tests répliquent le jour 2026-08-21 (aucune autre jambe, résiduel réel
-$23.11 pour PnL réel -$23.37) en synthétique et vérifient que, POST-correctif,
le sleeve funded ORB est modélisé et absorbé par Δ_micro (résiduel ~0, jour
expliqué)."""
import numpy as np
import pandas as pd
import pytest

import reconcile
from lib import LEGS
from lib import replay, statefiles

FUNDED_DAY = "2026-06-10"    # mercredi, pas ON


def _m5_forb_short_stop():
    """OR US100 15:30-16:00 (largeur ~10.3 bps, >= V2_MIN_WIDTH_BPS) ; casse à la
    baisse au 1er bar post-OR (16:00, entrée short) ; remonte immédiatement
    au-dessus de l'OR-high (16:05) -> stop touché (perte), sans jamais franchir
    le trail-to-BE (+1R)."""
    legs = {}
    times = [f"{h:02d}:{m:02d}" for h in range(0, 23) for m in range(0, 60, 5)]
    base = dict(XAUUSD=3300.0, USDJPY=145.0, US100=29000.0, GER40=24000.0)
    for l in LEGS:
        rows = []
        for t in times:
            v = base[l]
            if l == "US100":
                hm = int(t[:2]) * 100 + int(t[3:])
                if 1530 <= hm < 1600:
                    v = 29000.0 + (15.0 if t.endswith("5") else -15.0)  # or_hi/or_lo
                elif hm == 1600:
                    v = 28980.0                                          # casse basse
                elif hm > 1600:
                    v = 29020.0                                          # remonte -> stop
            rows.append([t, v])
        legs[l] = rows
    return legs


def test_replay_funded_orb_fires_and_prices_stop_loss():
    """Le modèle doit désormais exposer `funded_orb` (armé, déclenché, perte),
    quand avant ce correctif la clé n'existait pas et son PnL était invisible."""
    r = replay.replay_day(pd.Timestamp(FUNDED_DAY), "FUNDED", pd.Timestamp("2026-06-08"),
                          10000.0, np.zeros(4), np.full(4, np.nan),
                          (0.0, 0.0), False, _m5_forb_short_stop())
    assert "funded_orb" in r
    fo = r["funded_orb"]
    assert fo["armed"] and fo["fired"]
    assert fo["direction"] == -1                 # cassure basse = short
    assert fo["entry"] == fo["or_lo"]
    assert fo["exit"]["exit_px"] == fo["or_hi"]   # stop (pas BE)
    assert fo["pnl_usd"] < 0                       # perte, comme le trade réel du 21/08
    assert r["model_equity"] == pytest.approx(10000.0 + fo["pnl_usd"], abs=1e-6)


def test_replay_funded_orb_never_fires_in_challenge():
    """Non-régression : challenge.config a orb_risk=0.0 -> funded_orb ne doit
    jamais s'armer (mutuelle exclusivité avec le micro-ORB, mq5:170-171)."""
    r = replay.replay_day(pd.Timestamp(FUNDED_DAY), "P1", pd.Timestamp("2026-06-08"),
                          10000.0, np.zeros(4), np.full(4, np.nan),
                          (0.0, 0.0), False, _m5_forb_short_stop())
    assert not r["funded_orb"]["armed"]
    assert not r["funded_orb"]["fired"]


def _seed_funded_orb_day(files_dir, runtime, day, entry_px, exit_px, lots):
    """Jour FUNDED synthétique : SEUL le sleeve funded ORB trade (mêmes conditions
    que 2026-08-21 : n_fills=2, aucune autre jambe)."""
    m5 = _m5_forb_short_stop()
    statefiles.atomic_write_json(files_dir / "m5_today.json", dict(date=day, legs=m5))
    statefiles.atomic_write_json(files_dir / "targets.json", dict(
        schema="ftmo_live.targets.v1", ea_spec_sha256="x" * 64,
        ea_generated_at_paris=f"{day.replace('-', '.')} 21:50:00",
        ea_valid_for_date=day, ea_phase_hint="FUNDED",
        ea_w_xauusd=0.0, ea_w_usdjpy=0.0, ea_on_day=0))
    orb_pnl = (exit_px - entry_px) * -1.0 * lots      # short: SELL entry, BUY exit
    bal_real = 10000.0 + orb_pnl
    state = dict(schema="ftmo_live.state.v1",
                 ts_paris=f"{day.replace('-', '.')} 23:00:00", phase="FUNDED",
                 attempt_start="2026-06-08", balance=bal_real, equity=bal_real,
                 anchor_balance=10000.0, symbol_specs={},
                 last_rebalance=None,
                 eod=dict(date=day, balance=bal_real, equity=bal_real, positions=[]),
                 positions=[])
    statefiles.atomic_write_json(files_dir / "state.json", state)
    sod = runtime / "sod"
    sod.mkdir(exist_ok=True, parents=True)
    statefiles.atomic_write_json(sod / f"state_{day}.json", dict(
        balance=10000.0, anchor_balance=10000.0, positions=[]))
    for reason, side, px in (("funded_orb_entry", "SELL", entry_px),
                             ("funded_orb_exit", "BUY", exit_px)):
        statefiles.append_csv(files_dir / "fills.csv", statefiles.FILLS_COLUMNS, dict(
            ts_server="", ts_paris=f"{day.replace('-', '.')} 17:14:06", phase=3,
            reason=reason, symbol="US100.cash", side=side, lots=lots,
            req_price=px, fill_price=px, slip_bps=0.0, latency_ms=0, magic=220512))


def test_reconcile_funded_orb_day_no_longer_unexplained(files_dir, runtime_isolated):
    """AVANT le correctif : ce jour aurait été INEXPLIQUÉ (résiduel == PnL réel
    de l'ORB, exactement le motif du 2026-08-21 réel : PnL réel -$23.37, modèle
    $0.00, résiduel -$23.11 > tolérance $5.64). APRÈS : le sleeve funded ORB est
    modélisé -> résiduel ~0, jour expliqué."""
    entry_px, exit_px, lots = 28985.0, 29015.0, 0.83     # = sortie exacte du modèle
    _seed_funded_orb_day(files_dir, runtime_isolated, FUNDED_DAY, entry_px, exit_px, lots)
    row = reconcile.run(FUNDED_DAY, alert=False)
    assert row["pnl_real"] < 0                            # perte réelle, comme le 21/08
    assert row["unexplained"] == 0
    assert abs(row["residual_usd"]) <= row["tol_usd"]
    assert row["consec_unexplained"] == 0
