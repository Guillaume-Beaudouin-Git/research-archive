"""
Phase 4 — pre-registered rescue hypotheses (PREREG section 10), each L19-disciplined
(compare Sharpe — scale-invariant — so vol changes can't fake an improvement).

  H1 conditional / long-biased shorts (K2): long_only, short-CL-only, half-risk shorts.
     Report Sharpe AND retained decorrelation (corr to ES, crisis alpha).
  H2 portfolio vol-target ~15% + per-cluster risk budgets vs naive ATR-size baseline.
  H3 breadth: 10-instrument universe + param ensemble {20,40,55}d x {2,3}ATR, constant risk.
  Crypto SHORT-ONLY ablation (bear convexity 2018/2022; avoids double-counting A's longs).
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

from engine import Params, load_universe, simulate, build_costs, load_specs
from metrics import equity_metrics, daily_returns, trade_metrics
import trials

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
EXT = CORE + ["RTY", "SI", "ZN"]
START, END = "2014-01-01", "2026-06-12"
SEYK = Path("<HOME>/Desktop/Algo_claude/data/seykota_trend/daily")

specs = load_specs()
PER_SIDE, ROLL_BP, MULT = build_costs(specs)
DATA = load_universe(EXT)
ES_M = np.log(DATA["ES"]["close"]).resample("ME").last().diff()


def run(p, universe=CORE, data=None):
    data = data or {s: DATA[s] for s in universe}
    cs = {s: PER_SIDE[s] for s in universe}; rb = {s: ROLL_BP[s] for s in universe}
    res = simulate(data, p, 100_000, cs, rb, MULT, start=START, end=END)
    return res, equity_metrics(res["equity"], rf_annual=0.0), daily_returns(res["equity"])


def corr_es(res):
    sm = res["equity"]["equity"].resample("ME").last().pct_change()
    j = pd.concat([sm.rename("s"), ES_M.rename("es")], axis=1, sort=True).dropna()
    j = j[j.index >= "2014-01-01"]
    return float(j["s"].corr(j["es"])), float(j[j["es"] < 0]["s"].mean())


def dir_split(tr):
    out = {}
    for tag, sub in [("2014-2019", tr[tr.exit_date < "2020-01-01"]), ("2020-2026", tr[tr.exit_date >= "2020-01-01"])]:
        out[tag] = dict(long=round(float(sub[sub.direction > 0].pnl_net.sum())),
                        short=round(float(sub[sub.direction < 0].pnl_net.sum())))
    return out


def main():
    summary = {}
    others = [s for s in CORE if s != "CL"]

    print("=== H1 — conditional / long-biased shorts (Sharpe + decorrelation retention) ===")
    h1 = {
        "base_twosided": Params(),
        "H1a_long_only": Params(long_only=True),
        "H1b_short_CL_only": Params(long_only_syms=tuple(others)),
        "H1d_half_risk_short": Params(short_risk_mult=0.5),
        "H1bd_shortCL_half": Params(long_only_syms=tuple(others), short_risk_mult=0.5),
    }
    h1out = {}
    for name, p in h1.items():
        res, em, dr = run(p)
        ce, crisis = corr_es(res)
        h1out[name] = dict(sharpe=round(em["sharpe"], 3), cagr=round(em["cagr"], 3), maxdd=round(em["max_drawdown"], 3),
                           skew=round(em["skew"], 2), corr_es=round(ce, 2), crisis_alpha=round(crisis, 4),
                           short_pnl_split=dir_split(res["trades"]))
        print(f"  {name:20s} Sh={em['sharpe']:5.2f} MDD={em['max_drawdown']:6.1%} skew={em['skew']:5.2f} "
              f"corrES={ce:+.2f} crisis={crisis:+.2%}")
        if name.startswith("H1"):
            trials.log_trial("P4", name, em["sharpe"], em["cagr"], em["max_drawdown"], dsr_count=True, notes="H1 conditional short")
    summary["H1"] = h1out

    print("\n=== H2 — portfolio vol-target 15% + cluster budgets vs naive ATR-size (L19: compare Sharpe) ===")
    def overlay(res, target_vol=0.15, cap=0.45, span=60):
        pos = res["positions"]; syms = list(pos.columns)
        rets = pd.DataFrame({s: DATA[s]["close"].pct_change() for s in syms}).reindex(pos.index)
        sign = np.sign(pos)
        ivol = rets.ewm(span=span).std().shift(1)
        raw = (sign / ivol.replace(0, np.nan)).fillna(0.0)
        clusters = {s: specs[s]["cluster"] for s in syms}
        absr = raw.abs(); tot = absr.sum(axis=1).replace(0, np.nan)
        w = raw.copy()
        for cl in set(clusters.values()):
            cs = [s for s in syms if clusters[s] == cl]
            cl_abs = absr[cs].sum(axis=1)
            over = (cl_abs > cap * tot) & (cl_abs > 0)
            scale = (cap * tot / cl_abs).where(over, 1.0).fillna(1.0)
            w[cs] = w[cs].mul(scale, axis=0)
        book_unsc = (w.shift(1) * rets).sum(axis=1)
        pred = book_unsc.ewm(span=span).std().shift(1)
        sc = (target_vol / np.sqrt(252) / pred).clip(upper=5)
        return (sc * book_unsc).dropna()
    for base_name, p in [("two_sided", Params()), ("long_only", Params(long_only=True))]:
        res, em, dr = run(p)
        ov = overlay(res)
        ov = ov[ov.index >= "2014-01-01"]
        sh_ov = ov.mean() / ov.std() * np.sqrt(252)
        print(f"  base {base_name:10s} Sharpe={em['sharpe']:.2f}  ->  H2 vol-target Sharpe={sh_ov:.2f}  (Δ={sh_ov-em['sharpe']:+.2f})")
        summary[f"H2_{base_name}"] = dict(base=round(em["sharpe"], 3), h2=round(float(sh_ov), 3))
        trials.log_trial("P4", f"H2_voltarget_{base_name}", float(sh_ov), dsr_count=False, notes="H2 re-sizing overlay")

    print("\n=== H3 — breadth (10 instruments) + param ensemble {20,40,55}x{2,3} at constant risk ===")
    for dirname, p_kw in [("two_sided", {}), ("long_only", {"long_only": True})]:
        # 7-inst single-config baseline
        _, em7, _ = run(Params(**p_kw), universe=CORE)
        # 10-inst single config
        _, em10, dr10 = run(Params(**p_kw), universe=EXT)
        ce10, crisis10 = corr_es(run(Params(**p_kw), universe=EXT)[0])
        # 10-inst ensemble
        ens = []
        for bk in (20, 40, 55):
            for st in (2.0, 3.0):
                _, _, dr = run(Params(breakout=bk, atr_stop_mult=st, **p_kw), universe=EXT)
                ens.append(dr.rename(f"bk{bk}_st{st}"))
                trials.log_trial("P4", f"H3_ens_{dirname}_bk{bk}_st{st}", dr.mean() / dr.std() * np.sqrt(252),
                                 dsr_count=True, notes="H3 ensemble member")
        E = pd.concat(ens, axis=1, sort=True).dropna()
        ens_ret = E.mean(axis=1)
        sh_ens = ens_ret.mean() / ens_ret.std() * np.sqrt(252)
        print(f"  {dirname:10s}: 7-inst Sh={em7['sharpe']:.2f} | 10-inst Sh={em10['sharpe']:.2f} (corrES {ce10:+.2f}) | "
              f"10-inst ENSEMBLE Sh={sh_ens:.2f}")
        summary[f"H3_{dirname}"] = dict(inst7=round(em7["sharpe"], 3), inst10=round(em10["sharpe"], 3),
                                        ensemble=round(float(sh_ens), 3), corr_es_10=round(ce10, 2))

    print("\n=== Crypto SHORT-ONLY ablation (bear convexity; separate from core) ===")
    cdata = {s: pd.read_parquet(SEYK / f"{s}.parquet") for s in ["BTC", "ETH"]}
    cs = {s: 0.0010 for s in cdata}; rb = {s: 0.0 for s in cdata}
    res_c = simulate(cdata, Params(short_only=True), 100_000, cs, rb, {}, start="2017-01-01", end=END)
    em_c = equity_metrics(res_c["equity"], rf_annual=0.0)
    tr_c = res_c["trades"]
    yearly = res_c["equity"]["equity"].resample("YE").last().pct_change()
    print(f"  crypto short-only: Sharpe={em_c['sharpe']:.2f} CAGR={em_c['cagr']:.1%} MDD={em_c['max_drawdown']:.1%} "
          f"trades={len(tr_c)}")
    print(f"  yearly: " + "  ".join(f"{i.year}:{v:+.0%}" for i, v in yearly.dropna().items()))
    summary["crypto_short"] = dict(sharpe=round(em_c["sharpe"], 3), cagr=round(em_c["cagr"], 3),
                                   maxdd=round(em_c["max_drawdown"], 3))
    trials.log_trial("P4", "crypto_short_only", em_c["sharpe"], dsr_count=False, notes="bear-convexity ablation")

    json.dump(summary, open(RESULTS / "p4_summary.json", "w"), indent=2, default=str)
    print("\nsaved results/p4_summary.json")


if __name__ == "__main__":
    main()
