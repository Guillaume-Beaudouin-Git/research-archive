# PRÉ-ENREGISTREMENT — positionnement NAAIM, orthogonalisé au momentum

> **GELÉ avant tout contact avec les rendements futurs.** Le pré-test L37 ci-dessous ne regarde que
> les SIGNAUX, jamais les rendements. 2026-09-08.

## 1. Ce que le pré-test L37 a montré, et pourquoi il ne suffit pas

Signal NAAIM contrarien (`−signe` du z-score sur 52 semaines) contre momentum 12 semaines :
**désaccord 69,8 %**, très au-dessus du seuil L37 de 5 %. Gate franchi **littéralement**.

Mais la lecture fine contredit le verdict binaire :

| mesure | valeur |
|---|---|
| corr(z_NAAIM, momentum 12s) | **+0,526** |
| corr(niveau NAAIM, momentum 12s) | **+0,577** |
| désaccord avec momentum 4 / 26 / 52 s | 72,2 % / 65,2 % / 62,2 % |

**L'exposition NAAIM suit le momentum** (corrélation +0,53 à +0,58) : les gérants sont plus exposés
après une hausse. Le fort désaccord est donc **une conséquence mécanique** d'avoir retourné le signe,
pas la preuve d'une information propre. Tester le NAAIM contrarien tel quel reviendrait largement à
tester de **l'anti-momentum sur un indice en tendance** — une perte connue d'avance.

⇒ **Le gate L37 tel qu'écrit est insuffisant pour cette famille.** Un désaccord élevé peut venir de
l'inversion du signe, pas de l'indépendance. **Il faut compléter par la corrélation des signaux
continus** — c'est une amélioration de L37 à proposer au registre.

## 2. Le handicap de taux de base, connu d'avance

Le signal contrarien est vendeur **58,7 %** du temps. Avec la dérive inconditionnelle de US100
(+86,4 bps/semaine, mesurée sur l'étude liquidité nette), la baseline mécanique vaut
`(2 × 0,413 − 1) × 86,4 = −15,0 bps/semaine`.

**La stratégie part donc avec un handicap mécanique de −15 bps par semaine**, avant tout signal.
C'est la candidate « taux de base sur actif dérivant », appliquée ici **contre** la stratégie.

## 3. L'hypothèse réellement testée

Puisque le NAAIM brut est largement du momentum, on teste **ce qu'il contient au-delà du prix** :

- régresser `z_NAAIM` sur le momentum (4, 12 et 26 semaines) ; garder le **résidu `e`** ;
- signal : `côté = −signe(e)` — être contrarien sur le **positionnement inexpliqué par la tendance** ;
- point-in-time : l'enquête NAAIM porte sur le mercredi et paraît le jeudi ⇒ **entrée au jeudi**.
- horizons : 1 et 4 semaines. Actif : US100.

## 4. Critères, écrits avant de voir quoi que ce soit

**KILL** — rendement du résidu indistinguable de zéro **au-dessus de la baseline de taux de base**
aux deux horizons (|t_HAC| < 2,0 sur l'excédent). La comparaison se fait contre `(2p−1)×μ`,
**jamais contre zéro**.

**KILL — une seule jambe** (L25) : si l'edge n'existe que du côté acheteur, c'est du bêta ; la jambe
vendeuse doit être positive elle aussi.

**KILL — instabilité de signe** sur les sous-périodes 2013-2019 / 2020-2021 / 2022-2026.

**PASS** : excédent significatif sur la baseline, positif sur les deux jambes, signe stable, et
franchissant un placebo à taux de base apparié.

## 5. Breadth et comptage

~52 observations/an, **fortement autocorrélées** — `N_eff` à rapporter, jamais le nominal.
**2 essais** (un par horizon). Programme macro : 15 → 17.
