#!/usr/bin/env python3
"""
overnight_harvester.py
======================
Reference implementation of the MA200-gated overnight equity-drift harvester
and its FTMO 2-step first-passage evaluation.

Strategy (one sentence)
-----------------------
Each trading day, IF the index closed above its 200-day simple moving average,
hold a long position from the cash CLOSE to the next cash OPEN (overnight only),
sized as a constant fraction `L` of equity; otherwise stay flat. No time limit.

Economic basis: the overnight (close-to-open) equity risk premium — the well
documented tendency for equity index returns to accrue overnight rather than
intraday — harvested only while a slow trend filter says "risk-on".

Reproducibility
---------------
    python overnight_harvester.py --data <NQ_1min.parquet> --out ./out
Produces the same numbers as the dossier: nightly stats, equity-curve metrics,
the FTMO 2-step first-passage table, an in-sample/out-of-sample split, and the
by-year regime table.

NO LOOK-AHEAD. The gate decision for night t uses only closes up to and including
day t (the 200d SMA is computed on close[:t+1]); the position is opened at
close(t) and the realized return open(t+1)/close(t)-1 is the consequence of that
decision, not an input to it.

Author: FTMO research arc.  Data: Databento NQ 1-min, RTH cash, roll days excluded.
"""
from __future__ import annotations
import argparse, json, os
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------- #
# Configuration
# ----------------------------------------------------------------------------- #
@dataclass
class Config:
    data_path: str
    out_dir: str = "./out"
    tz: str = "US/Eastern"          # cash-session timezone for daily O/C boundaries
    ma_window: int = 200            # trend gate: SMA of daily close
    cost_per_night: float = 0.0002  # 2 bps round-trip (spread+commission). SWAP NOT INCLUDED.
    init_equity: float = 10_000.0
    p1_target: float = 1.10         # FTMO Phase 1: +10%
    p2_target: float = 1.05         # FTMO Phase 2: +5%
    daily_loss_limit: float = 0.05  # 5% max daily loss
    total_floor: float = 9_000.0    # static $9k floor (10% max loss from initial)
    leverages: tuple = (0.5, 0.75, 1.0)
    oos_split_year: int = 2019      # train < 2019 ; test >= 2019 (incl. COVID + 2022 bear)
    weeks: tuple = tuple(range(1, 11))
    months: tuple = (3, 6, 9, 12, 18, 24, 30, 36, 42, 48, 54, 60)


# ----------------------------------------------------------------------------- #
# 1. Data: clean daily Open/Close from intraday RTH non-roll bars
# ----------------------------------------------------------------------------- #
def load_daily_oc(cfg: Config) -> pd.DataFrame:
    """Return DataFrame indexed by session date with columns O (first RTH open)
    and C (last RTH close). Uses only regular-trading-hours bars and excludes
    contract-roll days (both flagged in the Databento export)."""
    df = pd.read_parquet(cfg.data_path, columns=["open", "close", "is_rth", "is_roll_day"])
    df = df[df["is_rth"] & ~df["is_roll_day"]]
    df.index = df.index.tz_convert(cfg.tz)
    day = df.index.normalize()
    g = df.groupby(day)
    daily = pd.DataFrame({"O": g["open"].first(), "C": g["close"].last()}).dropna()
    return daily


# ----------------------------------------------------------------------------- #
# 2. Signal: MA200-gated overnight return series (causal)
# ----------------------------------------------------------------------------- #
def build_signal(daily: pd.DataFrame, cfg: Config):
    """Return a dict of aligned arrays for the gated overnight strategy.
    All gate information is known at close(t); ov[t] = open(t+1)/close(t)-1."""
    C = daily["C"].to_numpy()
    O = daily["O"].to_numpy()
    dates = daily.index
    ov = O[1:] / C[:-1] - 1.0                                   # t = 0 .. n-2
    ma = pd.Series(C).rolling(cfg.ma_window).mean().to_numpy()  # SMA of close <= t
    gate_t = (C > ma)[:-1]                                      # decision at close t
    valid = ~np.isnan(ma[:-1])
    traded = valid & gate_t
    r_net = np.where(traded, ov - cfg.cost_per_night, 0.0)
    r_gross = np.where(traded, ov, 0.0)
    return dict(ov=ov, r_net=r_net, r_gross=r_gross, traded=traded, valid=valid,
                close_dates=dates[:-1], settle_dates=dates[1:])


# ----------------------------------------------------------------------------- #
# 3. Descriptive metrics
# ----------------------------------------------------------------------------- #
def _moments(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    m, s = x.mean(), x.std(ddof=1)
    skew = ((x - m) ** 3).mean() / s ** 3 if s > 0 else np.nan
    return dict(n=int(len(x)), mean_bps=float(m * 1e4), std_bps=float(s * 1e4),
                sharpe_ann=float(m / s * np.sqrt(252)) if s > 0 else np.nan,
                skew=float(skew), hit=float((x > 0).mean()))


def nightly_stats(sig: dict) -> dict:
    t = sig["traded"]
    return {"traded_net": _moments(sig["r_net"][t]),
            "traded_gross": _moments(sig["r_gross"][t]),
            "all_valid_net": _moments(sig["r_net"][sig["valid"]])}


def curve_metrics(r: np.ndarray, L: float) -> dict:
    eq = np.cumprod(1.0 + L * r)
    yrs = len(r) / 252.0
    cagr = eq[-1] ** (1 / yrs) - 1
    dd = eq / np.maximum.accumulate(eq) - 1.0
    mdd = dd.min()
    ds = L * r
    sharpe = ds.mean() / ds.std(ddof=1) * np.sqrt(252)
    return dict(L=L, total_return=float(eq[-1] - 1), CAGR=float(cagr),
                maxDD=float(mdd), Calmar=float(cagr / abs(mdd)), Sharpe_ann=float(sharpe))


# ----------------------------------------------------------------------------- #
# 4. FTMO 2-step first-passage simulation (contiguous real path)
# ----------------------------------------------------------------------------- #
def _run_phase(r, start, target_mult, cfg, L):
    eq, tgt, i, N = cfg.init_equity, cfg.init_equity * target_mult, start, len(r)
    while i < N:
        chg = L * r[i]
        if chg <= -cfg.daily_loss_limit:          # daily-loss breach (overnight gap)
            return i, "bust"
        eq *= (1.0 + chg)
        if eq < cfg.total_floor:                  # static total-loss floor
            return i, "bust"
        if eq >= tgt:
            return i, "pass"
        i += 1
    return N - 1, "run"                            # ran out of data (censored)


def _run_funded(r, start, cfg, L):
    e1, s1 = _run_phase(r, start, cfg.p1_target, cfg, L)
    if s1 != "pass":
        return dict(out=s1, d1=e1 - start + 1, d2=0, dtot=e1 - start + 1)
    d1 = e1 - start + 1
    e2, s2 = _run_phase(r, e1 + 1, cfg.p2_target, cfg, L)
    d2 = max(e2 - e1, 0)
    out = "funded" if s2 == "pass" else ("bust" if s2 == "bust" else "run")
    return dict(out=out, d1=d1, d2=d2, dtot=d1 + d2, reached_p2=(d2 > 0))


def ftmo_first_passage(r: np.ndarray, cfg: Config, start_lo=0, start_hi=None) -> dict:
    """Rolling-start contiguous first-passage. For each start date, chain Phase 1
    (+10%) then Phase 2 (+5%) on the real forward path under the daily/total caps.
    Returns p(funded), bust, running, conditional phase rates, time-to-funded
    quantiles, and cumulative-incidence curves by week and month."""
    N = len(r)
    start_hi = (N - 5) if start_hi is None else start_hi
    starts = np.arange(start_lo, start_hi)
    recs = [_run_funded(r, s, cfg, L=cfg._L) for s in starts]
    out = np.array([x["out"] for x in recs])
    dtot = np.array([x["dtot"] for x in recs])
    reached_p2 = np.array([x.get("reached_p2", False) for x in recs])
    fwd = (N - 1) - starts
    funded, bust, run = out == "funded", out == "bust", out == "run"
    term = funded | bust

    def cum_inc(Hdays):
        elig = term | (fwd >= Hdays)
        return float((funded & (dtot <= Hdays) & elig).sum() / max(elig.sum(), 1))

    ttf = dtot[funded]
    q = lambda a, p: float(np.percentile(a, p)) if len(a) else float("nan")
    return dict(
        n_starts=int(len(out)),
        p_funded_total=float(funded.mean()),
        p_funded_terminal=float(funded.sum() / max(term.sum(), 1)),
        p_P1=float(reached_p2.mean()),
        p_P2_given_P1=float(funded.sum() / max(reached_p2.sum(), 1)),
        pct_bust=float(bust.mean()), pct_running=float(run.mean()),
        ttf_years=dict(p25=q(ttf, 25) / 252, median=q(ttf, 50) / 252, p75=q(ttf, 75) / 252),
        by_week={w: round(cum_inc(w * 5), 4) for w in cfg.weeks},
        by_month={m: round(cum_inc(m * 21), 4) for m in cfg.months},
    )


# ----------------------------------------------------------------------------- #
# 5. Regime (by-year) and out-of-sample split
# ----------------------------------------------------------------------------- #
def regime_by_year(sig: dict, daily: pd.DataFrame) -> pd.DataFrame:
    sd = sig["settle_dates"]; r = sig["r_net"]; t = sig["traded"]; v = sig["valid"]
    C = daily["C"]; rows = []
    for y in sorted(set(sd.year)):
        m = (sd.year == y); tn = t & m
        if tn.sum() == 0:
            continue
        rn = r[tn]
        cy = C[C.index.year == y]
        bh = float(cy.iloc[-1] / cy.iloc[0] - 1) if len(cy) > 1 else np.nan
        rows.append(dict(year=int(y), traded_nights=int(tn.sum()),
                         gate_on_frac=float(tn.sum() / max((v & m).sum(), 1)),
                         mean_bps=float(rn.mean() * 1e4),
                         total_net_pct=float((np.prod(1 + rn) - 1) * 100),
                         worst_night_pct=float(rn.min() * 100),
                         buyhold_idx_pct=round(bh * 100, 2)))
    return pd.DataFrame(rows)


def oos_split(sig: dict, cfg: Config) -> dict:
    """In-sample (< split year) vs out-of-sample (>= split year) nightly edge."""
    sd = sig["settle_dates"]; t = sig["traded"]; r = sig["r_net"]
    res = {}
    for label, mask in [("in_sample", sd.year < cfg.oos_split_year),
                        ("out_of_sample", sd.year >= cfg.oos_split_year)]:
        sel = t & mask
        res[label] = dict(period=f"{'<' if label=='in_sample' else '>='}{cfg.oos_split_year}",
                          **_moments(r[sel]))
    return res


# ----------------------------------------------------------------------------- #
# 6. Driver
# ----------------------------------------------------------------------------- #
def run(cfg: Config) -> dict:
    os.makedirs(cfg.out_dir, exist_ok=True)
    daily = load_daily_oc(cfg)
    sig = build_signal(daily, cfg)
    out = dict(
        period=f"{daily.index[0].date()} .. {daily.index[-1].date()}",
        n_days=int(len(daily)), cost_bps=cfg.cost_per_night * 1e4, ma_window=cfg.ma_window,
        nightly=nightly_stats(sig),
        curves={f"{L}x": curve_metrics(sig["r_net"][sig["valid"]], L) for L in cfg.leverages},
        oos=oos_split(sig, cfg),
        ftmo={},
    )
    for L in cfg.leverages:
        cfg._L = L
        out["ftmo"][f"{L}x"] = ftmo_first_passage(sig["r_net"], cfg)
    reg = regime_by_year(sig, daily)
    reg.to_csv(os.path.join(cfg.out_dir, "regime_by_year.csv"), index=False)
    with open(os.path.join(cfg.out_dir, "metrics_summary.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out


def _print(out, cfg):
    print(f"\nNQ overnight harvester | {out['period']} | {out['n_days']} days | "
          f"cost {out['cost_bps']:.0f}bps/night | MA{out['ma_window']}")
    n = out["nightly"]["traded_net"]; g = out["nightly"]["traded_gross"]
    print(f"\nNightly traded  net : mean {n['mean_bps']:+.2f}bps  Sharpe {n['sharpe_ann']:.2f}  "
          f"skew {n['skew']:+.2f}  hit {n['hit']*100:.1f}%  (n={n['n']})")
    print(f"Nightly traded gross: mean {g['mean_bps']:+.2f}bps  Sharpe {g['sharpe_ann']:.2f}")
    print("\nOOS split (nightly net, traded):")
    for k, v in out["oos"].items():
        print(f"  {k:14s} {v['period']:>6}  mean {v['mean_bps']:+.2f}bps  Sharpe {v['sharpe_ann']:.2f}  "
              f"skew {v['skew']:+.2f}  n={v['n']}")
    print("\nEquity curve:")
    for L in cfg.leverages:
        c = out["curves"][f"{L}x"]
        print(f"  {L}x  CAGR {c['CAGR']*100:5.2f}%  maxDD {c['maxDD']*100:6.2f}%  "
              f"Calmar {c['Calmar']:.2f}  Sharpe {c['Sharpe_ann']:.2f}")
    print("\nFTMO 2-step first-passage:")
    for L in cfg.leverages:
        R = out["ftmo"][f"{L}x"]
        print(f"  {L}x  p(funded) total {R['p_funded_total']*100:5.1f}%  bust {R['pct_bust']*100:4.1f}%  "
              f"run {R['pct_running']*100:4.1f}%  median {R['ttf_years']['median']:.2f}y  "
              f"p(P1) {R['p_P1']*100:.0f}%  p(P2|P1) {R['p_P2_given_P1']*100:.0f}%")
        print(f"       p(pass) 4w={R['by_week'][4]*100:.1f}%  12mo={R['by_month'][12]*100:.1f}%  "
              f"24mo={R['by_month'][24]*100:.1f}%  48mo={R['by_month'][48]*100:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="path to NQ 1-min parquet")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--ma", type=int, default=200)
    ap.add_argument("--cost-bps", type=float, default=2.0)
    a = ap.parse_args()
    cfg = Config(data_path=a.data, out_dir=a.out, ma_window=a.ma,
                 cost_per_night=a.cost_bps / 1e4)
    _print(run(cfg), cfg)
