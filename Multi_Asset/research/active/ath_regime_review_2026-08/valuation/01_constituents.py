"""Parse index constituents from Wikipedia raw wikitext (cached in cache/).

Sources (vintage: fetched 2026-08-09):
  - cache/ndx_list.wiki : en.wikipedia.org/wiki/List_of_NASDAQ-100_companies (action=raw)
  - cache/dax_raw.wiki  : en.wikipedia.org/wiki/DAX (action=raw)

Output: cache/constituents_ndx.csv, cache/constituents_dax.csv
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def _clean_wikilink(s: str) -> str:
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = s.replace("'''", "").replace("''", "")
    return s.strip()


def parse_ndx(path: Path) -> pd.DataFrame:
    txt = path.read_text(encoding="utf-8")
    start = txt.index('id="constituents"')
    end = txt.index("|}", start)
    rows = []
    for block in txt[start:end].split("\n|-\n")[1:]:
        cells = [_clean_wikilink(c) for c in block.split("||")]
        if len(cells) < 2:
            continue
        ticker = cells[0].lstrip("| ").strip()
        if not re.fullmatch(r"[A-Z.]{1,6}", ticker):
            continue
        rows.append(
            {
                "ticker": ticker,
                "company": cells[1],
                "icb_industry": cells[2] if len(cells) > 2 else "",
                "icb_subsector": cells[3].split("\n")[0] if len(cells) > 3 else "",
            }
        )
    return pd.DataFrame(rows).drop_duplicates("ticker").reset_index(drop=True)


def parse_dax(path: Path) -> pd.DataFrame:
    """Row layout in the DAX article `id=constituents` table:

    | {{FWB link|ADS.DE}} || [[File:...]] || [[Adidas]] || Apparel || 2.5 || emp || founded

    The `Index weighting (%)` column is a STALE published weight (table
    vintage 2025-09-22) and is kept only as a cross-check, never as
    the working weight.
    """
    txt = path.read_text(encoding="utf-8")
    start = txt.index('id="constituents"')
    end = txt.index("\n|}", start)
    rows = []
    for block in txt[start:end].split("\n|-")[1:]:
        cells = block.split("||")
        if len(cells) < 4:
            continue
        m = re.search(r"FWB link\|([A-Z0-9]+\.[A-Z]{2})", cells[0])
        if not m:
            continue
        w = _clean_wikilink(cells[4]) if len(cells) > 4 else ""
        try:
            w_pub = float(w)
        except ValueError:
            w_pub = float("nan")
        rows.append(
            {
                "ticker": m.group(1),
                "company": _clean_wikilink(cells[2]),
                "sector": _clean_wikilink(cells[3]),
                "published_weight_pct_2025_09": w_pub,
            }
        )
    return pd.DataFrame(rows).drop_duplicates("ticker").reset_index(drop=True)


if __name__ == "__main__":
    ndx = parse_ndx(CACHE / "ndx_list.wiki")
    ndx.to_csv(CACHE / "constituents_ndx.csv", index=False)
    print(f"NDX parsed: {len(ndx)} rows")
    print(ndx.head(8).to_string())

    dax = parse_dax(CACHE / "dax_raw.wiki")
    dax.to_csv(CACHE / "constituents_dax.csv", index=False)
    print(f"\nDAX parsed: {len(dax)} rows")
    print(dax.to_string())
