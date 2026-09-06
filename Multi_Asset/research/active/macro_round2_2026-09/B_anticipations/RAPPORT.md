# Axe B — Trader le repricing des anticipations (banques centrales)

**Round 2 macro, dossier B_anticipations.** Rédigé 2026-09-06. Recherche web sur sources primaires (NBER, SF Fed, ECB, AEA, SSRN, GitHub des auteurs). Aucun backtest, aucune donnée téléchargée — ce document spécifie la meilleure version de l'axe et son protocole de falsification.

**Cadrage explicite** : ce n'est pas un verdict de faisabilité. Un round précédent a tué une formulation différente (score macro continu). L'objet ici est : (a) démonter ce que la littérature appelle en réalité « anticipations vs macro réalisée » — ce n'est PAS une seule famille mais trois, avec des propriétés statistiques opposées ; (b) identifier laquelle a la meilleure économie ; (c) écrire le test qui la tuerait ou la validerait, AVANT toute donnée touchée.

---

## 1. Le désassemblage : trois familles sous un seul label

Le brief parle d'« écart entre ce que la courbe price et ce qui se réalise ». La littérature distingue trois objets statistiquement différents, souvent confondus dans les pitchs de stratégie :

| Famille | Fenêtre | Signe attendu | Nature |
|---|---|---|---|
| **B1 — Drift PRÉ-annonce** | J-1 à J (avant la décision) | Positif systématique, **indépendant du sens de la surprise à venir** | Prime de risque pour incertitude non résolue (Lucca-Moench) |
| **B2 — Choc à l'annonce** | Fenêtre 30-70 min autour de l'annonce | Signe = signe de la surprise, par construction | Repricing quasi-instantané — c'est la variable exogène, pas une stratégie |
| **B3 — Drift POST-annonce** | J à J+15/50 | Signe = signe de la surprise (**continuation**), donc bilatéral par construction | Absorption lente du flux (Brooks-Katz-Lustig), extrapolation (Neuhierl-Weber) |

Ce tableau est la conclusion la plus importante du rapport : **B1 est structurellement à sens unique (donc jamais bilatéral, quoi qu'on fasse), B3 est structurellement bilatéral (le test bilatéral existe par construction du signe de la surprise)**. Le kill interne (« colonnes miroir qui ne testaient rien ») a de fortes chances d'avoir confondu ces deux natures — voir §7.

---

## 2. B1 — Le drift pré-FOMC (Lucca-Moench) : effet réel, mécaniquement non directionnel, et qui a DISPARU

**Papier fondateur** : Lucca, D. & Moench, E. (2015), *The Pre-FOMC Announcement Drift*, Journal of Finance 70(1), 329-371 — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12196), [NY Fed Staff Report 512](https://www.newyorkfed.org/research/staff_reports/sr512.html).

- Échantillon original septembre 1994 – mars 2011. Rendement excédentaire moyen sur actions US dans les 24h précédant l'annonce FOMC, économiquement large (rapporté ~80 bps annualisés concentrés sur ~8 jours/an) et statistiquement significatif à des niveaux qui domineraient la prime actions totale si on les extrapolait naïvement.
- **Mécanisme théorique établi ensuite** (Hu et al., Ai-Bansal, Laarits) : c'est une **prime de résolution d'incertitude**, pas un pari directionnel — le marché est payé pour porter le risque non résolu jusqu'à l'annonce, **indépendamment du sens** de ce que l'annonce va révéler. Ce point est central : par construction théorique, il n'existe **pas** de version « courte » symétrique de ce trade — être short avant chaque FOMC devrait perdre en moyenne, pas juste ne pas gagner. Un vrai test bilatéral de B1 n'est donc pas « long vs short symétrique », c'est « la prime existe-t-elle encore, avec quelle taille, et survit-elle au coût ».

**A-t-il survécu ? Non — c'est le résultat le plus solide du dossier.**
Kurov, Wolfe & Gilbert, *The Disappearing Pre-FOMC Announcement Drift*, Finance Research Letters 40 (2021) — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3134546), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7525326/). Échantillon étendu à décembre 2019 : **le drift disparaît après 2015-2016**, aussi bien pour les réunions avec conférence de presse que sans. Mécanisme de disparition proposé : baisse structurelle du VIX / de l'incertitude pré-réunion (moins de surprise à résoudre, notamment après l'adoption systématique du *forward guidance* écrit et des conférences de presse à chaque réunion depuis 2019, qui réduit l'opacité que la prime rémunérait). Une réplique ultérieure (*Economics Letters*/Applied Economics, 2024, ["short-lived or long-lasting?"](https://www.tandfonline.com/doi/full/10.1080/00036846.2024.2322573)) nuance sur volatilité implicite mais ne restaure pas l'effet actions.

**Sur les taux spécifiquement** : Pan & Peng, *The Pre-FOMC Drift in Long-Term Treasury Bonds* ([SSRN 4764451](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4764451), présenté AFA) documentent un drift distinct — antérieur dans le temps à celui des actions (dès J-2/J-1, pas seulement 24h) — sur le rendement 10 ans, **quasi absent sur le 2 ans** (0.71 bp vs 0.20 bp, ce dernier non significatif), attribué à la composante prime de terme. Le titre du papier (« et le déclin séculaire des taux longs ») indique que l'effet est lié au régime de taux bas post-2008 — **signal d'alerte de plus sur la survie dans le régime de taux actuel (post-2022, taux non nuls)**, non vérifié indépendamment ici.

**Verdict B1** : famille RESSUSCITABLE seulement comme *harvest* de prime (jamais directionnel), et la littérature dit qu'elle est **morte sur actions depuis 2015-2016** pour une raison structurelle (baisse de l'incertitude résiduelle, pas un artefact d'échantillon) — ce n'est pas un problème de puissance. Reste à vérifier si la version obligataire a le même profil de mort ou si elle est encore active — **c'est un candidat de réouverture légitime uniquement si quelqu'un actualise Pan-Peng post-2019 sur ZN**, pas une resucée du drift actions.

---

## 3. B3 — Le drift post-annonce : LA meilleure version de l'axe

C'est ici que se trouve la formulation la plus solide, et elle est **directement dans le véhicule visé (taux, ZN)**.

**Brooks, Katz & Lustig**, *Post-FOMC Announcement Drift in U.S. Bond Markets*, NBER WP 25127 (oct. 2018, révisé avril 2019) — [NBER](https://www.nber.org/papers/w25127), [Stanford GSB](https://www.gsb.stanford.edu/faculty-research/working-papers/post-fomc-announcement-drift-us-bond-markets). Auteurs : Jordan Brooks et Michael Katz sont chercheurs chez AQR, Hanno Lustig est macro-finance Stanford GSB — profil qui inspire confiance sur la robustesse aux coûts (AQR ne publie pas d'effets non monétisables).

- **Mécanisme** : une surprise de taux directeur FOMC déclenche des rachats/ventes de fonds obligataires par des investisseurs retail sensibles à la *salience* de la décision (pas à sa magnitude exacte) ; l'offre supplémentaire est absorbée **graduellement** par les arbitragistes, ce qui génère un drift de rendement dans le sens de la surprise pendant plusieurs semaines. C'est un mécanisme de **friction de flux**, pas d'information — donc a priori plus robuste à l'arbitrage rapide qu'un pur effet d'information (qui, lui, se corrige dès qu'il est documenté).
- **Taille mesurée** : une surprise de 10 bps sur les Fed funds ne déplace le 10 ans que de **1.7 bp le jour même**, mais le mouvement continue pour atteindre **14 bp après 50 jours** — soit un facteur ~8 entre la réaction instantanée et le drift cumulé. Effet également documenté sur le crédit IG, les TIPS et les swaps (spillover cross-marché).
- **Test bilatéral natif** : le signe du drift suit le signe de la surprise par construction (hausse de surprise → poursuite de la hausse de taux ; baisse → poursuite de la baisse). C'est exactement le test bilatéral qui manquait à la version interne — ici il n'a pas besoin d'être « construit », il est la définition même de l'hypothèse.
- **Faiblesse** : échantillon d'origine s'arrête ~2018 ; pas de version publique confirmant la survie post-2020 (régime de hikes 2022-2023 les plus rapides depuis 40 ans, changement de composition des détenteurs — plus de QT, moins de fonds mutuels retail marginal-price-setters). **C'est le point à falsifier en premier.**

**Neuhierl & Weber**, *Monetary Momentum*, NBER WP 24748 (2018, dernière révision SSRN mai 2024) — [NBER](https://www.nber.org/papers/w24748), [SSRN 3030126](https://www.ssrn.com/abstract=3030126). Version actions mais construite proprement en bilatéral dès l'origine — modèle direct de ce qu'un vrai test bilatéral doit ressembler :
- Drift **avant** (25 jours) ET **après** (15 jours) l'annonce, dans le sens du choc (expansionniste → hausse, restrictif → baisse).
- Écart cumulé actions : 2.5% jusqu'au jour de la décision, **4.5%+ quinze jours après**.
- Stratégie mécanique (long si choc expansionniste, short si restrictif) : **Sharpe multiplié par ~4** vs buy-and-hold sur l'échantillon étudié.
- Effet retrouvé cross-market (marché large, la plupart des industries, plusieurs indices actions internationaux) — **pas répliqué indépendamment ici sur les taux**, à vérifier avant de l'invoquer sur ZN.
- Statut : encore working paper en 2024 (pas de trace de publication en revue à comité de lecture trouvée) — **ne pas le citer comme peer-reviewed**, mais actualité de la révision (2024) suggère un intérêt et une robustesse qui persiste dans le temps aux yeux des auteurs.

**Pourquoi B3 est la meilleure version de l'axe, concrètement pour ce dépôt** :
1. Le véhicule (ZN/ZF/ZT futures, marge ~$1 800, coût ~0.01% RT) est directement le terrain de jeu de Brooks-Katz-Lustig (Treasuries).
2. Le test bilatéral est **structurel**, pas un artefact à construire après coup — la surprise a un signe mesuré par une méthode établie (§4), et l'hypothèse prédit une continuation du même signe. Il n'y a pas de piège « colonne miroir ».
3. La fenêtre (jusqu'à 15-50 jours) est compatible avec une tenue de position de plusieurs jours sur futures (IBKR, pas de contrainte daily-flat — L51/L53 du registre s'appliquent : le véhicule perso est de toute façon dominant).
4. Le gross rapporté (14 bp sur 50 jours pour un choc de 10 bp) est un ORDRE DE GRANDEUR au-dessus du coût futures (~0.4-1 bp RT sur ZN) — **gate IC largement passable en apparence**, à vérifier empiriquement (§8).

---

## 4. Le cœur méthodologique : comment isoler proprement une surprise de politique monétaire

C'est la pièce technique indispensable, quelle que soit la sous-famille retenue. Chronologie de la littérature :

1. **Kuttner (2001)**, *Monetary Policy Surprises and Interest Rates: Evidence from the Fed Funds Futures Market*, JME 47, 523-544 — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304393201000551). Fondateur : sépare la variation du taux cible en composante anticipée / surprise via le contrat fed funds futures du mois courant, dans une fenêtre étroite (souvent journalière avant les données intraday, puis 30 min). Résultat clé : les taux réagissent **fortement à la composante surprise, quasi nul à la composante anticipée** — c'est la preuve empirique fondatrice que seule la surprise compte, pas la décision elle-même.

2. **Gürkaynak, Sack & Swanson (2005)**, *Do Actions Speak Louder Than Words?*, Int. J. Central Banking 1(1), 55-93 — [Fed](https://www.federalreserve.gov/econres/feds/do-actions-speak-louder-than-words-the-response-of-asset-prices-to-monetary-policy-actions-and-statements.htm). Montre qu'**un seul facteur ne suffit pas** : il faut décomposer la surprise en (a) facteur « cible courante » et (b) facteur « chemin futur » (*path factor*, associé au communiqué). Base intraday depuis 1990. C'est la première preuve formelle que le communiqué déplace les prix indépendamment de la décision de taux — fondement direct de l'axe « anticipations, pas macro réalisée ».

3. **Nakamura & Steinsson (2018)**, *High-Frequency Identification of Monetary Non-Neutrality: The Information Effect*, QJE 133(3), 1283-1330 — [NBER w19260](https://www.nber.org/papers/w19260). Fenêtre de 30 minutes autour des annonces programmées ; construit un facteur unique de « policy news shock » (première composante principale de plusieurs contrats de maturités différentes) qui capture le chemin anticipé complet, pas juste le taux courant.

4. **Jarociński & Karadi (2020)**, *Deconstructing Monetary Policy Surprises — The Role of Information Shocks*, AEJ:Macro 12(2), 1-43 — [AEA](https://www.aeaweb.org/articles?id=10.1257%2Fmac.20180090). **La pièce la plus importante pour cet axe.** Sépare le choc composite en deux :
   - **MP shock** (choc de politique monétaire pur) : taux ↑, actions ↓ (co-mouvement négatif) ;
   - **CBI shock** (choc d'information de banque centrale) : taux ↑, actions ↑ (co-mouvement positif) — la banque centrale révèle une vue optimiste sur l'économie, pas une intention restrictive.
   - Identification par restriction de signe sur le co-mouvement haute fréquence taux/S&P 500 dans la fenêtre de l'annonce.
   - **Implication directe pour l'axe** : ignorer cette décomposition biaise n'importe quel test de « repricing des anticipations » — une partie des surprises mesurées naïvement (façon Kuttner brut) est en réalité de l'information sur l'économie, pas un choc de politique, et les deux ont des signes de réaction opposés sur les actions (mais probablement le MÊME signe sur les taux nominaux — à vérifier, c'est un point de design du test).

**Verdict méthodologique** : le protocole minimal pour toute version crédible de l'axe est **Kuttner/GSS pour le choc brut + décomposition Jarociński-Karadi pour isoler MP vs CBI**, jamais l'un sans l'autre. Une stratégie qui ne fait pas cette décomposition mélange deux effets aux dynamiques de marché différentes et sera instable hors échantillon dès que le mix change (ce qui est arrivé structurellement en 2020-2023 avec la prépondérance du choc inflation).

---

## 5. La prime de terme des fed funds futures (Piazzesi-Swanson) : biais réel, mais ce n'est pas un signal tradable directement

Piazzesi, M. & Swanson, E. (2008), *Futures Prices as Risk-Adjusted Forecasts of Monetary Policy*, JME 55(4), 677-691 — [NBER w10547](https://www.nber.org/system/files/working_papers/w10547/w10547.pdf), [SF Fed](https://www.frbsf.org/wp-content/uploads/piazezzi-0308.pdf).

- Les excess returns sur fed funds futures sont **positifs en moyenne et fortement contra-cycliques**, prédits par des indicateurs macro (croissance de l'emploi) et des spreads de crédit/Treasury.
- Conséquence : ignorer cette prime de risque **biaise systématiquement** toute lecture naïve des futures comme « anticipation pure » du marché — c'est un signal de risque, pas juste une espérance de taux.
- **A-t-elle survécu au ZLB (2008-2015) et post-2020 ?** La recherche n'a pas trouvé de réplication propre et publiée qui confirme ou infirme explicitement la persistance de cette prime au ZLB — le papier lui-même génère des valeurs extrêmes de prime au ZLB qui sont probablement de l'erreur de prévision plutôt qu'une vraie compensation de risque (le taux directeur ne pouvait pas baisser sous zéro, donc l'« excess return » mesuré à cette période est mécaniquement biaisé). Cette question reste **non tranchée par une source primaire trouvée** — c'est un point à traiter comme incertitude, pas comme un fait établi dans un sens ou l'autre.
- **Utilité pour l'axe** : la prime de terme est un input de correction, pas un signal — elle sert à ne pas confondre « le marché anticipe une baisse » et « le marché est payé pour porter du risque de taux », avant d'utiliser les futures comme mesure d'anticipation dans B1/B3. Pas une sous-stratégie autonome.

---

## 6. La littérature textuelle et de ton : tradable, mais pas gratuitement et pas en clair

- **Hansen & McMahon (2016)**, *Shocking Language: Understanding the Macroeconomic Effects of Central Bank Communication* — clustering LDA des communiqués FOMC dans un cadre FAVAR ; le *forward guidance* textuel a un impact distinct de l'info sur les conditions économiques et un impact de marché plus fort que le simple ton général.
- **Gorodnichenko, Pham & Talavera (2023)**, *The Voice of Monetary Policy*, AER — [NBER w28592](https://www.nber.org/system/files/working_papers/w28592/w28592.pdf), données et code sur [OpenICPSR](https://www.openicpsr.org/openicpsr/project/178302/version/V1/view). Modèle deep learning sur l'**audio** (pas le texte) des conférences de presse 2011-2019 : un ton vocal positif du président de la Fed fait monter les actions, **au-delà** de ce que capturent l'action de taux et le sentiment textuel. C'est un signal orthogonal aux deux précédents.
- **Verdict tradabilité** :
  1. Horizon d'exploitation extrêmement court (la réaction de marché au ton est quasi immédiate en conférence de presse — pas un signal de plusieurs jours comme B3).
  2. Reproduire ce signal exige (a) l'audio brut des conférences de presse en quasi temps réel, (b) un pipeline NLP/audio calibré — **infrastructure lourde, hors de portée d'un système signal-à-T-1/trade-à-T sur données gratuites**.
  3. Les données du papier (2011-2019, OpenICPSR) sont un jeu de réplication académique, **pas un flux temps réel** — inutilisable pour du live.
  4. **Conclusion** : cette famille est scientifiquement intéressante mais n'est PAS la meilleure version pour ce dépôt — coût d'infrastructure disproportionné par rapport à la breadth qu'elle ajoute (8 conférences de presse FOMC/an seulement, sur les 8 réunions ne sont pas toutes accompagnées d'une conférence). À classer « hors scope, infra manquante », pas « rejeté sur le fond ».

---

## 7. Le lien avec le dossier interne : pourquoi B3 est le bon angle de réouverture

Le dossier interne existant a mesuré un drift pré-FOMC réel sur 8 indices actions (L42 du registre), mais l'a classé NO-GO pour deux raisons : (a) les colonnes censées tester la jambe inverse (`_SS`) étaient `side = -side_long`, des miroirs exacts qui ne testent rien — **24/24 paires miroir**, donc **zéro information ajoutée sur l'asymétrie** ; (b) l'échantillon ne comptait que 49 événements sur 102 disponibles (sous-échantillonnage, la politique interne classe ce type de kill « PUISSANCE » comme rouvrable).

**Diagnostic à la lumière de ce round** : si le dossier interne testait un effet de type **B1** (drift avant l'annonce), le problème n'est pas seulement la puissance — c'est que B1 n'a **théoriquement pas** de jambe symétrique testable (§2) : une colonne miroir y est un artefact garanti puisqu'il n'existe pas de mécanisme économique qui prédirait un drift négatif pour une raison symétrique. Doubler l'échantillon sans changer la nature de l'hypothèse ne créera pas de test bilatéral valide.

**L'angle vraiment neuf, cohérent avec la politique de réouverture (catégorie PUISSANCE + GÉOMÉTRIE) :**
1. Basculer de B1 (pré-annonce, actions, non-directionnel) vers **B3 (post-annonce, taux, directionnel)** — l'hypothèse change de nature, ce n'est pas un simple ré-échantillonnage, donc ce n'est pas du data-mining sur le même angle (règle de la table de réouverture).
2. Construire le signe du test à partir du choc MP/CBI mesuré (Kuttner/GSS + décomposition JK), **jamais** en dérivant `side_short = -side_long` sur le même signal continu — le signe vient de la surprise mesurée à l'annonce, la continuation testée est sur la période suivante, ce sont deux variables différentes par construction, donc pas de miroir possible.
3. Doubler effectivement l'échantillon en utilisant TOUTES les réunions FOMC disponibles dans les séries USMPD/JK (voir §8 — profondeur 1988-2025 selon la série), pas seulement le sous-ensemble de 49/102 déjà utilisé.

---

## 8. Les données publiées et gratuites — inventaire vérifié

| Source | Couverture | Contenu | Fréquence MàJ | Accès |
|---|---|---|---|---|
| **USMPD** (Acosta, Ajello, Bauer, Loria, Miranda-Agrippino 2025, SF Fed WP 2025-30) | FOMC — profondeur à re-vérifier au téléchargement (page produit mentionne un focus récent, working paper couvre un historique plus long selon les auteurs) | Surprises MP1 (réunion courante), MP2 (réunion suivante), chocs Eurodollar/SOFR 4 trimestres ; fenêtres 30 min (déclaration), 70 min (conférence de presse), 30 min (minutes) | Régulière (dernière MàJ constatée : août 2026) | Gratuit, Excel + ZIP + code R, [frbsf.org](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/) |
| **JK shocks — Fed** (Jarociński & Karadi) | FOMC 1988–2025 (mise à jour à juillet 2025) | MP shock + CBI shock, décomposition « Poor Man's » et médiane, CSV par événement + agrégat mensuel | Mises à jour régulières par releases GitHub datées | Gratuit, CC-BY-4.0 (données) / BSD-3 (code), [github.com/marekjarocinski](https://github.com/marekjarocinski) |
| **JK shocks — ECB** | Réunions BCE, mis à jour à avril 2025 | Même décomposition MP/CBI appliquée à la zone euro | Régulière | Gratuit, mêmes licences, `jkshocks_update_ecb` |
| **EA-MPD** (Altavilla, Brugnolini, Gürkaynak, Motto, Ragusa) | Réunions BCE | Facteurs de politique monétaire (cible, chemin, QE, confiance) autour de la décision et de la conférence de presse | Mise à jour régulière | Gratuit, Excel via [ecb.europa.eu](https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx), factors via [gragusa.org/factors](https://gragusa.org/factors/) |
| **Calendriers officiels** | FOMC, ECB, BoE, BoJ | Dates passées et à venir (2026-2027 déjà publiées par les 4 banques) | Officielle | Gratuit — federalreserve.gov, ecb.europa.eu, bankofengland.co.uk, boj.or.jp |

**Ce qui manque encore** : aucune des sources ci-dessus ne fournit nativement une série de rendement futures ZN/ZF/ZT dans les fenêtres 30-70 min — il faudra apparier les dates d'événement (gratuites, ci-dessus) avec des données de prix haute fréquence sur les futures de taux (CME), qui elles ne sont PAS gratuites à la granularité intraday (le dépôt utilise déjà Databento pour NQ — extension possible mais coûteuse). **En clair : le signal (le choc, sa décomposition, le calendrier) est gratuit et téléchargeable dès aujourd'hui ; le prix d'exécution fin (l'entrée à la bonne minute) demande une source payante si on veut trader la fenêtre B2 elle-même — mais B3 (le drift des jours suivants) ne demande QUE des données de clôture quotidienne gratuites (yfinance ZN=F, en gardant à l'esprit L52 : `Open` = ouverture Globex du jour calendaire précédent), ce qui est un avantage économique net de B3 sur B1/B2.**

---

## 9. Breadth — comptage honnête, pas supposé

Calendriers 2026-2027 vérifiés aux sources officielles :

- **FOMC** : 8 réunions/an (confirmé 2026 et 2027).
- **BCE (Conseil des gouverneurs, décisions de politique monétaire)** : 8 réunions/an (les autres réunions du Conseil des gouverneurs ne sont pas des décisions de taux).
- **BoE (MPC)** : 8 réunions/an.
- **BoJ** : 8 réunions/an (confirmé calendrier 2027 : janvier, mars, avril, juin, juillet, septembre, octobre, décembre).

**Total central-bank event-days ≈ 32/an** pour les 4 banques majeures — c'est bien un ordre de grandeur au-dessus d'un score macro continu échantillonné en daily (qui génère ~252 observations/an mais dont la quasi-totalité ne porte aucune information nouvelle, contrairement à ce que suppose un test naïf en pseudo-daily).

Mais attention à ne pas confondre **nombre d'événements** et **nombre de paris indépendants** :
- Si on trade B3 (post-annonce) sur un seul instrument (ZN) avec une seule règle, on a **8 paris/an** sur cet instrument (un par FOMC) — la fenêtre de 15-50 jours entre deux FOMC consécutifs **se chevauche** (les réunions sont espacées de ~6-8 semaines, la fenêtre de drift de Brooks-Katz-Lustig va jusqu'à 50 jours) : les positions ne sont donc pas indépendantes, il faut traiter cela comme un processus continu avec chevauchement, pas 8 tirages i.i.d. — **HAC lag-6 obligatoire (déjà une hard rule du dépôt), et le bloc-bootstrap doit respecter le chevauchement, pas la fréquence d'échantillonnage**.
- Multiplier par 4 banques centrales (FOMC + BCE + BoE + BoJ) sur l'instrument de taux correspondant (ZN/ZT US, Bund/Schatz zone euro via Eurex — hors univers IBKR facile, Gilt UK, JGB Japon) donne une **vraie extension de breadth** SI et seulement si les mécanismes se généralisent (flux retail/fonds obligataires, structure de détention) — **non vérifié indépendamment ici pour la BCE/BoE/BoJ**, c'est une extension à tester, pas un fait acquis. La réplication de Neuhierl-Weber sur plusieurs marchés actions internationaux est un signal encourageant que le mécanisme n'est pas spécifique aux US, mais ce n'est pas une preuve sur les taux non-US.
- **Chiffrage honnête pour le design pré-enregistré** : traiter chaque banque centrale comme une hypothèse SÉPARÉE nécessitant sa propre correction Šidák (n_tests ≥ 4 avant même de compter les variantes de fenêtre), pas comme 32 tirages d'une seule hypothèse — c'est la discipline AMTP du dépôt.

---

## 10. Le risque d'efficience — ce que dit la taille mesurée du mouvement

- Brooks-Katz-Lustig : 14 bp de drift cumulé sur 50 jours pour une surprise de 10 bp — un **ratio gross/choc de 1.4**, largement au-dessus de 1 (le drift dépasse la réaction immédiate). Rapporté au coût futures ZN (~0.4-1 bp RT, selon le registre interne sur les futures propres), le ratio gross/coût serait de l'ordre de 14-35 — **très confortable si le chiffre tient hors échantillon**, mais c'est un chiffre d'un papier de 2018-2019, PAS vérifié sur 2020-2026 par une source trouvée ici.
- Le risque d'efficience concret n'est pas que le gross soit sub-bps (il ne l'est pas dans l'estimation d'origine) — c'est que **le régime ait changé** : (a) QT + retrait de la Fed comme acheteur marginal modifie la structure de détention qui est le mécanisme même du papier (les fonds mutuels retail ne sont peut-être plus le price-setter marginal) ; (b) le cycle de hikes 2022-2023 le plus rapide depuis 40 ans a pu accélérer l'apprentissage des arbitragistes et compresser le délai d'absorption documenté (mécanisme identique à la disparition du drift pré-FOMC actions, §2) ; (c) Nakamura-Steinsson elle-même documente un « effet d'information » qui, s'il domine de plus en plus le choc composite depuis 2020 (période de forte incertitude inflation), change le signe attendu de la continuation pour une partie des événements — d'où l'obligation de la décomposition JK (§4), qui n'était pas nécessairement appliquée dans la version 2018 de Brooks-Katz-Lustig.
- **Le test de falsification le moins cher, à faire AVANT tout backtest complet** : recalculer, sur les seules dates 2020-2026 (gratuites via USMPD + calendrier), la corrélation entre le choc MP (pas le choc composite brut) mesuré à l'annonce et le rendement du contrat ZN sur les 15 jours suivants. Si cette corrélation en sous-échantillon récent est proche de zéro ou de signe instable, l'axe est mort sur le RÉGIME, pas sur la méthode — et il faudrait alors regarder si l'effet a migré vers d'autres classes d'actifs/marchés (crédit, swaps — Brooks-Katz-Lustig documentent déjà un spillover, donc un candidat de repli existe dans le même papier).

---

## 11. Spécification pré-enregistrée de la meilleure version (à valider AVANT toute donnée touchée)

**Hypothèse H1 (primaire, B3)** : après une surprise de politique monétaire MP (décomposée JK, signe et magnitude mesurés dans la fenêtre officielle de l'annonce via une série publiée — USMPD ou JK), le rendement du future de taux correspondant (ZN pour FOMC en priorité) continue dans le même sens sur un horizon de 5 à 50 jours ouvrés, avec une magnitude croissante puis décroissante (profil documenté : 1.7 bp jour J → 14 bp à J+50 pour un choc canonique de 10 bp).

**Design du test** :
1. Univers d'événements : TOUTES les réunions FOMC USMPD/JK disponibles (pas un sous-échantillon arbitraire) — objectif explicite de doubler l'échantillon vs le dossier interne existant.
2. Signal = choc MP (composante JK), signé, standardisé. Rejet explicite du choc composite brut non décomposé (leçon §4).
3. Variable dépendante = rendement ZN cumulé à J+5, J+15, J+30, J+50 (courbe de profil, pas un seul horizon — condition de robustesse minimale).
4. Test bilatéral natif : régression du rendement futur sur le signe ET la magnitude du choc, sans jamais construire de colonne `-side` — le signe vient d'une variable EXOGÈNE distincte (le choc mesuré à l'annonce), la variable testée est une autre fenêtre temporelle. Vérifier explicitement, avant tout calcul de significativité, que la corrélation entre `side_long` de ce design et son opposé n'est PAS mécanique (contrôle L42 appliqué ici : si `sign(side_test) ≠ signal natif` moins de 5% du temps, retour au tableau de bord).
5. Walk-forward ≥5 folds (hard rule), HAC lag-6 obligatoire vu le chevauchement des fenêtres (§9), Šidák sur n_tests ≥4 (une banque centrale = un test) avant tout élargissement de l'univers.
6. **Sous-échantillon de falsification pré-enregistré** : 2020-01-01 → aujourd'hui, séparé du reste, jamais mélangé dans un test global qui masquerait une éventuelle décroissance de régime (discipline L31 du registre : split OOS/post-régime obligatoire pour les familles carry/reversal — application directe ici puisque le mécanisme dépend d'une structure de détention qui a changé).
7. Placebo apparié obligatoire (leçon L58/L49 du registre) : comparer contre une baseline non conditionnelle — le rendement moyen inconditionnel de ZN sur des fenêtres de même longueur non centrées sur un FOMC, pour s'assurer que ce n'est pas juste une saisonnalité de calendrier qui coïncide avec le motif FOMC.

**Ce qui falsifierait H1** :
- Corrélation signe(choc MP)/signe(rendement à J+15 ou J+30) non significative (HAC) sur le sous-échantillon 2020-2026 pris seul.
- Effet qui ne survit qu'au choc composite brut et disparaît une fois isolé le vrai choc MP (JK) — signe que c'était un artefact de confusion MP/CBI (§4), pas un vrai effet de flux.
- Placebo apparié qui rend un effet de taille comparable sur des fenêtres non-FOMC de même longueur (signe d'un artefact saisonnier, pas d'un mécanisme FOMC).
- Ratio gross/coût qui tombe sous 3× une fois les coûts réels ZN appliqués (gate IJR du dépôt) — peu probable vu l'écart mesuré en 2018 mais c'est le seuil qui tranche.

**Ce qui la validerait suffisamment pour passer en gate RESEARCH_PASS** : Sharpe walk-forward > 0.7 sur le sous-échantillon 2020-2026 seul (pas sur l'échantillon complet qui inclurait la période où le papier d'origine a mesuré l'effet — sinon on retesterait simplement Brooks-Katz-Lustig sur ses propres données), avec le test bilatéral et le placebo tous deux concluants.

---

## 12. Verdict de cadrage (pas de faisabilité)

La meilleure version de l'axe « repricing des anticipations » n'est **pas** le drift pré-FOMC (B1, actions) que le dossier interne a testé et dont la littérature dit qu'il est structurellement mort depuis 2015-2016 pour une raison de fond (baisse de l'incertitude résiduelle, pas de puissance). C'est le **drift post-annonce sur les taux** (B3, Brooks-Katz-Lustig / Neuhierl-Weber), qui a trois avantages décisifs : (1) le test bilatéral est natif à l'hypothèse, pas une reconstruction a posteriori vulnérable au piège des colonnes miroir ; (2) le véhicule (ZN futures) est déjà celui identifié comme dominant pour le compte personnel (L53) ; (3) les données du choc (USMPD, JK, gratuites, mises à jour 2025) permettent de doubler l'échantillon sans données payantes. Le point non tranché — et c'est le vrai risque, pas un artefact de méthode — est la survie du mécanisme (flux de fonds mutuels retail) au régime post-2020 de QT et de hikes rapides ; c'est exactement le test de falsification à faire en premier, sur le sous-échantillon 2020-2026 pris isolément, avant d'engager le moindre budget de mods (règle des 3 modifications max).
