"""
tsmom_regen.py — self-contained regeneration of the "TSMOM deployed" book NET OF REAL
per-night swap on held notional (the deployable cost the swap-free chosen_returns.csv omits).

Replicates the dossier construction (swap_test.strat_net: 3-lookback sign, theta gate,
per-inst vol-target, portfolio vol-target, turnover cost, vol-derisk + equity-curve gate
overlays) on LOCAL panels, then charges DIRECTIONAL per-night swap on held notional using
the dossier's MEASURED rate (non-crypto long −3.08 bps/night, short ≈ free; weekend ×3
≈ ×1.45/trading-day; crypto = the UNMEASURED leg, swept {0,12}).

Validates the swap-free version against chosen_returns.csv (Sharpe ~0.80) before trusting
the swap-net output. READ-ONLY on source data; writes only under research/ftmo_survivors_book/.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("<HOME>/Desktop/Algo_claude")
PAN = ROOT / "data/panels"
OUT = ROOT / "research/ftmo_survivors_book/results"
OUT.mkdir(parents=True, exist_ok=True)

INST = ["US500", "GLD", "SLV", "USO", "BTC", "ETH"]
NONCRYPTO = ["US500", "GLD", "SLV", "USO"]
SWAP_LONG_NONCRYPTO = 3.08      # bps/night, measured (US100.cash proxy), long pays
SWAP_SHORT_NONCRYPTO = 0.13     # bps/night, short ~free (the asymmetry)
WEEKEND_MULT = 1.45             # nights per trading-day (weekend x3 amortized)


def load_basket():
    fc = pd.read_csv(PAN / "ftmo_close.csv", index_col=0, parse_dates=True)
    cp = pd.read_csv(PAN / "commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(PAN / "macro_etf_panel.csv", index_col=0, parse_dates=True)
    px = {"US500": fc["US500"], "GLD": mac["GLD"], "SLV": cp["SLV"], "USO": cp["USO"],
          "BTC": pd.read_csv(PAN / "btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"],
          "ETH": pd.read_csv(PAN / "crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]}
    df = pd.DataFrame(px).sort_index()
    df.index = pd.to_datetime(df.index)
    return df


def strat(px, inst, lookbacks=(60, 120, 250), theta=0.34, port_vol=0.10, cost_bps=2.0,
          crypto_swap=0.0, apply_swap=False):
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)
    gross = (pos * rets).sum(1)
    scale = (port_vol / (gross.rolling(60).std() * np.sqrt(252))).clip(upper=3.0).shift(1)
    port = (gross * scale).fillna(0.0) - pos.diff().abs().sum(1) * cost_bps * 1e-4
    mult_vd = (port_vol / (port.rolling(20).std() * np.sqrt(252))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port * mult_vd
    eqc = (1 + port).cumprod()
    g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    mult_eg = 0.4 + 0.6 * g
    port = port * mult_eg
    Stot = scale.fillna(0.0) * mult_vd * mult_eg
    if apply_swap:
        swap = pd.Series(0.0, index=px.index)
        for c in inst:
            notion = pos[c] * Stot                                  # signed notional, L=1
            long_n = notion.clip(lower=0.0)
            short_n = (-notion.clip(upper=0.0))
            if c in NONCRYPTO:
                rate_l, rate_s = SWAP_LONG_NONCRYPTO, SWAP_SHORT_NONCRYPTO
            else:
                rate_l = rate_s = crypto_swap                       # crypto symmetric, unmeasured
            swap += (long_n * rate_l + short_n * rate_s) * 1e-4 * WEEKEND_MULT
        port = port - swap
    return port.dropna()


def sharpe(s):
    s = s[s != 0]
    return float(s.mean() / s.std(ddof=1) * np.sqrt(252)) if s.std(ddof=1) > 0 else 0.0


def peryear(s):
    return {int(y): round(g.mean() / g.std(ddof=1) * np.sqrt(252), 2)
            for y, g in s.groupby(s.index.year) if g.std(ddof=1) > 0}


def main():
    px = load_basket()
    chosen = pd.read_csv(ROOT / "data/ftmo_research/tsmom/chosen_returns.csv",
                         parse_dates=["Date"]).set_index("Date")["0"]
    variants = {}
    # validation: swap-free full basket vs chosen_returns
    sf = strat(px, INST, apply_swap=False)
    variants["swapfree_full"] = sf
    al = pd.concat([sf.rename("regen"), chosen.rename("chosen")], axis=1).dropna()
    print(f"VALIDATION swap-free regen vs chosen_returns.csv:")
    print(f"  regen Sharpe={sharpe(sf):.2f}  chosen Sharpe={sharpe(chosen):.2f}  corr={al.regen.corr(al.chosen):+.3f}  overlap n={len(al)}")

    variants["swapnet_crypto0_full"] = strat(px, INST, crypto_swap=0.0, apply_swap=True)
    variants["swapnet_crypto12_full"] = strat(px, INST, crypto_swap=12.0, apply_swap=True)
    variants["swapfree_nocrypto"] = strat(px, NONCRYPTO, apply_swap=False)
    variants["swapnet_nocrypto"] = strat(px, NONCRYPTO, apply_swap=True)

    print("\nTSMOM variants (post-2007 for FTMO comparability):")
    summ = {}
    for name, s in variants.items():
        s7 = s.loc["2007-01-01":]
        summ[name] = {"ann_sharpe_fullhist": round(sharpe(s), 2),
                      "ann_sharpe_2007+": round(sharpe(s7), 2),
                      "ann_sharpe_OOS_2025_26": round(sharpe(s.loc["2025-01-01":]), 2),
                      "peryear_2018+": {k: v for k, v in peryear(s).items() if k >= 2018}}
        print(f"  {name:24s} Sh(all)={summ[name]['ann_sharpe_fullhist']:+.2f} "
              f"Sh(2007+)={summ[name]['ann_sharpe_2007+']:+.2f} Sh(OOS25-26)={summ[name]['ann_sharpe_OOS_2025_26']:+.2f}")
        s.rename("ret").to_csv(OUT / f"tsmom_{name}.csv")
    json.dump(summ, open(OUT / "tsmom_regen_summary.json", "w"), indent=2, default=str)
    print("\nDossier anchor: swap-free 0.80; net-of-measured-swap (low/zero crypto) Sharpe <=0.33; crypto>=12 -> ~0 (the wall).")
    print("Headline TSMOM for book = swapnet_nocrypto (no unmeasured-rate dependence; cleanest FTMO-deployable).")


if __name__ == "__main__":
    main()
