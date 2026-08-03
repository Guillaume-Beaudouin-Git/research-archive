# Candidat — Paire AUDUSD / USDCAD (retour à la moyenne sur spread)

> **Statut** : Phase-2 complète, **kill de COÛT** — donc **rouvrable hors CFD** selon la politique
> de ré-ouverture. Seul survivant de 171 paires testées. **Pointeur, PAS un PASS.**
> **Source canonique** : `Multi_Asset/research/active/pairs_cointegration_2026-08/RESULTS.md`
> (branche mergée, `main` 2026-08-03).

## Mécanisme

Deux devises-matières face au dollar, exposées à des complexes différents (métaux/minerai pour
l'AUD, énergie pour le CAD) mais partageant un facteur commun dollar et un facteur risk-on. Les
divergences du spread se referment quand le facteur commun redevient dominant.

## Métriques mesurées

| Métrique | Valeur |
|---|---:|
| **Gross** | **+5.12 bps** — IC95 **[+2.79, +7.42]** |
| Two-sided (L25, jambes disjointes) | **passé des DEUX côtés** |
| β-orthogonalité (L38) | R² **0.003** |
| **DSR, déflaté sur les 171 paires** | **0.972** — ce n'est **pas** du data-mining |
| **Net sur CFD** | **+1.07 bps** — IC **[−1.25, +3.36]**, **contient zéro** |
| Part du gross mangée par le coût | **79 %** |

## Pourquoi il meurt sur CFD, et seulement là

Le gross est solide et honnêtement déflaté. C'est le **coût deux jambes** du CFD (3-4 bps aller-
retour, plus le markup de financement sur chaque jambe si tenu) qui absorbe 79 % de l'edge et fait
que l'intervalle net enjambe zéro. **Kill de COÛT ⇒ rouvrable** — le coût futures est d'un ordre de
grandeur inférieur.

## Véhicule à tester

**6A / 6C** (futures CME AUD et CAD), ou leurs micros M6A / M6C. ⚠ Sur les micros, vérifier le coût
**fixe** (L57) : il domine en bps sur petit notionnel et peut refermer seul un edge de 5 bps.
La marge de deux contrats doit tenir dans le capital — sinon, le test **L53** dit que l'affaire ne
vaut pas d'être montée.

## ⚠ Le contexte de famille, à ne pas ignorer

Ce candidat est le **seul survivant sur 171 paires**, dans une famille par ailleurs **fermée** :
- **0 paire sur 171** n'a une demi-vie compatible avec une séance (min **1 588 min**, porte 480) ;
- la **cointégration ne tient pas** (ADF rejette dans 8.6-19.7 % des fenêtres contre 5 % sous H0) ;
- **10 paires sur 18** ont leurs deux jambes de signe opposé (**L27 mesuré**) ;
- la littérature documente un déclin continu : **15.6 %/an avant 2000 → 6.4 % après 2010** (Krauss,
  76 études), et Do & Faff attribuent la cause aux paires qui **cessent de converger**.

⇒ Traiter ce candidat comme **un cas isolé à re-prouver**, pas comme la tête d'une famille vivante.
Un survivant unique sur 171 essais reste suspect malgré un DSR propre.

## Ce qu'il faut faire AVANT de le déployer

1. **Pré-enregistrer** avec kill rules chiffrées, sur le coût **réel** du véhicule futures.
2. Vérifier la **demi-vie sur le véhicule retenu** — si elle dépasse la séance, le portage revient.
3. Contrôle gratuit hérité : la durée médiane des trades était de **289 barres pour un plafond de
   288**, c'est-à-dire que **presque aucun ne sortait par convergence**. Si ça se reproduit, l'edge
   n'est pas ce qu'on croit.
