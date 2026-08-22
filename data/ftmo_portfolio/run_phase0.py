"""Phase 0 validation: cost model build + cross-checks + lot quantization table."""
import subprocess
import numpy as np
import pandas as pd
import config as C
import importlib, costs as costs_mod
importlib.reload(costs_mod)
from costs import (build_swap_model, swap_bps_per_night_today, commission_bps,
                   lot_table, PAIR_LEGS)

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)


def last_close(sym):
    f = C.M1_DIR / f"{sym}_M1.csv"
    if not f.exists():
        return np.nan
    line = subprocess.run(["tail", "-1", str(f)], capture_output=True, text=True).stdout
    try:
        return float(line.split(",")[4])
    except Exception:
        return np.nan


syms_m1 = C.FX + C.INDICES + C.METALS + C.ENERGY + ["COCOA","COFFEE","SUGAR","COTTON","SOYBEAN"]
prices = {s: last_close(s) for s in syms_m1}
# crypto prices from panels
btc = pd.read_csv(C.PANELS / "btc_full.csv", index_col=0, parse_dates=True)
cr = pd.read_csv(C.PANELS / "crypto_panel.csv", index_col=0, parse_dates=True)
prices["BTCUSD"] = float(btc.iloc[-1, 0]); prices["ETHUSD"] = float(cr["ETHUSD"].dropna().iloc[-1])
# USD conversion for quote/base ccys (price of 1 unit in USD)
usd_rate = {"USD": 1.0,
            "JPY": 1.0 / prices["USDJPY"], "CHF": 1.0 / prices["USDCHF"],
            "CAD": 1.0 / prices["USDCAD"], "EUR": prices["EURUSD"],
            "GBP": prices["GBPUSD"], "AUD": prices["AUDUSD"], "NZD": prices["NZDUSD"]}
prices["_usd_rate"] = usd_rate

rates = pd.read_csv(C.PANELS / "fx_rates_3m.csv", index_col=0, parse_dates=True)

print("=== last prices ==="); print({k: round(v, 4) for k, v in prices.items() if k != "_usd_rate"})

model = build_swap_model(prices, rates)
print("\n=== swap model (bps/night, signed; mL/mS markups %/yr) ===")
print(model.round(3).to_string())

# --- cross-checks ---
print("\n=== CROSS-CHECKS ===")
us100 = model.loc["US100"]
print(f"US100 long {us100.lb:+.2f} bps/night (anchor -3.08)  short {us100.sb:+.2f} (anchor +0.13)")
uj = model.loc["USDJPY"]
print(f"USDJPY long {uj.lb:+.2f} (expect ~+0.20)  short {uj.sb:+.2f} (expect ~-1.6)")
eu = model.loc["EURUSD"]
print(f"EURUSD long {eu.lb:+.2f} (expect ~-1.05)  short {eu.sb:+.2f} (expect ~+0.05)")
xau = model.loc["XAUUSD"]
print(f"XAUUSD long {xau.lb:+.2f}  short {xau.sb:+.2f}  (gold px {prices['XAUUSD']})")

comm = {s: commission_bps(s, prices.get(s, np.nan), usd_rate) for s in C.UNIVERSE}
print("\n=== commissions RT bps ===")
print({k: round(v, 2) for k, v in comm.items()})

lots = lot_table(prices, usd_rate)
lots["pct_of_10k_per_step"] = lots["step_usd"] / C.ACCOUNT_SIZE * 100
lots["pct_of_10k_min"] = lots["min_usd"] / C.ACCOUNT_SIZE * 100
print("\n=== lot quantization ($10k account) ===")
print(lots.round(2).to_string())

model.to_csv(C.OUT / "phase0_swap_model.csv")
lots.to_csv(C.OUT / "phase0_lot_table.csv")
pd.Series(comm).to_csv(C.OUT / "phase0_commissions_rt_bps.csv")
pd.Series({k: v for k, v in prices.items() if k != "_usd_rate"}).to_csv(C.OUT / "phase0_prices.csv")
print("\nsaved -> outputs/phase0_*.csv")
