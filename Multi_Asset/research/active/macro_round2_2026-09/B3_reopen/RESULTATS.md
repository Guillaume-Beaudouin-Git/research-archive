# B3 ré-ouverture — résultats

**2026-09-06.** Spec gelée : `PREREGISTRATION.md` (commit `40465436`). Moteur `code/engine_jk.py`.
Ledger 182 événements, **164 appariés** aux chocs Jarociński-Karadi, fenêtre commune
**2004-01 → 2024-01** (les chocs s'arrêtent en janvier 2024, comme annoncé au gel).

---

## 1. Mon hypothèse est RÉFUTÉE — et par la composition, avant tout rendement

J'avais avancé que le brut nul de l'étude d'origine était une **annulation** entre un choc de
politique monétaire et un choc d'information de signe opposé.

**Il n'y a pas assez de masse d'information pour annuler quoi que ce soit.**

| composante | médiane \|.\| | p75 | p90 | max | ≥ 5 bps |
|---|---|---|---|---|---|
| `pc1` (surprise totale) | 1,80 bps | 4,20 | 7,68 | 24,76 | 33 / 170 |
| `MP_pm` (politique) | 0,88 | 3,70 | 6,85 | 24,76 | **29** |
| `CBI_pm` (information) | **0,00** | 0,32 | 1,42 | 10,18 | **3** |

Parmi les grandes surprises FOMC de 2004-2024, **environ 91 % sont des chocs de politique
monétaire purs**. La composante information est quasi vide : médiane exactement nulle, p90 à
1,4 bps. Le bras CBI ne compte que **2 événements** tradés au seuil gelé — intestable, et surtout
sans la masse nécessaire pour compenser quoi que ce soit.

⇒ **L'axe « mélange » est fermé mécaniquement.** Ce n'était pas la bonne explication du nul.

## 2. Mais le proxy journalier atténuait bien — et c'est mesurable

L'étude d'origine anticipait cette possibilité dans son propre gel (*« accepted as noisier,
attenuation biases toward NO-GO »*) sans pouvoir la tester. On peut maintenant.

⚠ **Amendement déclaré.** Le seuil de 5 bps ne se transposait PAS directement : l'unité est la
même mais la dispersion n'a rien à voir (surprise haute fréquence médiane 1,8 bps contre variation
journalière du 2 ans médiane 4,0 bps). Mon pré-enregistrement affirmait le contraire — **c'est une
erreur de spécification de ma part**. Correction par une règle aveugle au résultat : seuil
**apparié en quantile** au taux de trade de l'étude d'origine (37,4 %), soit **2,06 bps**.
**Contamination à déclarer** : j'avais déjà vu le résultat à 5 bps (positif, non significatif) quand
j'ai posé cet amendement. J'avais donc un a priori directionnel. +1 essai.

| mesure de surprise | H=5 | H=10 | H=20 |
|---|---|---|---|
| **d2y journalier** (étude gelée, n=75) | +6,8 bps, t +0,46 | +4,5, t +0,24 | −0,8, t −0,08 |
| **choc HF politique** (n=62, seuil apparié) | **+21,2 bps, t +2,15** | **+30,0, t +1,60** | **+45,9, t +2,32** |

Le brut passe d'à peu près zéro à +21/+46 bps par événement, et le t de ~0 à ~2,2. **L'identification
de la surprise n'était pas un détail.**

## 3. Et pourtant : UNDERPOWERED, pas « presque significatif » (L65)

| H | n | brut | t_HAC | MDE80 | **effet / MDE80** | n requis pour t=2,5 |
|---|---|---|---|---|---|---|
| 5 | 62 | +21,15 bps | +2,15 | 32,39 | **0,65** | 116 |
| 10 | 62 | +29,96 | +1,60 | 47,68 | **0,63** | 125 |
| 20 | 62 | +45,87 | +2,32 | 70,41 | **0,65** | 116 |

L'effet est à **deux tiers de son propre plancher de détection** aux trois horizons. Un t de 2,32
avec un ratio effet/MDE de 0,65 n'est pas un résultat solide : c'est un échantillon trop petit qui a
eu de la chance. Le t est d'ailleurs **non monotone en horizon** (2,15 → 1,60 → 2,32), ce qu'un vrai
drift ne devrait pas produire.

**L'échantillon ne peut pas grandir de façon utile.** Il faudrait ~116-125 événements tradés contre
62 ; à 8 réunions par an et 37,4 % de taux de trade, cela représente **environ 18 ans** de données
supplémentaires. Et on ne peut pas remonter dans le passé : les chocs JK démarrent en 1990, mais
**IEF n'existe que depuis 2002** — l'instrument, pas le choc, est le facteur limitant.

## 4. Verdict, contre les critères gelés

| critère gelé | atteint ? |
|---|---|
| **Kill mécanique** — les deux composantes nulles en brut (\|t\| < 2,0 ET moyennes sous ±3 bps) | **non** — les moyennes MP valent +21 à +46 bps |
| **Validation partielle** — deux composantes non nulles, de signe opposé, stables sur 3 sous-périodes | **non** — la composante information n'a pas de masse |

**⇒ NON CONCLUANT**, exactement comme le pré-enregistrement le prévoyait pour ce cas.

Mais l'étude n'est pas vide, et le statut du kill se précise :

- **Axe « mélange » : FERMÉ MÉCANIQUEMENT.** Réfuté par la composition des chocs, indépendamment
  des rendements. Non rouvrable.
- **Axe « atténuation du proxy » : CONFIRMÉ dans son sens, mais NON DÉCIDABLE.** Corriger la mesure
  déplace le brut de ~0 à +21/+46 bps — le proxy journalier détruisait bien du signal. Mais l'effet
  corrigé reste sous son MDE, et **l'échantillon disponible ne permettra pas de trancher** avec cet
  instrument.

## 5. Ce que je ne recommande pas

Ne pas déployer sur ce résultat. Un ratio effet/MDE de 0,65 avec un t non monotone est précisément
le profil qui produit un faux positif après déflation — et le DSR du gel d'origine était déjà à
≤ 0,02 à N=101 essais.

Ne pas non plus faire varier l'instrument, l'horizon ou les banques centrales pour « aller chercher »
la significativité : le problème n'est pas la spécification, c'est le nombre d'événements. Toute
grille supplémentaire sur un échantillon de 62 achète du multiple testing, pas de la puissance.

**Reste ouvert et non testé ici** : le même choc HF sur un instrument à historique plus long que
IEF (futures ZN, ou un indice de rendement total obligataire remontant avant 2002) permettrait
d'utiliser les événements 1990-2002 et d'approcher les ~116 requis. C'est un axe de **véhicule**,
donc rouvrable — mais il exige son propre pré-enregistrement.
