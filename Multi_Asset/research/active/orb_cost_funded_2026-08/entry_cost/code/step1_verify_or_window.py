"""Volet A / étape 1 — vérification empirique du fuseau et de la fenêtre OR.

On ne suppose PAS 09:30-10:00 ET (L52/L56). On balaie une grille de fenêtres
candidates, dans plusieurs fuseaux, et on retient celle qui reproduit au tick
`or_hi`/`or_lo` du ledger.

Lecture seule sur le ledger et sur le M1 canonique.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
LEDGER = REPO / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet"
M1 = REPO / "data/raw/NQ_1min_databento_2010-2026.parquet"
OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

TICK = 0.25


def load_m1() -> pd.DataFrame:
    df = pd.read_parquet(M1, columns=["open", "high", "low", "close", "volume", "is_rth"])
    df.index = pd.DatetimeIndex(df.index)
    return df


def main() -> None:
    led = pd.read_parquet(LEDGER)
    m1 = load_m1()

    # horloge d'échange : America/New_York (avec son propre DST)
    et = m1.index.tz_convert("America/New_York")
    m1 = m1.assign(
        et_date=et.normalize().tz_localize(None),
        et_min=et.hour * 60 + et.minute,
        utc_min=m1.index.hour * 60 + m1.index.minute,
    )

    # échantillon stratifié : 40 dates par année civile (ou tout si moins)
    rng = np.random.default_rng(7)
    samp = (
        led.index.to_series()
        .groupby(led.index.year)
        .apply(lambda s: s.sample(min(len(s), 40), random_state=7))
        .droplevel(0)
    )
    samp = pd.DatetimeIndex(sorted(samp.values))

    led_s = led.loc[samp, ["or_hi", "or_lo"]]

    rows = []
    # grille : début de fenêtre (minutes depuis minuit dans le fuseau testé), durée
    starts = list(range(8 * 60, 11 * 60 + 1, 5))
    durations = [5, 10, 15, 20, 25, 30, 45, 60]

    for clock in ("ET", "UTC"):
        key_date = "et_date" if clock == "ET" else None
        if clock == "ET":
            day = m1["et_date"]
            minute = m1["et_min"]
        else:
            day = m1.index.normalize().tz_localize(None).to_series(index=m1.index)
            minute = m1["utc_min"]
        base = pd.DataFrame(
            {"day": day.values, "minute": minute.values,
             "high": m1["high"].values, "low": m1["low"].values},
            index=m1.index,
        )
        base = base[base["day"].isin(samp)]
        for st, dur in itertools.product(starts, durations):
            w = base[(base["minute"] >= st) & (base["minute"] < st + dur)]
            if w.empty:
                continue
            g = w.groupby("day").agg(hi=("high", "max"), lo=("low", "min"))
            j = led_s.join(g, how="left")
            ok = (
                (np.abs(j["hi"] - j["or_hi"]) < TICK / 2)
                & (np.abs(j["lo"] - j["or_lo"]) < TICK / 2)
            )
            rows.append(
                dict(clock=clock, start_min=st, dur=dur,
                     start=f"{st//60:02d}:{st%60:02d}",
                     n=len(j), n_exact=int(ok.sum()), frac_exact=float(ok.mean()))
            )

    res = pd.DataFrame(rows).sort_values("frac_exact", ascending=False)
    res.to_csv(OUT / "step1_or_window_grid.csv", index=False)
    print(res.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
