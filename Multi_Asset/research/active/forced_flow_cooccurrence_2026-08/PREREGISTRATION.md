# PRÉ-ENREGISTREMENT — Co-occurrence de flux forcés à dose calendaire

**Famille neuve. Compteur LOCAL N1. Rédigé et committé AVANT toute lecture de série de prix.**
Date : 2026-08-03. Branche `claude/forced-flow-cooccurrence`, worktree dédié.
Base : `origin/main` @ `72f07c4b`.

---

## 1. Le principe de conception (pourquoi ce test, et pourquoi maintenant)

Le profil qu'exige une barrière FTMO (WR > 55 %, win/loss ≈ 1, kurtosis basse, fréquent) est le
profil d'un **fournisseur de liquidité**. Au tarif retail on **paie** le spread qu'il faudrait
encaisser : ce profil est donc inaccessible par construction. La seule échappatoire logique est
qu'il existe un **acteur CONTRAINT** qui, dans une **fenêtre BORNÉE**, paie **plus que le spread**
— et dont la contrainte est **observable ex ante**.

D'où le triplet de tri : *dose observable ex ante · acteur forcé · fenêtre bornée*.

### Ce que la tentative précédente a enseigné (et qui dicte la conception d'ici)

Une dose-réponse a déjà été tentée dans ce dépôt avec `|R_day|` comme dose. Elle a échoué d'une
manière très informative : la dose prédisait la **variance** (R² 7-11 %) et non la **moyenne**
(R² 0.03-1.4 %), soit un rapport de 50 à 250×. Le « gross qui monte avec la dose » montait
parce que σ montait. **Une dose de PRIX est structurellement confondue avec la volatilité.**

⇒ **L'élément nouveau de ce test : la dose est EXOGÈNE AU PRIX, purement calendaire.** Elle est
connue des semaines à l'avance, elle ne dépend d'aucun rendement réalisé, donc elle **ne peut pas
être un artefact de variance**. C'est la seule chose qui distingue ce test de ce qui a déjà été
fait ici, et c'est ce qui le justifie.

### La question neuve : la CO-OCCURRENCE

Chaque flux forcé pris isolément est probablement sous le coût — ce dépôt en a déjà tué plusieurs
(month-end BTC, adjudications, drift pré-FOMC, reversal de fixing). La question **jamais posée**
est : **que se passe-t-il quand PLUSIEURS flux forcés tombent le même jour ?**

Le mécanisme postulé est additif en pression, pas en signal : si trois desks distincts doivent
chacun exécuter un ordre non discrétionnaire dans la même fenêtre bornée, la demande de liquidité
agrégée dépasse le seuil où un fournisseur exige une concession de prix. Un seul flux ne le fait
pas ; trois peut-être.

**Le résultat principal est donc la FORME DE LA COURBE en nombre de flux co-occurrents (0, 1, 2,
≥3), pas la valeur d'une cellule.** Un pic isolé sans gradient est du bruit sélectionné et sera
déclaré tel.

### Le flux de tête est NOTRE observation, pas celle d'un papier

`data/ftmo_portfolio/v22/spec_v22.yaml` porte `triple_days: {indices: vendredi, metaux_fx:
mercredi}` (`triple_dow_python` : XAUUSD 2, USDJPY 2, US100 4, GER40 4). **Un acteur qui paie
trois nuits de portage d'un seul coup, à date connue, sur notre véhicule exact, est
définitionnellement un acteur contraint.** Et le swap FTMO est **ASYMÉTRIQUE** :

| | swap long (bps/nuit) | swap short (bps/nuit) | côté qui PAIE |
|---|--:|--:|---|
| XAUUSD | −1.518 | −0.336 | long (×4.5) |
| US100 | −2.126 | +0.092 | long (le short ENCAISSE) |
| GER40 | −1.564 | −0.193 | long (×8.1) |
| USDJPY | +0.060 | −1.267 | **short** (le long encaisse) |

La pression n'a donc **aucune raison d'être symétrique**, et le signe attendu **change
d'instrument en instrument** selon quel côté paie. Cela fournit gratuitement un falsificateur
transversal piloté par le mécanisme (L44) et des jambes **disjointes par construction** (L25) :
l'ensemble « longs payeurs » et l'ensemble « shorts payeurs » sont des instruments différents,
pas un `-side_long`.

Personne dans ce dépôt n'a jamais testé le jour de swap triple.

---

## 2. Univers, données, horloge

**Données : `data/deep_history_utc/` uniquement** (vrai UTC vérifié, MANIFEST machine-généré,
trous 2018-2021 réparés). Importées en LECTURE SEULE depuis le répertoire principal par chemin
absolu `<HOME>/Desktop/Algo_claude/data/deep_history_utc/`.

**INTERDIT : `data/panels/m5_indices/`** — étiqueté `timestamp_utc` mais réellement EET (vérifié
au tick à −2 h). Ce bug a déjà fait tester 43.9 % de barres de pré-marché en croyant mesurer la
séance.

**Univers tradable (17)** — FX : EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, EURGBP,
EURJPY, AUDJPY · Indices : US500, US100, US30, GER40 · Métaux : XAUUSD, XAGUSD, COPPER ·
Énergie : UKOIL, USOIL. (19 séries, dont COPPER/UKOIL/USOIL en classe « autre » — voir §7.)
**Exclus d'office** sur coût RT mesuré : COCOA 1189 bps, NGAS 300, COTTON 282, SOYBEAN 153,
SUGAR 144, COFFEE 142, OJUICE, DIESEL.

**Horloge (L56).** Le jour pertinent est le **jour SERVEUR** (Europe/Bucharest, EET/EEST, avec
son DST) — c'est l'horloge qui définit le rollover de swap, donc l'horloge de l'acteur contraint.
Toutes les dates de flux et toutes les fenêtres sont calculées sur cette horloge, jamais sur UTC.

**Test de falsification d'horloge (gratuit, exécuté AVANT tout le reste)** : corréler le profil
horaire moyen hiver-vs-été de la fenêtre de trade dans les DEUX horloges (UTC et serveur). Si la
corrélation UTC ≥ corrélation serveur, l'ancrage serveur est faux et le protocole s'arrête pour
correction. (C'est le test qui a rattrapé l'erreur d'une heure sur la fenêtre overnight or/argent.)

---

## 3. La forme de trade — UNE seule, FIXE à tous les niveaux de dose

C'est la condition de validité de toute dose-réponse : **seule la dose varie, la forme de trade
ne varie jamais.**

> **Fenêtre W = les 60 dernières minutes de cotation du JOUR SERVEUR**, par instrument.

Justification unique et suffisante : c'est l'instant exact où **toute** contrainte « ceci doit
être fait avant la fin de la journée » devient liante. Le rollover de swap y est facturé (donc
c'est la dernière occasion d'éviter le triple portage) ; l'exécution des rebalancements de fonds,
des règlements d'expiration et des reconstitutions d'indice se concentre à la clôture (MOC /
fixing de clôture). Définir W comme « les 60 dernières minutes de barres disponibles du jour
serveur » a un second avantage : la fenêtre s'adapte automatiquement à la session de chaque
instrument, **sans horaire codé en dur**, donc sans possibilité d'erreur de DST.

**Exécution (L59 — entrée ET sortie).**
- Entrée : à l'**ouverture de la première barre M1 de W**. La dose est calendaire, connue des
  semaines à l'avance ⇒ aucune information de la fenêtre n'entre dans la décision (règle dure
  « signal en T−1, trade en T » satisfaite a fortiori).
- Sortie : à la **clôture de la dernière barre M1 de W**. Sortie **temporelle pure, sans stop** —
  le piège L59 (25 % des barres de stop ouvrent au-delà du stop) ne s'applique donc pas ici, et
  c'est délibéré : je refuse d'introduire une géométrie de sortie dont l'edge ne serait pas
  séparable du signal.
- Rendement : `r = log(close_dernière_barre / open_première_barre)`, en bps.
- **Aucun swap n'est payé** : la position est ouverte et fermée à l'intérieur du même jour
  serveur, avant le rollover. Le coût est donc **exclusivement** spread + slippage + commission.
  (C'est un point de conception, pas un oubli : c'est ce qui rend la fenêtre éligible malgré L36.)

**Jours écartés** : tout jour serveur où W contient < 45 barres M1, ou dont la dernière barre est
à plus de 5 minutes de la fin observée du jour serveur (jours écourtés, fêtes, trous). Écarté
**avant** toute mesure de rendement, sur critère de complétude uniquement.

---

## 4. Le calendrier des flux — définitions purement calendaires

Chacun est calculable au 1er janvier de l'année. Aucun n'utilise un prix.

| # | Flux | Définition (jour SERVEUR) | Instruments |
|---|---|---|---|
| F1 | **TRIPLE_SWAP** | `weekday == triple_dow` : mercredi (2) pour FX/métaux/énergie, vendredi (4) pour indices | tous |
| F2 | **MONTH_END** | dernier jour de cotation du mois calendaire | tous |
| F3 | **QUARTER_END** | dernier jour de cotation de mars/juin/sept/déc. **Compte EN PLUS de F2** (le rebalancement trimestriel est un flux distinct et plus gros que le mensuel) | tous |
| F4 | **OPEX** | 3ᵉ vendredi du mois (expiration des options listées indice/actions) | tous |
| F5 | **FUT_ROLL** | jeudi précédant le 3ᵉ vendredi de mars/juin/sept/déc (date de roll officielle CME des futures indices) | **indices seulement** |
| F6 | **INDEX_REBAL** | 3ᵉ vendredi de mars/juin/sept/déc (prise d'effet des rebalancements S&P / DAX à la clôture). Distinct de F4 : reconstitution ≠ expiration | **indices seulement** |
| F7 | **FOMC** | jour de décision FOMC, `data/personal_book/post_fomc_drift/data_cache/fomc_events.csv` (182 événements 2004-2026, déjà au dépôt) | tous |

**Dose** `D(instrument, jour) = nombre de flux VRAIS ce jour-là`, ∈ {0, 1, 2, ≥3}.
Bins : `D=0`, `D=1`, `D=2`, `D≥3`.

Limites assumées et écrites d'avance : F4 utilise le 3ᵉ vendredi pour tous les instruments alors
que les options FX se règlent au cut 10:00 New York et les options métaux COMEX ~4 jours ouvrés
avant la fin du mois de livraison ; F5 n'est défini proprement que pour les indices. Ces
approximations **diluent** la dose sur FX/métaux (elles ajoutent du bruit au comptage), elles ne
peuvent pas fabriquer un effet. Elles sont donc conservatrices dans le sens qui compte.

---

## 5. Sorties primaires — et le contrôle L54, qui a tranché le dossier précédent

Pour chaque niveau de dose : `N`, moyenne de `r` en bps, écart-type, t-HAC (Newey-West lag 6),
IC95 par bootstrap **par blocs** (Politis-Romano, longueur de bloc 5 jours ; iid interdit).

**Les DEUX R², systématiquement côte à côte (L54) :**

| quantité | régression | ce que ça mesure |
|---|---|---|
| **R²_moyenne** | `r ~ D` | la dose déplace-t-elle la MOYENNE ? |
| **R²_variance** | `r² ~ D` | la dose déplace-t-elle la VARIANCE ? |

**Version σ-normalisée obligatoire** : le test de moyenne est refait sur `r_z = r / σ₆₀(r)`
(σ des 60 jours serveurs précédents, strictement antérieurs). Si l'effet en bps disparaît en
unités σ, l'effet est un artefact d'échelle de volatilité et non un déplacement de moyenne.

**Monotonie** : Spearman ρ entre l'indice de bin (0,1,2,3) et la moyenne du bin, sur les bins où
N ≥ 100. La FORME est le résultat ; un pic isolé sans gradient sera nommé bruit.

---

## 6. Contrôles — aucun n'est optionnel, chacun a déjà coûté ici

- **GATE AU GROSS D'ABORD** (`cost_rt = 0`). Si l'effet n'existe pas à coût nul, il n'existe pas.
  Le coût n'est appliqué qu'ensuite : indices **~1.8 bps RT**, XAUUSD **1.84 centre / 3.88 queue
  provisionnée**, FX major ~1.3 bps (source `Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md`).
  ⚠ **La colonne `spread` de `deep_history_utc` n'est JAMAIS utilisée seule** : massivement
  zéro-inflée (EURUSD 66/69/63 % de barres nulles en 2021/2022/2023 ; US30 79.7/100/74.9 % en
  2019/2020/2021) et, même peuplée, optimiste d'un facteur ~2.4 sur le RT FTMO réel. Le coût
  vient du panel RT mesuré, pas de la colonne.
  ⚠ **Majoration spécifique à cette fenêtre** : W est adjacente au rollover, où le spread
  s'élargit structurellement (« Tokyo wide » = artefact de rollover, déjà identifié ici). Le coût
  de W sera donc **majoré explicitement**, et la sensibilité au coût sera rapportée comme une
  **courbe** (0 / 1× / 1.5× / 2× le RT central), pas comme un point.

- **L58 — baseline appariée, et c'est LE piège de ce sujet.** Un jour de fin de mois n'a pas
  l'espérance inconditionnelle d'un jour quelconque, et un placebo calendaire apparié peut
  **FABRIQUER un PASS** : L58 est née exactement là, quand un blackout d'adjudication avait poussé
  le pool placebo dans un creux de saisonnalité jour-du-mois. Protocole :
  1. Placebo apparié : pour chaque jour à `D ≥ 1`, tirage de jours de contrôle à `D = 0` de même
     **jour de semaine**, même **bucket de jour-du-mois** (1-5 / 6-10 / 11-15 / 16-20 / 21-25 /
     26-31) et même **mois calendaire**.
  2. **CONTRÔLE À COÛT NUL, obligatoire** : la moyenne du pool placebo doit **égaler l'espérance
     inconditionnelle de la forme de trade** (moyenne de `r` sur TOUS les jours). Écart toléré :
     1 erreur-type bootstrap. **Au-delà, c'est le PLACEBO qui est biaisé, pas le signal** — le
     résultat est alors rapporté contre la baseline inconditionnelle et le placebo est déclaré
     invalide dans le rapport.
  3. Placebo à **autocorrélation appariée** (décalage circulaire du calendrier de flux, 500
     tirages) pour tout p(pass) : une série dé-moyennée mais persistante atteint 92.9 % de
     p(pass) à horizon long — un p(pass) sans ce contrôle ne vaut rien.

- **L25 two-sided à jambes DISJOINTES.** Les jambes ne sont **pas** obtenues par `-side_long`.
  Elles sont l'ensemble « instruments où le LONG paie » (XAUUSD, XAGUSD, US100, US500, US30,
  GER40, …) contre l'ensemble « instruments où le SHORT paie » (USDJPY et tout autre à
  `swap_long > 0`). Ensembles d'instruments disjoints, testés séparément.

- **L38 — orthogonalité β.** Régression du rendement de la sleeve candidate sur un buy-and-hold
  vol-targeté de l'instrument primaire ; **R² > 30 % ⇒ ce n'est pas une sleeve neuve**, c'est du
  timing sur beta. (β, α HAC, R²) rapportés.

- **L60 — barres à fourchette nulle, par série ET par an**, mesurées et publiées **avant**
  utilisation. Une année-instrument dont la fenêtre W dépasse **20 %** de barres
  `high == low == close` est écartée : un print de règlement n'est pas un prix. (XPT/XPD ont déjà
  fabriqué 32 % d'un P&L de cette façon.)

- **DSR** via `dsr.py` **de la racine** uniquement. `framework.py:131` et `ftmo_lab.py:232` sont
  CASSÉES (σ_SR_trials absent ⇒ seuil 2.57 à N=142) et ne seront pas appelées.
  ⚠ **Le DSR ne voit pas la concentration de régime** : un candidat à DSR 0.982 est mort ici en
  walk-forward (1-2 folds/5, tout l'edge dans le fold COVID). **Les deux filtres sont orthogonaux
  ⇒ j'exige les DEUX** : DSR ET walk-forward ≥ 5 folds expanding.

- **Barrières** (si et seulement si un candidat survit au gross et au coût) : FTMO 2-step, daily
  **−5 %** sur l'**ÉQUITÉ intraday**, floor **STATIQUE −10 %** (le cliquet est 1-step, écarté),
  horizon **182 jours**. Décision sur **p(pass), durée et EV par unité de temps**.
  ⚠ Ce livre est **FLOOR-DOMINATED (49.7 % des morts)**, PAS daily-dominated — le 80.2 % qui
  traîne dans d'anciens rapports ne sera pas repris. Outil : `Portfolio/admission/barrier.py`,
  **importé, jamais modifié**.

---

## 7. Règles de kill, chiffrées, décidées maintenant

| # | Règle | Verdict si violée |
|---|---|---|
| **K1** | **Gate gross.** À coût nul, la moyenne de `r` à `D ≥ 2` doit différer de celle à `D = 0` avec **\|t_HAC\| ≥ 2.0** et un écart ≥ **1.0 bps** | REJECTED (classe) |
| **K2** | **Monotonie.** \|Spearman ρ\| ≥ 0.8 entre indice de bin et moyenne de bin, sur ≥ 3 bins à N ≥ 100 | pic isolé ⇒ **BRUIT**, pas un finding |
| **K3** | **L54.** `R²_variance / R²_moyenne ≤ 10` | dose = prédicteur de VARIANCE ⇒ REJECTED comme edge |
| **K4** | **Coût.** Effet net à `D ≥ 2` ≥ **1.5 ×** cost_rt majoré de la fenêtre | COST-DEAD |
| **K5** | **Placebo.** Effet > p95 du placebo apparié **valide** (cf. §6 contrôle à coût nul) | REJECTED |
| **K6** | **Puissance.** `N < 60` observations dans un bin d'une classe | ce bin est **UNDERPOWERED** — rapporté, **non scoré, ne consomme pas le budget d'essais** |
| **K7** | **σ-normalisation.** L'effet doit survivre en unités σ (même signe, \|t\| ≥ 1.5) | artefact d'échelle de vol ⇒ REJECTED |
| **K8** | **Régime.** Walk-forward expanding ≥ 5 folds : effet du même signe dans ≥ 3 folds/5 | concentration de régime ⇒ REJECTED **même à DSR élevé** |

Vocabulaire de verdict : **PASS** / **REJECTED** / **UNDERPOWERED** (un UNDERPOWERED ne consomme
pas le budget d'essais).

---

## 8. Comptabilité des essais — cellules déclarées d'avance

Compteur **LOCAL N1** pour cette famille (le global 321 est FIGÉ depuis 2026-05-30 ; le delta sera
réconcilié à la clôture).

| bloc | cellules | contenu |
|---|--:|---|
| A — courbe primaire | **1** | dose-réponse poolée sur les 17 instruments (la FORME est le résultat) |
| B — courbes par classe | **4** | FX (10) · indices (4) · métaux (XAUUSD, XAGUSD, COPPER) · énergie (UKOIL, USOIL) |
| C — asymétrie de swap | **2** | ensemble « long paie » vs ensemble « short paie » (jambes disjointes, L25) |
| D — flux de tête isolé | **2** | TRIPLE_SWAP seul, sur chacun des deux ensembles de C |
| **TOTAL déclaré** | **9** | |

Toute cellule au-delà de 9 sera déclarée comme **exploratoire** dans `RESULTS.md`, comptée, et
pénalisée en multiple-testing (Šidák) — pas dissimulée. Budget de modifications : **3 maximum**
sur cette hypothèse (règle dure), **0 consommée** à la rédaction.

---

## 9. Ce qui compterait comme fermeture propre

**Si la courbe est plate, je le dis.** Ce serait la fermeture propre de la dernière voie de
conception identifiée par le principe « acteur contraint / fenêtre bornée / dose ex ante », et
cela vaut le déplacement : cela transformerait « on n'a pas encore trouvé » en « le seul endroit
où la logique disait de chercher a été regardé, avec une dose que la volatilité ne peut pas
imiter, et il n'y a rien ». C'est un résultat, pas un échec.

Ce que le test ne pourra **pas** prouver, quel que soit le résultat, sera écrit dans `RESULTS.md`.

---

## 10. Hygiène d'exécution

- Interpréteur **`/usr/bin/python3` explicitement** (un alias zsh masque `python3` par un binaire
  SANS pandas — a déjà produit un faux PASS silencieux ici).
- Caches dans un chemin **propre à cette session** (scratchpad), jamais partagé : un agent frère
  tourne en parallèle et deux agents se sont déjà écrasés mutuellement dans ce projet.
- Données du répertoire principal en **LECTURE SEULE**, par chemin absolu.
- Livrable : **aucun blob de données** committé. **Aucun chemin live** touché (`ftmo_live/`,
  `strategies/`, `Futures/live/`, `Portfolio/`, `.github/`, `*.mq5`) — `Portfolio/admission/` est
  **importé**, jamais modifié.
