"""
Gold intraday candidate strategies + leaderboard + cost grid.

Two families:
  * intra-date momentum / seasonality (anchor 0 UTC);
  * session-timing (anchor 13 UTC so the overnight 21:00->13:00 window is contiguous):
    ON_long (long overnight, flat US), US_short (short the US session), and
    SESSION_NEUTRAL = long-overnight + short-US (isolates the timing alpha, ~no net
    gold beta).

Run: python candidates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from engine import stats as S  # noqa: E402
import intraday as iz  # noqa: E402

RES = HERE / "results"
RES.mkdir(exist_ok=True)
N_TRIALS = 40
BASE_COST = 2.0
US = list(range(13, 21))
OVERNIGHT = [21, 22, 23] + list(range(0, 13))

piv0 = iz.hourly_pivot("XAUUSD", anchor_hour=0)
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
ones0 = pd.Series(1.0, index=piv0.index)
ones13 = pd.Series(1.0, index=piv13.index)


def sgn(piv, hours):
    return np.sign(iz.win_ret(piv, hours))


def cond_sgn(piv, hours):
    s = iz.win_ret(piv, hours)
    return np.sign(s).where(s.abs() > s.abs().median(), 0.0)


def metrics_of(net, label, cost):
    eq = (1 + net).cumprod()
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, iz.ANN)
    mdd, _ = S.max_drawdown(eq.to_numpy())
    return dict(label=label, cost_bps=cost, n_days=int(len(net)),
                sharpe_net=float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), hac_t=float(t),
                dsr=float(dsr.get("dsr", float("nan"))), mean_bps=float(net.mean() * 1e4),
                ann_ret=float(net.mean() * iz.ANN), ann_vol=float(net.std() * np.sqrt(iz.ANN)),
                maxdd=float(mdd), wf=float(folds["wf_score"]), fold_sharpes=folds["fold_sharpes"])


def session_neutral(cost):
    on, _ = iz.backtest(piv13, ones13, OVERNIGHT, cost_bps=cost, label="ON")
    us, _ = iz.backtest(piv13, -ones13, US, cost_bps=cost, label="USs")
    return (on.rename("on").to_frame().join(us.rename("us"), how="inner").sum(axis=1))


# ---- build candidate net series at base cost ----
series = {}
series["MOM_preUS_US"], _ = iz.backtest(piv0, sgn(piv0, range(0, 13)), US, cost_bps=BASE_COST, voltarget=True, label="MOM")
series["MOM_cond"], _ = iz.backtest(piv0, cond_sgn(piv0, range(0, 13)), US, cost_bps=BASE_COST, voltarget=True, label="MOMc")
series["SEAS_22_23"], _ = iz.backtest(piv0, ones0, [22, 23], cost_bps=BASE_COST, label="SEAS")
series["ON_long"], _ = iz.backtest(piv13, ones13, OVERNIGHT, cost_bps=BASE_COST, label="ON")
series["US_short"], _ = iz.backtest(piv13, -ones13, US, cost_bps=BASE_COST, label="USs")
series["SESSION_NEUTRAL"] = session_neutral(BASE_COST)

rows = [metrics_of(s, name, BASE_COST) for name, s in series.items()]
lb = pd.DataFrame(rows).sort_values("sharpe_net", ascending=False)
cols = ["label", "sharpe_net", "hac_t", "dsr", "mean_bps", "ann_ret", "ann_vol", "maxdd", "wf"]
print(f"=== leaderboard (net {BASE_COST} bps/RT) ===")
print(lb[cols].round(3).to_string(index=False))
lb.to_csv(RES / "candidates_leaderboard.csv", index=False)

# ---- cost grid on the session strategies ----
print("\n=== cost sensitivity: net Sharpe by round-trip cost ===")
grid = {}
for name in ["ON_long", "SESSION_NEUTRAL", "MOM_cond"]:
    row = {}
    for c in [0, 1, 2, 3, 5]:
        if name == "SESSION_NEUTRAL":
            net = session_neutral(c)
        elif name == "ON_long":
            net, _ = iz.backtest(piv13, ones13, OVERNIGHT, cost_bps=c, label=name)
        else:
            net, _ = iz.backtest(piv0, cond_sgn(piv0, range(0, 13)), US, cost_bps=c, voltarget=True, label=name)
        row[c] = round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 2)
    grid[name] = row
    print(f"  {name:16s}", " ".join(f"{c}bp={row[c]:+.2f}" for c in [0, 1, 2, 3, 5]))
json.dump({"leaderboard": rows, "cost_grid": grid}, open(RES / "candidates_summary.json", "w"), indent=2)

# ---- sub-period stability of the best session strategy ----
best = lb.iloc[0]["label"]
print(f"\n=== best = {best}: per-fold (5 sub-periods) net Sharpe ===")
print("  ", metrics_of(series[best], best, BASE_COST)["fold_sharpes"])

# ---- figure ----
fig, ax = plt.subplots(figsize=(11, 5))
for name, c in [("ON_long", "seagreen"), ("SESSION_NEUTRAL", "navy"), ("MOM_cond", "darkorange")]:
    s = series[name]
    ax.plot(s.index, (1 + s).cumprod().values, label=name, lw=1.3, color=c)
ax.set_yscale("log"); ax.axhline(1, color="black", lw=0.6)
ax.set_title(f"Gold intraday session-timing — equity (net {BASE_COST} bps/RT, 2007–2026)")
ax.set_ylabel("equity (×, log)"); ax.legend(); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_session_equity.png", dpi=120); plt.close(fig)
print("\nsaved leaderboard + cost grid + fig")
