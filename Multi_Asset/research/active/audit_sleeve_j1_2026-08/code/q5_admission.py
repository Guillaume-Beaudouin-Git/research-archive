"""Q5 — is J1's value RETURN or DIVERSIFICATION?

rho with the overnight sleeve (the book's engine), then marginal effect at ERC weight
in Delta p(pass) / Delta duration against the real FTMO barriers, with the mandatory
autocorrelation-matched placebo (circular shift): a strictly zero-mean but persistent
series is known to score Delta p = +0.1495 here, so any Delta p below the placebo
distribution is noise, not admission evidence.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
CR = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CR)

from j1_lib import load_panels, sleeve_returns, sharpe, RT_BPS_USDJPY_ALLIN  # noqa: E402
from Portfolio.admission.barrier import BarrierConfig, pass_probability_delta, simulate_campaign  # noqa: E402
import engine as E  # noqa: E402

SCRATCH = Path("<SCRATCH>"
               "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/j1cache")

px, rets, sL, sS, mu, rt = load_panels()
_, j1, w_j1 = sleeve_returns(px, rets, sL, sS, mu, "long", RT_BPS_USDJPY_ALLIN)

# ---- gold sleeve (same engine block) and overnight sleeve (M5 sessions)
WT, ON = E.build_signals()
gold = (WT["XAUUSD"] * rets["XAUUSD"]).fillna(0.0)
gold = gold - (WT["XAUUSD"].diff().abs() * (1.98 / 2 / 1e4)).fillna(0.0)
bps_g = np.where(WT["XAUUSD"] > 0, sL["XAUUSD"], np.where(WT["XAUUSD"] < 0, sS["XAUUSD"], 0.0))
gold = gold + (WT["XAUUSD"].abs() * pd.Series(bps_g, index=WT.index) / 1e4 * mu["XAUUSD"]).fillna(0.0)

m5 = pd.read_parquet(Path(CR).parents[1] / "cache" / "sim_m5_repaired.parquet").ffill()
mins = m5.index.hour * 60 + m5.index.minute


def _px_at(col, minute):
    s = m5[col]
    sel = s[mins >= minute]
    return sel.groupby(sel.index.normalize()).first()


on_days = set(ON[ON > 0].index.normalize())
us_in, us_out = _px_at("US100", 22 * 60 + 5), _px_at("US100", 15 * 60 + 30)
ge_in, ge_out = _px_at("GER40", 17 * 60 + 35), _px_at("GER40", 9 * 60)
days = us_in.index
nxt = pd.Series(days, index=days).shift(-1)
rows = {}
for d0 in days:
    if d0 not in on_days:
        continue
    d1 = nxt.get(d0)
    if pd.isna(d1):
        continue
    tot = 0.0
    for a, b, swp, rtb in [(us_in, us_out, -2.126, 2.2), (ge_in, ge_out, -1.564, 2.2)]:
        if d0 in a.index and d1 in b.index and np.isfinite(a[d0]) and np.isfinite(b[d1]):
            tot += 0.6 * (b[d1] / a[d0] - 1.0) - 0.6 * rtb / 1e4 + 0.6 * swp / 1e4
    rows[d1] = rows.get(d1, 0.0) + tot
overnight = pd.Series(rows).reindex(WT.index).fillna(0.0).sort_index()

BOOK = pd.DataFrame({"overnight": overnight, "gold": gold}).loc["2013-10-01":]
J1 = j1.reindex(BOOK.index).fillna(0.0)
BOOK, J1 = BOOK.dropna(), J1.loc[BOOK.dropna().index]

print("### Q5a — sleeve stand-alone stats and correlations (research scale, net)")
allr = BOOK.assign(j1=J1)
for c in allr.columns:
    s = allr[c]
    print(f"  {c:<10} SR {sharpe(s):+.3f}  vol {s.std()*np.sqrt(252)*100:5.2f}%/yr  "
          f"ann {s.mean()*252*100:+.2f}%/yr  flat days {(s == 0).mean()*100:5.1f}%")
print("\n  correlation matrix:")
print(allr.corr().round(3).to_string())
ov = allr["overnight"]
both = ((J1 != 0) & (ov != 0)).mean()
print(f"\n  rho(J1, overnight) = {J1.corr(ov):+.4f}   "
      f"rho on days both active = {J1[(J1!=0)&(ov!=0)].corr(ov[(J1!=0)&(ov!=0)]):+.4f}")
print(f"  J1 active on {(J1!=0).mean()*100:.1f}% of days, overnight on {(ov!=0).mean()*100:.1f}%, "
      f"both {both*100:.1f}%")
print(f"  J1 active while the REST of the book is flat: "
      f"{((J1!=0) & (BOOK.sum(axis=1)==0)).mean()*100:.1f}% of days")

# ---------------------------------------------------------------- barriers
cfg = BarrierConfig(horizon_days=182)
SCALE = 6.0     # book re-levered so the incumbent's p(pass) sits in the live band
base = pass_probability_delta(BOOK, None, cfg=cfg, n_paths=4000, seed=7, scale=SCALE)
print(f"\n### Q5b — barriers: daily -5%, STATIC floor -10%, horizon 182d, scale x{SCALE}")
print(f"  book alone (overnight+gold, ERC): p(pass) {base['p_pass_book']*100:.2f} %  "
      f"median {base['median_days_book']:.0f} d")

res = pass_probability_delta(BOOK, J1.rename("j1"), cfg=cfg, n_paths=4000, seed=7, scale=SCALE)
print(f"  + J1                            : p(pass) {res['p_pass_combined']*100:.2f} %  "
      f"median {res['median_days_combined']:.0f} d")
print(f"  -> delta_p = {res['delta_p_pass']*100:+.2f} pt   "
      f"delta_median_days = {res['delta_median_days']:+.1f} d")
print(f"     fail split book:     floor {res['p_fail_floor_book']*100:.1f} % / "
      f"daily {res['p_fail_daily_book']*100:.1f} %")
print(f"     fail split combined: floor {res['p_fail_floor_combined']*100:.1f} % / "
      f"daily {res['p_fail_daily_combined']*100:.1f} %")

# ------------------------------------------------- autocorrelation-matched placebo
print("\n### Q5c — PLACEBO: circular shifts of J1 (identical marginal AND autocorrelation)")
rng = np.random.default_rng(11)
n = len(J1)
deltas, dd = [], []
for k in rng.choice(np.arange(60, n - 60), size=60, replace=False):
    pl = pd.Series(np.roll(J1.values, int(k)), index=J1.index, name="j1")
    r = pass_probability_delta(BOOK, pl, cfg=cfg, n_paths=1200, seed=7, scale=SCALE)
    deltas.append(r["delta_p_pass"])
    dd.append(r["delta_median_days"])
deltas, dd = np.asarray(deltas), np.asarray(dd)
pct = (deltas < res["delta_p_pass"]).mean() * 100
print(f"  placebo delta_p : mean {deltas.mean()*100:+.2f} pt  "
      f"p5 {np.percentile(deltas,5)*100:+.2f}  p50 {np.percentile(deltas,50)*100:+.2f}  "
      f"p95 {np.percentile(deltas,95)*100:+.2f}  (N=60 shifts)")
print(f"  placebo delta_days: mean {np.nanmean(dd):+.1f} d  "
      f"p5 {np.nanpercentile(dd,5):+.1f}  p95 {np.nanpercentile(dd,95):+.1f}")
print(f"  REAL J1 delta_p = {res['delta_p_pass']*100:+.2f} pt  ->  "
      f"percentile {pct:.0f} of the placebo distribution")
print(f"  VERDICT: {'ABOVE p95 - real diversification' if pct >= 95 else 'INDISTINGUISHABLE from a persistence placebo'}")

# zero-mean persistent control (the known +0.1495 failure mode)
zm = (J1 - J1.mean()).rename("j1")
rz = pass_probability_delta(BOOK, zm, cfg=cfg, n_paths=4000, seed=7, scale=SCALE)
print(f"  strictly zero-mean J1 (edge removed, persistence kept): "
      f"delta_p = {rz['delta_p_pass']*100:+.2f} pt, delta_days {rz['delta_median_days']:+.1f}")
