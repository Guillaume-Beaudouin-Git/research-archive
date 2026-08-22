"""Chargement des données locales (panels daily ETF + CFD)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent          # .../data
PANELS = DATA / "panels"
XAU_D1 = Path(__file__).resolve().parent / "xauusd_d1.csv"


def load_etf_closes() -> pd.DataFrame:
    """SPY, QQQ (equity_panel) + GLD (macro_etf_panel) — closes ajustés."""
    eq = pd.read_csv(PANELS / "equity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(PANELS / "macro_etf_panel.csv", index_col=0, parse_dates=True)
    df = pd.concat([eq[["SPY", "QQQ"]], mac[["GLD"]]], axis=1).dropna()
    df.index.name = "date"
    return df


def load_cfd_ohlc() -> dict[str, pd.DataFrame]:
    """US500/US100 daily OHLC (panels ftmo) + XAUUSD daily (resample M1 UTC)."""
    out = {}
    o = pd.read_csv(PANELS / "ftmo_open.csv", index_col=0, parse_dates=True)
    h = pd.read_csv(PANELS / "ftmo_high.csv", index_col=0, parse_dates=True)
    l = pd.read_csv(PANELS / "ftmo_low.csv", index_col=0, parse_dates=True)
    c = pd.read_csv(PANELS / "ftmo_close.csv", index_col=0, parse_dates=True)
    for sym in ["US500", "US100"]:
        df = pd.DataFrame({"open": o[sym], "high": h[sym], "low": l[sym], "close": c[sym]}).dropna()
        out[sym] = df
    xau = pd.read_csv(XAU_D1, index_col=0, parse_dates=True)[["open", "high", "low", "close"]]
    out["XAUUSD"] = xau
    return out


def load_extended_universe() -> pd.DataFrame:
    """Univers élargi pour l'axe diversification: indices + secteurs + macro ETF."""
    eq = pd.read_csv(PANELS / "equity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(PANELS / "macro_etf_panel.csv", index_col=0, parse_dates=True)
    cols_eq = ["SPY", "QQQ", "IWM", "EFA", "EEM", "EWJ", "XLE", "XLF", "XLK", "XLP", "XLU", "XLV"]
    df = pd.concat([eq[cols_eq], mac[["GLD", "TLT", "DBC"]]], axis=1)
    df.index.name = "date"
    return df


def load_vix() -> pd.Series:
    vix = pd.read_csv(PANELS / "vix.csv", index_col=0, parse_dates=True)
    return vix.iloc[:, 0]
