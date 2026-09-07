# Modélisation 5 ans du compte funded — la barrière journalière n'a jamais été touchée

**2026-09-07.** Book funded **réellement déployé** (or et USDJPY à poids nul), règles FTMO funded :
perte journalière max 500 $ sous l'ancre de 00:00, plancher statique 9 000, retrait tous les
14 jours de trading (part trader 80 %). Δn_tests = 0 — simulation sur série existante.

## Réponse directe

**Zéro bust sur la barrière journalière. Dans toutes les configurations testées.**

| horizon | cohortes | **bust JOURNALIER** | bust STATIQUE | marge min. journalière | P(net > 0) |
|---|---|---|---|---|---|
| 6 mois | 227 | **0** | 0 | +337,70 $ | 71,8 % |
| 1 an | 218 | **0** | 3 | +337,70 $ | 78,4 % |
| 2 ans | 200 | **0** | 25 | +337,70 $ | 84,5 % |
| 3 ans | 182 | **0** | 26 | +337,70 $ | 85,2 % |

**Tous les busts passent par le plancher statique**, jamais par la barrière journalière. Le compte
ne meurt pas d'une séance violente : il meurt d'une érosion lente.

## Le chemin continu 2021-2026

1 238 séances, du 2021-09-01 au 2026-06-05.

| | |
|---|---|
| bust journalier / statique | **0 / 0** |
| marge minimale vs plancher journalier | **+349,57 $** |
| marge minimale vs plancher statique | +598,62 $ |
| retraits cumulés (part trader) | **+3 539,20 $** |
| solde final | 9 833,93 $ |
| max drawdown du solde | −8,12 % |

Soit environ **708 $/an** de retraits sur un compte de 10 000 $, le solde revenant à peu près à son
point de départ.

## Pourquoi la barrière journalière est hors de portée

| | pire séance | en $ | % de la barrière |
|---|---|---|---|
| 2022-05-23 | −1,489 % | −148,86 | **29,8 %** |
| 2024-07-23 | −1,226 % | −122,62 | 24,5 % |
| 2025-04-08 | −1,179 % | −117,90 | 23,6 % |
| 2026-03-02 | −1,176 % | −117,63 | 23,5 % |
| 2023-08-01 | −1,171 % | −117,14 | 23,4 % |

**La pire séance de cinq ans vaut 30 % de la barrière.** Il faudrait une journée à −5,0 % pour
buster, soit **3,4 fois** le pire jour observé.

Jours les plus proches du plancher, en marge résiduelle : +331,08 $ (2026-03-02), +332,85
(2025-11-03), +333,48 (2025-04-08). **Le compte n'a jamais été à moins de 330 $ du plancher
journalier en cinq ans.**

## ⚠ La limite qui compte, et elle est structurelle

**Cette simulation ne voit que les CLÔTURES quotidiennes.** La barrière FTMO se contrôle sur
l'**équité intra-journalière**, toutes les 5 minutes. Une excursion intraday peut franchir la
barrière et revenir avant la clôture — invisible ici.

Ce n'est pas théorique : le dépôt a **déjà** connu ce cas. Le breach du compte <ACCOUNT_ID> (juillet)
était un flash move sur USDJPY, donc intraday, et la note de l'époque conclut que **« le sim
sous-estime cette queue »**.

⇒ **Le zéro de la colonne « bust journalier » est un zéro sur données de clôture, pas une preuve
d'impossibilité.** La vraie protection contre l'intraday est le breaker M5 (mise à plat si la marge
descend sous 30 % du budget journalier), qui est armé et n'apparaît pas dans ce modèle.

## Lecture opérationnelle

Le profil de risque de ce book est **une érosion lente, pas un accident**. Ça a deux conséquences :

1. **Le danger est le plancher statique**, pas la barrière journalière. Surveiller la tendance du
   solde sur plusieurs semaines compte plus que surveiller une séance.
2. **Le breaker M5 protège contre le scénario que ce modèle ne voit pas.** C'est lui qui porte le
   risque de queue intraday — sa désactivation serait le vrai changement de profil, pas un
   ajustement de sizing.
