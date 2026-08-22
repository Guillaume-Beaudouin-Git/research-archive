"""
Robustness suite. All runs use the cash-account variant (max_gross=1.0),
which is the realistic deployment, unless stated otherwise.

Outputs (results/):
  sens_ema_breakout.csv   Sharpe/CAGR/MDD grid, EMA x breakout window
  sens_stop_pyramid.csv   grid, ATR stop multiple x pyramid step
  variants.csv            rule-component ablations on both windows
  cost_stress.csv         cost multiplier stress
  is_oos.csv              2014-2020 vs 2020-2026 split
  bootstrap_ci.csv        block-bootstrap CIs (Sharpe, CAGR, MaxDD)
  benchmarks.csv          buy & hold comparators per window
  annual_returns.csv      strategy annual returns per variant
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from engine import COSTS, Params, load_universe, simulate
from metrics import block_bootstrap, equity_metrics, trade_metrics

OUT = Path(__file__).resolve().parent / "results"
UNIVERSE = ["US500", "US100", "XAUUSD", "USOIL", "BTC", "ETH"]
DATA = load_universe(UNIVERSE)

EXT = dict(start="2014-09-17", end="2026-06-05")
REP = dict(start="2020-06-01", end="2026-06-05")
BASE = Params(max_gross=1.0)


def stats(p: Params, window: dict, costs=None) -> dict:
    r = simulate(DATA, p, 100_000, costs=costs, **window)
    em, tm = equity_metrics(r["equity"]), trade_metrics(r["trades"])
    return {
        "cagr": em["cagr"], "sharpe": em["sharpe"], "max_dd": em["max_drawdown"],
        "calmar": em["calmar"], "ann_vol": em["ann_vol"],
        "win_rate": tm.get("win_rate"), "profit_factor": tm.get("profit_factor"),
        "n_trades": tm.get("n_trades"), "expectancy_R": tm.get("expectancy_R"),
    }, r


# ------------------------------------------------ 1. EMA x breakout grid
rows = []
for ema, bo in itertools.product([50, 100, 150, 200], [10, 20, 40, 55]):
    s, _ = stats(replace(BASE, ema_len=ema, breakout=bo), EXT)
    rows.append({"ema": ema, "breakout": bo, **s})
pd.DataFrame(rows).to_csv(OUT / "sens_ema_breakout.csv", index=False)
print("grid 1 done")

# ------------------------------------------------ 2. stop x pyramid grid
rows = []
for k, step in itertools.product([2.0, 2.5, 3.0, 4.0], [0.25, 0.5, 1.0]):
    s, _ = stats(replace(BASE, atr_stop_mult=k, pyramid_step_atr=step), EXT)
    rows.append({"atr_stop_mult": k, "pyramid_step": step, **s})
pd.DataFrame(rows).to_csv(OUT / "sens_stop_pyramid.csv", index=False)
print("grid 2 done")

# ------------------------------------------------ 3. rule ablations
VARIANTS = {
    "base_capped": BASE,
    "literal_leveraged": Params(),
    "long_only": replace(BASE, long_only=True),
    "no_pyramid": replace(BASE, max_adds=0),
    "no_trend_filter": replace(BASE, trend_filter=False),
    "wide_stop_4atr": replace(BASE, atr_stop_mult=4.0),
}
rows = []
for name, p in VARIANTS.items():
    for wname, w in [("2014-2026", EXT), ("2020-2026", REP)]:
        s, _ = stats(p, w)
        rows.append({"variant": name, "window": wname, **s})
pd.DataFrame(rows).to_csv(OUT / "variants.csv", index=False)
print("variants done")

# ------------------------------------------------ 4. cost stress
rows = []
for mult in [0.0, 1.0, 2.0, 3.0]:
    s, _ = stats(BASE, EXT, costs={k: v * mult for k, v in COSTS.items()})
    rows.append({"cost_mult": mult, **s})
pd.DataFrame(rows).to_csv(OUT / "cost_stress.csv", index=False)
print("cost stress done")

# ------------------------------------------------ 5. IS / OOS split
rows = []
for name, w in [
    ("IS_2014-2020", dict(start="2014-09-17", end="2020-05-31")),
    ("OOS_2020-2026", REP),
]:
    s, _ = stats(BASE, w)
    rows.append({"window": name, **s})
pd.DataFrame(rows).to_csv(OUT / "is_oos.csv", index=False)
print("IS/OOS done")

# ------------------------------------------------ 6. bootstrap CIs
ci_rows = []
for tag, w in [("extended_capped", EXT), ("replication_capped", REP)]:
    _, r = stats(BASE, w)
    rets = r["equity"]["equity"].pct_change().dropna()
    ci = block_bootstrap(rets, n_boot=2000, block=21)
    ci["run"] = tag
    ci_rows.append(ci.reset_index(names="quantile"))
pd.concat(ci_rows).to_csv(OUT / "bootstrap_ci.csv", index=False)
print("bootstrap done")

# ------------------------------------------------ 7. benchmarks
def bh_metrics(close: pd.Series, w: dict, label: str) -> dict:
    c = close[(close.index >= w["start"]) & (close.index <= w["end"])].dropna()
    eq = c / c.iloc[0] * 100_000
    ec = pd.DataFrame({"equity": eq, "gross_exposure": 1.0})
    em = equity_metrics(ec)
    return {"benchmark": label, "window": f"{w['start']}->{w['end']}",
            "cagr": em["cagr"], "sharpe": em["sharpe"], "max_dd": em["max_drawdown"],
            "ann_vol": em["ann_vol"]}

rows = []
for w in [REP, EXT]:
    rows.append(bh_metrics(DATA["US500"]["close"], w, "US500 buy&hold (price index)"))
    rows.append(bh_metrics(DATA["BTC"]["close"], w, "BTC buy&hold"))
    # equal-weight 6-asset basket, monthly rebalanced, no costs
    closes = pd.DataFrame({s: DATA[s]["close"] for s in UNIVERSE}).ffill()
    closes = closes[(closes.index >= w["start"]) & (closes.index <= w["end"])]
    r_d = closes.pct_change()
    avail = closes.notna()
    wts = (avail.div(avail.sum(axis=1), axis=0)).shift(1)
    ew = (r_d * wts).sum(axis=1, min_count=1).fillna(0)
    eq = (1 + ew).cumprod() * 100_000
    ec = pd.DataFrame({"equity": eq, "gross_exposure": 1.0})
    em = equity_metrics(ec)
    rows.append({"benchmark": "EW-6 basket (daily rebal, no cost)",
                 "window": f"{w['start']}->{w['end']}", "cagr": em["cagr"],
                 "sharpe": em["sharpe"], "max_dd": em["max_drawdown"],
                 "ann_vol": em["ann_vol"]})
pd.DataFrame(rows).to_csv(OUT / "benchmarks.csv", index=False)
print("benchmarks done")

# ------------------------------------------------ 8. annual returns
rows = {}
for tag, p, w in [
    ("capped", BASE, EXT),
    ("literal", Params(), EXT),
]:
    _, r = stats(p, w)
    a = r["equity"]["equity"].resample("YE").last()
    a0 = r["equity"]["equity"].iloc[0]
    ann = a.pct_change()
    ann.iloc[0] = a.iloc[0] / a0 - 1
    rows[tag] = ann.round(4)
pd.DataFrame(rows).to_csv(OUT / "annual_returns.csv")
print("annual returns done")
print("\nALL ROBUSTNESS RUNS COMPLETE")
