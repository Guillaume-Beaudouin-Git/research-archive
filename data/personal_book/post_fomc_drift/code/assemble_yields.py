"""Assemble canonical yield/RF/target-change inputs per HYPOTHESIS.md section 3.

Primary plan was FRED fredgraph.csv (DGS2, DGS10, DTB3, DFEDTAR, DFEDTARU). FRED was
unreachable at run time (504 / timeouts, see report). Fallback uses the PRIMARY sources
that FRED republishes:
  - treasury.gov daily yield-curve CSVs  -> '2 Yr' == DGS2, '10 Yr' == DGS10 (CMT)
  - treasury.gov daily bill-rates CSVs   -> '13 WEEKS BANK DISCOUNT' == DTB3
  - federalreserve.gov/monetarypolicy/openmarket.htm -> target-change dates
    (== DFEDTAR/DFEDTARU change dates; listed as EFFECTIVE dates, hence the
    pre-registered +/-1 business-day matching tolerance)

Whichever source is used is recorded in data_cache/provenance.json. The substitution is
a data-SOURCE substitution only (identical underlying H.15/Treasury data); cross-checked
numerically against the repo FRED parquet (t10y2y, t10y3m, dgs3mo; 2010-2026).

Outputs: data_cache/{DGS2,DGS10,DTB3}.csv (DATE,VALUE), data_cache/target_changes.csv,
data_cache/provenance.json
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
DC = BASE / "data_cache"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def fred_csv_valid(p: Path) -> bool:
    if not p.exists() or p.stat().st_size < 20_000:
        return False
    head = p.read_text(errors="ignore")[:200].lower()
    return ("date" in head or "observation" in head) and "504" not in head


def from_treasury_yc(col: str) -> pd.Series:
    frames = []
    for f in sorted(glob.glob(str(DC / "treasury/yc_*.csv"))):
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        if col not in df.columns:
            raise SystemExit(f"{f}: column {col!r} missing ({list(df.columns)})")
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(df["Date"], format="%m/%d/%Y"),
            "v": pd.to_numeric(df[col], errors="coerce"),
        }))
    s = (pd.concat(frames).dropna().drop_duplicates(subset="date").sort_values("date")
         .set_index("date")["v"])
    return s


def from_treasury_bills() -> pd.Series:
    frames = []
    for f in sorted(glob.glob(str(DC / "treasury/bill_*.csv"))):
        df = pd.read_csv(f)
        df.columns = [c.strip() for c in df.columns]
        col = next(c for c in df.columns if "13 WEEKS BANK DISCOUNT" in c.upper())
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(df["Date"], format="%m/%d/%Y"),
            "v": pd.to_numeric(df[col], errors="coerce"),
        }))
    s = (pd.concat(frames).dropna().drop_duplicates(subset="date").sort_values("date")
         .set_index("date")["v"])
    return s


def write_series(s: pd.Series, name: str) -> None:
    out = s.reset_index()
    out.columns = ["DATE", name]
    out.to_csv(DC / f"{name}.csv", index=False)


def changes_from_fred() -> pd.DatetimeIndex:
    chg = []
    for sid in ("DFEDTAR", "DFEDTARU"):
        df = pd.read_csv(DC / f"{sid}.csv", na_values=["."])
        df.columns = ["date", "v"]
        df["date"] = pd.to_datetime(df["date"])
        s = pd.to_numeric(df.set_index("date")["v"], errors="coerce").dropna()
        d = s.diff()
        chg += list(d.index[d.abs() > 1e-9])
    return pd.DatetimeIndex(sorted(set(chg)))


def changes_from_openmarket() -> pd.DatetimeIndex:
    html = (DC / "openmarket.html").read_text(errors="ignore")
    tables = [(m.start(), m.group(0)) for m in re.finditer(r"<table.*?</table>", html, re.S)]
    dates = []
    for pos, tab in tables:
        ctx = html[max(0, pos - 800):pos]
        years = re.findall(r">\s*(20[0-2]\d)\s*<", ctx)
        if not years:
            raise SystemExit(f"openmarket parse: no year header before table at {pos}")
        year = int(years[-1])
        txt = re.sub(r"<[^>]+>", "|", tab)
        for mname, day in re.findall(
            r"\|\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s*\|",
            txt,
        ):
            dates.append(pd.Timestamp(year=year, month=MONTHS[mname], day=int(day)))
    out = pd.DatetimeIndex(sorted(set(dates)))
    per_year = pd.Series(out.year).value_counts().sort_index()
    print(f"[openmarket] {len(out)} target-change dates; per year: {dict(per_year)}")
    return out


def main() -> None:
    prov = {}
    for name, builder in (
        ("DGS2", lambda: from_treasury_yc("2 Yr")),
        ("DGS10", lambda: from_treasury_yc("10 Yr")),
        ("DTB3", from_treasury_bills),
    ):
        p = DC / f"{name}.csv"
        if fred_csv_valid(p):
            prov[name] = "FRED fredgraph.csv"
            print(f"[{name}] FRED file valid -> kept")
        else:
            s = builder()
            write_series(s, name)
            prov[name] = "treasury.gov (primary source; FRED unreachable)"
            print(f"[{name}] treasury.gov {s.index.min().date()}..{s.index.max().date()} n={len(s)}")

    if fred_csv_valid(DC / "DFEDTAR.csv") and fred_csv_valid(DC / "DFEDTARU.csv"):
        chg = changes_from_fred()
        prov["target_changes"] = "FRED DFEDTAR/DFEDTARU diffs"
    else:
        chg = changes_from_openmarket()
        prov["target_changes"] = "federalreserve.gov openmarket.htm (primary source; FRED unreachable)"
    pd.DataFrame({"date": chg}).to_csv(DC / "target_changes.csv", index=False)
    print(f"[target_changes] {len(chg)} dates {chg.min().date()}..{chg.max().date()}")

    # cross-check vs repo FRED parquet (t10y2y = DGS10-DGS2, t10y3m = DGS10-DGS3MO)
    pq = sorted(glob.glob(str(REPO / "data/raw/fred_*DGS3MO*.parquet")))
    if pq:
        f = pd.read_parquet(pq[0])
        if not isinstance(f.index, pd.DatetimeIndex):
            f = f.set_index(pd.DatetimeIndex(f.index))
        dgs10_chk = (f["t10y3m"] + f["dgs3mo"]).dropna()
        dgs2_chk = (f["t10y3m"] + f["dgs3mo"] - f["t10y2y"]).dropna()
        d2 = pd.read_csv(DC / "DGS2.csv", parse_dates=["DATE"]).set_index("DATE").iloc[:, 0]
        d10 = pd.read_csv(DC / "DGS10.csv", parse_dates=["DATE"]).set_index("DATE").iloc[:, 0]
        a2 = pd.concat([d2, dgs2_chk], axis=1).dropna()
        a10 = pd.concat([d10, dgs10_chk], axis=1).dropna()
        prov["crosscheck_vs_repo_fred_parquet"] = {
            "DGS2_maxabsdiff": float((a2.iloc[:, 0] - a2.iloc[:, 1]).abs().max()),
            "DGS10_maxabsdiff": float((a10.iloc[:, 0] - a10.iloc[:, 1]).abs().max()),
            "n_common_DGS2": int(len(a2)),
        }
        print(f"[crosscheck] vs repo parquet: {prov['crosscheck_vs_repo_fred_parquet']}")
    (DC / "provenance.json").write_text(json.dumps(prov, indent=1))


if __name__ == "__main__":
    main()
