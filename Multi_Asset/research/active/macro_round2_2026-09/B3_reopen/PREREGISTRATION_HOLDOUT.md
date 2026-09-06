# PRÉ-ENREGISTREMENT — B3, extension de véhicule et test sur holdout 1990-2004

> **GELÉ avant tout contact avec les résultats.** À la rédaction j'ai vérifié la COUVERTURE des
> séries (DGS10 depuis 1962, DGS2 depuis 1976, chocs JK depuis 1990) et **aucun rendement, aucun
> drift, aucune statistique**. Date : 2026-09-07.
> Amont : `RESULTATS.md` (commit `6899ebbe`), `FICHE_KILL_B3.md` (`667f71fa`).

## 1. Pourquoi cette étude, et ce qu'elle corrige

`RESULTATS.md` a établi deux choses. L'axe « mélange » est mort (la composante information n'a pas
de masse). Mais **corriger la mesure de surprise déplace le brut de ~0 à +21/+46 bps** — sauf que
l'effet reste à **0,63-0,65 de son propre MDE à 80 %** : sous-puissant, avec n=62.

Le facteur limitant identifié était **l'instrument, pas le signal** : IEF n'existe que depuis 2002,
alors que les chocs JK remontent à **1990**. Cette étude lève cette contrainte.

## 2. L'atout de conception : un vrai holdout

Je n'ai regardé QUE la fenêtre 2004-2024 (via IEF). **Les 139 événements JK antérieurs à 2004 sont
des données que je n'ai jamais touchées.**

⇒ **Le test PRIMAIRE est le holdout 1990-2003.** C'est un hors-échantillon authentique, pas une
re-coupe. Le test poolé 1990-2024 est **secondaire** et déclaré contaminé (il contient la fenêtre
déjà vue).

## 3. Changement de véhicule — un seul axe bouge

L'instrument passe de **IEF (ETF, depuis 2002)** au **rendement du 10 ans lui-même (DGS10, depuis
1962)**. C'est la variable d'état que Brooks-Katz-Lustig étudient réellement.

- **Mesure primaire, sans hypothèse** : `drift_signé = signe(choc) × (DGS10[t+H] − DGS10[t]) × 100`,
  en **bps de rendement**. Positif = continuation dans le sens du choc. Aucune conversion, aucune
  duration supposée.
- **Mesure secondaire, indicative** : P&L approximé `≈ drift_signé × D`, avec **D = 7,5** (duration
  de IEF), rapportée **uniquement pour comparabilité** avec `RESULTATS.md`. Elle ne peut ni valider
  ni invalider — ce n'est pas un prix négociable.

⚠ **Limite assumée et écrite d'avance** : un rendement CMT n'est pas un instrument. Cette étude
teste **le MÉCANISME sur un échantillon long**, pas la tradabilité. Si le mécanisme tombe ici, il
est mort et la question de véhicule ne se pose plus. S'il tient, une étude de tradabilité séparée
sera nécessaire (futures ZN, coûts et roll réels) — elle n'est PAS incluse ici.

## 4. Signal — paramètres gelés

- **Choc** : `MP_pm` (composante politique monétaire, décomposition « poor man's » de JK).
- **Seuil** : apparié en quantile au taux de trade de l'étude d'origine (**37,4 %**), calculé
  **séparément sur chaque sous-échantillon** pour que le taux de trade soit constant partout.
- **Côté** : le signe est porté par `signe(choc)` dans la mesure de drift ; pas de convention
  d'entrée séparée.
- **Horizons** : H ∈ {5, 10, 20} jours ouvrés — les trois du gel d'origine.
- **Entrée** : T+1 après l'annonce, comme le gel d'origine.
- **Coût** : non applicable à une mesure en rendement. La mesure secondaire en P&L retranche
  **1,0 bp RT**, comme le gel.

## 5. Critères, écrits avant de voir quoi que ce soit

**CONTINUATION CONFIRMÉE** (le mécanisme vit) — sur le **holdout 1990-2003** :
drift signé > 0, avec **|t_HAC| ≥ 2,5** à au moins **2 des 3** horizons, **et** ratio
**effet/MDE80 ≥ 1,0** aux mêmes horizons. La condition de MDE est non négociable : c'est
exactement ce qui manquait en 2004-2024.

**MORT** — sur le holdout, |t_HAC| < 2,0 **et** effet sous son MDE80 aux trois horizons.
⇒ Le mécanisme est alors **mort sur 34 ans**, le kill devient **MÉCANIQUE et définitif**, et l'axe
B3 se ferme sans ré-ouverture possible. La mesure de surprise était le dernier axe ; le véhicule
était le dernier recours.

**NON CONCLUANT** — tout le reste. En particulier : un résultat positif sur le poolé mais pas sur le
holdout sera lu comme **une confirmation de la contamination**, pas comme un signal.

**Test de cohérence obligatoire** : le signe du drift doit être **le même sur le holdout 1990-2003 et
sur 2004-2024**. Un signe qui s'inverse entre les deux moitiés est un échec, quel que soit le t —
c'est la leçon de l'étude d'origine (inversion post-2022) et elle s'applique à moi aussi.

**Contrôle de calendrier (L58)** : la moyenne du drift signé sur les événements NON tradés (sous le
seuil) est rapportée. Elle doit être proche de zéro. Si les non-tradés portent eux-mêmes un drift,
le seuil sélectionne une période et non une dose — et le résultat est invalidé.

## 6. Comptage

**2 essais** (holdout, poolé). Programme macro : 3 → 5. Global figé.
