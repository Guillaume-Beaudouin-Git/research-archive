"""
run_improvements.py — test the PRE-REGISTERED improvement set (PRE_REGISTRATION.md) on the two
real edges (RH + TSMOM). Reuses verbatim: funnel_lib (true-UTC daily + real CFDCostModel rt_cost),
the audit's monotone first-passage engine, and the survivors `strat()` construction + swap model.
The ONLY change in I1 is the instrument set (FTMO-executable CFDs, not non-FTMO ETF proxies) + real
CFD swap. No new tuning. Causal, real cost incl. swap, untouched OOS, walk-forward, DSR at cumulative N.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "research/ftmo_candidate_funnel"))       # funnel_lib (cost + daily)
sys.path.insert(0, str(ROOT / "research/ftmo_portfolio_audit/code"))   # firstpassage (engine)
import funnel_lib as F
import firstpassage as fp
OUT = Path(__file__).parent / "results"; OUT.mkdir(exist_ok=True)

IS_END, OOS0, OOS1 = "2024-12-31", "2025-01-01", "2026-06-05"
EULER = 0.5772156649
PPY = 252
N_CUM = 97 + 6          # cumulative honest N = funnels (97) + 6 variants run here
WEEKEND_MULT = 1.45
SWAP_L, SWAP_S = 3.08, 0.13                 # measured non-crypto proxy (bps/night), long pays, short ~free
FTMO_BASKET = ["US500", "US100", "GER40", "XAUUSD", "BTCUSD"]   # all FTMO-executable CFDs
CRYPTO = ["BTCUSD"]

# ── helpers (match survivors book.py) ─────────────────────────────────────────
def ann_sharpe(s):
    s = s.dropna(); s = s[s != 0]
    return float(s.mean() / s.std(ddof=1) * np.sqrt(PPY)) if len(s) > 5 and s.std(ddof=1) > 0 else 0.0

def vt(s, sigma=0.01, lookback=63, cap=4.0):
    s = s.dropna()
    scale = (sigma / s.rolling(lookback).std()).clip(upper=cap).shift(1)
    return (s * scale).dropna()

def sharpe_ci(s, nb=2000, seed=1):
    s = s.dropna().values; T = len(s)
    if T < 60: return (np.nan, np.nan, np.nan)
    block = max(2, int(round(np.sqrt(T)))); rng = np.random.default_rng(seed); out = []
    nblk = int(np.ceil(T / block))
    for _ in range(nb):
        starts = rng.integers(0, T, nblk)
        idx = np.concatenate([np.arange(st, st + block) % T for st in starts])[:T]
        b = s[idx]; sd = b.std(ddof=1)
        out.append(b.mean() / sd * np.sqrt(PPY) if sd > 0 else 0.0)
    return (float(np.percentile(out, 5)), float(np.median(out)), float(np.percentile(out, 95)))

def dsr(s, n_trials):
    r = s.dropna().values; T = len(r); srd = r.mean() / r.std(ddof=1)
    g3 = skew(r, bias=False); g4 = kurtosis(r, fisher=False, bias=False)
    se = np.sqrt(max((1 - g3 * srd + ((g4 - 1) / 4) * srd ** 2) / (T - 1), 1e-12))
    emax = se * ((1 - EULER) * norm.ppf(1 - 1 / n_trials) + EULER * norm.ppf(1 - 1 / (n_trials * np.e)))
    return round(float(norm.cdf((srd - emax) / se)), 3)

def walk_forward(s, n=6):
    s = s.dropna()
    folds = np.array_split(np.arange(len(s)), n)
    sh = [round(ann_sharpe(s.iloc[f]), 2) for f in folds]
    return {"folds": sh, "pct_pos": float(np.mean(np.array(sh) > 0)), "worst": min(sh)}

def peryear(s):
    return {int(y): round(g.mean() / g.std(ddof=1) * np.sqrt(PPY), 2)
            for y, g in s.groupby(s.index.year) if g.std(ddof=1) > 0}

# ── I1: FTMO-CFD-native TSMOM (survivors strat() construction, FTMO instruments, real cost+swap) ──
def strat_ftmo(insts, crypto_swap=0.0, apply_swap=True, lookbacks=(60, 120, 250), theta=0.34, port_vol=0.10):
    px = pd.DataFrame({s: F.load_daily(s)["close"] for s in insts}).sort_index()
    rtc = pd.DataFrame({s: F.load_daily(s)["rt_cost"] for s in insts}).reindex(px.index)
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(PPY)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig * (port_vol / rv).clip(upper=5.0)).shift(1)
    gross = (pos * rets).sum(1)
    scale = (port_vol / (gross.rolling(60).std() * np.sqrt(PPY))).clip(upper=3.0).shift(1)
    turn_cost = (pos.diff().abs() * 0.5 * rtc).sum(1)              # REAL per-instrument cost on turnover
    port = (gross * scale).fillna(0.0) - turn_cost
    mult_vd = (port_vol / (port.rolling(20).std() * np.sqrt(PPY))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port * mult_vd
    eqc = (1 + port).cumprod()
    g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    mult_eg = 0.4 + 0.6 * g
    port = port * mult_eg
    Stot = scale.fillna(0.0) * mult_vd * mult_eg
    if apply_swap:
        swap = pd.Series(0.0, index=px.index)
        for c in insts:
            notion = pos[c] * Stot
            long_n = notion.clip(lower=0.0); short_n = -notion.clip(upper=0.0)
            rl, rs = (crypto_swap, crypto_swap) if c in CRYPTO else (SWAP_L, SWAP_S)
            swap += (long_n * rl + short_n * rs) * 1e-4 * WEEKEND_MULT
        port = port - swap
    return port.dropna()

# ── combination (vt each sleeve, align live, equal or risk-parity; optional book-level const-vol) ──
def combine(sleeves, weight="equal", book_constvol=False):
    df = pd.concat({k: vt(v) for k, v in sleeves.items()}, axis=1)
    start = max(df[c].first_valid_index() for c in df.columns)
    df = df.loc[start:]; z = df.fillna(0.0)
    if weight == "equal":
        comb = z.mean(axis=1)
    else:
        inv = 1.0 / df.rolling(63).std().shift(1).replace(0, np.nan)
        w = inv.div(inv.sum(axis=1), axis=0).fillna(0.0)
        comb = (w * z).sum(axis=1)
    if book_constvol:
        comb = vt(comb)                       # target the COMBINED book to constant 1%/day
    return comb.dropna()

def ppass(series, L, H):
    return fp.cdf_sequential(series, L, [H], n_paths=15000)[H]

def ppass_ci(series, L, H, n_outer=60):
    return fp.outer_resample_ci(series, L, H, n_outer=n_outer, n_paths=6000)

def fix_L_on_IS(series):
    iss = series.loc[:IS_END]
    grid = [1.5, 2.0, 2.5, 3.0, 3.5]
    return max(grid, key=lambda L: ppass(iss, L, 252))

def book_report(name, comb):
    L = fix_L_on_IS(comb)
    iss, oos = comb.loc[:IS_END], comb.loc[OOS0:OOS1]
    tbl = {}
    for win, s in [("IS", iss), ("OOS", oos)]:
        for H, mo in [(126, "6mo"), (252, "12mo")]:
            ci = ppass_ci(s, L, H)
            tbl[f"{win}_{mo}"] = {"p": round(ci["mean"], 3), "ci90": [round(ci["ci90"][0], 3), round(ci["ci90"][1], 3)]}
    return {"name": name, "Lstar_IS": L, "range": [str(comb.index.min().date()), str(comb.index.max().date())],
            "annSh_full": round(ann_sharpe(comb), 2), "annSh_IS": round(ann_sharpe(iss), 2),
            "annSh_OOS": round(ann_sharpe(oos), 2), "exkurt": round(float(kurtosis(comb.dropna(), fisher=True, bias=False)), 1),
            "wf": walk_forward(comb), "dsr_N103": dsr(comb, N_CUM), "dsr_N500": dsr(comb, 500),
            "ppass": tbl, "mono_OOS": {h: round(ppass(oos, L, h), 3) for h in [63, 126, 189, 252]}}


def main():
    rep = {"cumulative_N": N_CUM, "note_N": "N=103 floor (97 funnels + 6 here); true cumulative >=500 (RH 109-lib + TSMOM program)"}
    # ---- load edges ----
    RH = pd.read_csv(ROOT / "research/s076_replication/results/mtm_deployable.csv", parse_dates=["date"]).set_index("date")["ret"]
    TS_base = pd.read_csv(ROOT / "research/ftmo_survivors_book/results/tsmom_swapnet_nocrypto.csv", index_col=0, parse_dates=True).iloc[:, 0]
    TS_base.index = pd.to_datetime(TS_base.index)

    # ---- I1: FTMO-native TSMOM (swap-net no-crypto and crypto0) ----
    print("Building I1 FTMO-CFD-native TSMOM ...")
    TS_i1_nc = strat_ftmo([s for s in FTMO_BASKET if s not in CRYPTO], apply_swap=True)          # no-crypto
    TS_i1_c0 = strat_ftmo(FTMO_BASKET, crypto_swap=0.0, apply_swap=True)                          # crypto swap 0
    TS_i1_free = strat_ftmo(FTMO_BASKET, apply_swap=False)                                        # swap-free ref
    for nm, s in [("RH", RH), ("TSMOM_baseline_ETF_swapnet", TS_base),
                  ("TSMOM_I1_FTMOnative_swapnet_nocrypto", TS_i1_nc),
                  ("TSMOM_I1_FTMOnative_swapnet_crypto0", TS_i1_c0),
                  ("TSMOM_I1_FTMOnative_swapFREE(ref)", TS_i1_free)]:
        ic, oc = sharpe_ci(s.loc[:IS_END]), sharpe_ci(s.loc[OOS0:OOS1])
        print(f"  {nm:42s} full {ann_sharpe(s):+.2f} | IS {ic[1]:+.2f}[{ic[0]:+.2f},{ic[2]:+.2f}] OOS {oc[1]:+.2f}[{oc[0]:+.2f},{oc[2]:+.2f}] kurt {kurtosis(s.dropna(),fisher=True,bias=False):.0f}")
    rep["edges"] = {
        "RH": {"full": ann_sharpe(RH), "OOS": round(ann_sharpe(RH.loc[OOS0:OOS1]), 2), "peryear": peryear(RH)},
        "TSMOM_baseline_ETF": {"full": ann_sharpe(TS_base), "OOS": round(ann_sharpe(TS_base.loc[OOS0:OOS1]), 2)},
        "TSMOM_I1_FTMOnative_nocrypto": {"full": ann_sharpe(TS_i1_nc), "OOS": round(ann_sharpe(TS_i1_nc.loc[OOS0:OOS1]), 2), "peryear": peryear(TS_i1_nc)},
        "TSMOM_I1_FTMOnative_crypto0": {"full": ann_sharpe(TS_i1_c0), "OOS": round(ann_sharpe(TS_i1_c0.loc[OOS0:OOS1]), 2)},
        "TSMOM_I1_swapfree_ref": {"full": ann_sharpe(TS_i1_free), "OOS": round(ann_sharpe(TS_i1_free.loc[OOS0:OOS1]), 2)},
    }

    # ---- books (the pre-registered variants) ----
    books = {}
    books["B0_baseline(RH+ETF-TSMOM,equal)"] = combine({"RH": RH, "TSMOM": TS_base}, "equal")
    books["I2_RH_alone"] = vt(RH)
    books["I3_ERC(RH+I1-TSMOM)"] = combine({"RH": RH, "TSMOM": TS_i1_nc}, "risk-parity")
    books["I4_constvol(RH+I1-TSMOM,equal)"] = combine({"RH": RH, "TSMOM": TS_i1_nc}, "equal", book_constvol=True)
    books["I5_improved(RH+I1,ERC,constvol)"] = combine({"RH": RH, "TSMOM": TS_i1_nc}, "risk-parity", book_constvol=True)
    books["I6_bestcase(RH+I1-crypto0,ERC,constvol)"] = combine({"RH": RH, "TSMOM": TS_i1_c0}, "risk-parity", book_constvol=True)

    rep["books"] = {}
    print("\n=== BOOK p(pass) (L fixed on IS) ===")
    for nm, comb in books.items():
        r = book_report(nm, comb); rep["books"][nm] = r
        t = r["ppass"]
        print(f"\n[{nm}]  range {r['range'][0]}..{r['range'][1]}  L*={r['Lstar_IS']}")
        print(f"   full Sh {r['annSh_full']:+.2f} | IS {r['annSh_IS']:+.2f} OOS {r['annSh_OOS']:+.2f} | exk {r['exkurt']} | WF {r['wf']['folds']} (pos {r['wf']['pct_pos']:.0%}, worst {r['wf']['worst']})")
        print(f"   DSR N103 {r['dsr_N103']} / N500 {r['dsr_N500']}")
        print(f"   p(pass) OOS 6mo {t['OOS_6mo']['p']:.3f} CI{t['OOS_6mo']['ci90']} | OOS 12mo {t['OOS_12mo']['p']:.3f} CI{t['OOS_12mo']['ci90']}")

    # ---- verdict logic ----
    clears = []
    for nm, r in rep["books"].items():
        for k in ["OOS_6mo", "OOS_12mo"]:
            lo = r["ppass"][k]["ci90"][0]
            if lo > 0.50 and r["wf"]["pct_pos"] >= 0.6 and r["dsr_N103"] > 0.5:
                clears.append(f"{nm}:{k}")
    rep["verdict"] = {"any_clears_0.50_CI_and_WF_and_DSR": clears,
                      "max_OOS_12mo_point": round(max(r["ppass"]["OOS_12mo"]["p"] for r in rep["books"].values()), 3),
                      "max_OOS_12mo_ci_upper": round(max(r["ppass"]["OOS_12mo"]["ci90"][1] for r in rep["books"].values()), 3),
                      "conclusion": ("AT LEAST ONE principled improvement clears" if clears else
                                     "NO principled improvement clears 0.50 on CI+WF+DSR -> edges structurally sub-threshold")}
    (OUT / "improvement_results.json").write_text(json.dumps(rep, indent=2, default=str))
    print("\n=== VERDICT ===", rep["verdict"]["conclusion"])
    print("clears:", clears or "(none)")
    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
