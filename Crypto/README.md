# Crypto — TSMOM, delta-neutral carry, and closed cross-sectional lines

## Live

`live/strategy_a_tsmom` and `live/strategy_b_carry` are symlinks into `strategies/tsmom_v2_propfirm`
and `strategies/delta_neutral` (the actual deployed code lives under root `strategies/`, not here).
Current status of both (frozen A, testnet B) is in root `CLAUDE.md` §Live strategies snapshot — not
duplicated here to avoid the two going out of sync.

## Structure

| Directory | Contents |
|---|---|
| `research/active/` | Open lines: `token_unlocks`, `vrp_short_gamma`, `session_I_crypto_flows`, `pairs_btceth_D`, `ftmo_twoSided_makeOrBreak` |
| `research/passed/` | Studies that cleared RESEARCH_PASS: `tsmom_v3` (symlink to the live code), `halving_cycle`, `hmm_transitions`, `obv_signal`, `vpt_cmf` |
| `research/archived/` | Closed lines, organized by family: `carry/`, `mean_reversion/`, `ml/`, `momentum/`, `options/`, `patterns/`, `regime/`, `sentiment/`, `etf_regime_overlay/`, `h31_cs_fs_dn/`, `other/` |
| `research/archived/_frozen/strategy_a_propr_2026-05-30/` | Frozen code+state snapshot of Strategy A as it stood on Propr before that venue was abandoned — kept for reproducibility, not for reuse |
| `research/_meta/` | Cross-cutting notes: the crypto alpha landscape survey, the L11 (β-dominance) writeup, a documentation inventory, a sanity-check log |

## What is closed, and why

Long-only cross-sectional crypto is β-dominated regardless of information coefficient (L11,
`_meta/lessons_registry.md`) — the only way out of that ceiling is delta-neutral construction, which
is what Strategy B is. Sentiment-derived signals (Fear & Greed velocity, Wikipedia attention) turned
out to be momentum proxies with null incremental IC (L17/L18) — that branch is closed, not merely
paused; see `research/archived/other/wav_h3/` and `research/_meta/` for the taxonomy that closed it.
Weekly TSMOM two-sided on CFD is closed on three simultaneous axes (L45): the short leg is not
significant even at zero swap, the long leg duplicates Strategy A, and crypto swap on CFD erases the
edge regardless.

Before proposing a new crypto hypothesis, check `research_history.md` (repo root) and
`research/_meta/underexplored_families_2026-05-28.md` — a large fraction of the obvious signal space
here has already been tested and killed.
