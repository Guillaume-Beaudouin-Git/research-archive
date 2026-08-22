# Multi_Asset — the FTMO research trunk

This is where almost all research feeding the live FTMO book happens. Since 2026-07 it holds the
bulk of the studies behind lessons L51-L60 in `_meta/lessons_registry.md` — vehicle economics,
session-clock corrections, overnight futures mechanics, and the closures that shaped the current
book (two overnight index legs + one intraday breakout).

## Structure

`research/active/` holds ~35 dated study folders (`<topic>_2026-07` or `_2026-08`), each following
the pre-registration → results → verdict cycle described in `docs/RESEARCH_METHOD.md`. A few, to
orient a first read:

| Study | What it established |
|---|---|
| `month_end_vehicle_2026-07/` | Found the ZN month-end effect works on IBKR (personal account), not on any propfirm vehicle — the source of L51-L53 (a futures trading day is not a calendar day; if the minimum lot's margin fits in personal capital, the propfirm adds nothing) |
| `overnight_futures_2026-07/` | Session-clock corrections for the overnight gold/silver/WTI drift (L56, L57) |
| `gap_pattern_rehab_2026-07/` | Re-priced exits on the stop-entry family, found zero-range settlement-print bars contaminating some series (L59, L60) |
| `regime_overlay_ftmo_2026-07/` | Corrected condition for when a regime overlay can help at all (L54) |
| `cost_denominator_2026-07/` | The cost audit behind `COST_AUDIT.md` — measured US100 RT cost (1.045 bps) vs. the 2.2 bps hardcoded in the pipeline, and the gold cost table's 1.9× over-penalty |
| `treasury_auction_2026-07/` | Found a matched placebo that produced a false PASS because its baseline pool was itself biased (L58) |
| `two_sided_axis_2026-08/` | Closed the two-sided (long+short) axis for the deployed book — the swap differential nets to ~89% of the risk-free rate, and shorting replaces a FREE flat position, raising cost everywhere it was tried |
| `gold_cpi_eve_2026-08/` | Full worked pre-registration → rejection cycle; used as the example in `docs/RESEARCH_METHOD.md` |
| `wall_economics_2026-08/`, `wall_decision_2026-08/` | The funded-account "time wall" economics (holding-period breakeven vs. simulated payout) |

`research/archived/` holds closed lines with a narrower footprint: `mtf_a1_tsmom` (multi-horizon
TSMOM, falsified 2026-06-05), `network_momentum` (graph-learning momentum features, feasibility
failed), `oxfordstrat_109_audit` (an audit pass over the "109 strategies" oxfordstrat catalogue —
partial re-audit, not exhaustive; see its own files for scope).

## Before starting a new study here

Check `_meta/lessons_registry.md` (especially L51-L60, the most recently graved) before opening a
new dossier — a large share of the obvious angles on overnight futures, mean-reversion intraday
(closed: ~1,526 cells tested, zero survivors), and calendar-event conditioning have already been
tested here. **`_meta/research_active.md` predates this entire programme** (verified 2026-05-30,
only lightly restructured since) and does not index anything under this directory dated 2026-07 or
later — the table above and a directory listing are the more current sources for what is open here.
