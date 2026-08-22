"""Sleeve engines (daily, CE(S)T bars). All signals causal (.shift(1) before P&L).

S-TREND: blended TSMOM sign({60,120,250}) with |s|<0.34 -> 0 (frozen spec from
  STRATEGY_DOSSIER_TSMOM, NOT re-mined), per-instrument vol target, class buckets.
  Variant 'carry_adj': momentum measured on swap-inclusive total return.
S-ONIGHT: long equity-index overnight, Mon & Tue nights only (open-day Tue/Wed),
  verified spec from OVERNIGHT_VERIFICATION_REPORT (not re-mined).

Costs applied inside engines: spread+commission on |Δposition|, swap nightly on
held notional with 3x multiplier day. All in bps -> daily return decrements.
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def tsmom_signal(px: pd.Series, lookbacks=(60, 120, 250), theta=0.34,
                 carry_daily_bps: pd.Series | None = None) -> pd.Series:
    """Blended sign signal in {-1,-2/3,...,1}, 0 inside theta dead-zone.
    If carry_daily_bps given (signed for LONG holder, bps/night), trend is
    measured on total return (price + carry) — 'carry-adjusted momentum'."""
    if carry_daily_bps is not None:
        tr = np.log(px).diff() + carry_daily_bps.reindex(px.index).fillna(0) / 1e4
        cum = tr.cumsum()
        base = np.exp(cum)
    else:
        base = px
    sigs = []
    for L in lookbacks:
        sigs.append(np.sign(base / base.shift(L) - 1.0))
    s = pd.concat(sigs, axis=1).mean(axis=1)
    s = s.where(s.abs() >= theta, 0.0)
    return s


def realized_vol(ret: pd.Series, window=60) -> pd.Series:
    # min_periods: holey calendars (commodities sessions, holidays) must not
    # silently zero positions for 60 days after every gap (bug caught 2026-06-10)
    return ret.rolling(window, min_periods=max(20, window // 3)).std() * np.sqrt(TRADING_DAYS)


def trend_book(rets: pd.DataFrame, prices: pd.DataFrame,
               swap_long: pd.DataFrame, swap_short: pd.DataFrame,
               swap_mult: pd.DataFrame, rt_cost_bps: pd.Series,
               buckets: dict, bucket_risk: dict,
               inst_vol_target=0.10, inst_cap=5.0, port_vol_target=0.10,
               vol_derisk=True, eq_gate=True, carry_adj=False,
               theta=0.34, lookbacks=(60, 120, 250)) -> dict:
    """Vectorized multi-asset trend book.
    rets: daily close-to-close simple returns (CET days), NaN ok.
    swap_long/short: bps/night (signed: negative = cost). swap_mult: 1 or 3.
    rt_cost_bps: per-symbol round-trip spread+commission bps.
    buckets: {bucket_name: [symbols]}; bucket_risk: {bucket_name: weight}, sum=1.
    Returns dict(returns=net daily series, gross=..., pos=DataFrame, diag=...).
    """
    syms = [s for b in buckets.values() for s in b]
    rets = rets[syms]
    pos = pd.DataFrame(0.0, index=rets.index, columns=syms)
    for sym in syms:
        carry = None
        if carry_adj:
            carry = swap_long[sym]  # long-holder carry for trend measurement
        sig = tsmom_signal(prices[sym].dropna(), lookbacks, theta,
                           carry).reindex(rets.index)
        rv = realized_vol(rets[sym]).clip(lower=1e-4)
        w = (inst_vol_target / rv).clip(upper=inst_cap)
        pos[sym] = (sig * w)
    # bucket risk normalisation: scale each bucket to its risk share / n_inst
    for b, bsyms in buckets.items():
        bsyms = [s for s in bsyms if s in pos]
        pos[bsyms] = pos[bsyms] * (bucket_risk[b] / max(len(bsyms), 1))
    pos = pos.shift(1)                                  # decide t-1 close, hold t
    # portfolio vol targeting on trailing realized book vol
    raw = (pos * rets).sum(axis=1)
    bvol = raw.rolling(60).std().shift(1) * np.sqrt(TRADING_DAYS)
    scale = (port_vol_target / bvol.clip(lower=1e-4)).clip(upper=10.0)
    if vol_derisk:
        v20 = raw.rolling(20).std().shift(1) * np.sqrt(TRADING_DAYS)
        scale = scale * np.minimum(1.0, port_vol_target / v20.clip(lower=1e-4))
    pos = pos.mul(scale, axis=0)
    gross_ret = (pos * rets).sum(axis=1)
    # costs
    turn = pos.diff().abs()
    tc = (turn * (rt_cost_bps / 2.0 / 1e4)).sum(axis=1)      # half-RT per side
    held_swap = pd.DataFrame(0.0, index=rets.index, columns=syms)
    for sym in syms:
        p = pos[sym]
        bps = np.where(p > 0, swap_long[sym], np.where(p < 0, swap_short[sym], 0.0))
        held_swap[sym] = p.abs() * bps / 1e4 * swap_mult[sym]
    # swap bps are SIGNED (credit positive, cost negative) -> add contribution
    net = gross_ret - tc + held_swap.sum(axis=1)
    if eq_gate:
        eq = (1 + net.fillna(0)).cumprod()
        gate = (eq > eq.rolling(100).mean()).astype(float).replace(0.0, 0.4).shift(1)
        # apply gate multiplicatively to NEXT day positions: approximate by
        # scaling returns (positions linear) — re-run cost-consistently:
        pos2 = pos.mul(gate.fillna(1.0), axis=0)
        gross2 = (pos2 * rets).sum(axis=1)
        turn2 = pos2.diff().abs()
        tc2 = (turn2 * (rt_cost_bps / 2.0 / 1e4)).sum(axis=1)
        hs2 = pd.DataFrame(0.0, index=rets.index, columns=syms)
        for sym in syms:
            p = pos2[sym]
            bps = np.where(p > 0, swap_long[sym], np.where(p < 0, swap_short[sym], 0.0))
            hs2[sym] = p.abs() * bps / 1e4 * swap_mult[sym]
        net = gross2 - tc2 + hs2.sum(axis=1)
        pos = pos2
        gross_ret = gross2
        tc = tc2
        held_swap = hs2
    return dict(net=net, gross=gross_ret, pos=pos, tc=tc,
                swap=held_swap.sum(axis=1))


def overnight_sleeve(daily: dict, syms=("US100", "GER40"),
                     swap_long_bps: dict | None = None,
                     spread_bps: dict | None = None,
                     unit_exposure=1.0) -> pd.Series:
    """Long close(Mon)->open(Tue) and close(Tue)->open(Wed) on index CFDs.
    daily[sym]: DataFrame with open/close (CET days). Returns daily series of
    sleeve return per unit exposure, swap (1x) + full spread RT charged.
    Open-day convention: return booked on the OPEN day (Tue/Wed)."""
    out = []
    for sym in syms:
        d = daily[sym]
        ov = d["open"] / d["close"].shift(1) - 1.0
        wd = pd.Series(d.index.dayofweek, index=d.index)
        take = wd.isin([1, 2])                      # Tue & Wed open-days
        r = ov.where(take, 0.0)
        cost = ((spread_bps or {}).get(sym, 2.0) + 0.0) / 1e4   # RT spread
        sw = ((swap_long_bps or {}).get(sym, -3.08)) / 1e4      # 1 night, signed
        r = r - take.astype(float) * cost + take.astype(float) * sw
        out.append(r * unit_exposure)
    s = pd.concat(out, axis=1).mean(axis=1)
    return s.fillna(0.0)


def perf_stats(net: pd.Series, freq=TRADING_DAYS) -> dict:
    r = net.dropna()
    if len(r) < 100:
        return dict(sharpe=np.nan, ann=np.nan, vol=np.nan, maxdd=np.nan,
                    skew=np.nan, worst_day=np.nan, n=len(r))
    ann = r.mean() * freq
    vol = r.std() * np.sqrt(freq)
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return dict(sharpe=ann / vol if vol > 0 else np.nan, ann=ann, vol=vol,
                maxdd=dd, skew=r.skew(), worst_day=r.min(), n=len(r),
                t=r.mean() / r.std() * np.sqrt(len(r)))
