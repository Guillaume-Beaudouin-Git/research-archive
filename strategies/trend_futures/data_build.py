"""
Build continuous, PROPORTIONAL back-adjusted daily futures bars for the
non-crypto trend sleeve (PREREG section 4-5).

Why back-adjust: yfinance `=F` is a RAW front-month splice (Adj Close == Close);
roll-day basis jumps contaminate EMA/Donchian/ATR levels and would inject fake
P&L. We remove the roll-day overnight basis gap (proportional / ratio method,
most-recent contract anchored to real prices) so % moves and ATR are continuous
across rolls. The roll cost is charged SEPARATELY in the engine (cross the spread
once per roll), which is the correct futures accounting (L5).

Method (only inputs needed: the spliced daily series + a per-instrument roll
calendar window):
  - economic log-return r_t = log(close_t / close_{t-1}) on a normal day,
    = log(close_t / open_t) on a detected roll day (drops the overnight basis
    gap, keeps the clean intraday move).
  - roll day := inside the instrument's roll-calendar window AND the overnight
    gap |log(open_t/close_{t-1})| exceeds max(0.3%, 3.5 x rolling60 std). The
    calendar gate prevents neutralizing real shocks (FOMC, etc.) outside rolls.
  - adjusted price = cumprod(r), rescaled so the LAST close == raw last close;
    factor_t = adj_close_t/raw_close_t applied to O/H/L (intraday ratios preserved).

NQ is built two ways: (a) yfinance NQ=F via the method above; (b) the local
Databento batch (exact roll dates from the per-minute `symbol` column) as the
GOLD reference. (a) is cross-validated against (b) to validate the `=F` sourcing
for the six instruments that have no gold reference.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
DAILY = HERE / "daily"
DAILY.mkdir(exist_ok=True)
DB_NQ = Path("<HOME>/Desktop/Algo_claude/data/raw/NQ_1min_databento_2010-2026.parquet")

# --------------------------------------------------------------- instrument spec
# multiplier = $ per 1.0 index/price point for the MICRO contract.
# tick = price increment; comm_side = $/side commission assumption (micro, Tradovate-ish).
# roll = roll-calendar window type; n_rolls = approx rolls/yr (for documentation).
# cluster = correlation cluster for risk budgeting (H2).
INSTRUMENTS = {
    "NQ": dict(yf="NQ=F",  micro="MNQ", mult=2.0,    tick=0.25,   comm_side=0.37, roll="index_q", n_rolls=4,  cluster="equity"),
    "ES": dict(yf="ES=F",  micro="MES", mult=5.0,    tick=0.25,   comm_side=0.37, roll="index_q", n_rolls=4,  cluster="equity"),
    "GC": dict(yf="GC=F",  micro="MGC", mult=10.0,   tick=0.10,   comm_side=0.37, roll="gold",    n_rolls=6,  cluster="metal"),
    "CL": dict(yf="CL=F",  micro="MCL", mult=100.0,  tick=0.01,   comm_side=0.37, roll="crude",   n_rolls=12, cluster="energy"),
    "6E": dict(yf="6E=F",  micro="M6E", mult=12500.0, tick=0.0001, comm_side=0.37, roll="fx_q",    n_rolls=4,  cluster="fx"),
    "6A": dict(yf="6A=F",  micro="M6A", mult=10000.0, tick=0.0001, comm_side=0.37, roll="fx_q",    n_rolls=4,  cluster="fx"),
    "6B": dict(yf="6B=F",  micro="M6B", mult=6250.0,  tick=0.0001, comm_side=0.37, roll="fx_q",    n_rolls=4,  cluster="fx"),
    # extension (Phase 4 only)
    "RTY": dict(yf="RTY=F", micro="M2K", mult=5.0,   tick=0.10,    comm_side=0.37, roll="index_q", n_rolls=4,  cluster="equity"),
    "SI":  dict(yf="SI=F",  micro="SIL", mult=1000.0, tick=0.005,  comm_side=0.37, roll="silver",  n_rolls=5,  cluster="metal"),
    "ZN":  dict(yf="ZN=F",  micro="MZN", mult=1000.0, tick=0.015625, comm_side=0.37, roll="zn_q",  n_rolls=4,  cluster="rates"),
}
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
EXT = ["RTY", "SI", "ZN"]


def in_roll_window(roll_type: str, ts: pd.Timestamp) -> bool:
    m, d = ts.month, ts.day
    if roll_type == "index_q":
        return m in (3, 6, 9, 12) and 6 <= d <= 18
    if roll_type == "fx_q":
        return m in (3, 6, 9, 12) and 9 <= d <= 19
    if roll_type == "zn_q":
        return m in (2, 5, 8, 11) and d >= 20
    if roll_type == "gold":
        return m in (1, 3, 5, 7, 9, 11) and d >= 23
    if roll_type == "silver":
        return m in (2, 4, 6, 8, 11) and d >= 23
    if roll_type == "crude":
        return 13 <= d <= 22
    raise ValueError(roll_type)


def proportional_backadjust(df: pd.DataFrame, is_roll: pd.Series) -> pd.DataFrame:
    """df: raw daily OHLC(V). is_roll: bool per row. Returns adjusted OHLC + flags."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    prevc = c.shift(1)
    logret_cc = np.log(c / prevc)
    logret_intra = np.log(c / o)
    r = logret_cc.copy()
    r[is_roll] = logret_intra[is_roll]          # drop overnight basis gap on roll days
    r.iloc[0] = 0.0
    r = r.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    adj = np.exp(r.cumsum())
    adj = adj * (c.iloc[-1] / adj.iloc[-1])     # anchor: last adj close == raw last close
    factor = (adj / c).to_numpy()
    out = pd.DataFrame(index=df.index)
    out["open"] = o.to_numpy() * factor
    out["high"] = h.to_numpy() * factor
    out["low"] = l.to_numpy() * factor
    out["close"] = adj.to_numpy()
    out["raw_close"] = c.to_numpy()
    out["volume"] = df.get("volume", pd.Series(np.nan, index=df.index)).to_numpy()
    out["is_roll"] = is_roll.to_numpy()
    # sanitize OHLC consistency (rare raw bad bars / factor-step rounding)
    hi = out[["open", "high", "low", "close"]].max(axis=1)
    lo = out[["open", "high", "low", "close"]].min(axis=1)
    out["high"], out["low"] = hi, lo
    return out


def detect_rolls_calendar(df: pd.DataFrame, roll_type: str) -> pd.Series:
    """One roll per contiguous roll-window run: the argmax |overnight gap| day in
    the window, gated by a mild sigma-relative floor (so near-zero-basis FX/bond
    rolls and dead-flat days are not spuriously neutralized)."""
    overnight = np.log(df["open"] / df["close"].shift(1))
    abso = overnight.abs()
    roll60 = abso.rolling(60, min_periods=20).std().bfill()
    floor = 1.2 * roll60
    in_win = pd.Series([in_roll_window(roll_type, t) for t in df.index], index=df.index).fillna(False)
    is_roll = pd.Series(False, index=df.index)
    run_id = (in_win != in_win.shift()).cumsum()
    for _, idx in df.index.to_series().groupby([run_id, in_win]).groups.items():
        sub = in_win.loc[idx]
        if not bool(sub.iloc[0]):
            continue
        g = abso.loc[idx]
        if g.notna().any() and g.max() >= floor.loc[g.idxmax()]:
            is_roll.loc[g.idxmax()] = True
    return is_roll


def fetch_yf(ticker: str) -> pd.DataFrame:
    import yfinance as yf
    raw = yf.download(ticker, start="2012-06-01", auto_adjust=False, progress=False)
    raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
    raw.index = pd.to_datetime(raw.index).tz_localize(None).normalize()
    raw = raw[(raw[["open", "high", "low", "close"]] > 0).all(axis=1)].dropna(subset=["open", "high", "low", "close"])
    return raw


def build_databento_nq_gold() -> pd.DataFrame:
    cols = pd.read_parquet(DB_NQ, columns=["open", "high", "low", "close", "volume", "symbol", "is_roll_day"])
    daily = pd.DataFrame({
        "open": cols["open"].resample("1D").first(),
        "high": cols["high"].resample("1D").max(),
        "low": cols["low"].resample("1D").min(),
        "close": cols["close"].resample("1D").last(),
        "volume": cols["volume"].resample("1D").sum(),
    }).dropna(subset=["close"])
    roll = cols["is_roll_day"].resample("1D").max().reindex(daily.index).fillna(False).astype(bool)
    daily.index = daily.index.tz_localize(None).normalize()
    roll.index = daily.index
    return proportional_backadjust(daily, roll)


def main():
    print("=== Building yfinance =F continuous (proportional back-adjusted) ===")
    qa = []
    for sym, spec in INSTRUMENTS.items():
        raw = fetch_yf(spec["yf"])
        is_roll = detect_rolls_calendar(raw, spec["roll"])
        adj = proportional_backadjust(raw, is_roll)
        adj.to_parquet(DAILY / f"{sym}.parquet")
        # quality
        ohlc_viol = int(((adj["high"] < adj["low"]) |
                         (adj["close"] > adj["high"] + 1e-9) | (adj["close"] < adj["low"] - 1e-9) |
                         (adj["open"] > adj["high"] + 1e-9) | (adj["open"] < adj["low"] - 1e-9)).sum())
        on_gap = np.log(adj["open"] / adj["close"].shift(1)).abs()
        max_gap_after = float(on_gap[~adj["is_roll"]].max())
        qa.append(dict(sym=sym, n=len(adj), start=str(adj.index[0].date()), end=str(adj.index[-1].date()),
                       n_roll=int(adj["is_roll"].sum()), ohlc_viol=ohlc_viol,
                       max_nonroll_gap=round(max_gap_after, 4)))
        print(f"  {sym:4s} n={len(adj):5d} {adj.index[0].date()}->{adj.index[-1].date()} "
              f"rolls={int(adj['is_roll'].sum()):3d} ohlc_viol={ohlc_viol} max_nonroll_gap={max_gap_after:.3f}")

    print("\n=== Databento NQ gold ===")
    gold = build_databento_nq_gold()
    gold.to_parquet(DAILY / "_NQ_databento_gold.parquet")
    print(f"  gold n={len(gold)} {gold.index[0].date()}->{gold.index[-1].date()} rolls={int(gold['is_roll'].sum())}")

    print("\n=== Cross-validation: NQ=F adjusted vs Databento NQ gold ===")
    nqyf = pd.read_parquet(DAILY / "NQ.parquet")
    cy = np.log(nqyf["close"]); cg = np.log(gold["close"])
    a = cy.diff().rename("yf"); b = cg.diff().rename("gold")
    j = pd.concat([a, b], axis=1).dropna()
    j = j[j.index >= "2014-01-01"]
    # daily corr is depressed by UTC-day(gold) vs exchange-day(yf) boundary; report
    # best ±1d alignment AND convention-free weekly/monthly corr + vol match.
    best_daily = max(j["yf"].corr(j["gold"].shift(k)) for k in (-1, 0, 1))
    wk = pd.concat([cy.resample("W-FRI").last().diff().rename("yf"),
                    cg.resample("W-FRI").last().diff().rename("gold")], axis=1).dropna()
    wk = wk[wk.index >= "2014-01-01"]
    mo = pd.concat([cy.resample("ME").last().diff().rename("yf"),
                    cg.resample("ME").last().diff().rename("gold")], axis=1).dropna()
    mo = mo[mo.index >= "2014-01-01"]
    corr = float(wk["yf"].corr(wk["gold"]))
    vol_yf = float(j["yf"].std() * np.sqrt(252)); vol_gold = float(j["gold"].std() * np.sqrt(252))
    print(f"  daily corr (best ±1d)={best_daily:.3f}  WEEKLY corr={corr:.3f}  MONTHLY corr={mo['yf'].corr(mo['gold']):.3f}")
    print(f"  ann.vol yf={vol_yf:.3f} gold={vol_gold:.3f}  n_daily={len(j)}  n_weekly={len(wk)}")

    specs = {s: {k: v for k, v in sp.items()} for s, sp in INSTRUMENTS.items()}
    (DAILY / "specs.json").write_text(json.dumps(specs, indent=2))
    pd.DataFrame(qa).to_csv(DAILY / "data_quality.csv", index=False)
    meta = dict(corr_nqyf_gold=corr, vol_yf=vol_yf, vol_gold=vol_gold, n_common=len(j))
    (DAILY / "validation.json").write_text(json.dumps(meta, indent=2))
    print("\nSaved daily/*.parquet, specs.json, data_quality.csv, validation.json")


if __name__ == "__main__":
    main()
