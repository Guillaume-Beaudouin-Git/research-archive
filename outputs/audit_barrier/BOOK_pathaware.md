# VOLET B — Portage path-aware sur le book (le seul actif de valeur du programme)

**Auditeur ≠ auteur · 2026-07-13 · offline, aucun GO demandé.** Objet : le book porte du flottant intraday
tous les jours (Nightly/J1/Or/micro-ORB) ; le sim qui sert le triplet acté vérifie-t-il la barrière sur les
**closes M5** ou les **lows intra-barre** ? C'est le locus de risque #1 du projet.

## B.1 — Quel moteur, et sur quoi vérifie-t-il la barrière ? (SURFACÉ depuis le SOURCE, pas deviné)
Le triplet acté **(71,4 % , ~3,2 att , +$740)** à vm14 est produit par le cleanroom `engine_v22`
(`data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`). **Vérifié ligne à ligne :**
- `load_market` (L50-87) charge `sim_m5_repaired.parquet` = **un seul prix par barre M5 par jambe = le close** (ffill).
- `run_phase` (L258-275) marque l'équité sur ces closes et teste `hit_bust` (floor −5 %/j), `hit_brk`
  (breaker `lim_eff + 0,30·budget` ≈ 9650) et `day_min_eq` **uniquement sur les closes M5**.
→ **Le moteur du triplet acté est M5-CLOSE-ONLY.** Il ne voit jamais le low intra-barre. **MAIS** il est
déjà sur **grille M5**, PAS « EOD/net-daily » (point décisif pour §B, reconciliation ci-dessous).

**Le « low-check » de l'étude real-metrics EST ce fix** (vérifié dans `lowcheck_engine.py`, clone
bit-identique en `mode="close"`) : il bascule **seulement la détection de breach** —
- **floor FTMO** → **low intra-barre adverse** (liquidation CONTINUE ; réplique les breaches réels 02-03/07 où le monitor FTMO a battu le breaker M5 discret) ;
- **breaker EA** → **close M5 discret** (l'EA ne peut agir que sur la grille M5).
C'est le « close→low » fait **correctement** (distinction floor-continu / breaker-discret — subtilité que le rapport #1 rate).

## B.2/B.3 — Triplet AVANT / APRÈS + incertitude
Port exécuté par la session `real-book-metrics-lowcheck` (indépendamment auditée, author≠auditor =
**CONFIRM-WITH-CAVEATS** ; tout re-dérivé du brut). **Vérifications indépendantes de MA part (cette session) :**
(1) moteur close-only (source, ci-dessus) ; (2) sémantique lowcheck floor-low/breaker-close (source) ;
(3) **magnitude des offsets intra-M5** re-calculée par moi sur `lohi_m5_paris.parquet` :
median **XAU 2,90 / USDJPY 1,49 / US100 3,40 / GER40 3,68 bps** (p99 11-30), lo<close sur 100 % des barres,
couverture XAU 94 % / JPY 100 % — **identique au claim audité (1,5-3,7 bps)**. Ancres reproduisant le cité **exact** :
SWING OFF/close **330/462 = 71,4286 %**, EV **+$739,72** ; compte 3 **322/462 = 69,6970 %**, +$677,70.

| triplet **(p(funded 3 m), attempts moyens, EV/campagne)** | valeur |
|---|---|
| **AVANT — close-only (cité, vm14)** | **(71,4 % , ~3,2 , +$740)** |
| **APRÈS — path-aware (compte 3 = floor-low + breaker-close + gate J1, vm14)** | **(69,7 % , 3,29 , +$678)** |
| Δ low-check SEUL (SWING) | **−1,30 pt** [CI90 −4,11 ; +1,52] |
| Δ combiné (gate+low) | **−1,73 pt** ; ΔEV **−$62** |
| borne pessimiste (low_both, breaker aussi adverse) | −3,9 pt |

**« Deflated Sharpe » n'est pas l'instrument** pour un delta de p(pass) (ce n'est pas un ratio de Sharpe).
L'énoncé multiple-testing-conscient correct = la **CI90 par block-bootstrap** (apparié par cohorte, N_eff 73)
+ **McNemar p=0,327** → **le delta n'est PAS significatif** ; le point-estimate −1,3 pt est petit et son CI enjambe 0.

**Données jusqu'à aujourd'hui :** le sim s'arrête au **2026-06-05** ; le triplet compte-3 ancre les campagnes au
06/07. Aujourd'hui = 13/07 → +5 semaines non modélisées = **≤ 4 cohortes** (dernier start complétable 06/03 vu le mur
91 j), toutes en régime USDJPY ≥ 160 où le gate garde J1 **flat** (flash-insensible). **Impact pooled < bruit (4/462).**
Fetch → 07-13 **non exécuté** (indices Dukascopy fragiles + valeur marginale nulle sur le triplet ; cohérent avec le
raisonnement documenté de la session realmetrics). **Je ne re-run PAS un 4ᵉ sim redondant** (déjà triple-vérifié : port + son audit indépendant + mes 3 vérifs source/offset) — ce serait conclure du théâtre, pas de la donnée.

## B.4 — Le « 57 % des funded bustent dans l'année » (rapport #2 §7.1)
- **NON SOURCÉ** dans le rapport #2 (énoncé en caveat, sans citation ; sert à justifier E[funded]=$913 « porté par les survivants »). Pas un chiffre FTMO-publié identifiable.
- **Contredit par le sim path-aware DU PROJET** (realmetrics) : bust funded intra-barre = **14 % (dom-leg) à 30 % (all-legs)** sur 191 chemins funded (median life 169 j, 93 % conservent des retraits bankés, dégât VAL 1438→1425). Soit **~2-4× plus BAS** que le 57 % supposé.
- Conséquence : si le vrai bust funded est 14-30 %, **E[funded] est SOUS-estimé** par le rapport #2 (57 % trop pessimiste) → l'EV du regime-rotation serait plus HAUTE que $913… ce qui **ne le sauve pas** (DSR=0,00 tue quel que soit E[funded]). Le 57 % est un aléa non sourcé, pas un input fiable.
- **Le vrai tail funded** (là où le path-aware mord) : 14-30 % vs 3 % au M5-close (×4,7-×10), **vm-sensible** (funded = vm1 plein, marge SWING ne bind jamais), **porté par l'OR** (XAU survit à la borne dom-leg), dégât $ **borné** par le banking.

## Conclusion Volet B — vm14 tient au challenge ; le vrai chantier est funded (déjà ouvert)
- Le rapport #1 (§4.2) qualifie le sim du book d'« EOD-approx (net daily) » et en tire **« 34-49 pts »** de survie surestimée.
  **FAUX pour le book** : le moteur est **déjà M5-grid** (la correction EOD→M5-grid est *déjà appliquée*). Le résiduel réel
  (M5-close → low intra-M5) = **−1,3 pt** (challenge). Le « 34-49 pts » est la démo EOD-vs-path du *propre moteur du sleeve BTC*,
  **non transférable** au book → **surestimation ×25-35**.
- **vm14 :** brief = « si delta significatif → ré-examiner vm14 ». Au **challenge**, Δ = −1,3 pt, CI⊃0, McNemar 0,33 → **NS → vm14 TIENT.**
- Le seul angle mort réel = le **tail intra-barre FUNDED** (14-30 %, porté OR, $-borné), **signalé non tranché** par realmetrics = chantier séparé. **Aucune stratégie BTC n'est requise pour l'aborder ; le sleeve month-end/regime n'y change rien.**
