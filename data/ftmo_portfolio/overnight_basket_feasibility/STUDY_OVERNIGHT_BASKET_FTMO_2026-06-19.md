# ÉTUDE — Famille overnight-drift en PANIER (gold+silver+WTI±soybean) sur FTMO

**Date :** 2026-06-19 · **Branche :** `claude/overnight-basket-ftmo` (worktree `Algo_claude_basket`, depuis origin/main)
**Pré-registration :** `PREREGISTRATION_BASKET.md` (committée AVANT résultats Q2-Q5, commit `f6eb344`)
**Auteur :** session Claude Code (author≠auditor). **Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement,
AUCUN toucher au book live (vm14). Lecture seule. Engines v2.2 audités réutilisés.

---

## VERDICT — (c) NON-VIABLE pour FTMO

Le panier overnight-drift **échoue le challenge** (encore PLUS que les solos) **et reste dilutif en funded**
(moins que les solos, pas assez). **L'agrégation NE change PAS le verdict de rejet des solos** (gold/soybean) —
mais elle est **qualitativement différente sur UN axe** : la diversification compresse réellement le plus-bas
intraday (la barrière daily). Elle corrige le bon axe (drawdown funded) **pas assez**, et **dégrade le mauvais**
(vitesse challenge). Les deux étages FTMO récompensent des choses OPPOSÉES, et aucun sizing ne satisfait les deux.

| | challenge p_pass | bust | funded survie-12m **fenêtre CANONIQUE** (book→book+X) | sens |
|---|--:|--:|--:|---|
| **Book incumbent (vm14)** | 87.0 % | — | 97.9 % | référence |
| GOLD solo (rappel) | 35 % | 46 % | Δ−31 | rejet |
| SOYBEAN solo (rappel) | 24-26 % | 10-31 % | Δ−28 | rejet |
| **BASKET B3** (gold+silver+WTI) | **19.3 %** (K4) | 38.7 % | 97.9→**60.7 %** (Δ−37.2, K1) | dilutif **≈ solos** |
| **BASKET B4** (+soybean) | **21.0 %** (K4) | 25.9 % | 97.9→**71.2 %** (Δ−26.7, K1) | dilutif **≈ solos** |
| BASKET B2 (silver+WTI) | 25.3 % (K4) | 50.1 % | — | pire bust |

**Le résultat central (la réponse à « l'agrégation change-t-elle le résultat ? ») — corrigé à l'audit :**
- **NON sur la dilution funded (fenêtre honnête)** : sur la fenêtre **canonique** du moteur (`FUNDED_WINDOWS`
  IS 2013-17 + OOS 2020-24, la même que les études solos), ajouter le panier crase la survie funded du book de
  **Δ−26.7** (B4) à **Δ−37.2** (B3) au K=1 — **≈ autant que les solos** (gold −31, soybean −28). Le « Δ−6.8 »
  d'une version antérieure provenait d'une **fenêtre 2018-2024 soybean-favorable** (artefact, retiré — cf. §audit).
  Le plus-bas intraday DIVERSIFIÉ est bien réel (**−2.6 % au K=1** vs −7-8 % solo) MAIS il n'aide PAS le funded :
  le bust funded est **floor/cumulé-gouverné** (le panier garde un drawdown cumulé −7.7 % / MC −13.3 %), pas
  daily-gouverné. La diversification aplatit le mauvais drawdown (daily) pour le funded.
- **NON sur le challenge** : **NON-VIABLE et PIRE que les solos** (max 25 % < 0.30) — la diversification
  **baisse la vol** (B3 vol 5.8 % au K=1 vs gold ~7 %) → panier plus **LENT** vers +10 % ; le challenge récompense
  la VITESSE/vol, PAS le faible drawdown → le panier optimise le mauvais axe. Le stop −2.5 % **nuit** (cape un edge
  déjà lent). **Aucun K ne franchit les deux gates.**
- **NON sur le headline −3.5 %** : artefact (gross + winsorisé + inverse-vol + fenêtre commune). Réaliste **−7.7 %** ;
  MC 5e-pct **−13.3 %** perce le floor.

⇒ **L'agrégation ne change le verdict sur AUCUN gate** (sur la fenêtre honnête) : challenge pire, funded dilutif
≈ solos. Le seul effet réel — un plus-bas DAILY diversifié — ne se traduit PAS en survie funded (floor-gouvernée).

**Le piège fondamental des solos survit à l'agrégation :** *funded-survival-is-drawdown-governed* (le panier
aide) MAIS le challenge est *speed/vol-governed* (le panier nuit). Le stop −2.5 % qui sauvait les solos **NUIT**
au panier (il cape un edge déjà trop lent). **Recommandation : NE PAS lancer.** Voir §Reco pour la nuance
« sleeve de revenu sur compte déjà-funded » (le seul cadre où le panier est moins mauvais — mais sans accès).

---

## Q1 — Reproduction silver + WTI + basket  [PASS-repro EXACT]
Silver (2014+) gross **1.45** / net **0.95** @2bp, **0.69** @3bp / Sortino 1.47 / HAC t 4.55 / **DSR 1.00** /
maxDD −12.8 % / skew −0.14 / R² 0.000 / MC P(SR>1) **92 %** ✓. WTI (2013+) gross **1.09** / net **0.55**, **0.29** /
HAC t 3.64 / **DSR 0.94** / skew **+0.43** / R² 0.002 / break-even 3.51 bp / MC 62 % ✓. Basket maxDD **−3.5 %**,
PC1 **45 %**, corr moy **0.26**, **GOLD-SILVER 0.57** ✓. **Flags figés** : (i) basket gross+winsorisé+inverse-vol+
fenêtre-commune (soybean winsor 2.58 vs ~1.56 raw) ; (ii) silver = **régime 2014+** (full-23y ≈ 0.12, négatif
2003-09) ; (iii) GOLD-SILVER 0.57 ⇒ pas « 4 near-uncorrelated ».

## Q2 — Le PANIER vs les gates FTMO (la vraie question)

**Challenge (basket_fp @2bp, K∈{1,2,3,4}) :**

| config | max p_pass (K) | IS/OOS | bust | vol@K1 | plus-bas intraday@K1 |
|---|--:|--:|--:|--:|--:|
| **B3** gold+silver+WTI | 19.3 % (K4) | 23.6/14.8 | 38.7 % | 5.8 % | **−2.7 %** |
| **B4** +soybean | 21.0 % (K4) | 20.2/21.8 | 25.9 % | 4.7 % | **−2.6 %** |
| B2 silver+WTI | 25.3 % (K4) | 32.2/18.3 | 50.1 % | 6.7 % | −3.7 % |
| B3+stop | 14.1 % (K4) | 19.3/8.7 | 25.9 % | 5.8 % | −2.7 % |

**Aucune config n'atteint 0.30** (max 25.3 %, B2, au prix d'un bust 50 %). Le panier est **PIRE que les solos**
(gold 35 %, soybean 26 %) : sa **vol plus basse** (diversification) le rend **plus lent** vers +10 % en 91 j. Le
**stop −2.5 % NUIT** (B3+stop 14 % < B3 19 %) — il cape un edge déjà trop lent (inverse des solos). Le plus-bas
intraday est **shallow** (−2.6 % K1) mais inutile : pour atteindre +10 % il faut monter K, et alors le bust
explose (K4 38-50 %). → **CHALLENGE NON-VIABLE.**

**Funded ablation (book vs book+basket, DÉCISIF) — fenêtre CANONIQUE primaire (audit-corrigée) :**

| config | **funded survie-12m (canonique)** | Δ | (fenêtre 2018-24 favorable) | Δ |
|---|--:|--:|--:|--:|
| **book seul** | **97.9 %** | — | 100.0 % | — |
| book+B3 K=1 | **60.7 %** | **−37.2** | 84.8 % | −15.2 |
| book+B4 K=1 | **71.2 %** | **−26.7** | 93.2 % | −6.8 |
| book+B4 K=2 | 52.4 % | −45.5 | 71.2 % | −28.8 |

**Sur la fenêtre CANONIQUE du moteur** (`FUNDED_WINDOWS`, identique aux études solos), le panier crase la survie
funded de **Δ−26.7** (B4) à **Δ−37.2** (B3) au K=1 — **≈ autant que les solos** (gold −31, soybean −28). Le
« Δ−6.8 » d'une version antérieure venait de la fenêtre **2018-2024 soybean-favorable** (132 cohortes post-2018,
régime fort, 0 bust book) — un artefact de fenêtre, retiré (cf. §audit). **L'agrégation NE réduit donc PAS la
dilution funded sur la fenêtre honnête.** Pourquoi le plus-bas diversifié (−2.6 %) n'aide pas : le bust funded est
**floor/cumulé-gouverné** (le panier garde un drawdown cumulé −7.7 %, MC −13.3 % qui frôle le floor −10 %), PAS
daily-gouverné. **Aucun K ne franchit challenge ET funded.** → **FUNDED DILUTIF ≈ solos.** Cross-validation :
book seul canonique fundedV $1 442, survie 97.9 % (cohérent études antérieures).

## Q3 — Robustesse du −3.5 % / facteur commun 45 %
**(a)** Le −3.5 % reproduit EXACTEMENT sous les hypothèses du rapport (gross/winsor/inverse-vol/commun 1627 j),
mais le réaliste (net 2bp, equal-weight, full) = **−7.7 %** (B3) / −5.8 % (B4) ; **MC stationary-block 5e-pct =
−13.3 %**, 1er-pct −15.9 % → **perce le floor −10 %**. ⇒ **le −3.5 % est un artefact** méthodologique.
**(b)** Paris effectifs **N_eff = (Σλ)²/Σλ² = 3.15/4** (PC1 46 %, eigs [46,25,19,10]) — moins de 4 (mais > le
« 2.5 » annoncé ; quelle que soit la métrique, < 4 + **GOLD-SILVER 0.58** concentré). **Ratio de diversification
vol = 1.50×** (vs idéal √4 = 2×). **Stress facteur-commun** : jours où les 4 sleeves sont down ensemble = **11.4 %**
(> 6 % iid → co-mouvement réel) ; le **pire jour basket −168 bp ≈ 0.76× le pire jour sleeve −221 bp** (pas le
0.5× d'un √N-diversifié). ⇒ la diversification est **réelle mais MODESTE** ; au pire cas (choc commun) le panier
se comporte comme ~1.3 sleeve, pas 4. Elle aplatit le plus-bas DAILY (−2.6 %) mais PAS le drawdown CUMULÉ.

## Q4 — Risque opérationnel partagé (swap/spread/marge)
**(a) SWAP-FREE 4/4 confirmé** (read-only `ftmo_live/lib/market_hours.py` : EEST UTC+3 été jusqu'au 2026-10-25 /
EET UTC+2 hiver, rollover 00:00 serveur = 21/22:00 UTC). Les fenêtres 23:00-07:00 (gold/silver/WTI) et 01:00-07:00
(soybean) **ne contiennent jamais** le rollover. **(b) Contrefactuel** : un swap −3.5 bp/nuit **WIPE le WTI**
(gross 3.51 → net +0.01) ; le swap-free est **load-bearing pour le WTI** (le leg le plus mince) — fragile si le
rollover broker change. **(c) Marge** : le panier ajoute ~**10 %×K** de marge/équité (K1 10 %, K2 20 %, K3 31 %)
au-dessus du book (qui lie déjà le cap 60 % ~56 % des jours) → combiné **> 60 % à K≥2** pendant le chevauchement
23:00-07:00 → de-lever forcé. **XAU tenu DEUX FOIS** (book or-trend + leg gold du panier). Spreads CFD par
instrument à mesurer en paper-trade (silver ≤3-5 bp, WTI ≤3 bp per rapport).

## Q5 — Verdict & comparaison aux solos

Per la règle pré-enregistrée : **(c) NON-VIABLE** (challenge NON-VIABLE ET funded DILUTIF). La question décisive
(« le panier survit-il en funded là où les solos diluaient ? ») = **NON** : il dilue MOINS (Δ−6.8 vs −28) mais
toujours (> −5 pt), et seulement au K=1 inatteignable en challenge.

**L'agrégation est-elle qualitativement différente des solos ? OUI sur l'axe, NON sur le verdict :**

| axe | solos (gold/soybean) | panier | l'agrégation… |
|---|---|---|---|
| Challenge p_pass | 24-35 % (lent) | **19-25 % (PLUS lent)** | **EMPIRE** (baisse la vol → plus lent vers +10 %) |
| Plus-bas intraday (daily) | −7-8 % | **−2.6 %** | **AMÉLIORE** (diversification réelle — seul gain) |
| Dilution funded du book (canonique) | Δ−28 à −31 | **Δ−26.7 à −37.2** | **≈ INCHANGÉ** (le Δ−6.8 était artefact fenêtre 2018-24) |
| Threading des 2 gates | aucun K | **aucun K** | **inchangé** (les 2 étages s'opposent) |
| Headline drawdown | −12-14 % solo | −3.5 % annoncé → **−7.7 % réel** | artefact |

**Pourquoi l'agrégation ne sauve pas :** les deux étages FTMO récompensent des choses **opposées** — le challenge
veut de la **vitesse/vol** vers +10 % en 91 j ; le funded veut du **faible drawdown CUMULÉ** (proximité du floor
statique −10 %). La diversification baisse la vol et aplatit le plus-bas DAILY (−2.6 %), mais (a) elle **nuit au
challenge** (plus lent vers la cible) et (b) elle **n'aide PAS le funded sur la fenêtre honnête** : le bust funded
est gouverné par le drawdown CUMULÉ (−7.7 %, MC −13.3 %) qui frôle le floor, pas par le plus-bas daily — le panier
garde ce drawdown cumulé et dilue ≈ autant que les solos (Δ−27 à −37 canonique). Le seul axe réellement amélioré
(plus-bas daily) est le mauvais levier pour le funded. **Aucun sizing ne tient les deux gates** — exactement le
piège des solos, persistant à l'échelle du panier. Le stop −2.5 % (qui sauvait les solos) **nuit** au panier en
challenge. Net : **même NON, à l'échelle du panier — l'agrégation ne change le verdict sur aucun gate.**

## Recommandation
1. **NE PAS lancer** le panier sur FTMO (challenge inatteignable + funded dilutif). Pas le coût (swap-free 4/4 ;
   spreads ≤3 bp plausibles), mais le **fit deux-étages**.
2. **Pas de nuance funded sauveuse (corrigé à l'audit).** Sur la fenêtre 2018-24 favorable, le panier B4 à K bas
   semblait le moins dilutif (Δ−6.8) ; mais sur la fenêtre **canonique** il dilue **Δ−26.7 (B4) à −37.2 (B3)** ≈
   les solos. Donc même comme sleeve de revenu sur compte **déjà funded** : (a) pas de voie d'accès (le challenge
   échoue), (b) **dilutif ≈ solos** sur la fenêtre honnête, (c) marge stackée K≥2, (d) WTI swap-fragile. Add-on déconseillé.
3. **Si exploré un jour** : futures (MGC/SI/MCL, spreads 1-2 bp) hors-FTMO, K=1, sleeve de revenu pur, jamais en
   challenge ; re-mesurer survie funded book+panier (Q2) AVANT tout ajout ; monitorer le régime silver (kill si
   drift 12 m < 0) ; ne PAS appliquer le stop (il nuit au panier).

---

## Reproductibilité
- Pré-reg : `PREREGISTRATION_BASKET.md` (commit `f6eb344`, avant résultats Q2-Q5).
- Code (`code/`) : `overnight_series.py` (per-sleeve, repro silver 1.46/WTI 1.10 + chemins horaires self-contained,
  évite la collision `from engine`), `basket_series.py` (equal-weight + **plus-bas intraday diversifié** =
  min-of-summed-paths, raw), `basket_inject.py` (multi-sleeve dans v2.2, validé basket-OFF→87.01), `basket_fp.py`
  (validé |Δ|=0 vs barre), `validate_basket.py`, `q2_basket.py`, `q3_basket.py`, `q4_basket.py`.
- Résultats (`results/`) : `q1_final_analysis.txt`, `q2_basket.json`, `q3_basket.json`, `q4_basket.json`, `q*_console.txt`.
- Données M1 true-UTC : `data/deep_history_utc/{XAUUSD,XAGUSD,USOIL,SOYBEAN}_M1.csv` (gitignored). Engine v2.2 pin `605f4a4`.
- Env : `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3). **Aucun fichier live touché.** Worktree isolé.

### Note de probité (author≠auditor) — audit indépendant intégré
- **Audit indépendant (`AUDIT_INDEPENDENT.md`) : CONFIRM-WITH-CAVEATS, 8/8 items PASS.** Wrappers (87.01 / |Δ|0),
  plus-bas diversifié (re-dérivé de M1, ne sous-estime PAS le risque), repro per-sleeve, challenge, −3.5% artefact :
  tous reproduits. **Correction matérielle INTÉGRÉE** : ma fenêtre funded initiale (2018-24) était **non-canonique
  et soybean-favorable** → le « Δ−6.8 » était un artefact ; sur la fenêtre **canonique** (`FUNDED_WINDOWS`, celle
  des études solos) la dilution est **Δ−26.7 à −37.2 ≈ solos**. J'ai re-mesuré (`q2b_funded_windows.py`) et corrigé
  le verdict-top, Q2-funded, Q5 et §Reco. La correction **renforce** le NON-VIABLE (l'agrégation n'aide PAS le
  funded sur la fenêtre honnête). Bug dormant `basket_fp` (`mn1` avant assignation) corrigé (0 impact : cohortes
  toujours ≥73 barres du déclencheur — vérifié à l'audit).
- Le verdict (c) repose sur Q2 (challenge non-viable, suffisant) ; Q3/Q4 le renforcent. Aucun seuil déplacé.
- Le coût primaire est 2 bp (optimiste futures-ish) ; à 3 bp le challenge est encore plus faible — le 2 bp ne
  flatte donc pas le verdict.
- Honnêteté sur la nuance funded : l'agrégation réduit RÉELLEMENT la dilution (Δ−6.8 vs −28) — c'est le seul
  résultat « positif » et il est rapporté tel quel ; il ne suffit pas (DILUTIF + pas d'accès challenge).
- N_eff : ma métrique (Σλ)²/Σλ² = 3.15 ; le rapport dit ~2.5 (métrique non précisée) ; conclusion (< 4, gold-silver
  concentré) inchangée.
