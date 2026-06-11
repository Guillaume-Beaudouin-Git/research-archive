# v2.2.2 — re-fit container sous marge SWING (pré-enregistré, 2026-06-11)

## VERDICT (règle de décision verbatim appliquée)
**NULL — l'arm A (vm14 + clip proportionnel dynamique) RESTE.** Aucun arm ne le bat
significativement sur l'EV (CI90 appariés ⊃ 0 partout). Meilleur challenger : C_vm10,
EV **+$750 vs +$740** (Δ +10.6 [−87.3;+105.0] CI90 — bruit), p91 70.1 vs 71.4 (Δ −1.30
[−7.1;+4.3] ns). **Explication (décomposition pré-enregistrée)** : le pass PAR TENTATIVE
sans horloge s'ordonne à l'INVERSE de la taille (gambler's ruin : B×0.24 50.4 % > C6
46.3 > C8 43.9 > C10 43.6 > D 42.2 > A 41.7) mais l'horloge 91j domine et inverse tout
(p91 : A 71.4 > C10 70.1 > C8 66.0 > D 65.4 > C6 62.1 > B 47.4). Le clip dynamique est
déjà l'optimum du couple : taille maximale faisable à chaque instant = vitesse maximale
contre NOTRE wall, et le cap encaisse la sécurité. Adoption v2.3 : AUCUNE (null documenté).
*Tout conditionnel à l'hypothèse marge Swing officielle 1:30/1:15/1:9 — lecture
`margin_rate_live` serveur Swing PENDANTE (gate déploiement v2.2.1).*

## Gates
Policy 87.01 ✓ (87.0 ±0.5) · Swing-enforced 71.43 ✓ (71.4 ±0.5) — reproduction exacte
baseline 1947163. Identité de caisse : assertions moteur armées, **0 levée** sur 6 arms
(~8 800 tentatives). Costs = M_swc du re-cost (swaps mesurés + commissions), MRATE = Swing.

## Arms (wall 91j, retries ; CI95 block-bootstrap ; N_eff 63-80 ; VAL $1,438)
| arm | vm_eff | p91 (IS/OOS) | CI95 | p182 | p270 | att | t_med | **pass/att P1 no-clock** | EV91 | EV91@VAL1381 |
|---|---|---|---|---|---|---|---|---|---|---|
| **A vm14+clip** | 14→clip | **71.43** (64.8/78.2) | [62.8;79.4] | 92.2 | 96.5 | 2.99 | 38.5j | 41.69 | **+$740** | +$699 |
| C_vm10 | 10→clip | 70.13 (60.5/79.9) | [61.3;78.8] | 89.0 | 95.7 | 2.69 | 34j | 43.61 | +$750 | +$711 |
| C_vm8 | 8→clip | 66.02 | [56.9;74.7] | 86.8 | 97.2 | 2.67 | 36j | 43.86 | +$693 | +$656 |
| D vm14+J1half | 14→clip | 65.37 | [56.5;74.0] | 89.0 | 94.4 | 2.83 | 36j | 42.17 | +$668 | +$631 |
| C_vm6 | 6→clip | 62.12 | [52.6;71.2] | 88.5 | 95.7 | 2.58 | 42j | 46.27 | +$645 | +$610 |
| B ×0.24 statique | 3.36 | 47.40 | [37.9;57.1] | 72.7 | 84.8 | 2.14 | 44j | **50.36** | +$476 | +$449 |

## Tornado — deltas APPARIÉS vs A (p91 pt ; EV $ ; CI90)
```
C_vm10   Δp −1.30 [−7.1;+4.3] ns   ΔEV  +10.6 [ −87;+105] ns   ▌
C_vm8    Δp −5.41 [−11.5;+1.1] ns  ΔEV  −46.6 [−150; +58] ns   ▐▌
D J1half Δp −6.06 [−12.6;+0.2] ns  ΔEV  −71.8 [−173; +30] ns   ▐▌
C_vm6    Δp −9.31 [−16.2;−2.0] SIG ΔEV  −94.7 [−218; +30] ns   ▐█
B ×0.24  Δp −24.0 [−31.4;−16.9] SIG ΔEV −263.9 [−382;−145] SIG ▐███
```
Plateau vm∈[10,14] : le cap fait converger les books (bind 42.8 % vs 56.0 %, profondeur
de clip 0.42 vs 0.46 → tailles effectives quasi identiques) — le container n'est PAS
knife-edge en vm sous Swing. B (le « fix naïf ») est le pire des mondes : il abandonne
l'optionnalité du clip (plein régime quand le book est léger) sans gagner contre l'horloge.

## D (J1 relief) — le loo-nontransfer testé, KEEP de J1 confirmé même sous Swing
Halver J1 libère ~30 pt de marge (61→30 % d'equity à pleine charge) mais retire plus de
drift que le clip n'en rachète : le re-scaling profite à l'or (1:9, marge la plus CHÈRE
par $ de notionnel). Δp −6.06 [−12.6;+0.2], ΔEV −71.8 — direction NÉGATIVE. J1 = la
source de drift la moins chère en marge (1:30) ; la couper est du margin-relief inversé.

## Modes d'échec & interactions (REPORTÉS, pas retunés)
- **Abandon = mode d'échec dominant et INVARIANT** : 32.8-36.0 % des tentatives sur TOUS
  les arms (zombie 5j près du floor) ; bust_daily 7.3-9.8 % (C_vm10 7.7 < A 9.8 —
  contrainte « non dégradé » ✓) ; bust_floor 3.3-6.4 % ; timeouts par tentative ~0 %
  (l'horloge tue au niveau CAMPAGNE, entre tentatives — pas dans la tentative).
- **Pace** (tuné vm14 policy) : ne sature JAMAIS à 2.0 (0 % sur tous les arms) ; clampe
  à 0.8 (avance sur le glide) 21.7-23.6 % des jours ; à bas vm_eff il reste fonctionnel.
  Indice (non isolé — le mix de régimes des retries diffère) : P1 en-funnel 45.3 vs
  41.7 no-clock-pace-off, +3.6 pt cohérents avec un pace qui aide sous l'horloge.
- **Glide** actif 3.6-5.7 % des rebalances seulement (prog>0.8 rare sous Swing).
- No-clock : 47 starts censurés (<400 jours de données restants), exclus du dénominateur.

## FUNDED check (une ligne)
vm1.0 + ORB 0.25 % taper sous marge Swing : marge p50 7 % / p99 **24 %** / bind **0.00 %**
→ **aucun re-fit du funded requis** (attendu ~28 % ✓ confirmé sous le cap).

## E — INFO COMITÉ (wall = décision économique nôtre, PAS une adoption)
Arm A à wall étendu : p(funded) 91j **71.4** → 182j **92.2** → 270j **96.5** ;
EV **+$740 → +$980** (+$240), attempts 2.99 → 3.60, mais EV/jour **8.1 → 5.4 $/j**
(−34 %). (C_vm10 @182 : 89.0, +$962.) L'extension du wall achète du p(pass) et de l'EV
absolu au prix de la cadence de campagne — arbitrage fees/temps pour le comité, hors
périmètre d'adoption ici.

## Artefacts
`run_swing_fit.py` (gates → arms → appariés → funded) · `tables/arms_summary.csv` ·
`tables/tornado_paired_vs_A.csv` · `tables/arm_*_{91,182,270,noclock}.csv` ·
`summary.json` · `swing_fit_run.log`. Baseline READ-ONLY 1947163 ; AUCUNE édition de
spec (toute adoption aurait été LE changement gelé d'un re-run v2.3 — sans objet : null).
