# RÉSULTATS — Cycle d'adjudication du Trésor US (concession d'adjudication)

> Pré-enregistrement figé **avant** tout calcul : `PREREGISTRATION.md`.
> Item `E020` de l'inventaire 2026-07-30 — « jamais mesuré ». **Il l'est maintenant.**
> Interpréteur `/usr/bin/python3`. Logs bruts : `data/log_step*.txt`. Rien n'a été commité.
>
> ## VERDICT : **REJECTED — COST-DEAD & UNDERPOWERED**
> Le mécanisme n'est **pas** redondant avec B1 (c'est le point neuf et il est propre :
> recouvrement **0,0 %**, ρ **−0,001**). Il est tué ailleurs : l'effet primaire vaut
> **+7,72 bps/événement, t_HAC 1,75, IC95 [−1,6 ; +17,0]** — sous le gate de coût
> (9,9 bps requis), sous le DSR (0,863), et **dilutif** pour le book existant
> (**ΔSR = −0,072 brut, −0,162 net**). La **jambe de concession — le mécanisme lui-même —
> est nulle en daily** (+1,52 bps, t 0,48).

---

## 1. Le piège n°1 tranché EN PREMIER — recouvrement et corrélation avec B1

Le calendrier du Trésor se scinde en deux blocs, et la scission est **institutionnelle,
pas empirique** (elle était écrite dans le pré-enregistrement §2 avant toute mesure) :

| Cluster | jour-du-mois médian | n adjudications | **% événements touchant B1** | **% jours-de-position dans B1** | **ρ(rendements) vs B1** |
|---|---:|---:|---:|---:|---:|
| **10y — PRIMAIRE** | 10 | 272 | **0,0 %** | **0,0 %** | **−0,001** |
| mi-mois 3/10/30 | 9-11 | 725 | 0,2 % | 0,0 % | −0,001 |
| 20y | 19 | 76 | 1,4 % | 0,8 % | +0,002 |
| **month-end 2/5/7** | 25-27 | 823 | **80,8 %** | **38,1 %** | **+0,457** |
| tous coupons | — | 1 624 | 36,6 % | 17,2 % | +0,299 |

**K1 ne se déclenche pas sur la cellule primaire — et c'est le seul bon résultat du dossier.**
Le cluster 10y est *structurellement* disjoint de B1 : mi-mois contre fin-de-mois,
recouvrement exactement nul, corrélation quotidienne −0,001. Si un effet d'adjudication
existait sur le 10y, il serait **authentiquement neuf**.

**En revanche le cluster month-end EST B1**, et le repo aurait payé le piège une troisième
fois sans ce test. Effet du cluster 2/5/7 :

| Cluster 2/5/7 sur ZN | n | mean bps | t_HAC | p_block | PRE | t_PRE | POST | t_POST |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| brut | 594 | **+10,40** | **2,80** | 0,0040 | +1,69 | 0,69 | **+8,71** | **2,91** |
| **hors événements chevauchant B1** | **114** | +14,91 | **1,49** | 0,1178 | +16,12 | 2,47 | −1,21 | −0,15 |

Le `t = 2,80` du cluster month-end s'effondre à **1,49** dès qu'on retire le chevauchement
B1, et sa significativité vivait **entièrement dans la jambe LONGUE** (`t_POST 2,91`) —
c'est-à-dire dans le rallye month-end de B1 lui-même. Même signature sur les deux seules
cellules « significatives » de tout le dossier : **7y sur ZN (t 2,58)** et **5y sur ZF
(t 1,81)**, toutes deux du cluster month-end, toutes deux portées à 100 % par la jambe
longue (POST t +2,88 et +3,25 ; PRE t +0,65 et −0,79). **Ce ne sont pas des adjudications,
c'est B1 vu sous un autre calendrier.**

---

## 2. L'effet primaire — 10y sur ZN, 2000-2026

`S_V` = SHORT `close(t−3)→close(t−1)` puis LONG `close(t−1)→close(t+2)`.
n = 251 événements (272 adjudications 10y, **18 exclues** parce que l'annonce du Trésor
était postérieure au close d'entrée — filtre T−1 fail-loud, cf. §6).

| Cellule | n | mean bps | t_HAC | p_block | IC95 bps | SR_ann | hit |
|---|---:|---:|---:|---:|---|---:|---:|
| **1 · `S_V` brut** | 251 | **+7,72** | **1,75** | 0,105 | **[−1,63 ; +17,00]** | 0,36 | 53,4 % |
| 2 · **PRE (short)** = *la concession* | 251 | **+1,52** | **0,48** | 0,618 | [−4,51 ; +7,40] | 0,11 | 57,8 % |
| 3 · POST (long) = *la reprise* | 251 | +6,20 | 1,37 | 0,130 | [−1,86 ; +14,24] | 0,34 | 53,0 % |
| `S_V` demeaned | 251 | +7,59 | 1,73 | 0,110 | [−1,75 ; +16,88] | 0,36 | 53,4 % |
| PRE demeaned | 251 | +1,77 | 0,55 | 0,562 | [−4,26 ; +7,65] | 0,13 | 59,0 % |
| POST demeaned | 251 | +5,83 | 1,29 | 0,155 | [−2,23 ; +13,86] | 0,32 | 53,0 % |

Contexte : dérive inconditionnelle ZN 2000-2026 = **+0,124 bps/jour** (+0,31 %/an),
vol quotidienne 38,6 bps. Le demean ne change quasiment rien — **l'effet n'est pas du beta
obligataire**, il est simplement **trop petit**.

**Le point qui décide, et il est structurel, pas statistique :** la jambe qui porte le
mécanisme — la **concession pré-adjudication** — vaut `+1,52 bps` avec `t = 0,48`.
Elle est **nulle**. Tout le `+7,72` vient de la jambe POST, qui est elle-même à `t 1,37`.
On n'a donc **ni un effet significatif, ni un effet situé là où la théorie le place.**

### Cohérence temporelle — le contraste avec B1 est brutal

| | B1 (référence) | Adjudication 10y |
|---|---|---|
| années positives | **23 / 23** | **17 / 27 (63 %)** |
| jambe mécanisme, années positives | — | **PRE : 11 / 27** |
| t_HAC | 4,65 | 1,75 |

---

## 3. Kill rules — verdicts

| # | Règle | Mesure | Verdict |
|---|---|---|---|
| **K1** | Redondance B1 | recouvrement **0,0 %**, ρ **−0,001** sur la primaire | **NON DÉCLENCHÉE** ✅ |
| **K2** | Placebo apparié (L49) | pré-enregistré : PASS — **mais la version pré-enregistrée est INVALIDE** (§4). Version corrigée : contraste **+8,25 bps, t_HAC 1,68, p 0,094** | **NE FRANCHIT PAS** ⚠️ |
| **K3** | Régime (L31) | t = 0,94 / 1,32 / 0,74 (pré-QE / QE / QT) — faible **partout**, pas porté par un régime | **NON DÉCLENCHÉE** (mais aucun régime ne sauve) |
| **K4** | **Coût** | brut **7,72** < gate 3× central **9,9** (et < 18,3 stress) | **DÉCLENCHÉE — COST-DEAD** ❌ |
| **K5** | Signe | signe conforme au mécanisme (V positif) | non déclenchée |
| **K6** | Two-sided (L25) | PRE +1,77 dm / POST +5,83 dm — aucune jambe négative, mais **la jambe mécanisme est nulle (t 0,48)** | non déclenchée *stricto sensu*, **échec de fond** |
| **K7** | Roll de contrat | **0 / 251** événements en fenêtre de roll (10y = dom 7-12, roll ZN = dom ≥ 18) | **impossible** ✅ |
| **K8** | Admission marginale | **ΔSR = −0,072** brut, **−0,162** net central, **−0,238** net stress | **DÉCLENCHÉE** ❌ |
| **K9** | DSR (`n_trials`=16, σ mesuré) | **DSR = 0,863** sur la primaire | **DÉCLENCHÉE** ❌ |

### Le split de régime, en détail (L31) — instructif même s'il ne tue pas

| Régime | n | `S_V` brut | t | dérive ZN | PRE | t_PRE | POST | t_POST |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pré-QE 2000-2008 | 53 | +9,68 | 0,94 | +1,180 bps/j | **−9,75** | **−2,21** | +19,42 | +1,90 |
| QE/ZIRP 2009-2021 | 148 | +6,82 | 1,32 | +0,071 bps/j | +0,67 | +0,16 | +6,16 | +1,19 |
| QT 2022-2026 | 50 | +8,29 | 0,74 | −1,623 bps/j | **+15,99** | **+2,77** | −7,69 | −0,83 |

La somme `S_V` est remarquablement stable (~7-10 bps) et **jamais significative** ; mais
la **décomposition s'inverse complètement** entre régimes, et elle s'inverse **dans le sens
de la dérive des taux** (bull → la jambe short perd, bear → elle gagne). Une concession de
dealer ne devrait pas changer de signe parce que le marché obligataire est haussier ou
baissier. C'est le signe que le daily ne mesure pas la concession mais du bruit de tendance.

### Grille de robustesse (cellules 11-16, 16 cellules calculées)

| k \ m | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|
| 2 | 4,36 (1,31) | 6,98 (1,82) | **9,72 (2,01)** | 4,14 (0,73) |
| **3** | 5,79 (1,38) | **7,72 (1,75)** ★ | 10,04 (1,90) | 4,82 (0,79) |
| 4 | 5,52 (0,97) | 7,25 (1,38) | 9,36 (1,56) | 1,64 (0,25) |
| 5 | −0,69 (−0,06) | 3,24 (0,31) | 5,32 (0,48) | −3,72 (−0,35) |

*(mean bps, t_HAC entre parenthèses ; ★ = cellule primaire)*
Aucune cellule n'atteint t = 2,5. Le meilleur (2,01) est un maximum de grille. Le motif
`m = 3 monte puis m = 4 s'effondre` n'est pas une décroissance de mécanisme, c'est du bruit.
La jambe PRE est nulle sur **toute** la grille (k = 2,3,4) et négative à k = 5.

### Transfert de maturité (cellules 5-7)

| Cellule | n | mean bps | t_HAC | PRE (t) | POST (t) |
|---|---:|---:|---:|---|---|
| 6 · 30y sur ZB | 221 | +7,25 | 0,83 | +4,48 (0,72) | +2,77 (0,40) |
| 7 · 3y sur ZF | 179 | +2,01 | 0,39 | +2,35 (0,89) | −0,34 (−0,10) |
| *5y sur ZF (exploratoire)* | 241 | +8,22 | 1,81 | −1,95 (−0,79) | **+10,16 (3,25)** |
| *7y sur ZN (exploratoire)* | 208 | +12,62 | 2,58 | +2,03 (0,65) | **+10,58 (2,88)** |

Les deux maturités **pré-enregistrées** (30y, 3y) sont mortes. Les deux qui « marchent »
sont exploratoires, sont du cluster month-end, et sont **B1** (§1).

---

## 4. ⚠️ CORRECTION MÉTHODOLOGIQUE — le placebo pré-enregistré était biaisé

Le placebo pré-enregistré (même jour de semaine + jour-du-mois ±3 + **blackout de ±3 jours
autour de toute adjudication long-end**) a rendu un **PASS** : réel +7,72 contre médiane
placebo **−5,88**, p95 +3,07, `P(placebo ≥ réel) = 0,005`.

**Ce PASS est un artefact et je le rejette.** Une ligne de contrôle suffit à le voir : la
forme `S_V` appliquée à **tous** les jours de bourse vaut **+0,102 bps** — exactement la
valeur impliquée par la dérive (+0,124). Un placebo correct doit donc avoir une base ≈ 0 ;
celui-ci a une base à **−5,5 bps**.

Diagnostic (`log_step5_placebo_audit.txt`) — la forme `S_V` a une **forte saisonnalité de
jour-du-mois** sur ZN :

| jour du mois | 1-5 | 6-10 | 11-15 | 16-20 | 21-25 | 26-31 |
|---|---:|---:|---:|---:|---:|---:|
| mean `S_V` (bps) | **−9,21** | −0,11 | +4,71 | **−10,79** | +7,21 | **+7,81** |
| t_HAC | −3,18 | −0,04 | +1,61 | −3,38 | +2,53 | +2,85 |

Le blackout retire 38,3 % des jours, **centrés sur le mi-mois** (dom médian 12), et repousse
donc le pool placebo vers le seau **dom 16-20 qui vaut −10,79 bps**. Le placebo ne mesurait
plus « un jour ordinaire comparable » mais « un jour de la poche calendaire négative ».

Contribution de chaque contrainte, isolée :

| pool placebo | moyenne du pool |
|---|---:|
| aucune contrainte | +0,10 bps |
| jour de semaine seul | −1,08 |
| jour-du-mois ±3 seul | +1,56 |
| blackout seul | +0,69 |
| **jour de semaine + dom ±3 (SANS blackout)** | **+0,44** ← base saine |
| jour de semaine + dom ±3 + blackout *(pré-enregistré)* | **−5,54** ← base biaisée |

**Placebo corrigé (base saine).** Jours d'adjudication contre jours non-adjudication
appariés en jour de semaine et jour-du-mois ±3, sans blackout :

| | n | mean bps | t_HAC |
|---|---:|---:|---:|
| jours appariés **non**-adjudication | 1 597 | −0,54 | −0,24 |
| jours d'adjudication 10y | 251 | +7,72 | +1,75 |
| **contraste (régression à variable muette)** | | **+8,25** | **+1,68** (p 0,094) |

Le contraste propre est donc `+8,25 bps, t 1,68, p 0,094` — **la même conclusion que le
t brut**, et il **ne franchit pas** le seuil. Le placebo ne sauve rien ; correctement
construit, il ne fait que confirmer.

> **Candidat-leçon (nommé, non numéroté — la numérotation se grave en réconciliation) :**
> `placebo-baseline-must-be-verified-against-the-unconditional`. Un placebo apparié peut
> **fabriquer** un PASS si ses contraintes d'appariement interagissent (ici blackout ⊗
> jour-du-mois) pour sélectionner une poche calendaire biaisée. Contrôle obligatoire, coût
> nul : **la moyenne du pool placebo doit égaler l'espérance inconditionnelle de la forme
> de trade** (ici la dérive). Si elle en dévie, c'est le placebo qu'il faut réparer, pas
> l'edge qu'il faut célébrer. Complète L49 (qui exige le placebo) par *comment le valider*.

---

## 5. Décision — compte personnel €13 k, ZN sur IBKR (ni barrière, ni horloge)

### 5.1 Économie du sleeve seul (1 contrat ZN, nominal $108 328, compte $14 040)

| | $/événement | SR annualisé (√12, L47) | $/an | %/an du compte | MaxDD |
|---|---:|---:|---:|---:|---:|
| brut | +83,60 (sd 798) | +0,363 | +1 003 | **+7,15 %** | −$6 447 = **−45,9 %** |
| **net central (3,3 bps)** | **+47,85** | **+0,208** | **+574** | **+4,09 %** | −$7 126 = **−50,8 %** |
| net stress (6,1 bps) | +17,52 | +0,076 | +210 | +1,50 % | −$8 671 = −61,8 % |

Granularité : 1 contrat ZN = **7,7× le nominal du compte** (marge ~$1 800 = 13 % — la marge
n'est **pas** la contrainte, le nominal l'est). Kelly plein sur la distribution mesurée =
14,2× — mais ce « Kelly » est calculé sur un Sharpe de 0,36 dont l'IC contient zéro : il
n'a **aucune valeur prescriptive**. ¼ Kelly = 3,55×, soit **moins d'un contrat** — le sleeve
n'est pas implémentable à la taille qu'il mériterait.

Un MaxDD de **−50,8 % du compte** pour **+4,09 %/an** au coût central : le ratio
rendement/drawdown est de 0,08. Sans barrière ni horloge, ce n'est pas *interdit* — c'est
simplement **sans intérêt**.

### 5.2 Δ marginal sur le book existant (B1 sur ZN) — `Portfolio/admission/marginal.py`, poids ERC

| | SR candidat | ρ vs book | **ΔSR** | IC95 ΔSR | verdict |
|---|---:|---:|---:|---|---|
| brut | +0,296 | −0,001 | **−0,072** | [−0,343 ; +0,204] | **FAIL** |
| net central | +0,169 | −0,001 | **−0,162** | [−0,431 ; +0,113] | **FAIL** |
| net stress | +0,062 | −0,000 | **−0,238** | [−0,507 ; +0,036] | **FAIL** |

- SR du book seul (B1 sur ZN) : **0,962** → combiné 0,890.
- **Seuil marginal** (ρ·SR_book) = −0,001 : à ρ ≈ 0, *toute* Sharpe positive est accrétive
  **à la marge infinitésimale**. Mais le **seuil au poids ERC est +0,398**, et le candidat
  plafonne à 0,296 brut / 0,169 net. L'ERC impose un budget de risque **égal** à un sleeve
  dont la Sharpe vaut le sixième de celle de B1 → **dilution mécanique**.
- **Effet minimum détectable de ΔSR = 0,230** sur n = 6 487 jours. Le ΔSR observé
  (−0,072 à −0,238) est **du même ordre que le bruit**. Autrement dit : on ne peut pas
  certifier que ce sleeve dégrade le book — on peut seulement affirmer qu'**on ne peut pas
  le certifier accrétif**, ce qui est la condition K8 pour refuser d'allouer.

> **Un ΔSR positif dans le bruit serait UNDERPOWERED, pas PASS. Ici l'estimation ponctuelle
> est en plus NÉGATIVE dans les trois scénarios de coût.**

---

## 6. Contrôles d'intégrité

- **Signal T−1 / trade T.** Le calendrier est public : lead d'annonce médian **6 jours**.
  Contrôle fail-loud `announcementDate ≤ date(t−3)` → **18 événements exclus** (6,6 %).
  Sensibilité : avec look-ahead autorisé n = 269, mean +8,82, **t 2,09** ; sans, n = 251,
  **t 1,75**. Le filtre T−1 coûte 0,34 de t-stat — il n'est **pas** ce qui tue le résultat,
  mais l'ignorer aurait suffi à faire franchir « t > 2 » à un effet qui n'y est pas.
- **Champs / sessions (L51-L52).** Aucun usage de `ZN=F.Open` (= ouverture Globex 18:00 ET
  de la veille). Tous les rendements sont `Close`→`Close` (settlement 15:00 ET).
- **Rendements excédentaires.** Futures entièrement collatéralisés ⇒ le rendement de prix
  **est** le rendement excédentaire ; aucune soustraction de DTB3 (justifié, pas omis).
- **Bootstrap.** Bloc circulaire, bloc = 3 événements, 40 000 tirages. Jamais iid.
- **DSR.** `n_trials = 16` (déclaré au pré-enregistrement), `std_sr_trials = 0,1616`
  **mesuré** sur les 16 cellules de la grille (pas de σ implicite — c'est l'erreur qui a
  invalidé l'audit oxfordstrat, INVENTORY §3.1). Skew +0,04, kurtosis 3,57.
  `E[max] = 0,291` ⇒ **DSR primaire 0,863 (FAIL)**. Le meilleur de grille (SR 0,438) donne
  DSR 0,986, mais c'est précisément la quantité que la déflation existe pour disqualifier.
- **Source du calendrier.** API publique gratuite TreasuryDirect `/securities/search`
  (l'endpoint `/auctioned` est plafonné à 250 lignes et ignore `pagenum` — piège contourné
  par une boucle année-par-année). **1 624 adjudications de coupon nominal, 2000-01 → 2026-07.**
  Validations passées : couverture annuelle cohérente avec l'histoire institutionnelle
  (10y trimestriel avant 2009, mensuel après) ; `announcement < auction < issue` sur
  1 618/1 624 ; jours de bourse ; distribution jour-du-mois conforme (2y 25 / 5y 25 / 7y 27
  contre 3y 9 / 10y 10 / 30y 11 / 20y 19). TIPS et FRN exclus. Reopenings correctement
  reclassés (« 9-Year 10-Month » ⇒ 10y).

---

## 7. Ce qui reste ouvert — et pourquoi ce n'est pas testable ici

La décomposition **horaire** (descriptive, N = 18 événements 2024-07 → 2025-12, `t < 1` partout,
**aucun pouvoir décisionnel**) est directionnellement conforme au mécanisme :

| fenêtre intraday jour `t` | mean bps | t |
|---|---:|---:|
| 08:00 → 13:00 ET (concession) | **−2,62** | −0,79 |
| 13:00 → 14:00 ET (résultat) | +1,89 | +0,79 |
| 14:00 → 15:00 ET (queue) | +3,61 | +1,62 |

Cela suggère que **la concession est concentrée dans la matinée du jour d'adjudication**,
donc **à l'intérieur d'une seule barre daily** — et que la construction daily la noie
mécaniquement dans la jambe POST, qui contient à la fois la concession matinale et la reprise
d'après 13:00. C'est l'explication la plus économe du fait que la jambe PRE daily soit nulle.

**Ce n'est PAS un résultat, et cela ne rouvre pas le dossier.** Trois raisons :
1. N = 18, `t < 1` : c'est une observation post-hoc, pas une mesure.
2. La spécification intraday correspondante serait **nouvelle** (short `close(t−1)` → 12:30 ET,
   long → `close(t+1)`), donc à pré-enregistrer et à re-payer en `n_tests`.
3. **La donnée n'existe pas gratuitement** : il faudrait un historique ZN intraday sur
   ≥ 15 ans. Le repo n'a que ~2 ans de barres horaires. Sans cela, la puissance est nulle
   par construction.

**Et même dans le meilleur cas, l'arithmétique ne ferme pas** : la V intraday complète
mesurée vaut ~8 bps, contre ~1,6 bps d'aller-retour et un gate 3× à ~5 bps — la marge serait
mince, sur un effet que 251 événements daily n'arrivent déjà pas à distinguer de zéro.

**Recommandation : classer, ne pas rouvrir sans données intraday longues.**

### Falsificateur dose-réponse (exploratoire, hors ledger)

Si la concession est une pression de bilan de dealer, une adjudication **plus grosse**
relativement à son propre historique doit produire une concession **plus grosse**.

| quartile de taille (z sur 24 adj.) | n | `S_V` | **PRE** | POST |
|---|---:|---:|---:|---:|
| Q1 | 70 | −7,97 | −9,11 | +1,14 |
| Q2 | 54 | +8,84 | +11,80 | −2,96 |
| Q3 | 61 | +12,55 | +0,76 | +11,79 |
| Q4 | 62 | +18,53 | +4,60 | +13,93 |

`corr(taille_z, jambe PRE) = +0,056`. **Gradient plat sur la jambe du mécanisme.** La
montée monotone de `S_V` est portée par la jambe POST et par la confusion taille↔époque
(les adjudications ont grossi avec le temps). Même résultat sur le bid-to-cover
(`corr = +0,022`). **Signature de falsification identique à L49** (unlock-drift : gradient
plat ⇒ pas de mécanisme, quelle que soit la moyenne poolée).

---

## 8. Bilan pour le ledger

| | |
|---|---|
| **Verdict** | **REJECTED — COST-DEAD & UNDERPOWERED** |
| Motif principal | K4 (coût : 7,72 < 9,9 bps), K9 (DSR 0,863), K8 (ΔSR −0,072 / −0,162) |
| Redondance B1 | **NON** — 0,0 % de recouvrement, ρ −0,001 (le point neuf, et il est propre) |
| Mécanisme | **non retrouvé en daily** : jambe concession +1,52 bps, t 0,48 ; dose-réponse plate |
| Contribution `n_tests` | **+16 cellules** (ledger pré-enregistré §7) ; cellules exploratoires signalées comme telles |
| Famille | à classer **CLOSED au tier daily / futures retail** ; rouvrable **uniquement** avec un historique ZN intraday long |
| Effet secondaire utile | correction méthodologique du placebo (§4) — candidat-leçon nommé |

**Ce que ce dossier achète malgré le rejet.** L'inventaire notait que E020 était
« skippé sans qu'aucun chiffre ne soit produit ». Il y a maintenant des chiffres, et ils
disent trois choses utiles : (i) le skip au gate-0 FTMO **n'a rien coûté** — il n'y avait
pas d'edge sous le tapis ; (ii) la famille « flux contraint et calendaire sur le Treasury »
**ne se généralise pas** de B1 vers les adjudications, ce qui resserre ce que B1 est
réellement (une demande de *fin de mois*, pas une pression de dealer datée) ; (iii) le seul
endroit où les adjudications « marchent » est le cluster month-end, qui **est** B1 — le piège
n°1 était réel et il a été évité.

---

*Mesuré 2026-07-30. `/usr/bin/python3`. Aucun commit, aucun fichier hors
`Multi_Asset/research/active/treasury_auction_2026-07/`.*
