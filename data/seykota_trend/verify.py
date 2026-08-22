"""
Independent verification of the backtest engine.

Checks:
  V1  Accounting identity: final equity == initial + sum(trade net PnL).
  V2  No look-ahead: simulation truncated at T reproduces the full-sample
      equity path on the common dates (signals never use future data).
  V3  Fill integrity: every exit price lies inside the exit bar's range
      (or equals the open on gap-throughs); entries fill at the bar open.
  V4  Signal validity: for a sample of entries, the signal bar (fill bar - 1)
      satisfied the published rule (close vs EMA100 and 20-day extreme).
  V5  Independent metric recompute (numpy-only) vs metrics.py.
  V6  Video sanity anchor: a BTC long episode exists around Oct-Nov 2020
      with pyramiding, mirroring the example trade shown in the video.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine import Params, load_universe, prepare_asset, simulate
from metrics import equity_metrics

UNIVERSE = ["US500", "US100", "XAUUSD", "USOIL", "BTC", "ETH"]
data = load_universe(UNIVERSE)
P = Params()
ok = lambda name, cond, detail="": print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")

# ----------------------------------------------------------------- V1
res = simulate(data, P, 100_000, start="2020-06-01", end="2026-06-05")
ec, tr = res["equity"], res["trades"]
ok("V1 accounting identity",
   abs(ec['equity'].iloc[-1] - (100_000 + tr.pnl_net.sum())) < 1e-6,
   f"(final={ec['equity'].iloc[-1]:,.2f} vs 100k+PnL={100_000 + tr.pnl_net.sum():,.2f})")

# ----------------------------------------------------------------- V2
cut = "2023-06-30"
res_trunc = simulate(data, P, 100_000, start="2020-06-01", end=cut)
e_full = ec["equity"][ec.index <= cut]
e_trunc = res_trunc["equity"]["equity"]
common = e_full.index.intersection(e_trunc.index)[:-1]   # exclude liquidation day
diff = (e_full.loc[common] - e_trunc.loc[common]).abs().max()
ok("V2 no look-ahead (truncation invariance)", diff < 1e-6, f"(max diff = {diff:.2e})")

# ----------------------------------------------------------------- V3
bars = {s: data[s] for s in UNIVERSE}
viol_exit, viol_entry = 0, 0
for _, t in tr.iterrows():
    b = bars[t.symbol]
    if t.exit_date in b.index and t.exit_reason == "trail_stop":
        lo, hi, op = b.loc[t.exit_date, ["low", "high", "open"]]
        if not (lo - 1e-9 <= t.exit_px <= hi + 1e-9 or abs(t.exit_px - op) < 1e-9):
            viol_exit += 1
    if t.entry_date in b.index:
        if abs(t.entry_px - b.loc[t.entry_date, "open"]) > 1e-9:
            viol_entry += 1
ok("V3 exit fills inside bar range", viol_exit == 0, f"({viol_exit} violations)")
ok("V3 entries fill at bar open", viol_entry == 0, f"({viol_entry} violations)")

# ----------------------------------------------------------------- V4
prep = {s: prepare_asset(data[s], P) for s in UNIVERSE}
sample = tr.groupby("symbol").head(8)
bad = 0
for _, t in sample.iterrows():
    d = prep[t.symbol]
    i = d.index.get_loc(t.entry_date)
    sig = d.iloc[i - 1]
    is_first_unit = abs(
        t.entry_date - tr[(tr.symbol == t.symbol) & (tr.exit_date == t.exit_date)]
        .entry_date.min()) == pd.Timedelta(0)
    if is_first_unit:
        valid = (
            (t.direction > 0 and sig.close > sig.ema and sig.close > sig.hh)
            or (t.direction < 0 and sig.close < sig.ema and sig.close < sig.ll)
        )
        bad += not valid
ok("V4 entry signals satisfy published rule", bad == 0, f"({bad} bad signals in sample)")

# ----------------------------------------------------------------- V5
eq = ec["equity"].values
years = (ec.index[-1] - ec.index[0]).days / 365.25
cagr_np = (eq[-1] / eq[0]) ** (1 / years) - 1
r = np.diff(eq) / eq[:-1]
n_yr = len(eq) / years
sharpe_np = r.mean() / r.std(ddof=1) * np.sqrt(n_yr)
mdd_np = (eq / np.maximum.accumulate(eq) - 1).min()
em = equity_metrics(ec)
ok("V5 CAGR recompute", abs(cagr_np - em["cagr"]) < 1e-9, f"({cagr_np:.4%})")
ok("V5 Sharpe recompute", abs(sharpe_np - em["sharpe"]) < 1e-6, f"({sharpe_np:.3f})")
ok("V5 MaxDD recompute", abs(mdd_np - em["max_drawdown"]) < 1e-12, f"({mdd_np:.2%})")

# ----------------------------------------------------------------- V6
btc = tr[(tr.symbol == "BTC") & (tr.entry_date >= "2020-09-01")
         & (tr.entry_date <= "2020-12-15") & (tr.direction > 0)]
ok("V6 BTC Oct-Nov 2020 long episode with pyramiding",
   len(btc) >= 2, f"({len(btc)} unit fills)")
if len(btc):
    print(btc[["entry_date", "entry_px", "exit_date", "exit_px",
               "pnl_net", "r_multiple", "exit_reason"]].to_string(index=False))

# losses bounded (gap risk aside)
worst = tr.r_multiple.min()
ok("V7 losses bounded near -1R (gap slippage aside)", worst > -2.5, f"(worst={worst:.2f}R)")
