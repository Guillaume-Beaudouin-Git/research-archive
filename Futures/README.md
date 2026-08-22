# Futures — NQ opening momentum and the CME/CFD boundary

## Live infrastructure

`live/strategy_c_live/` is the **canonical** live infra for Strategy C (NQ opening momentum) — do
not create a parallel folder for it. `live/strategy_c_paper/` holds pre-existing paper-trade log
infrastructure only (`log_trade.py`, `paper_trade_log.csv`), not a second live path.

`live/orb_floor_ftmo/` is a **rejected** deployment attempt (US100 CFD ORB + floor-taper via an
FTMO 2-step challenge, June 2026): its own `DEPLOYMENT.md` states the verdict plainly — NO-GO at
realistic CFD cost (p(funded) 3.6% at 6 bps RT, 0% at 8+ bps, and the ORB triggers precisely inside
the 09:30 ET open auction where spread is widest). Kept as a record of a killed vehicle attempt, not
as active infra. It predates and is unrelated to the ORB leg that is part of the *currently live*
book in `ftmo_live/` (a different instrument set and cost regime — see `docs/ARCHITECTURE.md`).

Strategy C itself was cancelled as a Tradeify vehicle 2026-06-10 (FTMO does not support CME
futures) — code and infra kept, reusable if a futures-compatible propfirm vehicle reopens (see
`CLAUDE.md` §Portfolio context on the 2026-07-30 reopening of the "futures firms" freeze).

## Structure

| Directory | Contents |
|---|---|
| `research/active/` | `nq_intraday` (Strategy C research), `strategy_d` (D3+D5 portfolio candidate), `voie_b_ftmo` |
| `research/passed/` | Empty (`.gitkeep` only) |
| `research/archived/` | `nq_intraday_vwap` (N=19, insufficient sample), `orb_ivb_nq` |

## Re-baseline warning

The historical Strategy C Sharpe of 1.52 (Kaggle data, $19 RT slippage, 2022-2025 window) is
**superseded**. The 2026-06-07 re-baseline on Databento data (2014-2026, $29 RT slippage per L19)
gives Sharpe **0.41** full-sample / 0.69 on the Kaggle window, MaxDD -53.9%, N=765 — below
PROPFIRM_PASS. See `Futures/research/active/nq_intraday/results.json` and root `CLAUDE.md` for the
current numbers; do not cite the 1.52 figure without this context.
