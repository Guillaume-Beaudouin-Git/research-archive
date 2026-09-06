# Axe H — Offre de titres (adjudications, refinancement, QT, primary dealers)

> **Round 3, axe H.** Mandat : construire la version **la plus forte** de l'axe « le Trésor DOIT
> émettre, à dates connues, en quantités pré-annoncées ; les dealers DOIVENT absorber ». Ce
> document ne rend **pas de verdict** — il fait l'état de l'art, spécifie la meilleure
> construction testable, et nomme ce qui la falsifierait. Aucune donnée téléchargée, aucun
> backtest exécuté. Δn_tests = 0 (aucun chiffre de rendement neuf n'est produit ici).

---

## 0. Balayage du dépôt — ce qui existe déjà (obligatoire avant toute recherche web)

Commande exécutée : `grep -ril "auction\|adjudication\|treasury\|refunding\|dealer\|QT" --include='*.md' . | grep -v '\.git'`. Résultat pertinent (30 fichiers touchés au total, dont beaucoup par le seul mot « treasury » dans des chemins de données FX/deep_history) — les dossiers qui comptent réellement pour cet axe :

**Un dossier COMPLET existe déjà et a été MESURÉ : `Multi_Asset/research/active/treasury_auction_2026-07/`.**
Pré-enregistrement (`PREREGISTRATION.md`, gelé 2026-07-30) + résultats (`RESULTS.md`, mesuré le
même jour) testent exactement le mécanisme Lou-Yan-Zhang (concession d'adjudication, pression de
bilan dealer) sur ZN/ZB/ZF en daily, 2000-2026. **Verdict : REJECTED — COST-DEAD & UNDERPOWERED.**
Détail au §2 ci-dessous — c'est le point de départ obligatoire de tout ce document, pas une
curiosité annexe.

**`_meta/lessons_registry.md` — L58 (texte gravé dans `CLAUDE.md`, pas dupliqué dans le fichier
registre lui-même, qui s'arrête à L67 sans reprendre L51-L60 en toutes lettres ; le texte complet
de L58 vit dans `CLAUDE.md` §Registre L, cité en tête de mandat) :**

> « Un placebo apparié peut FABRIQUER un PASS : valider sa baseline contre l'espérance
> INCONDITIONNELLE. » — le blackout ±3 jours autour des adjudications retire 38 % des jours
> centrés mi-mois, poussant le pool placebo vers un creux de saisonnalité jour-du-mois
> (jours 16-20 : −10,79 bps, t −3,38) propre à ZN, non lié aux adjudications. Contrôle
> obligatoire, coût nul : **la moyenne du pool placebo doit égaler l'espérance inconditionnelle
> de la forme de trade testée**, sinon c'est le placebo qui est biaisé.

Ce piège est intégré **dès la conception** de la spécification proposée au §7 — pas ajouté après
coup.

**Autres dossiers pertinents trouvés et lus :**

| Dossier | Ce qu'il apporte à l'axe H |
|---|---|
| `Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.md` (item **E020**) | Le cycle d'adjudication avait été **skippé au gate-0 FTMO sans être mesuré** (« les obligations ne sont pas FTMO »), classé kill **VÉHICULE**. Le dossier `treasury_auction_2026-07` (postérieur) l'a depuis mesuré sur compte personnel et corrige le classement en **MÉCANIQUE/COÛT**, pas véhicule. |
| `Multi_Asset/research/active/month_end_vehicle_2026-07/` (**B1**, la « sœur de famille » citée par E020) | Le rebalancement mensuel obligataire month-end sur ZN/IBKR — **le meilleur edge du repo** (Sharpe net 0,92, +17,6 %/an, marge ~$1 800 sur $13k). C'est le book de référence contre lequel toute nouvelle sleeve « offre de titres » doit être admise en marginal (`Portfolio/admission/marginal.py`). C'est aussi la source des leçons L51-L55 (session CME, champs yfinance, granularité) réutilisées telles quelles dans `treasury_auction_2026-07` et ici. |
| `Multi_Asset/research/active/macro_round2_2026-09/C_dispersion_flux/RAPPORT.md` (axe C du round précédent, §4.4) | Revue de littérature indépendante (NY Fed staff report, ECB WP2208 Sigaux, Somogyi/FRBSF) confirmant la **décroissance de l'effet de concession** dans le temps, et surtout : **nomme explicitement l'angle non testé** — utiliser l'**annonce de taille** (QRA, quantité connue plusieurs semaines à l'avance) comme conditionneur de la position, plutôt qu'un simple filtre de date. C'est exactement l'axe 2 de ce document, et il n'a **jamais été mesuré** dans le dépôt. |
| `Multi_Asset/research/active/macro_round2_2026-09/B_anticipations/` (axe B3, priorisé au classement round 2) | Famille voisine mais **distincte** : drift **post-annonce sur les taux** (repricing d'anticipations de politique monétaire, Brooks-Katz-Lustig / Neuhierl-Weber), pas une pression de bilan dealer. Partage le véhicule (ZN) et une partie du calendrier (FOMC ≠ adjudications), mais le mécanisme est orthogonal — ne pas confondre les deux familles dans une même cellule de test. |
| `Multi_Asset/research/active/macro_context_2026-09/RAPPORT_MACRO_CONTEXTE.md` | Chronologie QT confirmée en repo : WALCL −9,8 %/an en 2023 (QT2 rapide), repassé YoY **positif** vers T1 2026 (**QT terminé de facto**, +1,9 % YoY août 2026). Utile pour caler tout découpage de régime QT sur cet axe. |
| `Futures/research/active/zn_baltussen/` | Famille **sans rapport** (momentum intraday ZN 09:30→15:00, Baltussen et al. 2021) — partage seulement le véhicule ZN, mécanisme différent (pas d'offre de titres). Écarté de ce document. |

**Conclusion du balayage : l'axe n'est pas vierge.** Une instanciation précise (concession
d'adjudication, daily, 10y/ZN) a déjà été testée et rejetée sur le coût et la puissance, pas sur
le mécanisme lui-même (la jambe de concession vaut +1,52 bps, t 0,48 — nulle, pas négative). Trois
instanciations restent **non mesurées** : la surprise de quantité au refinancement trimestriel, le
QT (effet de stock vs effet de flux), et les positions des primary dealers. C'est sur ces trois-là
que ce document doit apporter le plus de valeur neuve, en s'appuyant sur ce que le dossier existant
a déjà appris sur le coût et le placebo.

---

## 1. Le mécanisme générique et pourquoi il reste le candidat le plus pur

Le motif est le même dans les quatre sous-familles : un **acteur contraint** (le Trésor doit
émettre pour financer le déficit ; les primary dealers sont contractuellement tenus de
soumissionner à chaque adjudication — obligation réglementaire, pas choix ; la Fed exécute un
calendrier de runoff mécanique et pré-annoncé) agit à une **date connue à l'avance** (calendrier
d'adjudication ~1 semaine, calendrier de refinancement trimestriel publié le 1er mercredi de
février/mai/août/novembre, plafonds de QT annoncés en FOMC) sur une **dose observable** (montant
en dollars, publié). C'est structurellement la même famille que B1 (rebalancement mensuel des
fonds obligataires), qui est aujourd'hui le meilleur edge vivant du dépôt — et c'est précisément
pour cela que l'axe mérite d'être creusé au-delà de la seule instanciation déjà testée.

---

## 2. Volet 1 — La concession d'adjudication (ce qui a DÉJÀ été mesuré)

### 2.1 Le mécanisme et sa source

**Lou, Yan & Zhang (2013), *Review of Financial Studies* 26(8), « Anticipated and Repeated Shocks
in Liquid Markets ».** Les primary dealers, contraints d'absorber le papier neuf à chaque
adjudication sur un bilan à capacité limitée, se couvrent en shortant les substituts proches
**avant** l'émission — la prix baisse (« concession ») — puis la pression se dissipe une fois le
papier distribué et le prix récupère. Résultat cité de l'article : une stratégie long 2y / short
duration-matched 0,5y+10y dans les 10 jours précédant chaque adjudication, renversée dans les 10
jours suivants, rend un **Sharpe de 1,44 avant coûts, 0,90 après coûts**. L'écart de rendement
mesuré entre le titre nouvellement adjugé et un titre ancien de maturité proche (« on-the-run vs
off-the-run ») est de l'ordre de **2 à 4 points de base**.
[Discussion Collin-Dufresne (Treasury conference 2011)](https://home.treasury.gov/system/files/276/2011-session-2-yan-shocks-in-liquid-market-DISCUSSION-collin-dufresne.pdf)

### 2.2 La littérature confirme un effet réel mais qui DÉCROÎT

- **Fleming (NY Fed), « Intraday Pricing and Liquidity Effects of U.S. Treasury Auctions »**
  ([lien](https://www.phd-finance.uzh.ch/dam/jcr:ecc38075-0640-42d8-9ece-96ec2cb790f6/FS_spring18_paper_Fleming.pdf)) —
  documente la forme en V inversé intraday (concession pré-adjudication, reprise post-résultat)
  au tick, sur données de transactions réelles.
- **Sigaux (ECB WP 2208), « Trading ahead of Treasury auctions »**
  ([lien](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2208.en.pdf)) — établit que le
  front-running informé (hedge funds, spéculateurs anticipant le résultat) capture une partie
  croissante de la concession, ce qui la comprime dans le temps : plus le marché apprend à
  anticiper le schéma, plus l'effet résiduel disponible pour un suiveur tardif est petit.
- **Somogyi (FRBSF), « Treasury Auctions and Long-Term Bond Yields »**
  ([lien](https://www.frbsf.org/wp-content/uploads/Somogyi-paper.pdf)) — étend l'effet au segment
  long terme.
- **Synthèse indépendante déjà écrite dans le dépôt** (`macro_round2_2026-09/C_dispersion_flux`,
  §4.4, citant NY Fed staff report + les deux papiers ci-dessus) : « magnitude en baisse — les
  fonds d'investissement non-dealers absorbent de plus en plus l'offre, réduisant le pouvoir
  explicatif des contraintes de bilan des dealers historiquement citées comme mécanisme ».

**Le fil narratif est cohérent d'un bout à l'autre : mécanisme réel et documenté dans les années
2000-2010 (2-4 bps sur écart on/off-the-run, Sharpe institutionnel 0,9-1,4 en levier professionnel)
→ de plus en plus arbitragé par le front-running et par l'entrée de nouveaux absorbeurs non-dealers
→ résiduel daily, au tarif futures retail, indistinguable de zéro.**

### 2.3 Ce que la mesure du dépôt ajoute — et confirme cette lecture

`treasury_auction_2026-07/RESULTS.md` a testé le mécanisme sur ZN 10y, daily, 2000-2026, n=251
événements, **après avoir tranché en premier le piège de redondance avec B1** (recouvrement
0,0 %, ρ −0,001 — le cluster 10y est structurellement disjoint du calendrier month-end, donc c'est
un test authentiquement neuf, pas B1 déguisé) :

| | mean bps/événement | t_HAC | IC95 |
|---|---:|---:|---|
| `S_V` (short pré-adjudication + long post) | **+7,72** | **1,75** | [−1,63 ; +17,00] |
| jambe PRE seule (la concession, le mécanisme) | **+1,52** | **0,48** | [−4,51 ; +7,40] |
| jambe POST seule (la reprise) | +6,20 | 1,37 | [−1,86 ; +14,24] |

**Le point qui décide** : la jambe qui porte le mécanisme (la concession elle-même) est **nulle**
en daily (t 0,48), exactement ce que prédit la littérature de décroissance ci-dessus — l'effet de
2-4 bps documenté dans les années 2000-2010 sur écart on/off-the-run (un test *relatif*, deux
jambes du marché au comptant, arbitrable en interne par un market maker) ne survit pas transposé en
*directionnel absolu* sur futures daily retail. Coût du round-trip (S_V) ≈ 3,3 bps central / 6,1
bps stress ; gate à 3× = 9,8 bps ; brut mesuré 7,72 bps → **K4 coût déclenché**. DSR à `n_trials=16`
= 0,863 (< 0,95) → **K9 déclenché**. ΔSR marginal contre B1 sur ZN = −0,072 brut / −0,162 net
(poids ERC) → **K8 déclenché**. Verdict : **REJECTED — COST-DEAD & UNDERPOWERED**, pas
mécaniquement mort (le signe est conforme à la théorie, l'effet primaire brut n'est pas
significativement négatif) — **rouvrable sur la puissance**, uniquement avec de la donnée intraday
longue (§2.4), pas en re-testant la même construction daily.

### 2.4 La piste résiduelle documentée mais non actionnable

Le dossier a mesuré, hors ledger (exploratoire, N=18 événements, 2024-07→2025-12, aucune
puissance) : concession −2,62 bps (08:00→13:00 ET), reprise +1,89 puis +3,61 bps post-résultat. La
concession existe bien **à l'intérieur de la barre daily**, mais (a) N=18 ne permet aucune
conclusion, (b) une spécification intraday serait une **nouvelle** hypothèse à pré-enregistrer et
à payer en `n_tests`, (c) le repo n'a que ~2 ans de barres horaires ZN gratuites — sans historique
intraday sur ≥15 ans, la puissance statistique reste nulle par construction, et même dans le
meilleur cas (~8 bps intraday brut contre un gate ~5 bps) la marge serait mince. **Classé, non
rouvrable sans données intraday longues et payantes** — hors du périmètre gratuit de ce dépôt.

---

## 3. Volet 2 — L'annonce de refinancement trimestriel (Quarterly Refunding Announcement)

### 3.1 Mécanique institutionnelle

Le Trésor tient une consultation formelle multi-jours avec le **Treasury Borrowing Advisory
Committee** (TBAC, praticiens de marché) quatre fois par an, suivie d'une annonce publique — la
**Quarterly Refunding Statement** — habituellement le **premier mercredi de février, mai, août et
novembre**
([fiscaldata.treasury.gov, Treasury Securities Buybacks dataset](https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/)).
Le contenu de l'annonce : les tailles d'adjudication prévues pour le trimestre à venir, par
maturité (2y à 30y), et depuis 2023 le calendrier des opérations de rachat (buybacks). C'est
l'événement macro-obligataire le plus régulièrement surveillé par le marché des taux US, avec les
minutes FOMC.

**Preuve empirique récente que la surprise de quantité déplace le marché — pas une étude
académique, mais un cas observé en temps réel dans le dépôt du repo lui-même (WebSearch,
2026-08-24)** : le Trésor a annoncé le 19 août 2026 un doublement du montant des rachats
obligataires long terme (de 2 à 4 milliards $/opération, entre le 9 septembre et le 4 novembre),
**deux semaines après** l'annonce de refinancement trimestriel normale — un cas archétypal de
« surprise hors calendrier attendu ».
([CFR, « What the Treasury's Buyback Surprise Says About the Bond Market »](https://www.cfr.org/articles/what-the-treasurys-buyback-surprise-says-about-the-bond-market) ;
[Treasury, communiqué officiel](https://home.treasury.gov/news/press-releases/sb0607))

### 3.2 Ce que dit — et ne dit pas — la littérature académique

Recherche menée (WebSearch ciblée sur « refunding announcement surprise coupon size event study ») :
**aucun papier académique publié, indexé et directement identifiable, n'a été trouvé qui mesure
spécifiquement la réaction des rendements à la composante SURPRISE (taille annoncée moins taille
anticipée par le consensus TBAC/dealers) de la Quarterly Refunding Statement**, par opposition à
la littérature abondante sur (a) l'effet niveau de l'offre totale de duration sur les term premia
(Greenwood-Vayanos, *Bond Supply and Excess Bond Returns*, canon du champ) et (b) l'effet des
adjudications individuelles (§2). C'est un **vide de littérature identifiable avec les moyens
gratuits de cette recherche**, pas une preuve d'absence d'effet — à traiter comme tel : ni un
« papier propre existe donc c'est arbitré » (comme pour les adjudications individuelles), ni un
« rien n'a jamais été regardé donc l'edge est vierge ». C'est exactement pourquoi
`macro_round2_2026-09/C_dispersion_flux` §4.4 qualifie cet angle de **non encore testé** plutôt que
de fermé.

### 3.3 Pourquoi c'est probablement l'angle le plus propre de l'axe

Trois raisons, cohérentes avec le cadrage du mandat :
1. **Fréquence faible mais dose ÉNORME et bien identifiée** — 4 événements/an, mais chacun
   redéfinit l'offre de duration pour tout un trimestre (des dizaines de milliards de $ de
   variation, contre quelques milliards par adjudication individuelle). Le signal-à-bruit d'un
   choc de cette taille, s'il existe, devrait être bien supérieur à celui d'une concession
   individuelle de 2-4 bps.
2. **La surprise est mesurable objectivement** — le TBAC publie ses propres projections et
   recommandations avant l'annonce (documents « Presentation to TBAC »,
   [exemple](https://home.treasury.gov/system/files/221/CombinedChargesforArchivesQ42024.pdf)),
   et les économistes de sell-side publient des attentes de consensus (Econoday/Bloomberg
   consensus sur la QRA existe,
   [CME Group listing](https://www.cmegroup.com/education/events/econoday/652648)). Un
   `surprise = annoncé − consensus` est construisible sans donnée payante lourde (à confirmer par
   collecte manuelle des communiqués historiques — voir §6, limite de profondeur).
3. **C'est exactement l'angle que le dépôt a lui-même identifié comme non testé** (§0, ligne
   `macro_round2/C`) — ne pas re-tester la concession individuelle sous une forme légèrement
   différente serait payer du `n_tests` pour re-découvrir le même mur de coût ; conditionner sur
   la surprise de *taille annoncée trimestrielle* est un mécanisme réellement distinct (choc de
   niveau d'offre, pas pression de bilan dealer sur 5 jours).

### 3.4 Le risque à nommer honnêtement

L'échantillon reste petit à l'échelle de n_tests : ~4 événements/an, et une histoire
« annoncé vs consensus documenté » n'existe proprement que depuis que le TBAC publie ses charges
de façon systématique (dernière décennie environ) — donc peut-être 30-40 événements exploitables
avant tout split de régime. C'est un ordre de grandeur **comparable à l'annonce FOMC (~8/an)**, pas
au calendrier d'adjudication individuel (~250/an pour le 10y seul). La MDE sera large — l'attente
réaliste est **UNDERPOWERED** plus probable que **PASS**, à déclarer d'emblée, pas à découvrir après
coup.

---

## 4. Volet 3 — Le resserrement quantitatif (QT) : effet de stock vs effet de flux

### 4.1 Cadre théorique — le canal établi pour la QE, inversé pour la QT

**D'Amico & King (2013), *Journal of Financial Economics*, « Flow and Stock Effects of Large-Scale
Treasury Purchases: Evidence on the Importance of Local Supply »** — établit la distinction
canonique : un **effet de stock** (la quantité totale détenue par la Fed / disponible pour le
marché change les prix via la rareté et la préférence d'habitat) et un **effet de flux**
(l'acte même d'achat/vente, temporaire, lié à l'exécution). L'étude trouve un effet de stock
dominant et fortement **local** (concentré sur les maturités effectivement achetées et leurs
substituts proches — faible substituabilité inter-maturités). Trois canaux de transmission
identifiés dans la littérature qui en découle : rareté/portefeuille (l'offre disponible de l'actif
ciblé), duration-risk (la prime de terme via le risque de duration agrégé porté par le marché), et
signal (l'achat/vente révèle une information sur la trajectoire de politique monétaire).

### 4.2 Preuve empirique sur la QT elle-même — plus petite, plus récente, encore débattue

- **D'Amico & Seida, « Unexpected Supply Effects of Quantitative Easing and Tightening »**
  (Atlanta Fed Financial Markets Conference 2022 ; papier retrouvé cité, contenu détaillé non
  accessible via le lien direct — 404 rencontré lors de la vérification, à recouper avant citation
  ferme). Titre et positionnement confirment l'existence d'un travail dédié à la composante
  **surprise** (annoncée vs attendue) de la QE/QT — c'est le même schéma méthodologique que celui
  proposé au §3 pour le refinancement trimestriel, appliqué cette fois aux plafonds de runoff.
- **Littérature d'event-study sur QT2 (2022-2023)** : effets d'annonce substantiels sur les
  rendements du Trésor autour des dates d'annonce de bilan pendant QT2, **largement absents
  pendant QT1** (2017-2019) — cohérent avec un régime où le marché a appris à mieux anticiper QT1
  et réagit davantage à QT2 parce que le contexte macro (inflation, vitesse de resserrement) était
  inédit. Effets plus prononcés sur les indices actions et les contrats à terme de taux longue
  échéance que sur les rendements du Trésor eux-mêmes selon Ludvigson (2023).
- Cadre général confirmé : « QT fonctionne dans la direction opposée à la QE, mais avec des effets
  beaucoup plus petits » — cohérent avec l'asymétrie bien documentée par ailleurs dans la
  littérature de politique monétaire (les effets d'annonce sont typiquement plus forts à
  l'assouplissement qu'au resserrement, phénomène analogue à l'asymétrie VIX up/down).

### 4.3 Le point opérationnel qui compte pour ce dépôt

**Les plafonds de QT sont mécaniques et pré-annoncés** (le montant maximal de runoff mensuel est
fixé en FOMC et communiqué à l'avance ; le runoff réel suit les maturités du portefeuille, connues
à l'avance également puisque publiées par la Fed — SOMA holdings détaillées par CUSIP). Cela en
fait, en théorie, l'instanciation la plus proche du motif « dose connue, calendrier connu » — mais
à une fréquence d'ajustement **basse** (les plafonds changent lors des réunions FOMC, ~8/an, et
restent souvent inchangés sur plusieurs trimestres consécutifs). Le contexte repo confirme que le
régime a déjà changé deux fois en quatre ans (`macro_context_2026-09` : QT rapide 2022-2023 → QT
« lite » avec ralentissement du rythme 2024 → fin de facto du QT, WALCL YoY repassé positif ~T1
2026) — un split de régime (L31) est **obligatoire** avant toute mesure, exactement comme dans
`treasury_auction_2026-07` §5/§7.

**Distinction stock/flux à trancher empiriquement, pas supposer** : si c'est l'effet de **stock**
qui domine (la variation du niveau WALCL/SOMA), le signal actionnable est un score de niveau lent
(mise à jour hebdomadaire FRED, horizon de plusieurs semaines) — proche d'un conditionneur de
régime, pas d'un déclencheur daté. Si c'est l'effet de **flux** (l'exécution même du runoff, datée
au jour de maturité du titre qui tombe du bilan) qui domine, le signal serait daté et court —
mais la littérature ci-dessus penche pour un effet de stock dominant sur la QE, et rien ne prouve
que la QT soit symétrique dans sa décomposition stock/flux (c'est un des points à falsifier en
premier, cf. §7.3).

---

## 5. Volet 4 — Les positions des primary dealers (NY Fed, hebdomadaire)

### 5.1 La donnée

Le NY Fed publie hebdomadairement les statistiques agrégées de positions des primary dealers
(formulaires **FR 2004A/B/C** — positions nettes, transactions cumulées, financement). Collecte
arrêtée le **mercredi** (clôture de la semaine de reporting), publication le **jeudi suivant vers
16h15 ET**
([NY Fed, Primary Dealer Statistics](https://www.newyorkfed.org/markets/primarydealers) ;
[formulaire FR 2004A/B/C](https://www.newyorkfed.org/banking/reportingforms/FR_2004A_B_C)) — soit
un **décalage d'environ 8 jours calendaires** entre l'état réel du positionnement et sa
publication (même famille de contrainte que le COT du CFTC identifié dans
`macro_round2_2026-09/C_dispersion_flux` §4.1 : jamais un déclencheur intra-semaine, seulement un
conditionneur de régime lent, ≥1-2 semaines d'horizon).

### 5.2 Ce que dit la littérature sur le pouvoir prédictif

- **Fleming, Nguyen & Rosenberg (2024), « How do Treasury dealers manage their positions? »**,
  *Journal of Financial Economics* ([SSRN](https://www.ssrn.com/abstract=1012684) ;
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X24001089)) —
  31 ans de données (1990-2020) : **l'émission du Trésor est le principal moteur des variations
  hebdomadaires d'inventaire des dealers.** C'est un résultat structurellement important pour cet
  axe : il dit que les positions dealers sont **endogènes au calendrier d'émission**, pas un signal
  indépendant qui le précéderait. Toute conditionnalité construite sur les positions dealers doit
  donc d'abord contrôler pour le calendrier d'émission lui-même (§2-3), sous peine de mesurer deux
  fois la même chose.
- **Liberty Street Economics (NY Fed), « Dealer Positioning and Expected Returns » (2015)**
  ([lien](https://libertystreeteconomics.newyorkfed.org/2015/12/dealer-positioning-and-expected-returns)) —
  corrélation de **55 %** entre l'allocation de bilan des dealers en titres à revenu fixe et les
  rendements attendus (prime à terme 10 ans + écart Baa-Aaa), 1990-2015. **Attention à
  l'interprétation** : l'article lui-même la présente comme une relation **contemporaine**
  (les positions s'ajustent en réponse aux conditions de marché), pas comme une preuve de pouvoir
  prédictif directionnel *lead* — et note une exception notable en 2012-2013 où la relation
  s'est rompue (positions élevées malgré rendements attendus comprimés), signe que la relation
  n'est **pas invariante dans le temps**, cohérent avec la nécessité d'un split de régime (L31)
  sur toute la période 1990-2025.
- **Boston Fed WP 24-7, « The Effect of Primary Dealer Constraints »**
  ([lien](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/2024/WP2407.pdf)) et
  **NY Fed Staff Report 1070, « Dealer Capacity and U.S. Treasury Market Functionality »**
  ([lien](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1070.pdf)) —
  confirment que les contraintes de capacité des dealers dégradent la liquidité (turnover en
  baisse, spreads en hausse) sans établir de pouvoir prédictif directionnel exploitable
  actionnable à horizon court.

### 5.3 Verdict de préparation, honnête

Le tableau de la littérature est clair : les positions dealers sont un **conditionneur de régime
lent** (extrêmes de positionnement = risque accru de mouvement brutal, dans l'esprit d'un
conditionneur COT), publiées avec un **retard structurel de 8 jours** qui interdit tout usage
comme déclencheur, et **corrélées avec, plutôt que prédictives de**, les rendements — sans compter
qu'elles sont elles-mêmes endogènes au calendrier d'émission déjà couvert par les volets 1-2. **Ce
volet n'apporte pas un signal indépendant nouveau** ; son rôle le plus honnête dans la meilleure
version de l'axe est un **filtre de régime** (réduire la taille aux extrêmes de positionnement
dealer, jamais un déclencheur), exactement le rôle assigné au COT ailleurs dans le dépôt.

---

## 6. Données — accès, profondeur, latence, coût (par source)

| Source | Contenu | Accès | Profondeur | Latence | Coût |
|---|---|---|---|---|---|
| **TreasuryDirect API** `TA_WS/securities/{auctioned,search}` | Calendrier + résultats d'adjudication (bid-to-cover, tail, indirect/direct bidders, `announcementDate`, `issueDate`) | REST public, JSON | 2000-01 → aujourd'hui (1 624 adjudications de coupon nominal mesurées dans le dépôt) | Temps réel (résultats publiés le jour même de l'adjudication) | Gratuit |
| **fiscaldata.treasury.gov** (Enterprise API) | Mêmes données auction + **Treasury Securities Buybacks** (calendrier de rachat, montants) | REST public, JSON/CSV/XML, **pas de compte/token requis** | Comparable à TreasuryDirect, alternative sans plafond de pagination connu (TreasuryDirect `/auctioned` plafonne à 250 lignes, piège déjà rencontré et contourné par boucle année-par-année dans `treasury_auction_2026-07`) | Idem | Gratuit |
| **Quarterly Refunding Statement** (communiqués + charges TBAC) | Montants d'adjudication prévus par maturité pour le trimestre, calendrier de rachat, présentation TBAC | `home.treasury.gov/news/press-releases/` (archive HTML, pas d'API structurée identifiée) | Archive historique disponible mais **collecte manuelle nécessaire** pour construire une série exploitable de `surprise = annoncé − consensus` — pas de dataset prêt à l'emploi trouvé | Publication J0, 1er mercredi fév/mai/août/nov | Gratuit (main-d'œuvre de collecte non-nulle) |
| **Consensus pré-annonce (Econoday/Bloomberg)** | Attentes de marché avant l'annonce, nécessaires pour construire la surprise | Accès partiel via agrégateurs (ex. listing CME Group Econoday) ; historique complet probablement **payant** au-delà d'un horizon court | Limitée en gratuit | — | Partiellement payant — **contrainte à documenter avant tout budget de mods** |
| **FRED WALCL / SOMA holdings** | Bilan Fed hebdomadaire, composition par maturité | API FRED, gratuite, déjà utilisée dans `macro_context_2026-09` | 2002 → aujourd'hui | Hebdomadaire, retard ~1 semaine | Gratuit |
| **NY Fed Primary Dealer Statistics (FR2004)** | Positions nettes agrégées par catégorie d'instrument | Page publique NY Fed, téléchargement CSV/XLS | Historique remontant aux années 1990 (utilisé par Fleming-Nguyen-Rosenberg sur 1990-2020) | **~8 jours** (arrêté mercredi, publié jeudi suivant ~16h15 ET) | Gratuit |
| **Prix ZN/ZB/ZF daily** | yfinance `=F`, déjà en cache dans `month_end_vehicle_2026-07/data/` | Déjà validé au tick dans le dépôt (L51/L52) | 2000-09 → 2026-07 | J0 (Close = settlement 15:00 ET) | Gratuit, **réutiliser le cache existant, ne pas re-fetch** |
| **ZN intraday (horaire)** | `data/raw/ZN_1h_cache.parquet` + `month_end_vehicle/data/h1_ZNF.parquet` | Déjà en cache | ~2 ans seulement (2024-03→2026-07) | — | Gratuit mais **profondeur insuffisante** pour re-ouvrir le volet intraday de §2.4 |

**Le maillon faible identifié** : la série de consensus pré-QRA n'est pas disponible gratuitement
sur un historique long. C'est le point à vérifier **avant** tout engagement de budget de
modifications sur le volet 2 (§3) — une collecte manuelle des seuls communiqués Treasury (montants
annoncés) est gratuite et suffit pour un signal de **variation trimestre-sur-trimestre** (proxy
grossier de surprise), mais un vrai `surprise = annoncé − consensus` exigerait la donnée
consensus, potentiellement payante au-delà d'un historique court.

---

## 7. Véhicule et coût

### 7.1 Le véhicule est déjà tranché ailleurs dans le dépôt — réutiliser, pas redériver

`treasury_auction_2026-07` et `month_end_vehicle_2026-07` (B1) ont déjà établi et mesuré
(L51-L53) : **ZN sur IBKR**, marge ~$1 800 (≈14 % d'un compte de €13k / ~$14 040), pas de barrière
journalière, pas d'horloge de challenge — le compte personnel domine strictement toute route
propfirm sur ce terrain (FTMO ne supporte pas les futures CME, L22 ; L53 : la marge du lot minimum
tient dans le capital personnel, le propfirm n'apporte rien).

| Poste | Central | Stress |
|---|---:|---:|
| Slippage par côté | 0,5 tick = 7,81 $ | 1,0 tick = 15,63 $ |
| Commission all-in (IBKR + frais exch./reg.) par aller-retour | 2,30 $ | 2,30 $ |
| **Coût par aller-retour** | **17,93 $ ≈ 1,63 bps** | **33,55 $ ≈ 3,05 bps** |

(1 point ZN = 1 000 $, 1 tick = 1/64 pt = 15,625 $, nominal ≈ 108-110 k$ au prix courant.)

**Granularité** : 1 contrat ZN ≈ **7,7×** le nominal d'un compte $14k — la marge n'est pas la
contrainte, le **nominal** l'est (même diagnostic que MGC dans l'inventaire d'edges du dépôt). Un
sizing Kelly fractionnaire (¼ ou ½) tombe souvent sous 1 contrat, ce qui rend un edge de faible
Sharpe **non implémentable à la taille qu'il mériterait** — un point qui a déjà tué économiquement
le volet 1 (§2.3, MaxDD −50,8 % pour +4,09 %/an au coût central, ratio rendement/drawdown 0,08).

### 7.2 Alternatives de maturité pour les volets 2-3

Si le mécanisme testé porte sur le long terme (QRA quantité 30y/10y, QT flow sur les maturités
longues détenues par la Fed), **ZB (30y)** ou un mélange ZN/ZB pondéré par duration sont les
véhicules naturels — déjà dans le cache `daily_{ZNF,ZBF,ZFF}.parquet`. Le coût par contrat ZB est
plus élevé en $ (nominal plus grand, tick plus large) mais du même ordre en bps ; à chiffrer
précisément avant tout engagement, pas à supposer identique à ZN.

### 7.3 Point de vigilance coût — spécifique à ce volet

Les volets 2 (QRA) et 3 (QT) impliquent des positions **tenues plusieurs semaines à plusieurs
mois** (pas des allers-retours de 5 jours comme la concession d'adjudication) — le coût dominant
n'est donc **pas** le slippage/commission (négligeable sur si peu d'allers-retours par an) mais le
**coût d'opportunité de marge immobilisée** et le risque de **roll de contrat** (ZN roule tous les
3 mois, exactement la fréquence du cycle de refinancement — **un chevauchement structurel entre
la fenêtre de test et les semaines de roll est à vérifier en premier**, kill-rule K7 déjà rodée
dans `treasury_auction_2026-07`). Le levier utile sur un edge à faible fréquence et faible coût de
transaction est bien plus grand que sur un edge journalier — mais seulement si le Sharpe sous-jacent
est réel, ce qui reste précisément la question ouverte de ce document.

---

## 8. La meilleure version testable de l'axe H — spécification proposée

**Principe directeur** : ne pas re-tester le volet 1 (concession, daily) — il est mesuré et
classé. Concentrer le budget de test sur les volets 2 et 3, qui sont réellement neufs, avec le
volet 4 en rôle de filtre de régime seulement (jamais de déclencheur, jamais de test indépendant
compte tenu de son endogénéité au calendrier d'émission, §5.3).

### 8.1 Hypothèse primaire proposée (H_QRA) — surprise de refinancement trimestriel

- **Mécanisme** : une augmentation surprise des tailles d'adjudication annoncées au refinancement
  trimestriel (vs anticipation de marché, ou à défaut vs la tendance des 4 trimestres précédents
  comme proxy si le consensus n'est pas disponible gratuitement — à documenter comme limite) élève
  la prime de terme et pèse sur les prix obligataires dans les semaines qui suivent l'annonce ;
  une baisse surprise fait l'inverse. Two-sided par construction (le signe suit celui de la
  surprise, pas une direction fixe).
- **Fenêtre** : `close(annonce)` → `close(annonce + k semaines)`, k à pré-enregistrer sur une
  grille raisonnable (2, 4, 8, 12 semaines) — pas choisi après avoir vu les données (L64).
- **Véhicule** : ZN et/ou ZB selon la maturité la plus affectée par la surprise (à décomposer par
  segment de courbe, pas pooler).
- **Régime** : split obligatoire pré-QE / QE-ZIRP / QT (comme `treasury_auction_2026-07` §5, L31) —
  le mécanisme est *a priori* plus fort quand le Trésor est la seule variable marginale d'offre
  (QT, déficits records) que quand la Fed achetait elle-même le papier (QE).

### 8.2 Hypothèse secondaire (H_QT) — surprise de plafond de runoff

- **Mécanisme** : un changement de plafond de QT annoncé en FOMC (accélération, ralentissement,
  arrêt) au-delà de ce qu'anticipait le marché (proxy : réaction immédiate des futures Fed funds
  ou des options sur Treasury autour de l'annonce, à défaut simple variable indicatrice de
  changement de régime) déplace les rendements dans le sens du canal de rareté/duration
  (D'Amico-King, §4.1), avec un **délai plus long** que l'adjudication individuelle (semaines à
  mois, effet de stock plutôt que de flux).
- **Fréquence intrinsèquement basse** (~8 réunions FOMC/an, et le plafond change rarement à chaque
  réunion) — à traiter avec la même honnêteté que les opérations de banque centrale du round 2
  (§4.5 de `C_dispersion_flux`) : breadth structurellement faible, ne pas espérer un edge
  fréquent, évaluer sur la croissance annualisée et non sur un Sharpe daily.

### 8.3 Rôle du volet primary dealer

**Filtre de régime uniquement** : z-score de positionnement dealer (extrêmes = réduction de
taille), jamais un déclencheur, jamais testé comme signal indépendant compte tenu de son
endogénéité au calendrier d'émission (§5.3) — même traitement que le COT dans
`macro_round2_2026-09/C_dispersion_flux` §4.1. Tout test d'overlay doit d'abord passer le test
d'orthogonalité (L38, β sur un buy-and-hold vol-targeté de ZN, R² < 30 %) avant même un test de
timing, exactement la leçon déjà tirée sur `regime_markov_sleeves_2026-07`.

### 8.4 Le contrôle de placebo — intégré dès la conception (le point central du mandat)

Pour **chaque** cellule (H_QRA, H_QT), le protocole de placebo doit répliquer très exactement le
protocole déjà validé et corrigé dans `treasury_auction_2026-07` §4 :

1. **Construire d'abord le pool placebo SANS aucune contrainte d'exclusion** (pas de blackout, pas
   de filtre de proximité à un autre événement) et vérifier que sa moyenne **égale
   l'espérance inconditionnelle de la forme de trade** appliquée à tous les jours de bourse (la
   dérive pure de ZN sur la période). Ceci est un contrôle **gratuit et obligatoire avant toute
   autre étape.**
2. **Ajouter les contraintes d'appariement une par une** (jour de semaine, position dans le
   trimestre, régime), en **rapportant à chaque étape la moyenne du pool** — exactement le tableau
   produit dans `treasury_auction_2026-07` §4 (« aucune contrainte : +0,10 → jour de semaine + dom
   ±3 sans blackout : +0,44 → avec blackout : −5,54 »). **Toute contrainte qui déplace
   significativement la moyenne du pool loin de l'inconditionnelle est suspecte et doit être
   justifiée indépendamment**, pas acceptée parce qu'elle « semble raisonnable ».
3. **Si un blackout autour d'un autre type d'événement est nécessaire** (ex. exclure les semaines
   proches d'une adjudication individuelle pour isoler l'effet QRA pur), **vérifier explicitement
   qu'il n'interagit pas avec une saisonnalité calendaire connue** (jour-du-mois, jour-du-trimestre,
   fin d'année fiscale) — c'est précisément l'interaction qui a fabriqué le faux PASS de L58.
4. Ce contrôle **ne remplace pas** le placebo calendaire apparié standard (L49) — il s'y **ajoute**,
   comme diagnostic de validation du placebo lui-même, avant d'en interpréter le résultat.

### 8.5 Kill-rules proposées (héritées et adaptées de `treasury_auction_2026-07`)

| # | Règle | Verdict si déclenchée |
|---|---|---|
| K1 | Redondance avec B1 (month-end) ou avec B3 (drift post-FOMC) — recouvrement calendaire + corrélation | REJECTED — REDUNDANT |
| K2' | **Placebo calendaire, validé par le contrôle §8.4** (pas seulement le placebo brut) | REJECTED si effet réel ≤ p95 du placebo *validé* |
| K3 | Régime (QE/QT/pré-QE), L31 | REJECTED — REGIME ARTEFACT si porté par un seul régime |
| K4 | Coût — brut ≥ 3× coût central du véhicule retenu (§7) | REJECTED — COST-DEAD sinon |
| K5 | Signe conforme au mécanisme, pas de re-spécification post-hoc | REJECTED si signe inverse |
| K6 | Two-sided (L25) sur H_QRA (les deux sens de surprise doivent produire l'effet de signe opposé) | REJECTED — BETA sinon |
| K7 | Roll de contrat ZN/ZB — chevauchement avec les fenêtres de test | REJECTED — ARTEFACT si l'effet disparaît hors roll |
| K8 | Admission marginale contre B1 (`Portfolio/admission/marginal.py`, poids ERC) | UNDERPOWERED si ΔSR dans le bruit, jamais PASS |
| K9 | DSR (n_trials à fixer au pré-enregistrement, comme les 16 cellules de `treasury_auction_2026-07`) | REJECTED — MULTIPLE TESTING si DSR < 0,95 |

### 8.6 Ce qui falsifierait l'axe entier, pas seulement une cellule

- **H_QRA** : si le contraste réel (surprise positive vs négative) ne dépasse pas le p95 du
  placebo *validé selon §8.4*, ou si le gradient dose-réponse (taille de la surprise vs magnitude
  de l'effet) est plat — même signature de falsification que L49 (unlock-drift) et que la
  dose-réponse déjà mesurée sur la taille d'adjudication dans `treasury_auction_2026-07` §7
  (corr taille↔jambe PRE = +0,056, plat) — c'est un motif qui s'est déjà répété deux fois dans ce
  dépôt et qu'il faut activement chercher, pas espérer absent.
- **H_QT** : si l'effet est porté entièrement par le sous-échantillon 2022-2023 (le seul régime de
  QT rapide avec inflation élevée disponible) sans réplication sur un régime QT plus calme —
  risque de confusion régime unique, déjà nommé comme piège méthodologique récurrent du dépôt
  (L64 : rupture choisie après avoir vu les données).
- **Les deux** : si le meilleur résultat de la grille (plusieurs k, plusieurs maturités, plusieurs
  définitions de surprise) est significatif mais que le DSR à `n_trials` déclaré tombe sous 0,95 —
  exactement le motif qui a tué le volet 1 (DSR 0,863 sur 16 cellules).

---

## 9. Synthèse — état de l'art et priorité de test, sans verdict

| Volet | Mécanisme testable | Statut dans le dépôt | Littérature | Priorité |
|---|---|---|---|---|
| 1. Concession d'adjudication | Pression de bilan dealer, daily | **MESURÉ, REJECTED cost-dead/underpowered** | Réelle mais en décroissance (Lou-Yan-Zhang → Sigaux, front-running croissant) | Ne pas re-tester sans donnée intraday longue |
| 2. Surprise QRA | Choc de niveau d'offre trimestriel | **Jamais mesuré** | Mécanisme théorique solide (Greenwood-Vayanos, D'Amico-King), littérature spécifique à la composante *surprise* du QRA non trouvée en gratuit — vide, pas verdict | **La plus prometteuse** (dose la plus grosse, angle neuf, données gratuites suffisantes pour un proxy) |
| 3. Effet QT stock/flux | Runoff mécanique, calendrier connu | **Jamais mesuré** | Cadre établi côté QE (D'Amico-King), réplication QT plus récente et plus petite (asymétrie QE/QT documentée) | Prometteur mais fréquence intrinsèquement basse |
| 4. Positions primary dealers | Signal hebdomadaire | **Jamais mesuré** ; littérature dit endogène à l'émission, lag 8j | Corrélation contemporaine documentée (55 %), pas de preuve de pouvoir prédictif *lead* indépendant | **Filtre de régime seulement**, pas un test à part entière |

**Le point central du mandat, rappelé** : ce document ne classe pas l'axe H comme vivant ou mort.
Il établit que **la seule instanciation déjà mesurée** (concession d'adjudication daily) est
rejetée sur le coût et la puissance — pas sur le mécanisme, qui est confirmé par une littérature
indépendante en déclin cohérent avec la mesure du dépôt — et que **les trois instanciations
restantes** (QRA, QT, dealers) sont non mesurées, avec un ordre de priorité clair (QRA d'abord,
QT ensuite, dealers en filtre seulement), et un protocole de placebo qui intègre dès la conception
la correction découverte par L58 : valider la baseline du pool placebo contre l'espérance
inconditionnelle de la forme de trade, avant d'interpréter tout contraste comme un signal.

---

## Sources consultées

- [Lou, Yan & Zhang — discussion Collin-Dufresne (Treasury conference 2011)](https://home.treasury.gov/system/files/276/2011-session-2-yan-shocks-in-liquid-market-DISCUSSION-collin-dufresne.pdf)
- [Discussion « Anticipated and Repeated Shocks in Liquid Markets » (EPFL, 2021)](https://www.epfl.ch/labs/sfi-pcd/wp-content/uploads/2021/07/Discussion-of-Anticipated-and-Repeated-Shocks-in-Liquid-Markets-2011.pdf)
- [Fleming (NY Fed) — Intraday Pricing and Liquidity Effects of U.S. Treasury Auctions](https://www.phd-finance.uzh.ch/dam/jcr:ecc38075-0640-42d8-9ece-96ec2cb790f6/FS_spring18_paper_Fleming.pdf)
- [Sigaux — ECB Working Paper 2208, Trading ahead of Treasury auctions](https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2208.en.pdf)
- [Somogyi (FRBSF) — Treasury Auctions and Long-Term Bond Yields](https://www.frbsf.org/wp-content/uploads/Somogyi-paper.pdf)
- [CFR — What the Treasury's Buyback Surprise Says About the Bond Market](https://www.cfr.org/articles/what-the-treasurys-buyback-surprise-says-about-the-bond-market)
- [Treasury — Announces Increased Sizes of Nominal Long-End Liquidity Support Buybacks](https://home.treasury.gov/news/press-releases/sb0607)
- [Treasury — Presentation to TBAC (exemple, charges Q4 2024)](https://home.treasury.gov/system/files/221/CombinedChargesforArchivesQ42024.pdf)
- [CME Group — US Treasury Refunding Announcement (Econoday)](https://www.cmegroup.com/education/events/econoday/652648)
- [fiscaldata.treasury.gov — Treasury Securities Buybacks dataset](https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/)
- [fiscaldata.treasury.gov — Treasury Securities Auctions Data](https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/)
- [fiscaldata.treasury.gov — API documentation](https://fiscaldata.treasury.gov/api-documentation/)
- [TreasuryDirect — Auction Announcements, Data & Results](https://www.treasurydirect.gov/auctions/announcements-data-results/)
- [D'Amico & Seida — Unexpected Supply Effects of QE and QT (Atlanta Fed FMC 2022, lien vérifié en 404 au moment de la rédaction — à revalider avant citation ferme)](https://www.atlantafed.org/-/media/documents/news/conferences/2022/05/08/financial-markets-conference/damico-seida-unexpected-supply-effects-of-quantitative-easing-and-tightening.pdf)
- [RBA — Event study of QT/QE announcement effects](https://www.rba.gov.au/publications/rdp/2022/2022-02/event-study-of-announcement-effects.html)
- [NY Fed — Primary Dealer Statistics](https://www.newyorkfed.org/markets/primarydealers)
- [NY Fed — Reporting Form FR 2004A/B/C](https://www.newyorkfed.org/banking/reportingforms/FR_2004A_B_C)
- [Fleming, Nguyen & Rosenberg — How do Treasury dealers manage their positions? (SSRN)](https://www.ssrn.com/abstract=1012684)
- [Fleming, Nguyen & Rosenberg — ScienceDirect record](https://www.sciencedirect.com/science/article/abs/pii/S0304405X24001089)
- [Liberty Street Economics (NY Fed) — Dealer Positioning and Expected Returns (2015)](https://libertystreeteconomics.newyorkfed.org/2015/12/dealer-positioning-and-expected-returns)
- [Boston Fed WP 24-7 — The Effect of Primary Dealer Constraints](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/2024/WP2407.pdf)
- [NY Fed Staff Report 1070 — Dealer Capacity and U.S. Treasury Market Functionality](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1070.pdf)

**Fichiers du dépôt cités** : `Multi_Asset/research/active/treasury_auction_2026-07/{PREREGISTRATION,RESULTS}.md`,
`Multi_Asset/research/active/month_end_vehicle_2026-07/RESULTS.md`,
`Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.md`,
`Multi_Asset/research/active/macro_round2_2026-09/{SYNTHESE_ROUND2,C_dispersion_flux/RAPPORT,B_anticipations/RAPPORT}.md`,
`Multi_Asset/research/active/macro_context_2026-09/RAPPORT_MACRO_CONTEXTE.md`,
`CLAUDE.md` (§Registre L, L58), `Portfolio/admission/marginal.py`.

*Rédigé 2026-09-07. Aucune donnée téléchargée, aucun backtest exécuté, aucun fichier modifié hors
de ce dossier. Δn_tests = 0.*
