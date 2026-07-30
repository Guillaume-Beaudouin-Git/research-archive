# INVENTAIRE DES EDGES MESURÉS — fouille du repo, 2026-07-30

> **Contribution à `n_tests` : 0.** Aucun backtest, aucun re-test, aucune re-mesure. Ce document
> est une **lecture** de ce qui existe déjà : rapports, POSTMORTEM, ledgers, CSV de résultats et
> mémoires de projet. Le DSR de tous les candidats futurs est intact.
>
> Données machine-lisibles : **`INVENTORY.csv`** (118 entrées, 16 colonnes).
> Reproduire : `/usr/bin/python3 build_inventory.py` (concatène `rows_0*.psv`, ajoute la colonne véhicule).

---

## 0. Ce que la fouille a trouvé, en un paragraphe

Le repo contient **118 entrées mesurées identifiables** (représentant ~213 stratégies une fois les
cohortes oxfordstrat/session dépliées). **L'hypothèse de départ est confirmée : le month-end n'était
pas seul.** Il existe au moins **neuf edges à `t_HAC ≥ 3`, mesurés, audités, non contestés dans leur
statistique**, qui ont été classés morts pour une raison qui n'est pas leur signal — dont **un bloc de
quatre à `t 3.6–4.8`** (or / argent / WTI / soja overnight-drift) tué par la géométrie du challenge
FTMO et le tarif CFD, et **un bloc de trois saisonnalités précieux-Q1 à `t 3.0–3.7` net de coût CFD**
tué par la *sparsité* (1 fenêtre/an contre une horloge de 91 jours qui est **auto-imposée**). Aucune de
ces contraintes n'existe sur le compte IBKR. En face, la distribution des causes de mort reste
**saine** : ~76 % des kills (pondérés stratégie) sont **mécaniques**. Le processus de recherche ne
jette pas des edges valables en masse — mais il a systématiquement laissé mourir les edges valables
**au dernier gate, celui du véhicule**, et il l'a fait **neuf fois**.

---

## 1. Tableau complet — trié par force statistique décroissante

Extrait des 35 premières entrées. **Table complète : `INVENTORY.csv`.**
Colonnes clés du CSV : `t_stat`, `kill_reason`, `kill_class`, `reopenable`, `futures_vehicle_fits_13k`, `source`.

| # | Edge | Famille | Instr. | N | Sharpe | **t** | Verdict d'origine | **Raison du kill** | **Classe** |
|---|---|---|---|---|---|---|---|---|---|
| E001 | **Month-end Treasury (dash-for-cash)** | flux contraint | TLT/ZN/ZF/ZB | 311 évts | 0.92 net | **4.65 / 4.79 / 4.6-6.0** | VALIDATED, rejeté 2× | pas d'instrument obligataire FTMO, puis gel firmes futures | **VÉHICULE — RÉSOLU** |
| E002 | **ASIA_23_8 or overnight** | dérive de session | XAUUSD | 4001 j | 1.10 / OOS 0.96 | **4.82** | FTMO NON-VIABLE | mur 91 j **auto-imposé** + barrière −5 % percée à VT 3× + pas d'accès funded | **GÉOMÉTRIE + VÉHICULE** |
| E003 | **Argent overnight (post-2014)** | dérive de session | XAGUSD | ~3000 j | 1.45 gross | **4.55** | NON-VIABLE (panier) | géométrie panier FTMO + régime-conditionnel (nég. 2003-09) | **GÉOMÉTRIE + COÛT** |
| E005 | **Soja reopen drift** | dérive de session | SOYBEAN | ~2000 j | 1.32 / 1.08 @2bps | **4.60** (α) | NON-VIABLE FTMO | spread CFD ; OOS faible (0.49) ; le rapport recommande lui-même ZS/MZS à 1.5 bps | **COÛT + PUISSANCE** |
| M047 | TSMOM multi-actifs FTMO (le moteur) | trend | 6-14 CFD | ~2000 j | 0.9 gross → **0.0 net** | 4.70 gross | NO-GO | ~8 %/an de prime mangés par ~8 %/an de portage agrégé | **COÛT** (re-testé futures : SR 0.35-0.47) |
| M043 | Filtres de signal sur TSMOM | overlay | 19 CFD | 9 variantes | 0.90 best | 5.12 | 0 brique neuve | les 2 meilleures variantes sont du TSMOM déguisé (corr 0.69 / 0.95) | **MÉCANIQUE** |
| E004 | **WTI overnight** | dérive de session | USOIL | ~3300 j | 1.09 gross | **3.64** | NON-VIABLE (panier) | marge fine contre le spread CFD (break-even 3.5 bps) | **COÛT + GÉOMÉTRIE** |
| E016 | **Reversal 1 j SPX** | réversion CT | SPX/ES | 8097 j | 0.70 | **3.61** | CANDIDATE-near-dead | effondrement délai+1 (0.57→0.08) — artefact close-print **suspecté, jamais vérifié** | **GÉOMÉTRIE (horloge)** |
| E014 | **S1 VRP (VIX−RV) swing** | prime de vol | QQQ/NQ | 5026 obs | 0.467 gross / **0.454 futures** | **3.59** (IC) | FAIL RESEARCH_PASS | turnover 33×/an au coût **ETF** + gate « Sharpe > 0.7 en standalone » depuis **abandonné** | **COÛT + gate abandonné** |
| R015 | Fix reversal WMR (pattern B) | microstructure FX | G10 | true-UTC | — | **3.55** | NO-GO (L34) | tier de coût retail (besoin < 1 bp/jambe vs 2.48 mesuré) | **COÛT (institutionnel)** |
| E007 | **Platine janvier** | saisonnalité physique | Platinum | ~21 janv. | — | **3.74 g / 3.00 net-CFD** | survit net-CFD | sparsité : 1 fenêtre/an contre l'horloge du challenge | **GÉOMÉTRIE** |
| E006 | **Argent janvier** | saisonnalité physique | XAGUSD | ~21 janv. | — | **3.72 g / 3.07 net-CFD** | survit net-CFD | idem E007 (+ DSR×12 0.864 si janvier traité comme best-of-12) | **GÉOMÉTRIE** |
| E008 | **Or janvier** | saisonnalité physique | XAUUSD | 22 janv. (15/22+) | — | **3.22** | KEEPER | idem ; décroît (pré-2013 +251 → 2013+ +120, t 1.66) | **GÉOMÉTRIE** |
| M001 | CS macro momentum 17 instr. | momentum XS | 17 CFD | 3294 j | 0.36-0.41 | 3.18 (jambe longue seule) | **FERMÉ 07-29** | two-sided à coût **ZÉRO** : long +2.93 t 3.18 / short −0.85 t −0.90 | **MÉCANIQUE** |
| E009 | Précieux-Q1 combiné (Ag+Pt+Pd+Au) | saisonnalité | 4 métaux | ~21 janv. | — | 2.82 / 2.42 net | topping, pas moteur | sparsité | **GÉOMÉTRIE** |
| R004 | Unlock cliff short | événement calendaire | alt perps | 578 évts | — | 2.90 (DSR 0.94) | NO-GO (L49) | **sous le placebo apparié** malgré t/décroissance/DSR OK | **MÉCANIQUE** |
| E015 | VIX-term carry timé | carry de vol | VIXY/VX | 3871 j | 0.73 → 0.66 @20bps | 2.86 | DEAD-for-portfolio | mandat **skew+** : skew −0.01, β equity +0.26, corr +0.44 TSMOM | **GÉOMÉTRIE (mandat)** |
| E012 | **Gap Pattern Type A** | continuation de gap | 30 CFD | 3438 trades | 0.99 (0.30 récent) | délai+1 **améliore** | DISCARD 1/4 | **DSR invalidé** (1.39<1.52) + « ne bat plus le buy&hold récent » | **PUISSANCE + gate** |
| M026 | Post-limit-move reversion | réversion extrême | US500 | 110 évts | — | 2.30 (bear 2.12 / bull 1.38 NS) | KILL two-sided | asymétrique = dip-buying = beta long conditionnel | **MÉCANIQUE** |
| M042 | Filtres de régime (breadth) | overlay | indices | 5 filtres | 0.53 | 2.62 | 0 brique | échoue *beat-the-beta* (panier EW + même breadth = 0.87 > 0.53) | **MÉCANIQUE** |
| M002 | Pré-FOMC US30/GER40 | dérive événementielle | US30/GER40 | 97/99 évts | 0.96 (sur 49) | 2.41 → **2.12 sur 97** | **FERMÉ 07-29** | effet de **régime** : GER40 pré-2020 t 0.01 ; doubler N **baisse** le t | **MÉCANIQUE** |
| M006 | Piste B range-fade (XAU) | réversion de range | XAUUSD | 1607 trades | 0.57 net | 2.48 | FALSIFIED | la **détection** du range est look-ahead (causal −0.06 vs oracle +2.66) ; jambe XAU cost-dead | **MÉCANIQUE + COÛT** |
| M023 | Pré-CPI drift | dérive événementielle | indices US | 77 évts | — | 2.12 → **1.53 ex-2025** | NON-SURVIVOR | le t est porté par **une** année aberrante (2025 : +121 bps) | **MÉCANIQUE** |
| R012 | H1 réversion London-open | intraday FX | EUR/GBP/CHF/CAD | 127/paire | 0.60 gross | 2.11 (contraste XS) | DEAD (L43) | gross ~0.5 bps vs coût ; **déjà re-vérifié au tarif futures** — gate toujours non franchi | **COÛT (clos)** |
| E017 | **VIX expiry SOQ (day-after)** | dislocation d'enchère | ^VIX / VIXY | 182 évts | +2.07 | **2.02 spot / 1.76 tradable** | NEAR-MISS différé | gate-0 FTMO (ETF) + le daily ne voit pas le print SOQ | **VÉHICULE + PUISSANCE** |
| E010 | Café juillet (gel Brésil) | saisonnalité | COFFEE | ~21 juil. | — | 1.55 g / **1.96 net mesuré** | fragile | DSR×12 0.34 + edge concentré sur le gel 2020 | **PUISSANCE** |
| M048 | Donchian breakout daily | trend | panier | ~2000 j | 0.35 → −0.73 net | 1.98 | DEAD | long-biaisé (+0.71/−0.20), IS 0.96 → OOS 0.18, swap sur notionnel tenu | **MÉCANIQUE + COÛT** |
| M049 | XS-momentum panier | momentum XS | panier | 2094 j | 0.40 | 1.95 | WRONG-PROFILE | skew −0.16, corr +0.39 TSMOM | **MÉCANIQUE** |
| M007 | Piste C MR daily indices | réversion | 4 indices | 84 cellules | 0.53 best | 1.89 | FALSIFIED | jambe short négative sur **48/48** cellules ; le swap *favorise* le short ⇒ le tueur est la dérive | **MÉCANIQUE** |
| E011 | Blé mai (winter-wheat) | saisonnalité | WHEAT | ~21 mai | — | 1.69 g / 0.89 net | meurt | swap grain CFD −115 bps/mois + DSR×12 0.29 | **COÛT + PUISSANCE** |
| E018 | **Lev-ETF EOD rebalance** | flux mécanique | NQ | 1172 j | 0.59 (Q70) | 1.28 | NEAR-MISS différé | dose-réponse monotone (signature correcte) mais t plafonne ; coût intraday jamais mesuré | **PUISSANCE + COÛT** |
| E013 | Gap Pattern Type B | continuation de gap | 30 CFD | — | 1.02→1.14 délai+1 | — | DISCARD 1/4 | **DSR invalidé** (1.02<1.52) | **PUISSANCE** |
| M022 | CPI/NFP gap continuation | continuation | US100 | 146 évts | +6.5 bps net | 0.69 | sous-seuil | seul candidat à la **bonne forme** two-sided (+9.7/+9.1) mais mangé par le spread | **PUISSANCE + COÛT** |
| M020 | Gao time-of-day momentum | momentum intraday | NQ | 3978 j | gross ~0 | **−6.08 net** | mort robuste | gross nul même pré-2015, aucune jambe ne marche | **MÉCANIQUE** |
| E020 | **Cycle d'adjudication Treasury** | flux contraint | ZN/ZB/ZF | **JAMAIS MESURÉ** | — | — | SKIPPÉ au gate-0 | skippé **sans mesure** parce que les obligations ne sont pas FTMO. Sa sœur de famille est le meilleur edge du repo | **VÉHICULE (zéro information)** |

---

## 2. SHORTLIST — `t ≥ 3` (ou Sharpe ≥ 1.0, N décent) **et** kill rouvrable

**Neuf dossiers.** Pour chacun : ce qui l'a tué · pourquoi c'est rouvrable · le test décisif le moins cher.

### ⭐ 1. `ASIA_23_8` — or overnight 23:00→07:00 UTC · **t_HAC(α) 4.82**
`Sharpe 1.10 / OOS 0.96 / DSR 0.99 / WF 5/5 / MaxDD −19.4 % / β_or 0.004 / R² 0.001 / 17-20 ans positifs / skew +0.35`
- **Ce qui l'a tuée** : rien de statistique. (a) trop lente pour le **mur de 91 jours** — first-passage terminal 58-66 % mais médiane 200-300 jours ; (b) la barrière **−5 % journalière** est percée par le *low* intraday au plafond VT 3× ; (c) pas de chemin d'accès funded en standalone.
- **Pourquoi rouvrable** : les trois contraintes sont **spécifiquement FTMO**. Le mur de 91 j est **auto-imposé** — FTMO n'a aucune limite de temps (audit desk 07-24) — et sur IBKR il n'existe ni barrière, ni horloge, ni split. En version *funded* sans cible, elle survivait déjà à 92.4 %/12 mois avec un stop −2.5 % qui, **contre-intuitivement, ne mange pas l'alpha** (Sharpe 1.12, DSR 0.99).
- **Véhicule** : MGC (micro or) ≈ **$40 k/lot** (mesuré in-repo). La **marge tient** dans €13 k ; c'est le **notionnel** qui contraint — 1 lot = ~3× de gross, donc la cible de vol de la recherche (~6.8 %) n'est pas atteignable par le bas. Granularité, pas marge.
- **⚠ Le point qui décide** : le « swap-free » est une **propriété du rollover FTMO** (00:00 serveur = 21:00/22:00 UTC, jamais dans la fenêtre). Sur futures il n'y a pas de swap du tout — mais on paie **deux fois par jour** commission + slippage. Si l'aller-retour micro dépasse ~1.5 bps, l'edge (2.58 bps/jour brut) se dégrade vite.
- **Test décisif le moins cher** : relever le **coût aller-retour réel de MGC** (commission IBKR + 1 tick) et le comparer à la table de sensibilité au spread **déjà publiée** dans la due-diligence (Sharpe par bps) — c'est une lecture de table, zéro backtest.

### ⭐ 2. Argent overnight post-2014 · **t_HAC 4.55**, DSR 1.00
`Sharpe gross 1.45 · α t 4.6 · R² 0.000 · break-even 5.3 bps RT · net 0.69-0.95 à ≤3 bps`
- **Ce qui l'a tuée** : géométrie du **panier** FTMO (l'agrégation gold+silver+WTI ne bat pas la dilution solo) et le caractère **régime-conditionnel** (négatif chaque année 2003-2009, l'edge émerge ~2010).
- **Pourquoi rouvrable** : la « dilution du panier » est une contrainte de **barrière partagée**, pas une propriété de l'edge — hors barrière, un sleeve décorrélé à SR 1.45 s'additionne au lieu de se diluer. Et c'est **le plus gros coussin de spread de tout le repo** (5.3 bps de break-even contre ~1.2-1.6 bps en micro-futures).
- **Véhicule** : SIL (micro argent, 1000 oz) — notionnel **non relevé cette session**, à vérifier. SI plein (5000 oz) **ne tient pas** dans €13 k.
- **Test décisif** : relever le notionnel et l'aller-retour de SIL, et vérifier que le régime post-2010 tient encore sur 2024-2026 (lecture du tableau annuel déjà publié).

### ⭐ 3. Soja reopen drift · **α t_HAC 4.6**
`Sharpe 1.32 gross / 1.08 @2 bps / DSR 0.75 · MaxDD −19.7 % · OOS 0.49 · skew −1.9`
- **Ce qui l'a tuée** : le spread CFD (il faut ≤2 bps), la moitié OOS faible, et une sortie de drawdown de 4 ans.
- **Pourquoi rouvrable** : le rapport de due-diligence **écrit lui-même la conclusion** — « préférer les futures CBOT (ZS / micro MZS, ~1.5 bps RT → Sharpe ~1.3) ; exécution futures = la route la plus propre ». Le kill est un kill de tarif, sur un véhicule qu'on n'utilisait pas.
- **Véhicule** : MZS (micro soja, 500 bu = 1/10 de ZS) — tient probablement dans €13 k ; ZS plein non.
- **Réserve honnête** : c'est le plus faible des quatre (skew −1.9, OOS 0.49). Sa valeur réelle est la **complémentarité de régime avec l'or** (fort 2018-2021 = exactement quand l'edge asiatique de l'or était mort).
- **Test décisif** : confirmer le RT de MZS ≤ 2 bps, puis lire la ligne correspondante de la table de sensibilité au spread déjà publiée.

### ⭐ 4. WTI overnight · **t_HAC 3.64**, DSR 0.94
`Sharpe 1.09 sur les 13 ans complets (pas de patch de régime) · skew +0.43 · R² 0.002 · 11/14 ans · break-even ~3.5 bps`
- **Ce qui l'a tué** : marge fine contre le spread CFD (net 0.29 @3 bps) + géométrie du panier.
- **Pourquoi rouvrable** : c'est le seul de la famille **sans patch de régime** et avec un **skew positif**, et le **micro-WTI est le contrat le mieux dimensionné pour €13 k** (~$8-14 k/lot, mesuré in-repo) — le seul de la famille dont la granularité ne force pas un levier subi.
- **Test décisif** : RT réel de MCL vs le break-even 3.5 bps déjà publié.

### ⭐ 5. Bloc saisonnalité précieux-Q1 — argent / platine / or janvier · **t net-CFD 3.07 / 3.00 / 3.22**
`Survit au coût CFD le plus lourd testé (21 nuits × −3.5 bps + spread = −81 bps/mois), robuste à 2× l'hypothèse de swap`
- **Ce qui l'a tué** : **la sparsité, pas le signal.** 1 fenêtre/an ⇒ à vol-target prudente le sleeve fait +1.1 %/janvier ⇒ +10 % demande ~8 ans ; à un levier qui va vite (L≥4), 25-36 % de breach de la règle journalière. Aucun *sweet spot* : entre L=1 (8 ans) et L=4 (bust), L=2-3 est médiocre des deux côtés.
- **Pourquoi rouvrable** : « 8 ans pour faire +10 % » n'est un problème que **s'il y a une horloge**. Sur le compte personnel il n'y en a pas : un sleeve à +1.1 %/an décorrélé, qui ne porte du risque que 21 jours par an, est **exactement** le profil de complément recherché (le raisonnement qui a fait passer B1). Et il survit déjà au tarif CFD — sur futures le coussin ne peut que grandir.
- **Véhicule** : **c'est ici que ça coince**. MGC ($40 k/lot) et SIL passent en marge. **Le platine n'a pas de contrat micro** (PL = 50 oz) : à €13 k il est très probablement **matériellement mort**, exactement comme ZN l'était pour le propfirm. Le panier à 4 métaux dégénère alors en MGC+SIL, dont la corrélation janvier est **0.86** — donc en pratique **un seul pari**, pas quatre.
- **Réserve** : la cellule argent seule échoue DSR×12 = 0.864 si janvier est traité comme le meilleur de 12 mois ; elle ne passe que si janvier est **pré-spécifié par le mécanisme or** (ce qu'il est — transfert de mécanisme, pas fouille).
- **Test décisif** : relever le notionnel de PL et de SIL. Si PL ne rentre pas, le vrai objet à évaluer n'est plus « précieux-Q1 » mais « or-janvier + argent-janvier, corr 0.86 » — une revendication beaucoup plus modeste, à énoncer honnêtement avant tout travail.

### ⭐ 6. `S1 VRP` (VIX − vol réalisée) sur QQQ · **t_HAC(IC) 3.59**
`IC 0.050 (h=1) → 0.075 (h=10), stable pré/post-2020 (0.039 / 0.069), N=5026, WF 4/5 · Sharpe gross 0.467 · **net futures 0.454 déjà calculé***
- **Ce qui l'a tué** : turnover 33×/an au coût **ETF** (0.10 % RT) et le gate `RESEARCH_PASS` **Sharpe > 0.7 en standalone**.
- **Pourquoi rouvrable — deux fois** : (a) le POSTMORTEM **contient déjà** la colonne futures : **0.454** ; (b) le gate qui l'a recalé a été **explicitement abandonné** par `CLAUDE.md` — l'admission se juge désormais sur `ΔSR > 0 au poids ERC`, dont le seuil à ρ=0 est **0**, pas 0.7. C'est le gate lui-même qui a laissé le livre mono.
- **Véhicule** : MNQ ≈ $40 k/lot ; la marge tient, la granularité contraint (~3× de gross).
- **Test décisif** : calculer la corrélation de la série de rendements déjà sauvegardée avec le book de référence et lire `ΔSR` au poids ERC via `Portfolio/admission/marginal.py` — pas de backtest, juste deux séries existantes.

### ⭐ 7. Gap Pattern Type A (+ Type B) · Sharpe 0.99, N = 3438 trades
`Passe délai+1 (et **s'améliore** : +0.99 → +1.11) · passe two-sided (long +0.043 / short +0.018) · passe OOS · grille 100 % positive`
- **Ce qui l'a tué** : (a) le **DSR de l'audit oxfordstrat — invalidé** (voir §3) ; (b) « Sharpe récent 0.30 < buy&hold récent 1.02 ».
- **Pourquoi rouvrable** : c'est **le seul edge bilatéral non-beta des 109** à franchir les trois gates qui comptent. Le second critère — battre un buy&hold apparié — est une **lentille de passage de challenge**, pas une lentille de sleeve ; le repo a lui-même gravé la distinction (`portfolio-sleeve-lens ≠ challenge-passing-lens`, session_3). Un sleeve à ρ≈0 n'a pas à battre le beta, il a à s'y ajouter.
- **Réserve honnête** : la décroissance est réelle (expR OOS +0.052 → +0.013). Ce dossier est un dossier de **puissance et de fin de vie**, pas un dossier de découverte.
- **Test décisif** : recalculer le DSR avec la bonne dispersion (σ ≈ 0.216 et non ~0.98) sur les Sharpes de grille **déjà stockés** — c'est une correction arithmétique sur des nombres existants, coût nul.

### ⭐ 8. Reversal 1 jour SPX · **t 3.61**, Sharpe 0.70, skew +0.71
`Les DEUX jambes positives (long-après-baisse 1.11 / short-après-hausse 0.28) · corr ~0 partout · décroît 0.76 → 0.33`
- **Ce qui l'a tué** : l'effondrement au **délai+1** (0.57 → 0.08) ⇒ artefact de close-print / rebond bid-ask **suspecté**.
- **Pourquoi rouvrable** : le suspect n'a **jamais été mis en accusation**. Les deux fiches (`personal_book/_candidates/`, `session_vol_tail`) portent la même phrase depuis juin : « question ouverte : tester open→close vs close→close » — et la re-mesure n'a jamais été faite. Le prior est le kill, mais ce n'est pas une mesure.
- **Test décisif** : mesurer le même signal en **open→close** sur ES (une jambe, données déjà en cache). Si l'edge disparaît, le dossier se ferme **définitivement** au lieu de rester ouvert au conditionnel — c'est un gain net dans les deux issues.

### ⭐ 9. Cycle d'adjudication Treasury · **jamais mesuré**
- **Ce qui l'a tué** : rien. Il a été **skippé au gate-0** — « obligations ⇒ pas FTMO-tradeable ⇒ perso-only ⇒ skip » — **sans qu'aucun chiffre ne soit produit**.
- **Pourquoi rouvrable** : c'est le même mécanisme (flux contraint et daté sur le complexe Treasury) et **la même classe d'instrument** que B1, le meilleur edge du repo, qui affiche `t 4.65` et 23/23 années positives. Le skip a été décidé par la règle « GATE-0 FTMO d'abord » — une règle qui était bonne pour économiser du travail sur un mandat FTMO, et qui est devenue une machine à jeter dès que le compte personnel est redevenu un véhicule de première classe.
- **Véhicule** : ZN/ZF/ZB (marge ~$1 100-3 800) ou micro-yield 10Y (~$320) — **tient largement**, c'est le véhicule de B1.
- **Test décisif** : le calendrier d'adjudication du Treasury est public et gratuit ; un event-study à une seule fenêtre sur ZN suffit à trancher. **C'est le seul item de la shortlist qui produirait de l'information neuve** (les huit autres re-classent des mesures existantes) — et donc le seul qui consomme du `n_tests`. À pré-enregistrer.

### Mention adjacente — Or/argent en valeur relative (Sharpe 0.77)
Sous le seuil `t ≥ 3` mais **la synthèse decorrelated_sleeves le désigne explicitement** comme « le suivi le plus valable » : edge medium-Sharpe réel, robuste au coût et au délai, tué **uniquement par le plancher −10 %**. Véhicule : MGC + SIL, deux micros — marge OK, notionnel deux jambes ~$75 k = 5.8× sur €13 k, **serré**.

---

## 3. LES FAUX MORTS

### 3.1 Tués par un DSR invalidé — audit oxfordstrat 109
Le gate DSR de `ftmo_lab.py` comparait `E[max]` directement au Sharpe **sans mise à l'échelle de la
dispersion** (σ implicite ~0.98 là où 0.216 était correct). Un « Gate 3 DSR FAIL » de cet audit **n'est
pas une information**. J'ai agrégé les 98 fiches `*_gates.csv` :

| Constat | N |
|---|---|
| Fiches auditées | 98 |
| Échouent **uniquement** le DSR | **5** — S012, S013, S035, S036, S043 |
| Passent les 4 gates | 4 — S076-S079 (Ross Hook) |
| Échouent le two-sided | 82 |
| Échouent le délai+1 | 32 |

Sur les 5, **trois ne sont pas des faux morts** après vérification des dossiers :
- **S012 / S013 (Bollinger %b)** — le **re-audit les a tués indépendamment** : ils ne battent pas un
  buy&hold apparié en exposition **et** en vol (0.97 vs 0.93 ; version low-vol 1.33 **<** BH-low-vol 1.41,
  donc le gain low-vol est mécanique), regime-alpha ≈ 0. Réversion réelle, **zéro edge sur le beta**.
- **S043 (Hook Crabel)** — passe two-sided et OOS, mais **le fill intrabar porte tout l'edge**
  (délai+1 : +0.33 → +0.03). Artefact d'exécution.

⇒ **Vrais faux morts : S035 et S036 (Gap Pattern A et B)** — les deux seuls de tout l'audit à franchir
délai+1 **et** two-sided **et** OOS. Voir shortlist n°7. Le correctif coûte une ligne d'arithmétique.

### 3.2 Tué par un échantillon tronqué par un fichier d'entrée — le cas pré-FOMC, et sa portée réelle
Le batch `top10_test` lit `Forex/data/news_events_2020_2025.csv`, qui **plafonne toutes les familles
d'événements à 2020-2025** : FOMC 49, CPI_US 72, NFP_US 72, ECB 48, BOE 50, BOJ 48. Le cache
`fomc_events.csv` en contenait **182 (2004-2026)**. La troncature était accidentelle et n'avait jamais
été vérifiée.

**Mais l'issue est instructive et va contre l'intuition** : la ré-ouverture du 29/07 sur 97 événements
a fait **baisser** le t (2.41 → 2.12, quand la stabilité prédisait 3.39) et a révélé un **effet de
régime post-2020** (GER40 pré-2020 : t 0.01). La troncature ne cachait pas de la puissance : elle
cachait un **régime**.

⇒ **Portée pour le reste du batch** : 92 des 142 lignes (`ed_` 48, `me_` 8, `per_` 36) tournent sur la
même fenêtre 2020-2025 = COVID + QE illimité + hausses de 75 bps. Ce n'est **pas** un réservoir de
faux morts à récupérer ; c'est un **avertissement de régime sur toute la famille**. Aucune de ces
lignes ne dépasse `t 2.41` de toute façon (max du batch), et **aucune** n'atteint le seuil de shortlist.

### 3.3 Le troisième mode, non demandé mais présent : tués par un gate depuis abandonné
Deux entrées fortes ont été recalées par des règles que `CLAUDE.md` a **elle-même retirées** :
- **E014 (VRP QQQ)** — recalé par `RESEARCH_PASS: Sharpe > 0.7 en standalone`. L'admission se juge
  désormais sur `ΔSR > 0 au poids ERC` (seuil **0** à ρ=0). Le net futures **0.454 est déjà calculé**.
- **E012/E013 (Gap Pattern)** — recalés par « ne bat plus le buy&hold récent », une lentille de
  challenge appliquée à un candidat-sleeve.

C'est le même mécanisme qui a produit le livre mono : **un hurdle qui exige d'un diversifieur qu'il
soit un amplificateur de rendement**.

### 3.4 Ce qui n'est **pas** un faux mort, malgré les apparences
- Le `_SS` du batch top10 (`side = -side_long`) n'est **pas** un test two-sided — c'est l'inverse
  mécanique exact. **L25 n'a jamais été appliqué à la famille `event_drift`.** Mais aucune ligne
  n'atteignant `t 2.5`, cela ne crée pas de candidat : cela crée une **dette de méthode**.
- `R004` unlock (t 2.90, DSR 0.94, non décayé) : franchit tous les gates statistiques et se retrouve
  quand même **sous la médiane d'un placebo apparié**. Kill mécanique, correctement établi.
- `M010` sector_hothand (t 10.38) : look-ahead dans `entry_px` + HAC lag-6 sous-spécifié pour T=6138.
  Artefact, pas edge.

---

## 4. CE QUE L'INVENTAIRE DIT DU PROCESSUS

### 4.1 Distribution des raisons de kill

**Pondéré par entrée** (118) — *une entrée peut porter deux causes ; la classe primaire est retenue* :

| Classe | N | % | Rouvrable ? |
|---|---|---|---|
| **MÉCANIQUE** | 70 | **59.3 %** | non |
| PUISSANCE | 15 | 12.7 % | oui |
| COÛT | 9 | 7.6 % | oui |
| GÉOMÉTRIE | 8 | 6.8 % | oui |
| DONNÉES | 8 | 6.8 % | si la donnée arrive |
| VÉHICULE | 7 | 5.9 % | oui |
| **Total rouvrable** | **39** | **33.0 %** | |

**Pondéré par stratégie** (213, cohortes oxfordstrat et session dépliées) — *la mesure honnête, parce
que « la famille ORB-stop » compte 8 stratégies et « la famille trend » ~40* :

| Classe | N | % |
|---|---|---|
| **MÉCANIQUE** | 162 | **76.1 %** |
| PUISSANCE | 15 | 7.0 % |
| DONNÉES | 11 | 5.2 % |
| COÛT | 9 | 4.2 % |
| GÉOMÉTRIE | 8 | 3.8 % |
| VÉHICULE | 7 | 3.3 % |
| **Total rouvrable** | **50** | **23.5 %** |

Détail des causes mécaniques (ce qui tue réellement) : **two-sided / beta déguisé** ≈ 82 fiches
oxfordstrat + les pistes A/C + CS macro ; **artefact de fill (délai+1)** ≈ 32 fiches + gap-fade +
Friday momentum ; **gross ≈ 0** (Gao, H2 FX, credit momentum, TOM) ; **régime / décroissance**
(pré-FOMC, RSI2, carry G10, COT) ; **sous placebo** (unlock) ; **artefact de mesure** (sector_hothand,
short-vol clip, oops #60, lev-ETF look-ahead attrapé).

### 4.2 Interprétation

**La recherche est saine. Le tri est le bon. Le problème n'est pas là.**

À 76 % de kills mécaniques, le processus fait exactement ce qu'on lui demande : il tue des signaux
qui n'existent pas, et il les tue avec les bons outils — le test two-sided et le délai+1 font à eux
seuls ~70 % du travail. On ne trouvera pas de gisement caché en recalibrant des statistiques : on ne
ressuscite pas un gross de 0.00 bps. **La conclusion de sprint du 30/07 (« trois fermetures
mécaniques ⇒ le cadre ne rejetait pas des edges valables en masse ») est confirmée à l'échelle du
repo entier.**

**Mais il y a un gaspillage, et il est concentré, systématique et diagnosticable.**

Les **23.5 % de kills rouvrables** ne sont pas répartis au hasard dans la distribution de force
statistique — **ils sont concentrés au sommet**. C'est le résultat le plus important de cet
inventaire :

| Tranche (t de stratégie, artefacts exclus) | Entrées | dont kill rouvrable |
|---|---|---|
| **`t ≥ 3.0`** | **15** | **10 (67 %)** |
| `2.0 ≤ t < 3.0` | 13 | 4 (31 %) |
| `t < 2.0` + cohortes | 90 | ~25 (~28 %, dont 8 DONNÉES) |

Le détail de la tranche haute, nommément :

| `t ≥ 3` | rouvrable | non rouvrable |
|---|---|---|
| | E002 (4.82) · E001 (4.79, résolu) · E005 (4.60 α) · E003 (4.55) · E007 (3.74) · E006 (3.72) · E004 (3.64) · E016 (3.61) · E014 (3.59) · E008 (3.22) | M047 (4.70 gross, déjà re-testé futures : SR 0.35-0.47) · M033 (4.04, dérive overnight = beta, re-testé futures) · M043 (5.12, variante de TSMOM) · R015 (3.55, tier institutionnel) · M001 (3.18, jambe longue seule) |

*(M010 sector_hothand `t 10.38` est exclu : c'est un artefact de look-ahead, pas une mesure.)*

**Plus un edge est statistiquement fort, plus la probabilité qu'il ait été tué par autre chose que son
signal est grande.** Une partie est mécaniquement attendue — un signal faible meurt de sa faiblesse
avant d'atteindre le gate du véhicule — mais l'ampleur ne l'est pas : **10 des 15 edges à `t ≥ 3` du
repo sont morts d'un véhicule, d'un coût CFD, d'une horloge ou d'un gate depuis abandonné**, et les
cinq autres ont été correctement tués (dont trois par un re-test explicite sur véhicule futures — la
preuve que le processus *sait* faire ce contrôle quand il le fait).

Trois défauts de processus, nommément :

1. **Le véhicule passait en dernier.** Le repo l'a déjà gravé (L53 : « la matrice de véhicule passe
   AVANT le backtest »). Mais le coût de l'ordre inverse n'est pas seulement du travail perdu — il est
   **asymétrique** : quand le véhicule est vérifié en premier, il fait *skipper* (E020 Treasury, jamais
   mesuré, zéro information produite) ; quand il est vérifié en dernier, il fait *jeter* une étude
   complète (E002 or overnight, entièrement auditée puis classée non-viable). Les deux ordres
   produisent une perte ; seule la **matrice de véhicule multi-comptes** — « où cet edge est-il
   tradable ? », et non « est-il tradable chez FTMO ? » — les évite.

2. **Un mandat unique a servi de critère universel.** Presque tout l'arc 2026-06 a été jugé sous
   `FTMO + skew+ + barrière −10 % + horloge 91 j`. Des edges réels y ont été classés morts pour
   *mauvais profil* (E015 VIX-term : « bon edge, mauvais profil »), pour *sparsité* (précieux-Q1), pour
   *gate-0 instrument* (E017 VIX SOQ, E019 long-vol, E020 Treasury). Le vocabulaire employé était
   pourtant correct — les rapports écrivent « perso-only », « hors-challenge », « sleeve de
   portefeuille » — mais **il n'existait aucun registre qui relise ces verdicts quand le mandat change.**
   Cet inventaire est ce registre manquant.

3. **Un gate d'admission mal spécifié a fabriqué le livre mono.** Le hurdle `1.10 × SR_book` exigeait
   d'un diversifieur qu'il amplifie le rendement ; `RESEARCH_PASS Sharpe > 0.7` exigeait d'un sleeve
   qu'il soit un livre. Les deux ont été retirés — mais **les verdicts qu'ils ont produits n'ont jamais
   été rejoués.** E014 (net futures 0.454, déjà calculé, jamais admis) en est la preuve directe.

**Le taux de découverte n'est pas le goulot.** Le repo a découvert au moins neuf edges forts en deux
ans — c'est un bon rendement pour un chercheur solo sur données gratuites. Le goulot est **la
conversion** : de neuf edges forts, **un seul** est aujourd'hui déployé, et il ne l'est que parce que
quelqu'un a rouvert son dossier de véhicule ce matin. Le levier n'est pas de chercher plus ; il est de
**faire passer la matrice de véhicule sur les huit autres**.

---

## 5. Complétude — ce que je n'ai PAS pu inventorier, et pourquoi

À dire franchement, cet inventaire est **exhaustif sur les sources machine-lisibles et sur les
rapports de synthèse ; incomplet sur trois fronts** :

1. **Les artefacts vivant sur d'autres branches.** `INVENTORY.csv` cite 8 entrées (`R009` VRP réel,
   `M053`/`M054`/`M055`/`M056`/`M057`/`M058`/`M059` growth-engine, `M061` prop-suitable) dont les
   dossiers ne sont pas sur `claude/inference-layer-fix`. Je les ai lus via `git show b79b2c9a` et via
   les mémoires de projet — **je n'ai donc pas vérifié leurs CSV de résultats**, seulement leurs
   registres. Idem `data/ftmo_portfolio/asia_23_8_feasibility/` (branche
   `claude/asia-23-8-ftmo-feasibility`) : les chiffres d'`E002` viennent de la due-diligence in-branch
   et de la mémoire, pas de l'étude de faisabilité elle-même.
2. **Les cohortes de masse ne sont pas dépliées ligne à ligne.** Les 142 lignes de `summary_batch_142`,
   les 92 lignes d'`ic_summary`, les 90 de `cs_carry`, les 96/84/56 des grilles decorrelated et les
   ~40 fiches trend d'oxfordstrat figurent comme **entrées de cohorte** avec leur meilleure cellule et
   leur cause commune. J'ai vérifié qu'aucune cellule individuelle de ces cohortes n'atteint le seuil
   de shortlist (max du batch 142 : `t 2.41`), donc rien n'est perdu pour le classement — mais le CSV
   ne les recense pas une par une. Les fichiers sources sont cités et directement triables.
3. **Ce qui n'a jamais été écrit.** Les arcs `L40/L41` (top10-rigorous) n'ont **aucun rapport dans le
   repo** — la constitution le dit elle-même (« originating report not in repo, session memory only »).
   Les mesures de cet arc sont hors d'atteinte d'une fouille du repo.

**Questions ouvertes que j'ai refusé de trancher en relançant du code** (chacune aurait été un
« juste vérifier un chiffre ») :
- Le notionnel et l'aller-retour réels de **MGC / SIL / MCL / MZS / PL** — je les ai marqués
  « non relevés cette session » dans la colonne véhicule plutôt que de les estimer. La seule ancre
  mesurée in-repo est MES $38 k / MGC $40 k / M2K-MCL-M6E $8-14 k.
- Le **DSR corrigé** de S035/S036 avec σ = 0.216 : les Sharpes de grille sont stockés, le recalcul est
  trivial — je ne l'ai pas fait parce qu'il produit un nombre neuf.
- La **corrélation d'E014 (VRP QQQ) au book de référence** et son `ΔSR` au poids ERC : les deux séries
  existent, `Portfolio/admission/marginal.py` existe. Non lancé.
- Le **nombre d'événements CPI/NFP disponibles au-delà de 2020** : aucun cache long n'existe en repo
  (seul FOMC en a un, 182 événements). Les dates de publication du BLS sont gratuites, mais les
  récupérer est une acquisition de données, pas une lecture.

---

## 6. Fichiers

```
INVENTORY.md          ce document
INVENTORY.csv         118 entrées x 16 colonnes (dont futures_vehicle_fits_13k)
build_inventory.py    concatène les .psv -> CSV (I/O pur, aucun accès donnée)
rows_01_strong.psv    20 entrées — edges forts / rouvrables
rows_02_mecanique.psv 50 entrées — kills mécaniques et cohortes
rows_03_reste.psv     48 entrées — crypto, FX, personal book, data-blocked, jamais testés
```
