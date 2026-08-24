# ÉTUDE — Améliorations overnight-drift CIBLÉES FTMO (4 pistes)

**Date :** 2026-06-20 · **Worktree :** `../Algo_claude_overnight_improve` · **Branche :** `claude/overnight-ftmo-improve`
**Pré-registration :** `PREREGISTRATION.md` (committée AVANT résultats, commit `259ed1a`)
**Cadre :** RECHERCHE PURE, FTMO-only (pas le Sharpe absolu), lecture seule live, AUCUN déploiement.

---

## VERDICT GLOBAL — aucune piste ne débloque l'overnight-drift pour FTMO ; la famille reste inadaptée aux DEUX étages

Les 3 leviers d'amélioration testés **attaquent chacun une propriété qui EST l'edge** → aucun n'aide.
Le critère FTMO (drawdown cumulé funded OU vitesse challenge), pas le Sharpe, tranche net :

| Piste | Levier (axe FTMO visé) | Résultat clé | Seuil pré-enregistré | Verdict |
|---|---|---|---|--:|
| **P0** | edge vivant/mort | silver + soybean **VIVANTS** (silver décline) | — | pas de clôture |
| **P1** | overlay régime gold (drawdown funded ↓) | funded Δ −50.3→**−40.8 pt** ; challenge p_pass 3.9→**0.0 %** ; Sharpe 1.01→0.88 ; maxDD −15.9→−15.4 | Δsurvie ≥ −3 pt | **ÉCHEC** |
| **P2** | spread silver−β·gold (décorrélation funded) | corr 0.02 ✓ MAIS **Sharpe −0.99**, funded Δ **−81.7 pt** | Δ ≥ −3 pt & corr<0.3 | **ÉCHEC** |
| **P3** | sortie 05:00 (DD ↓ + vitesse ↑) | Sharpe 1.01→**0.39** (gold)/0.61→0.52 (WTI) ; low à peine ↓ ; Δsurvie & p_pass PIRES | Sharpe ≥90% & DD↓ | **ÉCHEC** |

**Le « pourquoi » synthétique** : l'overnight-drift est un edge **réel, lent, pleine-vol, directionnel commun,
distribué sur toute la fenêtre**. Les 3 améliorations naturelles retirent chacune une de ces propriétés —
qui sont précisément l'edge : (P1) couper la vol aide la survie funded **+9.5 pt** mais tue la vitesse
challenge ; (P2) hedger le facteur commun **enlève l'edge** (le facteur directionnel commun EST l'edge,
pas une nuisance) ; (P3) raccourcir la fenêtre **enlève l'edge** (il est distribué sur les 8 h). La famille
reste inadaptée aux deux étages FTMO. Confirme les REJET solo/panier antérieurs.

**Référence (canonique FUNDED_WINDOWS) : book_only survive252 = 97.9 %.** L'edge gold lui-même est réel
(DSR cumul-famille n_trials=160 = **0.905**) — mais **non-améliorable pour FTMO**.

---

## P0 — Edge vivant ou mourant ? (decay test SILVER + SOYBEAN)
Sur `win_w` (edge brut fenêtre), tout l'historique :

| | full Sharpe (t_HAC) | pré-split | post-split (t_HAC) | recent-2y Sharpe (CI90) | verdict |
|---|--:|--:|--:|--:|--:|
| **SILVER** (2014→, split 2020) | 1.12 (3.58) | 2.12 | **0.67 (1.62)** | 0.82 [**−0.33**, 1.86] | **VIVANT** (mais déclin net) |
| **SOYBEAN** (2018→, split 2022) | 2.52 (6.84) | 3.26 | 1.95 (3.87) | 1.34 [+0.18, +2.42] | **VIVANT** |

Per la règle figée (MORT si post-t<1.5 OU recent-CI entièrement ≤0) : **aucun n'est clos**. Silver passe
de justesse (post-t 1.62>1.5, recent-CI pierce 0) — **VIVANT mais en décroissance** (Sharpe 2.12→0.67,
recent non-significatif) ; soybean reste robustement significatif. Piste 2 procède (silver non-mort), décline noté.

## P1 (la principale) — Overlay régime gold, signal EXOGÈNE DTWEXBGS
Spec figée : trade gold seulement si variation 63 j DTWEXBGS ≤ 0 (USD non-appréciant), flat sinon (causal).
Le gate est ON **51.7 %** des jours.

| | Sharpe | maxDD | funded Δsurvie (K=1) | funded Δsurvie (K=2) | challenge p_pass (K=2) |
|---|--:|--:|--:|--:|--:|
| gold_full (baseline dilutif) | 1.01 | −15.9 % | −50.3 pt (47.6 %) | −58.6 pt | 3.9 % |
| **gold_overlay** | 0.88 | −15.4 % | **−40.8 pt (57.1 %)** | −55.5 pt | **0.0 %** |

**Lecture.** L'overlay **bouge le bon axe** (survie funded 47.6→57.1 %, +9.5 pt — **le mécanisme est réel** :
couper les régimes USD-fort aide la survie cumulée). MAIS (i) il reste **−40.8 pt dilutif** (≫ seuil −3 pt) ;
(ii) il **whipsawe** (Sharpe 1.01→0.88, drawdown à peine réduit −15.9→−15.4 — il coupe aussi les bons jours) ;
(iii) il **TUE la vitesse challenge** (p_pass 3.9→0.0 % : couper la vol ralentit le sprint +10 %, c'est
`two-FTMO-stages-reward-opposite-axes` en action). → **ÉCHEC** : le seul levier qui aide funded sabote
challenge, et la magnitude funded est un ordre de grandeur trop faible. La robustesse OOS est sans objet
(échec même poolé). DSR overlay 0.431 (whipsaw dégrade) vs gold_full 0.905.

## P2 — Spread silver − β·gold (hedge du facteur commun)
β (OLS silver~gold) = **1.07**. Spread = silver-long − 1.07·gold-short (swap-free, même fenêtre).

| | Sharpe | maxDD | corr(gold_trend) | funded Δsurvie (K=1) |
|---|--:|--:|--:|--:|
| **spread** | **−0.99** | −57.7 % | 0.02 ✓ | **−81.7 pt (16.2 %)** |
| silver solo (réf) | 1.12 | — | — | −52.4 pt (45.6 %) |

**Lecture.** Le spread est **décorrélé du book** (corr 0.02 < 0.3 ✓) — mais a un **Sharpe NÉGATIF −0.99** :
hedger le facteur commun gold/silver **retire l'edge**. Le **facteur directionnel commun EST l'edge**, pas
une nuisance dilutive ; ce qui reste (composante silver-spécifique) n'a aucun edge positif. Funded Δ−81.7 pt
(pire que silver solo) → **ÉCHEC** net. Réfutation propre de l'hypothèse. DSR 0.0.

## P3 — Sortie précoce 05:00 (fenêtre [23,0,1,2,3,4], −25 % de temps) — GOLD + WTI

| | Sharpe (vs full) | worst intraday-low (vs full) | funded Δsurvie | challenge p_pass |
|---|--:|--:|--:|--:|
| GOLD full | 1.01 | −4.0 % | −50.3 pt | 3.9 % |
| **GOLD early05** | **0.39** | −3.2 % | −59.7 pt (PIRE) | 0.4 % (PIRE) |
| WTI full | 0.61 | −7.1 % | −49.7 pt | 8.4 % |
| **WTI early05** | **0.52** | −7.0 % | −50.3 pt (PIRE) | 4.1 % (PIRE) |

**Lecture.** La sortie 05:00 **écrase le Sharpe** (gold 1.01→0.39 ; < 90 % du plein) en ne réduisant le
plus-bas intraday **qu'à peine** (−4.0→−3.2 % ; WTI −7.1→−7.0 %), et la survie funded ET la vitesse
challenge **empirent**. → **ÉCHEC** : l'edge est **distribué sur les 8 h** (pas concentré au début) ; le
raccourcir enlève de l'edge proportionnellement sans réduire le drawdown intrinsèque à tenir la position.
(Spec figée à 05:00 — pas de 2e essai à 06:00 ; le rapport disait 06:00-07:00 « forgiving », mais retirer
**aussi** l'heure 5 tue l'edge, et un retrait d'1 h ne toucherait de toute façon ni le drawdown ni la vitesse.)

## Verdict de recherche (seuils figés, sans déplacement)
- **Aucune des 4 pistes ne touche l'axe FTMO visé** : P1 bouge funded de +9.5 pt (mécanisme réel) mais
  reste −40.8 pt dilutif ET tue la vitesse ; P2 décorrèle mais à edge négatif ; P3 raccourcit mais détruit
  l'edge. Tous **ÉCHEC** per les seuils pré-enregistrés (−3 pt funded / Sharpe ≥90 % / vitesse↑).
- **La famille overnight-drift reste structurellement inadaptée aux deux étages FTMO.** Les 3 leviers
  d'amélioration échouent car chacun retire une propriété qui EST l'edge (vol → drawdown ; directionnel-commun
  → l'edge ; fenêtre-pleine → l'edge). Cohérent avec `two-FTMO-stages-reward-opposite-axes` (le levier
  pro-funded est anti-challenge) et les REJET solo/panier.
- **L'edge est réel mais non-améliorable POUR FTMO** (gold DSR cumul 0.905 ; silver/soybean vivants). Il
  appartient au book futures hors-propfirm (projet futur), pas à FTMO.

### Candidat de leçon (NOMMÉ, non gravé)
**« overnight-drift-improvement-levers-each-attack-the-edge »** : sur un edge directionnel pleine-vol lent,
les 3 améliorations FTMO naturelles (couper-régime / hedger-facteur-commun / raccourcir-fenêtre) retirent
chacune une propriété qui EST l'edge → aucune n'aide ; et le seul levier qui améliore la survie funded
(couper la vol) dégrade la vitesse challenge (`two-FTMO-stages-reward-opposite-axes`). Pour FTMO, viser des
edges **rapides + faible-vol** dès la conception, pas raffiner un edge lent pleine-vol.

---

## Reproductibilité
- Pré-reg `259ed1a` (avant résultats). Code : `code/p0_decay.py`, `code/lib.py` (sleeve/overlay/spread/funded
  ablation/challenge/DSR), `code/run_pistes.py`. Moteur `overnight_series/basket_series/basket_inject/basket_fp`
  **extrait verbatim de `claude/overnight-basket-ftmo`** (validé sleeve-OFF→0.87), import v22 + caches read-only
  du main dir. Résultats : `results/p0_decay.json`, `results/run_pistes.json`.
- Ablation funded = **FUNDED_WINDOWS canoniques** (book_only 97.9 %), survive252. Challenge = `basket_fp` mur 91 j.
  DSR cumul-famille n_trials=160. Spread low = pire MtM horaire-close combiné (silver dip − β·gold dip).
- **Book live + EA jamais touchés. Aucun déploiement.** Env `/usr/bin/python3`. Integrity à vérifier en MAIN dir.
