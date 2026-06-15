"""Régression chemin PRODUCTION (non dry-run) — incident 2026-06-15.

Le brain de 21:50 plantait sur `KeyError('account')` : la boucle d'export
`for leg, sp in export["symbols"].items()` réutilisait `sp` (la spec chargée),
si bien qu'à la l.110 `spec.account_size(sp)` recevait le dict de la DERNIÈRE
jambe (GER40, sans clé 'account'). Les tests dry-run ne couvrent PAS cette
branche (state=None, --balance fourni) — d'où ce test dédié qui pilote le vrai
`run(dry_run=False)` avec un Files dir frais (export multi-jambes + state),
SANS écrire de targets (write=False).
"""
import json

import numpy as np
import pandas as pd

import brain
from lib import LEGS, marketdata, statefiles


def _write_fresh_files(files_dir, target_date):
    """market_export.json (4 jambes, AUCUNE ne porte 'account') + state.json frais."""
    px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")
    tail = px.index[-40:]
    now = statefiles.now_paris().replace(tzinfo=None)
    symbols = {}
    for leg in LEGS:
        closes = px[leg].reindex(tail).ffill().bfill()
        d1 = [[d.strftime("%Y.%m.%d"), float(c), float(c), float(c), float(c), 0]
              for d, c in closes.items()]
        symbols[leg] = dict(
            broker_symbol=leg, digits=2, contract=1.0, tick_value=1.0,
            tick_size=0.01, swap_long=-1.0, swap_short=-1.0, swap_mode=0,
            swap_r3d=3 if leg in ("XAUUSD", "USDJPY") else 5,
            margin_rate_live=0.05, d1=d1)
    export = dict(generated_at_paris=statefiles.fmt_ts(now),
                  server_minus_paris_min=60,
                  account=dict(balance=10000.0, equity=10000.0, phase=1),
                  symbols=symbols)
    (files_dir / "market_export.json").write_text(json.dumps(export))
    state = dict(schema=statefiles.STATE_SCHEMA, ts_paris=statefiles.fmt_ts(now),
                 phase="P1", attempt_start=str(target_date.date()),
                 balance=10000.0, equity=10000.0, positions=[], symbol_specs={})
    (files_dir / "state.json").write_text(json.dumps(state))


def test_production_path_no_account_keyerror(tmp_path, files_dir):
    px = pd.read_parquet(marketdata.FROZEN_CACHE / "panel_px.parquet")
    target_date = pd.bdate_range(px.index.max() + pd.Timedelta(days=1), periods=1)[0]
    _write_fresh_files(files_dir, target_date)

    # balance=None (défaut prod) => exerce le fallback l.110 qui plantait.
    res = brain.run(dry_run=False, as_of=str(target_date.date()),
                    cache_dir=tmp_path / "cache", write=False)

    assert res["status"] == "OK"
    assert res["written"] is None, "write=False ne doit RIEN écrire dans Files"
    prev = res["targets"]["audit"]["governor_preview"]
    # la balance vient bien du state (10000), pas d'un crash spec
    assert prev["bal_used"] == 10000.0
    tq = prev["targets_usd_quantized"]
    assert set(tq) == set(LEGS)
    for leg, v in tq.items():
        assert np.isfinite(v), f"{leg} target non fini: {v}"
    assert np.isfinite(res["targets"]["ea_w_xauusd"])
    assert np.isfinite(res["targets"]["ea_w_usdjpy"])
