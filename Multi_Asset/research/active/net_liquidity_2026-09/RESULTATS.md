# Liquidité nette — REJETÉE : c'est du bêta récolté par un taux de base asymétrique

**2026-09-08.** Spec gelée : `PREREGISTRATION.md`. 958 semaines, 2008-01 → 2026-05.
`NL = WALCL/1000 − TGA − RRP`, point-in-time respecté (donnée du mercredi ⇒ entrée jeudi soir).

## Le résultat de surface, qui a l'air bon

| horizon | n | rendement | t_HAC |
|---|---|---|---|
| 1 semaine | 958 | **+20,9 bps** | **+2,67** |
| 4 semaines | 958 | +20,1 | +1,21 |

Un t de 2,67 sur près de mille observations. C'est exactement le type de chiffre qu'on publie.

## Mon prior était faux, mais dans une direction intéressante

J'avais écrit que l'effet serait concentré sur **2020-2021**, la fenêtre où liquidité et actions ont
explosé ensemble. **C'est l'inverse** :

| période | n | 1 sem. | t | 4 sem. | t |
|---|---|---|---|---|---|
| 2008-2019 | 626 | +22,4 bps | +2,70 | +28,6 | +1,98 |
| **2020-2021** | 105 | **−14,8** | −0,51 | **−88,2** | −1,10 |
| 2022-2026 | 227 | +33,5 | +1,76 | +46,8 | +1,13 |

L'effet est **absent, voire négatif, précisément dans la fenêtre de tendance commune**. Le kill par
confusion de tendance que j'avais pré-enregistré ne se déclenche donc pas. Mais **le signe n'est pas
stable sur les trois sous-périodes**, ce que le critère de PASS exigeait.

## Les trois contrôles qui tuent

### D. Le contrôle inconditionnel — le plus important

Le rendement hebdomadaire **inconditionnel** de US100 sur la période est de **+86,4 bps (t +9,10)**.
Et `ΔNL > 0` survient **55,0 %** du temps.

Donc, **même sans aucune relation**, une règle fondée sur le signe rapporte mécaniquement
`(2×0,55 − 1) × 86,4 = +8,7 bps`. Le taux de base asymétrique appliqué à une dérive haussière
fabrique du rendement à partir de rien.

Observé : **+21,1**. L'excédent sur cette base mécanique n'est que de **+12,4 bps**, pas +21.

### E. Le test des deux jambes (L25) — décisif

| jambe | n | rendement brut du marché | contribution signée | t |
|---|---|---|---|---|
| `ΔNL > 0` → achat | 529 | +97,7 bps | **+97,7** | +8,29 |
| `ΔNL < 0` → vente | 432 | **+72,7 bps** | **−72,7** | **−4,66** |

**Quand la liquidité baisse, le marché monte quand même de +72,7 bps.** La jambe vendeuse perd donc
massivement. La stratégie ne « marche » que parce que la jambe longue (+97,7) l'emporte sur la jambe
courte (−72,7) dans un partage 55/45.

Ce n'est pas un edge directionnel. **C'est être long le marché 55 % du temps pendant un marché
haussier de dix-huit ans.**

### F. Placebo à taux de base apparié

10 000 tirages de signes aléatoires au même taux de base (55 %) : moyenne **+8,8 bps**
(écart-type 8,1). Le réel (+21,1) se situe au **93,79ᵉ percentile**, soit **p = 0,0621**.
**Échoue à 5 %.**

## Verdict

**REJETÉE.** Le kill « régression signée plate » du pré-enregistrement se déclenche (pente
+0,0002 bps par milliard, t +0,80 — l'effet ne dépend pas de l'ampleur du mouvement de liquidité),
le signe n'est pas stable entre sous-périodes, la jambe courte est massivement négative, et le
placebo apparié n'est pas franchi.

**Nature du kill : MÉCANIQUE.** Ce qui est mesuré est du bêta, pas un signal. Non rouvrable sans un
mécanisme entièrement neuf.

## Leçon candidate

**Candidate « taux de base sur actif dérivant »** — une règle fondée sur le **signe** d'un
prédicteur, appliquée à un actif à forte dérive, **fabrique du rendement à partir du seul taux de
base**, sans aucune relation prédictive. La baseline mécanique vaut `(2p − 1) × μ`, où `p` est la
fréquence du signe positif et `μ` la dérive inconditionnelle. Mesuré ici : `p = 55 %`,
`μ = +86,4 bps/semaine` ⇒ **+8,7 bps « gratuits »** sur les +21,1 observés, soit **41 % du résultat
affiché**, avant toute considération de signal.
⇒ **Toujours rapporter la baseline `(2p−1)×μ` à côté du résultat d'une règle de signe**, et
comparer au placebo à taux de base apparié, pas à zéro. Parente de L58 (valider la baseline du
placebo) mais distincte : elle vise les règles de SIGNE sur actifs à dérive, pas les placebos
calendaires. Le test des deux jambes (L25) l'attrape aussi, et les deux devraient être exigés
ensemble.
