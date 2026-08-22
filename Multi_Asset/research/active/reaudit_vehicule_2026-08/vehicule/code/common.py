"""Plumbing commun — PROGRAMME 2 (question du véhicule).

Lecture seule sur tout chemin du dépôt principal. Écriture confinée à
`reaudit_vehicule_2026-08/vehicule/`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

INVENTORY = REPO / "Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.csv"

# ---------------------------------------------------------------- compte perso
EURUSD = 1.1522
ACCOUNT_EUR = 12_000.0
ACCOUNT_USD = ACCOUNT_EUR * EURUSD          # $13 826

# ------------------------------------------------------- commissions IBKR (USD)
# Source : `overnight_futures_2026-07/code/common.py` (all-in retail fixed / tiered).
COMM_SIDE_FIXED = 0.85
COMM_SIDE_TIERED = 0.50

# ------------------------------------------------------------- specs contrats
# notional = multiplicateur x prix de reference. Les marges overnight sont des
# ordres de grandeur broker (elles BOUGENT) : celles marquees `measured` viennent
# de la table live rafraichie le 2026-07-30 par `overnight_futures_2026-07`.
CONTRACTS = {
    # code       mult   px_ref    tick_usd  margin_usd  src_margin      famille
    "MGC":  dict(mult=10,      px=4070.90, tick=1.00,  margin=2308.0, msrc="measured 07-30", desc="Micro Gold 10oz COMEX"),
    "SIL":  dict(mult=1000,    px=58.164,  tick=5.00,  margin=6469.0, msrc="measured 07-30", desc="Micro Silver 1000oz"),
    "MCL":  dict(mult=100,     px=73.52,   tick=1.00,  margin=840.0,  msrc="measured 07-30", desc="Micro WTI 100bbl"),
    "MZS":  dict(mult=5.0,     px=1195.0,  tick=0.625, margin=210.0,  msrc="CME micro-ag spec", desc="Micro Soybean 500bu"),
    "ZS":   dict(mult=50.0,    px=1195.0,  tick=6.25,  margin=2100.0, msrc="ordre de grandeur", desc="Soybean 5000bu CBOT"),
    "MZW":  dict(mult=5.0,     px=599.5,   tick=0.625, margin=220.0,  msrc="ordre de grandeur", desc="Micro Wheat 500bu"),
    "ZW":   dict(mult=50.0,    px=599.5,   tick=12.50, margin=2200.0, msrc="ordre de grandeur", desc="Wheat 5000bu CBOT"),
    "MNQ":  dict(mult=2.0,     px=30000.0, tick=0.50,  margin=3200.0, msrc="ordre de grandeur", desc="Micro Nasdaq-100 $2/pt"),
    "MES":  dict(mult=5.0,     px=7350.0,  tick=1.25,  margin=2400.0, msrc="ordre de grandeur", desc="Micro S&P500 $5/pt"),
    "ZN":   dict(mult=1000.0,  px=112.0,   tick=15.625, margin=1800.0, msrc="month_end_vehicle 07-30", desc="10y T-Note $1000/pt"),
    "M6E":  dict(mult=12500.0, px=1.16,    tick=1.25,  margin=350.0,  msrc="ordre de grandeur", desc="Micro EUR/USD 12.5k EUR"),
    "6E":   dict(mult=125000.0, px=1.16,   tick=6.25,  margin=2900.0, msrc="ordre de grandeur", desc="EUR/USD 125k EUR"),
}
# ZS/ZW : prix en cents/boisseau -> notionnel = mult * px / 100 * 100 ... voir contract_specs()


def contract_specs(account_usd: float = ACCOUNT_USD) -> pd.DataFrame:
    """Notionnel, marge, coût RT en bps — la table L53/L57."""
    rows = []
    for code, c in CONTRACTS.items():
        px = c["px"]
        # grains cotés en cents/boisseau, ZN en points de 1/32 -> le multiplicateur
        # ci-dessus est déjà en USD par unité de cotation.
        notional = c["mult"] * px
        if code in ("MZS", "ZS", "MZW", "ZW"):
            notional = c["mult"] * px          # mult déjà = size/100 (cents -> USD)
        tick_bps = c["tick"] / notional * 1e4
        comm_bps = 2 * COMM_SIDE_FIXED / notional * 1e4
        comm_bps_t = 2 * COMM_SIDE_TIERED / notional * 1e4
        rows.append(dict(
            contract=code, desc=c["desc"],
            notional_usd=round(notional, 0),
            margin_usd=c["margin"], margin_src=c["msrc"],
            margin_pct_account=round(100 * c["margin"] / account_usd, 1),
            notional_x_account=round(notional / account_usd, 2),
            tick_bps=round(tick_bps, 3),
            comm_rt_bps_fixed=round(comm_bps, 3),
            comm_rt_bps_tiered=round(comm_bps_t, 3),
            rt_bps_base=round(tick_bps + comm_bps, 3),
            rt_bps_stress_2tick=round(2 * tick_bps + comm_bps, 3),
            # part du coût qui est du frais FIXE (le point L57)
            fixed_share_pct=round(100 * comm_bps / (tick_bps + comm_bps), 1),
        ))
    df = pd.DataFrame(rows)
    df["L53_margin_fits"] = np.where(df.margin_pct_account <= 100.0, "OUI", "NON")
    df["L53_margin_fits_35pct"] = np.where(df.margin_pct_account <= 35.0, "OUI", "NON")
    return df


# ------------------------------------------------------------------ statistique
def hac_t(x: np.ndarray, lags: int = 6) -> float:
    """t de Newey-West (lag-6) sur la moyenne. Retourne nan si dégénéré."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    d = x - x.mean()
    g0 = (d @ d) / n
    s = g0
    for l in range(1, min(lags, n - 1) + 1):
        gl = (d[l:] @ d[:-l]) / n
        s += 2.0 * (1.0 - l / (lags + 1.0)) * gl
    if s <= 0:
        return np.nan
    return x.mean() / np.sqrt(s / n)


def block_bootstrap_mean(x: np.ndarray, n_boot: int = 5000, mean_block: int = 10,
                         seed: int = 20260813) -> np.ndarray:
    """Bootstrap stationnaire Politis-Romano sur la moyenne. iid INTERDIT."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.array([])
    p = 1.0 / mean_block
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=np.int64)
        i = rng.integers(0, n)
        for k in range(n):
            idx[k] = i
            if rng.random() < p:
                i = rng.integers(0, n)
            else:
                i = (i + 1) % n
        out[b] = x[idx].mean()
    return out
