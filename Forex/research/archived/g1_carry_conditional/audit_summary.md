# Audit summary — G1 carry G10 conditionnel

**Source :** `audit_v1.md` (audit constitutionnel complet, snapshot immutable)
**Date audit :** 2026-05-26
**Verdict global audit :** REVISE → conclusion du rapport (KILL G1) résiste, deal-breakers
  empêchent toute exécution du protocole tel que rédigé

---

## Grille complète F1-F14 — verbatim audit_v1.md

| ID | Description courte | Sévérité | Section(s) impactée(s) | Action requise |
|----|--------------------|-----------|-----------------------|----------------|
| **F9** | AMTP + n_tests budget absents | **Deal-breaker** | TL;DR, Protocol, tout | Ajouter n_tests count, AMTP p-value |
| **F12** | Seuil HAC 1.96 vs constitution 2.5 | **Deal-breaker** | Protocol Step 2 | Corriger à t > 2.5 |
| **F3b** | Budget FX-1→FX-4 + 3-mod limit non vérifié | **Deal-breaker** | TL;DR, Recs | Vérifier avant toute ouverture G1 |
| **F14** | FX n_tests budget et 3-mod limit non audités | **Deal-breaker** | Fragilités additionnelles | Clarifier structure FX-1→FX-4 avant ouverture G1 |
| **F7** | Macrosynergy SR 0.67-0.78 sans haircut G10-only | **Major** | Details 1a, Recs G2B | Quantifier dégradation ou caveat explicite |
| **F1** | Cost gate sans décomposition IR formelle | **Major** | Details 3, 4 | Ajouter IC × √breadth ; vérifier 3× gate |
| **F5** | Endogénéité VXY identifiée, non résolue | **Major** | KF4, Caveat 4 | Proposer proxy non-endogène ou conclure "aucun disponible retail" |
| **F6** | Corrélation VXY proxy >0.90 non sourcée | **Major** | Details 5b | Source ou requalifier "estimation" |
| **F11** | WF ≥5 folds absent du protocole (hard rule) | **Major** | Protocol | Ajouter Step 4 obligatoire si Steps 1-3 PASS |
| **F2** | L16 n'existe pas ; concern G10 momentum mort valide | **Minor** | Recs G2A | Remplacer "L16" par ref research history |
| **F3a** | L16 n'existe pas ; REER finding partiellement mitigé | **Minor** | Recs G2B | Remplacer "L16" par ref research history |
| **F8** | Seuil 0.25 vs RESEARCH_PASS 0.7 non réconcilié | **Minor** | Protocol Step 3 | Labeler comme pre-filter, non critère final |
| **F10** | Corrélations portfolio théoriques, outil non cité | **Minor** | Section 7 | Référencer Portfolio/risk/correlation.py |
| **F13** | Vol proxy 21d peut inclure T-day (T-1 rule) | **Minor** | Details 2d | Clarifier lag |
| **F4** | Tension L15 vs empirique (faux positif audit) | **Résolu** | n/a | L15 et résultat empirique alignés — aucune action |

**Note :** F3b (table sévérité) et F14 (Fragilités additionnelles) couvrent le même enjeu
constitutionnel (budget Lesson 10, famille carry G10). F3b signale le risque ; F14 l'instrumente
et conclut que G1 serait la 4ème modification si FX-2/FX-3 sont des variations du carry.
Les deux ont le statut Deal-breaker dans audit_v1.md — les deux sont reproduits.

---

## Verbatim des 4 deal-breakers — audit_v1.md

### F9 (section "Recommendations — AMTP")

> **Claim** : [Absence de discussion n_tests et AMTP dans tout le protocole]
>
> **Standard** : Hard rule : "Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1."
> AMTP est exigé dès n_tests > 1.
>
> **Verdict** : FAIL (F9 — Deal-breaker)
>
> **Justification** : Le protocole 3 étapes teste au minimum :
> - Test 1 : carry G10 inconditionnel (baseline)
> - Test 2 : carry G10 + VXY filter
> - Test 3 : carry G10 + Fed filter
> - Test 4 : carry G10 + VXY + Fed combinés
>
> n_tests = 4 pour ce protocole seul. Global : 321 → 325+. La constitution exige AMTP à partir
> de n_tests > 1. Pour n_tests = 4 (Bonferroni simple), le seuil α effectif par test = 0.05/4
> = 0.0125 → t critique ≈ 2.50 (se retrouve par hasard proche du seuil constitutionnel). Mais
> l'absence totale de discussion AMTP est une violation formelle.

### F12 (section "Fragilités additionnelles F12")

> **F12 — HAC threshold 1.96 vs 2.5 [Deal-breaker]**
> **Constitution** : "Significance: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC
> feasibility."
> Le protocole Step 2 utilise t > 1.96. Voir Revision en section Key Finding 8 et Recommendations.

### F3b (table sévérité)

> | **F3b** | Budget FX-1→FX-4 + 3-mod limit non vérifié | **Deal-breaker** | TL;DR, Recs | Vérifier avant toute ouverture G1 |

### F14 (section "Fragilités additionnelles F14")

> **F14 — FX n_tests budget et 3-mod limit non audités [Deal-breaker]**
> **Constitution** : "Max 3 modifications per strategy hypothesis." Research history : "G10 carry
> (FX-1 to FX-4): dead post-GFC."
>
> Les strategies FX-1 à FX-4 ont consommé 4 tests sur la famille carry G10. Selon l'hypothèse
> que FX-1 = carry inconditionnel de base, les modifications FX-2, FX-3, FX-4 représentent
> déjà 3 modifications. G1 (carry conditionnel) serait une **4ème modification**, au-delà du
> budget constitutionnel de 3.
>
> Ce point n'est ni adressé ni même mentionné dans le rapport. Si FX-1→FX-4 sont des hypothèses
> indépendantes (pas des modifications de la même hypothèse), le budget est intact. Mais si FX-1
> = plain carry et FX-2/FX-3/FX-4 = variations du carry, le budget est épuisé.
>
> **Révision** : Clarifier la structure FX-1→FX-4 dans le research history avant toute ouverture
> G1. Si FX-1 = plain carry G10 et FX-2, FX-3, FX-4 = modifications (e.g., with momentum, with
> REER, with vol filter), alors G1 conditionnel est modification #4 → **interdit
> constitutionnellement sans ouverture d'une nouvelle hypothèse dédiée**.

---

## Verdict par section — audit_v1.md

| Section rapport | Verdict audit | Issue principale |
|----------------|---------------|------------------|
| TL;DR (Sharpe nets espérés) | NEEDS_REVISION | F9 : AMTP absent |
| TL;DR (G2A carry × momentum) | NEEDS_REVISION | F2, F7 : momentum G10 mort |
| Key Finding 1 (carry mort post-2010) | **PASS** | Solide, per-decade breakdown présent |
| Key Finding 2 (vol filter insignificant) | **PASS** | Cohérent avec L15 (faux positif audit résolu) |
| Key Finding 3 (Fed stance canal rompu) | **PASS** | Yoldas 2024 précis et contemporain |
| Key Finding 4 (endogénéité VXY) | NEEDS_REVISION | F5 : identifié, non résolu |
| Key Finding 5 (coûts retail) | NEEDS_REVISION | F1 : gate 3× non formalisé (530 < 540 bps) |
| Key Finding 6 (swap broker asymmetry) | **PASS** | Contribution originale, correcte |
| Key Finding 7 (propfirm-fit) | NEEDS_REVISION | L22 : MC sim non lancée |
| Key Finding 8 (G2A AMP 2013) | **FAIL** | F2 : momentum G10 mort selon research history |
| Details 1a (Macrosynergy SR) | NEEDS_REVISION | F7 : univers 24 devises ≠ G10-only |
| Details 2d (VXY proxy) | **FAIL** | F6 : corrélation >0.90 non sourcée |
| Details 2c/2d (T-1 rule) | NEEDS_REVISION | F13 : lag vol proxy non précisé |
| Details 4 (coûts RT) | **PASS** | Cohérent avec const. FX 0.15% RT |
| Details 5b (VXY données) | **PASS** | Factuel correct |
| Details 6a (publication effect) | **PASS** | Deux sources indépendantes |
| Details 6c (AMP 2013) | **FAIL** | F2 répétition |
| Details 7 (décorrélation portfolio) | NEEDS_REVISION | F10 : correlation.py non référencé |
| Recommandations — Step 2 HAC | **FAIL** | F12 : 1.96 vs 2.5 |
| Recommandations — Step 3 gate | NEEDS_REVISION | F8, F11 : threshold 0.25 et WF absent |
| Recommandations — AMTP | **FAIL** | F9 : deal-breaker |
| Caveats 1-3, 5-9 | **PASS** | — |
| Caveat 4 (endogénéité VXY) | NEEDS_REVISION | F5 répétition |

---

## Implication pour n_tests

G1 tué lors de l'audit constitutionnel, avant toute exécution d'IC test ou backtest.
**n_tests global reste à 321.** Aucune incrémentation.

*Note :* si le protocole G1 avait été lancé (4 sous-hypothèses), n_tests serait passé à 325.
Le kill précoce préserve 4 tests du budget global.
