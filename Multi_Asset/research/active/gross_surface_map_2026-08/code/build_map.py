"""Gross-surface map: instrument x exchange-local hour x horizon x predictor.

N0 SCREENING. Zero cost applied to the returns by mandate; cost only enters as a
READ-OFF THRESHOLD in the output columns. No PASS is claimed anywhere here.

Conventions
-----------
Price at clock time t = close of the H1 bar labelled [t-1h, t). So `px` is the
H1 close series re-indexed onto its own bar-END. Everything a signal reads at t
is <= t; the traded return is px[t+H]/px[t]-1. No lookahead by construction.

Clock: exchange-local WITH DST (L56), never UTC. See CLOCKS below.

Baseline (L58): every conditional cell reports the unconditional mean of the
SAME trade form (a) on the cell's own signal pool and (b) on the full pool of
that (hour, horizon). A conditional gross that is merely `side_mean x drift` is
a directional tilt, not an asymmetry.

Null (H0): a date-shifted placebo per cell -- the side series is rotated k
observations inside its own hour-subset, so its autocorrelation and its marginal
long/short balance are preserved while its alignment with the returns is
destroyed. 10 rotations per cell give an empirical null t-distribution that
carries the SAME cross-cell correlation structure as the real sweep.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

CACHE = os.environ.get(
    "GROSSMAP_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/grossmap_cache",
)
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
      "EURGBP", "EURJPY", "AUDJPY"]
IDX = ["US500", "US100", "US30", "GER40"]
MET = ["XAUUSD", "XAGUSD", "COPPER"]
NRG = ["UKOIL", "USOIL"]
INSTRUMENTS = FX + IDX + MET + NRG

# exchange clock (with its DST) + local hour at which the daily settlement halt starts
CLOCKS = {i: ("America/New_York", 17) for i in FX}
CLOCKS.update({i: ("America/New_York", 17) for i in ["US500", "US100", "US30"]})
CLOCKS["GER40"] = ("Europe/Berlin", 22)
CLOCKS.update({i: ("America/New_York", 17) for i in ["XAUUSD", "XAGUSD", "COPPER", "USOIL"]})
CLOCKS["UKOIL"] = ("Europe/London", 23)

CLASS = {**{i: "FX" for i in FX}, **{i: "index" for i in IDX},
         **{i: "metal" for i in MET}, **{i: "energy" for i in NRG}}

# Round-trip cost, bps. Sources:
#  indices  1.8  -- COST_AUDIT.md S5 "fourchette honnete [1.8 ; 2.9]", low end taken
#  XAUUSD   1.84 -- COST_AUDIT.md S3, measured (spread 0.699 + 2x0.5 slip + comm)
#  FX       1.50 -- framework.py catalogue; phase0's 1.13-1.36 is zero-inflated LOW (S2)
#  others   estimated in-file from the H1 spread column + 1.0 bps slippage, and
#           flagged UNMEASURED in the output.
COST_RT = {**{i: 1.50 for i in FX}, **{i: 1.80 for i in IDX},
           "XAUUSD": 1.84, "XAGUSD": np.nan, "COPPER": np.nan,
           "UKOIL": np.nan, "USOIL": np.nan}

HORIZONS = [1, 2, 4, 8, 24]
PREDICTORS = ["S0_LONG", "S1_MOM", "S2_RANGE", "S3_MA"]
SPLIT = pd.Timestamp("2021-01-01")
MIN_N = 200
ROTATIONS = [13, 29, 47, 71, 97, 131, 163, 197, 233, 271]
HAC_LAG = 6


# ---------------------------------------------------------------- statistics
def hac_t(x: np.ndarray, lag: int = HAC_LAG) -> tuple[float, float]:
    """(mean, Newey-West t-stat of the mean). Bartlett kernel, `lag` lags."""
    n = x.size
    if n < 30:
        return float("nan"), float("nan")
    m = x.mean()
    e = x - m
    s = float(e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - k / (lag + 1.0)) * float(e[k:] @ e[:-k]) / n
    if s <= 0:
        return m, float("nan")
    return m, m / np.sqrt(s / n)


# ---------------------------------------------------------------- data layer
def load(inst: str) -> pd.DataFrame:
    df = pd.read_parquet(f"{CACHE}/{inst}_H1.parquet")
    df.index = df.index + pd.Timedelta(hours=1)          # bar label -> bar END = clock time
    full = pd.date_range(df.index.min(), df.index.max(), freq="1h")
    df = df.reindex(full)
    tz, _ = CLOCKS[inst]
    loc = df.index.tz_localize("UTC").tz_convert(tz)
    df["lhour"] = loc.hour
    df["ldate"] = loc.date
    return df


def crosses_break(inst: str, h: int, H: int) -> bool:
    """True if a trade h -> h+H is HELD THROUGH the daily settlement halt (=> swap)."""
    b = CLOCKS[inst][1]
    return any((h + k) % 24 == b for k in range(1, H))


# ---------------------------------------------------------------- the sweep
def sweep() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, nulls = [], []
    for inst in INSTRUMENTS:
        df = load(inst)
        px = df["close"]
        logpx = np.log(px)

        # predictors, all computed on the regular grid, all info <= t
        rng_hi = px.rolling(24, min_periods=18).max()
        rng_lo = px.rolling(24, min_periods=18).min()
        pctb = (px - rng_lo) / (rng_hi - rng_lo)

        fwd = {H: (logpx.shift(-H) - logpx) * 1e4 for H in HORIZONS}
        prv = {H: (logpx - logpx.shift(H)) for H in HORIZONS}

        for h in range(24):
            at_h = df["lhour"].to_numpy() == h
            if at_h.sum() < MIN_N:
                continue
            sub = df.index[at_h]
            px_h = px.reindex(sub)
            # rolling over the OBSERVED points only: the hour-subset still carries
            # weekend NaNs, and a 20-window containing one poisons the whole MA.
            obs = px_h.dropna()
            ma20 = obs.rolling(20, min_periods=20).mean().reindex(sub)
            sig_ma = np.sign((px_h - ma20).to_numpy())
            pb = pctb.reindex(sub).to_numpy()
            sig_rng = np.where(pb >= 0.8, 1.0, np.where(pb <= 0.2, -1.0, 0.0))
            sig_rng = np.where(np.isnan(pb), np.nan, sig_rng)

            for H in HORIZONS:
                r = fwd[H].reindex(sub).to_numpy()
                sig_mom = np.sign(prv[H].reindex(sub).to_numpy())
                sides = {"S0_LONG": np.ones_like(r), "S1_MOM": sig_mom,
                         "S2_RANGE": sig_rng, "S3_MA": sig_ma}
                xbrk = crosses_break(inst, h, H)

                for pname in PREDICTORS:
                    side = sides[pname]
                    ok = np.isfinite(r) & np.isfinite(side) & (side != 0)
                    if ok.sum() < MIN_N:
                        continue
                    dates = sub[ok]
                    rr, ss = r[ok], side[ok]

                    for era, msk in (("post2021", dates >= SPLIT), ("pre2021", dates < SPLIT)):
                        if msk.sum() < MIN_N:
                            continue
                        re_, se_ = rr[msk], ss[msk]
                        yrs = (dates[msk].max() - dates[msk].min()).days / 365.25
                        g, t = hac_t(se_ * re_)
                        u, ut = hac_t(re_)                      # same pool, unconditional long
                        rows.append(dict(
                            instrument=inst, cls=CLASS[inst], era=era, lhour=h, horizon_h=H,
                            predictor=pname, n=int(msk.sum()), freq_per_yr=msk.sum() / max(yrs, 1e-9),
                            gross_bps=g, t_hac6=t,
                            side_mean=float(se_.mean()),
                            uncond_pool_bps=u, uncond_pool_t=ut,
                            explained_bps=float(se_.mean()) * u, excess_bps=g - float(se_.mean()) * u,
                            holds_through_break=xbrk,
                        ))
                        if era == "post2021" and pname != "S0_LONG":
                            for k in ROTATIONS:
                                gp, tp = hac_t(np.roll(se_, k) * re_)
                                nulls.append(dict(instrument=inst, lhour=h, horizon_h=H,
                                                  predictor=pname, k=k, gross_bps=gp, t_hac6=tp))
        print(f"  swept {inst}", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(nulls)


# ---------------------------------------------------------------- cost layer
def measured_costs() -> pd.DataFrame:
    """Post-2021 spread diagnostic, restricted to bars the map can actually trade."""
    out = []
    for inst in INSTRUMENTS:
        df = pd.read_parquet(f"{CACHE}/{inst}_H1.parquet")
        df = df[df.index >= SPLIT]
        px = df["close"]
        sp_px = df["spread_med"] / px * 1e4 if CLASS[inst] != "FX" else np.nan
        out.append(dict(
            instrument=inst, cls=CLASS[inst],
            spread_zero_frac=float(df["spread_zero_frac"].mean()),
            spread_med_raw=float(df["spread_med"].median()),
            spread_med_bps_est=float(np.nanmedian(sp_px)) if CLASS[inst] != "FX" else np.nan,
            cost_rt_used=COST_RT[inst],
        ))
    return pd.DataFrame(out)


def main() -> None:
    cost = measured_costs()
    # fill the unmeasured instruments from their own spread + 1.0 bps slippage
    est = cost.set_index("instrument")
    for inst in INSTRUMENTS:
        if not np.isfinite(COST_RT[inst]):
            COST_RT[inst] = round(float(est.loc[inst, "spread_med_bps_est"]) + 1.0, 2)
    cost["cost_rt_used"] = [COST_RT[i] for i in cost["instrument"]]
    cost["cost_measured_here"] = [not np.isfinite(v) for v in
                                  [1.5 if CLASS[i] == "FX" else (1.8 if CLASS[i] == "index" else
                                   (1.84 if i == "XAUUSD" else np.nan)) for i in cost["instrument"]]]
    cost.to_csv(f"{OUT}/cost_reference.csv", index=False)
    print(cost.to_string(index=False))

    cells, nulls = sweep()
    cells["cost_rt_bps"] = cells["instrument"].map(COST_RT)
    cells["gate_3x_bps"] = 3.0 * cells["cost_rt_bps"]
    cells["passes_cost_gate"] = cells["gross_bps"] > cells["gate_3x_bps"]
    cells["gross_over_cost"] = cells["gross_bps"] / cells["cost_rt_bps"]
    cells.to_csv(f"{OUT}/cells_all.csv", index=False)
    nulls.to_csv(f"{OUT}/null_placebo_t.csv", index=False)
    print(f"\ncells={len(cells)}  nulls={len(nulls)}")


if __name__ == "__main__":
    main()
