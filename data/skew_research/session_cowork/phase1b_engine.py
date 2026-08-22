#!/usr/bin/env python3
"""session_cowork — Phase 1 for the 5 microstructure/behavioral candidates.
Raw edge + SKEW, naked signals (L10), generous gate. Gap-fade includes the
delay+1 execution test IN phase 1 (per brief). NO cost yet (except gap-fade delay)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_cowork"
NQ = f"{D}/raw/NQ_1min_databento_2010-2026.parquet"


def st(x, lab):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; s = x.std(ddof=1)
    return dict(cand=lab, n=int(len(x)), mean_bps=round(float(x.mean()*1e4), 2),
                t=round(float(x.mean()/s*np.sqrt(len(x))), 2) if s > 0 else 0,
                skew=round(float(((x-x.mean())**3).mean()/s**3), 2) if s > 0 else 0,
                hit=round(float((x > 0).mean()), 2))


def gap_fade():
    df = pd.read_parquet(NQ, columns=["open","high","low","close","is_rth","is_roll_day"])
    df = df[df["is_rth"] & ~df["is_roll_day"]]; idx = df.index.tz_convert("US/Eastern")
    di = (idx.year*10000+idx.month*100+idx.day).to_numpy()
    O, C = df["open"].to_numpy(), df["close"].to_numpy()
    chg = np.where(np.diff(di) != 0)[0]+1; starts = np.concatenate([[0], chg]); ends = np.concatenate([chg, [len(C)]])
    op = O[starts]; cl = C[ends-1]; c30 = np.array([C[min(s+30, e-1)] for s, e in zip(starts, ends)])  # price ~30min after open
    gap = op[1:]/cl[:-1]-1                 # overnight gap (open_t vs close_{t-1})
    intra_full = cl[1:]/op[1:]-1           # open->close
    intra_del = cl[1:]/c30[1:]-1           # +30min->close (delay test)
    thr = np.nanpercentile(np.abs(gap), 80)   # large gaps = top quintile
    big = np.abs(gap) > thr
    fade = -np.sign(gap)                   # fade the gap
    return dict(full=st(fade[big]*intra_full[big], "GapFade open->close"),
                delay=st(fade[big]*intra_del[big], "GapFade +30min->close (delay test)"))


def post_limit():
    px = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)["US500"].dropna()
    r = px.pct_change(); sd = r.rolling(20).std()
    extreme = (r.abs() > 2.5*sd)            # ~limit-move proxy
    fwd = r.shift(-1)                        # next-day return
    cont = (np.sign(r)*fwd)[extreme].dropna()      # continuation
    rev = (-np.sign(r)*fwd)[extreme].dropna()      # reversion
    return dict(cont=st(cont.values, "PostExtreme continuation"), rev=st(rev.values, "PostExtreme reversion"))


def sector_pairs():
    px = pd.read_csv(f"{D}/panels/single_stocks.csv", index_col=0, parse_dates=True)
    duos = [("XOM","CVX"),("JPM","BAC"),("KO","PEP"),("V","MA"),("HD","LOW"),("GS","MS")]
    allR = []
    for a, b in duos:
        if a not in px or b not in px: continue
        la, lb = np.log(px[a]), np.log(px[b]); sp = (la-lb)
        z = (sp - sp.rolling(60).mean())/sp.rolling(60).std()
        ra, rb = px[a].pct_change(), px[b].pct_change()
        pos = (-np.sign(z.where(z.abs() > 2, 0.0))).shift(1)   # fade |z|>2 spread
        allR.append((pos*(ra-rb)).dropna())
    R = pd.concat(allR).dropna()
    return st(R.values, "Sector-pairs (intra-sector MR)")


def vvix():
    v = pd.read_csv(f"{D}/panels/vix.csv", index_col=0, parse_dates=True)
    spx = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)["US500"]
    vv = v["^VVIX"]; vvz = (vv - vv.rolling(60).mean())/vv.rolling(60).std()
    fwd5 = spx.pct_change(5).shift(-5)
    j = pd.DataFrame({"vvz": vvz, "fwd5": fwd5}).dropna()
    c = j["vvz"].corr(j["fwd5"])
    # simple signal: high VVIX z -> risk-off (short equity)?  edge of -sign(vvz) on fwd1
    fwd1 = spx.pct_change().shift(-1)
    sig = (-np.sign(vvz.where(vvz.abs() > 1, 0.0))).shift(1)
    edge = (sig*fwd1).dropna()
    return dict(corr_vvz_fwd5=round(float(c), 3), edge=st(edge.values, "VVIX->fwd-equity signal"))


def main():
    print("=== PHASE 1b — microstructure/behavioral (raw, generous gate t>2 & skew>=0) ===")
    gf = gap_fade()
    for k in ("full", "delay"): print("  ", gf[k])
    pl = post_limit()
    for k in ("cont", "rev"): print("  ", pl[k])
    print("  ", sector_pairs())
    vv = vvix()
    print("   VVIX corr(z, fwd5d-equity) =", vv["corr_vvz_fwd5"], "|", vv["edge"])
    print("\n  [note] Intraday volume U-shape: no clean standalone signal (it is an execution-timing overlay);")
    print("         intraday => the ORB cost-kill applies (archived). Not a standalone skew+ edge. Characterized, not tested.")


if __name__ == "__main__":
    main()
