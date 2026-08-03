# Candidat — Avance-retard XAGUSD → XAUUSD, h=120 min

> **Statut** : Phase-2 complète, verdict **UNDERPOWERED** (pas rejeté). Tous les contrôles de
> mécanisme passent ; meurt sur la **puissance** (DSR 0.610) et sur le **levier exigé par la
> barrière FTMO**. **Orphelin de véhicule : sa maison est un compte sans barrière.**
> **Source canonique** : `Multi_Asset/research/active/statarb_multivariate_2026-08/RESULTS.md`
> (branche mergée, `main` 2026-08-03).

## Mécanisme

L'argent mène l'or à horizon intra-journalier : le signe du rendement XAGUSD sur une fenêtre
glissante prédit le rendement XAUUSD sur les 120 minutes suivantes. Les deux partagent le même
facteur (métal précieux / dollar réel), mais l'argent est le plus volatil et le moins liquide des
deux — l'ajustement du plus liquide au choc porté par le moins liquide n'est pas instantané.

⚠ **Contre-intuition mesurée, importante** : le `|IC|` **CROÎT** avec l'horizon (0.003 à 1 min →
**0.016 à 120 min**) et l'edge **survit à 15 minutes de retard d'entrée**. Cette famille n'est donc
**pas fermée par le tier de latence** — elle est fermée par la largeur et le coût. C'est ce qui la
rend transposable à un véhicule bon marché.

## Métriques mesurées

| Métrique | Valeur |
|---|---:|
| Fenêtre | 19 ans |
| Walk-forward | **5 folds / 5** |
| Two-sided (L25, jambes disjointes) | **passé** |
| Placebo | **p = 0.0000** |
| β-orthogonalité (L38) | R² **0.6 %** |
| Retard d'entrée +15 min | **survit** |
| **DSR** (n = 132 cellules) | **0.610** ← le point de mort |
| Trades / an | **66** |
| **Sharpe** (annualisé en **√66**, L47 — PAS √252) | **0.491** au coût centre / **0.262** en queue |
| Rendement à levier 1× | **+2.87 %/an** |
| Pire trade observé | **−25.15 %** |

## Pourquoi il meurt sur FTMO — et c'est de la GÉOMÉTRIE, pas du signal

Pour atteindre +10 % en 182 jours il faut **×6.9 de levier**. À ce levier :
- **un écart-type d'un seul trade = 5.00 % du capital** — soit **exactement la barrière journalière** ;
- le pire trade observé vaut **2.5× le plancher statique**, en **une seule position**.

C'est un edge réel que la géométrie du challenge ne peut pas monétiser.

## Pourquoi le compte IBKR le déverrouille

- **Intraday-flat ⇒ zéro swap.** Aucune nuit tenue, donc le portage — tueur habituel des sleeves
  CFD (L36) — ne s'applique pas.
- **Pas de barrière ⇒ pas de contrainte de levier.** C'est la contrainte qui le tue qui disparaît,
  pas le signal qui s'améliore. Cas d'école **L53 : le véhicule d'abord.**
- Véhicules plausibles : XAUUSD/XAGUSD spot chez un courtier à spread serré, ou **GC/SI (voire
  MGC/SIL)** en futures. ⚠ Vérifier le coût **fixe** sur les micros (L57 : $1.70 sur un petit
  notionnel pèse 2.3-2.8 bps à lui seul).

## Ce qu'il faut faire AVANT de le déployer

1. **Pré-enregistrer un angle neuf** — la version actuelle est post-hoc, et son DSR dit qu'elle n'a
   pas payé son propre coût de recherche. Ne pas la rejouer à l'identique.
2. **Re-mesurer sur le coût réel du véhicule retenu**, pas sur le coût CFD.
3. **Vérifier la queue** : un pire trade à −25 % impose un dimensionnement fractionnaire strict, et
   la granularité de lot peut interdire le vol-targeting (L57).

## Réserve

Les coûts de XAGUSD utilisés dans l'étude sont des **estimations** (3.00 bps), absents de
`COST_AUDIT.md`. Le verdict n'en dépend pas — le candidat est jugé sur le coût **mesuré** de
XAUUSD — mais tout déploiement exige une mesure réelle des deux jambes.
