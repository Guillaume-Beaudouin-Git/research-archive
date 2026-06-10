"""Trial I-1 stage (a): cliff-unlock event DB from DefiLlama + Binance perp mapping.

Output: cache/i1_events.parquet + i1_coverage.md (coverage report).
Spec frozen in ../preregistration.md — no parameter here is tunable.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
import pandas as pd

import lib_data as ld

MIN_SIZE_PCT = 1.0          # cliff >= 1% of circulating proxy
SAMPLE_END = pd.Timestamp("2026-05-25", tz="UTC")   # need T+3d inside 1h archive (<= 2026-05)
EXCLUDED_CATS = {"noncirculating"}


def circ_proxy_series(em: dict) -> pd.Series | None:
    """Cumulative documented unlocked minus noncirculating labels, daily."""
    dd = (em.get("documentedData") or {}).get("data") or []
    if not dd:
        return None
    # label -> category from events (recipient -> category)
    label_cat: dict[str, str] = {}
    for ue in (em.get("metadata") or {}).get("unlockEvents") or []:
        for a in (ue.get("cliffAllocations") or []) + (ue.get("linearAllocations") or []):
            label_cat[a.get("recipient", "")] = a.get("category", "")
    frames = []
    for sec in dd:
        lab = sec.get("label", "")
        if label_cat.get(lab, "") in EXCLUDED_CATS:
            continue
        rows = sec.get("data") or []
        if not rows:
            continue
        s = pd.Series({pd.Timestamp(float(r["timestamp"]), unit="s", tz="UTC"): float(r.get("unlocked") or 0)
                       for r in rows if r.get("timestamp") is not None})
        frames.append(s.sort_index())
    if not frames:
        return None
    df = pd.concat(frames, axis=1).sort_index().ffill().fillna(0)
    return df.sum(axis=1)


def extract_events(protocol: str, em: dict) -> list[dict]:
    meta = em.get("metadata") or {}
    events = meta.get("events") or []
    gecko = em.get("gecko_id") or ""
    circ = circ_proxy_series(em)
    if circ is None or not events:
        return []
    by_day: dict[pd.Timestamp, dict] = defaultdict(lambda: {"tokens": 0.0, "cats": set()})
    for ev in events:
        if ev.get("unlockType") != "cliff":
            continue
        cat = ev.get("category", "")
        if cat in EXCLUDED_CATS:
            continue
        if ev.get("timestamp") is None:
            continue
        ts = pd.Timestamp(float(ev["timestamp"]), unit="s", tz="UTC")
        n = ev.get("noOfTokens") or []
        amt = float(np.nansum([float(x) for x in n])) if n else 0.0
        if amt <= 0:
            continue
        day = ts.normalize()
        by_day[day]["tokens"] += amt
        by_day[day]["cats"].add(cat or "Uncategorized")
    out = []
    for day, agg in by_day.items():
        # circulating proxy strictly before the event day
        prior = circ[circ.index < day]
        if prior.empty or prior.iloc[-1] <= 0:
            continue
        size_pct = 100.0 * agg["tokens"] / prior.iloc[-1]
        out.append({
            "protocol": protocol, "gecko_id": gecko, "day": day,
            "tokens": agg["tokens"], "circ_proxy": prior.iloc[-1],
            "size_pct": size_pct, "cats": "|".join(sorted(agg["cats"])),
            "insider": int(bool(agg["cats"] & {"insiders", "privateSale"})),
        })
    return out


def main() -> None:
    protocols = ld.llama_protocol_list()
    print(f"protocols listed: {len(protocols)}")
    ems = ld.fetch_all_emissions(protocols)
    print(f"emissions fetched: {len(ems)}")

    rows: list[dict] = []
    for p, em in ems.items():
        rows += extract_events(p, em)
    ev = pd.DataFrame(rows)
    n_all = len(ev)
    ev = ev[ev["day"] <= SAMPLE_END]
    ev_big = ev[ev["size_pct"] >= MIN_SIZE_PCT].copy()
    print(f"cliff events (merged by day): {n_all}; <= sample end: {len(ev)}; >= {MIN_SIZE_PCT}%: {len(ev_big)}")

    # ---- map to Binance UM perp ----
    tick = ld.coingecko_ticker_map()
    syms = set(ld.all_um_symbols())
    def to_symbol(gid: str) -> str | None:
        t = tick.get(gid)
        if not t:
            return None
        for cand in (f"{t}USDT", f"1000{t}USDT"):
            if cand in syms:
                return cand
        return None
    ev_big["symbol"] = ev_big["gecko_id"].map(to_symbol)
    mapped = ev_big.dropna(subset=["symbol"]).copy()
    print(f"with a Binance UM perp (ever listed): {len(mapped)} events / {mapped['symbol'].nunique()} symbols")

    # ---- ex-ante floor at T-10d: listing age >= 60d AND 30d median quote vol >= $20M ----
    keep = []
    for sym, grp in mapped.groupby("symbol"):
        lm = ld.listing_month(sym)
        if lm is None:
            continue
        listed = pd.Timestamp(lm + "-01", tz="UTC")
        try:
            d = ld.rest_daily_klines(sym)
        except Exception as e:  # noqa: BLE001
            print(f"  REST daily FAIL {sym}: {e} -> events dropped (fail-loud)")
            continue
        med30 = d["quote_volume"].rolling(30, min_periods=20).median()
        for _, r in grp.iterrows():
            t10 = r["day"] - pd.Timedelta(days=10)
            if (t10 - listed).days < 60:
                continue
            m = med30[med30.index <= t10]
            if m.empty or not np.isfinite(m.iloc[-1]) or m.iloc[-1] < 20e6:
                continue
            keep.append({**r.to_dict(), "listed": listed, "medvol_t10": m.iloc[-1]})
    db = pd.DataFrame(keep).sort_values("day").reset_index(drop=True)
    db.to_parquet(ld.CACHE / "i1_events.parquet")
    print(f"FINAL event DB: {len(db)} events / {db['symbol'].nunique()} symbols")

    # ---- circ proxy validation vs CoinGecko mcap/price (3 tokens x 3 dates) ----
    val_rows = []
    for gid in ["arbitrum", "aptos", "celestia"]:
        try:
            import requests
            r = requests.get(f"https://api.coingecko.com/api/v3/coins/{gid}/market_chart",
                             params={"vs_currency": "usd", "days": "365", "interval": "daily"}, timeout=30)
            j = r.json()
            mc = pd.Series({pd.Timestamp(t, unit="ms", tz="UTC"): v for t, v in j["market_caps"]})
            px = pd.Series({pd.Timestamp(t, unit="ms", tz="UTC"): v for t, v in j["prices"]})
            cg_circ = (mc / px).dropna()
            em = ld.llama_emissions(next(p for p, e in ems.items() if e.get("gecko_id") == gid))
            ours = circ_proxy_series(em)
            for q in (0.25, 0.5, 0.75):
                t = cg_circ.index[int(q * (len(cg_circ) - 1))]
                o = ours[ours.index <= t]
                if o.empty:
                    continue
                val_rows.append({"token": gid, "date": str(t.date()),
                                 "ours": o.iloc[-1], "coingecko": cg_circ.loc[t],
                                 "rel_err": o.iloc[-1] / cg_circ.loc[t] - 1})
        except Exception as e:  # noqa: BLE001
            val_rows.append({"token": gid, "date": "FAIL", "ours": np.nan, "coingecko": np.nan,
                             "rel_err": np.nan})
            print(f"  CG validation fail {gid}: {e}")
    val = pd.DataFrame(val_rows)
    val.to_csv(ld.CACHE / "i1_circ_validation.csv", index=False)

    with open(ld.ROOT / "i1_coverage.md", "w") as f:
        f.write("# I-1 stage (a) — event DB coverage report\n\n")
        f.write(f"- DefiLlama protocols listed: **{len(protocols)}**, emissions JSONs fetched: **{len(ems)}**\n")
        f.write(f"- Cliff events (same-day merged, ex-noncirculating): **{n_all}**; ≤ {SAMPLE_END.date()}: **{len(ev)}**\n")
        f.write(f"- ≥ {MIN_SIZE_PCT}% of circ proxy: **{len(ev_big)}**; with a Binance UM perp ever listed: **{len(mapped)}**\n")
        f.write(f"- Passing ex-ante floor (age≥60d, 30d med vol ≥ $20M at T-10): **{len(db)}** events, "
                f"**{db['symbol'].nunique()}** symbols, {db['day'].min().date()} → {db['day'].max().date()}\n")
        f.write(f"- Insider/privateSale-flagged events: **{int(db['insider'].sum())}** vs other: {int((1-db['insider']).sum())}\n\n")
        f.write("## Circulating-proxy validation vs CoinGecko (mcap/price)\n\n")
        f.write("| token | date | ours | coingecko | rel_err |\n|---|---|---|---|---|\n")
        for _, r in val.iterrows():
            f.write(f"| {r['token']} | {r['date']} | {r['ours']:.3e} | {r['coingecko']:.3e} | "
                    f"{r['rel_err']:+.1%} |\n" if pd.notna(r["rel_err"]) else
                    f"| {r['token']} | {r['date']} | — | — | FAIL |\n")
        f.write("\n")
        f.write("Coverage bias (from phase0_audit): DefiLlama list skews to post-2022 survivors; "
                "early-cycle dead tokens absent at the SOURCE; Binance-perp requirement is the binding "
                "selection and Vision retains delisted symbols, so exchange-side survivorship is handled; "
                "calendar-side survivorship remains and is reported, not hidden.\n")
    print("coverage report written")


if __name__ == "__main__":
    main()
