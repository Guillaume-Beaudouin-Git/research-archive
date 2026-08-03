# PRÉ-ENREGISTREMENT — conditionnement croisé de deux edges sous-puissants

**Écrit et committé AVANT toute lecture de donnée dans ce worktree.**
Worktree `claude/cross-conditioning`, base `origin/main` @ `72f07c4b`.
Interpréteur : **`/usr/bin/python3` explicitement** (un alias zsh masque `python3` par un
binaire sans pandas — cause documentée d'un faux PASS silencieux dans ce dépôt).

**Ce qui a été regardé avant d'écrire ce document, et rien d'autre :** la liste des fichiers de
`data/deep_history_utc/`, la **ligne d'en-tête** de `XAUUSD_M1.csv` et `US100_M1.csv`
(`timestamp_utc,open,high,low,close,tick_volume,spread,real_volume`), et le **code** des dossiers
sources (`close_continuation_gold_subwindows_2026-08/code/`, `close_momentum_dose_2026-08/`).
Aucune valeur, aucune mesure, aucune statistique n'a été calculée. L'inspection de schéma est
nécessaire pour écrire une spec exécutable ; elle est déclarée ici pour que le lecteur puisse la
disqualifier s'il estime qu'elle contamine.

---

## 0. La question, et pourquoi elle n'est pas un nouveau mécanisme

Ce dépôt a testé **un mécanisme à la fois**. Il en résulte deux edges **réels et sous-puissants** :

1. **Dérive de réouverture de l'or (E002)** — gross post-2021 3.79 bps (t_HAC 2.74) dans
   `overnight_sleeve_reopen_2026-08`, 4.35 bps (t 2.96) sur l'échantillon plus strict de
   `close_continuation_gold_subwindows_2026-08` ; survit au retard d'entrée (93 % à +10 min) ;
   **DSR 0.284** ; **le coût mange 42-47 % du signal**. Verdict hérité : **UNDERPOWERED,
   famille OUVERTE**.
2. **Continuation de la pression de clôture sur indices US** — mécanisme **CONFIRMÉ** sur US100
   (gradient t 3.53 sans seuil, quintiles 4/4, 1ᵉʳ sur 12 ancres, hors-échantillon t 2.10) et
   **edge REJECTED sur l'EXÉCUTION** : 2.83 bps à d=0, 1.96 à d=1, 0.59 à d=2 ; demi-vie ≈ 1 min ;
   fourchette de la barre d'entrée 7.66 bps = 2.7× l'edge.

**La question jamais posée : existe-t-il un ÉTAT, mesurable à T-1, qui sépare les séances où ces
dérives paient de celles où elles ne paient pas ?** Zéro donnée nouvelle, zéro papier importé :
on croise nos propres mesures.

**Ce que je NE fais pas, et pourquoi.** `close_momentum_dose_2026-08` a testé la dose par
**amplitude de prix** et a échoué proprement : la dose prédisait la **variance** (R² 7-11 %) et
non la **moyenne** (R² 0.03-1.4 %), monotonie 0/5. **Aucun de mes états n'est une amplitude de
mouvement.** Ils sont de trois natures différentes : **participation/liquidité**, **calendrier
structurel**, **position scale-free dans la fourchette** (et non sa largeur).

**Ce que je n'invente pas non plus.** Le signe de la continuation de clôture a déjà été
pré-enregistré et testé par `close_continuation_gold_subwindows_2026-08` TEST A, qui l'a jugé
**mécanisme confirmé / edge rejeté sur l'exécution**. Je ne le re-revendique pas : je prends ce
verdict comme point de départ et je teste **si un conditionnement le fait passer la barre
d'exécution**, ce qui est une question distincte et falsifiable (§2.4).

---

## 1. Invariants communs (non négociables, aucun n'est optionnel)

- **Gate au GROSS d'abord** : toutes les décisions de §2 et §3 sont prises à `cost_rt = 0`.
  Le coût n'intervient qu'au dernier bloc, économique.
- **États calculables à T-1**, sans look-ahead, exclusivement à partir de
  `data/deep_history_utc/` (vrai UTC). **`data/panels/m5_indices/` est INTERDIT** (EET étiqueté
  UTC, vérifié au tick).
- **Aucune série de `overnight_futures_2026-07/code/step3_performance.py` n'est importée** :
  elle winsorise à 0.5/99.5 **dans le constructeur**. Tout est **reconstruit du M1 BRUT**.
- **Horloge d'échange avec DST** (L56), jamais UTC fixe.
- **HAC Newey-West lag-6** partout ; **bootstrap par BLOCS** (circulaire/Politis-Romano,
  bloc moyen 10), **jamais iid**.
- **DSR** via `dsr.py` **de la racine du dépôt** (`framework.py:131` et `ftmo_lab.py:232` sont
  cassées et ne doivent pas être appelées).
- **L59** : retard d'entrée **et** de sortie testés ; aucune exécution sur barrière (les deux
  formes de trade sont à heure fixe, au marché, sans stop-entry ni bracket — L59 est donc
  satisfaite par construction et vérifiée par le ladder de retard).
- **L60** : part de barres à fourchette nulle **par série et par année**, dans la zone d'entrée
  ET dans la zone de sortie.
- **L54** : pour chaque état, **les DEUX R² côte à côte** — R² sur la MOYENNE et R² sur la
  VARIANCE (régression de |rendement| sur l'état). Un état qui ne prédit que la variance n'est
  pas un conditionnement, c'est un vol-scaler.
- **L38** : R² de toute sleeve conditionnelle survivante contre un buy-and-hold vol-targeté de
  son actif primaire ; **R² > 30 % ⇒ pas une sleeve neuve**.
- **L25** : jambes longues et courtes **disjointes** et rapportées séparément.
- **Compteurs N1 SÉPARÉS** pour la section OR et la section INDICES. Aucune fusion au ledger
  global (321, figé).
- **Aucun blob data dans git** ; caches écrits **hors du dépôt**, dans un chemin qui m'est propre
  (`.../scratchpad/xcond_cache/`), avec **assertion de schéma au chargement** (un agent frère
  tourne en parallèle ; deux agents se sont déjà écrasés ici).
- **Aucun chemin live touché** : `ftmo_live/`, `strategies/`, `Futures/live/`, `Portfolio/`,
  `.github/`, `*.mq5`. `Portfolio/admission/barrier.py` est **importé, jamais modifié**.

### 1.1 Le piège n°1 — la baseline appariée (L58), et sa construction exacte

**La baseline inconditionnelle DÉRIVE AVEC L'ÉTAT.** Mesuré ailleurs dans ce dépôt : de +0.15 à
+0.83 bps du quintile bas au quintile haut. Une baseline pleine fenêtre **fabriquerait un faux
PASS**. Deux baselines appariées sont donc pré-enregistrées, et **le verdict est lu sur l'excès,
jamais sur le niveau brut** :

- **BL-A (appariée au JOUR, ancres alternatives).** Pour la section OR : la même forme de trade
  (même durée) ancrée sur les deux autres blocs de 8 h du même cycle de 24 h
  (`[t0+8h, t0+16h]`, `[t0+16h, t0+24h]`). `excès = R_réouverture − moyenne(R_ancre2, R_ancre3)`.
  Si le quintile haut d'un état est simplement un jour où l'or monte, l'excès s'annule.
- **BL-B (appariée à l'ÉTAT, inconditionnelle en signal).** Pour la section INDICES : dans chaque
  bucket d'état, la moyenne de la **même forme de trade sans condition de signal** (tous les
  jours du bucket, position nulle→rendement post-clôture nu). `excès = cellule − BL-B(bucket)`.
  C'est le contrôle exact qui a démasqué le faux PASS du cycle d'adjudication (L58).

**Règle de lecture** : un état ne peut être déclaré porteur que si **le GRADIENT sur l'EXCÈS**
franchit ses seuils, pas seulement le gradient sur le niveau.

### 1.2 Le piège n°2 — le DSR ne voit pas la concentration de régime

Un candidat à DSR 0.982 est mort en walk-forward (1-2 folds/5, tout l'edge dans le fold COVID).
**Les deux filtres sont orthogonaux et les DEUX sont exigés** : DSR (racine) **et** walk-forward
expanding **≥5 folds** avec un compte de folds positifs.

### 1.3 Déflation pré-annoncée

**6 états au total** (3 or + 3 indices), un test de gradient primaire chacun. Seuil familial
**Šidák à 5 % sur 6 tests ⇒ |t| ≥ 2.63**. Un gradient à `2.0 ≤ |t| < 2.63` est rapporté comme
**« gradient présent, non significatif au niveau familial »** — jamais comme un PASS.

### 1.4 p(pass) : escalade conditionnelle uniquement

Aucun p(pass) n'est calculé dans le passage principal. **Un p(pass) n'est produit que si un état
franchit la totalité de KG1-KG7 (ou KU1-KU7)**, et alors il est **obligatoirement** accompagné de
sa distribution **placebo à autocorrélation appariée** (décalage circulaire de l'état, 400 tirages,
médiane et p95 rapportés) et ne peut être revendiqué qu'au-dessus d'elle. Barrières FTMO 2-step
utilisées le cas échéant : daily **−5 % sur l'ÉQUITÉ**, floor **STATIQUE −10 %**, horizon
**182 jours**. Ce livre est **FLOOR-DOMINATED (49.7 %)**, pas daily-dominated ; le 80.2 % qui
traîne dans d'anciens rapports ne sera pas repris.

---

## 2. SECTION 1 — la dérive de réouverture de l'or (matériau 1)

### 2.1 Forme de trade — GELÉE, héritée, non ré-optimisée

- Instrument **XAUUSD**, `data/deep_history_utc/XAUUSD_M1.csv`, **M1 brut**.
- `t0` = **premier print à/après 18:00 ET** (horloge d'échange avec DST), recherché ≤ 60 min.
  Ancrage sur le premier print exécutable, pas sur l'horloge murale — la réouverture nominale
  n'est pas l'heure de cotation du véhicule (médiane 18:05 ET depuis 2018).
- **Entrée `t0 + d`, d = 0 (PRIMAIRE)**. `d = 10` est la **variante de robustesse
  pré-enregistrée** (93 % du gross conservé post-2021, et elle s'éloigne du pire moment de
  spread). Sortie `t0 + 8 h`, horloge de sortie fixe ; sortie à durée constante `t0+8h+d`
  rapportée en contrôle (L59).
- Rendement en **log × 1e4** (bps). Long-only par construction (c'est une dérive).
- **Échantillon décisionnel : post-2021** (`>= 2021-01-01`). Le full sample (2007+) et le
  pré-2018 sont rapportés pour traçabilité mais **ne portent aucun verdict**.

### 2.2 Les trois états, et leur raison MÉCANIQUE écrite d'avance

Tous les trois sont calculés **à partir d'information strictement antérieure à `t0`** et
normalisés par un **rang causal sur 250 séances glissantes** (fenêtre décalée de 1, donc
aucune information du jour t n'entre dans sa propre normalisation).

**GS1 — participation pré-pause (nature : LIQUIDITÉ / ACTIVITÉ).**
Somme de `tick_volume` sur les 60 minutes se terminant au dernier print avant la pause de
règlement (donc ≈ 16:00-17:00 ET, strictement avant `t0`), en rang causal.
*Mécanisme :* la dérive de réouverture est une **concession payée à qui fournit la liquidité**
dans un carnet mince et déséquilibré. À déséquilibre donné, l'impact prix est inverse de la
profondeur (Kyle : λ ∝ σ/V). Un carnet pré-pause **peu actif** signifie que moins du déséquilibre
a été absorbé avant la coupure, donc une concession **plus grande** à la réouverture.
**Direction pré-enregistrée : la dérive DÉCROÎT avec la participation (Q1 > Q5).**
*Contrôle de contamination obligatoire :* corrélation de GS1 avec |rendement pré-pause|, puis
re-test de GS1 **résidualisé** sur |rendement pré-pause|. Si le gradient disparaît après
résidualisation, GS1 est une amplitude déguisée et il est **mort**.

**GS2 — durée de fermeture programmée (nature : CALENDRIER / STRUCTURE).**
Heures entre le règlement programmé de la séance précédente (17:00 ET du jour ouvré précédent)
et 18:00 ET du jour t, **calculées du seul calendrier**, donc connues à T-1. Trois niveaux
ordonnés : **semaine (≈1 h)** < **post-férié (≈25 h)** < **réouverture du dimanche (≈49 h+)**.
*Mécanisme :* le flux d'ordres non absorbé **s'accumule** pendant la fermeture ; la concession de
réouverture croît avec le déséquilibre accumulé.
**Direction pré-enregistrée : la dérive CROÎT avec la durée de fermeture.**

**GS3 — pression de clôture pré-pause, scale-free (nature : POSITION, PAS AMPLITUDE) — LE CROISEMENT.**
`CLV = (P_dernier − min(low)) / (max(high) − min(low))` sur les **15 dernières minutes cotées
avant la pause**, ∈ [0,1]. **Scale-free : c'est une position dans la fourchette, pas sa largeur.**
Séances dont la fourchette 15 min est nulle : exclues de GS3 (et comptées).
*Mécanisme — et c'est exactement le croisement demandé :* notre **matériau 2** établit que la
pression de clôture **continue** après la clôture parce que celui qui absorbe le déséquilibre de
clôture le dénoue ensuite. Si le même mécanisme d'inventaire opère sur l'or, une séance qui se
termine **en haut** de sa fourchette finale (déséquilibre acheteur dans le règlement) laisse les
teneurs **courts d'inventaire** pendant la coupure ; ils doivent se recouvrir à la réouverture,
d'où une dérive de réouverture **plus forte**.
**Direction pré-enregistrée : la dérive CROÎT avec le CLV pré-pause.**

### 2.3 Règles de mort chiffrées — section OR (lues post-2021, au GROSS)

| Règle | Contenu | Mort si |
|---|---|---|
| **KG0** hygiène (L60) | barres à fourchette nulle dans les 5 min autour de l'entrée et de la sortie, par année | > 5 % une année quelconque post-2021 ⇒ l'état n'est pas évaluable sur cette année |
| **KG1** GRADIENT | pente HAC(6) du rendement de fenêtre sur le rang causal de l'état | `\|t\| < 2.0` **ou signe contraire à la direction pré-enregistrée** |
| **KG2** MONOTONIE | quintiles d'état (3 niveaux pour GS2) | < 3/4 transitions dans la direction prédite (< 2/2 pour GS2) |
| **KG3** BASELINE APPARIÉE (L58) | gradient refait sur l'**excès BL-A** (ancres alternatives du même jour) | le gradient sur l'excès a `\|t\| < 2.0` ou change de signe |
| **KG4** RÉGIME (piège n°2) | walk-forward expanding **5 folds** post-2021 sur le quintile porteur | < 3/5 folds positifs |
| **KG5** VARIANCE vs MOYENNE (L54) | R²(moyenne) et R²(variance) côte à côte | R²(moyenne) < 0.5 % **et** R²(variance) > 3× R²(moyenne) ⇒ vol-scaler, pas conditionnement |
| **KG6** DSR | `dsr.py` racine, `n_trials` = compteur N1_OR déclaré | rapporté ; DSR < 0.90 interdit le mot **PASS** |
| **KG7** ÉCONOMIE | net à **1.84 bps** (centre) et **3.88 bps** (queue) — jamais la colonne `spread` | le sous-ensemble conditionnel n'améliore pas le **SR net** ni le **t net** de la version inconditionnelle ⇒ le conditionnement est inutile même s'il est réel |

**Ce que « PASS » signifie ici, et rien d'autre :** KG1-KG5 franchies, `\|t\| ≥ 2.63` (Šidák),
DSR ≥ 0.90, et KG7 améliorée. Toute combinaison inférieure est **UNDERPOWERED** ou **REJECTED**,
jamais un PASS.

---

## 3. SECTION 2 — la continuation de pression de clôture sur indices US (matériau 2)

**Section strictement séparée de la section 1 : compteur séparé, verdict séparé, aucun résultat de
l'une n'est utilisé comme argument dans l'autre.**

### 3.1 Forme de trade — GELÉE, héritée de `close_continuation_gold_subwindows` TEST A

- Instruments : **US100 (PORTEUR DE PREUVE)** ; US500 et US30 en réplication **avec leurs
  disqualifications héritées explicitement rappelées** (US500 échoue l'hygiène L60 à la barre de
  sortie, 9.64 % en 2019 ; US30 porte un momentum intraday générique t 2.90 et échoue la
  monotonie). Aucun des deux ne peut porter un verdict.
- Signal : `z` = z-score causal (250 séances, décalé de 1) du rendement des **K = 15 dernières
  minutes avant la clôture cash** (15:45→15:59 ET, prix de clôture M1).
- Position : **continuation**, `z > θ ⇒ LONG`, `z < −θ ⇒ SHORT`, **θ = 1.0**, **jambes
  disjointes** (L25), rapportées séparément.
- Entrée à l'**open de la barre 16:01+d ET** (delay+1 natif), sortie à l'**open de 16:11 ET**
  (horloge de sortie fixe) ; sortie à durée constante `16:11+d` en contrôle (L59).
- Retards pré-enregistrés **d = 0, 1, 2** — d = 0 est un plafond théorique, **d = 1 est la
  référence décisionnelle** (c'est le premier retard exécutable honnête).
- Échantillon **2018+**, coupure hors-échantillon **2022** (héritée, non re-choisie).

### 3.2 Les trois états, et leur raison MÉCANIQUE écrite d'avance

Tous calculés **à la clôture de t−1 ou du seul calendrier** — **aucune information du jour t
n'entre dans un état**. C'est plus strict que nécessaire, et c'est délibéré : cela rend toute
discussion de look-ahead sans objet.

**US1 — participation de la fenêtre de clôture de t−1 (nature : LIQUIDITÉ / ACTIVITÉ).**
`tick_volume` cumulé sur 15:45-16:00 ET du jour **t−1**, rang causal 250 séances.
*Mécanisme :* la continuation post-clôture est la **concession de liquidité** payée à qui absorbe
le déséquilibre de clôture ; à déséquilibre donné, l'impact est inverse de la profondeur
(Kyle). La participation de clôture est **fortement autocorrélée** d'un jour à l'autre, donc
celle de t−1 est un proxy ex-ante légitime de celle de t.
**Direction pré-enregistrée : la continuation DÉCROÎT avec la participation.**
⚠ *Le mécanisme concurrent est explicitement nommé d'avance* : « plus de volume de clôture = plus
de flux indiciel mécanique = plus de déséquilibre = plus de continuation », qui prédit le signe
**inverse**. Un gradient significatif de signe inverse sera rapporté comme **« gradient présent,
direction pré-enregistrée FALSIFIÉE »** — **pas** comme un PASS. Cette clause est écrite pour
m'interdire de récupérer les deux signes après coup.

**US2 — proximité de la fin de mois (nature : CALENDRIER STRUCTUREL).**
Nombre de jours ouvrés jusqu'à la fin du mois calendaire (0 = dernier jour ouvré), du seul
calendrier. Buckets ordonnés : `{0}`, `{1}`, `{2-3}`, `{4-6}`, `{≥7}`.
*Mécanisme :* les flux de réplication indicielle et de rééquilibrage se concentrent dans
l'enchère de clôture de fin de mois ; si la continuation est la trace d'un déséquilibre
d'enchère absorbé, elle doit être **plus forte** quand ce déséquilibre est mécaniquement plus
gros. **Direction pré-enregistrée : la continuation CROÎT quand on approche la fin de mois.**
⚠ **C'est ici que L58 mord le plus fort** (ZN : forte saisonnalité jour-du-mois, blackout ±3 j
⇒ faux PASS). La baseline **BL-B par bucket** est donc **obligatoire** pour cet état, et le
verdict est lu **exclusivement sur l'excès**.
*Note de coordination :* un agent frère travaille sur les flux calendaires. Ici la fin de mois
n'est **pas** un edge testé pour lui-même, c'est un **état de conditionnement** d'une forme de
trade préexistante ; s'il y a recoupement, il est de nature, pas d'objet.

**US3 — persistance du P&L propre de la sleeve (nature : AUTOCORRÉLATION D'INVENTAIRE).**
Moyenne du P&L gross de la **même** forme de trade sur les **5 séances précédentes** (jours sans
signal comptés 0), rang causal 250 séances.
*Mécanisme :* si la continuation est le dénouement d'un inventaire de teneur, cet inventaire ne
se solde pas nécessairement en 10 minutes ; un déséquilibre persistant produit une
**autocorrélation positive du P&L de la sleeve**. **Direction pré-enregistrée : la continuation
CROÎT avec le P&L des 5 séances précédentes.**
⚠ Contrôle obligatoire : le **placebo à décalage circulaire** de l'état est ici indispensable
(un état construit sur le P&L propre est structurellement persistant, et une série persistante
strictement dé-moyennée atteint 92.9 % de p(pass) à horizon long).

### 3.3 Règles de mort chiffrées — section INDICES (lues sur US100, au GROSS)

| Règle | Contenu | Mort si |
|---|---|---|
| **KU0** hygiène (L60) | fourchette nulle aux barres d'entrée et de sortie, par année | > 5 % une année ⇒ instrument non porteur de preuve (US500 est déjà disqualifié à ce titre) |
| **KU1** GRADIENT | pente HAC(6) du P&L de continuation (d=1) sur le rang causal de l'état | `\|t\| < 2.0` **ou signe contraire à la direction pré-enregistrée** |
| **KU2** MONOTONIE | quintiles d'état (5 buckets pour US2) | < 3/4 transitions dans la direction prédite |
| **KU3** BASELINE APPARIÉE (L58) | tout relu sur l'**excès BL-B** (inconditionnel en signal, dans le même bucket d'état) | le gradient sur l'excès a `\|t\| < 2.0` ou change de signe |
| **KU4** RÉGIME | walk-forward expanding **5 folds** 2018-2026 sur le bucket porteur | < 3/5 folds positifs |
| **KU5** VARIANCE vs MOYENNE (L54) | les deux R² côte à côte | R²(moyenne) < 0.5 % **et** R²(variance) > 3× R²(moyenne) |
| **KU6** JAMBES (L25) | jambes longue et courte du bucket porteur, disjointes | une jambe de signe contraire à la thèse ⇒ l'effet est du beta, pas de la continuation |
| **KU7** EXÉCUTABILITÉ — **la barre qui décide** | à **d = 1** et coût mesuré **1.8 bps RT** | gross du bucket porteur **< 2.8 bps** ou `t < 2.0` à d=1 ⇒ le conditionnement **ne sauve pas** l'edge, et la famille reste REJECTED sur l'exécution |

**KU7 est la règle décisive et elle est chiffrée d'avance.** L'inconditionnel vaut 1.96 bps à
d=1 (+0.16 bps net). Pour que le conditionnement change quoi que ce soit, il faut **≈ +43 % de
concentration** et un net ≥ **1.0 bps/trade**. En dessous, le résultat est un fait de
microstructure sans conséquence économique, et il sera écrit comme tel.

---

## 4. Comptage des essais (N1 SÉPARÉS, déclarés d'avance)

**N1_OR** : 3 états × 1 test de gradient primaire = **3 essais primaires**. Les quintiles, la
baseline appariée, le walk-forward, la résidualisation et le ladder de retard sont des
**contrôles du même essai**, comptés en cellules et non en essais.
**N1_IDX** : 3 états × 1 test de gradient primaire = **3 essais primaires**, même convention.
**Total primaire = 6**, seuil familial Šidák |t| ≥ 2.63 (§1.3).
Diagnostics **N0**, non comptés : L60 par série et par année, profils d'horloge, couverture des
barres, corrélations de contamination, audit de schéma de cache.
**Budget de modifications de spec : 3 maximum, 0 consommé à l'ouverture.** Toute modification
sera datée et justifiée dans `RESULTS.md`.

## 5. Ce qui serait un résultat NET même sans PASS

**Un gradient plat sur les six états est un résultat publiable en interne** : il dirait que nos
edges sous-puissants le sont **uniformément**, qu'aucun conditionnement de nature liquidité,
calendrier ou pression de clôture ne les concentre, et que la seule issue reste l'échantillon ou
le véhicule. Je m'engage à l'écrire tel quel s'il se produit, sans aller chercher un septième
état après avoir vu les six premiers.
