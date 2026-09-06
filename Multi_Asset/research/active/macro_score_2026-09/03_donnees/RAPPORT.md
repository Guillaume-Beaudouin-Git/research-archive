# Plan d'acquisition de données macro — scoring macro systématique
### Volet 03 — données, avec le point-in-time au centre

Chercheur : recherche solo, budget quasi nul (préférence forte gratuit, plafond ~quelques centaines d'€/an).
Infrastructure existante : FX/indices M1 vrai UTC 2007-2026, futures via yfinance, crypto. **Manque : la donnée macro.**

Statut des affirmations dans ce document : chaque ligne de tableau est soit **[VÉRIFIÉ]** — j'ai consulté la documentation
officielle ou un papier académique cité en source — soit **[NON VÉRIFIÉ]** — connaissance générale non recoupée dans cette
session, à confirmer avant d'engager du temps d'ingénierie dessus. Je n'ai téléchargé aucune donnée ; ceci est un plan.

---

## 0. Résumé exécutif

Le problème central n'est pas l'accès aux séries macro — elles sont presque toutes gratuites. Le problème est que
**la quasi-totalité des séries macro largement utilisées en recherche (FRED "standard", Eurostat, OECD Data Explorer,
World Bank, IMF) ne renvoient QUE la valeur actuelle, la plus révisée** — c'est-à-dire l'inverse de ce qu'un backtest
honnête exige. Trois bases seulement livrent le millésime (la valeur telle que publiée à l'époque, avant révision) avec
une profondeur et une fiabilité suffisantes pour un usage systématique gratuit : **ALFRED** (Fed de St. Louis, US, le
socle), **le Real-Time Data Set de la Fed de Philadelphie** (US, redondant avec ALFRED sur le cœur mais avec un
historique plus long sur certaines séries et un format dédié à la recherche), et **FRED-MD/FRED-QD en version vintage**
(panels standardisés McCracken-Ng, avec un vrai historique de vintages téléchargeables depuis 1999-08). Pour la zone
euro, l'**Eurostat vintages database** et la **Real-Time DataBase de la BCE** existent et sont documentées, mais avec
une profondeur et une fraîcheur d'update très inférieures au dispositif américain — c'est le trou le plus sérieux de ce
plan pour qui veut un score macro multi-pays.

Le deuxième problème, orthogonal au premier : **la date de référence d'une donnée (« PIB T2 2026 ») n'est PAS la date
à laquelle elle a été rendue publique**. Le signal doit se déclencher à la date/heure de publication, jamais à la date
de référence. Aucune des bases de vintages ci-dessus ne donne systématiquement l'heure de publication à la minute pour
un usage de type "trading intraday sur annonce" — c'est le rôle des calendriers économiques (Section 2), dont l'accès
gratuit et fiable en historique est plus fragile que celui des données elles-mêmes.

Le troisième axe — consensus et surprise — est celui où le fossé gratuit/payant est le plus large : le standard
académique et desk (Bloomberg BEST, Citigroup Economic Surprise Index) n'est pas reconstructible à l'identique sans
abonnement Bloomberg, mais un proxy défendable existe (Section 3), avec une méthodologie publiée (Scotti, 2013/2016,
Fed Board) permettant de le reconstruire soi-même à partir de sources gratuites, moyennant une perte de qualité
documentée.

---

## 1. Le problème de révision, chiffré

Ce qui suit détermine si un score construit par erreur sur des données déjà révisées est *légèrement optimiste* ou
*complètement illusoire*.

- **PIB américain** : la révision moyenne entre première estimation ("advance") et estimation finale du taux de
  croissance trimestriel annualisé est de l'ordre de **+0,45 point de pourcentage** en moyenne (biais net positif : le
  chiffre publié en premier sous-estime en moyenne la croissance finale) — chiffre issu de la littérature de révision
  synthétisée dans un policy brief SUERF/BCE (Asimakopoulos et al., *"GDP revisions are not cool"*). Mais la moyenne
  masque des cas extrêmes : Croushore (2006) documente un trimestre (1977 T1) dont le taux de croissance du PIB réel a
  varié **entre 4,9 % et 9,6 %** annualisé selon le millésime consulté — un facteur ~2× sur le même trimestre, uniquement
  dû aux révisions successives (rebasages d'indices, changements méthodologiques, nouvelles données sources). **[VÉRIFIÉ,
  chiffres secondaires cités par une revue académique — je n'ai pas pu extraire le texte du PDF ECB WP 2857 lui-même,
  corrompu au fetch ; les chiffres viennent du résumé WebSearch du même papier et de Croushore]**.
- **Emploi américain (nonfarm payrolls)** : deux couches de révision distinctes.
  - Révisions mensuelles courantes : chaque chiffre est révisé deux fois dans les deux mois qui suivent (rapports
    suivants), avant la révision annuelle dite "benchmark". **[NON VÉRIFIÉ — je n'ai pas de chiffre moyen fiable pour
    cette couche dans cette session ; ne pas citer de nombre avant vérification BLS directe]**.
  - Révision annuelle "benchmark" (recalage sur les données exhaustives QCEW, ~1 an de décalage) : sur les 10 dernières
    années, la révision absolue moyenne a été de **0,2 % du niveau d'emploi total**, avec une fourchette de <0,05 % à
    0,3 % — mais 2021-2025 a vu cette moyenne grimper à **0,34 %** contre 0,12 % en 2016-2020. La révision d'août 2026
    (portant sur l'année finissant mars 2025) est l'une des plus grosses de l'histoire de la série : préliminaire
    **-911 000** emplois, ramenée à **-898 000** en révision finale (soit environ **-0,6 %** du niveau d'emploi non
    agricole). **[VÉRIFIÉ — CRS/Congress.gov IF12827, BLS CES Benchmark Announcement, FXStreet]**.
- **Inflation (CPI américain)** : structurellement beaucoup plus stable que le PIB ou l'emploi, car la révision ne
  vient QUE du recalcul annuel des facteurs saisonniers (appliqué rétroactivement sur 5 ans), pas d'une refonte de la
  donnée brute. Les révisions à l'inflation CPI mensuelle ont une masse de probabilité concentrée à zéro et **dépassent
  très rarement 1 point de pourcentage annualisé**. Exception notable : la révision de janvier 2023 a relevé
  l'inflation cœur annualisée du T4 2022 de **3,1 % à 4,3 %** (+1,2 pt), un cas où la révision a changé la lecture de
  politique monétaire du marché. **[VÉRIFIÉ — Liberty Street Economics/NY Fed, Barchart/Nasdaq]**.

**Implication pour le score macro** : un signal construit sur GDP au premier chiffre publié capte une variable
structurellement différente d'un signal construit sur le chiffre "actuel" de FRED standard — l'écart peut inverser le
signe du signal sur certains trimestres (cf. l'exemple 1977 T1). L'emploi a le même problème mais concentré sur un
événement annuel (le benchmark d'août-septembre), pas diffus mois par mois. Le CPI est de loin la série la plus sûre à
traiter en "quasi-PIT" avec la donnée courante — mais "quasi" n'est pas "jamais" (cf. 2022 T4).

---

## 2. Bases de millésimes point-in-time

| Source | Contenu | Couverture pays | Fréquence | Profondeur historique | Millésimes PIT | Latence pub. | Accès | Lib Python | Licence | Coût | Fiabilité |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ALFRED** (Fed St. Louis, archive de FRED) | >350 000 séries archivées avec 3 dates par observation (`date`, `realtime_start`, `realtime_end`) | Majoritairement US (BEA/BLS/Census/Fed) ; séries internationales mirroir présentes mais **profondeur de vintage non garantie pour ces dernières — à tester série par série avant usage** | Selon série (D/M/Q) | Variable par série, certaines remontent aux années 1950-60 | **OUI** — cœur du produit | Selon série, alignée sur la publication de l'agence source | API REST (`fred/series/observations` avec `realtime_start`/`realtime_end`), CSV web | **`fredapi`** (mortada/fredapi, PyPI, gère explicitement ALFRED/vintages), package R `alfred` (hors périmètre Python) | Clé API gratuite (inscription) | **0 €** | **[VÉRIFIÉ]** doc officielle St. Louis Fed + fredapi GitHub. Fiabilité : référence académique de facto pour le PIT US, maintenue en continu par la Fed |
| **Philadelphia Fed — Real-Time Data Set for Macroeconomists** | Vintages mensuelles de séries macro majeures (PIB réel/nominal, chômage, emploi non-agricole, IPC, indice de production industrielle, etc.) | US uniquement | Vintages mensuelles (nouvelle "release" chaque mois) | GNP/PIB réel : vintages trimestrielles depuis **1965 T4**, vintages mensuelles depuis **1965-11** ; chômage depuis 1966 | **OUI** — produit fondateur du champ real-time (Croushore & Stark) | Vintage = date de publication officielle de l'agence, documentée par série | Fichiers texte/CSV par série, téléchargement direct (pas d'API REST documentée) | Aucune lib dédiée trouvée ; parsing manuel des CSV (trivial, format stable) | Domaine public / usage académique libre | **0 €** | **[VÉRIFIÉ]** philadelphiafed.org. Fiabilité : source historique de la littérature real-time (Croushore-Stark 2001) ; recoupe largement ALFRED sur le noyau US mais utile en cross-check et pour l'historique plus ancien |
| **OECD Real-Time Database** (Dallas Fed) | 13 variables (PIB/GNP réel et nominal, déflateur, production industrielle, taux de chômage, IPC, masse monétaire, etc.) | 26 pays OCDE (dont zone euro implicitement via pays membres, pas d'agrégat euro) | Vintages trimestrielles | Vintages de **1962 T1 à 1998 T4** (valeurs remontant parfois à 1956 T1) | **OUI mais figé** — "as is", projet non commercial, **non mis à jour depuis 1998** | Vintage = date de publication du Main Economic Indicators de l'époque | Fichiers Excel, un par pays/variable | Aucune | Libre, "as is", pas de support | **0 €** | **[VÉRIFIÉ]** page Dallas Fed. **Utilité limitée pour un score 2026** : la base s'arrête en 1998. La continuation annoncée ("OECD Main Economic Indicators Original Release Data and Revisions Database", vintages continues depuis janvier 1999) existait sous l'ancien data.oecd.org/OECD.Stat, **retiré le 1er juillet 2024** au profit d'OECD Data Explorer + SDMX — **je n'ai pas pu confirmer dans cette session si le module "original release + revisions" a survécu à la migration**. [NON VÉRIFIÉ — À TESTER avant d'y investir du temps : interroger `https://sdmx.oecd.org/public/rest/` pour un dataflow de type MEI_REV] |
| **Eurostat — Vintages of data (euroind_vtg)** | Tables de vintages pour indicateurs euro (PIB en tête), avec une dimension "date de révision" | Zone euro / UE (agrégats + pays membres selon table) | Selon table, cœur trimestriel (PIB) | Dimension de révision continue **depuis 2001** dans les tables statiques, **depuis 2021** dans les tables mises à jour régulièrement | **OUI** | Date de publication dans Eurobase | API SDMX Eurostat (REST), aussi Eurostat Data Browser | `eurostat` (package R non-Python), sinon **`sdmx1`** générique en Python, ou `pandasdmx` | Réutilisation libre (licence Eurostat standard, citation requise) | **0 €** | **[VÉRIFIÉ]** metadata ESMS Eurostat officielle (euroind_vtg_esms.htm). Fiabilité : institutionnelle, mais couverture de variables et de pays bien plus étroite que ALFRED — à vérifier série par série avant de bâtir un score EUR dessus |
| **BCE — Real Time DataBase (RTDB / RTD)** | Vintages de >200 variables macro/financières zone euro, basées sur le Monthly/Economic Bulletin de la BCE | Zone euro (agrégat) | Selon variable (M/Q) | Vintages depuis **janvier 2001** | **OUI** | Date de parution du Bulletin BCE | Fichiers par période (2001-2014) + **ECB Data Portal web services** pour 2015+ (SDMX) | `sdmx1` / `pandasdmx` pour l'extraction SDMX du ECB Data Portal | Libre (SDW standard ECB) | **0 €** | **[VÉRIFIÉ]** ECB SDW node 9689716, EABCN mirror, doc ECB (mb201009_focus05). ⚠ Deux sources divergent sur la fréquence de mise à jour : une page indique "mise à jour semestrielle (janvier/juillet)", une autre "trimestrielle" — **à trancher à l'inscription**, mais dans les deux cas c'est un ordre de grandeur bien plus lent qu'ALFRED (mensuel) |
| **FRED-MD / FRED-QD — vintages historiques** | Panel standardisé McCracken-Ng : 128 séries mensuelles (FRED-MD) / panel trimestriel (FRED-QD), conçu pour la recherche factorielle/big-data macro | US uniquement | Mensuel (FRED-MD) / trimestriel (FRED-QD) | **Archives de vintages téléchargeables** : FRED-MD 1999-08 à 2014-12 et 2015-01 à 2025-12 (deux zips) ; FRED-QD 2018-05 à 2025-12 | **OUI, confirmé** — chaque zip contient un CSV par mois/trimestre de publication, donc reconstruction PIT directe sans repasser par ALFRED série par série | Vintage = mois de génération du panel (aligné sur le calendrier FRED) | Téléchargement direct des zips (research.stlouisfed.org/econ/mccracken/fred-databases), pas d'API dédiée | Aucune lib officielle ; lecture triviale des CSV (format documenté dans le papier JBES 2016) | Libre, citer McCracken & Ng (2016) / Federal Reserve Bank of St. Louis | **0 €** | **[VÉRIFIÉ par fetch direct de la page officielle en session]**. C'est probablement **la meilleure base de départ** pour un score macro multi-facteurs US : standardisée, documentée académiquement (JBES 2016, McCracken-Ng), et vintage-trackée nativement — contrairement à la légende répandue qui présente FRED-MD/QD comme une base "current vintage only" |

**Verdict pratique** : pour un score US, ALFRED (granularité série-par-série, historique le plus long) + FRED-MD/QD
vintages (panel prêt à l'emploi, standardisé académiquement) couvrent l'essentiel à coût nul. Pour l'international, le
dispositif est nettement plus faible : Eurostat/BCE existent mais avec une profondeur, une largeur de variables et une
fraîcheur inférieures ; OECD RTD est un artefact historique figé à 1998 sauf confirmation que la continuation SDMX
existe encore. **Aucune base de millésimes gratuite et vivante identifiée pour le Japon, la Chine, le Royaume-Uni ou le
Canada dans cette session — à rechercher spécifiquement si le score doit être multi-pays au-delà US/zone euro.**

---

## 3. Calendriers de publication (date et heure exactes)

Le signal doit se déclencher à la publication, pas à la date de référence de la donnée — ALFRED/Philly Fed donnent la
date de vintage (donc la date de publication au jour près, en général), mais **pas systématiquement l'heure**, ce qui
suffit pour un score qui se recalcule en fin de journée mais pas pour du trading intraday sur annonce.

| Source | Contenu | Couverture | Historique | Heure exacte | Accès | Coût | Fiabilité |
|---|---|---|---|---|---|---|---|
| **Econoday** | Calendrier US + 18+ pays/zones, consensus avec fourchette complète, nombre d'économistes sondés, historique de révisions | US fort, international en option payante | Le calendrier public couvre l'actuel ; profondeur d'historique du consensus non vérifiée sans abonnement | Oui (heure de publication officielle par indicateur) | Calendrier web gratuit (portée limitée), API/flux temps réel réservés à l'abonnement institutionnel | Gratuit (public, limité) / payant pour l'entreprise (tarif non public, contact commercial requis) | **[VÉRIFIÉ existence + description]**. C'est la source que la plupart des courtiers (Schwab, Fidelity, E*TRADE) embarquent en marque blanche — signe de fiabilité de facto dans l'industrie retail/institutionnelle légère |
| **Trading Economics** | Calendrier ~1600 événements/mois, 150+ pays, consensus ("survey"), API dédiée | Très large (150+ pays) | Historique disponible via API, profondeur non chiffrée précisément dans cette session | Oui | API REST à crédits (chaque endpoint a un coût en crédits, 1-10 crédits/appel) + offre web Basic ($29/mois) / Standard ($199/mois) | **Payant** — mais le plan Basic tombe dans le budget "quelques centaines d'€/an" si annualisé | **[VÉRIFIÉ]** docs.tradingeconomics.com + page pricing. Bon rapport couverture/prix pour qui a besoin d'international large ; fiabilité du consensus lui-même non auditée indépendamment dans cette session |
| **Investing.com — calendrier économique** | Le calendrier le plus largement utilisé par les traders retail (nom d'événement, pays, devise, importance, actual/forecast/previous) | Très large | Aucune API officielle | Oui, affiché sur le site | **Pas d'API publique** ("terms de leurs fournisseurs de données" l'interdisent) ; scraping tiers via Apify (plusieurs scrapers listés, ex. `pintostudio/economic-calendar-data-investing-com`) — fragile, sujet à rupture si le site change de structure, zone grise contractuelle | Scraper tiers : quelques €/mois selon volume Apify | **[VÉRIFIÉ non-existence d'API officielle]**. Risque juridique/technique documenté par la source elle-même (pas de garantie de disponibilité). À utiliser en dernier recours ou en cross-check, pas comme source primaire d'un système qui tourne sans supervision |
| **FXStreet / MarketWatch** | Calendriers concurrents d'Investing.com, même absence d'API publique documentée | Large | — | Oui, affiché | Scraping uniquement, mêmes réserves | Variable | **[NON VÉRIFIÉ dans cette session]** — cité dans le brief, non recherché individuellement ; traiter comme équivalent d'Investing.com en fiabilité jusqu'à vérification |
| **CFTC / BLS / BEA / Fed — calendriers officiels de publication** | Dates ET heures officielles de publication de LEURS PROPRES séries (ex. BLS publie systématiquement à 8:30 ET) | US, par agence | Le calendrier futur/actuel est public ; l'historique des heures passées demande recoupement avec les archives de presse ou ALFRED (`realtime_start`) | Oui, à la minute, et c'est la source la plus fiable qui existe puisque c'est l'émetteur lui-même | Pages web par agence (bls.gov/schedule, bea.gov/news/schedule) | Gratuit | **[NON VÉRIFIÉ dans cette session — mais quasi-certain]** : à confirmer que ces calendriers remontent assez loin en arrière pour reconstruire un historique complet d'heures de publication. **C'est la piste la plus solide pour la partie US du calendrier, moins chère et plus fiable que du scraping tiers** — à explorer en priorité avant tout scraping |

**Recommandation calendrier** : construire le socle US à partir des calendriers officiels d'agences (gratuit, autorité
primaire) recoupés avec `realtime_start` d'ALFRED pour la date, et n'aller vers Trading Economics (payant, structuré,
API) que pour l'extension internationale — éviter Investing.com/FXStreet en source primaire de production tant qu'un
scraper n'a pas été audité pour la stabilité et la légalité.

---

## 4. Consensus et surprises

La surprise (réalisé − consensus) est le signal macro le plus documenté dans la littérature (Andersen-Bollerslev-Diebold-Vega
2003 et suite), mais **le standard du marché (consensus Bloomberg) n'est pas accessible sans terminal Bloomberg**.

### 4.1 Alternatives au consensus Bloomberg

| Source | Nature du consensus | Profondeur historique | Licence/coût | Fiabilité argumentée |
|---|---|---|---|---|
| **Trading Economics** | Moyenne ("survey") d'un panel d'économistes, méthodologie propriétaire non publiée en détail | Disponible via API (payante) | Payant, cf. section 2 | **[VÉRIFIÉ existence]**. Panel plus petit et moins audité que Bloomberg BEST (qui interroge des dizaines d'économistes sell-side avec pondération) — s'attendre à un consensus plus bruité, surtout sur les indicateurs de seconde zone |
| **Econoday** | Fourchette complète + nombre d'économistes sondés + historique de révisions du consensus lui-même | Institutionnel (payant) plus riche que le public | Payant au niveau entreprise | **[VÉRIFIÉ]**. C'est la source qui documente le MIEUX sa propre méthodologie (nombre de contributeurs affiché) — meilleure candidate en fiabilité parmi les non-Bloomberg si le budget entreprise est atteignable, ce qui est incertain sous "quelques centaines d'€/an" |
| **Investing.com / FXStreet / MarketWatch** | Consensus affiché sans méthodologie publiée, panel et pondération inconnus | Non structuré pour l'historique (scraping requis) | Gratuit à consulter, coût = scraping | **[NON VÉRIFIÉ, scepticisme de principe]**. Aucune de ces sources ne documente son panel de contributeurs ni sa méthode d'agrégation — à traiter comme un proxy bruité du consensus réel, jamais comme une vérité de terrain pour une étude de significativité statistique sérieuse |

### 4.2 Construction du Citigroup Economic Surprise Index (CESI) — et reconstruction possible

**[VÉRIFIÉ via littérature académique et fiches descriptives]** : le CESI est un indice de surprises économiques
pondérées et standardisées, construit ainsi :
1. Pour chaque indicateur publié, calcul de la surprise = (réalisé − consensus Bloomberg médian).
2. Standardisation par l'écart-type historique des surprises de CET indicateur (pour rendre comparables des surprises
   en unités différentes — points de PIB vs milliers d'emplois vs points d'indice PMI).
3. Pondération de chaque indicateur par son **impact FX historique mesuré** (choc de 1 écart-type sur le spot FX à
   haute fréquence).
4. **Décroissance temporelle** : chaque événement perd du poids avec l'âge, avec une **demi-vie de 45 jours**
   (convention Citigroup) — un choc vieux de 45 jours pèse la moitié d'un choc du jour même.
5. Agrégation glissante sur une fenêtre de **trois mois**, recalculée quotidiennement.

**Référence académique pour la reconstruction** : Scotti, C. (2013/révisé 2016), *"Surprise and Uncertainty Indexes:
Real-Time Aggregation of Real-Activity Macro-Surprises"*, Federal Reserve Board IFDP 1093 — publie une méthodologie
alternative complète et documentée pour construire un indice de surprise à partir de données réalisées vs. attentes
(état-espace / filtre de Kalman sur les surprises standardisées), **conçue précisément pour être reproductible sans
Bloomberg**. C'est la voie la plus défendable pour reconstruire un équivalent CESI maison : remplacer le consensus
Bloomberg par Trading Economics/Econoday (avec la perte de qualité documentée en 4.1), et suivre soit la méthode Citi
(pondération FX + demi-vie 45j, plus simple à répliquer), soit la méthode Scotti (état-espace, plus rigoureuse
statistiquement mais plus lourde à implémenter).

**Limite honnête** : sans le panel de contributeurs Bloomberg, l'indice reconstruit mesurera un objet corrélé au CESI
officiel mais pas identique — à valider par une comparaison directe sur la période où le CESI officiel est
publiquement affiché en continu (ex. via Cbonds ou les graphiques librement diffusés par Citi/desks), avant toute
utilisation comme feature de production.

---

## 5. Séries macro brutes directement téléchargeables en Python

| Source | Contenu | Couverture | Lib Python | Coût | Fiabilité |
|---|---|---|---|---|---|
| **FRED (standard, non-vintage)** | ~800k séries, agrégateur qui mirroir BEA/BLS/Census/Fed + une partie d'OCDE/Eurostat/BIS | US fort, international partiel (mirroir) | `fredapi`, `pandas-datareader` (module FRED) | 0 € (clé API gratuite) | **[VÉRIFIÉ]** — référence de facto, mais **ATTENTION : c'est la valeur COURANTE, révisée**. Ne jamais l'utiliser pour un backtest sans repasser par ALFRED pour les séries sujettes à révision significative (section 1) |
| **FRED-MD / FRED-QD** | Panel standardisé 128 séries US (voir section 2) | US | Lecture CSV directe (pas de lib dédiée) | 0 € | Voir section 2 — **utiliser la version vintage, pas le CSV "current" seul** |
| **OECD (Data Explorer / SDMX)** | Statistiques OCDE post-migration 2024 (national accounts, CLI, prix, chômage, etc.) | 38 pays OCDE + partenaires | `sdmx1`, `pandasdmx`, ou requêtes REST directes vers `sdmx.oecd.org/public/rest/` | 0 € | **[VÉRIFIÉ migration, non vérifiée la persistance du volet "original release + revisions"]** — traiter la donnée OCDE "current" comme non-PIT par défaut |
| **Eurostat** | Comptes nationaux, emploi, prix, commerce extérieur UE/zone euro | UE + zone euro | `sdmx1` / `pandasdmx` (SDMX Eurostat officiel) | 0 € | **[VÉRIFIÉ]** — voir aussi section 2 pour le volet vintage |
| **BIS Data Portal** | Statistiques bancaires internationales (LBS, taux de change effectifs, prix immobiliers, dérivés, crédit) | International (banques déclarantes + 200+ contreparties) | API SDMX officielle (`data.bis.org`) + package non-officiel `stefanangrick/BIS` (GitHub) | 0 € | **[VÉRIFIÉ]** — API SDMX RESTful documentée, "free" confirmé |
| **IMF** | International Financial Statistics, Balance of Payments, WEO | International | Accès direct API SDMX (guide `bd-econ.com/imfapi1.html`, requests + parsing manuel), pas de package Python officiel dominant identifié | 0 € | **[PARTIELLEMENT VÉRIFIÉ]** — l'accès existe, l'écosystème de librairies Python dédiées semble plus pauvre que pour FRED/BIS/Eurostat ; prévoir du code maison au-dessus de `sdmx1` ou `requests` |
| **World Bank** | Indicateurs de développement, séries annuelles majoritairement | International, y compris pays hors OCDE | **`wbgapi`** (package officiel-adjacent, cité par un billet du blog World Bank), aussi module World Bank de `pandas-datareader` | 0 € | **[VÉRIFIÉ existence de wbgapi]** — utile pour du contexte macro basse fréquence (annuel), peu pertinent pour un score à fréquence mensuelle/trimestrielle réactif |
| **Banques centrales nationales** (BoE, BoJ, BoC, RBA, etc.) | Taux directeurs, bilans, publications propres | Par pays | Variable, souvent CSV/API propriétaire par banque centrale | 0 € | **[NON VÉRIFIÉ dans cette session]** — à traiter au cas par cas si le score s'étend au-delà US/zone euro |

**Point de vigilance transversal** : `pandas-datareader` reste activement maintenu (dernière release stable 0.11.1,
mi-2026, confirmé par PyPI/GitHub dans cette session) — la réputation de package à l'abandon qui circule dans la
littérature grise n'est plus d'actualité, mais certains lecteurs historiques internes (ex. AlphaVantage, Enigma) ont
été explicitement dépréciés ; vérifier lecteur par lecteur avant d'en dépendre.

---

## 6. Données de positionnement et de flux

| Source | Contenu | Fréquence | Historique | PIT | Accès | Lib Python | Coût | Exploitabilité comme entrée macro |
|---|---|---|---|---|---|---|---|---|
| **CFTC Commitments of Traders (COT)** | Positions ouvertes par catégorie de trader (commercial/non-commercial/etc.) sur futures et options US | Hebdomadaire (mardi, publié vendredi) | Depuis 1986 (legacy), plus récent pour disaggregated/TFF | **OUI de facto** — c'est un instantané figé à la date de collecte, republié tel quel, pas de "révision" ultérieure au sens PIB | Fichiers bulk CFTC.gov | **`cot_reports`** (PyPI `cot-reports`, actif, couvre Legacy/Disaggregated/TFF Futures-only et Futures+Options), alternatives `cftc-cot`, `pycot` | 0 € | **[VÉRIFIÉ existence des libs]**. Exploitable comme proxy de positionnement/flux (ex. extrêmes de positionnement spéculatif comme signal contrarian) — MAIS ce n'est pas un signal macro "fondamental" au sens du PIB/emploi, plutôt une donnée de microstructure/sentiment de marché ; à classer séparément dans le score si le design distingue macro fondamental vs positionnement |
| **TIC (Treasury International Capital)** | Flux de capitaux transfrontaliers US (achats étrangers de titres US, avoirs officiels étrangers, etc.) | Mensuel | Archives mensuelles disponibles, profondeur non chiffrée précisément ici | Publication mensuelle figée, pas de révision du type PIB documentée dans cette session | CSV/HTML sur home.treasury.gov + catalogue data.gov | **Aucune lib Python dédiée trouvée** — `pandas.read_csv`/`read_html` sur les fichiers Treasury suffit | 0 € | **[VÉRIFIÉ absence d'API structurée]** — donnée exploitable (flux de portefeuille étranger vers/depuis les bons du Trésor, pertinent pour un facteur de flux macro-financier) mais l'ingestion demandera du parsing maison, pas de raccourci |
| **BIS (positionnement bancaire international, dérivés OTC)** | Locational/Consolidated Banking Statistics, statistiques dérivés | Trimestriel (LBS/CBS), semestriel (dérivés OTC) | Longue (décennies pour certaines séries) | Pas un concept de "vintage PIT" au sens PIB — données de stock rapportées, révisions mineures possibles non quantifiées ici | SDMX API (section 5) | Idem section 5 | 0 € | **[VÉRIFIÉ existence]** — utile pour un facteur de flux bancaire transfrontalier / risque systémique, fréquence trop basse pour un score réactif mais pertinent en régime/contexte |

---

## 7. Taux et courbes

| Source | Contenu | Historique | Accès | Lib Python | Coût | Fiabilité |
|---|---|---|---|---|---|---|
| **Treasury.gov — Daily Par Yield Curve Rates** | Courbe de taux souverains US officielle quotidienne (1M à 30Y) | Archives par année, historique long (décennies) | Pages TextView par année + flux XML dédié (`treasury-daily-interest-rate-xml-feed`) | Packages tiers non officiels : `dailytreasuryrates` (PyPI), projet GitHub `data-ust` | 0 € | **[VÉRIFIÉ]** — source primaire officielle, aucune ambiguïté de fiabilité ; c'est la meilleure base gratuite pour la courbe US |
| **CME FedWatch (Fed funds futures)** | Probabilités de décision FOMC implicites dans les futures Fed Funds 30 jours | Historique étendu à 2015 pour l'API payante ; le dashboard temps réel est gratuit mais sans profondeur d'historique programmable | Dashboard web gratuit ; **FedWatch API payante dès ~25 $/mois** pour l'historique exploitable en backtest | Aucune lib Python officielle trouvée ; à consommer via l'API REST FedWatch si abonné | Gratuit (dashboard, non exploitable en batch) / ~25 $/mois (API, backtestable) | **[VÉRIFIÉ]** — c'est la seule voie *directement* estampillée CME pour un historique programmable ; alternative gratuite partielle via Investing.com "Fed Rate Monitor" (même source sous-jacente CME, mais sans garantie d'API stable, cf. section 3) |
| **OIS (Overnight Index Swap)** | Anticipations de taux court terme, alternative/complément aux Fed funds futures | — | **Aucune source gratuite fiable identifiée dans cette session** | — | — | **[NON VÉRIFIÉ / lacune ouverte]** — probable qu'il faille reconstruire un proxy à partir des Fed funds futures (CME) plutôt que d'accéder à de l'OIS pur gratuitement ; à creuser séparément si le score a spécifiquement besoin de la jambe OIS plutôt que Fed funds futures |
| **FRED (taux directeurs, courbes internationales)** | Fed funds rate, taux directeurs BCE/BoE/BoJ, spreads de taux via séries FRED dérivées | International (via mirroir FRED) | `fredapi` | 0 € | **[VÉRIFIÉ, cf. section 5]** — bon complément gratuit pour les taux directeurs hors US, moins riche que Treasury.gov pour la granularité de la courbe elle-même |

---

## 8. Plan d'acquisition priorisé

**Phase 1 — socle US point-in-time (coût : 0 €, complexité : faible-moyenne)**
1. Inscription clé API FRED/ALFRED (gratuite) → `fredapi`, extraction vintage des séries BEA (PIB), BLS (emploi, CPI),
   Census pour les composantes utilisées dans le score.
2. Téléchargement des deux archives de vintages FRED-MD et de l'archive FRED-QD (zips officiels McCracken-Ng) →
   panel prêt à l'emploi, standardisé, cité académiquement.
3. Calendriers officiels BLS/BEA (dates/heures de publication US) comme socle de l'horodatage des signaux, recoupés
   avec `realtime_start` ALFRED.

**Phase 2 — extension zone euro (coût : 0 €, complexité : moyenne, couverture moindre)**
4. Eurostat vintages (euroind_vtg) + ECB RTDB via SDMX (`sdmx1`) pour les agrégats zone euro — accepter une
   profondeur, une largeur de variables et une fraîcheur nettement inférieures au socle US ; documenter cette
   asymétrie dans le score plutôt que de la masquer.

**Phase 3 — surprise/consensus (coût : 0-300 €/an selon ambition)**
5. Construire un indice de surprise maison façon Scotti (2013/2016) à partir d'un consensus gratuit ou low-cost
   (Trading Economics plan Basic ~29 $/mois si le budget le permet ; sinon scraping prudent d'Investing.com/Econoday
   public en dernier recours, avec avertissement de fragilité).

**Phase 4 — compléments (coût : 0 €, valeur secondaire)**
6. CFTC COT (`cot_reports`) comme facteur de positionnement séparé (pas un facteur macro fondamental).
7. Treasury.gov courbe de taux + FRED taux directeurs internationaux pour le volet taux.
8. TIC / BIS pour un facteur de flux transfrontalier, fréquence basse, priorité la plus faible.

**Ce qui reste ouvert et non résolu par cette session** : la survie du module OECD "original release + revisions"
post-migration SDMX (section 2), la persistance d'un historique d'heures de publication BLS/BEA suffisamment profond,
l'existence d'une source OIS gratuite propre, et la fiabilité réelle des consensus non-Bloomberg par rapport au CESI
officiel (à mesurer empiriquement dès que les deux séries sont en main, avant tout usage en production).

---

*Aucune donnée n'a été téléchargée dans le cadre de cette session — document de planification uniquement.*
