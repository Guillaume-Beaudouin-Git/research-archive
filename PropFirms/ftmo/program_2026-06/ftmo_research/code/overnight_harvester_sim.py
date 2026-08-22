"""
overnight_harvester_sim.py — Hardening sim for the MA200-gated overnight
equity-drift harvester on NQ (and replicable to other indices).

Purpose (OVERNIGHT_drift_hardening mission)
-------------------------------------------
The *existence* of the overnight equity-risk-premium signal is settled
(see OVERNIGHT_drift_findings.md). This module does NOT re-test the signal.
It prices the DEPLOYABLE number: net of financing (swap) at a given rate,
crash-tail-aware, time-aware, across sizings — using a contiguous real-path
construction and a stationary block bootstrap (NOT an IID bootstrap, which
destroys the regime clustering the trend gate relies on).

Strategy spec
-------------
- One position per session: enter LONG at RTH close[t], exit at RTH open[t+1]
  (harvest the overnight close->open segment), flat intraday.
- Trend gate: hold only if continuous_close[t] > MA200[t] (decision uses only
  information available at close[t] -> no look-ahead). Gate off -> flat, no cost.
- Net overnight P&L on notional = on_return - spread - swap   (in-market nights)
- Position notional = k * current_equity (k = sizing multiple), geometric comp.

FTMO 2-Step $10k rules
----------------------
P1: +10% target (>= 11,000), >= 4 trading days, 5% daily DD (-$500 from day
    start), 10% total DD (absolute floor $9,000). No time limit.
P2: reset to 10,000, +5% target (>= 10,500), same DD rules. Funded = P1 & P2.

Costs (bps of notional per in-market night), defaults editable:
    spread (round-trip US100 CFD) ~ 1.5 bps; swap swept 0..2.5 bps.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

BPS = 1e-4

# Real FTMO swap on a LONG index hold (the overnight premium's required side), bps/night.
# US100 long swap = -3.31 bps/night (ftmo_swaps.py). The overnight equity premium is LONG
# but the positive-swap side of an index is SHORT -> you cannot collect the premium without
# paying this swap. At swap=3.31 the net edge -> ~+0.2 bps/night and p_funded -> ~31%.
# => the swap-sign rule (ftmo_swaps.swap_allowed) forbids holding an index LONG overnight.
REAL_INDEX_LONG_SWAP_BPS = 3.31

# ----------------------------------------------------------------------------
# 1. Build the per-night signal from clean NQ databento daily RTH series
# ----------------------------------------------------------------------------
def build_overnight_signal(daily: pd.DataFrame, ma_win: int = 200) -> pd.DataFrame:
    """
    daily must have: rth_open, rth_close, roll(bool), symbol.
    Returns df with: on_return (clean overnight close->open, roll nights masked),
    cont_close (ratio back-adjusted continuous close), ma, gate(bool),
    in_mkt(bool) = gate & not roll-night.
    """
    d = daily.sort_index().copy()
    # ---- ratio back-adjusted continuous close (remove roll seams) ----
    # daily close-to-close return; on roll days replace c2c by clean intraday
    # return of the NEW contract (close/open) -> drops the artificial roll gap.
    c2c = d["rth_close"].pct_change()
    intraday = d["rth_close"] / d["rth_open"] - 1.0
    adj_ret = c2c.copy()
    adj_ret[d["roll"].values] = intraday[d["roll"].values]
    adj_ret.iloc[0] = 0.0
    d["cont_close"] = 100.0 * (1.0 + adj_ret).cumprod()
    d["ma"] = d["cont_close"].rolling(ma_win).mean()
    # ---- overnight return (tradeable): open[t+1]/close[t]-1, attributed to t ----
    # NOTE we store it on the *decision* night t (position opened at close[t]).
    on_next = d["rth_open"].shift(-1) / d["rth_close"] - 1.0
    # mask nights whose realization crosses a roll seam (next day is roll day)
    roll_next = d["roll"].shift(-1).fillna(False).astype(bool)
    on_next[roll_next.values] = np.nan
    d["on_return"] = on_next
    # ---- gate decided at close[t] (no look-ahead) ----
    d["gate"] = d["cont_close"] > d["ma"]
    d["in_mkt"] = d["gate"] & d["on_return"].notna() & d["ma"].notna()
    return d


# ----------------------------------------------------------------------------
# 2. Stationary block bootstrap of the (in_mkt, on_return) night sequence
# ----------------------------------------------------------------------------
def stationary_bootstrap_paths(in_mkt: np.ndarray, on_ret: np.ndarray,
                               n_paths: int, path_len: int,
                               mean_block: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """
    Politis-Romano stationary bootstrap. Resamples contiguous blocks (geometric
    length, mean=mean_block) to preserve short/medium-range dependence and
    regime clustering. Returns (in_mkt_paths, on_paths) shape (n_paths, path_len).
    """
    n = len(on_ret)
    p = 1.0 / mean_block
    # starting indices for each step
    out_in = np.empty((n_paths, path_len), dtype=np.bool_)
    out_on = np.empty((n_paths, path_len), dtype=np.float32)
    cur = rng.integers(0, n, size=n_paths)
    for t in range(path_len):
        out_in[:, t] = in_mkt[cur]
        out_on[:, t] = on_ret[cur]
        # with prob p start a new block, else advance (wrap)
        newblk = rng.random(n_paths) < p
        cur = np.where(newblk, rng.integers(0, n, size=n_paths), (cur + 1) % n)
    return out_in, out_on


# ----------------------------------------------------------------------------
# 3. Vectorised FTMO 2-step barrier sim across many paths
# ----------------------------------------------------------------------------
def ftmo_2step(in_mkt_paths: np.ndarray, on_paths: np.ndarray,
               k: float, spread_bps: float, swap_bps: float,
               start: float = 10_000.0, p1_target: float = 11_000.0,
               p2_target: float = 10_500.0, daily_loss: float = 500.0,
               total_floor: float = 9_000.0, min_days: int = 4) -> dict:
    """
    Walk each path night-by-night through Phase 1 then Phase 2.
    Net overnight return on notional (in-market) = on - (spread+swap)*BPS.
    Equity multiplies by (1 + k*net) on in-market nights; flat otherwise.
    Daily breach: single-night loss > daily_loss from that day's start equity.
    Returns pass/bust/running fractions and time stats (in *calendar* nights).
    """
    N, T = on_paths.shape
    cost = (spread_bps + swap_bps) * BPS
    net = np.where(in_mkt_paths, on_paths - cost, 0.0).astype(np.float64)
    traded = in_mkt_paths

    eq = np.full(N, start)
    phase = np.ones(N, dtype=np.int8)        # 1=P1, 2=P2
    status = np.zeros(N, dtype=np.int8)       # 0 running, 1 funded, 2 bust
    tdays = np.zeros(N, dtype=np.int32)       # trading days in current phase
    nights_to_fund = np.full(N, -1, dtype=np.int32)
    p1_done_night = np.full(N, -1, dtype=np.int32)

    for t in range(T):
        live = status == 0
        if not live.any():
            break
        nm = traded[:, t] & live              # in-market & live this night
        r = k * net[:, t]
        loss = np.where(r < 0, -r * eq, 0.0)  # $ loss this night
        new_eq = eq + r * eq
        # apply only to in-market live paths
        eq = np.where(nm, new_eq, eq)
        tdays = np.where(nm, tdays + 1, tdays)
        # breaches (only meaningful where traded)
        daily_breach = nm & (loss > daily_loss)
        total_breach = nm & (eq < total_floor)
        bust = live & (daily_breach | total_breach)
        status = np.where(bust, 2, status)
        # targets
        live = status == 0
        in_p1 = live & (phase == 1)
        p1_pass = in_p1 & (eq >= p1_target) & (tdays >= min_days)
        p1_done_night = np.where(p1_pass & (p1_done_night < 0), t, p1_done_night)
        # reset to P2
        eq = np.where(p1_pass, start, eq)
        tdays = np.where(p1_pass, 0, tdays)
        phase = np.where(p1_pass, 2, phase)
        in_p2 = (status == 0) & (phase == 2)
        p2_pass = in_p2 & (eq >= p2_target) & (tdays >= min_days)
        funded = p2_pass
        nights_to_fund = np.where(funded & (nights_to_fund < 0), t, nights_to_fund)
        status = np.where(funded, 1, status)

    funded_mask = status == 1
    return {
        "k": k, "spread_bps": spread_bps, "swap_bps": swap_bps,
        "p_funded": float(funded_mask.mean()),
        "p_bust": float((status == 2).mean()),
        "p_running": float((status == 0).mean()),
        "median_nights_to_fund": float(np.median(nights_to_fund[funded_mask]))
            if funded_mask.any() else None,
    }


# ----------------------------------------------------------------------------
# 4. Rolling-start contiguous real-path cross-check (no resampling)
# ----------------------------------------------------------------------------
def rolling_start_pfunded(in_mkt: np.ndarray, on_ret: np.ndarray, k: float,
                          spread_bps: float, swap_bps: float, **kw) -> dict:
    """Every trading-day index is a start; walk the ONE real contiguous path
    forward to pass/bust/end-of-data. Right-censored near series end."""
    n = len(on_ret)
    # treat as N paths each = the real tail from start i (ragged -> pad with flat)
    # Build as a single pass per start would be O(n^2); n~4000 is fine but we
    # vectorise by reusing ftmo_2step on a padded matrix in chunks.
    res = {"p_funded": 0.0, "p_bust": 0.0, "p_running": 0.0, "n_starts": 0,
           "times": []}
    starts = np.arange(0, n - 5)
    # chunk to bound memory
    for s0 in range(0, len(starts), 1500):
        idx = starts[s0:s0 + 1500]
        L = n - idx.min()
        M = len(idx)
        im = np.zeros((M, L), dtype=np.bool_)
        on = np.zeros((M, L), dtype=np.float32)
        for j, st in enumerate(idx):
            ln = n - st
            im[j, :ln] = in_mkt[st:]
            on[j, :ln] = np.nan_to_num(on_ret[st:])
        r = ftmo_2step(im, on, k, spread_bps, swap_bps, **kw)
        w = M
        res["p_funded"] += r["p_funded"] * w
        res["p_bust"] += r["p_bust"] * w
        res["p_running"] += r["p_running"] * w
        res["n_starts"] += w
    for kk in ("p_funded", "p_bust", "p_running"):
        res[kk] /= res["n_starts"]
    return res


if __name__ == "__main__":
    OUT = Path("/sessions/blissful-upbeat-newton/mnt/outputs")
    daily = pd.read_parquet(OUT / "nq_daily_rth.parquet")
    sig = build_overnight_signal(daily)
    im = sig["in_mkt"].values
    on = sig["on_return"].values
    on_clean = np.nan_to_num(on)

    # ---- signal diagnostics ----
    g = sig[sig["in_mkt"]]
    print("=== NQ overnight signal diagnostics (2010-2026) ===")
    print(f"sessions total            : {len(sig)}")
    print(f"in-market nights (gated)  : {im.sum()}  ({100*im.mean():.1f}% of sessions)")
    print(f"gated overnight mean      : {g['on_return'].mean()*1e4:+.2f} bps/night")
    print(f"ungated overnight mean    : {sig['on_return'].mean()*1e4:+.2f} bps/night")
    print(f"gated overnight std       : {g['on_return'].std()*1e4:.1f} bps")
    print(f"gated Sharpe (ann, /night): {g['on_return'].mean()/g['on_return'].std()*np.sqrt(252):.2f}")
    for yr in [2018, 2020, 2022, 2023]:
        sub = sig[sig.index.year == yr]
        print(f"  {yr}: in-mkt {sub['in_mkt'].mean()*100:4.0f}%  "
              f"overnight gated mean {sub[sub.in_mkt]['on_return'].mean()*1e4 if sub.in_mkt.any() else 0:+.1f} bps")

    rng = np.random.default_rng(7)
    print("\n=== Stationary block bootstrap p(funded), 2-step, N=20000, 6yr cap ===")
    print("spread=1.5 bps. Rows=swap (bps/night), cols=sizing k.  val=p_funded%[median yrs]")
    PATH_LEN = 252 * 6
    SWAPS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, REAL_INDEX_LONG_SWAP_BPS)  # 3.31 = real US100 long
    KS = (0.5, 0.75, 1.0)
    # generate paths ONCE per k, reuse across swaps (same paths, only cost differs)
    grid = {}
    for k in KS:
        imp, onp = stationary_bootstrap_paths(im, on_clean, 20000, PATH_LEN, 21, rng)
        for swap in SWAPS:
            r = ftmo_2step(imp, onp, k, 1.5, swap)
            grid[(k, swap)] = r
        del imp, onp
    hdr = f"{'swap':>5} |" + "".join(f"   k={k:<8}" for k in KS)
    print(hdr); print("-" * len(hdr))
    for swap in SWAPS:
        row = f"{swap:5.1f} |"
        for k in KS:
            r = grid[(k, swap)]
            yrs = (r["median_nights_to_fund"] or np.nan) / 252
            row += f"  {100*r['p_funded']:4.0f}%[{yrs:4.1f}]"
        print(row)

    print("\n=== Rolling-start contiguous cross-check (real path, swap=0, spread=1.5) ===")
    for k in (0.5, 0.75, 1.0):
        r = rolling_start_pfunded(im, on_clean, k, 1.5, 0.0)
        print(f"  k={k}: p_funded {100*r['p_funded']:.0f}%  bust {100*r['p_bust']:.0f}%  "
              f"running {100*r['p_running']:.0f}%  (n_starts={r['n_starts']})")
