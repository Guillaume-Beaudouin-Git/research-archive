"""
Monday intraday long sleeve (US100 / NQ) — backtest + stress-test reproductible.

Signal : long à l'open RTH 09:30 ET le lundi, sortie au close 16:00 ET (intraday pur).
Décorrélé de l'ORB. Edge de régime post-2018, confirmé cross-asset 6/6 indices.

Usage:
    python monday_sleeve.py                  # backtest + stress depuis le panel
    python monday_sleeve.py --cross-asset    # + réplication Yahoo (réseau requis)

Dépend de : nq_intraday_panel.parquet (colonnes open0=09:30, c29=10:00,
c359=15:30, c389=16:00, r_rth=open->close). Reconstruit depuis le 1-min si absent.
"""
from __future__ import annotations
import argparse
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

COST_RT = 2e-4          # 2 bps round-trip (CFD US100)
# /!\ Le sleeve trade 1×/semaine (les lundis) -> ~52 obs/an, donc on annualise
# le Sharpe en sqrt(52), PAS sqrt(252). (Erreur initiale corrigee : sqrt(252)
# surevaluait le Sharpe x2.2. Monday reel ~0.60 full / ~0.94 2018-26, sous-1.)
ANN = np.sqrt(52)
PANEL = Path("outputs/nq_intraday_panel.parquet")
RAW = Path("data/raw/NQ_1min_databento_2010-2026.parquet")


# ---------- métriques ----------
def sharpe(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN) if len(x) > 20 and x.std() > 0 else np.nan


def max_dd(x: pd.Series) -> float:
    eq = (1 + pd.Series(x).dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


# ---------- données ----------
def build_panel_from_raw(raw_path: Path) -> pd.DataFrame:
    """Reconstruit le panel intraday depuis le 1-min databento (RTH only)."""
    df = pd.read_parquet(raw_path, columns=["open", "close", "is_rth"])
    df = df[df["is_rth"].values]
    date = df.index.normalize()                  # date UTC == date ET pour RTH
    dc = pd.factorize(date)[0]
    newday = np.r_[True, dc[1:] != dc[:-1]]
    cc = np.arange(len(df)) - np.maximum.accumulate(
        np.where(newday, np.arange(len(df)), 0)
    )
    g = pd.DataFrame(
        {"d": dc, "cc": cc, "o": df["open"].values, "c": df["close"].values}
    )
    full = g.groupby("d")["cc"].max()
    keep = full[full >= 388].index
    g = g[g["d"].isin(keep)]
    at_open = lambda k: g[g["cc"] == k].set_index("d")["o"]
    at_close = lambda k: g[g["cc"] == k].set_index("d")["c"]
    udate = pd.Series(date.values).groupby(dc).first()
    panel = pd.DataFrame(
        {"open0": at_open(0), "c29": at_close(29), "c359": at_close(359),
         "c389": at_close(389)}
    ).dropna()
    panel.index = pd.DatetimeIndex(udate.loc[panel.index].values)
    panel["r_rth"] = panel["c389"] / panel["open0"] - 1
    return panel


def load_panel() -> pd.DataFrame:
    if PANEL.exists():
        return pd.read_parquet(PANEL)
    if RAW.exists():
        p = build_panel_from_raw(RAW)
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        p.to_parquet(PANEL)
        return p
    raise FileNotFoundError("Ni le panel ni le 1-min brut trouvés.")


def mondays(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[panel.index.weekday == 0].copy()


# ---------- backtest & stress ----------
def perf_by_period(mon: pd.DataFrame) -> pd.DataFrame:
    r = mon["r_rth"] - COST_RT
    rows = {}
    for lab, start in [("2010-26", "2010"), ("2018-26", "2018"), ("2022-26", "2022")]:
        s = r[r.index >= start]
        rows[lab] = {
            "Sharpe": sharpe(s), "ann%": 100 * s.mean() * 252,
            "MaxDD%": 100 * max_dd(s), "win%": 100 * (s > 0).mean(),
            "t": s.mean() / s.std() * np.sqrt(len(s)), "n": len(s),
        }
    return pd.DataFrame(rows).T.round(2)


def window_robustness(mon: pd.DataFrame) -> pd.DataFrame:
    wins = {"09:30->16:00": ("open0", "c389"), "10:00->16:00": ("c29", "c389"),
            "09:30->15:30": ("open0", "c359"), "10:00->15:30": ("c29", "c359")}
    out = {}
    for lab, (a, b) in wins.items():
        r = (mon[b] / mon[a] - 1) - COST_RT
        out[lab] = {"SR full": sharpe(r), "SR 2018-26": sharpe(r[r.index >= "2018"])}
    return pd.DataFrame(out).T.round(2)


def cost_sensitivity(mon: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for bp in (1, 2, 3, 5, 8):
        r = mon["r_rth"] - bp / 1e4
        out[f"{bp}bp"] = {"SR full": sharpe(r), "SR 2018-26": sharpe(r[r.index >= "2018"])}
    return pd.DataFrame(out).T.round(2)


def vol_targeted(mon: pd.DataFrame, target: float = 0.11) -> pd.Series:
    r = mon["r_rth"] - COST_RT
    rv = r.rolling(26).std().shift(1) * ANN          # no look-ahead
    pos = (target / rv).clip(upper=3.0)
    return (pos * r).dropna()


def recursive_wf(mon: pd.DataFrame, win: int = 104) -> dict:
    """Kill-switch : trade le lundi seulement si Sharpe trailing>0. Déployable réel."""
    r = (mon["r_rth"] - COST_RT).values
    pnl, took = [], []
    for i in range(len(r)):
        if i < win:
            pnl.append(0.0); continue
        tr = r[i - win:i]
        g = 1.0 if (tr.std() > 0 and tr.mean() / tr.std() > 0) else 0.0
        took.append(g); pnl.append(g * r[i])
    s = pd.Series(pnl, index=mon.index)[win:]
    return {"SR_deployable": sharpe(s), "pct_invested": 100 * np.mean(took),
            "ann%": 100 * s.mean() * 252,
            "SR_always_on": sharpe(pd.Series(r, index=mon.index)[win:])}


def tail_risk(mon: pd.DataFrame) -> dict:
    w = mon["r_rth"].sort_values()
    r = mon["r_rth"] - COST_RT
    vt_scale = 0.11 / (r.std() * ANN)
    return {"worst_day%": 100 * w.min(), "p1%": 100 * w.quantile(.01),
            "p5%": 100 * w.quantile(.05), "skew": w.skew(),
            "worst_voltgt%": 100 * w.min() * vt_scale}


def bootstrap_ci(mon: pd.DataFrame, n: int = 3000, seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for lab, start in [("full", "2010"), ("2018-26", "2018")]:
        r = (mon["r_rth"] - COST_RT)[lambda s: s.index >= start]
        bs = [sharpe(r.sample(len(r), replace=True, random_state=rng.integers(1e9)))
              for _ in range(n)]
        out[lab] = (round(np.percentile(bs, 2.5), 2), round(np.percentile(bs, 97.5), 2))
    return out


# ---------- cross-asset (optionnel, réseau) ----------
def _yahoo(tk: str) -> pd.DataFrame:
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
         f"?period1=1199145600&period2=1780272000&interval=1d")
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    return pd.DataFrame({"o": q["open"], "c": q["close"]},
                        index=pd.to_datetime(d["timestamp"], unit="s")).dropna()


def cross_asset() -> pd.DataFrame:
    tks = {"SPY": "S&P", "QQQ": "Nasdaq", "DIA": "Dow", "IWM": "Russell",
           "EWG": "Germany", "EWJ": "Japan"}
    out = {}
    for tk, nm in tks.items():
        try:
            df = _yahoo(tk); r = df["c"] / df["o"] - 1
            mon = r[r.index.weekday == 0]
            out[nm] = {"Lun full": sharpe(mon),
                       "2008-17": sharpe(mon[mon.index < "2018"]),
                       "2018-26": sharpe(mon[mon.index >= "2018"])}
        except Exception as e:  # noqa
            out[nm] = {"Lun full": np.nan, "2008-17": np.nan, "2018-26": np.nan}
    return pd.DataFrame(out).T.round(2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cross-asset", action="store_true")
    args = ap.parse_args()

    panel = load_panel()
    mon = mondays(panel)
    print(f"\n# Monday sleeve — n={len(mon)} lundis, "
          f"{mon.index.min().date()} -> {mon.index.max().date()}\n")
    print("## Performance par période\n", perf_by_period(mon), "\n")
    print("## Robustesse fenêtre (L26)\n", window_robustness(mon), "\n")
    print("## Sensibilité coût\n", cost_sensitivity(mon), "\n")
    vt = vol_targeted(mon)
    print(f"## Vol-target 11% : SR {sharpe(vt):+.2f}, "
          f"vol réalisée {100*vt.std()*ANN:.1f}%\n")
    print("## Walk-forward récursif (kill-switch)\n", recursive_wf(mon), "\n")
    print("## Risque de queue\n", tail_risk(mon), "\n")
    print("## Bootstrap CI95 Sharpe\n", bootstrap_ci(mon), "\n")
    if args.cross_asset:
        print("## Réplication cross-asset (Yahoo)\n", cross_asset(), "\n")


if __name__ == "__main__":
    main()
