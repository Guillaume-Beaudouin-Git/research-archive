"""Modèle swap (ancres yaml x triple-days) + construction du cache live."""
import json

import numpy as np
import pandas as pd
import pytest

from lib import LEGS
from lib import marketdata, spec, swaps


# ---------------------------------------------------------------- swaps
def test_night_multiplier_rule():
    fri = pd.Timestamp("2026-06-12")
    wed = pd.Timestamp("2026-06-10")
    assert swaps.night_multiplier("US100", fri) == 3
    assert swaps.night_multiplier("GER40", fri) == 3
    assert swaps.night_multiplier("US100", wed) == 1
    assert swaps.night_multiplier("XAUUSD", wed) == 3
    assert swaps.night_multiplier("USDJPY", wed) == 3
    assert swaps.night_multiplier("XAUUSD", fri) == 1


def test_multiplier_agrees_with_frozen_panel():
    mu = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_mult.parquet")
    tail = mu[LEGS].tail(300).dropna()
    agree = np.mean([[swaps.night_multiplier(l, d) == tail.loc[d, l]
                      for l in LEGS] for d in tail.index])
    assert agree >= 0.95          # écarts = jours fériés décalant le triple


def test_forecast_night_matches_measured_points():
    f = swaps.forecast_night({"US100": 84000.0}, pd.Timestamp("2026-06-12"))
    bps = swaps.swap_bps("US100", "long")
    assert f["per_leg"]["US100"]["usd"] == pytest.approx(84000 * bps / 1e4 * 3, abs=0.01)
    assert f["per_leg"]["US100"]["measured"] is True
    # prix-aware: à prix double, bps moitié
    assert swaps.swap_bps("US100", "long", 2 * spec.measured_specs()["ref_px"]["US100"]) \
        == pytest.approx(bps / 2)


def test_all_sides_measured_v221():
    for leg in LEGS:
        for side in ("long", "short"):
            bps, measured = swaps.anchor_bps(leg, side)
            assert measured and bps is not None


def test_swap_bps_reconstructs_billed_night():
    """4/4 au centime (gate G0 du recost) — nuit 10->11/06, mercredi x3."""
    ms = spec.measured_specs()
    refpx = ms["ref_px"]
    # XAU 0.01 lot x3 = -$1.97
    usd = swaps.swap_bps("XAUUSD", "long") / 1e4 * 100 * refpx["XAUUSD"] * 0.01 * 3
    assert usd == pytest.approx(-1.97, abs=0.005)
    # US100 0.1 lot x1 = -$0.64
    usd = swaps.swap_bps("US100", "long") / 1e4 * refpx["US100"] * 0.1
    assert usd == pytest.approx(-0.64, abs=0.005)


def test_billed_vs_model_gate():
    r = swaps.billed_vs_model({"US100": -8.0}, {"US100": -6.0})
    assert r["gate_breach"] and r["total_drift_pct"] == pytest.approx(33.3, abs=0.1)
    r2 = swaps.billed_vs_model({"US100": -6.4}, {"US100": -6.0})
    assert not r2["gate_breach"]


# ---------------------------------------------------------------- marketdata
def _export(frozen_end, days, seam_shift=0.0):
    sym = {}
    for l in LEGS:
        px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")[l].dropna()
        rows = [[d.strftime("%Y.%m.%d"), 0, 0, 0, float(px.iloc[-1] * (1 + seam_shift))]
                for d in px.index[-3:]]
        for i, d in enumerate(days):
            rows.append([d.strftime("%Y.%m.%d"), 0, 0, 0,
                         float(px.iloc[-1]) * (1.0 + 0.001 * (i + 1))])
        sym[l] = dict(d1=rows)
    return dict(generated_at_paris=pd.Timestamp.now().strftime("%Y.%m.%d %H:%M:%S"),
                symbols=sym)


def test_build_live_cache_extension(tmp_path):
    px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")
    frozen_end = px.index.max()
    new_days = pd.bdate_range(frozen_end + pd.Timedelta(days=1), periods=3)
    target = new_days[-1] + pd.offsets.BDay(1)
    exp = _export(frozen_end, list(new_days))
    diag = marketdata.build_live_cache(exp, target, tmp_path / "cache")
    assert diag["n_extended"] == 3
    px2 = pd.read_parquet(tmp_path / "cache" / "panel_px.parquet")
    rets2 = pd.read_parquet(tmp_path / "cache" / "panel_rets.parquet")
    sL2 = pd.read_parquet(tmp_path / "cache" / "panel_swapL.parquet")
    mu2 = pd.read_parquet(tmp_path / "cache" / "panel_mult.parquet")
    assert pd.Timestamp(target) in px2.index          # ligne NaN à T
    assert np.isnan(px2.loc[target, "XAUUSD"])
    d0 = new_days[0]
    prev = px[ "XAUUSD"].dropna().iloc[-1]
    assert rets2.loc[d0, "XAUUSD"] == pytest.approx(
        px2.loc[d0, "XAUUSD"] / prev - 1.0, rel=1e-9)
    # extension swap v2.2.1 = points mesurés -> bps au prix du jour
    px_d1 = float(px2.loc[new_days[1], "US100"])
    assert sL2.loc[new_days[1], "US100"] == pytest.approx(
        swaps.swap_bps("US100", "long", px_d1), abs=1e-9)
    assert diag["swap_anchor_gap_bps"]["US100"] is not None
    for d in list(new_days) + [target]:
        for l in LEGS:
            assert mu2.loc[d, l] == swaps.night_multiplier(l, d)


def test_export_stale_raises(tmp_path):
    p = tmp_path / "market_export.json"
    p.write_text(json.dumps(dict(
        generated_at_paris="2026.06.01 21:45:00",
        symbols={l: {"d1": []} for l in LEGS})))
    with pytest.raises(marketdata.MarketDataError, match="stale"):
        marketdata.load_export(p, now=pd.Timestamp("2026-06-02 21:50").to_pydatetime())


def test_export_missing_leg_raises(tmp_path):
    p = tmp_path / "market_export.json"
    now = pd.Timestamp("2026-06-02 21:50")
    p.write_text(json.dumps(dict(
        generated_at_paris="2026.06.02 21:45:00",
        symbols={"XAUUSD": {"d1": []}})))
    with pytest.raises(marketdata.MarketDataError, match="manquantes"):
        marketdata.load_export(p, now=now.to_pydatetime())


def test_swap_anchor_gap_reported(tmp_path):
    """L'écart panel-gelé vs ancre mesurée (attendu post-recost, le prix a
    bougé) est rapporté en diag, jamais bloquant."""
    px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")
    frozen_end = px.index.max()
    new_days = pd.bdate_range(frozen_end + pd.Timedelta(days=1), periods=1)
    exp = _export(frozen_end, list(new_days))
    diag = marketdata.build_live_cache(exp, new_days[-1] + pd.offsets.BDay(1),
                                       tmp_path / "cache")
    gap = diag["swap_anchor_gap_bps"]
    assert set(gap) == set(LEGS)
    assert isinstance(diag["swap_anchor_gap_warn"], list)
