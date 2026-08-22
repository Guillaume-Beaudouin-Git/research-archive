# Forex — mostly a closed book

Almost every FX line tested here is archived. The two still open are narrower re-openings of
previously-closed families, on an explicitly new angle (per the reopening policy in root
`README.md` / `CLAUDE.md`), not a re-run of the same idea.

## Structure

| Directory | Contents |
|---|---|
| `research/active/` | `fix_reversal` — the one FX two-sided effect with a real gross signal (Ranaldo, t=3.55) but dead at retail cost (L34); `fx_intraday_deepdive` — the deepdive that established L43/L44 |
| `research/passed/` | Empty in practice (`.gitkeep`, one helper script) — no FX line has cleared RESEARCH_PASS on this repo's cost model |
| `research/archived/` | `fx_carry_em`, `fx_carry_fred`, `fx_carry_trend`, `g1_carry_conditional` (G10 carry, dead post-GFC — the 2005-07 sample carried the whole historical effect), `fx_momentum_monthly`, `cip_eoq`, `london_orb_v1`, `round_number_cascade`, `strategy_d_modified_carry` (+v2), `strategy_e_fix_flow`, `strategy_f2_asian_breakout` |
| `backtest/` | Shared harness: `amtp.py`, `costs.py`, `metrics.py`, `vol_targeting.py`, `walk_forward.py` |
| `data/` | FX-specific loaders: `binance_klines_downloader.py`, `bis_reer_loader.py`, `cot_loader.py`, `dukascopy_downloader_m5.py`, `dukascopy_loader.py`, `fred_loader.py` |

## Why this asset class is mostly closed

**L43 (strictly FX)**: intraday-flat FX is cost-dead on reversal/drift/seasonality — best observed
gross/cost ratio across the whole family is 0.36, against a 1.5 pre-flight bar. **L43 does not
transfer to indices** — indices run roughly 4× the FX gross and are killed by a different mechanism;
see `_meta/lessons_registry.md` if tempted to cite L43 outside FX.

**L23 / L23b**: a regulatory-window edge (e.g. pre-2015 WMR fixing window) is not predictive once
the window it depended on has been reformed, and an edge documented as HFT-mediated in the academic
literature is not automatically tradable at retail cost tiers (2-7 bps RT vs the 0.5-1.5 bps the
literature assumes).

**L34**: the one genuine two-sided flow-anchored effect found (Ranaldo, 2.07 bps/day gross, t=3.55)
needs sub-1-bp RT per leg to survive; measured retail cost is 2.48 bps.

Before proposing a new FX idea, check whether it fits one of these three kill mechanisms first —
most obvious FX signal families already do.
