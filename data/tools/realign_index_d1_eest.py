#!/usr/bin/env python3
"""realign_index_d1_eest.py — réaligne la convention de clôture D1 des INDICES
(US100, GER40) du panneau gelé `panel_px.parquet` sur la frontière jour-serveur EEST
du feed FTMO live, en les reconstruisant depuis le dernier bar M5 du jour.

Contexte (Mission 3, 2026-06-19 ; cf. ftmo_live/SEAM_GER40_INVESTIGATION_2026-06-16.md) :
le panneau gelé construit les colonnes indices avec une convention d'heure-de-clôture D1
≠ de celle du broker FTMO (EEST) → seam au raccord (GER40 ~96.7 bps, US100 ~30.5 bps,
audit.data.seams_bps). Le M5 source du sim (sim_m5_repaired.parquet) est DÉJÀ en EEST :
son dernier bar du jour == la clôture D1 du broker (vérifié 511 dates, médiane 0.000 bps
vs export EA). Le fix reconstruit donc panel_px[US100,GER40] = dernier bar M5 du jour.

PORTÉE STRICTE :
  - SEULEMENT US100 + GER40. JAMAIS XAUUSD/USDJPY (qui ALIMENTENT le signal
    build_signals — les toucher changerait WT). Les indices N'entrent PAS dans WT
    (poids fixe on_w=0.6 overnight) → réalignement signal-invariant (vérifié ici).
  - Reconstruit aussi panel_rets[US100,GER40] = pct_change du px réaligné (sémantique
    panel ; ces rets ne sont lues NI par build_signals NI par les 462 cohortes/load_market).
  - Étend la couverture indices jusqu'à la fin du M5 (comble le trou 05-27→frozen_end).

Défaut = DRY-RUN (rapport AVANT/APRÈS, n'écrit rien). `--apply` réécrit panel_px +
panel_rets (cache gelé, gitignoré). NE PAS --apply sans GO (le panneau alimente le brain).

Usage:
  realign_index_d1_eest.py [--ea-json /tmp/ea_d1_closes.json] [--apply]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "data" / "ftmo_portfolio" / "cache"
CLEANROOM = REPO / "data" / "ftmo_portfolio" / "audit_v2_independent" / "cleanroom"

INDEX_LEGS = ["US100", "GER40"]          # SEULS légs réalignés (jamais XAU/USDJPY)
SIGNAL_LEGS = ["XAUUSD", "USDJPY"]
SEAM_LOOKBACK = 5                        # idem lib/marketdata._seam_bps


def _eest_d1(m5: pd.DataFrame, leg: str) -> pd.Series:
    """Clôture D1 EEST = dernier bar M5 du jour (convention serveur FTMO)."""
    s = m5[leg].dropna()
    d1 = s.groupby(s.index.normalize()).last()
    d1.index = pd.DatetimeIndex(d1.index)
    return d1


def _seam_bps(frozen: pd.Series, live: pd.Series, lookback: int = SEAM_LOOKBACK) -> dict:
    common = frozen.dropna().index.intersection(live.dropna().index)
    if len(common) == 0:
        return dict(n=0, tail_max=float("nan"), all_max=float("nan"), all_med=float("nan"))
    bps = (live[common] / frozen[common] - 1.0).abs() * 1e4
    tail = common[-lookback:]
    return dict(n=len(common),
                tail_max=float(bps[tail].max()),          # ce que marketdata loggue
                all_max=float(bps.max()), all_med=float(bps.median()))


def _load_ea(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = json.load(open(path))
    out = {}
    for leg, d in raw.items():
        out[leg] = pd.Series({pd.Timestamp(k.replace(".", "-")): float(v)
                              for k, v in d.items()}).sort_index()
    return out


def _wt_invariance(px_realigned: pd.DataFrame) -> dict:
    """build_signals (cleanroom) sur cache courant vs cache réaligné → WT identique ?"""
    if not (CLEANROOM / "engine.py").exists():
        return dict(checked=False, reason="cleanroom engine absent")
    sys.path.insert(0, str(CLEANROOM))
    import engine as E
    wt0, on0 = E.build_signals()
    tmp = Path(tempfile.mkdtemp()) / "cache"
    tmp.mkdir(parents=True)
    for f in CACHE.glob("*.parquet"):
        shutil.copy(f, tmp / f.name)
    px_realigned.to_parquet(tmp / "panel_px.parquet")
    saved = E.CACHE
    E.CACHE = tmp
    try:
        wt1, on1 = E.build_signals()
    finally:
        E.CACHE = saved
    return dict(checked=True, wt_identical=bool(wt0.equals(wt1)),
                on_identical=bool(on0.equals(on1)),
                wt_cols=list(wt0.columns),
                wt_tail=wt0.dropna(how="all").tail(2).round(6).to_dict())


def run(ea_json: Path, apply: bool) -> None:
    px = pd.read_parquet(CACHE / "panel_px.parquet")
    rets = pd.read_parquet(CACHE / "panel_rets.parquet")
    m5 = pd.read_parquet(CACHE / "sim_m5_repaired.parquet")
    ea = _load_ea(ea_json)

    print("=" * 78)
    print("M3 — RÉALIGNEMENT D1 INDICES (US100, GER40) SUR LA FRONTIÈRE EEST — DRY-RUN"
          if not apply else
          "M3 — RÉALIGNEMENT D1 INDICES (US100, GER40) — APPLY (écriture cache gelé)")
    print("=" * 78)

    realigned = {leg: _eest_d1(m5, leg) for leg in INDEX_LEGS}
    px_new = px.copy()

    print("\n[1] SEAM vs export EA (broker EEST) — AVANT (panneau actuel) → APRÈS (M5-EEST)")
    for leg in INDEX_LEGS:
        if leg in ea:
            b = _seam_bps(px[leg], ea[leg])
            a = _seam_bps(realigned[leg], ea[leg])
            print(f"  {leg}: AVANT tail_max {b['tail_max']:.1f} | all med {b['all_med']:.2f} "
                  f"max {b['all_max']:.1f} bps  →  APRÈS tail_max {a['tail_max']:.2f} | "
                  f"all med {a['all_med']:.3f} max {a['all_max']:.1f} bps  (n={a['n']})")
        else:
            print(f"  {leg}: (pas d'export EA fourni — passe la validation seam)")

    print("\n[2] COUVERTURE D1 indices — AVANT (panneau) → APRÈS (M5)")
    for leg in INDEX_LEGS:
        last_before = px[leg].dropna().index.max()
        last_after = realigned[leg].dropna().index.max()
        print(f"  {leg}: AVANT dernière date {last_before.date()} → APRÈS {last_after.date()}"
              f"  (+{(realigned[leg].dropna().index > last_before).sum()} jours comblés)")

    # construire le panneau réaligné (px + rets) pour les légs indices, sur la plage M5
    idx_union = px.index.union(pd.DatetimeIndex(
        sorted(set().union(*[set(realigned[l].index) for l in INDEX_LEGS]))))
    px_new = px_new.reindex(idx_union)
    for leg in INDEX_LEGS:
        r = realigned[leg]
        px_new.loc[r.index, leg] = r.values
    rets_new = rets.reindex(idx_union)
    for leg in INDEX_LEGS:
        rets_new[leg] = px_new[leg].pct_change()

    print("\n[3] INVARIANCE DU SIGNAL — build_signals (WT = XAUUSD,USDJPY) AVANT vs APRÈS")
    inv = _wt_invariance(px_new)
    if inv.get("checked"):
        print(f"  WT colonnes: {inv['wt_cols']} (les indices N'y sont PAS)")
        print(f"  WT identique: {inv['wt_identical']} | ON identique: {inv['on_identical']}")
        print(f"  WT (derniers jours): {inv['wt_tail']}")
        print(f"  → réalignement indices SIGNAL-INVARIANT: "
              f"{'CONFIRMÉ ✓' if inv['wt_identical'] and inv['on_identical'] else 'ÉCHEC ✗'}")
    else:
        print(f"  (non vérifié: {inv.get('reason')})")

    print("\n[4] IMPACT SIZING INDICES — notionnel GER40/US100 = on_w×scale×eq "
          "(PRIX-INDÉPENDANT)\n  → notionnel inchangé ; lots live quantifiés au PRIX LIVE "
          "(state.symbol_specs), pas au panneau. Le panneau indices ne sert qu'au seam-warn,\n"
          "  au forecast de swap, et au px-fallback brain (si prix live manquant).")

    if apply:
        # sauvegarde + écriture
        for name, df in (("panel_px", px_new), ("panel_rets", rets_new)):
            bak = CACHE / f"{name}.parquet.pre_realign_backup"
            if not bak.exists():
                shutil.copy(CACHE / f"{name}.parquet", bak)
            df.to_parquet(CACHE / f"{name}.parquet")
        print(f"\n[APPLY] panel_px + panel_rets réécrits (backup *.pre_realign_backup). "
              f"Relancer brain --dry-run pour vérifier seams_bps < 30.")
    else:
        print("\n[DRY-RUN] aucune écriture. `--apply` pour réécrire (cache gelé) APRÈS GO.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea-json", default="/tmp/ea_d1_closes.json", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    run(a.ea_json, a.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
