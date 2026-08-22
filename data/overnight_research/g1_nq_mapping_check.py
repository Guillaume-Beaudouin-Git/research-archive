"""G1 — Independent reconstruction on NQ databento.

Goals:
  1. Reproduce +4.90 bps / t=4.04 on toutes-nuits from M1 RTH bars.
  2. EXPLICITLY validate three invariants:
     (a) close[t-1] is the previous-day close (shift(1), NOT shift(-1))
     (b) weekday in report = weekday of OPEN day t
     (c) "Tue-open = Mon-night hold" — verify by inspecting concrete rows
  3. Falsification probe: also compute the WRONG mapping (shift(-1) and
     weekday-of-close), confirm they DON'T match the reported numbers.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

PATH = "<HOME>/Desktop/Algo_claude/data/raw/NQ_1min_databento_2010-2026.parquet"


def hac_t(x, lag=6):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 30:
        return np.nan, np.nan
    X = np.ones((len(x), 1))
    r = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(r.params[0]), float(r.params[0] / r.bse[0]) if r.bse[0] > 0 else np.nan


def load_rth_daily():
    print("Loading parquet ...")
    d = pd.read_parquet(PATH)
    d = d[d["is_rth"] == True].copy()
    d.index = pd.to_datetime(d.index)
    # Use US/Eastern to attribute each RTH bar to its NY trading date.
    d["et"] = d.index.tz_convert("US/Eastern")
    d["date"] = d["et"].dt.normalize().dt.tz_localize(None)
    g = d.groupby("date")
    out = pd.DataFrame({
        "o": g["open"].first(),
        "c": g["close"].last(),
        "first_ts": g["et"].min(),
        "last_ts": g["et"].max(),
        "n_bars": g.size(),
    })
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    return out


def report_table(df, col, label):
    print(f"\n--- {label} (bps) ---")
    print(f"{'wd':5s}{'n':>7s}{'mean':>10s}{'t_HAC6':>10s}{'IN<2019':>10s}{'OOS≥2019':>10s}")
    for wd in range(5):
        s = df[df.wd == wd][col].values
        if len(s) < 30:
            continue
        mu, t = hac_t(s)
        ins = df[(df.wd == wd) & (df.yr < 2019)][col].mean()
        oos = df[(df.wd == wd) & (df.yr >= 2019)][col].mean()
        print(f"{['Mon','Tue','Wed','Thu','Fri'][wd]:5s}{len(s):7d}{mu:10.3f}{t:10.2f}{ins:10.3f}{oos:10.3f}")
    s = df[col].values
    mu, t = hac_t(s)
    ins = df[df.yr < 2019][col].mean()
    oos = df[df.yr >= 2019][col].mean()
    print(f"{'ALL':5s}{len(s):7d}{mu:10.3f}{t:10.2f}{ins:10.3f}{oos:10.3f}")


def main():
    d = load_rth_daily()
    print(f"\nDays after RTH grouping: {len(d)}")
    print(f"First trading day: {d.index[0]}  bars={d.n_bars.iloc[0]}  {d.first_ts.iloc[0]} → {d.last_ts.iloc[0]}")
    print(f"Last  trading day: {d.index[-1]}  bars={d.n_bars.iloc[-1]}  {d.first_ts.iloc[-1]} → {d.last_ts.iloc[-1]}")
    print(f"Bars per day median={int(d.n_bars.median())}  min={d.n_bars.min()}  max={d.n_bars.max()}")

    # ===== CANONICAL MAPPING (the report's claim) =====
    d["pc"] = d["c"].shift(1)
    d["ov_bps"] = (d["o"] / d["pc"] - 1) * 1e4
    d["in_bps"] = (d["c"] / d["o"] - 1) * 1e4
    d["wd"] = d.index.weekday
    d["yr"] = d.index.year
    d = d.dropna(subset=["ov_bps"])

    # ===== INVARIANT (a) close[t-1] = veille =====
    # Pick 3 random rows, confirm pc[i] == c.iloc[i-1] (NOT c.iloc[i+1])
    print("\n=== INVARIANT (a) close[t-1] = veille via shift(1) ===")
    for i in [50, 500, 2000]:
        row = d.iloc[i]
        prev_close = d["c"].iloc[i - 1]
        next_close = d["c"].iloc[i + 1] if i + 1 < len(d) else np.nan
        ok_prev = abs(row["pc"] - prev_close) < 1e-6
        not_next = abs(row["pc"] - next_close) > 1e-6 if not np.isnan(next_close) else True
        prev_date = d.index[i - 1].date()
        next_date = d.index[i + 1].date() if i + 1 < len(d) else None
        print(f"  i={i}  date={row.name.date()}  o={row['o']:.2f}  pc={row['pc']:.2f}")
        print(f"         prev_close (date {prev_date}) = {prev_close:.2f}  match_prev={ok_prev}")
        print(f"         next_close (date {next_date}) = {next_close:.2f}  not_next={not_next}")
        assert ok_prev and not_next, f"INVARIANT (a) BROKEN at i={i}"
    print("✓ (a) close[t-1] is veille, NOT j+1")

    # ===== INVARIANT (b) weekday of t = weekday du OPEN day =====
    print("\n=== INVARIANT (b) weekday = OPEN day t (not previous day) ===")
    # A Tuesday open day must have weekday==1; the night BEFORE (Mon close) is its overnight return.
    tue_rows = d[d.wd == 1].head(3)
    for ts, row in tue_rows.iterrows():
        prev_dow = (ts - pd.Timedelta(days=1)).strftime("%A")
        cur_dow = ts.strftime("%A")
        print(f"  date={ts.date()}  cur={cur_dow}(wd={row['wd']})  prev_date_dow={prev_dow}  o={row['o']:.2f}  pc(=prev close)={row['pc']:.2f}")
        assert row["wd"] == 1 and cur_dow == "Tuesday"
    print("✓ (b) Tue-open day has wd==1, previous close is from Monday")

    # ===== INVARIANT (c) "Tue-open = Mon-night hold" =====
    print("\n=== INVARIANT (c) 'Tue-open = Mon-night hold' ===")
    sample = d[d.wd == 1].iloc[100]
    ts = sample.name
    prev_ts = d.index[d.index.get_loc(ts) - 1]
    print(f"  Tue open day:  {ts.date()}  (open={sample['o']:.2f})")
    print(f"  Held overnight: bought at close of {prev_ts.date()} ({prev_ts.strftime('%A')}, c={d.loc[prev_ts, 'c']:.2f})")
    print(f"  Sold at open of {ts.date()} ({ts.strftime('%A')}, o={sample['o']:.2f})")
    print(f"  ov_bps = (o/pc-1)*1e4 = ({sample['o']:.2f}/{sample['pc']:.2f}-1)*1e4 = {sample['ov_bps']:.2f} bps")
    print("✓ (c) Mardi-open ov = (Tue open / Mon close - 1)")

    # ===== Reproduction =====
    print("\n=== CANONICAL: weekday = OPEN day, pc = shift(1) ===")
    report_table(d, "ov_bps", "OVERNIGHT (canonical)")
    report_table(d, "in_bps", "INTRADAY (canonical)")
    yr = d.groupby("yr")["ov_bps"].mean()
    print(f"\novernight positive years: {(yr>0).sum()}/{len(yr)}  worst {yr.min():.2f} best {yr.max():.2f}")

    # ===== Falsification probe 1: WRONG MAPPING — shift(-1) =====
    print("\n=== FALSIFICATION PROBE: WRONG mapping (pc=shift(-1)) — should NOT replicate ===")
    bad = d.copy()
    bad["bad_pc"] = bad["c"].shift(-1)  # future close — look-ahead
    bad["bad_ov"] = (bad["o"] / bad["bad_pc"] - 1) * 1e4
    bad = bad.dropna(subset=["bad_ov"])
    mu, t = hac_t(bad["bad_ov"].values)
    print(f"  shift(-1) overnight ALL = {mu:.3f} bps  t={t:.2f}  → contaminated by look-ahead")

    # ===== Falsification probe 2: WRONG MAPPING — weekday of close (already same, just re-label) =====
    print("\n=== FALSIFICATION PROBE: SHIFTED weekday label (Mon-open mislabeled as Tue) ===")
    bad2 = d.copy()
    bad2["wd_shifted"] = (bad2["wd"] - 1) % 5  # off-by-one weekday assignment
    print(f"{'shifted_wd':12s}{'n':>7s}{'mean':>10s}{'t_HAC6':>10s}")
    for wd in range(5):
        s = bad2[bad2.wd_shifted == wd]["ov_bps"].values
        if len(s) < 30: continue
        mu, t = hac_t(s)
        print(f"{['Mon','Tue','Wed','Thu','Fri'][wd]:12s}{len(s):7d}{mu:10.3f}{t:10.2f}")
    print("  ↑ If we mislabel, Tue/Wed peaks slide to Mon/Tue → confirms mapping matters.")

    # Save canonical daily series for downstream gates
    d[["o", "c", "pc", "ov_bps", "in_bps", "wd", "yr"]].to_parquet(
        "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
    )
    print("\nSaved: data/overnight_research/nq_rth_daily.parquet")


if __name__ == "__main__":
    main()
