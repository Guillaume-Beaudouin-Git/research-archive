"""Signal + P&L engine — PREREGISTRATION sections 3, 4, 5.

Execution discipline (hard rule, enforced structurally): the score on a rebalance
date T is built **only** from closes up to T-1, and the new book is executed at the
**open of T**. Day T's P&L therefore splits into the old book carrying the
overnight gap (close T-1 -> open T) and the new book carrying the session
(open T -> close T). Nothing in the pipeline can read a price it would not have had.

Interpretations of under-specified points in the frozen spec, declared here and not
revisited after seeing results:

* *"rebalance 2x/semaine"* — Monday and Thursday (evenly spaced; no other pair was
  evaluated).
* *"Top 4 ... long-only sur le score positif"* — the composite score is a mean of
  normalised ranks and is non-negative by construction, so "positive score" is read
  on the only signed component of the spec: an instrument in the top 4 is held long
  only if its ``trend`` component (sign of the 60-day return) is +1.
* *"vol realisee 20j"* of the regime overlay — the **book's own** trailing 20-day
  realised volatility, measured on returns up to T-1.
* sizing unit — ``vm`` multiplies a base book scaled so that each held leg carries
  a risk budget of ``TARGET_VOL / n_legs``; ``vm = 1`` is a 10%-annual-vol risk
  budget before the overlay. Realised volatility per ``vm`` is reported so the unit
  is interpretable rather than nominal.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import costs as C
from . import panel as P

TARGET_VOL = 0.10
ANN = 252.0
TREND_LB, MOM_LB, VOL_LB, PROXY_LB, OVERLAY_LB = 60, 120, 60, 20, 20
N_TOP = 4


@dataclass
class Config:
    name: str = "V0"
    rebalance: str = "2w"        # "2w" (Mon+Thu) | "monthly"
    vol_overlay: bool = True
    intraday_flat: bool = False
    vm: float = 1.0
    swap_mult: float = 1.0
    spread_field: str = "spread_med"
    spread_uplift: bool = False  # rescale panel spread to the live FTMO RT anchors
    side: str = "long"           # "long" | "short" | "both"  (L25 two-sided control)
    zero_cost: bool = False      # L25 control runs at zero cost


def rebalance_mask(dates: pd.DatetimeIndex, mode: str) -> np.ndarray:
    if mode == "2w":
        return np.isin(dates.dayofweek, (0, 3))
    if mode == "monthly":
        m = pd.Series(dates.month.values, index=dates)
        return (m != m.shift(1)).fillna(True).to_numpy()
    raise ValueError(mode)


def build_signals(close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Score components on closes. All are backward-looking by construction."""
    ret = close.pct_change()
    vol = ret.rolling(VOL_LB).std() * np.sqrt(ANN)
    trend = np.sign(close / close.shift(TREND_LB) - 1.0)
    mom = (close / close.shift(MOM_LB) - 1.0) / vol
    proxy = (close / close.shift(PROXY_LB) - 1.0).abs() / vol
    return {"trend": trend, "mom": mom, "proxy": proxy, "vol": vol, "ret": ret}


def _norm_rank(df: pd.DataFrame) -> pd.DataFrame:
    r = df.rank(axis=1, method="average")
    n = df.notna().sum(axis=1)
    return (r.sub(1.0, axis=0)).div((n - 1.0).replace(0, np.nan), axis=0)


def target_weights(sig: dict[str, pd.DataFrame], cfg: Config,
                   book_vol: pd.Series) -> pd.DataFrame:
    score = (_norm_rank(sig["trend"]) + _norm_rank(sig["mom"])
             + _norm_rank(sig["proxy"])) / 3.0
    w = pd.DataFrame(0.0, index=score.index, columns=score.columns)

    if cfg.side in ("long", "both"):
        ranked = score.rank(axis=1, ascending=False, method="first")
        sel = (ranked <= N_TOP) & sig["trend"].gt(0) & sig["vol"].gt(0)
        inv = sel.astype(float).div(sig["vol"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        n_sel = sel.sum(axis=1).replace(0, np.nan)
        w = w + inv.mul(TARGET_VOL / n_sel, axis=0).fillna(0.0)

    if cfg.side in ("short", "both"):
        srank = score.rank(axis=1, ascending=True, method="first")
        ssel = (srank <= N_TOP) & sig["trend"].lt(0) & sig["vol"].gt(0)
        sinv = ssel.astype(float).div(sig["vol"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        ns = ssel.sum(axis=1).replace(0, np.nan)
        w = w - sinv.mul(TARGET_VOL / ns, axis=0).fillna(0.0)

    if cfg.vol_overlay:
        ov = (TARGET_VOL / book_vol.replace(0, np.nan)).clip(0.5, 1.5).fillna(1.0)
        w = w.mul(ov, axis=0)
    return w * cfg.vm


def run(panel: pd.DataFrame, cfg: Config) -> dict:
    """Simulate one variant. Returns daily net/gross series and cost attribution."""
    close = P.closes(panel)
    open_ = P.opens(panel)
    dates = close.index
    syms = list(close.columns)

    sig = build_signals(close)
    ret_cc = close.pct_change().fillna(0.0)
    ret_on = (open_ / close.shift(1) - 1.0).fillna(0.0)      # close T-1 -> open T
    ret_id = (close / open_ - 1.0).fillna(0.0)               # open T -> close T

    sp = (C.spread_bps(panel, cfg.spread_field, uplift=cfg.spread_uplift)
          .reindex(columns=syms).ffill().fillna(0.0))
    comm = C.commission_rt_bps(syms)
    swap_l = C.swap_bps_frame(syms, dates, "long") * cfg.swap_mult
    swap_s = C.swap_bps_frame(syms, dates, "short") * cfg.swap_mult
    if cfg.zero_cost:
        sp = sp * 0.0
        comm = comm * 0.0
        swap_l = swap_l * 0.0
        swap_s = swap_s * 0.0

    rb = rebalance_mask(dates, cfg.rebalance)
    n = len(dates)
    w_prev = np.zeros(len(syms))
    book_vol_hist: list[float] = []
    net = np.zeros(n)
    gross = np.zeros(n)
    c_spread = np.zeros(n)
    c_swap = np.zeros(n)
    turn = np.zeros(n)
    w_hist = np.zeros((n, len(syms)))

    scoreable = sig["vol"].notna().all(axis=1) & sig["mom"].notna().all(axis=1)
    bv = pd.Series(np.nan, index=dates)

    for i in range(n):
        # book volatility measured on returns strictly before day i
        if i >= OVERLAY_LB:
            hist = np.asarray(book_vol_hist[-OVERLAY_LB:])
            bv.iloc[i] = hist.std(ddof=1) * np.sqrt(ANN) if hist.size >= 5 else np.nan

        if rb[i] and i > 0 and scoreable.iloc[i - 1]:
            # score from T-1 data only
            one = {k: v.iloc[[i - 1]] for k, v in sig.items()}
            bvv = pd.Series([bv.iloc[i]], index=[dates[i - 1]])
            w_new = target_weights(one, cfg, bvv).iloc[0].reindex(syms).fillna(0.0).to_numpy()
        else:
            w_new = w_prev.copy()

        rebalanced = not np.array_equal(w_new, w_prev)

        if cfg.intraday_flat:
            g = float((w_new * ret_id.iloc[i].to_numpy()).sum())
            cost_sp = float((np.abs(w_new) * (sp.iloc[i].to_numpy()
                                              + comm.to_numpy())).sum()) / 1e4
            cost_sw = 0.0
            turn[i] = float(np.abs(w_new).sum())
        else:
            if rebalanced:
                g = float((w_prev * ret_on.iloc[i].to_numpy()).sum()
                          + (w_new * ret_id.iloc[i].to_numpy()).sum())
                dw = np.abs(w_new - w_prev)
                cost_sp = float((dw * (sp.iloc[i].to_numpy() / 2.0
                                       + comm.to_numpy() / 2.0)).sum()) / 1e4
                turn[i] = float(dw.sum())
            else:
                g = float((w_new * ret_cc.iloc[i].to_numpy()).sum())
                cost_sp = 0.0
            sw = np.where(w_new >= 0, swap_l.iloc[i].to_numpy(), swap_s.iloc[i].to_numpy())
            cost_sw = -float((np.abs(w_new) * sw).sum()) / 1e4   # sw<0 => cost>0

        gross[i] = g
        c_spread[i] = cost_sp
        c_swap[i] = cost_sw
        net[i] = g - cost_sp - cost_sw
        book_vol_hist.append(net[i])
        w_hist[i] = w_new
        w_prev = w_new

    idx = dates
    out = pd.DataFrame({"gross": gross, "net": net, "cost_spread": c_spread,
                        "cost_swap": c_swap, "turnover": turn}, index=idx)
    out = out.loc[P.START:]
    return {
        "daily": out,
        "weights": pd.DataFrame(w_hist, index=idx, columns=syms).loc[P.START:],
        "cfg": cfg,
    }
