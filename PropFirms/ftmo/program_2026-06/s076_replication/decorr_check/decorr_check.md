# A.1 decorrelation re-check — Ross Hook (independent replication) vs TSMOM-deployed

**Ross Hook** = `research/s076_replication/results/mtm_deployable.csv` col `ret` — deployable MTM (indices+commodity+crypto, ex-FX),
independent replication, never through ftmo_lab; EET server-day daily returns.
**TSMOM deployed** = `data/ftmo_research/tsmom/chosen_returns.csv` col `0` — the exact series Cowork loaded (`session_cowork/phase2_3.py:46`).

| metric | all common days | both-active (no flat day either side) |
|---|---|---|
| Pearson | 0.2616 | **0.2988** |
| Spearman | 0.227 | **0.279** |
| n days | 5769 | 3920 |
| window | 2007-01-03..2026-05-28 | 2007-02-08..2026-05-28 |

Date-convention diagnostic (both-active, ±1-day shift of Ross Hook): rh−1d Pearson=-0.046, rh+1d=-0.0229
(same-date alignment 0.2988 is the strongest → conventions match).

**Verdict:** ~0.25 CONFIRMED (A.1 sealed on real data): independent-replication Ross-Hook vs TSMOM-deployed Pearson=0.2988 / Spearman=0.279 (both-active n=3920, 2007-02-08..2026-05-28) ≈ Cowork's +0.27.

*Both series are daily returns (not prices); strict inner-join on date; "both-active" drops days strictly flat
on either side (no position) — the window comparable to Cowork's 2018-2026 TSMOM_PROXY overlap.*
