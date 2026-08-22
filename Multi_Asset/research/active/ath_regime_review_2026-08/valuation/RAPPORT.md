# Dossier de valorisation et de santé fondamentale — GER40 (DAX 40) et US100 (Nasdaq-100)

**Date d'arrêté : 2026-08-09.** Dernière séance boursière incluse : **vendredi 2026-08-07**.
Nature du document : **descriptif**. Aucune règle de trading, aucun seuil, aucune recommandation
d'entrée ou de sortie n'est proposée ici — voir §5, qui explique pourquoi ces chiffres ne
sauraient en fonder une à l'horizon considéré.

---

## 0. ENCADRÉ — Couverture des données

> **À lire avant tout chiffre agrégé.**
>
> Les fondamentaux proviennent de `yfinance` (surface « key statistics » de Yahoo Finance),
> interrogée le **2026-08-09 entre 21:15 et 21:18 UTC**. Chaque constituant a été interrogé
> individuellement ; **0 ticker sur 142 a renvoyé un `.info` vide**. Aucune valeur manquante
> n'a été imputée : une cellule vide reste vide et est comptée ci-dessous.
>
> **Couverture champ par champ** (n disponible / n constituants, et % de la capitalisation
> de l'indice couverte) :
>
> | Champ | NDX (n=101) | % cap NDX | DAX (n=40) | % cap DAX |
> |---|---|---|---|---|
> | Capitalisation | 101/101 (100 %) | 100.0 % | 40/40 (100 %) | 100.0 % |
> | P/E trailing | **91/101 (90.1 %)** | 93.0 % | **38/40 (95.0 %)** | 97.1 % |
> | P/E forward (consensus) | 101/101 (100 %) | 100.0 % | 40/40 (100 %) | 100.0 % |
> | P/S trailing | 101/101 (100 %) | 100.0 % | 39/40 (97.5 %) | 99.6 % |
> | EV/EBITDA | 101/101 (100 %) | 100.0 % | **37/40 (92.5 %)** | 92.2 % |
> | Price/Book | 101/101 (100 %) | 100.0 % | 40/40 (100 %) | 100.0 % |
> | Marge nette | 101/101 (100 %) | 100.0 % | 40/40 (100 %) | 100.0 % |
> | Croissance CA (Yahoo, YoY trim.) | 101/101 (100 %) | 100.0 % | 39/40 (97.5 %) | 99.6 % |
> | Croissance BPA (Yahoo, YoY trim.) | **86/101 (85.1 %)** | 91.6 % | **38/40 (95.0 %)** | 97.3 % |
> | CAGR CA (états financiers, recalculé) | 101/101 (100 %) | 100.0 % | 40/40 (100 %) | 100.0 % |
> | CAGR BPA dilué (états fin., recalculé) | **77/101 (76.2 %)** | **81.5 %** | **35/40 (87.5 %)** | 88.2 % |
> | Dette nette / EBITDA | **98/101 (97.0 %)** | 99.7 % | **36/40 (90.0 %)** | 91.8 % |
>
> **Les deux champs à surveiller** sont le **P/E trailing** (90.1 % des noms du NDX) et le
> **CAGR du BPA dilué** (76.2 % des noms du NDX, **81.5 % de la capitalisation**). Le trou du
> P/E trailing n'est pas un défaut du fournisseur : Yahoo ne publie pas de P/E pour une société
> à résultat négatif. Ces 10 sociétés du NDX **existent et pèsent 7.0 % de la capitalisation** ;
> elles sont réintégrées avec leurs bénéfices négatifs dans les agrégats (voir §2, note 3).
> Le trou du CAGR du BPA concerne des sociétés sans historique annuel exploitable de BPA dilué
> positif (AMZN, INTC, PLTR, SHOP, CRWD, SPCX, MSTR, WBD…) — **tout chiffre de croissance du
> BPA du NDX ci-dessous porte donc sur 81.5 % de la capitalisation seulement et est marqué
> comme tel.**
>
> **Ce que ce dossier NE contient PAS**, faute de source vérifiable : un **historique long des
> multiples d'indice** permettant de calculer un percentile propre sur 10-20 ans (§3.4). Ce
> chiffre n'est pas inventé ; il est absent, et un point de comparaison tiers non reproductible
> est cité comme tel.
>
> Fichiers de données : `constituents_NDX.csv` (101 lignes), `constituents_DAX.csv` (40 lignes),
> `cache/coverage_NDX.csv`, `cache/coverage_DAX.csv`.

---

## 1. Périmètre, sources et millésimes

| Élément | Source | Millésime |
|---|---|---|
| Composition Nasdaq-100 | Wikipédia, `List_of_NASDAQ-100_companies`, wikitext brut | récupéré 2026-08-09 ; **102 lignes = 101 sociétés** (Alphabet coté 2× : GOOGL + GOOG) |
| Composition DAX 40 | Wikipédia, article `DAX`, wikitext brut | table datée **2025-09-22** dans la source |
| Fondamentaux par titre | yfinance 1.2.0 → Yahoo Finance | **2026-08-09, 21:15-21:18 UTC** |
| États financiers annuels | yfinance `.income_stmt` / `.balance_sheet` | dernier exercice publié par société |
| Cours et historiques indices | yfinance `^NDX`, `^GDAXI` | dernière clôture **2026-08-07** |
| Taux US 10 ans (nominal + réel TIPS) | **home.treasury.gov**, courbe des taux journalière | **2026-08-07** : 4.65 % nominal, 2.40 % réel |
| Taux 10 ans zone euro AAA | **ECB Data Portal**, `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y` | **2026-08-06** : 3.147 % |
| Taux 10 ans allemand (convergence) | **ECB Data Portal**, `IRS.M.DE.L.L40.CI.0000.EUR.N.Z` | **2026-06** (série **mensuelle**) : 2.964 % |

**Réserve sur la composition du DAX.** La table Wikipédia porte le millésime 2025-09-22. Une
recherche de contrôle indique que la revue de **mars 2026 n'a produit aucun changement** sur le
DAX 40, et qu'une modification des « DAX Blue Chip Indices » a pris effet le **22 juin 2026**
sans que le détail par indice ait pu être confirmé. **La liste des 40 utilisée ici est donc
possiblement périmée d'un ou deux titres.** Sur un indice où le top-10 fait 59.5 % de la
capitalisation, un échange en queue de classement déplacerait les agrégats de façon négligeable,
mais le point est signalé plutôt que passé sous silence.

**Réserve sur le taux Bund.** Le taux allemand 10 ans strict n'est disponible via l'ECB Data
Portal qu'en fréquence **mensuelle** (2.964 % en juin 2026). La prime de risque du DAX est donc
calculée contre le **taux 10 ans zone euro AAA quotidien (3.147 %, 2026-08-06)**, plus récent et
de même fréquence que le reste du dossier. L'écart entre les deux références (~18 pb) est
inférieur à l'incertitude sur le numérateur.

---

## 2. Niveau constituants

### 2.1 Trois choix de méthode qui déplacent les chiffres

Ces choix sont documentés ici parce qu'ils ne sont pas neutres.

**(1) Dédoublonnage des classes d'actions.** Le champ `marketCap` de Yahoo est la capitalisation
**de la société entière**, toutes classes confondues, tandis que `sharesOutstanding` est le
compte de la **classe cotée**. Vérification : `sharesOutstanding × prix / marketCap = 1.000`
pour **118 des 142 tickers**, et les 24 exceptions sont exactement les sociétés multi-classes
connues (GOOG/GOOGL, MRK.DE, HEN3.DE, VOW3.DE, PAH3.DE, META…). Sommer `marketCap` sur les deux
lignes d'Alphabet compterait Alphabet **deux fois, pour 8.7 tn USD**. **GOOG est donc retiré et
GOOGL conservé** comme unique ligne Alphabet — d'où 101 lignes et non 102.

**(2) Les multiples agrégés sont des rapports de sommes, pas des moyennes de rapports.**
On calcule `P/E agrégé = Σ capitalisations / Σ bénéfices`, et non `Σ wᵢ × (P/E)ᵢ`. La seconde
formule est une moyenne arithmétique de ratios : elle explose dès qu'un constituant a un
dénominateur proche de zéro et ne décrit aucun portefeuille. Écart mesuré sur le NDX : le P/E
trailing agrégé vaut **34.9**, la moyenne arithmétique pondérée par la capitalisation vaut
**52.2**. Le second chiffre n'a pas de sens économique.

**(3) Les bénéfices sont reconstruits pour porter les sociétés déficitaires.**
`Eᵢ = (BPA_trailingᵢ / prixᵢ) × marketCapᵢ`, et non `marketCapᵢ / P/Eᵢ`. Les deux sont
identiques quand le P/E est positif, mais le P/E est **NaN** pour une société en perte : la
formule naïve **supprime silencieusement les bénéfices négatifs** et flatte le rendement des
bénéfices de l'indice. Concerné : **10 sociétés du NDX pesant 7.0 % de la capitalisation**
(dont SPCX, seul, 4.17 %) et **2 du DAX pesant 2.9 %** (Bayer, Continental).

**(4) Les pondérations sont des capitalisations pleines, pas les poids officiels.** Les indices
réels pondèrent par le **flottant** et **plafonnent** (NDX : 24 % maximum sur le premier nom ;
DAX : 15 %). Les concentrations du §3.3 sont donc des parts **économiques** brutes, qui
constituent une **borne supérieure** du poids officiel pour les plus gros noms.
*Contrôle de qualité* : sur le DAX, la corrélation entre les poids recalculés ici et les poids
flottants publiés (millésime 2025-09) est de **0.920 (n=38)**, et les écarts vont dans le sens
attendu — SAP, à flottant quasi total, pèse davantage en poids officiel (14.0 %) qu'en part de
capitalisation pleine (9.5 %) ; Merck KGaA, détenue à ~70 % par la famille, l'inverse
(1.1 % officiel contre 2.9 % recalculé). Le mécanisme se vérifie, la méthode tient.

### 2.2 Fichiers livrés

`constituents_NDX.csv` et `constituents_DAX.csv` — une ligne par constituant, avec ticker,
société, secteur, devise, cours, capitalisation, poids recalculé, P/E trailing et forward, P/S,
EV/EBITDA, P/B, marge nette, croissance du CA et du BPA (versions Yahoo **et** versions
recalculées sur les états financiers annuels, avec le nombre d'exercices utilisés), dette
nette/EBITDA, rendement des bénéfices, nombre d'analystes suivant la valeur, et l'horodatage
UTC de récupération de chaque ligne.

---

## 3. Niveau indice

### 3.1 Multiples : agrégé contre médian

L'écart entre les deux colonnes est le résultat le plus informatif de ce dossier.

**Nasdaq-100** — capitalisation totale **42.01 tn USD**, 101 sociétés.

| Multiple | Agrégé (Σ/Σ) | Médiane du constituant | n | % cap |
|---|---|---|---|---|
| P/E trailing | **34.9** | **38.2** | 91 | 93.0 % |
| P/E forward (consensus) | **22.3** | 24.0 | 101 | 100 % |
| P/S trailing | 6.94 | 7.01 | 101 | 100 % |
| Price/Book | 10.13 | 9.79 | 101 | 100 % |
| EV/EBITDA | *45.1 — non fiable* | **24.4** | 98 / 101 | — |
| Marge nette | **19.9 %** (Σ bénéfices/Σ CA) | 19.7 % | 101 | 100 % |
| Dette nette/EBITDA | **0.25** | 0.47 | 98 | 99.7 % |

**DAX 40** — capitalisation totale **2.17 tn EUR**, 40 sociétés.

| Multiple | Agrégé (Σ/Σ) | Médiane du constituant | n | % cap |
|---|---|---|---|---|
| P/E trailing | **19.1** | **20.3** | 38 | 97.1 % |
| P/E forward (consensus) | **13.6** | 14.4 | 40 | 100 % |
| P/S trailing | 1.21 | 1.58 | 39 | 99.6 % |
| Price/Book | 1.78 | 2.24 | 40 | 100 % |
| EV/EBITDA | 11.7 | 12.6 | 36 | 91.8 % |
| Marge nette | **6.3 %** (Σ bénéfices/Σ CA) | 7.7 % | 39 | 99.6 % |
| Dette nette/EBITDA | **3.06** | 2.07 | 36 | 91.8 % |

**Trois lectures de ces tableaux.**

**(a) Sur le NDX, la médiane est AU-DESSUS de l'agrégé (38.2 contre 34.9).** C'est l'inverse du
récit habituel selon lequel les méga-capitalisations gonflent le multiple de l'indice. Ici, les
cinq premières lignes sont, sur bénéfices publiés, **moins chères que l'indice** : Alphabet 17.8,
Amazon 22.1, Microsoft 27.9, Nvidia 34.2, Apple 36.0 — contre une médiane de constituant à 38.2.
Chiffre décisif : **le P/E agrégé du NDX hors top-5 vaut 51.7**, contre 34.9 tous noms confondus.
Le poids des méga-capitalisations **abaisse** le multiple de l'indice, il ne le relève pas.

**(b) L'EV/EBITDA agrégé du NDX (45.1) doit être écarté ; seule la médiane (24.4) est lisible.**
Le rapport de sommes est ici pollué par des constituants à EBITDA quasi nul mais à valeur
d'entreprise élevée : CRWD affiche un EV/EBITDA de 3 618, ASML de 2 754, DDOG de 969. Ce n'est
pas un défaut de collecte, c'est la limite de l'agrégation par ratio de sommes quand le
dénominateur est proche de zéro pour des noms substantiels. Signalé plutôt que publié tel quel.

**(c) L'écart trailing → forward du NDX est très large et n'est pas entièrement de la
croissance.** L'agrégé passe de 34.9 à 22.3, ce qui implique une progression des bénéfices de
**+56.7 %** (1 203 mds USD de bénéfices trailing contre 1 885 mds attendus). Deux causes se
superposent, et il faut les distinguer :
  - *Une attente de croissance réelle, très concentrée* : Nvidia (+154 mds), Micron (+125 mds),
    Broadcom (+64 mds) et MicroStrategy (+57 mds) expliquent l'essentiel du delta. Le cycle
    mémoire/semi-conducteurs porte à lui seul la majorité de la révision.
  - *Un artefact de base comptable* : le BPA trailing de Yahoo est proche du GAAP (éléments
    exceptionnels inclus), le BPA forward est un **consensus d'analystes en base ajustée**.
    Ce ne sont **pas les mêmes bénéfices**. La preuve est dans l'échantillon : Alphabet affiche
    un P/E trailing de **17.8** et un P/E forward de **24.0** — le consensus « prévoit » une
    baisse de 26 % des bénéfices, ce qui traduit surtout un trailing gonflé par des éléments
    non récurrents. **Le taux de +56.7 % ne doit donc pas être lu comme une prévision de
    croissance.**

> **Statut épistémique du P/E forward.** Toutes les colonnes « forward » de ce dossier sont des
> **consensus d'analystes** — une opinion agrégée, révisable, non une donnée comptable. Elles
> sont disponibles sur 101/101 noms du NDX et 40/40 du DAX, avec un nombre d'analystes renseigné
> par titre dans les CSV.

### 3.2 Croissance et levier

| | NDX pondéré cap. | NDX médiane | DAX pondéré cap. | DAX médiane |
|---|---|---|---|---|
| CAGR du CA (états financiers) | **24.6 %** | **9.0 %** | **3.9 %** | **2.1 %** |
| CAGR du BPA dilué (états fin.) | 46.0 % ⚠ | 9.5 % ⚠ | 13.5 % ⚠ | 7.0 % ⚠ |
| Croissance CA (Yahoo, YoY trim.) | 44.3 % | 16.7 % | 8.9 % | 3.4 % |
| Marge nette | 30.5 % | 19.7 % | 10.6 % | 7.7 % |
| Dette nette/EBITDA | 0.25 (agrégé) | 0.47 | 3.06 (agrégé) | 2.07 |

⚠ **CAGR du BPA : couverture partielle** — 77/101 noms du NDX (**81.5 % de la capitalisation**)
et 35/40 du DAX (88.2 %). À traiter comme indicatif, pas comme un agrégat d'indice.

Le rapport pondéré/médian se répète sur la croissance : **24.6 % pondéré contre 9.0 % en
médiane** sur le CA du NDX. La croissance est intensément concentrée dans les plus grosses
lignes ; le constituant typique du Nasdaq-100 croît à un chiffre. Sur le DAX, l'écart existe
(3.9 % contre 2.1 %) mais l'ordre de grandeur reste faible des deux côtés.

**Levier : deux régimes.** Le NDX est structurellement peu endetté (dette nette/EBITDA agrégée
**0.25**). Le DAX est à **3.06**, tiré par l'immobilier et les industries capitalistiques :
Vonovia 16.8, Volkswagen 11.1, RWE 10.9, BMW 7.3, Mercedes-Benz 7.1 — les captives de
financement automobiles et les bilans d'utilities dominent. *Caveat* : la mesure n'a pas de sens
pour les banques et assureurs, et n'est de fait renseignée que partiellement pour eux
(Munich Re, Deutsche Bank, Commerzbank : absents ; Allianz : −4.77, non interprétable). Les
36/40 sur lesquels l'agrégat porte incluent donc quelques valeurs financières parasites.

### 3.3 Concentration

| | NDX | DAX |
|---|---|---|
| Nombre de lignes | 101 | 40 |
| Premier poids | **12.9 %** (NVDA) | 9.8 % (Siemens) |
| Top-5 | **50.0 %** | 41.1 % |
| Top-10 | **68.0 %** | 59.5 % |
| Top-20 | 80.7 % | 81.7 % |
| Herfindahl | **0.0613** | 0.0492 |
| N effectif (1/HHI) | **16.3** | 20.3 |

Top-10 NDX : NVDA 12.9, AAPL 10.9, GOOGL 10.3, MSFT 8.8, AMZN 7.1, AVGO 4.8, **SPCX 4.2**,
META 3.6, TSLA 3.1, MU 2.4.
Top-10 DAX : Siemens 9.8, SAP 9.5, Airbus 7.8, Allianz 7.6, Deutsche Telekom 6.4,
Siemens Energy 6.0, Infineon 3.7, Munich Re 3.0, Merck 2.9, Deutsche Post 2.9.

Le Nasdaq-100 se comporte comme un portefeuille de **16 titres équipondérés**, le DAX comme un
portefeuille de **20** — le DAX, avec 2.5× moins de lignes, est le **moins** concentré des deux.
La composition sectorielle explique l'écart : le NDX pèse **57.9 % en Technologie** (43 noms)
plus 16.0 % en Communication Services, contre un DAX réparti entre Industrie 32.0 %, Financières
19.0 %, Technologie 13.2 % et Santé 9.3 %.

À noter : **SpaceX (SPCX) figure au 7ᵉ rang du NDX avec 4.17 % du poids et 1.75 tn USD de
capitalisation**, pour un **résultat trailing négatif** (rendement des bénéfices −0.83 %) et un
P/S de 76.1. Il s'agit du plus gros contributeur individuel au bloc déficitaire de l'indice.

*Comparaison historique de la concentration* : non produite. Elle exigerait la composition et
les poids du NDX à chaque date passée, non disponibles gratuitement. **Aucun percentile de
concentration n'est avancé.**

### 3.4 Rendement des bénéfices, taux et prime de risque implicite

**La grandeur calculée est explicitement nommée dans chaque ligne.**

| | NDX | DAX |
|---|---|---|
| Rendement des bénéfices trailing (agrégé) | **2.86 %** | **5.25 %** |
| Rendement des bénéfices forward (consensus) | 4.49 % | 7.37 % |
| Taux 10 ans **nominal** de référence | **4.65 %** (UST, 2026-08-07) | **3.15 %** (zone euro AAA, 2026-08-06) |
| **Prime implicite = EY trailing − taux NOMINAL** | **−1.79 pt** | **+2.10 pt** |
| Prime implicite = EY forward − taux nominal | −0.16 pt | +4.22 pt |
| Taux 10 ans **réel** (TIPS) | 2.40 % (2026-08-07) | *non disponible* |
| **Prime = EY trailing − taux RÉEL** | **+0.46 pt** | *non calculée* |

Lecture. Sur bénéfices publiés et contre le taux **nominal**, le Nasdaq-100 offre un rendement
des bénéfices **inférieur de 1.79 point** au 10 ans américain : la prime de risque actions
implicite est **négative**. Rapportée au taux **réel** (TIPS 10 ans à 2.40 %), elle redevient
**légèrement positive, +0.46 point** — ce qui montre que la conclusion dépend entièrement du
déflateur retenu, d'où l'obligation de nommer lequel on utilise. Le point d'inflation implicite
(breakeven 10 ans) ressort à **2.25 %**.

Le DAX est dans une configuration inverse et bien plus confortable : **+2.10 points** contre le
nominal sur trailing, **+4.22 points** sur forward.

Il faut ajouter que le **taux américain lui-même est haut au regard du passé récent** : à
4.65 %, il se situe au **98.3ᵉ percentile des 10 dernières années** et au **95.5ᵉ des 20
dernières** — mais seulement au **42.3ᵉ percentile depuis 1962** (^TNX, historique depuis
1962-01-02 ; valeur yfinance 4.66 %, écart de **1 pb** avec la donnée officielle du Trésor, ce
qui valide la série). Le taux zone euro AAA à 3.15 % est au **99.2ᵉ percentile sur 10 ans** et au
**71.9ᵉ depuis 2005**. Une part de la compression des primes de risque vient donc du
dénominateur obligataire, pas seulement du numérateur actions.

**Position des multiples dans leur propre distribution historique — NON PRODUITE.**
Le calcul d'un percentile 10-20 ans sur le P/E d'indice exige un historique **de bénéfices
d'indice** validé (Nasdaq, STOXX, Bloomberg), que les sources gratuites employées ici ne
fournissent pas. **Aucun percentile de multiple n'est donc avancé comme calcul propre.**
À titre de point de comparaison tiers, **non reproductible et non vérifié** : GuruFocus donne un
P/E du Nasdaq-100 à **28.81 en août 2026**, pour une médiane historique de 22.93 et une moyenne
longue de 27.54. L'écart avec les 34.9 de ce dossier est cohérent avec une différence de
traitement des sociétés déficitaires — hors sociétés en perte, l'agrégé recalculé ici tombe à
**30.6**, ce qui rapproche sensiblement les deux mesures. Cette comparaison est indicative et ne
vaut pas validation.

---

## 4. Niveau prix — descriptif

### 4.1 Indices

| | NDX (`^NDX`) | DAX (`^GDAXI`) |
|---|---|---|
| Historique | 1985-10-01 → 2026-08-07 (10 292 séances) | 1987-12-30 → 2026-08-07 (9 762 séances) |
| Dernière clôture | 29 722.30 | 26 319.45 |
| Plus haut historique | 30 660.60 le **2026-06-02** | **26 319.45 le 2026-08-07** |
| Distance au plus haut | **−3.06 %** | **0.00 %** |
| Séances depuis le dernier plus haut | **46** (66 jours calendaires) | **0** |
| Vol. réalisée 20 j (annualisée) | **26.1 %** | **11.1 %** |
| Vol. réalisée 60 j | 26.1 % | 14.4 % |
| Percentile vol 20 j (historique complet) | **74.6ᵉ** | **15.5ᵉ** |
| Percentile vol 20 j (10 ans) | **77.7ᵉ** | 23.5ᵉ |
| Médiane historique de la vol 20 j | 18.2 % | 16.3 % |
| Performance YTD / 1 an / 3 ans ann. | +17.7 % / +27.1 % / +24.5 % | +7.5 % / +8.8 % / +18.2 % |
| Pire drawdown historique | −82.9 % | −72.7 % |

> **Avertissement de comparabilité.** `^NDX` est un indice de **prix** ; `^GDAXI` est le DAX
> **de performance**, c'est-à-dire un indice de **rendement total** qui réinvestit les dividendes
> nets. Le niveau, le « plus haut historique » et la profondeur des drawdowns du DAX ne sont
> donc **pas** directement comparables à ceux du NDX : le réinvestissement pousse
> mécaniquement l'indice vers de nouveaux sommets et raccourcit ses phases de repli. Le fait
> que le DAX close à son plus haut absolu et le NDX 3 % en dessous du sien **ne mesure pas la
> même chose des deux côtés.**

Les deux indices sont dans des régimes de volatilité opposés : le NDX à **26.1 %** de
volatilité 20 jours, soit le **77.7ᵉ percentile de sa décennie** et 1.4× sa propre médiane
historique ; le DAX à **11.1 %**, au **23.5ᵉ percentile** et sous sa médiane. La proximité au
sommet est, elle, banale : le NDX a passé **27.5 % de son histoire** (et **51.6 % des dix
dernières années**) à moins de 3 % de son plus haut ; le DAX a clôturé à un sommet absolu lors
de **5.5 %** de ses séances.

### 4.2 Breadth (participation des constituants)

| | NDX | DAX |
|---|---|---|
| Au-dessus de leur MM200 | **74/100 (74.0 %)** | **30/40 (75.0 %)** |
| À moins de 5 % de leur plus haut 52 semaines | **15/102 (14.7 %)** | **15/40 (37.5 %)** |
| À moins de 10 % de leur plus haut 52 semaines | 30.4 % | 52.5 % |
| **Écart médian au plus haut 52 semaines** | **−16.7 %** | **−7.7 %** |
| Plus de 20 % sous leur plus haut 52 semaines | **42/102** | 11/40 |

*(MM200 calculée sur 100/102 noms du NDX : deux constituants n'ont pas 200 séances d'historique.)*

C'est la divergence la plus nette du dossier. **L'indice NDX est à 3.1 % de son sommet pendant
que son constituant médian est 16.7 % sous le sien, et que 42 de ses 102 lignes sont en repli de
plus de 20 %.** Seuls 15 noms sur 102 sont à moins de 5 % de leur propre plus haut. Ce n'est pas
une contradiction : c'est l'expression arithmétique directe de la concentration mesurée au
§3.3 — un top-5 à 50 % du poids peut porter l'indice au sommet pendant que la majorité des
lignes recule. Le DAX présente la même asymétrie, mais nettement atténuée (médiane à −7.7 %,
11 noms sur 40 en repli de plus de 20 %).

---

## 5. Ce que ces chiffres prédisent et ne prédisent pas

Cette section est la contrepartie obligatoire des quatre précédentes. Elle est écrite pour être
lue **avant** que quiconque tire une inférence des tableaux ci-dessus.

### 5.1 Le pouvoir prédictif des ratios de valorisation croît avec l'horizon, et il est quasi nul en dessous d'un an

C'est le résultat central de **Campbell & Shiller, « Valuation Ratios and the Long-Run Stock
Market Outlook » (NBER WP 8221, 2001)**. Leurs R², cités verbatim :

| Prédicteur | Variable prédite | Horizon | R² |
|---|---|---|---|
| Ratio dividende/prix | croissance du **prix** réel | **1 an** | **« moins de 1 % »** |
| Ratio dividende/prix | croissance du prix réel | 10 ans | **9 %** |
| Ratio dividende/prix | **rendement** réel | 10 ans | **16 %** |
| P/E lissé 10 ans (CAPE) | croissance du prix réel | 10 ans | **30 %** |
| P/E lissé 10 ans (CAPE) | **rendement** réel | 10 ans | **40 %** |
| P/E lissé 10 ans (CAPE) | croissance des bénéfices lissés | 1 an / 10 ans | 1 % / 5 % |

Les auteurs écrivent que, à un an, « *le bruit de court terme dans les cours des actions submerge
la variation prévisible* » (« the short-run noise in stock prices swamps the predictable
variation »). Le contraste 1 an ≈ 0 % / 10 ans = 40 % est l'objet même du papier.

**Trois réserves que les auteurs posent eux-mêmes**, et qu'il serait malhonnête de ne pas
reprendre :
- **Chevauchement des intervalles** (note 6) : les observations à 10 ans se recouvrent, donc ne
  sont pas indépendantes. C'est le mécanisme classique qui **gonfle** les R² de long horizon —
  une littérature ultérieure a montré que ce gonflement peut être considérable.
- **Extrapolation hors échantillon** : sur le CAPE record de janvier 2000, ils écrivent
  explicitement « *nous ne trouvons pas cette prévision extrême crédible ; lorsque la variable
  indépendante s'est déplacée si loin de la plage historiquement observée, nous ne pouvons pas
  faire confiance à une droite de régression linéaire* ». C'est directement transposable au
  P/E du NDX mesuré au §3.1.
- **Ces régressions portent sur des indices larges de marché américain sur données longues**, pas
  sur un indice sectoriellement concentré à 58 % en technologie ni sur le DAX.

### 5.2 Hors échantillon, ces mêmes ratios ne battent souvent même pas la moyenne historique

**Goyal & Welch, « A Comprehensive Look at the Empirical Performance of Equity Premium
Prediction » (Review of Financial Studies, 2008)** réexaminent l'ensemble des prédicteurs
usuels — dividend/price, earnings/price, book/market, payout, taux d'intérêt, spreads. Leur
conclusion : ces modèles **échouent en échantillon comme hors échantillon**, sont instables, et
**n'auraient pas aidé un investisseur ne disposant que de l'information disponible à l'époque**
à timer le marché. La mise à jour **Goyal, Welch & Zafirov (« A Comprehensive 2022 Look… », RFS
2024)** teste 29 variables nouvelles issues de 26 papiers postérieurs : **plus d'un tiers ne sont
plus significatives même en échantillon**, et parmi celles qui le restent, **la moitié se comporte
mal hors échantillon**.

Autrement dit : même à l'horizon **pluriannuel** où le §5.1 accorde un pouvoir prédictif réel à la
valorisation, sa **valeur opérationnelle en temps réel** est contestée par la littérature la
plus complète disponible.

### 5.3 Un multiple élevé n'a aucun pouvoir de timing à l'horizon de quelques semaines

C'est la conséquence directe de 5.1 et 5.2, et elle mérite d'être écrite sans détour. Le CAPE de
janvier 2000 était à un record absolu de 44.9 — le marché a continué de monter pendant
deux mois supplémentaires. Le mécanisme est statistique et non anecdotique : un R² inférieur à
1 % à **un an** implique un R² indiscernable de zéro à **une semaine**, puisque le signal
supposé (une dérive lente du taux d'actualisation) se dilue dans une variance de bruit qui, elle,
croît linéairement avec le temps. Le rapport signal/bruit d'un ratio de valorisation **décroît
comme √horizon quand on raccourcit l'horizon**.

### 5.4 Ce qui prédit réellement à horizon jours

La littérature est claire sur le fait que la prévisibilité à court terme existe — mais qu'elle
porte sur le **second moment**, pas sur le premier.

- **La volatilité est fortement prévisible ; le rendement ne l'est pas.** Le modèle **HAR de
  Corsi (2009)**, qui régresse la volatilité réalisée sur ses composantes journalière,
  hebdomadaire et mensuelle, est devenu le benchmark standard précisément parce qu'il capture la
  mémoire longue de la volatilité avec de bons R². Le contraste est structurel : la volatilité
  persiste et reste durablement élevée après un choc, alors que les affirmations de forte
  prévisibilité des rendements proviennent le plus souvent d'inférences défectueuses sur
  intervalles chevauchants.
- **La volatilité implicite ajoute de l'information sur la volatilité future.** **Christensen &
  Prabhala (Journal of Financial Economics, 1998)** montrent que l'implicite domine la
  volatilité passée pour prévoir la volatilité future, et la subsume dans certaines
  spécifications. La littérature ultérieure ajoute que **l'appariement de la maturité de
  l'implicite à l'horizon de prévision est déterminant** — la structure par terme de la
  volatilité implicite est donc informative, **sur la volatilité**.
- **Le seul objet dérivé des options qui prédit les rendements le fait à horizon trimestriel,
  pas journalier.** **Bollerslev, Tauchen & Zhou (RFS, 2009)** montrent que la prime de risque de
  variance explique **plus de 15 %** de la variation des rendements excédentaires **trimestriels**
  du marché (1990-2005), et qu'**à cet horizon elle domine le P/E**, le default spread et CAY.
  Combinée au P/E, le R² trimestriel dépasse 25 %. Cela déplace le curseur du « très long terme »
  vers le « trimestre » — **pas** vers la journée ou la nuit.
- **Les événements à date connue sont le prédicteur de court horizon le mieux établi.**
  **Lucca & Moench (Journal of Finance, 2015)** documentent une dérive de rendement importante
  dans les 24 heures précédant les annonces **programmées** du FOMC ; **Savor & Wilson (2013)**
  documentent une prime de rendement concentrée sur les jours d'annonces macroéconomiques
  programmées. Le point commun de ces effets est qu'ils sont ancrés sur un **calendrier**, pas
  sur un niveau de valorisation. Le registre méthodologique interne du desk converge (L42 : la
  dérive pré-FOMC est réelle sur les indices actions), tout en signalant que la version
  *two-sided* de ce test n'a pas de support empirique dans le batch concerné.

### 5.5 Conclusion de la section, en toutes lettres

**La valorisation ne dit rien sur le rendement d'une position tenue une quinzaine d'heures.**

Ni le P/E de 34.9 du Nasdaq-100, ni sa prime de risque implicite négative de −1.79 point, ni le
P/E de 19.1 du DAX ne portent d'information exploitable sur la direction d'une nuit donnée. Le
R² de la meilleure de ces variables est « moins de 1 % » à **un an** ; à quinze heures, il est
indiscernable de zéro. Ces chiffres décrivent **le prix payé pour un flux de bénéfices** et
appartiennent à un horizon pluriannuel.

Ce qu'ils peuvent légitimement informer, à condition de ne pas confondre les niveaux :
- **la taille de la queue de distribution**, et non son signe. Un indice à P/E 34.9, à 58 % en
  technologie, dont 50 % du poids tient en cinq lignes et dont la volatilité réalisée est au
  77.7ᵉ percentile de sa décennie, est un objet dont **la variance conditionnelle** est
  descriptible — et la variance, elle, est prévisible (§5.4) ;
- **l'hétérogénéité entre les deux indices**, qui est réelle et documentée ici : régimes de
  volatilité opposés (26.1 % contre 11.1 %), concentration différente (N effectif 16.3 contre
  20.3), primes implicites de signes opposés (−1.79 pt contre +2.10 pt), leviers opposés
  (0.25× contre 3.06×). Traiter GER40 et US100 comme deux instances du même objet « indice
  actions proche de son plus haut » serait contredit par les données.

Aucune de ces deux lectures ne constitue un signal, et aucune ne figure dans ce document sous
forme de seuil.

---

## 6. Limites connues

1. **Composition du DAX** possiblement périmée d'un ou deux titres (§1) ; effet négligeable sur
   les agrégats pondérés, non nul sur les statistiques de breadth en nombre de noms.
2. **Fournisseur unique** pour tous les fondamentaux (Yahoo via yfinance). Aucune source
   secondaire n'a permis de recouper titre par titre. Les mélanges de base comptable
   (GAAP trailing contre consensus ajusté forward) sont documentés au §3.1(c) mais non corrigés.
3. **Devises non converties, et il ne faut pas les convertir.** Les agrégats du NDX sont en USD,
   ceux du DAX en EUR. Les ratios étant sans dimension, ils restent comparables ; les
   capitalisations totales (42.01 tn USD contre 2.17 tn EUR) ne le sont pas directement.
4. **Poids recalculés ≠ poids officiels** (flottant, plafonnement) — validé à 0.920 de
   corrélation sur le DAX, non validable sur le NDX faute de poids publiés accessibles.
5. **`^GDAXI` est un indice de rendement total**, `^NDX` un indice de prix (§4.1).
6. **Aucun percentile historique de multiple** n'est produit (§3.4).
7. **EV/EBITDA agrégé du NDX inutilisable** ; médiane seule retenue (§3.1(b)).
8. **Dette nette/EBITDA du DAX** contaminée par quelques valeurs financières pour lesquelles la
   mesure n'a pas de sens (§3.2).
9. La couverture des données est celle d'**un instant** (2026-08-09, 21:15-21:18 UTC). Yahoo
   révise ses champs ; une ré-exécution ultérieure ne redonnera pas exactement ces chiffres.

---

## 7. Reproductibilité

Tous les fichiers sont dans
`Multi_Asset/research/active/ath_regime_review_2026-08/valuation/`.

```
01_constituents.py   parse les compositions depuis le wikitext brut mis en cache
02_fundamentals.py   récupère les fondamentaux par titre (cache disque, 1 JSON/ticker,
                     sleep 0.6 s, exceptions capturées) ; --refresh pour forcer
03_prices.py         historiques ^NDX / ^GDAXI, vol réalisée, drawdown, ATH, breadth
04_aggregate.py      couverture, agrégats Σ/Σ et médians, concentration, ERP
05_context.py        percentiles de taux, proximité historique à l'ATH, breadth détaillé

constituents_NDX.csv     LIVRABLE — 101 lignes
constituents_DAX.csv     LIVRABLE —  40 lignes
cache/                   données téléchargées + résultats intermédiaires (~6.5 Mo)
  raw/*.json                 1 fichier par ticker, horodaté UTC
  coverage_{NDX,DAX}.csv     couverture champ par champ
  aggregates.json            tous les agrégats du §3
  index_stats.json           tout le §4.1
  context.json               tout le §4.2 et les percentiles de taux
  ust_daily_treasury_*.csv   courbes du Trésor US (nominale et réelle)
  ecb_*.csv                  séries ECB (zone euro AAA quotidienne, Allemagne mensuelle)
```

Ordre d'exécution : `01 → 02 → 03 → 04 → 05`. Les scripts sont idempotents ; tout ce qui a été
téléchargé est relu depuis `cache/` et n'est pas re-téléchargé.

**Sources citées**

- [Campbell & Shiller, *Valuation Ratios and the Long-Run Stock Market Outlook*, NBER WP 8221](https://www.nber.org/system/files/working_papers/w8221/w8221.pdf)
- [Goyal & Welch, *A Comprehensive Look at the Empirical Performance of Equity Premium Prediction*, RFS 2008](https://www.nber.org/system/files/working_papers/w10483/w10483.pdf)
- [Goyal, Welch & Zafirov, *A Comprehensive 2022 Look…*, RFS 2024](https://academic.oup.com/rfs/article/37/11/3490/7749383)
- [Bollerslev, Tauchen & Zhou, *Expected Stock Returns and Variance Risk Premia*, RFS 2009](https://public.econ.duke.edu/~boller/Published_Papers/rfs_09.pdf)
- [Christensen & Prabhala, *The relation between implied and realized volatility*, JFE 1998](https://www.sciencedirect.com/science/article/pii/S0304405X98000348)
- [Corsi, *A Simple Approximate Long-Memory Model of Realized Volatility* — synthèse et usage comme benchmark](https://portfoliooptimizer.io/blog/volatility-forecasting-har-model/)
- [US Department of the Treasury — Daily Treasury Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve)
- [ECB Data Portal — courbe des taux zone euro AAA](https://data.ecb.europa.eu/)
- [Wikipedia — List of NASDAQ-100 companies](https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies) · [Wikipedia — DAX](https://en.wikipedia.org/wiki/DAX)
- Point de comparaison tiers non reproductible : [GuruFocus — Nasdaq 100 PE Ratio](https://www.gurufocus.com/economic_indicators/6778/nasdaq-100-pe-ratio)
