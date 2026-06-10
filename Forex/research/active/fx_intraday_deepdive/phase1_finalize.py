"""
phase1_finalize.py — DSR @ cumulative N + p(pass) + noise floor for H1's strongest variant.
Confirms: even the GROSS (un-tradeable) signal, deflated at N, sits at/under the noise floor; NET is dead.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

import fx_intraday_lib as L
import funnel_lib as F
from dsr import deflated_sharpe_ratio

RES = Path(__file__).parent / "results"
N_CUM = 127                       # 108 + 1 prior-look + 1 primary IC + 14 surface + 3 delay (see N_ledger)
_GAMMA = 0.5772156649015329


def e_max_iid(n):
    return (1 - _GAMMA) * norm.ppf(1 - 1.0 / n) + _GAMMA * norm.ppf(1 - 1.0 / (n * math.e)) if n > 1 else 0.0


def best_cell_series(asian_start_hh=23, exit_hh=15):
    """a23_e15 = best gross/cost cell. Equal-weight primary-pool daily gross & net."""
    g, n = {}, {}
    for s in L.PRIMARY:
        t = L.session_table(s, asian_start_hh=asian_start_hh, open_hh=7, exit_hh=exit_hh, delay_bars=1)
        sig = (-t["asian_ret"]) / t["asian_ret"].shift(1).rolling(60, min_periods=20).std(ddof=0)
        t = t.assign(x=sig).dropna(subset=["x", "trade_ret"])
        pos = np.sign(t["x"]); gross = pos * t["trade_ret"]
        cost = 0.5 * F.rt_cost_fraction(s, t["sp_entry"].to_numpy(), t["entry_px"].to_numpy()) \
             + 0.5 * F.rt_cost_fraction(s, t["sp_exit"].to_numpy(), t["exit_px"].to_numpy())
        g[s] = gross.rename(s); n[s] = (gross - cost).rename(s)
    G = pd.concat(g.values(), axis=1, sort=True).mean(axis=1).dropna()
    N = pd.concat(n.values(), axis=1, sort=True).mean(axis=1).dropna()
    return G, N


def main():
    G, Nn = best_cell_series()
    T = len(G)
    se0 = math.sqrt(252.0 / T)
    floor = se0 * e_max_iid(N_CUM)
    dg = deflated_sharpe_ratio(G.to_numpy(), n_trials=N_CUM, periods_per_year=252)
    dn = deflated_sharpe_ratio(Nn.to_numpy(), n_trials=N_CUM, periods_per_year=252)
    pf = F.p_funded(Nn, sigma_d=0.01)
    out = dict(
        cell="a23_e15 (best gross/cost ratio), primary European pool, delay+1",
        N_cumulative=N_CUM, T_days=T, full_sharpe_gross=round(dg["sharpe"], 3),
        full_sharpe_net=round(dn["sharpe"], 3),
        noise_floor_sharpe_at_N=round(floor, 3),
        gross_beats_floor=bool(dg["sharpe"] > floor),
        DSR_gross_at_N=round(dg["dsr"], 4), DSR_net_at_N=round(dn["dsr"], 4),
        p_funded_net=round(pf["p_combined"], 4),
        note="Gross is un-tradeable; net is the only honest number. Net Sharpe<0 -> DSR~0, p(pass)~floor.",
    )
    (RES / "phase1_finalize.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\nNoise floor (Sharpe to beat at N={N_CUM}, T={T}): {floor:.3f}")
    print(f"GROSS Sharpe {dg['sharpe']:.3f}  vs floor {floor:.3f} -> "
          f"{'ABOVE' if dg['sharpe']>floor else 'BELOW'} | DSR_gross {dg['dsr']:.3f}")
    print(f"NET   Sharpe {dn['sharpe']:.3f}  -> DSR_net {dn['dsr']:.3f}, p(pass) {pf['p_combined']:.3f}")


if __name__ == "__main__":
    main()
