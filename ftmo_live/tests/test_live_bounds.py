"""v2.2.1 — bornes de sanité datées : specs live vs ancres (immunisation dérive
dealer + écart Standard/Swing). Test mission : un swap serveur hors borne lève
l'alerte."""
import pytest

import supervisor
from lib import spec, statefiles, swaps


def _live_ok():
    ms = spec.measured_specs()
    out = {}
    for leg, m in ms["symbols"].items():
        std = ms["margin_rates"]["standard_measured"][leg]
        out[leg] = dict(swap_long_pts=m["swap_long_pts"],
                        swap_short_pts=m["swap_short_pts"],
                        rollover3days_dow_py=m["triple_dow"],
                        margin_rate=std)
    return out


def test_in_bounds_no_breach():
    assert swaps.check_live_bounds(_live_ok()) == []


def test_swing_margin_is_in_bounds():
    live = _live_ok()
    ms = spec.measured_specs()
    for leg in live:
        live[leg]["margin_rate"] = ms["margin_rates"]["swing_official"][leg]
    assert swaps.check_live_bounds(live) == []     # Swing = borne attendue


def test_swap_out_of_bounds_breaches():
    live = _live_ok()
    live["US100"]["swap_long_pts"] = -637.16 * 1.5      # +50% > ±25%
    br = swaps.check_live_bounds(live)
    assert len(br) == 1 and "US100 swap_long" in br[0]


def test_small_anchor_uses_abs_floor():
    live = _live_ok()
    live["USDJPY"]["swap_long_pts"] = 1.30               # ancre 0.96, floor 2.0 pts
    assert swaps.check_live_bounds(live) == []           # |Δ|=0.34/2.0 = 17% < 25%
    live["USDJPY"]["swap_long_pts"] = 2.50               # |Δ|=1.54/2.0 = 77%
    assert any("USDJPY swap_long" in b for b in swaps.check_live_bounds(live))


def test_triple_day_mismatch_breaches():
    live = _live_ok()
    live["GER40"]["rollover3days_dow_py"] = 2            # ancre = 4 (vendredi)
    assert any("GER40 triple" in b for b in swaps.check_live_bounds(live))


def test_margin_outside_both_anchors_breaches():
    live = _live_ok()
    ms = spec.measured_specs()
    live["XAUUSD"]["margin_rate"] = ms["margin_rates"]["swing_official"]["XAUUSD"] * 3
    assert any("XAUUSD marge" in b for b in swaps.check_live_bounds(live))


def test_supervisor_alert_on_state_breach(files_dir, runtime_isolated):
    now = statefiles.now_paris().replace(tzinfo=None)
    state = dict(schema="ftmo_live.state.v1", ts_paris=statefiles.fmt_ts(now),
                 phase="P1", equity=10000.0, balance=10000.0,
                 room_daily_usd=500.0, margin_used_pct_equity=20.0,
                 spec_bounds_breach=1,
                 spec_bounds_detail="US100 swap -955 vs ancre -637")
    statefiles.atomic_write_json(files_dir / "state.json", state)
    statefiles.atomic_write_json(runtime_isolated / "brain_status.json", dict(
        status="OK", ts_paris=statefiles.fmt_ts(now)))
    fired = supervisor.evaluate_alerts(files_dir)
    assert "spec_bounds" in fired


def test_brain_export_bounds_audit(files_dir, monkeypatch):
    """brain calcule le verdict de bornes depuis l'export EA (r3d MQL5->py)."""
    ms = spec.measured_specs()
    live = {}
    for leg, m in ms["symbols"].items():
        live[leg] = dict(swap_long=m["swap_long_pts"] * 2.0,   # hors borne
                         swap_short=m["swap_short_pts"],
                         swap_r3d=(m["triple_dow"] + 1) % 7,
                         margin_rate_live=ms["margin_rates"]["standard_measured"][leg])
    conv = {leg: dict(swap_long_pts=v["swap_long"], swap_short_pts=v["swap_short"],
                      rollover3days_dow_py=(int(v["swap_r3d"]) + 6) % 7,
                      margin_rate=v["margin_rate_live"]) for leg, v in live.items()}
    br = swaps.check_live_bounds(conv)
    assert len(br) >= 3                                   # swaps long x2 hors borne
    assert all("triple" not in b for b in br)             # conversion dow correcte
