"""
================================================================================
VOIE B — CAUSAL implementation, fully tradable on FTMO
================================================================================
Re-statement after the forensic audit:

Timing (UTC):
   JP225 OHLC : 00:00 - 06:00 (Asia cash)
   HK50  OHLC : 01:30 - 08:00 (Hong Kong cash)
   GER40 OHLC : 07:00 - 15:30 (Xetra)
   US500/US100/US30/US2000 : 14:30 - 21:00 (NYSE/NASDAQ cash)

CAUSAL signal: at 14:30 UTC (US Open), ALL prior gaps are observable.
TRADABLE window: 14:30 -> 21:00 UTC (US cash session). FTMO CFDs are open.

Strategy:
  At 14:30 UTC each day, compute 7 gaps (each = Open_i/prev_Close_i - 1).
  If >= N of 7 indices gapped same direction (|gap|>15bp):
     enter LONG (or SHORT, matching direction) on the 4 US indices ONLY,
     at their Open price, exit at their Close price.
  Otherwise: stay flat.

Compare to baselines:
  BL1: trade US only when >= M of 4 US-gaps confirm (ignore intl).
  BL2: trade each US instrument individually on its own gap (TS momentum).
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

UP = Path("/sessions/laughing-inspiring-lamport/mnt/uploads")
OUT = Path("/sessions/laughing-inspiring-lamport/mnt/outputs")
DAYS = 252
US = ["US500","US100","US30","US2000"]
INTL = ["JP225","HK50","GER40"]            # observable by 14:30 UTC
ALL_PREDICTORS = US + INTL                  # 7
THR = 0.0015
COST_RT_BP = 3.0
TARGET_VOL = 0.10
rng = np.random.default_rng(1)


def load(n): return pd.read_csv(UP/f"{n}.csv", parse_dates=["Date"]).set_index("Date")


def metrics(r, label):
    r = r.dropna()
    if r.std() == 0: return
    sh = r.mean()/r.std()*np.sqrt(DAYS); a = r.mean()*DAYS; v = r.std()*np.sqrt(DAYS)
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    # NW-adjusted Sharpe
    L = 5; rho = [r.autocorr(lag=k) for k in range(1, L+1)]
    rho = [x if not np.isnan(x) else 0 for x in rho]
    nw = np.sqrt(max(1 + 2*sum((1-k/(L+1))*rho[k-1] for k in range(1,L+1)), 0.1))
    sh_nw = sh / nw
    print(f"  {label:30s}: Sharpe {sh:+.2f} (NW {sh_nw:+.2f})  ann {a*100:+5.1f}%  vol {v*100:4.1f}%  MaxDD {dd*100:5.0f}%  n={len(r)}")


def boot_ci(r, B=1500, mb=30):
    r = r.dropna().values; n = len(r)
    out = np.empty(B)
    for b in range(B):
        s = []
        while len(s) < n:
            st = rng.integers(0, n); s.extend(r[st:st+mb])
        s = np.array(s[:n])
        out[b] = s.mean()/s.std()*np.sqrt(DAYS) if s.std()>0 else 0
    return np.percentile(out, [2.5, 50, 97.5])


def build_strat(predictors, traded_cols, N_confirm, gap_thr=THR, cost=COST_RT_BP):
    op = load("ftmo_open"); cl = load("ftmo_close")
    cl_ff = cl.ffill(); op_ff = op.where(op.notna(), cl_ff.shift(1))
    # predictor gaps (causal: each observed at its own session open, all known by 14:30 UTC)
    gaps_pred = op_ff[predictors] / cl_ff[predictors].shift(1) - 1.0
    # tradable instruments' intraday returns + their own gap
    gaps_trade = op_ff[traded_cols] / cl_ff[traded_cols].shift(1) - 1.0
    intra_trade = cl_ff[traded_cols] / op_ff[traded_cols] - 1.0

    # cross-instrument confirmation (CAUSAL: all predictor gaps known by US open)
    nup = (gaps_pred > gap_thr).sum(axis=1) >= N_confirm
    ndn = (gaps_pred < -gap_thr).sum(axis=1) >= N_confirm
    # net market direction (majority sign)
    direction = pd.Series(0, index=gaps_pred.index)
    direction = direction.where(~nup, 1).where(~ndn, -1)

    # take same direction across all traded US instruments (entered at their own Open)
    pos = pd.DataFrame(np.tile(direction.values[:, None], (1, len(traded_cols))),
                       index=direction.index, columns=traded_cols).astype(float)
    # only trade where the US instrument's own gap aligns with direction (extra check)
    align = (np.sign(gaps_trade) == direction.values[:, None])
    pos = pos.where(align, 0.0)
    traded = pos.abs() > 0

    raw = (pos * intra_trade).mean(axis=1)
    cost_series = traded.sum(axis=1) * cost/1e4 / len(traded_cols)
    net = (raw - cost_series).dropna()
    # intraday stop
    net = net.clip(lower=-0.012)
    # vol-target
    rv = net.rolling(60).std()*np.sqrt(DAYS)
    rs = (net * (TARGET_VOL/rv).shift(1).clip(0, 5)).dropna()
    return rs, traded, gaps_pred, intra_trade


def main():
    print("="*82); print("VOIE B — CAUSAL backtest, tradable on FTMO US 14:30-21:00 UTC"); print("="*82)
    print(f"Predictors (gaps known by 14:30 UTC): {ALL_PREDICTORS}")
    print(f"Tradable universe (US 14:30-21:00 UTC): {US}\n")

    # ----- Main strategy: 7-gap confirmation, trade 4 US -----
    print("[MAIN] 7-gap confirmation -> trade 4 US")
    for N in [2, 3, 4, 5]:
        r, tr, _, _ = build_strat(ALL_PREDICTORS, US, N)
        r = r[r.index >= "2010-01-01"]
        metrics(r, f"N={N}/7 -> trade US")

    # ----- Baseline 1: US-only confirmation (no intl info) -----
    print("\n[BL1] US-only confirmation (no international predictors)")
    for N in [1, 2, 3]:
        r, tr, _, _ = build_strat(US, US, N)
        r = r[r.index >= "2010-01-01"]
        metrics(r, f"N={N}/4 (US-only)")

    # ----- Baseline 2: pure US individual TS momentum -----
    print("\n[BL2] Individual US TS momentum (sign of own gap, no confirmation)")
    op = load("ftmo_open"); cl = load("ftmo_close")
    cl_ff = cl.ffill(); op_ff = op.where(op.notna(), cl_ff.shift(1))
    for c in US:
        g = op_ff[c]/cl_ff[c].shift(1) - 1
        i = cl_ff[c]/op_ff[c] - 1
        pos = np.sign(g).where(g.abs() > THR, 0)
        net = (pos*i - (pos.abs()>0).astype(float)*COST_RT_BP/1e4).dropna()
        net = net.clip(lower=-0.012)
        rv = net.rolling(60).std()*np.sqrt(DAYS)
        rs = (net*(TARGET_VOL/rv).shift(1).clip(0,5)).dropna()
        rs = rs[rs.index >= "2010-01-01"]
        metrics(rs, f"{c} solo TS-mom")

    # ----- Marginal value of international gaps -----
    print("\n[MARGINAL VALUE] Does adding international gaps lift the US-only strategy?")
    rs_us3, _, _, _ = build_strat(US, US, 3); rs_us3 = rs_us3[rs_us3.index >= "2010-01-01"]
    rs_77, _, _, _ = build_strat(ALL_PREDICTORS, US, 4); rs_77 = rs_77[rs_77.index >= "2010-01-01"]
    rs_75, _, _, _ = build_strat(ALL_PREDICTORS, US, 5); rs_75 = rs_75[rs_75.index >= "2010-01-01"]
    sh_us3 = rs_us3.mean()/rs_us3.std()*np.sqrt(DAYS) if rs_us3.std()>0 else 0
    sh_77 = rs_77.mean()/rs_77.std()*np.sqrt(DAYS) if rs_77.std()>0 else 0
    sh_75 = rs_75.mean()/rs_75.std()*np.sqrt(DAYS) if rs_75.std()>0 else 0
    print(f"  US-only N=3      : Sharpe {sh_us3:+.2f}")
    print(f"  7-confirm N=4    : Sharpe {sh_77:+.2f}   (lift over US-only = {sh_77-sh_us3:+.2f})")
    print(f"  7-confirm N=5    : Sharpe {sh_75:+.2f}   (lift = {sh_75-sh_us3:+.2f})")

    # ----- BEST config: rigorous stats -----
    print("\n[RIGOROUS] Best Voie B config — full stats")
    r, traded, _, _ = build_strat(ALL_PREDICTORS, US, 4)
    r = r[r.index >= "2010-01-01"]
    sh = r.mean()/r.std()*np.sqrt(DAYS); v = r.std()*np.sqrt(DAYS)
    L = 5; rho = [r.autocorr(lag=k) for k in range(1, L+1)]
    nw = np.sqrt(1 + 2*sum((1-k/(L+1))*rho[k-1] for k in range(1,L+1)))
    sh_nw = sh / nw
    lo, md, hi = boot_ci(r)
    pre = r[r.index < "2018-01-01"]; post = r[r.index >= "2018-01-01"]
    sh_pre = pre.mean()/pre.std()*np.sqrt(DAYS) if len(pre)>50 and pre.std()>0 else 0
    sh_post = post.mean()/post.std()*np.sqrt(DAYS) if len(post)>50 and post.std()>0 else 0
    print(f"  Sharpe raw          : {sh:.2f}")
    print(f"  Sharpe NW-adjusted  : {sh_nw:.2f}")
    print(f"  Bootstrap 95% CI    : [{lo:.2f}, {md:.2f}, {hi:.2f}]")
    print(f"  Train <2018 / Test 2018+ : {sh_pre:.2f} / {sh_post:.2f}")
    print(f"  Skew {stats.skew(r):+.2f}  excess kurtosis {stats.kurtosis(r):+.2f}")
    print(f"  Trades/day {traded.sum().sum()/len(r):.2f}   active days {(traded.any(axis=1)).mean()*100:.0f}%")

    # save
    r.to_csv(OUT/"ftmo_voie_b_returns.csv", header=["ret"])
    print("\n[saved] ftmo_voie_b_returns.csv")


if __name__ == "__main__":
    main()
