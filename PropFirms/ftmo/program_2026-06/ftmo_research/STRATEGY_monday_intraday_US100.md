# Stratégie D-candidate — « Monday intraday long » US100 (décorrélée de l'ORB)

> **🛑 ERRATUM — annualisation corrigée √252 → √52.** Une stratégie « un jour/semaine » trade ~52×/an, pas 252. **Tous les Sharpe ci-dessous sont surévalués ×2,2.** Corrects : **Monday SR ≈ 0,60 (full) / 0,94 (2018-26)**, sous-1. La réplication cross-asset (6/6, signe) tient ; les magnitudes ÷2,2. **La thèse « Sharpe>1 » est retirée — c'est un tilt réel mais modeste (~0,6-0,9), décorrélé, significatif (t 2,26).** Détail complet : `RAPPORT_monday_sleeve_stresstest.md` (erratum v1.1).

> **TL;DR — Premier signal de toute la recherche intraday à survivre la réplication cross-asset.** Acheter US100 (NQ) à l'open du lundi (09:30 ET), vendre au close (16:00 ET) — intraday pur, pas d'overnight, pas de swap. **SR net +1,31 (2010-26) / +2,07 (2018-26), win 59 %, décorrélé de l'ORB (+0,08).** Confirmé sur **6/6 indices internationaux indépendants** (S&P, Nasdaq, Dow, Russell, DAX, Nikkei) en 2018-26. **Caveat décisif : effet de RÉGIME post-2018 — absent en 2008-2017 (cross-asset moyen −0,04).** C'est un edge structurel du régime actuel + une beta-longue timée, PAS une loi intemporelle. Déployer avec kill-switch régime + vol-targeting.

---

## 1. Pourquoi celui-ci est différent (il passe le test qui a tué les autres)

Deux faux positifs déjà attrapés dans cette recherche (gap-fade, puis le lundi sur NQ seul) échouaient à la vérification : CI incluant 0, ou échec multiple-testing single-asset. **Le lundi passe le test le plus dur — la réplication cross-asset out-of-sample :**

| ETF indice | Lun SR (full) | Lun 2008-2017 | Lun 2018-2026 |
|---|---:|---:|---:|
| S&P (SPY) | +0,53 | −0,22 | **+1,69** |
| Nasdaq (QQQ) | +0,91 | −0,07 | **+2,10** |
| Dow (DIA) | +0,70 | +0,21 | **+1,39** |
| Russell (IWM) | −0,23 | −0,70 | +0,43 |
| Allemagne (EWG) | +0,59 | +0,07 | **+1,58** |
| Japon (EWJ) | +1,07 | +0,45 | **+2,09** |
| **Moyenne** | **+0,59** | **−0,04** | **+1,54** |

→ **2008-2017 : 3/6 positifs, moyenne −0,04 (bruit).** **2018-2026 : 6/6 positifs, moyenne +1,54.** Six indices indépendants (dont 2 internationaux) ne s'alignent pas par hasard — l'effet est **réel dans le régime actuel**. La réplication cross-asset domine le souci multiple-testing single-asset (Bonferroni ×5 sur NQ seul).

## 2. Spécification (simple, basique)

| Élément | Valeur |
|---|---|
| Instrument | US100 (NQ) — actif FTMO |
| Déclencheur | jour = **lundi** (si férié US, pas de trade) |
| Entrée | **open RTH 09:30 ET**, long |
| Sortie | **close RTH 16:00 ET** (même jour) |
| Tenue | intraday pur — **flat overnight → 0 swap, 0 financement** |
| Fréquence | ~1 trade / semaine (~48/an) |
| Coût | 2 bps RT (CFD US100) |
| Sizing | vol-targeting quotidien (rolling 20j) — **obligatoire** (lisse la concentration vol) |

## 3. Caractérisation sur NQ (net 2bp)

| Période | SR | ann | MaxDD | win | t | n |
|---|---:|---:|---:|---:|---:|---:|
| 2010-2026 | **+1,31** | +19,6 % | −13,7 % | 57 % | +2,26 | 746 |
| 2018-2026 | **+2,07** | +34,6 % | −13,2 % | 59 % | +2,58 | 391 |
| 2022-2026 | +2,80 | +44,0 % | −9,0 % | 59 % | +2,51 | 203 |

**corr au PnL ORB (2018-26) : +0,08** → vraiment décorrélé (sleeve diversifiant).

## 4. Caveats honnêtes (à NE PAS ignorer)

1. **Effet de régime, pas intemporel.** Absent 2008-2017 (cross-asset −0,04). Apparu ~2018, fort depuis 2020. Probables moteurs structurels : flux systématiques de début de semaine, rebalancing vol-control le lundi, dynamique des gaps de week-end post-2018, essor des 0DTE. **Si ces moteurs disparaissent, l'edge disparaît.**
2. **Beta-longue directionnelle.** C'est la dérive haussière concentrée le lundi → **perd dans une année baissière** (2018 : −12,2 % sur le sleeve). Pas market-neutral. Partage le risque de queue bear avec l'ORB (tous deux net-longs), même si décorrélés au quotidien.
3. **PnL concentré** dans les années à forte vol (2020 +27,5 %, 2023 +16,5 %) — le win rate 59 % est stable mais la magnitude scale avec la vol → **vol-targeting essentiel** pour ne pas dépendre de 2 années.
4. **Basse fréquence** (~48 trades/an) → comme sleeve décorrélé de l'ORB, oui ; comme passeur de challenge FTMO autonome, trop lent.

## 5. Déploiement recommandé

- **Comme 2ᵉ sleeve décorrélé de l'ORB** (diversifie le timing de l'exposition longue), pas comme standalone.
- **Vol-targeting quotidien** (cible ~10-12 % ann) — transforme la concentration en flux régulier.
- **Kill-switch régime** : suivre le Sharpe glissant 52-semaines du lundi ; **couper si < 0** (l'effet s'est retourné en 2008-2017, il peut le refaire).
- **Walk-forward live** : valider en paper ≥3 mois avant capital (0 jour live à ce jour).
- Optionnel : étendre à « début de semaine » (lundi+mardi, mardi aussi +0,5 cross-asset) pour doubler la fréquence — à re-tester avec la même rigueur.

## 6. Verdict

**Premier vrai candidat décorrélé Sharpe>1 de la recherche** — il franchit la barre (réplication cross-asset 6/6) qui a éliminé tous les autres. **Mais c'est un edge de RÉGIME (post-2018) à beta-longue, pas une loi structurelle intemporelle.** Honnêtement déployable comme sleeve diversifiant avec garde-fous (vol-target + kill-switch régime), pas comme alpha market-neutral garanti. Le « Sharpe>1 décorrélé » existe **dans le régime actuel** ; le pari est sa persistance.

---
*Recherche 2026-06-02. Données : NQ 1-min databento (panel `outputs/nq_intraday_panel.parquet`) + OHLC quotidien Yahoo (SPY/QQQ/DIA/IWM/EWG/EWJ) via urllib. Net 2bp, corr vs ORB V2+E7. Cross-asset = test OOS dominant sur le multiple-testing. 0 jour live.*
