# PRÉ-ENREGISTREMENT — Dose-réponse du close momentum (mécanisme LETF)

**Écrit et committé AVANT toute mesure.** Aucune donnée n'a été chargée à l'heure de ce commit.
Compteur local : **N1**, ouvert à 0. Instrument-cellules comptées à la clôture.

---

## 1. Mécanisme testé

Baltussen, Da, Lammers, Martens (JFE 2021). Les ETF à levier doivent rééquilibrer **dans le sens
du mouvement du jour**, au plus près de la clôture ; les dealers courts gamma sont contraints dans
le même sens. Ce sont des acteurs **forcés**, opérant dans une **fenêtre bornée**, qui paient pour
s'exécuter. Mesure des auteurs : le flux LETF vaut **16.8 %** du volume MOC les jours à ±1 %, et
**50.2 %** les jours à ±5 %.

**La prédiction n'est pas « ça marche en moyenne ». C'est une DOSE-RÉPONSE** : l'effet doit croître
avec l'amplitude du mouvement de la journée, parce que la contrainte de rééquilibrage croît avec
elle. Un effet plat en amplitude falsifie le mécanisme même si la moyenne est positive.

## 2. Pourquoi ce n'est pas un re-run de l'essai SG-2

Ce desk a mesuré `sign(rendement 1re demi-heure) × dernière demi-heure` sur US100 : gross ≈ 0,
net −3 bps, t −6. **Ce test ne falsifie pas le mécanisme :**
1. le prédicteur du mécanisme est le **rendement cumulé open → 15:30**, pas la première demi-heure ;
2. le mécanisme prédit un effet **proportionnel à |mouvement|** ; pooler ~4 000 jours dilue vers
   zéro. Un gross poolé nul est **exactement ce qu'on attend d'un effet concentré** ;
3. SG-2 tournait à 3 bps RT ; le coût mesuré sur indices est **~1.8 bps**
   (`Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md`).

L'angle nouveau, écrit avant la donnée : **la forme de la courbe en amplitude**. Catégorie de
ré-ouverture : **puissance** (effet concentré dilué par le pooling) + **coût** (3 bps → 1.8 bps).

## 3. Spécification gelée

### 3.1 Instruments et horloges (L56 — horloge de l'ÉCHANGE avec son DST, jamais UTC)

| Instrument | Horloge | Session cash | Fenêtre prédicteur | Fenêtre de trade |
|---|---|---|---|---|
| US500, US100, US30 | `America/New_York` | 09:30 → 16:00 | 09:30 → 15:30 | 15:31 → 16:00 |
| GER40 | `Europe/Berlin` | 09:00 → 17:30 | 09:00 → 17:00 | 17:01 → 17:30 |
| **XAUUSD** (contrôle −) | `America/New_York` | — (continu) | 09:30 → 15:30 | 15:31 → 16:00 |

Source : **`data/deep_history_utc/*_M1.csv`** (vrai UTC vérifié), importé du répertoire principal
par chemin absolu, **lecture seule**. `data/panels/m5_indices/` est **INTERDIT** (EET étiqueté
`timestamp_utc`, −2 h — a déjà fait tester 43.9 % de barres de pré-marché).

**Test de falsification d'horloge, exécuté AVANT tout le reste** : profil horaire moyen
(|rendement| par heure) calculé séparément sur l'échantillon d'hiver et celui d'été, corrélé
hiver-vs-été **dans les deux horloges**. Attendu si l'horloge d'échange est la bonne :
corr(ET) ≫ corr(UTC). Si ce n'est pas le cas, la spécification d'horloge est fausse et le reste du
test est invalide — on s'arrête là.

### 3.2 Signal et trade (L59 — delay+1 sur l'ENTRÉE **et** la SORTIE)

- `R_day` = rendement cumulé `open(09:30) → close(15:30)`, en bps, horloge d'échange.
- `side = sign(R_day)`.
- **Entrée** : close de la barre M1 **suivante** (15:31), jamais la barre du signal.
- **Sortie** : close de la dernière barre de la session (15:59/16:00).
- **Variante de robustesse obligatoire** : sortie une barre plus tôt (15:58) — si l'effet vit
  entièrement dans le dernier print, il n'est pas exécutable et doit être déclaré tel quel.
- Aucun stop, aucun bracket : la géométrie de sortie est **constante** par construction (L59).

### 3.3 Dosage

Deux découpages rapportés côte à côte :
- **Quintiles de |R_day|** par instrument (n égaux) — c'est la courbe demandée ;
- **Bins absolus ex-ante**, alignés sur le papier et **sans look-ahead** :
  `[0,50) [50,100) [100,200) [200,500) [500,∞)` bps.
Le découpage absolu est le juge en cas de désaccord : les seuils sont connus d'avance.

### 3.4 Jambes disjointes (L25)

Chaque bin est rapporté **séparément pour `R_day > 0` et `R_day < 0`**. Ce sont des jours
disjoints. Une jambe obtenue par `−side_long` ne compte pas. Le mécanisme exige les deux :
un LETF long rachète à la hausse, vend à la baisse.

## 4. Critères de falsification — les trois, conjointement

Le test est un **PASS** seulement si les trois tiennent :

1. **MONOTONIE** du gross à travers les bins de dose (croissance faible tolérée, mais gradient
   présent et de bon signe). *Un pic isolé sans gradient est du bruit sélectionné, pas un
   mécanisme.*
2. **BIN HAUT > 5.4 bps** de gross par trade. Seuil L11b : `E[gross/trade] > 3 × coût/trade`,
   soit `3 × 1.8`.
3. **CONTRASTE DE MÉCANISME (L44)** : l'écosystème LETF est massivement américain ⇒ attendu
   **US500/US100 ≫ GER40 ≫ XAUUSD**. **XAUUSD est le contrôle négatif** : s'il montre le même
   effet dans la même fenêtre horaire, ce n'est pas le mécanisme LETF mais un **artefact de
   clôture générique**, et le candidat est mort quelle que soit la valeur des gross.

Si la courbe est **plate** : la famille est **fermée sur le mécanisme**, définitivement. C'est une
issue aussi bonne que l'autre et elle est rapportée comme telle.

## 5. Contrôles obligatoires (chacun a déjà coûté à ce desk)

- **L58 — baseline inconditionnelle appariée AU BIN.** Chaque bin est comparé à l'espérance
  inconditionnelle de la **même forme de trade dans le même bin**, jamais à une baseline pleine
  fenêtre. Les jours de grande amplitude ont une moyenne inconditionnelle différente ; une
  baseline globale **fabriquerait un faux PASS**. Rapporté : `E[r_fenêtre]` non signé par bin.
- **Placebo à autocorrélation appariée** (décalage circulaire du vecteur `side`, ≥200 tirages),
  par bin. Une série de moyenne nulle mais persistante produit un Δ apparent (+0.1495 mesuré
  ailleurs sur ce desk). Le gross doit battre le **p95 du placebo**, pas zéro.
- **L60 — barres à fourchette nulle** (`high == low`), par instrument, par an, **et restreint à la
  fenêtre de trade**. ⚠ US30 est signalé à 79.7 / 100 / 74.9 % en 2019/2020/2021. Toute année
  au-dessus de ~20 % dans la fenêtre est exclue ou explicitement marquée non citable.
- **L54 — moyenne vs variance.** Si l'amplitude prédit surtout la **variance** du rendement de
  fenêtre et non sa moyenne, ce n'est pas une sleeve : `σ` par bin est rapporté à côté de `μ`, et
  le ratio `μ/σ` par bin est la vraie courbe décisionnelle.
- **t_HAC Newey-West lag 6**, IC par **bootstrap par blocs** (Politis-Romano), **jamais iid**.
- **DSR** via `dsr.py` (racine) uniquement si un PASS émerge. ⚠ `framework.py:131` et
  `ftmo_lab.py:232` sont CASSÉES (σ_SR_trials absent) — interdites ici.

## 6. Coût — appliqué seulement APRÈS le gate gross

`cost_rt = 0` pour toute la courbe dose-réponse. Le gate 5.4 bps est un gate **gross**. Si et
seulement si le gate passe, le net est calculé avec les coûts **mesurés** du COST_AUDIT
(US500 1.82, US100 1.80, US30 1.47, GER40 1.73, XAUUSD 1.84 bps RT). La colonne `spread` seule
n'est **jamais** utilisée comme coût.

## 7. Ce qui n'est PAS fait dans ce test

Pas de p(pass), pas de sizing, pas de simulation de barrière — sauf si les trois critères de §4
passent. Le mandat s'arrête à la forme de la courbe. Pas de modification de spécification après
avoir vu la donnée : le budget de modifications est **0**.

## 8. Vocabulaire de sortie

**PASS** / **REJECTED** / **UNDERPOWERED** (IC contenant zéro sur échantillon insuffisant ≠ rejet).
