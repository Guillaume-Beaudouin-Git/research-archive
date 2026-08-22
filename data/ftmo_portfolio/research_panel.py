"""Assemble the master daily research dataset.

Anchors (documented, accepted for sleeve research; simulator re-times on CET M1):
  - FX/metals/energy/softs: CET-midnight daily bars from M1 (2007+)
  - Indices: panels/ftmo_close.csv exchange-close daily (2000+), validated vs
    NQ databento corr 0.997 (prior program)
  - Crypto: panels (UTC daily close), 2014+
Outputs: prices (close), rets, spreads (recent median RT bps incl. slippage),
swap series long/short (bps/night), swap multipliers.
"""
import numpy as np
import pandas as pd
import config as C
import costs as cm

SLIPPAGE_BPS = {"fx": 0.3, "index": 0.5, "metal": 0.5, "energy_soft": 1.0, "crypto": 2.0}


def load_all(start="2000-01-03"):
    prices, spreads = {}, {}
    # indices from panel (long history)
    idx = pd.read_csv(C.PANELS / "ftmo_close.csv", index_col=0, parse_dates=True)
    for s in C.INDICES:
        prices[s] = idx[s]
    # M1-cached groups
    for s in C.FX + C.METALS + C.ENERGY + C.SOFTS:
        f = C.CACHE / f"{s}_daily_cet.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f)
        d = d[d["n_bars"] > 100]                      # drop degenerate days
        prices[s] = d["close"]
        spreads[s] = d["spread_med_bps"]
    # crypto
    btc = pd.read_csv(C.PANELS / "btc_full.csv", index_col=0, parse_dates=True)
    cr = pd.read_csv(C.PANELS / "crypto_panel.csv", index_col=0, parse_dates=True)
    prices["BTCUSD"] = btc.iloc[:, 0]
    prices["ETHUSD"] = cr["ETHUSD"]
    px = pd.DataFrame(prices).loc[start:]
    px = px[~px.index.duplicated()]
    # business-day master grid (Mon-Fri)
    px = px.asfreq("B") if px.index.freq is None else px
    rets = px.pct_change(fill_method=None)
    # winsor guard vs bad ticks (none expected post-manifest, belt&braces)
    rets = rets.clip(lower=-0.30, upper=0.30)
    return px, rets, spreads


def cost_tables(px: pd.DataFrame, spreads: dict):
    rates = pd.read_csv(C.PANELS / "fx_rates_3m.csv", index_col=0, parse_dates=True)
    prices_today = {s: float(px[s].dropna().iloc[-1]) for s in px.columns}
    usd_rate = {"USD": 1.0, "JPY": 1.0 / prices_today["USDJPY"],
                "CHF": 1.0 / prices_today["USDCHF"], "CAD": 1.0 / prices_today["USDCAD"],
                "EUR": prices_today["EURUSD"], "GBP": prices_today["GBPUSD"],
                "AUD": prices_today["AUDUSD"], "NZD": prices_today["NZDUSD"]}
    prices_today["_usd_rate"] = usd_rate
    model = cm.build_swap_model(prices_today, rates)
    idxg = px.index
    swap_L = pd.DataFrame(index=idxg, columns=px.columns, dtype=float)
    swap_S = pd.DataFrame(index=idxg, columns=px.columns, dtype=float)
    mult = pd.DataFrame(1.0, index=idxg, columns=px.columns)
    for s in px.columns:
        ss = cm.swap_series(s, model, rates, idxg)
        swap_L[s] = ss["long_bps"]; swap_S[s] = ss["short_bps"]
        mult[s] = cm.swap_multiplier(idxg, model.loc[s, "triple"],
                                     crypto=(s in C.CRYPTO)).values
    # round-trip friction = spread (recent 3y median of daily medians) + slip + commission
    rt = {}
    for s in px.columns:
        kind = model.loc[s, "kind"]
        sp = (np.nanmedian(spreads[s].tail(750)) if s in spreads else
              {"index": 1.2, "crypto": 8.0}.get(kind, 2.0))
        rt[s] = sp + 2 * SLIPPAGE_BPS[kind] + cm.commission_bps(s, prices_today[s], usd_rate)
    rt = pd.Series(rt)
    return model, swap_L, swap_S, mult, rt


if __name__ == "__main__":
    px, rets, spreads = load_all()
    model, sL, sS, mult, rt = cost_tables(px, spreads)
    px.to_parquet(C.CACHE / "panel_px.parquet")
    rets.to_parquet(C.CACHE / "panel_rets.parquet")
    sL.to_parquet(C.CACHE / "panel_swapL.parquet")
    sS.to_parquet(C.CACHE / "panel_swapS.parquet")
    mult.to_parquet(C.CACHE / "panel_mult.parquet")
    rt.to_csv(C.OUT / "phase0_rt_cost_bps.csv")
    print("RT cost bps (spread+slip+comm):"); print(rt.round(2).sort_values().to_string())
    print("panel:", px.shape, px.index.min().date(), "->", px.index.max().date())
