"""Double 7 (Connors & Alvarez, 2008) — moteur de backtest.

Règles (long only, base):
  1. Close > SMA(ma_len)            — filtre de tendance (200 j par défaut)
  2. Close = plus bas close sur     — entrée au close du jour de signal
     `entry_lb` jours (7 par défaut)
  3. Close = plus haut close sur    — sortie au close du jour de signal
     `exit_lb` jours (7 par défaut)
  Pas de stop, pas de target dans la version de base.

Conventions d'exécution (documentées dans le rapport):
  - Signaux calculés sur le close du jour t, exécution au close du jour t
    (ordre passé ~15h58, hypothèse identique à la vidéo).
  - Slippage en bps appliqué par côté (achat: px*(1+s), vente: px*(1-s)).
  - Aucun look-ahead: les fenêtres rolling incluent le jour courant
    uniquement pour des données connues au close de ce jour.
  - Parts fractionnaires autorisées (négligeable au niveau des métriques).

Deux modes de sizing:
  - "sleeves":  capital / n_symbols par instrument, sleeve all-in à chaque
    signal, capitalisation indépendante (méthode 1 de la vidéo).
  - "vol":      risque fixe par trade (risk_frac de l'équité, ou montant fixe),
    stop à stop_mult * vol_unit sous l'entrée, taille = risque / distance stop.
    vol_unit = ATR(20) si OHLC dispo, sinon σ20 des variations de prix en $.
    Stop évalué sur le close (données close-only) — documenté.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# --------------------------------------------------------------------------- #
# Indicateurs / signaux
# --------------------------------------------------------------------------- #

def compute_signals(
    close: pd.Series,
    entry_lb: int = 7,
    exit_lb: int = 7,
    ma_len: int = 200,
) -> pd.DataFrame:
    """Signaux Double 7 sur une série de closes. Sans look-ahead."""
    sma = close.rolling(ma_len, min_periods=ma_len).mean()
    is_entry = (close <= close.rolling(entry_lb).min()) & (close > sma)
    is_exit = close >= close.rolling(exit_lb).max()
    return pd.DataFrame(
        {"close": close, "sma": sma, "entry_sig": is_entry, "exit_sig": is_exit}
    )


def vol_unit_from_close(close: pd.Series, window: int = 20) -> pd.Series:
    """Proxy d'ATR sur données close-only: σ rolling des variations en $."""
    return close.diff().rolling(window, min_periods=window).std()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    """ATR classique (moyenne simple du True Range) — pour données OHLC."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


# --------------------------------------------------------------------------- #
# Structures
# --------------------------------------------------------------------------- #

@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    exit_date: Optional[pd.Timestamp]
    entry_px: float          # prix payé (slippage inclus)
    exit_px: Optional[float] # prix reçu (slippage inclus)
    shares: float
    pnl: Optional[float]
    ret: Optional[float]
    holding_days: Optional[int]  # en jours de BOURSE (barres détenues)
    exit_reason: str = ""


@dataclass
class BacktestResult:
    equity: pd.Series                    # équité portefeuille, mark-to-market au close
    trades: list[Trade] = field(default_factory=list)
    sleeve_equity: Optional[pd.DataFrame] = None
    exposure: Optional[pd.Series] = None # fraction de l'équité investie (notionnel/équité)

    @property
    def trades_df(self) -> pd.DataFrame:
        return pd.DataFrame([t.__dict__ for t in self.trades])


# --------------------------------------------------------------------------- #
# Backtest — equal sleeves
# --------------------------------------------------------------------------- #

def backtest_sleeves(
    closes: pd.DataFrame,
    capital: float = 100_000.0,
    entry_lb: int = 7,
    exit_lb: int = 7,
    ma_len: int = 200,
    slippage_bps: float = 5.0,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> BacktestResult:
    """Un sleeve par colonne de `closes`, all-in au signal, compounding isolé.

    Le warm-up (ma_len barres) est consommé avant `start`: les indicateurs
    sont calculés sur l'historique complet, le trading ne démarre qu'à `start`.
    """
    s = slippage_bps * 1e-4
    symbols = list(closes.columns)
    sleeve0 = capital / len(symbols)

    sig = {sym: compute_signals(closes[sym].dropna(), entry_lb, exit_lb, ma_len) for sym in symbols}

    idx = closes.loc[start:end].index
    sleeves = pd.DataFrame(index=idx, columns=symbols, dtype=float)
    invested = pd.DataFrame(0.0, index=idx, columns=symbols)
    trades: list[Trade] = []

    for sym in symbols:
        d = sig[sym].reindex(idx).dropna(subset=["close"])
        cash, shares = sleeve0, 0.0
        entry_date, entry_px, entry_bar = None, None, None
        for bar, (t, row) in enumerate(d.iterrows()):
            px = row["close"]
            if shares > 0 and row["exit_sig"]:
                fill = px * (1 - s)
                cash = shares * fill
                trades.append(Trade(sym, entry_date, t, entry_px, fill, shares,
                                    shares * (fill - entry_px), fill / entry_px - 1,
                                    bar - entry_bar, "7d_high"))
                shares = 0.0
            elif shares == 0 and row["entry_sig"] and not np.isnan(row["sma"]):
                fill = px * (1 + s)
                shares = cash / fill
                entry_date, entry_px, entry_bar, cash = t, fill, bar, 0.0
            sleeves.loc[t, sym] = cash + shares * px
            invested.loc[t, sym] = shares * px
        # position encore ouverte en fin de période: marquée au dernier close
        if shares > 0:
            trades.append(Trade(sym, entry_date, None, entry_px, None, shares,
                                None, None, None, "open_at_end"))

    sleeves = sleeves.ffill().fillna(sleeve0)
    equity = sleeves.sum(axis=1)
    exposure = invested.sum(axis=1) / equity
    return BacktestResult(equity=equity, trades=trades, sleeve_equity=sleeves, exposure=exposure)


# --------------------------------------------------------------------------- #
# Backtest — vol-sized (risque fixe par trade, stop k * vol_unit)
# --------------------------------------------------------------------------- #

def backtest_vol_sized(
    closes: pd.DataFrame,
    vol_units: pd.DataFrame,
    capital: float = 100_000.0,
    risk_per_trade: float = 2_000.0,
    risk_is_fraction: bool = False,
    stop_mult: float = 3.0,
    entry_lb: int = 7,
    exit_lb: int = 7,
    ma_len: int = 200,
    slippage_bps: float = 5.0,
    max_gross: float = 1.0,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> BacktestResult:
    """Compte unique. Taille = risque / (stop_mult * vol_unit), notionnel
    plafonné par le cash restant (gross <= max_gross * équité, pas de levier
    par défaut). Stop évalué sur le close. Sortie prioritaire: 7d high.
    """
    s = slippage_bps * 1e-4
    symbols = list(closes.columns)
    sig = {sym: compute_signals(closes[sym].dropna(), entry_lb, exit_lb, ma_len) for sym in symbols}

    idx = closes.loc[start:end].index
    cash = capital
    pos: dict[str, dict] = {}
    eq_hist, expo_hist, trades = [], [], []

    for bar, t in enumerate(idx):
        # 1) sorties puis 2) entrées, au close de t
        for sym in symbols:
            if sym not in pos:
                continue
            row = sig[sym].loc[t] if t in sig[sym].index else None
            if row is None or np.isnan(row["close"]):
                continue
            p = pos[sym]
            exit_reason = None
            if row["exit_sig"]:
                exit_reason = "7d_high"
            elif row["close"] <= p["stop_px"]:
                exit_reason = "stop"
            if exit_reason:
                fill = row["close"] * (1 - s)
                cash += p["shares"] * fill
                trades.append(Trade(sym, p["entry_date"], t, p["entry_px"], fill,
                                    p["shares"], p["shares"] * (fill - p["entry_px"]),
                                    fill / p["entry_px"] - 1,
                                    bar - p["entry_bar"], exit_reason))
                del pos[sym]

        # équité courante (mark-to-market) pour le sizing fractionnel
        mtm = cash + sum(
            p["shares"] * sig[sym].loc[t, "close"]
            for sym, p in pos.items()
            if t in sig[sym].index and not np.isnan(sig[sym].loc[t, "close"])
        )

        for sym in symbols:
            if sym in pos or t not in sig[sym].index:
                continue
            row = sig[sym].loc[t]
            vu = vol_units[sym].loc[t] if t in vol_units.index else np.nan
            if (not row["entry_sig"]) or np.isnan(row["sma"]) or np.isnan(vu) or vu <= 0:
                continue
            fill = row["close"] * (1 + s)
            risk = mtm * risk_per_trade if risk_is_fraction else risk_per_trade
            stop_dist = stop_mult * vu
            shares = risk / stop_dist
            notional = min(shares * fill, cash, max(max_gross * mtm - (mtm - cash), 0.0))
            if notional <= 0:
                continue
            shares = notional / fill
            cash -= notional
            pos[sym] = {"entry_date": t, "entry_px": fill, "shares": shares,
                        "stop_px": row["close"] - stop_dist, "entry_bar": bar}

        mtm = cash + sum(
            p["shares"] * sig[sym].loc[t, "close"]
            for sym, p in pos.items()
            if t in sig[sym].index and not np.isnan(sig[sym].loc[t, "close"])
        )
        eq_hist.append(mtm)
        expo_hist.append((mtm - cash) / mtm if mtm > 0 else 0.0)

    for sym, p in pos.items():
        trades.append(Trade(sym, p["entry_date"], None, p["entry_px"], None,
                            p["shares"], None, None, None, "open_at_end"))

    equity = pd.Series(eq_hist, index=idx)
    exposure = pd.Series(expo_hist, index=idx)
    return BacktestResult(equity=equity, trades=trades, exposure=exposure)
