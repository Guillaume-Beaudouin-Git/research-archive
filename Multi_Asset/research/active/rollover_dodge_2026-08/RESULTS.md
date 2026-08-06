# Esquiver le rollover de swap en décalant l'entrée — KILL

**2026-08-06.** Worktree `claude/rollover-dodge`, base `25be227f`. Interpréteur `/usr/bin/python3`
explicite. **Diagnostic — aucun chemin live touché, aucune modification de spec proposée.**
Données `data/deep_history_utc/` (vrai UTC vérifié), lues en lecture seule depuis le répertoire
principal ; caches hors repo. Aucun blob de données commité.

Hypothèse testée : le serveur FTMO est à Paris + 1 h, donc le rollover de swap (00:00 serveur)
tombe à **23:00 Paris**. L'entrée à 22:05 le franchit de 55 min et paie le swap. Une entrée
**après 23:00** serait ouverte après le rollover, sortirait à 15:30 le lendemain, et paierait
**zéro swap** — soit ~1.9 bps récupérés sur les 4.37 bps de coût qui font échouer la sleeve.

---

## 0. La réponse, en une phrase

**Non — et le blocage est structurel, pas statistique : il n'existe aucune cotation entre 22:50 et
00:00 Paris.** Le rollover serveur est *à l'intérieur* de la pause de maintenance du CFD. « Être en
position après le rollover » et « être en position après le gap de réouverture » sont **le même
événement**. On ne peut donc pas esquiver le swap sans abandonner aussi le gap — et le gap est
payant. Post-2021, décaler l'entrée à la réouverture (00:05) sacrifie **2.70 bps de gross sur
US100 (39 % du total, t 2.98)** et **5.61 bps sur GER40 (63 %, t 3.29)** pour économiser **2.21 bps
de swap au poids du book**. Le net du book passe de **+5.09 bps (t 1.82)** à **+2.32 bps (t 0.95)** :
**Δ = −2.77 bps, t −2.02, IC90 bloc [−5.09 ; −0.63]** — la dégradation est significative.

**Le swap n'est pas un coût évitable : c'est le péage du gap de halt.**

---

## 1. Étape 0 — les bornes, avant tout rendement

### L56 — dans quelle horloge décomposer

Test de falsification gratuit, fait **en premier** : corrélation du profil intra-journalier
hiver-vs-été dans les trois horloges (`results/step0_l56_clock.csv`).

| série | statistique | Europe/Paris | America/New_York | UTC |
|---|---|--:|--:|--:|
| US100 | \|rendement\| horaire | 0.888 | **0.988** | 0.781 |
| US100 | tick_volume horaire | **0.988** | 0.773 | 0.744 |
| GER40 | \|rendement\| horaire | **0.981** | 0.972 | 0.733 |
| GER40 | tick_volume horaire | **0.979** | 0.953 | 0.492 |
| US100 | *rendement MOYEN horaire* | −0.024 | 0.254 | 0.044 |
| GER40 | *rendement MOYEN horaire* | 0.082 | 0.097 | −0.055 |

Deux enseignements :

1. **L'UTC est la mauvaise horloge** (0.49-0.78 partout), Paris et New York sont toutes deux
   valides — elles basculent quasiment ensemble. **Je décompose en horloge Paris**, qui est à la
   fois l'horloge du schedule EA, celle du serveur (à 1 h près, sans écart de DST : Prague et la
   zone EET partagent le DST européen) et donc celle du rollover. C'est l'horloge dans laquelle la
   question est posée.
2. **Le rendement MOYEN horaire est un estimateur inutilisable pour un test d'horloge** : il donne
   ~0 dans les trois horloges et ne discrimine RIEN. Seule la **volatilité** (ou l'activité) a le
   rapport signal/bruit nécessaire. Ligne conservée dans le tableau comme contre-exemple.

### La pause de maintenance — le fait qui décide

Couverture de barre M1, minute par minute, jours ouvrés (`results/step0_coverage_night.csv`) :

| Paris | 22:05 | 22:15 | 22:45 | **22:50** | **23:05** | **23:35** | **23:55** | 00:00 | 00:05 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| US100 post-2021 | 0.95 | 0.83 | 0.83 | **0.00** | **0.01** | **0.01** | **0.01** | 0.11 | 0.79 |
| GER40 post-2021 | 0.82 | 0.65 | 0.65 | **0.00** | **0.00** | **0.00** | **0.00** | 0.18 | 0.78 |

**Identique en 2021, 2023, 2025, hiver comme été** — la pause est fixe dans l'horloge Paris/serveur.
Mode de la dernière cotation avant la pause : **22:49**. Mode de la première après : **00:05**
(664/810 jours US100, 615/800 GER40) — `results/step0_halt_bounds.csv`.

⇒ **La variante « entrée 23:05 Paris » demandée par le brief N'EXISTE PAS.** Il n'y a pas de prix.
Un ordre placé à 23:05 ne peut être rempli qu'à la réouverture. **La seule façon réelle d'être en
position après le rollover est d'entrer à 00:05.**

### L60 — barres à fourchette nulle

`results/step0_l60_zero_range.csv`. US100 : ≤ 0.007 % toutes années post-2021 — **PASS**.
GER40 : 0.6-1.9 % post-2021, et **1.3 % à l'horodatage 22:35 / 0.9 % à 22:45 / 1.6 % à 01:05**.
Non nul mais très en dessous du seuil de L60 (XPTUSD : 61-69 %). Aucun horodatage utilisé n'est
dominé par des prints de règlement. **PASS, avec réserve mineure sur GER40 en fin de séance.**

---

## 2. Le profil horaire du gross — la question qui décide

Décomposition additive en log, horloge Paris, jours d'entrée lundi + mardi, **gross**, échantillon
commun à tous les checkpoints (`results/step1_hourly_segments.csv`,
`results/step1_hourly_cumulative.csv`).

### US100 — fenêtre 22:05 (D) → 15:30 (E), post-2021, N = 457, total **7.78 bps (t 2.47)**

| segment | bps | t | cumulé | % du total | t cum |
|---|--:|--:|--:|--:|--:|
| **22:05 → 22:45** | **+1.21** | 1.87 | +1.21 | **15.5 %** | 1.87 |
| **22:45 → 00:05** *(GAP DE HALT)* | **+1.59** | 1.90 | **+2.79** | **35.9 %** | **2.68** |
| 00:05 → 01:05 | +0.46 | 0.67 | +3.25 | 41.8 % | 2.54 |
| 01:05 → 08:05 *(7 h d'Asie/Europe)* | +0.41 | — | +3.68 | 47.3 % | 1.64 |
| 08:05 → 09:05 | +1.88 | 1.72 | +5.56 | 71.5 % | 2.43 |
| 09:05 → 10:05 | +2.38 | 2.20 | +7.94 | 102.1 % | 2.97 |
| 10:05 → 11:05 | +1.17 | 1.07 | +9.10 | 117.1 % | 3.23 |
| 11:05 → 15:30 | −1.32 | — | +7.78 | 100.0 % | 2.47 |

### GER40 — fenêtre 17:35 (D) → 09:00 (E), post-2021, N = 418, total **7.99 bps (t 2.50)**

| segment | bps | t | cumulé | % du total |
|---|--:|--:|--:|--:|
| 17:35 → 22:05 *(4 h 30)* | +2.83 | 1.59 | +2.83 | 35.4 % |
| **22:05 → 22:45** | **+1.50** | **2.68** | +4.33 | 54.2 % |
| **22:45 → 00:05** *(GAP DE HALT)* | **+0.49** | 0.79 | **+4.82** | **60.3 %** |
| 00:05 → 01:05 | +1.24 | 2.16 | +6.05 | 75.8 % |
| 01:05 → 07:05 | −0.77 | — | +5.28 | 66.1 % |
| 07:05 → 09:00 | +2.71 | — | +7.99 | 100.0 % |

**Réponse à la question posée.** L'heure 22:05 → 22:45, seule partie *tradable* de la fenêtre
sacrifiée, porte **15.5 % du gross US100** et **18.8 % du gross GER40** — c'est le chiffre que le
brief attendait, et pris isolément il aurait rendu l'idée séduisante. Mais on ne peut pas
s'arrêter là : la fenêtre réellement abandonnée va jusqu'à la réouverture, et le **gap de halt**
ajoute 1.59 bps sur US100. **Total sacrifié : 35.9 % du gross US100, 60.3 % du gross GER40.**

Note : le segment 22:05 → 22:45 est un des rares dont le t individuel dépasse 2 sur GER40 (2.68
post-2021, **3.07** full-sample). Ce n'est pas une heure morte : c'est l'heure la plus dense de la
nuit sur GER40.

---

## 3. Table appariée — 22:05/17:35 (live) vs 00:05 (esquive réelle)

Mêmes dates, **même géométrie de sortie** (15:30 / 09:00 inchangées : seule l'entrée bouge, donc
la comparaison est à sortie constante au sens de L59), mêmes coûts de spread (1.8 bps RT par jambe
dans les deux variantes). N apparié = 513 post-2021 (`results/step3_book_paired.csv`,
`results/step3_gross_sacrifie.csv`).

### Par jambe, gross sacrifié

| post-2021, N=513 | gross live | gross à 00:05 | **gross sacrifié** | t | % du gross | IC90 bloc |
|---|--:|--:|--:|--:|--:|---|
| US100 (22:05→00:05) | 6.88 | 4.18 | **2.70** | **2.98** | **39.3 %** | [+1.26 ; +4.22] |
| GER40 (17:35→00:05) | 8.89 | 3.29 | **5.61** | **3.29** | **63.1 %** | [+2.96 ; +8.44] |

Le gross sacrifié est **significativement positif** dans les deux cas. Ce n'est pas du bruit qu'on
abandonne.

### BOOK (0.6 par jambe), net

| post-2021, N=513 | moy. bps | t_HAC6 | Sharpe ann. | IC90 bloc | DSR |
|---|--:|--:|--:|---|--:|
| **BOOK_LIVE** (22:05 / 17:35, 1 nuit de swap) | **+5.09** | **1.82** | 0.60 | [+0.67 ; +9.68] | 0.569 |
| **BOOK_DODGE** (00:05 / 00:05, 0 swap) | **+2.32** | **0.95** | 0.33 | [−1.75 ; +6.33] | 0.279 |
| **Δ (dodge − live)** | **−2.77** | **−2.02** | −0.70 | **[−5.09 ; −0.63]** | — |

Décomposition du Δ : **swap économisé +2.21 bps**, **gross perdu −4.99 bps**, RT inchangé.

Full-sample (N = 887) le verdict s'adoucit sans jamais s'inverser : Δ = **−0.63 bps (t −0.60)**,
IC90 [−2.40 ; +1.03]. **L'échantillon décisionnel est le post-2021, et il est franchement négatif.**

### Sensibilité au swap — la dérive live ne sauve rien

Les swaps facturés ont dérivé au-dessus des ancres (§5). Δ (dodge − live), post-2021 :

| hypothèse de swap | swap économisé | Δ net | t |
|---|--:|--:|--:|
| ancre spec (−2.126 / −1.564) | +2.21 | **−2.77** | −2.02 |
| live mesuré (−2.125 / −1.679) | +2.28 | **−2.70** | −1.97 |
| live **+17 %** (dérive maximale) | +2.67 | **−2.32** | −1.68 |
| swap **ZÉRO** *(borne théorique)* | 0.00 | **−4.99** | −3.62 |

**Même en supposant le swap 17 % plus cher qu'il ne l'est aujourd'hui, l'esquive reste perdante et
son IC90 exclut zéro** ([−4.63 ; −0.17]). Il faudrait un swap **≈ 2.3× l'ancre** pour que
l'arbitrage bascule. Le résultat ne dépend d'aucun choix de dénominateur.

---

## 4. Balayage de l'heure d'entrée — et le faux PASS qu'il fallait éviter

BOOK, post-2021, swap = ancre, une seule heure appliquée aux deux jambes
(`results/step2_variants.csv`).

| entrée | exécutable ? | N | gross | t | swap | RT | **net** | **t** |
|---|:--:|--:|--:|--:|--:|--:|--:|--:|
| 17:35 | oui | 556 | 11.43 | 3.45 | −2.21 | −2.16 | **+7.06** | **2.13** |
| **22:05** *(live US100)* | oui | 520 | 7.13 | 2.66 | −2.21 | −2.16 | **+2.76** | 1.03 |
| 22:35 | oui | 421 | 6.67 | 2.13 | −2.21 | −2.16 | +2.29 | 0.73 |
| 22:45 *(dernière cotation)* | oui | 421 | 6.47 | 2.02 | −2.21 | −2.16 | +2.10 | 0.66 |
| **23:05** | **NON** | 421 | 6.46 | 2.01 | **0.00** | −2.16 | **+4.30** | **1.34** |
| **00:05** *(réouverture)* | oui | 549 | 3.35 | 1.41 | 0.00 | −2.16 | **+1.19** | 0.50 |
| 00:35 | oui | 553 | 2.81 | 1.26 | 0.00 | −2.16 | +0.65 | 0.29 |
| 01:05 | oui | 553 | 2.46 | 1.16 | 0.00 | −2.16 | +0.30 | 0.14 |

**Il n'y a pas d'optimum étroit ni de plateau : il y a une falaise.** Le gross s'effondre d'un coup
entre 22:45 (6.47) et 00:05 (3.35) — la falaise, c'est la pause. Après la réouverture le net
décroît encore, monotone (1.19 → 0.65 → 0.30) : entrer plus tard n'aide jamais.

### La ligne « 23:05 » est un artefact, et c'est le vrai piège de ce dossier

Sur US100 post-2021 la variante 23:05 remplie par `ffill` affiche **gross 6.72, swap 0, net 4.92
(t 1.45)** contre **net 2.49 (t 0.85)** pour le live : +2.4 bps et un t qui double. **Ce serait un
PASS, et il est entièrement faux.** Le prix « de 23:05 » obtenu par report est le prix de **22:45**
(gross 6.71, identique au millième) — c'est-à-dire un prix d'**avant** le rollover. Le script a
donc supprimé le swap tout en gardant l'entrée qui le déclenche : il a facturé le bénéfice d'un
décalage sans en payer le coût.

Deux garde-fous en sortent :

- **La tolérance de `ffill` ne doit jamais enjamber une frontière de session.** J'utilise 10 min
  partout ; à 20 min (la valeur du dossier `overnight_vs_intraday`), 23:05 remonte jusqu'à 22:45 et
  fabrique un prix qui n'existe pas. La tolérance doit être bornée par la structure de la séance,
  pas choisie une fois pour toutes.
- **Toute variante d'horaire doit déclarer sa couverture de barre EXACTE avant d'être chiffrée.**
  Ici : 0.6 % à 23:05, contre 95 % à 22:05.

---

## 5. Vérité terrain — le swap est réel, sa dérive est systématique sur GER40

`data/ftmo_portfolio/swaps_billed_live.csv`, 8 facturations, reconstruites en bps
(`results/step3_swap_groundtruth.csv`) :

| date Paris | jour | symbole | notionnel $ | swap $ | **bps** | ancre | écart |
|---|---|---|--:|--:|--:|--:|--:|
| 2026-07-21 | mardi | US100 | 41 337.77 | −8.82 | −2.134 | −2.126 | +0.4 % |
| 2026-07-21 | mardi | GER40 | 50 555.85 | −8.46 | −1.673 | −1.564 | **+7.0 %** |
| 2026-07-27 | lundi | US100 | 45 139.34 | −8.01 | −1.775 | −2.126 | −16.5 % |
| 2026-07-27 | lundi | GER40 | 45 182.81 | −7.54 | −1.669 | −1.564 | **+6.7 %** |
| 2026-08-03 | lundi | US100 | 45 215.54 | −9.70 | −2.145 | −2.126 | +0.9 % |
| 2026-08-03 | lundi | GER40 | 41 742.81 | −6.97 | −1.670 | −1.564 | **+6.8 %** |
| 2026-08-04 | mardi | US100 | 47 818.14 | −10.16 | −2.125 | −2.126 | −0.1 % |
| 2026-08-04 | mardi | GER40 | 48 970.82 | −8.22 | −1.679 | −1.564 | **+7.3 %** |

Ce qui est **établi** : les 8 facturations tombent exclusivement sur des **lundis et mardis**,
c'est-à-dire exactement les nuits tenues ; aucune nuit ON n'est sans swap. US100 colle à son ancre
à ±1 % sur 3 nuits sur 4 (la 4ᵉ, −16.5 %, est isolée et probablement un décalage d'instantané de
notionnel). **GER40 est à +6.7/+7.3 % de son ancre sur les 4 nuits — une dérive systématique, pas
du bruit** : l'ancre GER40 du spec est périmée d'environ 7 %, et devrait être re-mesurée.

Ce qui **n'est PAS établi, et que je ne peux pas trancher avec la donnée disponible** : que le swap
serait **absent** sur une nuit où la position est ouverte *après* 23:00 Paris. Le fichier ne
contient que des nuits ON, toutes ouvertes à 22:05/17:35 ; il n'existe aucune observation de
contrefactuel. Le raisonnement (MT5 facture les positions ouvertes à l'instant du rollover) est
standard mais **reste une hypothèse**. De plus, l'instrument étant en pause à 23:00, le courtier
peut appliquer le rollover à la réouverture (01:00 serveur) plutôt qu'à 00:00 serveur — ce qui ne
changerait rien à la conclusion (une entrée à 00:05 Paris = 01:05 serveur reste postérieure dans
les deux cas), mais qui n'est pas vérifiable ici. **C'est une vérification LIVE que le propriétaire
devrait faire s'il voulait rouvrir le sujet** : ouvrir 0.01 lot à 00:05 Paris, lire le swap le
lendemain. **Elle n'est pas nécessaire ici, puisque l'idée meurt avant, sur le gross.**

---

## 6. Walk-forward du delta apparié (DSR et WF sont orthogonaux)

Δ (dodge − live), swap = ancre, folds chronologiques égaux
(`results/step3_walkforward_delta.csv`) :

| 6 folds | période | Δ net bps | t | live | dodge |
|---|---|--:|--:|--:|--:|
| 1 | 2013-10 → 2018-07 | +3.25 | 1.70 | +0.36 | +3.61 |
| 2 | 2018-07 → 2020-02 | +4.52 | 2.14 | +7.72 | +12.24 |
| 3 | 2020-03 → 2021-10 | −2.85 | −1.08 | +18.06 | +15.21 |
| 4 | 2021-10 → 2023-05 | −0.11 | −0.05 | +8.15 | +8.04 |
| 5 | 2023-05 → 2024-11 | −0.27 | −0.22 | −1.85 | −2.12 |
| 6 | 2024-11 → 2026-06 | **−8.37** | **−2.40** | +9.78 | +1.41 |

**2/6 folds favorables (2/5 en découpage à 5 folds) — très en dessous du gate WF > 60 %**, et le
signe est structuré dans le temps : les deux folds favorables sont les plus anciens (2013-2020), le
fold le plus récent est le pire de tous et le seul significatif. **L'esquive se dégrade avec le
temps.** C'est le contraire du profil qu'on voudrait voir avant de toucher une spec live.

Le DSR va dans le même sens sans rien ajouter (0.569 pour le live contre 0.279 pour l'esquive
post-2021, `n_trials = 8` = les 8 heures balayées, `std_sr_trials` au plancher d'échantillonnage,
`rf = 0.0`) — conformément au constat que **DSR et walk-forward sont orthogonaux**, les deux sont
rapportés et les deux condamnent la variante.

---

## 7. Ce que ça veut dire

**L'idée est morte, et elle meurt proprement — sur le gross, pas sur une subtilité d'inférence.**
La prémisse arithmétique du brief était juste (le rollover est bien à 23:00 Paris, le swap est bien
réel, mesuré, et vaut bien ~1.9-2.2 bps par événement). C'est la prémisse **de marché** qui est
fausse : il n'y a rien à acheter à 23:05, et la première cotation disponible arrive de l'autre côté
d'un gap qui vaut à lui seul 1.59 bps sur US100.

**Reformulé mécaniquement : le swap overnight est le prix d'entrée du gap de réouverture. Les deux
sont facturés à la même frontière. Il n'existe aucune politique d'horaire qui prenne l'un sans
l'autre.** C'est un kill de nature **mécanique** au sens de la politique de ré-ouverture — le gross
abandonné n'est pas nul, il est significativement positif — donc **la famille « décaler l'entrée
pour esquiver un rollover » reste fermée** sur cette sleeve, sauf angle explicitement nouveau écrit
avant de toucher la donnée.

**Recommandation de modification de spec : AUCUNE.** `schedule_cet` reste `22:05` / `17:35`. Aucun
chemin live n'a été touché ; toute modification passerait de toute façon par la chaîne de gel et la
fenêtre du samedi, et c'est une décision humaine.

**Deux sous-produits qui, eux, méritent d'être retenus :**

1. **L'ancre de swap GER40 du spec est périmée d'environ +7 %**, systématiquement sur les 4 nuits
   facturées. Ce n'est pas de la dérive aléatoire. À re-mesurer et à repincer — c'est une correction
   de comptabilité, sans rapport avec l'hypothèse testée ici.
2. **Le problème de coût de la sleeve reste entier.** Le swap est ~50 % du coût et il vient d'être
   montré non évitable par l'horaire. Si la sleeve doit franchir le gate post-2021, ce sera par le
   gross (ajouter des moteurs) ou par le véhicule, **pas** par une optimisation de l'heure d'entrée.
   À swap nul — borne inatteignable sur CFD — le book ferait 7.30 bps (t 2.61) au lieu de 5.09
   (t 1.82) : **même en offrant le swap, la sleeve n'atteint pas confortablement le gate.** Cela
   dimensionne ce que vaut au maximum toute la piste « coût de portage » : elle ne suffit pas.

---

## 8. Ce que ce dossier ne prouve PAS

1. **Il ne prouve pas qu'une entrée à 00:05 échapperait effectivement au swap.** Aucune nuit de ce
   type n'existe dans le facturé. J'ai supposé la mécanique MT5 standard, et l'ai supposée
   **favorablement à l'hypothèse testée** (swap = 0) : l'esquive perd quand même. Une vérification
   live reste requise si quelqu'un voulait rouvrir le sujet.
2. **Il ne prouve rien sur des heures d'entrée intermédiaires non balayées** (par ex. 21:05 ou
   20:05, en amont). Le balayage couvre 17:35 et 22:05 → 01:05 ; la ligne 17:35 du §4 suggère
   d'ailleurs qu'**entrer plus TÔT** est la direction qui améliore le net — direction non testée
   ici, et qui serait un tout autre dossier (elle allonge l'exposition à la barrière, ce que
   `overnight_vs_intraday` a montré coûteux).
3. **Il ne prouve rien sur le fill réel à la réouverture.** J'ai facturé 1.8 bps RT identiques aux
   deux variantes. En pratique, entrer à 00:05 c'est entrer sur le premier tick après une pause,
   probablement au spread le plus large de la session : le coût réel de l'esquive est
   **sous-estimé**, donc le verdict est conservateur. La colonne `spread` de `deep_history_utc`
   étant inutilisable seule, je n'ai pas cherché à le chiffrer.
4. **Il ne prouve rien sur le p(pass) du challenge.** Aucun Δp(pass) ni Δdurée n'a été calculé, et
   post-2021 le p(pass) du livre tombe dans la bande placebo : un tel calcul aurait exigé un
   placebo à autocorrélation appariée, hors périmètre d'un diagnostic de coût.
5. **Il ne revalide pas la sleeve.** Mon `BOOK_LIVE` post-2021 donne 5.09 bps (t 1.82) contre 4.73
   (t 1.66) dans `overnight_vs_intraday` : écart attendu, dû à ma tolérance `ffill` plus serrée
   (10 min au lieu de 20) et à l'exigence supplémentaire d'une cotation à 00:05 pour l'appariement.
   **Le chiffre de référence de la sleeve reste celui du dossier `overnight_vs_intraday`** ; le mien
   n'existe que pour rendre la comparaison appariée légitime.
6. **La pause est mesurée sur ce flux de données, pas sur le carnet FTMO live.** 22:50-00:00 Paris
   est la fenêtre sans barre M1 dans `deep_history_utc`. Que le courtier accepte ou non des ordres
   dans cette fenêtre n'y change rien : sans cotation, il n'y a pas de prix d'entrée mesurable, et
   un ordre au marché y serait rempli à la réouverture — c'est-à-dire au scénario `00:05` chiffré.

---

## Annexe — reproduction

```
/usr/bin/python3 code/step0_integrity.py    # L52/L56/L60, couverture nocturne, bornes de pause
/usr/bin/python3 code/step1_hourly.py       # profil horaire du gross, segments + cumulé
/usr/bin/python3 code/step2_variants.py     # balayage d'heure d'entrée, appariement, faux PASS
/usr/bin/python3 code/step3_book_wf.py      # BOOK au schedule réel, WF, sensibilité, vérité terrain
```

Conventions : log-returns en bps ; t de Newey-West lag 6 ; bootstrap **par blocs** circulaire
(blocs de 10, 5 000 tirages) ; annualisation en **√(événements/an)** ; DSR via `dsr.py` racine avec
`std_sr_trials` au plancher d'échantillonnage et **`rf = 0.0`** ; tolérance `ffill` **10 min**
(25 min pour la seule ligne `2305_PHANTOM`, dont c'est précisément le défaut à exhiber).

**Compteur local d'essais de ce diagnostic : 8** (les 8 heures d'entrée balayées), à réconcilier au
ledger global à la clôture. Aucun blob de données commité, aucun chemin live modifié.
