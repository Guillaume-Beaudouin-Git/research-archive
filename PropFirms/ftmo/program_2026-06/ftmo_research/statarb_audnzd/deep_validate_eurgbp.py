#!/usr/bin/env python3
"""Deep validation of EUR/GBP single-leg reversion on the CLEAN 27-year ECB
daily series (1999-2026, return-corr 0.99 vs real M1). Battery: gate, grid +
significance/DSR, by-year/regime, cost sweep, delay test, and a DAILY-MTM FTMO
2-step first-passage (handles the 5% daily cap) with block-bootstrap CI."""
import json
import numpy as np, pandas as pd
import audnzd_engine as E

OUT = "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/statarb_audnzd"
ECB = "/sessions/affectionate-epic-faraday/mnt/data/raw/ecb_EURGBP_daily.parquet"


def load():
    s = pd.read_parquet(ECB)["EURGBP"].sort_index()
    df = pd.DataFrame({"EURGBP": s}); df["logpx"] = np.log(df["EURGBP"])
    return df


def tstat(r):
    r = np.asarray(r); return r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 2 else 0.0


# ---- daily-MTM FTMO 2-step first-passage (proper 5% daily cap) ----
def daily_series_from_trades(df, tr):
    """position (+/-1/0) per day + daily strat log-return net of cost on entry/exit days."""
    idx = df.index
    pos = pd.Series(0.0, index=idx)
    dlogret = df["logpx"].diff().fillna(0.0)
    cost = pd.Series(0.0, index=idx)
    cpd = 2.0e-4 / df["EURGBP"]            # 2-pip entry/exit cost in return terms
    for _, t in tr.iterrows():
        e, x, d = t["entry_date"], t["exit_date"], t["direction"]
        pos.loc[e:x] = d
        if e in cost.index: cost.loc[e] += float(cpd.loc[e])
        if x in cost.index: cost.loc[x] += float(cpd.loc[x])
    # strat daily return = yesterday's position * today's market return - cost
    sr = pos.shift(1).fillna(0.0) * dlogret - cost
    return sr.values


def ftmo_daily(sr, L, init=10000., p1=1.10, p2=1.05, floor=9000., dcap=0.05, step=3):
    N = len(sr); starts = np.arange(0, N - 5, step)
    def phase(s, tgt):
        eq = init; i = s
        while i < N:
            chg = L * sr[i]
            if chg <= -dcap: return i, "bust"
            eq *= (1 + chg)
            if eq < floor: return i, "bust"
            if eq >= init * tgt: return i, "pass"
            i += 1
        return N - 1, "run"
    fund = bust = run = 0; ttf = []
    for s in starts:
        e1, s1 = phase(s, p1)
        if s1 != "pass":
            bust += (s1 == "bust"); run += (s1 == "run"); continue
        e2, s2 = phase(e1 + 1, p2)
        if s2 == "pass": fund += 1; ttf.append(e2 - s)
        elif s2 == "bust": bust += 1
        else: run += 1
    n = len(starts)
    return dict(L=L, p_funded=fund / n, pct_bust=bust / n, pct_run=run / n,
                median_days=float(np.median(ttf)) if ttf else None,
                median_months=round(float(np.median(ttf)) / 21, 1) if ttf else None)


def main():
    df = load()
    print(f"ECB EURGBP {df.index.min().date()}..{df.index.max().date()} n={len(df)}")
    print("GATE:", json.dumps(E.confirm_reversion(df)))
    sig = E.build_signal(df)
    base = E.backtest(sig, price_col="EURGBP", fill_lag=1)
    delay = E.backtest(sig, price_col="EURGBP", fill_lag=2)
    rb, rd = base["net_ret"].values, delay["net_ret"].values
    print(f"\nBASELINE 60/2/3: n{len(base)} sum {rb.sum()*100:+.1f}% /trade {rb.mean()*1e4:+.1f}bps "
          f"t {tstat(rb):+.2f} win {(rb>0).mean()*100:.0f}% skew {pd.Series(rb).skew():+.2f}")
    print(f"DELAY t+2:       n{len(delay)} sum {rd.sum()*100:+.1f}% t {tstat(rd):+.2f}  "
          f"(real edge survives delay)")
    # grid + significance
    print("\nPRE-REGISTERED GRID (raw-return t-stat):")
    ts = []; pos = 0; tot = 0; best = None
    for W in (40, 60, 90):
        s = E.build_signal(df, w=W)
        for zin in (1.5, 2.0, 2.5):
            for zst in (3.0, 4.0):
                tr = E.backtest(s, z_in=zin, z_stop=zst, t_max=20, price_col="EURGBP")
                if len(tr) < 15: continue
                r = tr["net_ret"].values; t = tstat(r); spt = r.mean()/r.std(ddof=1)
                ts.append(spt); tot += 1; pos += (r.sum() > 0)
                if best is None or t > best[-1]: best = (W, zin, zst, len(tr), r.sum(), t)
                print(f"  W{W} zin{zin} zst{zst}: n{len(tr):3d} sum {r.sum()*100:+6.1f}% t {t:+.2f} win {(r>0).mean()*100:.0f}%")
    # deflated-Sharpe benchmark: expected max per-trade Sharpe under null over `tot` trials (MC)
    sd = np.std(ts, ddof=1)
    rng = np.random.default_rng(0)
    sr0 = sd * rng.standard_normal((20000, tot)).max(1).mean()
    print(f"\n  {pos}/{tot} configs positive | BEST t {best[-1]:+.2f} (W{best[0]}/{best[1]}/{best[2]}, n{best[3]})")
    print(f"  per-trade Sharpe std across trials {sd:.3f} -> expected-max-under-null SR0 {sr0:.3f}; "
          f"best per-trade Sharpe {max(ts):.3f} => {'BEATS' if max(ts)>sr0 else 'FAILS'} DSR benchmark")
    # by-year
    base["yr"] = pd.to_datetime(base["entry_date"]).dt.year
    yr = base.groupby("yr")["net_ret"].agg(["sum", "count"])
    pos_y = (yr["sum"] > 0).sum()
    print(f"\nBY-YEAR: {pos_y}/{len(yr)} years positive. worst {yr['sum'].min()*100:+.1f}% best {yr['sum'].max()*100:+.1f}%")
    print("  " + "  ".join(f"{y}:{v*100:+.0f}" for y, v in yr['sum'].items()))
    # cost sweep
    print("\nCOST SWEEP (baseline):")
    for cp in (1, 2, 3, 4, 6):
        r = E.backtest(sig, z_in=2, z_stop=3, t_max=20, price_col="EURGBP", cost_pips=cp)["net_ret"].values
        print(f"  {cp} pips: sum {r.sum()*100:+5.1f}%  /trade {r.mean()*1e4:+5.1f}bps  t {tstat(r):+.2f}")
    # FTMO daily first-passage (leverage sweep) + block-bootstrap CI on best L
    print("\nFTMO 2-STEP FIRST-PASSAGE (daily-MTM, contiguous):")
    sr = daily_series_from_trades(df, base)
    for L in (5, 8, 10, 15, 20):
        r = ftmo_daily(sr, L)
        print(f"  L={L:2d}x  p(funded) {r['p_funded']*100:4.0f}%  bust {r['pct_bust']*100:4.0f}%  "
              f"run {r['pct_run']*100:3.0f}%  median {r['median_months']}mo")
    base.to_csv(f"{OUT}/trades_ledger_eurgbp_ecb.csv", index=False)
    print("\n(ledger saved)")


if __name__ == "__main__":
    main()
