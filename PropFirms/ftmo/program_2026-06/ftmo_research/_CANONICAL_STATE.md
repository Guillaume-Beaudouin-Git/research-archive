# FTMO — ÉTAT CANONIQUE (source unique de vérité)
*MAJ 2026-06-03. À coller en tête de toute session travaillant sur FTMO. Si une session produit un chiffre qui contredit ce document, c'est la session qui a tort — réconcilier avant de continuer.*

> **Statut de réconciliation (ajouté par session Cowork 2026-06-03) :** les deux dossiers `NQ_ORB_metrics/` et `NQ_overnight_metrics/` ont été vérifiés contre ce document. **ORB : cohérent** (§3 reproduit exactement : 34/33/32% funded). **Overnight harvester (82-88%) : réconcilié** — ce chiffre est à coût idéalisé (swap NON compté) ; au swap réel long-CFD il sign-flip comme l'ORB (même mécanisme L33). Détail dans `_RECONCILIATION_overnight.md`. **Le verdict FTMO = CONFIRMÉ-CLOS tient pour les DEUX exploits** (intraday tué par spread, overnight tué par swap).

---
## ⚠ MISE À JOUR MAJEURE (2026-06-03, session Cowork) — le verdict "clos" est RÉVISÉ.
**Un vrai candidat FTMO a été trouvé : un ensemble TREND-FOLLOWING diversifié, vol-targeté, bidirectionnel.** p(funded) ≈ **54% single-attempt / ~80-90% en multi-tentatives** (no-time-limit), **validé OOS** (IS 2006-15 → 52%, OOS 2016-26 → 63%, pas de décroissance), **conforme** (single-leg par instrument sur actifs décorrélés), Sharpe 0,85, t=4,76, positif ~23/27 ans. **Pourquoi il passe là où tout le reste échoue : il est SHORT pendant les krachs (2008 +13%, 2020 +25%, 2022) au lieu de saigner du bêta long dans le floor.** Détail complet : `IDEA_TSMOM.md`. → **FTMO n'est PLUS "confirmé-clos" : il reste fermé aux familles price-pattern/réversion/stat-arb, mais le trend-following multi-actifs bidirectionnel est une exception réelle et déployable.** Caveats : bust ~40%/tentative, coût réel à mesurer (L33, surtout sleeve crypto), multi-attempt ~80-88% (pas 95%).

## VERDICT (une ligne) — RÉVISÉ
**FTMO = clos pour le price-pattern / réversion / stat-arb (l'essentiel de l'effort), MAIS ouvert au trend-following multi-actifs bidirectionnel** (le seul à profiter des krachs au lieu de les subir). Résultat négatif propre sur ~10 familles + **un positif validé OOS**. *(Le texte ci-dessous reste valable pour l'ORB et les familles réversion ; il est antérieur à la découverte TSMOM.)*
---
## 1. LE MEILLEUR ALGO POUR FTMO
**ORB sur NQ / US100 — spec V2+E7.** Opening Range Breakout 30 min, stop = côté opposé de l'OR (1R), exit E7 = trail-to-breakeven après +1R sinon close RTH, filtre V2 = OR ≥ 10 bps, flat overnight, ~1 trade/jour.
> **"Seul survivant" ≠ "bon".** En standalone : Sharpe 0,27, MaxDD −56% à −89%. Deflated Sharpe ~0,70 (échoue le bar 1,0). Ce n'est PAS une stratégie investable. C'est un exploit de barrière : on passe vite ou on buste vite.
Deux causes distinctes de la médiocrité, à ne jamais confondre :
- **Fragilité de régime → mauvais Sharpe.** 6 années sur 16 négatives (2013-16, 2020), edge concentré sur les années qui trendent (2022, 2024). Vrai à n'importe quel coût.
- **Coût → bascule du signe de l'edge.** mean_R si fin que 2 bps de coût le font passer positif→négatif (voir §4). C'est ça qui tue le déploiement réel.
---
## 2. QUEL CHALLENGE : 2-STEP
Le **1-step est PLUS DUR, pas plus facile.** Son daily 3% + DD trailing + règle Best-Day 50% punissent directement le skew positif qui *est* l'edge de l'ORB (~−13 pts de p(pass) rien que par Best-Day). Toujours raisonner 2-step pour l'ORB.
**Règles FTMO 2-step (SETTLED — NE JAMAIS RE-VÉRIFIER) :**
- Cible : +10% Phase 1, +5% Phase 2
- Daily DD : 5% (fixe, du solde initial)
- Total DD : 10% **statique** (floor $9 000)
- Min 4 jours/phase, **AUCUNE limite de temps**
---
## 3. p(pass) ET DURÉE — chiffres honnêtes
**FTMO 2-step, ORB V2+E7, full sample 2010-2026, coût idéalisé 2 bps :**
| Risk/trade | p(funded) | bust | médiane si financé |
|---|---|---|---|
| 1,0% | 34% | 60% | 132 j |
| 1,5% | 33% | 64% | 58 j |
| 2,5% | 32% | 67% | 25 j |
**Lecture critique :** p(pass) PLAT à ~33% quel que soit le sizing. Le résultat est déterminé par le **régime de marché au démarrage** (non chronométrable), pas par la taille. Monter le risque ne change pas la proba — seulement la vitesse de résolution (running → bust plus vite).
**Décomposition placebo :** ~80% de ce 33% = pure math de container (no-bust + temps illimité). L'ORB n'ajoute que ~15-20 pts. **Le levier est la règle, pas le signal.**
**Plafond DP :** le sizing DP-optimal est l'optimum sur TOUTES les politiques → le gap résiduel à 50% est une propriété de l'edge, pas du money-management. Mieux sizer ne remonte pas le plafond.
**Mur Sharpe :** >60% en 1 essai exigerait Sharpe ~1,4 tenu ~6 mois. Meilleur edge robuste de tout le programme = 0,34. Écart facteur ~4, non comblable en price-pattern retail.
**Chiffres flatteurs à rejeter :** 44-52% (régime 2022+ in-sample), "50,9%" (2022-25), "93%" (2026) = tous cherry-pick de fenêtre favorable. Les deux dossiers l'admettent.
---
## 4. LE COÛT — le paramètre qui décide tout (L33)
Le sign-flip entre les 4 anciens rapports n'était PAS un bug : hypothèses de coût différentes sur le même ledger. Grille canonique (`nq_v2_trades.parquet`) :
| Coût RT | mean_R baseline | mean_R E7 | Statut |
|---|---|---|---|
| 2 bps (abstrait) | +0,004 | +0,020 | hypothèse dossiers — non mesurée |
| **3 bps (réel futures direct)** | **−0,018** | **−0,003** | **mort arithmétique** |
| 6 bps (FTMO CFD US100) | −0,085 | −0,070 | mort franc |
**Bascule du signe entre 2 et 3 bps RT.** mean_R<0 ⇒ pas de "durée pour passer" : drift négatif sur barrière symétrique ne converge jamais, il dérive vers le bust.
---
## 5. ITEM OUVERT — le seul (mesure spread US100.cash)
Le coût "2 bps" des dossiers était une **hypothèse, jamais une mesure.** Specs FTMO US100.cash confirmées par capture broker :
- **Commission = 0%** → 100% du coût = **spread flottant** (non mesuré)
- Swap long −662,4 / court +28,58 (asymétrique, L30) → **non pertinent ORB** (flat overnight)
**Protocole de mesure (compte démo, ~5 sessions, 20 min/jour) :**
- Ouverture cash US = **16:30 EET** (broker) = **~15:30 Paris (CEST)**. Vérifier le décalage sur l'horloge MT5.
- Logger le spread **en points** à : 15:30:00 (auction, pire cas), 15:33, 15:35, + réf 16:30 (calme).
- Conversion : bps_RT = (spread_points / 21500) × 10000 × 2. Ajouter le slippage market order à l'open.
- **Seuil de mort : ~3 points cumulés (spread+slippage) RT ⇒ mean_R<0 ⇒ FTMO US100 mort par mesure.**
Cette mesure ne valide PAS la stratégie — elle transforme une estimation en mesure et boucle le NO-GO définitivement. Statut attendu : confirme le NO-GO (commission 0 + spread flottant CFD = profil 6-10 bps estimé).
---
## 6. CONDITIONS DE RÉ-OUVERTURE (≈ 0)
Rouvrir FTMO/ORB SEULEMENT si TOUTES réunies :
1. Firme 1-step futures-direct + DD static + cible≤DD + no daily + no consistency → **n'existe pas 2026-06**
2. Coût all-in ≤ 2 bps **confirmé sur 60+ trades démo**
3. Edge OOS **post-2026** (pas 2022-24 in-sample post-hoc)
4. DSR > 1,0 avec mod-count L10-compliant (actuel : 0,70 / 8 mods — **à re-vérifier contre le journal**)
---
## 7. CE QU'ON BANQUE (CV / journal)
- **L33** — l'instrument réel (sa structure de coût), pas le signal, décide si un exploit de barrière vit. Backtest 2 bps ne transfère pas à un CFD 6-10 bps.
- **L34 (proposé)** — checklist d'honnêteté prop-firm : 1 ledger canonique + coût réel + spec gelée + full-sample regime. Quand les 4 sont réunis, plus de sign-flip.
- **L35 (proposé)** — DP-optimal = ceiling, pas heuristique. Money-management n'est pas le levier.
- **Placebo** — ~80% du p(pass) = math no-bust × temps illimité, pas signal.
---
## 8. DÉCISION / ALLOCATION
- **Ne pas allouer de cycles à FTMO.** Confirmé-clos.
- **Cycles → A→BreakoutProp** (vrai edge +EV, Sharpe ~1,33) + personal book (A crypto, B delta-neutral mainnet pending).
- Make-or-break BreakoutProp (inchangé) : est-ce que son daily DD encaisse la DD intra-semaine naturelle de A (le facteur exact qui a breaché Propr à 3%) ?
---
*Ne pas mélanger les chiffres de specs différentes (V2+E7 two-sided vs long-only filtré doc3). Honnêteté > optimisme. Réconciliation > régénération. Si doute sur un chiffre : retour à ce document.*
