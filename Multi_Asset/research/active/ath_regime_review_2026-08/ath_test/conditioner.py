"""Build the ATH conditioner (C1 expanding, C2 52-week-high ratio) and the raw
overnight leg returns, strictly at T-1, from the engine's own ledger.

Nothing is written outside this folder; the cleanroom engine and the 2026-07 study are
imported read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

sys.path.insert(0, str(OVERLAY))
import build_book as B  # noqa: E402

E = B.E

LEG_IDX = {"US100": 2, "GER40": 3}
BUCKET_EDGES = [0.0, 0.01, 0.03, 0.07, np.inf]
BUCKET_NAMES = ["B0_at_high", "B1_1to3", "B2_3to7", "B3_far"]


# ------------------------------------------------------------------ price series
def daily_closes() -> pd.DataFrame:
    """Audited daily closes for US100/GER40, from panel_px (starts 2000-01)."""
    px = pd.read_parquet(REPO / "data/ftmo_portfolio/cache/panel_px.parquet")
    return px[["US100", "GER40"]].dropna(how="all").sort_index()


def m5_daily_last(M) -> pd.DataFrame:
    """Last M5 bar of each engine day, for the cross-check against panel_px."""
    rows = {}
    for i in range(M["n"]):
        px_day, _ = M["days"][i]
        rows[M["dates"][i]] = px_day[-1][[LEG_IDX["US100"], LEG_IDX["GER40"]]]
    return pd.DataFrame(rows, index=["US100", "GER40"]).T


def deep_history_daily(sym: str) -> pd.Series:
    """Daily close from the canonical true-UTC M1 file (cross-check only)."""
    f = CACHE / f"{sym}_daily_deep.parquet"
    if f.exists():
        return pd.read_parquet(f)[sym]
    src = REPO / f"data/deep_history_utc/{sym}_M1.csv"
    head = pd.read_csv(src, nrows=3)
    tcol = head.columns[0]
    ccol = [c for c in head.columns if c.lower() in ("close", "c")][0]
    it = pd.read_csv(src, usecols=[tcol, ccol], chunksize=2_000_000,
                     parse_dates=[tcol])
    out = []
    for ch in it:
        ch = ch.set_index(tcol)[ccol]
        out.append(ch.groupby(ch.index.normalize()).last())
    s = pd.concat(out).groupby(level=0).last().rename(sym)
    s.to_frame().to_parquet(f)
    return s


# ------------------------------------------------------------------ conditioner
def build_conditioners(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """C1 = drawdown from the EXPANDING running max; C2 = 1 - price/252d-rolling max.

    Both computed on daily closes, then reindexed onto the engine calendar and lagged one
    full engine day, so day T can only use information stamped strictly before T.
    """
    px = daily_closes()
    out = {}
    for sym in ("US100", "GER40"):
        c = px[sym].dropna()
        c1 = 1.0 - c / c.cummax()
        c2 = 1.0 - c / c.rolling(252, min_periods=252).max()
        for tag, s in (("C1", c1), ("C2", c2)):
            out[f"{tag}_{sym}"] = s.reindex(
                s.index.union(dates)).ffill().reindex(dates).shift(1)
    return pd.DataFrame(out, index=dates)


def assert_no_lookahead(dates: pd.DatetimeIndex, n_cuts: int = 40) -> None:
    """Rebuild the conditioner from truncated prices; every past value must be unchanged."""
    full = build_conditioners(dates)
    px = daily_closes()
    rng = np.random.default_rng(11)
    cuts = np.sort(rng.choice(np.arange(400, len(dates) - 5), size=n_cuts, replace=False))
    bad = 0
    for k in cuts:
        cut_date = dates[k]
        trunc = px.loc[:cut_date - pd.Timedelta(days=1)]
        sub = {}
        for sym in ("US100", "GER40"):
            c = trunc[sym].dropna()
            c1 = 1.0 - c / c.cummax()
            c2 = 1.0 - c / c.rolling(252, min_periods=252).max()
            for tag, s in (("C1", c1), ("C2", c2)):
                sub[f"{tag}_{sym}"] = s.reindex(
                    s.index.union(dates[:k + 1])).ffill().reindex(dates[:k + 1]).shift(1)
        sub = pd.DataFrame(sub, index=dates[:k + 1])
        a = full.iloc[:k + 1].to_numpy()
        b = sub.to_numpy()
        m = np.isfinite(a) & np.isfinite(b)
        if not np.allclose(a[m], b[m], atol=1e-12):
            bad += 1
    if bad:
        raise AssertionError(f"look-ahead detected at {bad}/{n_cuts} cut dates")
    print(f"look-ahead assertion: PASS ({n_cuts} cut dates, both conditioners, both legs)")


def bucketize(dd: pd.Series) -> pd.Series:
    return pd.cut(dd, bins=BUCKET_EDGES, labels=BUCKET_NAMES,
                  include_lowest=True, right=True)


# ------------------------------------------------------------------ leg returns
def leg_overnight_returns(M) -> pd.DataFrame:
    """Overnight return of each deployed leg, on the engine's own segment boundaries.

    US100: 22:05 CET day T -> 15:30 CET next engine day.
    GER40: 17:35 CET day T -> 09:00 CET next engine day.

    Returns gross bps, the round-trip cost and the measured asymmetric long swap, so net
    is reconstructible. Restricted downstream to ON days (Mon/Tue).
    """
    n = M["n"]
    rec = []
    for i in range(n - 1):
        px_d, b_d = M["days"][i]
        px_n, b_n = M["days"][i + 1]
        row = {"date": M["dates"][i]}
        for sym, k in LEG_IDX.items():
            ent_b = b_d[3] if sym == "US100" else b_d[2]      # 22:05 / 17:35
            ext_b = b_n[1] if sym == "US100" else b_n[0]      # 15:30 / 09:00
            ent = px_d[min(ent_b, len(px_d) - 1)][k]
            ext = px_n[min(ext_b, len(px_n) - 1)][k]
            g = (ext / ent - 1.0) * 1e4 if np.isfinite(ent) and np.isfinite(ext) and ent > 0 else np.nan
            row[f"{sym}_gross_bps"] = g
            row[f"{sym}_rt_bps"] = M["rt"][k]
            row[f"{sym}_swap_bps"] = M["swL"][i, k] * M["mult"][i, k]
        rec.append(row)
    df = pd.DataFrame(rec).set_index("date")
    for sym in LEG_IDX:
        df[f"{sym}_net_bps"] = (df[f"{sym}_gross_bps"] - df[f"{sym}_rt_bps"]
                                + df[f"{sym}_swap_bps"])
    return df


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])

    # --- data cross-checks demanded by the pre-registration
    pxd = daily_closes()
    m5d = m5_daily_last(M)
    print("=== DATA CROSS-CHECKS ===")
    for sym in ("US100", "GER40"):
        j = pd.concat([pxd[sym].rename("panel"), m5d[sym].rename("m5")], axis=1).dropna()
        print(f"{sym}: corr(panel_px, engine M5 daily last) = {j['panel'].corr(j['m5']):.6f}  N={len(j)}")
        try:
            dh = deep_history_daily(sym)
            j2 = pd.concat([pxd[sym].rename("panel"), dh.rename("deep")], axis=1).dropna()
            print(f"{sym}: corr(panel_px, deep_history_utc daily) = "
                  f"{j2['panel'].corr(j2['deep']):.6f}  N={len(j2)}")
        except Exception as exc:  # cross-check only; never blocks the study
            print(f"{sym}: deep_history cross-check unavailable ({exc})")
        c = pxd[sym].dropna()
        print(f"{sym}: panel_px {c.index.min().date()} -> {c.index.max().date()}, "
              f"N={len(c)}, zero-range/dup share={float((c.diff() == 0).mean()):.3f}")

    assert_no_lookahead(dates)

    cond = build_conditioners(dates)
    legs = leg_overnight_returns(M)
    cond.to_parquet(CACHE / "conditioners.parquet")
    legs.to_parquet(CACHE / "leg_returns.parquet")

    print("\n=== CONDITIONER COVERAGE (engine calendar) ===")
    for c in cond.columns:
        s = cond[c].dropna()
        print(f"{c:12s} N={len(s):5d}  median={s.median():.4f}  "
              f"share dd<=1%={float((s <= 0.01).mean()):.3f}")

    on = np.isin(dates.dayofweek, [0, 1])
    print(f"\nON days (Mon/Tue): {int(on.sum())} / {len(dates)}")
    print("leg return coverage on ON days:")
    for sym in LEG_IDX:
        s = legs[f"{sym}_gross_bps"].reindex(dates)[on].dropna()
        print(f"  {sym}: N={len(s)}  mean_gross={s.mean():.2f}bps  "
              f"rt={M['rt'][LEG_IDX[sym]]:.2f}bps  "
              f"mean_swap={legs[f'{sym}_swap_bps'].reindex(dates)[on].mean():.2f}bps")


if __name__ == "__main__":
    main()
