"""Pistes 1-3: funded ablation (canonical FUNDED_WINDOWS) + challenge speed + Sharpe/DSR.
P1 gold regime overlay (DTWEXBGS) — the main one; P2 silver-gold spread; P3 early exit 05:00 gold+WTI.
FTMO criterion = funded Δsurvival (non-dilutive >= -3pt) OR challenge p_pass, NOT Sharpe."""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib as L
import overnight_series as OS
V, C22, E = L.V, L.C22, L.E
OUT = HERE.parent / "results"


def gold_trend_net():
    """Reconstruct gold_trend sleeve daily net (for P2 correlation)."""
    px = pd.read_parquet(E.CACHE / "panel_px.parquet")
    rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")
    WT, _ = E.build_signals()
    w = WT["XAUUSD"].reindex(rets.index).fillna(0.0)
    return (w * rets["XAUUSD"]).rename("gt")


def fund_triplet(series, K, b0):
    net = L.align(series["net"]); low = L.align(series["low"])
    s, fv = L.funded_with(net, low, K)
    return dict(survive252=round(s, 4), d_surv=round(s - b0, 4), fundedV=round(fv, 0), K=K)


def edge_stats(series, label):
    net = series["net"]
    return dict(label=label, n=int((net != 0).sum()), sharpe=round(L.sharpe(net), 2),
                maxdd=round(L.maxdd(net) * 100, 1), worst_low=round(float(series["low"].min()) * 100, 1),
                dsr160=round(L.dsr(net), 3), mean_bp=round(float(net[net != 0].mean()) * 1e4, 2),
                frac_traded=round(float((net != 0).mean()), 3))


def chal(series, K=2.0):
    r = L.challenge(series["net"], series["low"], K=K)
    return dict(p_pass=round(r["p_funded"], 3), attempts=round(r["attempts_mean"], 2),
                p_bust=round(r["p_bust_per_attempt"], 3), K=K)


def main():
    t0 = time.time()
    res = {}
    print("=== book_only survive252 (canonical FUNDED_WINDOWS) ===")
    b0 = L.book_only_survive()
    print(f"  book_only: {b0*100:.1f}%")
    res["book_only_survive252"] = round(b0, 4)

    # ---------------- PISTE 1: gold regime overlay (DTWEXBGS exogenous) ----------------
    print("\n=== PISTE 1 — gold regime overlay (DTWEXBGS) ===")
    gold = L.sleeve("GOLD")[["net", "low"]]
    gate = L.dxy_gate(gold.index)
    gold_ov = gold.copy()
    gold_ov["net"] = gold["net"].to_numpy() * gate
    gold_ov["low"] = gold["low"].to_numpy() * gate
    p1 = {"gold_full": edge_stats(gold, "gold_full"), "gold_overlay": edge_stats(gold_ov, "gold_overlay")}
    p1["gate_frac_on"] = round(float(gate.mean()), 3)
    for tag, ser in [("gold_full", gold), ("gold_overlay", gold_ov)]:
        for K in (1.0, 2.0):
            p1[f"funded_{tag}_K{K}"] = fund_triplet(ser, K, b0)
            print(f"  funded {tag} K={K}: survive {p1[f'funded_{tag}_K{K}']['survive252']*100:.1f}% "
                  f"(Δ{p1[f'funded_{tag}_K{K}']['d_surv']*100:+.1f})")
    p1["chal_gold_full"] = chal(gold); p1["chal_gold_overlay"] = chal(gold_ov)
    print(f"  Sharpe full {p1['gold_full']['sharpe']} maxDD {p1['gold_full']['maxdd']}% | "
          f"overlay {p1['gold_overlay']['sharpe']} maxDD {p1['gold_overlay']['maxdd']}% (gate on {p1['gate_frac_on']*100:.0f}%)")
    res["PISTE1"] = p1

    # ---------------- PISTE 2: silver-gold spread (silver alive per P0) ----------------
    print("\n=== PISTE 2 — silver-gold spread ===")
    gw = OS._wins(OS._win_ret(OS._hourly_pivot("XAUUSD", 13), OS.SPECS["GOLD"]["hours"]))
    sw = OS._wins(OS._win_ret(OS._hourly_pivot("XAGUSD", 13).loc["2014":], OS.SPECS["SILVER"]["hours"]))
    j = pd.concat([sw.rename("s"), gw.rename("g")], axis=1).dropna()
    import statsmodels.api as sm
    beta = float(sm.OLS(j["s"], sm.add_constant(j["g"])).fit().params.iloc[1])
    spr = L.spread(beta)
    silv = L.sleeve("SILVER")[["net", "low"]]
    gt = gold_trend_net()
    sp_exit = spr["net"].copy(); sp_exit.index = pd.to_datetime(sp_exit.index)
    corr = round(float(pd.concat([sp_exit.rename("sp"), gt], axis=1).dropna().corr().iloc[0, 1]), 3)
    p2 = {"beta_silver_gold": round(beta, 3), "spread": edge_stats(spr, "spread"),
          "silver_solo": edge_stats(silv, "silver_solo"), "corr_spread_goldtrend": corr}
    for tag, ser in [("spread", spr), ("silver_solo", silv)]:
        p2[f"funded_{tag}_K1"] = fund_triplet(ser, 1.0, b0)
        print(f"  funded {tag} K=1: survive {p2[f'funded_{tag}_K1']['survive252']*100:.1f}% "
              f"(Δ{p2[f'funded_{tag}_K1']['d_surv']*100:+.1f})")
    p2["chal_spread"] = chal(spr)
    print(f"  beta {beta:.2f} | spread Sharpe {p2['spread']['sharpe']} maxDD {p2['spread']['maxdd']}% "
          f"corr_goldtrend {corr}")
    res["PISTE2"] = p2

    # ---------------- PISTE 3: early exit 05:00 (gold + WTI) ----------------
    print("\n=== PISTE 3 — early exit 05:00 (gold + WTI) ===")
    EARLY = [23, 0, 1, 2, 3, 4]
    p3 = {}
    for inst in ("GOLD", "WTI"):
        full = L.sleeve(inst)[["net", "low"]]
        early = L.sleeve(inst, hours=EARLY)[["net", "low"]]
        p3[f"{inst}_full"] = edge_stats(full, f"{inst}_full")
        p3[f"{inst}_early05"] = edge_stats(early, f"{inst}_early05")
        for tag, ser in [(f"{inst}_full", full), (f"{inst}_early05", early)]:
            p3[f"funded_{tag}_K1"] = fund_triplet(ser, 1.0, b0)
        p3[f"chal_{inst}_full"] = chal(full); p3[f"chal_{inst}_early05"] = chal(early)
        print(f"  {inst}: full Sh {p3[f'{inst}_full']['sharpe']} low {p3[f'{inst}_full']['worst_low']}% "
              f"Δsurv {p3[f'funded_{inst}_full_K1']['d_surv']*100:+.1f} | "
              f"early Sh {p3[f'{inst}_early05']['sharpe']} low {p3[f'{inst}_early05']['worst_low']}% "
              f"Δsurv {p3[f'funded_{inst}_early05_K1']['d_surv']*100:+.1f}")
    res["PISTE3"] = p3

    OUT.mkdir(exist_ok=True)
    (OUT / "run_pistes.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten run_pistes.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
