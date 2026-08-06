# L'axe du SIGNE — le différentiel de swap compense-t-il jamais la dérive ?

**2026-08-06. N1 — 21 essais déclarés, pré-enregistrés (3 règles × 7 instruments).**
Gate au GROSS d'abord (`cost_rt = 0`, `swap = 0`). Univers 19 tradables,
`data/deep_history_utc/` (vrai UTC) resamplé sur **l'instant de facturation du swap**.
Verdict : **l'axe du signe est FERMÉ, et il l'est pour une raison structurelle, pas empirique.**

---

## 0. Résultat en quatre lignes

1. **Le différentiel de swap « en faveur du short » n'est pas une inefficience : c'est le taux sans
   risque.** Décomposé sur le snapshot MT5 mesuré, sur US100 les 2.2174 bps/nuit de différentiel se
   scindent en **1.9671 bps de cash (3.59 %/an) + 0.2503 bps de vraie remise de markup (0.914 %/an)**.
   Le short « encaisse » très exactement ce que le long touchait déjà via la dérive. **89 % du
   différentiel n'est pas de l'alpha.**
2. **Le markup du broker est payé des DEUX côtés.** Une sleeve two-sided 50/50 paie
   **−3.91 %/an sur US100, −3.30 % GER40, −4.38 % XAUUSD, −2.39 % USDJPY** — et ce chiffre est
   **rigoureusement invariant au régime de taux** (identique en ZIRP et en 2023-2026, cf. §1).
   Le signe déplace la facture de portage dans une fourchette, il ne la supprime jamais.
3. **Aucun signal two-sided ne franchit L25 : 0/21 cellules ont leurs DEUX jambes positives à coût
   nul.** La jambe short est négative au gross dans **20/21** cellules. Le meilleur short gross de
   tout le balayage vaut **+0.16 bps/barre, t = 0.06** (USDJPY, régime de vol).
4. **Passer two-sided détruit de la valeur dans 21/21 cellules**, médiane **−3.71 %/an**, et
   — contre-intuitivement — **augmente la facture de portage**, parce que les jours short
   remplacent des jours **FLAT** (portage zéro), pas des jours long.

**⇒ La réponse à la question du brief est OUI, avec le chiffre : le différentiel de carry ne
compense jamais la dérive, et l'écart est d'un facteur ~33 sur US100** (subvention réelle
0.46 %/an de déplacement de seuil contre 15.29 %/an de dérive à franchir).

---

## 1. LE BILAN DE CARRY EN FONCTION DE LA FRACTION SHORT

`headline_carry_by_short_fraction.csv` · `carry_by_duty_cycle.csv` · `breakeven_short_fraction.csv`

Facture de portage `carry(f) = (1−f)·swap_long + f·swap_short`, annualisée à **365 nuits**
(une position tenue en continu est facturée 7 nuits/semaine via le jour triple — voir §1.3).

| instrument | ère | f=0 (long) | f=0.25 | **f=0.50** | f=0.75 | f=1 (short) | FLAT | fraction short d'équilibre |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| **US100** | full 2013-26 | −6.32 | −5.12 | **−3.91** | −2.71 | −1.51 | **0.00** | **inatteignable** |
| US100 | ZIRP 13-21 | −5.23 | −4.57 | **−3.91** | −3.25 | −2.60 | 0.00 | inatteignable |
| US100 | haut-taux 23-26 | −9.15 | −6.53 | **−3.91** | −1.29 | **+1.33** | 0.00 | **0.873** |
| **GER40** | full | −4.47 | −3.88 | **−3.30** | −2.71 | −2.13 | 0.00 | inatteignable |
| GER40 | haut-taux | −6.77 | −5.03 | **−3.30** | −1.56 | +0.18 | 0.00 | **0.974** |
| **XAUUSD** | full | −5.66 | −5.02 | **−4.38** | −3.74 | −3.10 | 0.00 | inatteignable |
| XAUUSD | haut-taux | −8.49 | −6.44 | **−4.38** | −2.32 | −0.27 | 0.00 | **inatteignable** |
| **USDJPY** | full | **−0.08** | −1.24 | **−2.39** | −3.54 | −4.70 | 0.00 | inatteignable (c'est le **LONG** qui porte) |
| USDJPY | haut-taux | **+2.50** | +0.05 | −2.39 | −4.83 | −7.28 | 0.00 | inatteignable |

### 1.1 Trois faits que cette table impose

**(a) La colonne f=0.50 est constante à travers les ères.** −3.91 sur US100 en ZIRP comme en
2023-2026. Ce n'est pas une coïncidence : à f=0.50 la facture vaut `(sL+sS)/2 = −(mL+mS)/2`, soit
le markup pur — le taux s'annule exactement. **Une sleeve two-sided équilibrée est un hedge parfait
du risque de taux sur son portage, et ce qui reste est le péage du broker : irréductible,
invariant, payé quel que soit le côté.**

**(b) La neutralité de portage est inatteignable presque partout.** Elle exige `swap_short > 0`,
c'est-à-dire que le taux directeur dépasse le markup côté short. Sur l'historique complet : **jamais**,
sur aucun des 4 instruments du livre. Dans la seule ère haut-taux : **87.3 % de short sur US100**,
**97.4 % sur GER40**, et **toujours inatteignable sur l'or et sur USDJPY**. Une sleeve à 87 % short
n'est pas « two-sided » — c'est un short déguisé, qui porte toute la prime de risque à l'envers.

**(c) FLAT domine strictement le short en portage, dans toutes les ères sauf une.**
Le portage d'une position flat est **exactement zéro**. Sur l'historique complet, `swap_short` est
négatif partout ⇒ **rester flat coûte moins cher que d'être short.** C'est le point que la prémisse
de la mission ratait : *les sleeves du livre ne sont pas « long au lieu de short », elles sont
« long ou FLAT »*, et le livre déployé est flat **60.5 %** des jours (chiffre canonique CLAUDE.md,
corroboré ici indépendamment : la spec or live en long-only est en marché **40.4 %** du temps).
L'alternative au côté cher n'est pas le côté bon marché — **c'est l'absence de côté, qui est gratuite.**

### 1.2 Le crédit de portage côté short est un RÉGIME, pas une propriété

`short_carry_regime.csv` — part des jours 2013-2026 où `swap_short > 0` :

| | US500 | US100 | US30 | GER40 | XAUUSD | XAGUSD | USDJPY |
|---|--:|--:|--:|--:|--:|--:|--:|
| % jours à portage short positif | 26.8 | **26.8** | 26.8 | 13.7 | 10.6 | 27.4 | **0.0** |
| 1er jour | 2022-10-31 | 2022-10-31 | 2022-10-31 | 2023-03-31 | 2023-05-01 | 2022-09-30 | **jamais** |
| portage short moyen 2013-2021 (%/an) | −2.60 | **−2.60** | −2.60 | −2.95 | −4.19 | −2.57 | −3.69 |
| portage short moyen 2023-2026 (%/an) | +1.32 | **+1.33** | +1.32 | +0.18 | **−0.27** | +1.35 | **−7.28** |

**L'observation qui motive la mission est datée du 2022-10-31.** Sur 73 % des 13 dernières années,
le short payait AUSSI — et sur l'or il paie encore aujourd'hui. Construire une sleeve sur ce
différentiel, c'est parier que la Fed reste au-dessus de 3.3 % (le markup court US100) indéfiniment.

### 1.3 Deux corrections d'annualisation

- **Annualiser un swap à 252 nuits sous-estime la facture de 45 %.** Une position tenue en continu
  est facturée **365 nuits/an** (les week-ends passent par le jour triple : vendredi indices,
  mercredi métaux/FX). Le « ~550 bps/an » du brief sur US100 est le différentiel × 252 ; à 365 il
  vaut **810 bps/an**. Cela ne change pas le verdict, mais toute facture de swap doit être citée
  **avec son compte de nuits tenues** (continu 365 · hors jour triple 208 · sleeve overnight Mon+Mar 104).
- **Ancre GER40 : vérifiée périmée, indépendamment.** Facturé live mesuré (`swaps_billed_live.csv`,
  4 nuits) : GER40 **−1.6726 bps/nuit** contre −1.564 en spec ⇒ **+6.9 %**, conforme au +6.7/+7.3 %
  annoncé. US100 facturé **−2.0445** contre −2.1257 ⇒ **−3.8 %** (la spec sur-facture légèrement).
  Sensibilité (`ger40_anchor_sensitivity.csv`) : à +6.9 % la vraie subvention GER40 passe de
  0.948 à **1.293 %/an**, à +15 % à 1.698 %/an. **Le verdict ne bouge pas** : il faudrait ×7 pour
  atteindre la dérive de 9.44 %/an.

---

## 2. POURQUOI : la décomposition du swap

`markup_asymmetry.csv` · `swap_decomposition.csv` · `sign_flip_hurdle.csv`

    swap_long_t  = −(r_t + mL)          r_t = taux de référence 3M
    swap_short_t = +(r_t − mS)          mL, mS = markups du broker, par côté

    différentiel en faveur du short = swap_short − swap_long = 2·r_t + (mL − mS)

**Le terme `2·r_t` n'est PAS de l'alpha** : c'est exactement l'accumulation sans risque qu'un short
abandonne, et la dérive du long la contient déjà. Il s'annule dans la décision de signe. **Seul
`(mL − mS)` est une vraie subvention pour prendre le côté short.**

Sur le snapshot MT5 **mesuré** (spec_v22 `measured_specs`, lu 2026-06-10), taux 3M au 2026-05-31 :

| | swap_long | swap_short | différentiel | dont **cash** | dont **VRAIE subvention** | part alpha |
|---|--:|--:|--:|--:|--:|--:|
| **US100** (USD 3.59 %) | −2.1257 | +0.0917 | 2.2174 | 1.9671 | **0.2503** (0.914 %/an) | **11.3 %** |
| **GER40** (EUR 2.03 %) | −1.5640 | −0.1933 | 1.3707 | 1.1111 | **0.2596** (0.948 %/an) | **18.9 %** |
| XAUUSD | −1.5180 | −0.3358 | 1.1822 | 1.9671 | −0.7849 | *n.i.* |
| USDJPY | +0.0599 | −1.2665 | −1.3264 | 1.2719 | −2.5983 | *n.i.* |

⚠ **La scission n'est interprétable que là où la référence est univoque.** Sur US100 (USD) et GER40
(EUR) elle l'est. Sur l'or le financement fait intervenir le taux de prêt (lease rate), sur USDJPY
le tom-next diffère du différentiel 3M : la décomposition y rend `mL = −2.54 %/an` (un markup
négatif, impossible) ⇒ **elle est mal spécifiée pour ces deux-là, et je ne la cite pas.** Le
`markup_n_distinct_values = 1` sur toute la période dans `swap_decomposition.csv` est un **artefact
de construction** de `costs.build_swap_model` (les markups y sont calibrés une fois sur le snapshot
2026-05-31), pas une découverte — c'est pourquoi §2 est calculé sur le snapshot brut et pas sur le panel.

### 2.1 Le seuil de bascule de signe — forme SANS référence

Sans aucune hypothèse de taux : le short bat le long cette nuit **ssi**

    R_t  <  (swap_short − swap_long) / 2   par nuit tenue

| | seuil (%/an, 365n) | dérive mesurée 2013-26 (%/an) | **écart à franchir** | short incond. − long incond. |
|---|--:|--:|--:|--:|
| **US100** | **4.05** | 19.34 | **15.29** | **−30.59 %/an** |
| GER40 | 2.50 | 10.49 | 7.99 | −15.98 %/an |
| XAUUSD | 2.16 | 7.13 | 4.97 | −9.94 %/an |
| USDJPY | −2.42 | 4.45 | 6.87 | −13.74 %/an |

**Lecture.** Sur US100, tout le « le swap punit le long » revient à ceci : le seuil de bascule
passe de « battre le cash » à « battre le cash **+ 0.46 %/an** ». La subvention déplace la barre de
**0.46 point** alors que la barre est à **15.29 points**. **Elle en couvre 3.0 %.**
Un short inconditionnel sur US100 perd **30.6 %/an** contre le long. C'est le chiffre demandé.

### 2.2 Le corollaire, qui est le vrai résultat structurel

Puisque le markup est payé des deux côtés et que le reste du différentiel est le taux sans risque :

> **Sur un CFD, le côté optimal est le signe du rendement EXCÉDENTAIRE attendu, et le portage
> n'offre aucune subvention pour le découvrir.** La question « peut-on être short profitablement »
> est *identiquement* la question « peut-on prédire une prime de risque négative » — ni plus facile,
> ni subventionnée. **C'est pour cela que tout le livre est long : ce n'est pas un biais de
> sélection, c'est le seul côté où une prime existe.**

---

## 3. EXISTE-T-IL UN SIGNAL TWO-SIDED ? (L25, gate au GROSS)

`two_sided_gross_gate.csv` — 3 règles × 7 instruments = **21 essais déclarés**.

Règles pré-enregistrées, **aucun tuning**, toutes à **zone morte** — donc les jambes sont
**disjointes** et la jambe short n'est jamais `−side_long` (24/24 paires miroir ont déjà été
trouvées dans ce dépôt). Preuve rapportée par cellule : `union_share = long_share + short_share`,
mesuré entre **0.386 et 0.876**, jamais 1.000.

- **R1** TSMOM blend `sign{60,120,250}`, zone morte 0.34 — la spec or **live, verbatim**
- **R2** momentum 12-1, zone morte 2 % — la spec J1 live, généralisée two-sided
- **R3** état de VOLATILITÉ : long si rv20 < 0.80×médiane 1 an, short si > 1.25× — un signe piloté
  par un prédicteur de **variance**, pas de prix (L54 transposée dans le domaine du signe)

### Résultat

| gate | passe |
|---|---|
| **L25 — les DEUX jambes positives à coût nul** | **0 / 21** |
| jambe short positive au gross | **1 / 21** (USDJPY R3 : **+0.164 bps/barre, t_HAC 0.061**) |
| L58 — les deux jambes battent leur baseline inconditionnelle | 3 / 21 |

Jambes short au gross, quelques cellules : US100 R1 **−22.73 bps/barre** (t −1.46), US500 R1
**−19.80** (t −1.83), GER40 R3 **−12.40** (t −1.65), XAUUSD R1 **−2.06** (t −0.53).
**La jambe short n'est pas marginale — elle est franchement négative**, avant tout coût et avant
tout swap.

### 3.1 Le piège L58, traité de front

La baseline inconditionnelle d'une jambe short est **négative** (−dérive) : c'est le cas dangereux
annoncé. En corrigeant, **3 cellules passent** (XAUUSD R1, XAUUSD R2, USDJPY R2) — mais elles
passent uniquement parce qu'on leur soustrait une baseline négative. Traduction honnête : *« ce
short perd moins qu'un short au hasard »*. Ce n'est pas une jambe positive, c'est un énoncé de
timing de bêta — que la §5 exécute.

---

## 4. NET APRÈS PORTAGE RÉEL, par jambe et par direction

`net_by_sign_policy.csv` — portage facturé par barre selon le signe **réellement tenu**
(`swap_long_t` ou `swap_short_t` × multiplicateur de jour triple contractuel), coût RT mesuré
(`COST_AUDIT.md` : indices 1.47-1.82 bps, XAUUSD 1.84, XAGUSD 6.37, FX 1.50) sur `|Δposition|`.

**Passer two-sided vs rester long-only : 0 / 21 cellules gagnantes. Médiane −3.71 %/an.**

| | US100 R1 | US100 R2 | XAUUSD R1 | XAUUSD R2 |
|---|--:|--:|--:|--:|
| LONG_ONLY net %/an | **+4.85** | **+7.78** | **+3.20** | **+2.51** |
| TWO_SIDED net %/an | +1.14 | +5.79 | +1.81 | −0.37 |
| SHORT_ONLY net %/an | −3.71 | −1.99 | −1.39 | −2.88 |
| **Δ two-sided − long-only** | **−3.71** | **−1.99** | **−1.39** | **−2.88** |

**SHORT_ONLY est négatif dans 21/21 cellules**, Sharpe net entre **−0.18 et −0.65**.

### 4.1 Le fait contre-intuitif : two-sided AUGMENTE la facture de portage

| US100 R1 | LONG_ONLY | TWO_SIDED | SHORT_ONLY |
|---|--:|--:|--:|
| temps en marché | 62.8 % | 69.1 % | 6.2 % |
| **portage %/an** | **−3.92** | **−3.99** | −0.07 |

La sleeve two-sided paie **plus** de portage que la long-only. Raison : les 6.2 % de jours short
qu'elle ajoute étaient des jours **FLAT** sous long-only — donc à portage **zéro**. Ajouter du
short n'échange pas du portage cher contre du portage bon marché : **cela échange du portage nul
contre du portage négatif** (et, sur 73 % de l'historique, `swap_short < 0`). Vrai sans exception :
la facture two-sided est plus lourde que la long-only sur **21/21** cellules.

---

## 5. L38 — orthogonalité (obligatoire)

`l38_orthogonality.csv` — 63 régressions HAC(6) sur un buy-and-hold vol-targeté 10 % du même instrument.

| politique | R² moyen | R² médian | cellules **R² > 30 %** |
|---|--:|--:|--:|
| **LONG_ONLY** | **41.3 %** | 40.4 % | **14 / 21 ⇒ ÉCHEC L38** |
| SHORT_ONLY | 17.6 % | 18.3 % | 3 / 21 |
| TWO_SIDED | 13.9 % | 8.8 % | 3 / 21 |

Deux lectures, et la seconde est celle qui compte :

1. **Le two-sided est bel et bien plus orthogonal** — R² divisé par 3. La prémisse « le signe
   décorrèle » est **vraie**.
2. **Et c'est sans valeur : sur les 63 régressions, ZÉRO n'a un alpha positif significatif**
   (`alpha_t > 2`). Le meilleur alpha two-sided de tout le balayage est **+1.09 bps, t 0.58** (US100 R3). Les 3 rescapés du gate
   L58 (§3.1) rendent des alphas de **−0.43 / −1.24 / +0.14 bps**, t entre **−0.34 et +0.18**.

**⇒ L'axe du signe livre exactement ce que le brief annonçait comme insuffisant : de la
décorrélation, et rien d'autre.** Mesuré ici sur le livre : corr(Δp, remplissage calendaire) = −0.06
contre +0.82 pour le Sharpe solo. Une sleeve orthogonale de Sharpe **−0.4** n'achète pas de p(pass).

Note incidente sur le livre existant : **LONG_ONLY échoue L38 dans 14/21 cellules (R² médian 40 %)**.
Les sleeves longues du livre *sont* largement du timing de bêta — ce n'est pas une découverte de
cette étude, mais elle le re-mesure indépendamment.

---

## 6. Le kill est-il robuste ?

| test | résultat |
|---|---|
| **Block bootstrap** (Politis-Romano, blocs 21j, 5 000 tirages, jamais iid) sur Δ = two-sided − long-only | **4/21** IC95 excluent zéro, **les 4 du côté NÉGATIF** ; `p(Δ>0)` médian **0.11**, max **0.26** |
| **Walk-forward** 5 folds expansifs, signe OOS de Δ | médiane **1/5** folds positifs ; **0/21** cellules à ≥3/5 |
| **Ère haut-taux 2023-2026 seule** (l'objection la plus forte) | **0/21** cellules où le two-sided gagne. Δ médian **−3.44 %/an** |
| **DSR** (`dsr.py` racine, **rf = 0**, n_trials = 21, `std_sr_trials` calibré) sur la meilleure cellule two-sided (US100 R2, SR **0.281**) | **DSR 0.174 — FAIL** (benchmark 0.551) |

DSR et walk-forward sont exigés tous les deux : ils sont orthogonaux (DSR 0.982 déjà observé avec
1-2 folds/5 dans ce dépôt). Ici **les deux échouent**, dans le même sens.

**L'ère 2023-2026 est le test décisif** et il tranche net : c'est la seule fenêtre où
`swap_short > 0` sur les indices, donc la seule où la prémisse de la mission tient — et le
two-sided y perd quand même sur **21/21** cellules, parce que la dérive actions y a été forte.
Le portage devient favorable au short précisément quand les taux montent, c'est-à-dire quand
`drift = rf + ERP` monte aussi. **Les deux termes bougent ensemble, et le second est plus gros.**

---

## 7. Conformité méthodologique

- **Horloge (L56)** — barres quotidiennes ancrées sur **l'instant de facturation du swap** :
  00:00 heure broker (EET/EEST) = **17:00 America/New_York**, ce qui rend « une barre = une nuit de
  swap » vrai par construction. ⚠ **Divulgation** : EET et US bascules DST à des dates différentes
  ⇒ l'ancre est décalée d'une heure pendant ~4 semaines/an (8 mars→29 mars et 25 oct→1 nov en 2026),
  soit **7.7 % de l'échantillon**. Sans effet matériel à fréquence quotidienne, mais c'est déclaré.
- **Données** — `data/deep_history_utc/` uniquement (vrai UTC), **jamais** `data/panels/m5_indices/`
  (EET étiqueté UTC). Cache horaire privé, jamais partagé avec un agent frère.
- **L60** — `l60_zero_range_diag.csv`, part de barres H1 à fourchette nulle : EURUSD 0.39 %,
  XAUUSD 0.51 %, US100 0.73 % (propres) ; **XAGUSD 5.53 %** (gardé, signalé), **COPPER 6.44 %**
  (⇒ **exclu** du panel de tests). UKOIL/USOIL exclus aussi : leur markup mesuré est de
  **20.1 et 26.6 %/an**, aucune sleeve tenue n'y survit, quel que soit le signe.
- **L59** — entrée ET sortie sont la clôture 17:00 NY du jour du signal +1. **Aucune géométrie
  stop-entry / bracket-exit n'est utilisée**, donc la re-tarification L59 des sorties ne s'applique
  pas ici. Énoncé plutôt que supposé.
- **T-1 / T** — signal calculé jusqu'à la clôture de la barre t−1, position portée sur la barre t
  (`sig.shift(1)`), sur les 21 cellules sans exception.
- **L58** — chaque jambe est notée en brut ET contre l'espérance inconditionnelle de la MÊME forme
  de trade ; l'écart entre les deux gates (0/21 vs 3/21) est rapporté, pas arbitré en silence.
- **HAC** — `cov_type='HAC', maxlags=6` sur toutes les moyennes de jambes et sur tous les Δ.

**Budget d'essais** : 21, déclarés avant exécution, aucune règle ajoutée ni seuil bougé après
lecture des résultats. Aucun paramètre optimisé : R1 et R2 sont les specs live copiées, R3 a des
seuils fixes (0.80 / 1.25 / 20 / 252) posés avant tout calcul.

---

## 8. Verdict

**L'axe du SIGNE est FERMÉ, par un kill MÉCANIQUE** — au sens de la politique de ré-ouverture
(§registre L) : la jambe short a un gross **négatif** à coût **nul** dans 20/21 cellules, et le
différentiel de portage qui devait la financer est, à 89 %, le taux sans risque que le long
touchait déjà. Ce n'est ni un kill de véhicule, ni de coût, ni de puissance, ni de géométrie.
**Recalibrer une statistique ne ressuscite pas un gross de −22.7 bps.**

Ce que ça explique, et qui est le vrai livrable : **le livre n'est pas long par accident ni par
biais de sélection.** Il est long parce que le portage n'offre aucune subvention pour découvrir un
côté short — le seul côté où une prime de risque existe est le long, et le broker prélève son
markup sur les deux. Le levier de portage réellement disponible n'est pas le SIGNE : c'est le
**DUTY CYCLE**, parce que FLAT coûte exactement zéro et domine strictement le short sur 73 % de
l'historique.

### Ce qui n'est PAS fermé par ce travail
- **Le duty cycle.** Réduire le temps en marché est le seul levier de portage démontré ici comme
  gratuit. Non testé : cela retire aussi du rendement, et l'arbitrage n'est pas mesuré.
- **USDJPY long.** C'est le seul instrument du livre dont le côté tenu porte **positivement**
  (+2.50 %/an en 2023-2026 à duty 100 %). La sleeve J1 est du bon côté du carry ; elle échoue
  ailleurs (L38 R² 45 %), pas ici.
- **L'intraday-flat**, qui ne paie aucun swap et sort donc entièrement de ce cadre (soumis à L33b).

---

## 9. Ce que ça ne prouve PAS

1. **Ça ne prouve pas qu'aucun signal two-sided n'existe.** 21 essais sur 3 familles de règles, ce
   n'est pas un balayage. Ça prouve que **les trois règles de signe déjà présentes dans le livre**
   n'en produisent pas, et — plus fort — que **l'incitation de portage censée financer une telle
   sleeve n'existe pas** (§2). Le second point est structurel et vaut pour tout signal ; le premier
   ne vaut que pour ces 21 cellules.
2. **Ça ne prouve pas que le short est mort en général** — seulement sur des **CFD FTMO tenus la
   nuit**. Sur un véhicule sans markup de financement (futures, ~0.4 bps RT, financement implicite
   dans le prix), la §2 entière tombe : il n'y a plus de `mL`, plus de `mS`. **Le compte IBKR perso
   est explicitement hors de portée de cette étude.** C'est un 4ᵉ dossier d'affilée dont la maison
   naturelle n'est pas FTMO.
3. **La décomposition markup/taux n'est valide que sur US100 et GER40.** Elle est mal spécifiée sur
   l'or (lease rate) et sur USDJPY (tom-next ≠ 3M) — je la rapporte comme non interprétable là, et
   toutes les conclusions y reposent sur la forme **sans référence** du §2.1, qui n'a besoin
   d'aucun taux.
4. **Le panel de swaps est un MODÈLE, pas un relevé.** `costs.build_swap_model` génère
   `rate_t ± markup` avec markups calibrés une fois au 2026-05-31. Les 13 ans de variation de
   portage sont donc une **reconstruction**, validée seulement à deux points (snapshot MT5
   2026-06-10, 4 nuits facturées live). Si FTMO a changé ses markups entre 2013 et 2022, l'histoire
   du portage de cette étude est fausse — mais **§2.1, §3 (gross à coût nul) et §5 n'en dépendent
   pas.**
5. **La dérive mesurée est un échantillon, pas une constante.** 19.34 %/an sur US100 2013-2026,
   t 2.79. L'écart au seuil (15.29 points) est si large que même un ERP divisé par 3 ne le referme
   pas — mais si les actions entraient dans une décennie à ERP négatif, la §2.2 dit que le short
   deviendrait le bon côté. **Elle ne dit pas qu'on saurait le voir à l'avance**, et c'est
   précisément le point qui n'a pas été testé.
6. **Rien ici n'est un test de p(pass).** Aucun placebo à autocorrélation appariée n'a été construit,
   parce qu'aucune cellule n'a atteint un stade où un p(pass) aurait un sens. Toute reprise qui
   voudrait revendiquer un p(pass) doit le construire.

---

### Fichiers

| fichier | contenu |
|---|---|
| `headline_carry_by_short_fraction.csv` · `carry_by_duty_cycle.csv` | §1, table de tête |
| `breakeven_short_fraction.csv` · `carry_vs_short_fraction.csv` | fraction short d'équilibre, 18 instruments × 3 ères |
| `markup_asymmetry.csv` · `sign_flip_hurdle.csv` · `swap_decomposition.csv` | §2, décomposition et seuil |
| `short_carry_regime.csv` · `ger40_anchor_sensitivity.csv` | §1.2, §1.3 |
| `two_sided_gross_gate.csv` | §3, les 21 essais au gross |
| `net_by_sign_policy.csv` · `sign_flip_threshold.csv` | §4 |
| `l38_orthogonality.csv` | §5, 63 régressions |
| `delta_block_bootstrap.csv` · `delta_walkforward.csv` · `delta_by_rate_era.csv` · `dsr_best_two_sided.csv` | §6 |
| `l60_zero_range_diag.csv` | §7, contrôle L60 |
| `code/` | `build_daily.py` · `carry_arithmetic.py` · `markup_asymmetry.py` · `two_sided_battery.py` · `net_and_orthogonality.py` · `robustness.py` · `headline_carry_table.py` |

Interpréteur `/usr/bin/python3` (pandas 2.2.3). Aucun blob data. Caches en chemin privé de session.
