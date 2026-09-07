# PRÉ-ENREGISTREMENT — « liquidité nette » (Fed − TGA − RRP) et rendements actions

> **GELÉ avant tout contact avec les rendements.** J'ai vérifié la couverture des séries et rien
> d'autre. 2026-09-08. Origine : `macro_round4_2026-09/IDEES.md`, idée n°4.

## 1. La thèse à tester, et mon prior

Thèse populaire : la **liquidité nette** `WALCL − TGA − RRP` piloterait les prix des actifs risqués.
Très citée, presque exclusivement dans des blogs. **L'agent du round 4 n'a trouvé aucune évaluation
académique sérieuse.**

**Mon prior est défavorable et je l'écris avant de mesurer** : les trois séries ont explosé en
2020-2021 en même temps que les actions. Une corrélation entre deux séries fortement tendancielles
sur la même fenêtre est le piège de confusion le plus banal qui soit — et c'est exactement ce qui a
tué `fx_macro_score`. Le test sert à **mesurer si quelque chose survit hors de cette fenêtre**.

## 2. Données

- `WALCL` (bilan Fed, millions), `WTREGEN` (compte du Trésor, milliards), hebdomadaires du mercredi,
  2002-12 → 2026-09, 1 238 observations.
- `RRPONTSYD` (prises en pension au jour le jour, milliards), quotidienne, 2003-02 → 2026-09.
- Actions : `US100_M1` de `deep_history_utc` (vrai UTC).

Unités harmonisées en **milliards** : `NL = WALCL/1000 − WTREGEN − RRP`.

## 3. Point-in-time — la contrainte que la thèse populaire ignore

`WALCL` porte la date du **mercredi** mais n'est **publié que le jeudi vers 16h30 ET**. Un signal
calculé sur la donnée du mercredi n'est donc **pas actionnable avant la clôture du jeudi**.

⇒ **Signal de la semaine `t` ⇒ position prise à la clôture du jeudi de la semaine `t`, rendement
mesuré sur la semaine `t+1`.** Toute version qui trade le mercredi utilise une donnée non publiée.

## 4. Signal — paramètres gelés

- `ΔNL_t` = variation hebdomadaire de la liquidité nette, en milliards.
- Côté : `+signe(ΔNL)` — hausse de liquidité ⇒ achat d'actions (le sens de la thèse).
- **Aucun seuil** : tous les points sont tradés. Comme pour l'EIA, la relation dose-effet devient un
  diagnostic au lieu d'un paramètre à ajuster.
- Horizons : **1 et 4 semaines**.

## 5. Critères, écrits avant de voir quoi que ce soit

**KILL — confusion de tendance commune** *(le plus probable)* : si l'effet est concentré sur
**2020-2021** et disparaît sur les deux autres sous-périodes (avant 2020, après 2021), la thèse est
un artefact de tendance commune. Kill **mécanique**.

**KILL — régression signée plate** : si la régression du rendement futur sur `ΔNL` signé a une pente
indistinguable de zéro alors que des terciles semblent « marcher », l'effet tient à la magnitude et
non à la direction ⇒ ce n'est pas la thèse. (Diagnostic qui vient de trancher l'axe EIA.)

**KILL — non significatif** : |t_HAC| < 2,0 aux deux horizons sur l'échantillon complet.

**PASS** : pente signée significative, **de même signe sur les trois sous-périodes**, et survivant à
un placebo apparié. La stabilité de signe est obligatoire — c'est le test que B3 a échoué.

## 6. Breadth

~52 observations hebdomadaires par an, mais **fortement autocorrélées** (les variations de bilan sont
persistantes). Le nombre de paris indépendants sera **très inférieur** à 52 et devra être rapporté
via `N_eff`, jamais le nombre nominal.

## 7. Comptage

**2 essais** (un par horizon). Programme macro : 13 → 15. Global figé.
