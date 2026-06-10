"""Trial I-1 stages (b)(c)(d): gross effect, dose-response, L11 cost gate, backtest + kills.

Spec frozen in ../preregistration.md. Fill convention: signal at UTC day close ->
fill at next 1h open == next UTC daily open (identical at day boundaries); funding
accrued over (entry, exit] (same-instant resolves to NEXT, L26).
Short P&L per event, bps: -(ln open[T+4] - ln open[T-6])*1e4 + funding - fees - slip.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats as sst

import lib_data as ld

TAKER_BPS = 5.0
SLIP_BPS_MAJ = 1.0
SLIP_BPS_ALT = 4.0
N_PLACEBO = 1000
RNG = np.random.default_rng(20260610)


def hac_t(x: np.ndarray, lags: int = 6) -> tuple[float, float]:
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for l in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - l / (lags + 1)) * (e[:-l] @ e[l:]) / n
    return x.mean(), x.mean() / np.sqrt(max(s, 1e-18) / n)


def dsr(x: np.ndarray, n_trials: int) -> float:
    x = np.asarray(x, float)
    t = len(x)
    sr = x.mean() / (x.std(ddof=1) + 1e-18)
    sk = float(sst.skew(x))
    ku = float(sst.kurtosis(x, fisher=False))
    em = 0.5772156649
    sr0 = (((1 - em) * sst.norm.ppf(1 - 1 / n_trials)
            + em * sst.norm.ppf(1 - 1 / (n_trials * np.e))) * np.sqrt(1 / (t - 1)))
    denom = np.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr**2, 1e-12) / (t - 1))
    return float(sst.norm.cdf((sr - sr0) / denom))


class Book:
    """Per-symbol O(1) lookups: daily open by day, funding cumsum, vol terciles, floor."""

    def __init__(self, sym: str):
        d = ld.rest_daily_klines(sym)
        f = ld.funding_history(sym)
        self.open_by_day = pd.Series(d["open"].values, index=d.index.normalize())
        self.open_by_day = self.open_by_day[~self.open_by_day.index.duplicated()]
        self.fcum = f["rate"].cumsum()
        ret = np.log(d["close"]).diff()
        self.v30 = ret.rolling(30).std()
        self.terc = self.v30.rank(pct=True)
        self.terc.index = d.index.normalize()
        self.med30 = d["quote_volume"].rolling(30, min_periods=20).median()
        self.med30.index = d.index.normalize()

    def funding_sum(self, t0: pd.Timestamp, t1: pd.Timestamp) -> float:
        i0 = self.fcum.index.searchsorted(t0, side="right")
        i1 = self.fcum.index.searchsorted(t1, side="right")
        a = self.fcum.iloc[i0 - 1] if i0 > 0 else 0.0
        b = self.fcum.iloc[i1 - 1] if i1 > 0 else 0.0
        return float(b - a)

    def pnl(self, day: pd.Timestamp, slip_bps: float, slip_mult: float = 1.0) -> dict | None:
        e_day, x_day = day - pd.Timedelta(days=6), day + pd.Timedelta(days=4)
        p_in = self.open_by_day.get(e_day)
        p_out = self.open_by_day.get(x_day)
        if p_in is None or p_out is None or not np.isfinite(p_in) or not np.isfinite(p_out) or p_in <= 0:
            return None
        gross = -(np.log(p_out) - np.log(p_in)) * 1e4
        funding = self.funding_sum(e_day, x_day) * 1e4
        fees = 2 * TAKER_BPS + 2 * slip_bps * slip_mult
        return {"gross_bps": gross, "funding_bps": funding, "fees_bps": fees,
                "net_bps": gross + funding - fees}


def main() -> None:
    db = pd.read_parquet(ld.CACHE / "i1_events.parquet")
    db["day"] = pd.to_datetime(db["day"], utc=True)
    print(f"events in DB: {len(db)}")

    books: dict[str, Book] = {}
    rows = []
    for _, r in db.iterrows():
        sym = r["symbol"]
        if sym not in books:
            books[sym] = Book(sym)
        slip = SLIP_BPS_MAJ if sym in ("BTCUSDT", "ETHUSDT") else SLIP_BPS_ALT
        res = books[sym].pnl(r["day"], slip)
        if res is None:
            continue
        rows.append({**r.to_dict(), **res, "slip_bps_used": slip})
    ev = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    ev.to_parquet(ld.CACHE / "i1_event_pnl.parquet")
    print(f"events with full price+funding coverage: {len(ev)}")

    out: dict = {"n_events": int(len(ev)), "n_symbols": int(ev["symbol"].nunique()),
                 "span": [str(ev["day"].min().date()), str(ev["day"].max().date())]}

    g_mean, g_t = hac_t(ev["gross_bps"].values)
    rho, rho_p = sst.spearmanr(ev["size_pct"], ev["gross_bps"])
    ev["decile"] = pd.qcut(ev["size_pct"], 10, labels=False, duplicates="drop")
    dec = ev.groupby("decile").agg(size_med=("size_pct", "median"),
                                   gross_mean=("gross_bps", "mean"),
                                   n=("gross_bps", "size")).reset_index()
    out["stage_b"] = {"gross_mean_bps": g_mean, "gross_hac_t": g_t,
                      "spearman_size_gross": float(rho), "spearman_p": float(rho_p),
                      "deciles": dec.to_dict("records")}
    print(f"(b) gross {g_mean:+.1f} bps t={g_t:.2f} | dose-response rho={rho:.3f} p={rho_p:.3f}")

    cost = ev["fees_bps"] - ev["funding_bps"]
    stress = ev["fees_bps"] + 2 * ev["slip_bps_used"] - ev["funding_bps"]
    gate = {"median_cost_bps": float(cost.median()),
            "median_gross_bps": float(ev["gross_bps"].median()),
            "median_funding_bps": float(ev["funding_bps"].median()),
            "median_fees_slip_bps": float(ev["fees_bps"].median()),
            "share_funding_negative_for_short": float((ev["funding_bps"] < 0).mean()),
            "stress2x_slip_median_cost_bps": float(stress.median())}
    gate["DEAD_at_gate"] = bool(gate["median_cost_bps"] >= gate["median_gross_bps"])
    out["stage_c_gate"] = gate
    print(f"(c) median cost {gate['median_cost_bps']:.1f} vs median gross {gate['median_gross_bps']:.1f}"
          f" -> {'DEAD' if gate['DEAD_at_gate'] else 'PASS'}")

    if not gate["DEAD_at_gate"]:
        net = ev["net_bps"].values
        n_mean, n_t = hac_t(net)

        # Placebo pools: ±15d exclusion as registered; monthly-cliff tokens have EMPTY
        # ±15d pools (mechanical), forced adaptation -> ±10d (window disjointness:
        # windows span T-6..T+4); still empty -> event excluded from the K2 subset.
        elig: dict[str, tuple[pd.DatetimeIndex, np.ndarray]] = {}
        for sym in ev["symbol"].unique():
            b = books[sym]
            ok = (b.med30 >= 20e6) & b.terc.notna()
            days_ok = b.med30.index[ok.values]
            real = list(ev.loc[ev["symbol"] == sym, "day"])
            for dist in (15, 10):
                mask = np.ones(len(days_ok), bool)
                for rd in real:
                    mask &= np.abs((days_ok - rd).days) > dist
                if mask.any():
                    break
            elig[sym] = (days_ok[mask], b.terc.reindex(days_ok[mask]).values)
        ev["terc"] = [books[s].terc.asof(t) for s, t in zip(ev["symbol"], ev["day"])]
        ev["k2_included"] = [len(elig[s][0]) > 0 for s in ev["symbol"]]
        inc = ev[ev["k2_included"]]
        n_excl = int((~ev["k2_included"]).sum())

        placebo_means = []
        for _ in range(N_PLACEBO):
            vals = []
            for sym, want, slip in zip(inc["symbol"], inc["terc"], inc["slip_bps_used"]):
                pool, tt = elig[sym]
                cand = pool[np.abs(tt - want) < 1 / 3] if np.isfinite(want) else pool
                if len(cand) == 0:
                    cand = pool
                day = cand[RNG.integers(len(cand))]
                res = books[sym].pnl(pd.Timestamp(day), slip)
                if res:
                    vals.append(res["net_bps"])
            placebo_means.append(float(np.mean(vals)))
        p95 = float(np.percentile(placebo_means, 95))
        real_mean_k2 = float(inc["net_bps"].mean())
        np.save(ld.CACHE / "i1_placebo_means.npy", np.array(placebo_means))

        sub24 = ev.loc[ev["day"] >= pd.Timestamp("2024-01-01", tz="UTC"), "net_bps"]
        tot = ev["net_bps"].sum()
        tok_share = float((ev.groupby("protocol")["net_bps"].sum() / tot).max()) if tot > 0 else np.nan
        q_share = float((ev.groupby(ev["day"].dt.to_period("Q"))["net_bps"].sum() / tot).max()) if tot > 0 else np.nan
        d_val = dsr(net, n_trials=117)
        out["stage_d"] = {"net_mean_bps": n_mean, "net_hac_t": n_t, "K1_fail": bool(n_t < 2.0),
                          "real_mean": real_mean_k2, "placebo_p95": p95,
                          "k2_n_included": int(len(inc)), "k2_n_excluded": n_excl,
                          "K2_fail": bool(real_mean_k2 <= p95),
                          "K3_fail": bool(rho <= 0 or rho_p >= 0.10),
                          "sub2024_mean": float(sub24.mean()) if len(sub24) else np.nan,
                          "sub2024_n": int(len(sub24)),
                          "K4_fail": bool(sub24.mean() <= 0) if len(sub24) else True,
                          "max_token_share": tok_share, "max_quarter_share": q_share,
                          "K5_fail": bool(np.nanmax([tok_share, q_share]) > 0.60) if tot > 0 else True,
                          "dsr_at_117": d_val, "K6_fail": bool(d_val <= 0)}
        print(f"(d) net {n_mean:+.1f} bps t={n_t:.2f} | placebo p95 {p95:+.1f} | DSR {d_val:.3f}")

    cc = ev.groupby("insider")["gross_bps"].agg(["mean", "count"])
    out["category_contrast_gross"] = {str(k): {"mean_bps": float(v["mean"]), "n": int(v["count"])}
                                      for k, v in cc.iterrows()}

    prof = {}
    for off in range(-30, 31):
        vals = []
        for sym, day in zip(ev["symbol"], ev["day"]):
            b = books[sym]
            a = b.open_by_day.get(day + pd.Timedelta(days=off))
            c = b.open_by_day.get(day + pd.Timedelta(days=off + 1))
            if a and c and a > 0:
                vals.append(np.log(c / a) * 1e4)
        prof[off] = float(np.mean(vals)) if vals else np.nan
    out["event_time_profile_descriptive"] = prof

    json.dump(out, open(ld.ROOT / "i1_results.json", "w"), indent=1, default=float)
    print("i1_results.json written")


if __name__ == "__main__":
    main()
