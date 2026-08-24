"""
Independent verification of the futures trend engine (port of seykota_trend/verify.py).
  V1  Accounting identity: final equity == initial + Σ trade.pnl_net − total_roll_cost.
  V2  No look-ahead: truncated-at-T simulation reproduces the full-sample path.
  V3  Fill integrity: exits inside the bar range (or at the open on gaps); entries at open.
  V4  Signal validity: sampled first-unit entries satisfy the published rule.
  V5  Independent numpy metric recompute vs metrics.py.
  V6  Trend sanity: at least one large captured trend (R>3) WITH pyramiding exists.
  V7  Losses: typical losing-stop R ≈ -1R; report worst (gap aside).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from engine import Params, load_universe, prepare_asset, simulate, build_costs, load_specs
from metrics import equity_metrics

UNIVERSE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
specs = load_specs()
per_side, roll_bp, mult = build_costs(specs)
data = load_universe(UNIVERSE)
P = Params()
ok = lambda name, cond, detail="": print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")

res = simulate(data, P, 100_000, per_side, roll_bp, mult, start="2014-01-01", end="2026-06-12")
ec, tr, rollc = res["equity"], res["trades"], res["total_roll_cost"]

# V1
identity = 100_000 + tr.pnl_net.sum() - rollc
ok("V1 accounting identity (incl. roll cost)", abs(ec["equity"].iloc[-1] - identity) < 1e-4,
   f"(final={ec['equity'].iloc[-1]:,.2f} vs {identity:,.2f}; roll_cost={rollc:,.2f})")

# V2
cut = "2021-06-30"
res_t = simulate(data, P, 100_000, per_side, roll_bp, mult, start="2014-01-01", end=cut)
e_full = ec["equity"][ec.index <= cut]; e_t = res_t["equity"]["equity"]
common = e_full.index.intersection(e_t.index)[:-1]
diff = (e_full.loc[common] - e_t.loc[common]).abs().max()
ok("V2 no look-ahead (truncation invariance)", diff < 1e-6, f"(max diff = {diff:.2e})")

# V3
prep = {s: prepare_asset(data[s], P) for s in UNIVERSE}
viol_exit = viol_entry = 0
for _, t in tr.iterrows():
    b = prep[t.symbol]
    if t.exit_date in b.index and t.exit_reason == "trail_stop":
        lo, hi, op = b.loc[t.exit_date, ["low", "high", "open"]]
        if not (lo - 1e-6 <= t.exit_px <= hi + 1e-6 or abs(t.exit_px - op) < 1e-6):
            viol_exit += 1
    if t.entry_date in b.index and abs(t.entry_px - b.loc[t.entry_date, "open"]) > 1e-6:
        viol_entry += 1
ok("V3 exit fills inside bar range", viol_exit == 0, f"({viol_exit} violations)")
ok("V3 entries fill at bar open", viol_entry == 0, f"({viol_entry} violations)")

# V4
sample = tr.groupby("symbol").head(10)
bad = 0
for _, t in sample.iterrows():
    d = prep[t.symbol]; i = d.index.get_loc(t.entry_date); sig = d.iloc[i - 1]
    is_first = t.entry_date == tr[(tr.symbol == t.symbol) & (tr.exit_date == t.exit_date)].entry_date.min()
    if is_first:
        valid = ((t.direction > 0 and sig.close > sig.ema and sig.close > sig.hh) or
                 (t.direction < 0 and sig.close < sig.ema and sig.close < sig.ll))
        bad += not valid
ok("V4 entry signals satisfy published rule", bad == 0, f"({bad} bad in sample)")

# V5
eq = ec["equity"].values; years = (ec.index[-1] - ec.index[0]).days / 365.25
cagr_np = (eq[-1] / eq[0]) ** (1 / years) - 1
r = np.diff(eq) / eq[:-1]; n_yr = len(eq) / years
sharpe_np = r.mean() / r.std(ddof=1) * np.sqrt(n_yr)
mdd_np = (eq / np.maximum.accumulate(eq) - 1).min(); em = equity_metrics(ec)
ok("V5 CAGR recompute", abs(cagr_np - em["cagr"]) < 1e-9, f"({cagr_np:.4%})")
ok("V5 Sharpe recompute", abs(sharpe_np - em["sharpe"]) < 1e-6, f"({sharpe_np:.3f})")
ok("V5 MaxDD recompute", abs(mdd_np - em["max_drawdown"]) < 1e-12, f"({mdd_np:.2%})")

# V6
pyr = tr.groupby(["symbol", "exit_date"]).size()
big = tr[tr.r_multiple > 3.0]
ok("V6 large captured trend (R>3) exists", len(big) >= 1, f"({len(big)} units R>3, max {tr.r_multiple.max():.1f}R)")
ok("V6 pyramiding occurs (>1 unit/episode)", (pyr > 1).any(), f"({int((pyr > 1).sum())} pyramided episodes)")

# V7
losers = tr[(tr.pnl_net <= 0) & (tr.exit_reason == "trail_stop")]
med_loss_R = losers.r_multiple.median()
ok("V7 typical losing-stop R ~ -1R", -1.8 <= med_loss_R <= -0.4, f"(median={med_loss_R:.2f}R, worst={tr.r_multiple.min():.2f}R)")

print(f"\nbase config (2014-2026, cash, fractional): Sharpe {em['sharpe']:.2f}  CAGR {em['cagr']:.1%}  "
      f"MaxDD {em['max_drawdown']:.1%}  trades {len(tr)}  roll_cost ${rollc:,.0f}")
