#!/usr/bin/env python3
"""skew_research / session_cowork — Phase 1: raw edge + SKEW for skew-positive candidates.
Naked literature signals (L10), NO cost yet, generous gate (t>2 raw & skew>=0).
New tests here: Donchian breakout, cross-sectional momentum, long-vol (VXX).
TSMOM and carry are cited from archive (not re-proven)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"
OUT = "/sessions/affectionate-epic-faraday/mnt/data/skew_research/session_cowork"


def load_basket():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    px["US500"] = fc["US500"]
    cp = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["GLD"], px["SLV"], px["USO"] = mac["GLD"], cp["SLV"], cp["USO"]
    px["BTC"] = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px); df.index = pd.to_datetime(df.index)
    return df.sort_index()


def stats(x, lab):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; nz = x[x != 0]
    s = nz.std(ddof=1)
    eq = np.cumprod(1 + x); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return dict(cand=lab, n=int(len(x)), mean_bps=round(float(x.mean()*1e4), 2),
                t=round(float(x.mean()/s*np.sqrt(len(nz))), 2),
                skew=round(float(((x-x.mean())**3).mean()/s**3), 2),
                ann_sharpe=round(float(x.mean()/s*np.sqrt(252)), 2),
                hit=round(float((nz > 0).mean()), 2), maxdd_pct=round(float(dd*100), 1))


def voltarget_combine(sig_df, rets, port_vol=0.10):
    rv = rets.rolling(60).std()*np.sqrt(252)
    pos = (sig_df * (0.10/rv).clip(upper=5)).shift(1)
    gross = (pos*rets).sum(1)
    scale = (port_vol/(gross.rolling(60).std()*np.sqrt(252))).clip(upper=3).shift(1)
    return (gross*scale).dropna()


def main():
    import os; os.makedirs(OUT, exist_ok=True)
    px = load_basket(); rets = px.pct_change().clip(-0.5, 0.5)
    series = {}

    # --- 2. DONCHIAN breakout (two-sided, 20-day channel) ---
    hi = px.rolling(20).max().shift(1); lo = px.rolling(20).min().shift(1)
    sig = pd.DataFrame(np.where(px > hi, 1.0, np.where(px < lo, -1.0, np.nan)), index=px.index, columns=px.columns).ffill()
    donch = voltarget_combine(sig, rets); series["Donchian-breakout"] = donch

    # --- 3. CROSS-SECTIONAL momentum (rank 90d return; long top2 / short bottom2) ---
    mom = px.pct_change(90)
    rank = mom.rank(axis=1)
    n = px.notna().sum(1)
    longs = rank.ge(n.values[:, None] - 1, axis=0)      # top 2
    shorts = rank.le(2)                                  # bottom 2
    xsig = (longs.astype(float) - shorts.astype(float))
    xsmom = voltarget_combine(xsig, rets); series["XS-momentum"] = xsmom

    # --- 5. LONG-VOL / tail (VXX daily return) ---
    vxx = pd.read_csv(f"{D}/panels/vol_etf_panel.csv", index_col=0, parse_dates=True)["VXX"]
    longvol = vxx.pct_change().clip(-0.5, 1.0).dropna(); series["Long-vol(VXX)"] = longvol

    # also: long-equity proxy for phase-3 correlation
    series["[proxy]Long-US500"] = rets["US500"].dropna()

    print("=== PHASE 1 — raw edge + skew (NO cost, generous gate t>2 & skew>=0) ===")
    for lab, s in series.items():
        st = stats(s.values, lab);
        gate = "PHASE2" if (st["t"] > 2 and st["skew"] >= 0) else ("flag:skew<0" if st["skew"] < 0 else "no-raw-edge")
        print(f"  {lab:20s} mean {st['mean_bps']:+6.2f}bps  t {st['t']:+5.2f}  SKEW {st['skew']:+5.2f}  "
              f"Sharpe {st['ann_sharpe']:+.2f}  hit {st['hit']}  maxDD {st['maxdd_pct']:.0f}%  -> {gate}")
        s.to_csv(f"{OUT}/series_{lab.replace('[proxy]','').replace('(','_').replace(')','')}.csv")
    # CITED from archive (not re-proven):
    print("\n  [CITE] TSMOM two-sided     -> archive ftmo_research/tsmom: daily skew ~-0.04..-0.15 (positive at trade/monthly horizon),")
    print("         Sharpe 0.85 gross; net of MEASURED swap edge ~0 (container-math). Best candidate but cost-degraded.")
    print("  [CITE] Carry (FX/MF)       -> archive: carry = NEGATIVE skew native (carry-crash); parallel J1/G1 found carry=beta-proxy (L32 one-sided). WRONG profile flag.")
    # save the combined frame for phase-3 correlation
    pd.DataFrame(series).to_csv(f"{OUT}/phase1_series_all.csv")


if __name__ == "__main__":
    main()
