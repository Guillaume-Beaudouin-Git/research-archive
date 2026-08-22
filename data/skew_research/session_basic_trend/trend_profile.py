#!/usr/bin/env python3
"""session_basic_trend — PROFILE study of basic discretionary trend setups.
Goal: skew AT THE HOLDING (per-trade) horizon + decorrelation, NOT standalone Sharpe.
GATE-0: only FTMO-tradeable instruments (indices/crypto + GLD/SLV as proxies for the
FTMO XAUUSD/XAGUSD CFDs — deploy = CFD, ETF is backtest proxy). Daily only (OOM-safe)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_basic_trend"


def load():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    for s in ["US500", "US100", "GER40"]:
        px[s] = fc[s]
    cp = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["XAU(GLD proxy)"], px["XAG(SLV proxy)"] = mac["GLD"], cp["SLV"]      # -> FTMO XAUUSD/XAGUSD CFDs
    px["BTC"] = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px); df.index = pd.to_datetime(df.index)
    return df.sort_index()


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def position(setup, p):
    """daily position (-1/0/1), causal (.shift(1))."""
    if setup == "EMA 50/200":
        sig = np.sign(ema(p, 50) - ema(p, 200))
    elif setup == "Donchian 55":
        hi = p.rolling(55).max().shift(1); lo = p.rolling(55).min().shift(1)
        sig = pd.Series(np.where(p > hi, 1.0, np.where(p < lo, -1.0, np.nan)), index=p.index).ffill()
    elif setup == "Momentum MA200":
        sig = np.sign(p - p.rolling(200).mean())
    elif setup == "MACD cross":
        macd = ema(p, 12) - ema(p, 26); sig = np.sign(macd - ema(macd, 9))
    elif setup == "Pullback-in-uptrend":
        up = p > p.rolling(200).mean(); dip = p < ema(p, 20)
        sig = (up & dip).astype(float)           # long-only: buy dips within an uptrend
    return sig.shift(1)


def trades_from_pos(price, pos):
    p = pos.fillna(0).values; px = price.values; dt = price.index; out = []
    i, n = 0, len(p)
    while i < n:
        if p[i] == 0: i += 1; continue
        d = p[i]; entry = i; j = i
        while j < n and p[j] == d: j += 1
        ex = j - 1
        if px[entry] > 0: out.append((d, ex - entry, d * (px[ex]/px[entry] - 1)))
        i = j
    return out


def main():
    import os; os.makedirs(OUT, exist_ok=True)
    df = load(); rets = df.pct_change().clip(-0.5, 0.5)
    eq_proxy = rets[["US500", "US100", "GER40"]].mean(axis=1)      # long-equity beta to decorrelate from
    setups = ["EMA 50/200", "Donchian 55", "Momentum MA200", "MACD cross", "Pullback-in-uptrend"]
    print(f"GATE-0: FTMO-tradeable universe {list(df.columns)} | {df.index.min().date()}..{df.index.max().date()}")
    print("\nPROFILE per setup — skew AT HOLDING (per-trade) horizon + decorrelation (Sharpe is secondary):")
    daily_series = {}
    for su in setups:
        alltr = []; daily = pd.Series(0.0, index=df.index); k = 0
        for c in df.columns:
            s = df[c].dropna()                       # drop NaN-pad (diff start dates) -> clean trades
            pos = position(su, s); alltr += trades_from_pos(s, pos)
            daily = daily.add((pos.reindex(df.index).fillna(0) * rets[c]), fill_value=0); k += 1
        daily = daily / k
        tr = np.array([(t[1], t[2]) for t in alltr], float)
        tr = tr[~np.isnan(tr[:, 1])]
        hold = tr[:, 0]; R = tr[:, 1]
        sk = float(((R - R.mean())**3).mean() / R.std(ddof=1)**3)
        nz = daily[daily != 0]
        shp = float(daily.mean()/nz.std()*np.sqrt(252))
        corr_eq = float(daily.corr(eq_proxy))
        daily_series[su] = daily
        print(f"  {su:20s}: trades {len(R):4d}  med-hold {int(np.median(hold)):3d}d  "
              f"**TRADE-SKEW {sk:+.2f}**  win {(R>0).mean()*100:.0f}%  meanR {R.mean()*100:+.2f}%  "
              f"| daily Sharpe {shp:+.2f}  corr→equity {corr_eq:+.2f}")
    print("\nCorrelation matrix (daily strat returns) — decorrelation check:")
    M = pd.DataFrame(daily_series); M["LongEquity"] = eq_proxy
    print(M.corr().round(2).to_string())
    M.to_csv(f"{OUT}/setup_daily_series.csv")


if __name__ == "__main__":
    main()
