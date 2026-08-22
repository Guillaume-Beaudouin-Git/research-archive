"""
Refinement (modification 2): vol-targeted overnight window + a full-day blend with
the (orthogonal-in-time) US-session momentum.

  * window search: best contiguous overnight window, long, vol-targeted;
  * FULL_DAY = inverse-vol blend of [vol-targeted overnight drift] (21:00->...) and
    [US-session momentum] (sign of pre-US move, held 13:00->21:00). The two trade
    disjoint hours, so the blend simply diversifies across the day.
Run: python mod2.py
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
N_TRIALS = 60
US = list(range(13, 21))

piv0 = iz.hourly_pivot("XAUUSD", anchor_hour=0)
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
ones13 = pd.Series(1.0, index=piv13.index)


def window(start, length):
    return [(start + i) % 24 for i in range(length)]


def report(net, label, cost):
    eq = (1 + net).cumprod()
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, iz.ANN)
    mdd, _ = S.max_drawdown(eq.to_numpy())
    return dict(label=label, cost=cost,
                sharpe=round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 3),
                hac_t=round(float(t), 2), dsr=round(float(dsr.get("dsr", float("nan"))), 3),
                mean_bps=round(float(net.mean() * 1e4), 2), ann_vol=round(float(net.std() * np.sqrt(iz.ANN)), 3),
                maxdd=round(float(mdd), 3), wf=round(float(folds["wf_score"]), 2),
                folds=[round(x, 2) for x in folds["fold_sharpes"]])


# --- overnight window search (vol-targeted long), net 2 bps ---
rows = []
nets = {}
for start in [21, 22, 23, 0]:
    for length in [4, 6, 8, 10, 12, 16]:
        w = window(start, length)
        net, _ = iz.backtest(piv13, ones13, w, cost_bps=2.0, voltarget=True, label=f"ON_{start}_{length}")
        nets[f"ON_{start}_{length}"] = net
        rows.append(report(net, f"ON_{start}_{length}", 2.0))
lb = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
print("=== overnight window search (VT long, net 2 bps) — top 8 ===")
print(lb.head(8)[["label", "sharpe", "hac_t", "dsr", "mean_bps", "ann_vol", "maxdd", "wf"]].to_string(index=False))

# --- US-session momentum (VT), net 2 bps ---
mom_sig = np.sign(iz.win_ret(piv0, range(0, 13)))
mom_net, _ = iz.backtest(piv0, mom_sig, US, cost_bps=2.0, voltarget=True, label="MOM")
print("\nUS momentum:", report(mom_net, "MOM_preUS_US_VT", 2.0))

# --- FULL_DAY blend: best overnight + US momentum (inverse-vol) ---
best_on = lb.iloc[0]["label"]
on_net = nets[best_on]
df = pd.concat([on_net.rename("on"), mom_net.rename("mom")], axis=1).dropna()
w_on, w_mom = 1 / df["on"].std(), 1 / df["mom"].std()
full = (w_on * df["on"] + w_mom * df["mom"]) / (w_on + w_mom)
print(f"\ncorr(overnight, US-momentum) = {df['on'].corr(df['mom']):+.3f}")
print("=== FULL_DAY blend (best overnight + US momentum) ===")
for c in [1.0, 1.5, 2.0]:
    # rebuild both legs at cost c then blend
    on_c, _ = iz.backtest(piv13, ones13, window(int(best_on.split('_')[1]), int(best_on.split('_')[2])),
                          cost_bps=c, voltarget=True)
    mom_c, _ = iz.backtest(piv0, mom_sig, US, cost_bps=c, voltarget=True)
    d = pd.concat([on_c.rename("on"), mom_c.rename("mom")], axis=1).dropna()
    wo, wm = 1 / d["on"].std(), 1 / d["mom"].std()
    fb = (wo * d["on"] + wm * d["mom"]) / (wo + wm)
    print(f"  cost={c}bp:", report(fb, f"FULL_DAY", c))

json.dump({"window_search": rows, "best_on": best_on,
           "full_day_2bp": report(full, "FULL_DAY", 2.0)},
          open(RES / "mod2_summary.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(11, 5))
for nm, s, col in [(best_on, on_net, "seagreen"), ("US momentum", mom_net, "darkorange"),
                   ("FULL_DAY", full, "navy")]:
    ax.plot(s.index, (1 + s).cumprod().values, label=nm, lw=1.3, color=col)
ax.set_yscale("log"); ax.axhline(1, color="black", lw=0.6)
ax.set_title("Gold intraday — overnight + US-momentum blend (net 2 bps/RT)")
ax.set_ylabel("equity (×, log)"); ax.legend(); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_fullday.png", dpi=120); plt.close(fig)
print("\nsaved mod2_summary + fig")
