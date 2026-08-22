"""
finalize_B.py — TRACK B validation + MANIFEST.
(1) random-day spot-check of each final commodity CSV vs `dukascopy-node -t m1` (0 mismatch),
(2) MANIFEST (md + csv) -> audit-fetch-B/.  READ-ONLY on sources.
"""
from __future__ import annotations
import json, random, subprocess, warnings
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

warnings.filterwarnings("ignore")
import duka_m1_backfill as D  # noqa: E402
from duka_commodities import COMM  # noqa: E402

OUT = D.BASE.parent / "deep_history_utc"
AUDIT = D.BASE.parent.parent / "audit-fetch-B"; AUDIT.mkdir(parents=True, exist_ok=True)
DNODE = D.BASE / "_tool" / "node_modules" / ".bin" / "dukascopy-node"
TMP = Path("/tmp/spotcheck_B"); TMP.mkdir(exist_ok=True)
random.seed(11)
ABSENT = {"WHEAT": "no Dukascopy code in instrumentMetaData", "CORN": "no Dukascopy code in instrumentMetaData"}


def spotcheck(sym: str, cfg: dict, per: int = 2) -> dict:
    f = OUT / f"{sym}_M1.csv"
    if not f.exists():
        return dict(n_days=0, mismatches=None, note="no CSV")
    dp = cfg["dp"]; tol = 1.5 * 10 ** -dp; dnid = cfg["code"].lower()
    yrs = [int(y) for y in subprocess.run(["bash", "-c", f"grep -oE '^[0-9]{{4}}' '{f}' | sort -u"],
           capture_output=True, text=True).stdout.split()]
    if not yrs:
        return dict(n_days=0, mismatches=None)
    days, mism, matched, checked = [], 0, 0, 0
    tries = 0
    while len(days) < per and tries < 60:
        tries += 1
        y = random.choice(yrs[:-1] if len(yrs) > 1 else yrs)
        d = date(y, random.randint(1, 12), random.randint(1, 28))
        if d.weekday() >= 5 or d in days:
            continue
        days.append(d)
        out = TMP / f"{sym}_{d}.csv"
        if out.exists():
            out.unlink()
        subprocess.run([str(DNODE), "-i", dnid, "-from", d.isoformat(), "-to", (d + timedelta(days=1)).isoformat(),
                        "-t", "m1", "-p", "bid", "-f", "csv", "-dir", str(TMP), "-fn", f"{sym}_{d}", "-s"],
                       capture_output=True, timeout=120)
        if not out.exists():
            continue
        tv = pd.read_csv(out)
        tv["hm"] = pd.to_datetime(tv["timestamp"], unit="ms", utc=True).dt.strftime("%H:%M")
        r = subprocess.run(["grep", f"^{d.strftime('%Y.%m.%d')} ", str(f)], capture_output=True, text=True)
        mine = {ln.split(",")[0][11:16]: [float(x) for x in ln.split(",")[1:5]] for ln in r.stdout.splitlines()}
        for _, row in tv.iterrows():
            if row["hm"] in mine:
                matched += 1
                for i, col in enumerate(("open", "high", "low", "close")):
                    if abs(mine[row["hm"]][i] - round(row[col], dp)) > tol:
                        mism += 1
        checked += 1
    return dict(n_days=checked, matched_bars=matched, mismatches=mism)


def main():
    asm = {r["symbol"]: r for r in json.load(open(D.BASE / "reports" / "commodity_assembly.json"))}
    dl = json.load(open(D.BASE / "reports" / "download_status_COMM.json")) if (D.BASE / "reports" / "download_status_COMM.json").exists() else []
    dl_fail = [d for d in dl if d.get("status") in ("fetch_err", "ohlc_fail")]
    fail_str = "none" if not dl_fail else ", ".join(f"{d['sym']} {d['year']} ({d['status']})" for d in dl_fail)

    rows = []
    for sym in COMM:
        a = asm.get(sym, {"symbol": sym, "status": "MISSING"})
        sc = spotcheck(sym, COMM[sym]) if a.get("status") == "ok" else {"n_days": 0, "mismatches": None}
        a["spotcheck_days"] = sc.get("n_days"); a["spotcheck_mismatches"] = sc.get("mismatches")
        rows.append(a)
        print(f"  {sym:9} spotcheck {sc.get('n_days')}d mism={sc.get('mismatches')}", flush=True)

    cols = ["symbol", "code", "decimalFactor", "point", "start", "end", "rows", "monotonic", "dups",
            "ohlc_violations", "ohlc_dropped", "spread_negative", "spread_median", "spread_p95", "spread_zero_frac",
            "spread_basis", "tick_volume_zero_frac", "tick_volume_all_zero", "real_volume",
            "intraweek_gaps_gt2min", "max_gap_hours", "spotcheck_days", "spotcheck_mismatches", "status"]
    df = pd.DataFrame([{c: r.get(c) for c in cols} for r in rows])
    df.to_csv(AUDIT / "manifest_commodities.csv", index=False)

    L = ["# Track B — Commodity complex MANIFEST (Dukascopy M1, TRUE UTC)", "",
         "**Output:** `data/deep_history_utc/<SYM>_M1.csv` · **Schema:** `timestamp_utc,open,high,low,close,"
         "tick_volume,spread,real_volume` (= existing XAUUSD), OHLC = Dukascopy BID, **TRUE UTC** (native, "
         "no shift). Pipeline reused from Track A (`duka_m1_backfill.py`: OCLH decode, per-instrument "
         "decimalFactor, `v<=0 AND h<=l` flat-drop, fail-loud-on-dropped-day, nw=8).", "",
         "## Decoder gate (new decimalFactor families)",
         "- df=1000 (WTI) and **df=10000 (copper, natgas — NEW)** vs `dukascopy-node`, days with down-bars: "
         "**0 OHLC mismatches**, max|Δ|=0.0. OCLH byte order confirmed for commodities.", "",
         "## ⚠ Spread basis (honest — NOT validated MT5)",
         "`ftmo_specs_full.csv` has **no spread column** (only digits/swap/commission/session) → spec-anchor "
         "unavailable. So:",
         "- **XAGUSD = gold-proxy**: raw ECN spread × gold's hour-of-UTC ECN→MT5 multiplier (fitted on the "
         "2024 FTMO-XAU vs Duka-XAU overlap).",
         "- **all others = ECN_RAW_UNCALIBRATED**: raw Dukascopy ask−bid (instrument points = 1/decimalFactor).",
         "> These commodity spreads are **ECN-or-proxied, NOT validated MT5**. Acceptable for a daily, "
         "cost-robust strategy (Ross Hook); **NOT** for intraday spread-sensitive use without a real FTMO overlap.",
         "- `real_volume` = all-zero (Dukascopy has none). `tick_volume` = Dukascopy M1 candle volume "
         "(zero-fraction reported per instrument; some bars carry v=0 with a real range, kept via the h>l rule).", "",
         "## Instruments", "",
         "| sym | code | df | range (UTC) | rows | spread_basis | sprd_med | vol0% | mono/dups/ohlc✗ | spotcheck | gaps |",
         "|---|---|--:|---|--:|---|--:|--:|---|---|--:|"]
    for r in rows:
        if r.get("status") != "ok":
            L.append(f"| {r['symbol']} | {COMM[r['symbol']]['code']} | {COMM[r['symbol']]['df']} | — | — | — | — | — | "
                     f"**{r.get('status')}** | — | — |"); continue
        L.append(f"| {r['symbol']} | {r['code']} | {r['decimalFactor']} | {str(r['start'])[:10]}→{str(r['end'])[:10]} | "
                 f"{r['rows']} | {r['spread_basis'][:14]} | {r['spread_median']} | {r['tick_volume_zero_frac']} | "
                 f"{r['monotonic']}/{r['dups']}/{r['ohlc_violations']} | {r['spotcheck_days']}d "
                 f"mism={r['spotcheck_mismatches']} | {r['intraweek_gaps_gt2min']} |")

    L += ["", "## What could NOT be fetched (reported, not invented)",
          "- **WHEAT, CORN — ABSENT on Dukascopy** (no instrument code in `instrumentMetaData`). Not fetched, not invented.",
          "- **Depth floors (Dukascopy candle):** silver 2003-08, Brent 2010-12, copper 2012-03, natgas 2012-09, "
          "WTI 2013-01, all ags 2017. PRIORITY = breadth: shallow ags kept, floors reported.",
          "- **No FTMO M1 overlap** for any new commodity (existing FTMO commodity = gold only) → no instrument got "
          "a validated MT5 spread calibration; silver is gold-proxied, the rest are raw ECN (flagged above).",
          "- **ftmo_specs has no spread field** → option (b) spec-anchored calibration impossible.",
          "- M5 Dukascopy caches exist (`Forex/data/cache/dukascopy_m5/` XAGUSD/USOIL/UKOIL/NGAS) but are M5, not "
          "M1 — not used; this delivers fresh M1.",
          f"- **Download failures (OHLC-guard/fetch_err):** {fail_str}"]
    L += ["", "## Scope", "Commodities ONLY. FX/metals-gold/indices/crypto untouched and NOT re-fetched. No splice "
          "(net-new). No Ross-Hook re-test (separate Cowork step). Daily resample (EET server-day) is downstream."]
    (AUDIT / "MANIFEST_commodities.md").write_text("\n".join(L))
    print(f"\nMANIFEST -> {AUDIT/'MANIFEST_commodities.md'} + manifest_commodities.csv")
    if dl_fail:
        print("  download failures:", [(d["sym"], d["year"]) for d in dl_fail])


if __name__ == "__main__":
    main()
