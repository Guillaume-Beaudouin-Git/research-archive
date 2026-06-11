"""Dry-run brain vs cibles du SIMULATEUR (mission, tolérance = quantization).

(a) Poids : pipeline brain (panels tronqués causaux + ligne NaN à T) == WT du
    sim sur le stack complet, 10 derniers jours, tolérance 0.
(b) Cibles : engine_v22.run_phase instrumenté (E._target_for_segment espionné)
    sur une cohorte couvrant ces jours ; pour chaque décision s∈{3,4}, le
    gouverneur brain (mêmes états bal/pos/avg/px, poids BRAIN) doit reproduire
    la cible quantisée du moteur.
"""
import numpy as np
import pandas as pd
import pytest

import engine as E
import engine_v22 as V22
import config_v22 as C22
from lib import LIVE_CACHE
from lib import governor, marketdata, signals

N_DAYS = 10


@pytest.fixture(scope="module")
def frozen():
    WT, ON = E.build_signals()
    px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")
    return dict(WT=WT, ON=ON, dates=px.index[-N_DAYS:])


@pytest.fixture(scope="module")
def brain_weights(frozen):
    out = {}
    for d in frozen["dates"]:
        cache = LIVE_CACHE / f"test_equiv_{d.date()}"
        marketdata.build_truncated_cache(d, cache)
        row, diag = signals.weights_for(d, cache)
        out[d] = (float(row["XAUUSD"]), float(row["USDJPY"]), bool(diag["on_day"]))
    return out


def test_weights_equal_sim_aligned(frozen, brain_weights):
    for d in frozen["dates"]:
        wx, wj, on = brain_weights[d]
        ref = frozen["WT"].loc[d]
        assert wx == pytest.approx(float(ref["XAUUSD"]), abs=1e-12)
        assert wj == pytest.approx(float(ref["USDJPY"]), abs=1e-12)
        assert on == bool(frozen["ON"].loc[d] > 0)


def test_targets_match_instrumented_engine(frozen, brain_weights, monkeypatch):
    """Chaîne de tentatives depuis n-30 (états riches: pos/avg/bal en vol) ;
    chaque décision s∈{3,4} reproduite par le gouverneur brain — poids BRAIN
    (pipeline complet) dans la fenêtre des 10 derniers jours, poids sim ailleurs
    (l'égalité des poids est prouvée séparément par test_weights_equal_sim)."""
    M = V22.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WTa, ONa = V22.align(M, frozen["WT"], frozen["ON"])
    i0 = M["n"] - 30
    records = []
    orig = E._target_for_segment

    def spy(s, i, Mx, WT, ON, cfg, bal, pos, avg, px0, ii0, vm):
        tgt, opened = orig(s, i, Mx, WT, ON, cfg, bal, pos, avg, px0, ii0, vm)
        if s in (3, 4) and tgt is not None:
            records.append(dict(s=s, i=i, bal=bal, pos=pos.copy(), avg=avg.copy(),
                                px=np.array(px0, float), tgt=np.array(tgt, float),
                                i0=ii0))
        return tgt, opened

    monkeypatch.setattr(E, "_target_for_segment", spy)
    cfg = dict(C22.CFG_CHALLENGE, target=E.TARGET1, max_cal=C22.WALL)
    i = i0
    while i < M["n"] - 1:                      # chaîne de tentatives (funnel sim)
        r = V22.run_phase(M, i, WTa, ONa, cfg)
        i = max(int(r["last"]) + 2, i + 1)
    monkeypatch.setattr(E, "_target_for_segment", orig)
    assert len(records) >= 8, "fenêtre trop courte pour le test"

    cfg_brain = governor.phase_cfg("P1")
    n_checked = n_brain = 0
    for r in records:
        d = pd.Timestamp(M["dates"][r["i"]])
        if d in brain_weights:
            wx, wj, on = brain_weights[d]
            n_brain += 1
        else:
            ref = frozen["WT"].loc[d]
            wx, wj = float(ref["XAUUSD"]), float(ref["USDJPY"])
            on = bool(frozen["ON"].loc[d] > 0)
        tgt_brain, _ = governor._call(
            r["s"], cfg_brain, (wx, wj), 1.0 if on else 0.0, r["bal"],
            r["pos"], r["avg"], r["px"], pd.Timestamp(M["dates"][r["i0"]]), d,
            quantize=True, margin_cap=cfg_brain.get("margin_cap"))
        assert np.allclose(np.asarray(tgt_brain), r["tgt"], atol=1e-6), \
            f"cible brain != sim au {d.date()} s={r['s']}"
        n_checked += 1
    assert n_checked >= 8 and n_brain >= 3
