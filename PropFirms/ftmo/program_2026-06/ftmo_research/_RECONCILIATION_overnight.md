# Reconciliation — the overnight harvester vs. "FTMO confirmé-clos"
*Created 2026-06-03 (Cowork session) to reconcile `NQ_overnight_metrics/` (which reported p(funded) 82-88%) against `_CANONICAL_STATE.md` (which declares FTMO closed). Per the canonical rule: reconcile before continuing.*

## The apparent contradiction
- `NQ_overnight_metrics/` dossier: MA200-gated overnight harvester on NQ → **p(funded) 82-88%**, "deployable ~70-80%".
- `_CANONICAL_STATE.md`: **FTMO confirmé-clos**, best robust edge Sharpe 0.34, no retail alpha accessible.

These look incompatible. They are not — the 82-88% is a **coût idéalisé** number (the exact trap the canonical doc warns about in §4/§5, L33). It is reconciled below and the canonical verdict **holds**.

## The mechanism (same L33 as the ORB)
The overnight harvester **holds a long index position every night for years** → it pays the **overnight swap every single night**. The dossier's net was computed at **2 bps/night = spread only, swap NOT included** (stated as open Check 1). The canonical doc §5 shows the broker **long swap is large and asymmetric (−662.4 long vs +28.58 short)** — and for a held-overnight strategy this is the *dominant* cost, exactly the line item that is irrelevant for the (flat-overnight) ORB.

So the harvester's true cost stack = **daily round-trip spread (~2 bps) + overnight long swap**. Its gross edge is only **+5.59 bps/night**, so it has almost no room.

## The grid (mirrors the ORB cost grid §4) — re-run on clean NQ 2010-2026
Gross mean (traded nights) = **+5.59 bps/night** → breakeven total per-night cost = **5.59 bps**.

| Total cost/night (spread+swap) | net bps/night | p(funded) 0.5× / bust | p(funded) 0.75× / bust | status |
|---|---:|---:|---:|---|
| 2 bps (idealized, swap = 0) | +3.59 | **88% / 0%** | **82% / 9%** | the dossier number |
| 3 bps (swap ≈ 1) | +2.59 | 88% / 0% | 62% / 28% | holding |
| 4 bps (swap ≈ 2) | +1.59 | 80% / 0% | 58% / 32% | degrading |
| **5 bps (swap ≈ 3)** | **+0.59** | **34% / 36%** | **31% / 57%** | **collapsing** |
| **6 bps (swap ≈ 4)** | **−0.41** | **8% / 49%** | **12% / 69%** | **sign-flipped → dead** |
| 7 bps (swap ≈ 5) | −1.41 | 1% / 59% | 8% / 71% | dead |

## Conclusion
The harvester needs **total per-night cost < ~4 bps** (i.e. swap < ~2 bps/night) to keep p(funded) ≥ 80% at 0.5×. The canonical doc's estimated real US100 CFD profile (6-10 bps, commission 0 + floating spread + asymmetric long swap −662.4) puts it **firmly in the collapse zone (8-34% funded)**. Net sign-flips negative around 6 bps → on a symmetric barrier a negative-drift never converges → **drifts to bust**, exactly like the ORB at 3 bps.

**The overnight harvester is NOT an exception to "FTMO confirmé-clos."** It is the *same* idealized-cost mirage as the ORB — alive only on paper at an unmeasured low cost, dead at the real instrument cost. The ORB is killed by **spread**; the harvester is killed by **swap**. Same L33 lesson, same NO-GO.

## What this means for the dossiers
- `NQ_overnight_metrics/STRATEGY_DOSSIER*` : the 82-88% / "deployable 70-80%" is **conditional on swap < ~2 bps/night**, which is almost certainly false for a long index CFD. **Treat as idealized-cost, not deployable.** A reconciliation banner has been added to the dossier `.md` (the `.docx` is stale on this single point — rebuild only if needed; per canonical §8 do not spend cycles).
- The **same open measurement** (canonical §5: log the real US100 cost on demo) closes the loop for BOTH strategies: spread for the ORB, spread+swap for the harvester. Expected result: confirms the NO-GO for both.

*Reproduce: `cd NQ_overnight_metrics && python3 -c "import overnight_harvester as oh; ..."` sweeping total cost (the grid above), or `python3 overnight_harvester.py --data <nq> --cost-bps 6 --out ./swap6`.*
