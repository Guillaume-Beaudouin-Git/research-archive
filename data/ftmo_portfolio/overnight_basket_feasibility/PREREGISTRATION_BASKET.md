# PRÉ-REGISTRATION — Famille overnight-drift en PANIER (gold+silver+WTI±soybean) sur FTMO

**Horodatage (committé AVANT tout résultat) :** 2026-06-19
**Auteur :** session de recherche Claude Code (author≠auditor — validation en session fraîche)
**Branche :** `claude/overnight-basket-ftmo` (worktree isolé `Algo_claude_basket`, depuis `origin/main`)
**Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement. AUCUN toucher au book live (`ftmo_live/`, EA gelé,
FLAT, targets, compte vm14). Lecture seule sur tout artefact live. Go/no-go de recherche.

**Règle d'or :** questions, configs (≤6), métriques et seuils ci-dessous **FIGÉS**. Aucun ajustement post-résultat.

---

## 0. Objet, ce qui est DÉJÀ tranché, et l'angle NEUF

- **Famille overnight-drift** : long sur la fenêtre post-rollover, vol-targetée (cap 3×), complete-window,
  winsorisée 0.5/99.5%, swap-free. 4 sleeves :
  - **GOLD** XAUUSD 23:00→07:00 UTC (full) — **DÉJÀ REJETÉ en solo** (challenge 35 %, funded dilutif ;
    [[asia_23_8_ftmo_feasibility_2026-06]]). NE PAS re-tester en solo.
  - **SOYBEAN** 01:00→07:00 UTC (2017-12+) — **DÉJÀ REJETÉ en solo** (challenge 24-26 %, funded crase
    100→43-72 % ; branche `claude/soybean-ftmo-feasibility`). NE PAS re-tester en solo.
  - **SILVER** XAGUSD 23:00→07:00 UTC (2014+) — **NOUVEAU** (Q1 repro : gross 1.45, net 0.95@2bp/0.69@3bp,
    DSR 1.00, skew −0.14, R² 0.000 ; régime-conditionnel, full-23y ≈ 0.12).
  - **WTI** USOIL 23:00→07:00 UTC (2013+) — **NOUVEAU** (Q1 repro : gross 1.09, net 0.55@2bp/0.29@3bp,
    DSR 0.94, skew +0.43, R² 0.002, break-even 3.5 bp = le plus mince).
- **Leçons à appliquer (non re-testées) :** *funded-survival-is-drawdown-governed-not-Sharpe* ;
  *funded-daily-loss-binds-not-the-static-floor* (daily −5 % = $500 fixe vs solde@minuit ; floor statique $9 000) ;
  *extraire-bat-thésauriser*.
- **L'ANGLE NEUF = LE PANIER, PAS les sleeves solo.** Silver/WTI échoueront probablement en solo (edge lent,
  drawdown pleine-vol — même signature que gold/soybean). La vraie question : **l'agrégation equal-risk
  (basket maxDD −3.5 % gross vs −12-14 % solo) bat-elle la DILUTION funded qui a tué les solos ?** Les solos
  diluaient car ils empilaient du drawdown pleine-vol contre le floor/daily. Un panier à −3.5 % empile BEAUCOUP
  MOINS → il pourrait survivre. **C'est la question décisive (Q2-funded).**

### Réservations pré-inscrites (à confronter, pas supposer)
1. **Le −3.5 % est GROSS, WINSORISÉ, close-to-close** (`basket_audit.py`). La barrière FTMO voit le **plus-bas
   intraday RAW**. Le −3.5 % pourrait être un artefact (winsor enlève les tails que la barrière subit).
2. **GOLD-SILVER corr = 0.57** (reproduit) — PAS « 4 near-uncorrelated ». PC1 = 45 %, ~2.5 paris effectifs.
   Le panier est un pari gold-silver + 2 satellites, pas 4 paris indépendants.
3. **Silver = régime 2014+** (cherry-pické ; négatif 2003-09). Le DSR 1.00 est sur le régime favorable.
4. **Lenteur** : le panier réduit le drawdown mais **accélère-t-il l'edge** vers +10 % en 91 j ? À VÉRIFIER
   (les solos échouaient sur la lenteur, pas le drawdown — le panier corrige le mauvais axe ?).

### Engines RÉUTILISÉS (read-only) + NOUVEAU code basket
- **Moteur barre v2.2 audité** (`data/ftmo_portfolio/v22/engine_v22.py` + cleanroom, pin `605f4a4`, pooled 0.87) —
  présent sur `main`, lu via chemin absolu MAIN (branch-invariant).
- **Données** M1 true-UTC (`data/deep_history_utc/{XAUUSD,XAGUSD,USOIL,SOYBEAN}_M1.csv`) + H1 caches — gitignored,
  MAIN. Moteur de série `gold_research/intraday.py` (`hourly_pivot/win_ret`, déjà validé asia/soybean).
- **NOUVEAU (code/)** : `overnight_series.py` (généralise asia/soy_series : per-sleeve net + **chemins horaires**
  pour le plus-bas intraday), `basket_series.py` (combine equal-risk + **plus-bas intraday DIVERSIFIÉ**),
  `basket_inject.py` (injection MULTI-sleeve dans v2.2, alignement morning-exit→book même-jour), `basket_fp.py`
  (first-passage lean, copie générique d'asia_fp). Les engines mono-sleeve asia/soy sont sur d'autres branches ;
  je RÉ-IMPLÉMENTE le pattern VALIDÉ et le re-valide (mêmes 3 checks).
- **Validation obligatoire (avant tout chiffre Q2)** : (i) per-sleeve `overnight_series` reproduit
  `metals_energy_research`/`asia` (Sharpe au centième) ; (ii) basket OFF ⇒ moteur reproduit pooled **87.0**
  [86,91] ; (iii) `basket_fp` == moteur barre (book off, basket on) |Δ| ≤ 0.5 pt.

### Construction du PANIER (figée — le cœur méthodologique)
- **Per-sleeve** : winsorisé(0.5/99.5%) × VT(expanding-median/rolling-20, cap 3×) × win_ret(fenêtre), net du
  spread. Indexé par la **date de SORTIE-matin** (gold/silver/WTI : entrée 23:00 j → sortie 07:00 j+1, shift +1 ;
  soybean : 01:00→07:00 j, pas de shift) → toutes les sleeves **sortent à 07:00 UTC le même jour-book**.
- **Poids equal-risk = equal-weight (1/N) des sleeves VT'd** (causal, sans look-ahead : chaque sleeve est déjà
  VT'd à ~même vol). Variante reportée : inverse-vol full-sample (le `1/df.std()` du rapport — look-ahead, pour
  comparaison au −3.5 %).
- **Plus-bas intraday DIVERSIFIÉ (clé)** : pour la barrière, `basket_low` = **min sur la fenêtre 23:00-07:00 du
  Σ pondéré des chemins horaires cumulés (account-fraction) des sleeves**. Calculé sur chemins **RAW
  (non-winsorisés)** = ce que le compte subit (conservateur). Variante : winsorisé (hypothèse implicite du
  rapport). C'EST le test honnête de la diversification : `min(Σ paths) ≪ Σ min(paths)` ssi imparfaitement
  corrélé. Soybean ne contribue qu'entre 01:00-07:00 (0 sur 23:00-01:00).
- **P&L basket** = `INIT × K × Σ_i (1/N) net_i` (notionnel fixe, swap-free), réalisé à l'ouverture du jour-book
  (avant segment-0), barrière sur `INIT × K × basket_low`. K = levier basket (vol compte ≈ K × vol_basket).
- Coût : **2 bp RT/sleeve (primaire)** + **3 bp (conservateur)**. (FTMO ne trade pas les futures CME ; sur CFD
  le spread réel par instrument est à mesurer — Q4. 2 bp = borne futures-ish/optimiste, cohérente rapport.)

### Convention triplet (imposée) : (p, attempts_moyen, EV). Cohortes 7 j, IS 2013-19 / OOS 2020-26, mur 91 j,
funnel 2-step. EV = p × funded_value − attempts × $96. (Soybean/silver absents avant 2014/2017 → cohortes IS
réduites, reporté.)

### Configs FIGÉES (≤6 ; budget anti-sur-recherche — DSR déjà 0.75-1.00, gold+soybean ont consommé des essais)
- **B3** = gold+silver+WTI (panier préféré du rapport, fenêtre commune 23:00-07:00). PRIMAIRE.
- **B4** = gold+silver+WTI+soybean (famille complète).
- **B2** = silver+WTI (les 2 NOUVEAUX seuls — isole leur apport marginal, hors gold déjà rejeté).
- **B3+stop** = B3 + stop intraday −2.5 % du compte (la mitigation qui a aidé les solos).
4 configs basket. K ∈ {1, 2, 3, 4} et coût {2,3} bp = sensibilités (PAS des configs). Au-delà : budget épuisé.

---

## Q1 — Reproduction silver + WTI + basket  [FAIT, PASS-repro EXACT]
Silver gross 1.45 / net 0.95@2bp,0.69@3bp / DSR 1.00 / skew −0.14 / MC P(SR>1) 92% ✓ ; WTI gross 1.09 / net
0.55,0.29 / DSR 0.94 / skew +0.43 / 62% ✓ ; basket maxDD −3.5 % / PC1 45 % / corr moy 0.26 / GOLD-SILVER 0.57 ✓.
**Flags figés** : winsorisation gonfle le basket (soybean winsor 2.58 vs ~1.56 raw) ; silver = régime 2014+ ;
panier ~2.5 paris effectifs.

## Q2 — Le PANIER vs les gates FTMO (la vraie question)
**Challenge** : B3/B4/B2/B3+stop, balayage K, coût 2/3 bp. Triplet (p_pass, attempts, EV) + p_bust + plus-bas
intraday distribution. **Le drawdown réduit aide-t-il la survie, ET l'edge agrégé est-il assez RAPIDE pour +10 %
en 91 j ?** Contre-vérif `basket_fp` + close-to-close.
**Funded (DÉCISIF)** : ablation **book vs book+basket** (moteur audité, cohortes funded). Triplet funded
(extraction $, survie 12 m, min-balance). **Le panier −3.5 % DILUE-t-il encore la survie (comme les solos 100→43-72 %)
ou l'agrégation le rend-il non-dilutif/accrétif ?**

**Seuils (figés) :**
- **Challenge VIABLE** : ∃ config p_pass(poolé) ≥0.50 ET p_bust ≤0.35 ET OOS ≥0.40 ; **CONDITIONNEL** [0.30,0.50) ;
  **NON-VIABLE** <0.30.
- **Funded — le test neuf** : **NON-DILUTIF/ACCRÉTIF** ssi book+basket survie-12m **≥ book − 0.02** (le panier bat
  la dilution solo) ; **DILUTIF** ssi **< book − 0.05** (même non au niveau panier) ; zone grise entre les deux.

## Q3 — Le facteur commun 45 % / robustesse du −3.5 %
(a) **MC block-bootstrap** du maxDD basket (RAW vs winsorisé) : le −3.5 % tient-il, ou explose-t-il sur RAW /
en 5e-percentile ? Seuil **ROBUSTE** : 5e-pct maxDD RAW reste < ~10 % (dans le floor) ; **ARTEFACT** si ≫ −3.5 %
(p.ex. RAW ou bootstrap > −8 %).
(b) **Paris effectifs** = (Σλ)²/Σλ² (PCA). **Stress facteur-commun adverse** : choc simultané des 4 legs (jour où
tous down — premium overnight comprimé, ou tous swap-payants si rollover change) → le panier « diversifié »
se comporte-t-il comme **1 sleeve** au pire cas ? Seuil : si paris-effectifs ≤ ~2.5 ET le pire-jour-basket ≈
moyenne-des-pires-jours-sleeve (pas √N plus petit), la diversification est sur-vendue.

## Q4 — Risque opérationnel partagé (W2)
Lecture seule infra FTMO : les 4 instruments (XAU/XAG/USOIL/SOYBEAN.c) sont-ils **swap-free** sur 23:00-07:00
(rollover serveur ≤22:00 UTC) ? Un seul payant le swap (−3 à −4 bp/nuit) suffit-il à couler sa contribution
(contrefactuel) ? Spreads CFD par instrument (mesurer/flagger paper-trade). **Conflit de marge** : le book live
(micro-ORB US100 + nightly GER40 + or-trend XAU) touche déjà XAU+indices ; le panier ajoute XAU+XAG+USOIL+soybean
→ marge cumulée sous cap 60 % pendant le chevauchement 23:00-07:00.
**Seuil** : SWAP-FREE CONFIRMÉ si fenêtre ne contient pas le rollover (4/4) ; sinon flag le(s) leg(s) impacté(s).

## Q5 — Verdict (règle figée)
- **(a) VIABLE-challenge** : Q2-challenge ∈ {VIABLE} ET Q4 swap-free ET marge OK.
- **(b) VIABLE-funded-add-on** : Q2-funded = NON-DILUTIF/ACCRÉTIF (le panier bat enfin la dilution) — **le
  résultat majeur ssi démontré par l'ablation survie, pas juste un DD plus bas**.
- **(c) NON-VIABLE** : Q2-challenge NON-VIABLE ET Q2-funded DILUTIF (même non, à l'échelle du panier).
**Comparaison explicite aux solos (gold/soybean rejet)** : l'agrégation change-t-elle le résultat, OUI/NON, et
pourquoi ? Si le panier survit en funded là où les solos diluaient → démontrer rigoureusement (ablation survie).
Livrable : `STUDY_OVERNIGHT_BASKET_FTMO_2026-06-19.md`. Puis audit indépendant.

### Lessons rappelées : L24/funded-drawdown-governed/daily-binds-not-floor ; L20/21 DSR (n_mod cumulé élevé) ;
L33/46 coût réel décide ; L39 skew daily ET mensuel ; règle 3-mods (B-configs = budget complet).
