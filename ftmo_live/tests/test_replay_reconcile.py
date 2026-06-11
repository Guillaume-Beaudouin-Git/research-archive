"""Replay un-jour (atomes sim) + réconciliation bout-en-bout sur journée
synthétique : résiduel ~0 quand réel == modèle ; gate STOP à 3 jours."""
import json

import numpy as np
import pandas as pd
import pytest

import reconcile
from lib import LEGS
from lib import replay, statefiles

DAY = "2026-06-09"          # mardi (jour ON) -- non, 06-09 = mardi ; flat day choisi mercredi
FLAT_DAY = "2026-06-10"     # mercredi (pas ON)


def _m5(flat=True, breakout=False):
    """Journée M5 synthétique 00:00-22:55 ; US100 peut casser l'OR à la hausse."""
    legs = {}
    times = [f"{h:02d}:{m:02d}" for h in range(0, 23) for m in range(0, 60, 5)]
    base = dict(XAUUSD=3300.0, USDJPY=145.0, US100=21500.0, GER40=24000.0)
    for l in LEGS:
        rows = []
        for t in times:
            v = base[l]
            if breakout and l == "US100":
                hm = int(t[:2]) * 100 + int(t[3:])
                if 1530 <= hm < 1600:
                    v = 21500.0 + (15 if t.endswith("5") else -15)  # OR 30 pts ~14 bps
                elif hm >= 1600:
                    v = 21540.0                                     # cassure haute
            rows.append([t, v])
        legs[l] = rows
    return legs


def test_replay_flat_day_rebalance_only():
    r = replay.replay_day(pd.Timestamp(FLAT_DAY), "P1", pd.Timestamp("2026-06-08"),
                          10000.0, np.zeros(4), np.full(4, np.nan),
                          (0.3, 1.0), False, _m5())
    segs = [t["seg"] for t in r["trades"]]
    assert segs == [4]
    assert not r["micro"]["fired"]            # pas de breakout, largeur nulle
    assert r["events"] == []
    cost = r["trades"][0]["cost_model_usd"]
    assert r["model_equity"] == pytest.approx(10000.0 - cost, abs=1e-6)


def test_replay_micro_fires_on_breakout_day():
    r = replay.replay_day(pd.Timestamp(FLAT_DAY), "P1", pd.Timestamp("2026-06-08"),
                          10000.0, np.zeros(4), np.full(4, np.nan),
                          (0.0, 0.0), False, _m5(breakout=True))
    m = r["micro"]
    assert m["armed"] and m["fired"] and m["direction"] == 1
    assert m["entry"] == pytest.approx(m["or_hi"])


def test_replay_on_day_holds_ger40_and_us100():
    r = replay.replay_day(pd.Timestamp("2026-06-08"), "P1",        # lundi
                          pd.Timestamp("2026-06-08"), 10000.0, np.zeros(4),
                          np.full(4, np.nan), (0.0, 0.0), True, _m5())
    segs = [t["seg"] for t in r["trades"]]
    assert segs == [3, 4]
    assert r["model_pos_usd"]["GER40"] > 0    # tenu overnight
    assert r["model_pos_usd"]["US100"] > 0
    assert not r["micro"]["fired"]            # jour ON: jamais (605f4a4)


def _seed_files(files_dir, runtime, day, residual_usd=0.0):
    """Fabrique une journée cohérente réel==modèle (+ residual injecté)."""
    m5 = _m5()
    (files_dir / "m5_today.json").write_text(json.dumps(dict(date=day, legs=m5)))
    statefiles.atomic_write_json(files_dir / "targets.json", dict(
        schema="ftmo_live.targets.v1", ea_spec_sha256="x" * 64,
        ea_generated_at_paris=f"{day.replace('-', '.')} 21:50:00",
        ea_valid_for_date=day, ea_phase_hint="P1",
        ea_w_xauusd=0.3, ea_w_usdjpy=1.0, ea_on_day=0))
    mod = replay.replay_day(pd.Timestamp(day), "P1", pd.Timestamp("2026-06-08"),
                            10000.0, np.zeros(4), np.full(4, np.nan),
                            (0.3, 1.0), False, m5)
    t4 = mod["trades"][0]
    eod_px = mod["eod_px"]
    positions = []
    for l in LEGS:
        usd = t4["tgt"][l]
        if usd == 0.0:
            continue
        positions.append(dict(leg=l, symbol=l, lots=1.0, dir=1 if usd > 0 else -1,
                              avg=t4["px"][l], notional_usd=abs(usd), swap_acc=0))
    mtm = sum(abs(p["notional_usd"]) * (eod_px[p["leg"]] / p["avg"] - 1.0)
              * p["dir"] for p in positions)
    # fills réels à prix modèle SANS slippage -> le réel n'a pas payé le half-RT
    # que le modèle déduit ; cohérence: bal_real = modèle + coût modèle (+injection)
    cost_model = sum(t.get("cost_model_usd", 0.0) for t in mod["trades"])
    bal_real = mod["model_balance"] + cost_model + residual_usd
    state = dict(schema="ftmo_live.state.v1",
                 ts_paris=f"{day.replace('-', '.')} 23:00:00", phase="P1",
                 attempt_start="2026-06-08", balance=bal_real,
                 equity=bal_real + mtm, anchor_balance=10000.0,
                 symbol_specs={l: dict(tick_value=0.01, tick_size=0.01, price=100.0)
                               for l in LEGS},
                 last_rebalance=dict(ts="", eq_used=10000.0, scale=0.0,
                                     targets_usd=t4["tgt"]),
                 eod=dict(date=day, balance=bal_real, equity=bal_real + mtm,
                          positions=positions),
                 positions=positions)
    statefiles.atomic_write_json(files_dir / "state.json", state)
    sod = runtime / "sod"
    sod.mkdir(exist_ok=True, parents=True)
    statefiles.atomic_write_json(sod / f"state_{day}.json", dict(
        balance=10000.0, anchor_balance=10000.0, positions=[]))
    # fills réels EXACTEMENT au modèle (prix M5 22:05, pas de slippage)
    for l in LEGS:
        usd = t4["tgt"][l]
        if usd == 0.0:
            continue
        statefiles.append_csv(files_dir / "fills.csv", statefiles.FILLS_COLUMNS, dict(
            ts_server="", ts_paris=f"{day.replace('-', '.')} 22:05:30", phase=1,
            reason="rebalance", symbol=l, side="BUY" if usd > 0 else "SELL",
            lots=abs(usd) / 100.0, req_price=t4["px"][l], fill_price=t4["px"][l],
            slip_bps=0.0, latency_ms=4000, magic=220500))
    return mod


def test_reconcile_clean_day(files_dir, runtime_isolated):
    _seed_files(files_dir, runtime_isolated, FLAT_DAY)
    row = reconcile.run(FLAT_DAY, alert=False)
    assert row["unexplained"] == 0
    assert abs(row["residual_usd"]) <= row["tol_usd"]
    assert row["consec_unexplained"] == 0
    assert (runtime_isolated / "eod" / f"reconcile_{FLAT_DAY}.json").exists()


def test_reconcile_three_strikes_stop(files_dir, runtime_isolated):
    days = ["2026-06-10", "2026-06-11", "2026-06-12"]
    last = None
    for d in days:
        for f in ("fills.csv",):
            p = files_dir / f
            if p.exists():
                p.unlink()
        _seed_files(files_dir, runtime_isolated, d, residual_usd=500.0)
        last = reconcile.run(d, alert=False)
        assert last["unexplained"] == 1
    assert last["consec_unexplained"] == 3
    assert last["stop_recommended"] == 1
