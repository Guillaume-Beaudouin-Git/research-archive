# Axe G — Propagation du choc macro entre classes d'actifs (lead-lag cross-asset)

**Round** : macro_round3_2026-09, axe G. **Statut** : cadrage littérature + spécification, aucun test empirique lancé (contrainte de mission). **Verdict rendu** : aucun — livrable = meilleure version de l'axe + protocole de falsification, conformément au cadrage demandé.

---

## 0. Résumé exécutif

L'idée — après une surprise macro, les classes d'actifs (taux, change, actions) intègrent l'information à des vitesses différentes, et l'ordre est tradable — est **structurellement de la même famille que celle qui a produit L66** : toute hypothèse qui relie plusieurs instruments cotés séparément, sur un horodatage commun, est vulnérable à un artefact de désynchronisation qu'aucun placebo temporel n'attrape. La littérature primaire confirme trois choses utiles :

1. Il existe un ordre documenté et répliqué (obligations > change > actions en amplitude de réaction, Andersen-Bollerslev-Diebold-Vega 2003 et son extension multi-marchés) — mais c'est un résultat d'**amplitude**, pas explicitement de **vitesse relative** cross-asset au sens d'un décalage tradable.
2. Le canal de transmission le mieux documenté (Evans-Lyon, flux d'ordres) démontre un ajustement progressif et une prévisibilité **hors échantillon réelle** — mais à un horizon de **10 jours à 3 semaines**, et **à l'intérieur d'une seule classe d'actifs** (le change se prédit lui-même via son propre flux d'ordres). Aucun papier trouvé dans cette recherche n'établit un canal de flux d'ordres CROSS-classe (ex. flux d'ordres obligataire prédisant le change) à un horizon tradable.
3. Les indices de connectivité (Diebold-Yilmaz) montrent que la **direction** de la transmission n'est PAS stable : elle s'intensifie et se retourne en régime de stress, et un papier déjà repéré dans le pipeline `alpha_hunt` du dépôt (network reconfiguration crypto-équity, régime-dépendant) le confirme sur un panel adjacent.

**Conséquence pour la conception** : la version la plus défendable de cet axe n'est PAS un lead-lag intraday haute fréquence (zone de contamination maximale, L66), mais un pari sur la **vitesse d'ajustement à l'échelle du jour-à-la-semaine**, ancré sur le canal d'attention limitée / capital lent (Duffie 2010, Hendershott-Li-Menkveld-Seasholes 2022), qui est explicitement calibré à cette fréquence et PAS à la microstructure intraday. C'est aussi la seule fréquence où le véhicule (CFD/futures retail, ~13k€) a une chance économique : un lead-lag intraday exige une exécution à la seconde et paie le spread des deux côtés, sur un book qui n'a ni la latence ni le tarif institutionnel pour ça.

Le protocole proposé au §6 exige, AVANT tout backtest de rendement, les trois diagnostics non temporels de L66 appliqués à cet axe précis, plus un test de décalage supplémentaire qui n'existe pas dans L66 (le test de **substituabilité du proxy**, §6.4) parce qu'ici — contrairement à la coherence FX de L66 — les trois pattes ne sont pas trois cotations du même sous-jacent, donc le mécanisme de péremption différentielle ne peut pas se manifester à l'identique. Cette différence est argumentée explicitement au §2, pas supposée.

---

## 1. Balayage du dépôt — ce qui existe et ce que ça tue ou ne tue pas

Commande exécutée : `grep -ril "lead-lag\|leadlag\|propagation\|spillover\|cross-asset" --include='*.md' .` (hors `.git`), puis lecture de `research_history.md` et `_meta/lessons_registry.md`.

**Ce qui existe et qui est ADJACENT mais ne teste PAS cet axe :**

- `Forex/research/active/g2d_carry_cross_asset/` (report_v0, report_v1) — pivot Koijen-Moskowitz-Pedersen-Vrugt 2018, carry cross-asset (across equity/FX/bonds/commodities). C'est une prime de **portage**, pas un **délai d'ajustement à un choc**. Mécanisme différent, aucun recouvrement de test.
- `Multi_Asset/research/active/macro_score_2026-09/01_academique/RAPPORT.md` et `Multi_Asset/research/active/macro_round2_2026-09/E_nowcast_consensus/RAPPORT.md` — citent déjà **Andersen-Bollerslev-Diebold-Vega (2003)** et son extension multi-marchés (« les marchés obligataires réagissent le plus fortement aux nouvelles macro, suivis du FX, puis des actions »). C'est le socle empirique de l'ordre inter-classes, déjà dans le dépôt — je le reprends ici mais je ne le re-découvre pas, et je vais plus loin (le point non couvert par les rounds précédents : est-ce que cet ordre d'AMPLITUDE implique un ordre de VITESSE exploitable, et à quel horizon).
- `Multi_Asset/research/active/macro_round2_2026-09/E_nowcast_consensus/RAPPORT.md` §8(c) — pose déjà le test de corrélation croisée entre séries macro pour vérifier le N_eff de breadth (motivé par L12b). Directement réutilisable ici si l'axe avance (§6.5).
- `_automation/arxiv/2026-07-03_analysis.md` — paper sur la rupture du trend cross-asset post-2009 par « vitesse de signal et classe d'actif » : sujet voisin dans le vocabulaire, mais porte sur la **dégradation du momentum**, pas sur un lead-lag entre classes. Non pertinent directement.
- `_automation/alpha_hunt/promising/arxiv_econ_em_when_market_boundaries_weaken_crypto_cross_20260621.md` (arXiv 2605.30442) — **directement pertinent** pour le point 3 de la mission (stabilité de la direction de connectivité) : panel crypto/FX/actions 2017-2024, connectivité VAR + réseaux de corrélation glissante, résultat central = la connectivité s'**intensifie en régime turbulent** et la communauté crypto migre vers la communauté actions au fil du temps. Ce papier est actuellement classé `TEST_LATER` pour un usage de kill-switch de la Strategy B (delta-neutral), PAS pour cet axe — je le réutilise ici pour sa conclusion méthodologique (direction non stable), sans dupliquer son usage prévu.

**Ce qui n'existe PAS dans le dépôt** : aucun test empirique, préenregistré ou non, d'un lead-lag directionnel entre classes d'actifs suite à une surprise macro (taux→change→actions ou l'inverse). Aucune fiche kill, aucun POSTMORTEM, aucun n_test consommé sur cette hypothèse précise. **L'axe est neuf.** (Contrairement à l'avertissement de la mission comme quoi une session précédente aurait recommandé un axe déjà testé faute d'avoir balayé — ce risque ne se matérialise pas ici sur la base du grep exécuté ; le risque analogue le plus proche est plutôt que L66 s'applique PAR FAMILLE, pas par citation exacte, ce qui est traité en détail au §2.)

**Ce que L66 tue et ne tue PAS ici** — traité en détail au §2, mais le résumé : L66 tue la **méthode naïve** (rééchantillonner obligations/change/actions sur un horodatage commun et lire l'écart comme un signal), pas l'**hypothèse économique** (les classes intègrent l'info à des vitesses différentes). C'est un point de méthode, pas un verdict sur l'existence du phénomène.

---

## 2. Traitement frontal de la mise en garde L66

### 2.1 Pourquoi l'axe est *a priori* dans la zone de danger de L66

L66, gravée le 2026-09-02, dit noir sur blanc : « Dès qu'une hypothèse relie plusieurs instruments cotés séparément, un placebo temporel (décalage, permutation, bootstrap) est INSUFFISANT : il préserve la structure de péremption qu'il devrait tester. » Un lead-lag rates→FX→actions relie, par construction, trois instruments cotés sur trois venues différentes (marché obligataire OTC/futures, marché des changes OTC, marché actions/indices coté). C'est la définition même de la famille où vit le piège.

Le mécanisme précis de L66 était : sur une grille de cohérence triangulaire FX, l'écart mesuré prédisait dans les DEUX sens (la croisée prédit les majeures ET les majeures prédisent la croisée, avec des signes opposés), parce que le « dernier print » de chaque patte a un âge différent dans le même bin — ce n'est pas de l'information qui se propage, c'est un décalage d'horloge de cotation qui se résorbe à la barre suivante.

### 2.2 Ce qui est structurellement DIFFÉRENT ici — et pourquoi ça ne suffit pas à écarter le risque

Argument à charge (pourquoi on pourrait croire l'axe protégé) : dans L66, les trois pattes sont des **fonctions déterministes les unes des autres** (une croisée EUR/GBP = EUR/USD × USD/GBP par no-arbitrage), donc n'importe quel décalage de cotation entre les trois crée mécaniquement un écart mesurable — la « prédictibilité » est un artefact de calcul, pas de marché. Un contrat à terme sur taux (ZN), une paire de change (6E) et un indice actions (ES) n'ont **aucune relation d'arbitrage déterministe** de ce type : il n'y a pas d'identité comptable entre eux. Donc le canal spécifique de L66 (extraction d'un résidu de non-arbitrage entre cotations d'un même objet économique) ne s'applique pas littéralement.

Argument à charge inverse (pourquoi ça ne suffit pas) : le mécanisme profond de L66 n'est PAS spécifique à l'arbitrage triangulaire — c'est la **non-synchronicité de cotation en général** (la famille Epps / Scholes-Williams 1977 / Lo-MacKinlay 1990, citée dans L66 elle-même). La littérature microstructure confirmée dans cette recherche le dit explicitement : le phénomène de lead-lag intraday « n'est pas constant dans la journée » et change précisément « aux annonces macro et à l'ouverture du marché US » (cf. §3.5) — c'est-à-dire exactement les moments où cet axe cherche à mesurer un effet. Trois marchés à des horaires de session, de liquidité et de fréquence de cotation différents (le marché des changes cote en continu 24h, les futures de taux ont une session Globex avec pause de règlement, les indices actions ont une session cash) **auront systématiquement des "derniers prints" d'âges différents** au moment où on les échantillonne sur un horodatage commun — exactement l'ingrédient qui a produit L66. La destruction de l'identité comptable retire une SOURCE d'artefact (le calcul déterministe), pas la source PRINCIPALE (le décalage de fraîcheur de cotation entre venues asynchrones).

**Conclusion de cette section** : l'axe n'est pas *automatiquement* condamné par L66, mais il n'est pas non plus protégé par construction. Il doit être traité avec exactement les diagnostics prescrits, adaptés à sa structure.

### 2.3 Les trois diagnostics de L66, appliqués à cet axe précis

**(a) Test de saut — décaler d'une barre supplémentaire.**
Appliqué ici : si le décalage optimal mesuré est, disons, +1 jour (les taux bougent le jour J, le change intègre le jour J+1), le test consiste à comparer l'effet à horizon J+1 contre horizon J+2 contre horizon J+3. **Signature attendue si c'est de l'information réelle** : l'effet décroît progressivement (une nouvelle économique se dissipe sur plusieurs jours, cf. Kroner 2025 §3.4 — mais PAS un effondrement brutal). **Signature attendue si c'est un artefact de désynchronisation** : l'effet s'effondre presque entièrement au décalage supplémentaire suivant (L66 mesure 6%/46%/23% de fraction conservée) parce qu'un défaut de synchronisation entre deux séries se résorbe dès que les deux séries ont eu le temps de rattraper leur horloge — ce qui, à l'échelle JOURNALIÈRE (contrairement à l'échelle intraday de L66), demande de vérifier un pas plus fin : décaler d'une SESSION (pas juste d'un jour calendaire), car la fenêtre 18:00 ET → 17:00 ET des futures de taux (L51/L52) n'est pas alignée sur la session cash actions ni sur le cycle continu du FX. **Ce test doit comparer le décalage à l'échelle de la SESSION de l'instrument, pas du jour calendaire** — directement motivé par L52 (« yfinance ZN=F.Open = ouverture Globex 18:00 ET du jour PRÉCÉDENT »), qui a déjà piégé une lecture naïve de calendrier sur ce même instrument dans ce dépôt.

**(b) Décomposition par patte — l'écart prédit-il AUSSI les deux autres pattes, avec un signe incohérent ?**
Dans L66, l'écart de cohérence triangulaire prédisait ses trois pattes constitutives avec des signes contradictoires — signature d'un mécanisme qui « ne sait pas » laquelle des trois cotations est périmée. Ici, l'analogue est : si le signal « rates ont bougé, change n'a pas encore bougé » prédit un mouvement du change, il faut vérifier que le signal symétrique « change a bougé, actions n'ont pas encore bougé » ne produise pas une prédiction dont le signe implique une INCOHÉRENCE avec la première (ex. la même surprise macro impliquant simultanément un délai rates→FX ET un délai FX→rates dans le sens opposé, ce qui reviendrait à dire que chaque marché est systématiquement en retard sur l'autre — impossible économiquement, signature d'artefact). C'est le test le plus discriminant pour cet axe précis parce que la mission demande un ORDRE (rates→FX→actions OU l'inverse) : un ordre cohérent doit être TRANSITIF (si rates mène FX et FX mène actions, alors rates doit mener actions avec un délai plus long, pas un délai contradictoire) — un test de transitivité additionnel, propre à cet axe, à ajouter au triptyque L66.

**(c) Reconstruction TWAP au lieu du dernier print.**
Directement transposable : rééchantillonner chaque classe (taux, change, actions) en TWAP (ou VWAP si volume disponible) sur la fenêtre de bin plutôt qu'en dernier print, et vérifier si l'effet de lead-lag survit. Si le triangle le plus fort de la grille (par analogie avec L66) s'effondre ou change de signe sous TWAP, c'est un artefact de fraîcheur de cotation. **Contrainte de faisabilité à noter honnêtement** : contrairement au FX où yfinance/Dukascopy donnent des cotations tick, un TWAP correctement construit sur les futures de taux ET sur les indices actions ET sur le change, aux MÊMES fenêtres, demande une donnée intraday synchronisée sur les trois classes — actuellement `data/deep_history_utc/` couvre FX et indices (M1, true UTC), mais pas de couverture confirmée pour les futures de taux (ZN) à cette granularité dans l'inventaire data du dépôt. **Ce test peut être bloqué par la donnée, pas seulement par la méthode** — à vérifier avant de lancer un backtest (§6.1, prérequis data).

### 2.4 Réponse à (b) — à quelle granularité l'axe cesse-t-il d'être contaminé

Synthèse des trois diagnostics ci-dessus et de la littérature (§3) : **l'axe cesse d'être contaminé par le mécanisme de L66 dès que l'échelle de mesure est strictement plus grande que l'écart typique entre horaires de clôture/liquidité des trois classes.** Concrètement :

- **Intraday (minutes à quelques heures)** : zone de contamination maximale. C'est exactement l'échelle où (i) les trois marchés ont des horaires de session, de liquidité et de fréquence de cotation les plus différents entre eux (FX continu, taux avec pause de règlement Globex, actions cash 6h30/j) ; (ii) la littérature confirme que le lead-lag intraday n'est PAS stable dans la journée et change de comportement précisément aux annonces macro et à l'ouverture US (§3.5) — c'est-à-dire que la fenêtre où on veut mesurer l'effet économique est aussi la fenêtre où l'artefact de non-synchronicité est le plus actif. **Ne pas tester ici sans TWAP + test de transitivité validés en amont.**
- **Journalier (close-to-close, 1 jour)** : zone grise. C'est l'échelle par défaut de la littérature d'attention limitée / capital lent (Duffie 2010, Hendershott-Li-Menkveld-Seasholes 2022 — « corrélations contemporaines, en avance et en retard aux fréquences quotidienne, hebdomadaire, bihebdomadaire et mensuelle »), donc c'est l'échelle où le MÉCANISME ÉCONOMIQUE proposé est censé opérer. Mais c'est aussi l'échelle où L52 a déjà piégé une lecture naïve de « close » sur CE MÊME instrument (ZN) dans ce dépôt — un close journalier mal daté (settlement 15:00 ET vs clôture cash 16:00 ET vs minuit UTC) reproduit une version light du problème L66. **Testable, mais seulement avec les mêmes horaires de settlement tick-matchés entre les trois classes (discipline déjà exigée par L52).**
- **Hebdomadaire ou plus lent** : hors zone de contamination de L66 par construction (l'échelle de désynchronisation de cotation, de l'ordre de la minute à l'heure, devient négligeable face à un horizon de plusieurs jours), mais c'est aussi l'échelle où Evans-Lyon (§3.2) situe leur prévisibilité OOS réelle (10-20 jours) — cohérence encourageante entre le mécanisme économique documenté et l'échelle protégée de l'artefact.

**Verdict de granularité (réponse explicite à la demande b)** : l'axe n'est jamais protégé par construction, mais il est SEULEMENT défendable à l'échelle **journalière avec horaires de settlement alignés, ou plus lente** — jamais à l'intraday sans les trois diagnostics validés en amont. C'est cohérent avec le fait que le mécanisme économique invoqué (attention limitée, capital lent) est lui-même documenté à cette échelle, pas en intraday — ce n'est donc pas une concession arbitraire, c'est le point où littérature et prudence méthodologique convergent.

### 2.5 Réponse à (c) — l'axe est-il indissociable de l'artefact ?

**Non, pas au vu de cette recherche** — sous deux conditions non encore vérifiées empiriquement (donc à statut PRÉ-REGISTRÉ, pas validé) : (i) l'horizon testé est ≥1 jour avec settlement tick-matché entre classes (§2.4), et (ii) les trois diagnostics de L66 + le test de transitivité (§2.3b) passent. **Si (i) ou (ii) échouent, l'axe DEVIENT indissociable de l'artefact et doit être classé kill MÉCANIQUE — non rouvrable au même angle**, exactement au même titre que la cohérence FX de L66. Ce n'est pas un verdict rendu ici (aucun test lancé), c'est le critère de bascule à appliquer à la première itération empirique.

---

## 3. Littérature primaire

### 3.1 Vitesse (amplitude) d'ajustement différentielle par classe d'actifs

**Andersen, Bollerslev, Diebold & Vega, *Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange*, American Economic Review 93(1), 2003** — six ans de cotations FX temps réel, établit que les surprises d'annonces macro programmées produisent des SAUTS discontinus de la moyenne conditionnelle (pas une dérive lente), avec une réaction asymétrique (mauvaise nouvelle > bonne nouvelle en magnitude). Déjà cité dans le dépôt (`macro_score_2026-09/01_academique`, `macro_round2_2026-09/E_nowcast_consensus`) — je ne le re-découvre pas.

**Extension multi-marchés des mêmes auteurs, *Real-Time Price Discovery in Stock, Bond and Foreign Exchange Markets*, NBER WP 11312** — résultat central pour cet axe : **le marché obligataire réagit le PLUS fortement aux nouvelles macro, suivi du change, puis des actions** — mais en conditionnant sur l'état de l'économie (récession vs expansion), FX et actions deviennent comparables. C'est un ordre d'AMPLITUDE de réaction contemporaine, mesuré à haute fréquence (minutes) — **ce n'est PAS directement un ordre de VITESSE relative (qui intègre en premier)**, et le papier ne le prétend pas. L'extrapolation « bonds réagissent le plus fort donc bonds réagissent le plus vite » est une hypothèse de travail de cette mission, pas un résultat établi dans la littérature trouvée — **à traiter comme hypothèse candidate, pas comme fait acquis**.

**Kroner (Fed Reserve Board, FEDS 2025-022), *How Markets Process Macro News: The Importance of Investor Attention*** — déjà cité dans le dépôt (`E_nowcast_consensus`). Résultat clé additionnel pour cet axe : la fonction de réaction n'est PAS stable dans le temps, elle dépend d'un régime d'attention des investisseurs propre à CHAQUE série macro. Implication directe : un ordre rates→FX→actions mesuré sur un historique complet mélange des régimes d'attention différents par série — **la stabilité de l'ordre lui-même (pas seulement son ampleur) doit être testée en fenêtre glissante**, pas figée sur tout l'historique. C'est un renfort méthodologique direct pour le protocole du §6.

### 3.2 Le canal du flux d'ordres — Evans & Lyon

**Evans & Lyon, *Order Flow and Exchange Rate Dynamics*, JPE 2002 ; *How Is Macro News Transmitted to Exchange Rates?*, et suites (2005, 2007)** — le mécanisme central : l'information macro est transmise au prix du change de façon PROGRESSIVE via le flux d'ordres (les traders hétérogènes interprètent différemment l'annonce, ce qui génère du flux informé qui se résorbe sur plusieurs jours), pas instantanément. **Preuve hors échantillon documentée** : forecastabilité significative à horizon 1 jour à 2-3 semaines (Evans-Lyon 2007), avec la prévisibilité la plus forte à 10-20 jours (Evans-Lyon 2005) — le flux d'ordres bat un random walk sur cet horizon, avec environ un tiers du pouvoir prédictif à 1 mois venant de la capacité du flux à prédire le flux futur (auto-corrélation du flux lui-même, pas une nouvelle information à chaque pas).

**Ce que ce résultat couvre et ne couvre PAS pour cet axe** : c'est une prévisibilité **intra-classe** (le flux d'ordres FX prédit le PRIX FX), à un horizon qui tombe pile dans la zone « protégée » du §2.4 (jours à semaines). **Aucun papier trouvé dans cette recherche n'établit un canal de flux d'ordres CROSS-classe** — ex. le flux d'ordres sur futures de taux prédisant le prix du change, ou le flux d'ordres FX prédisant les actions, à un horizon comparable. C'est un TROU DE LITTÉRATURE identifié, pas un résultat négatif : la mission demande explicitement si le mécanisme Evans-Lyon est « documenté hors échantillon » — la réponse honnête est **oui, mais uniquement pour la prédictibilité INTRA-classe du change par son propre flux ; l'extension cross-classe implicite dans cet axe est une hypothèse non testée dans la littérature repérée**, à traiter comme telle (charge de preuve empirique complète, pas de raccourci de citation).

### 3.3 Spillovers documentés (Diebold-Yilmaz) et stabilité de la direction

**Diebold & Yilmaz (2009, 2012, 2014)** — méthodologie de décomposition de variance en VAR pour mesurer la connectivité directionnelle entre marchés (« qui reçoit / qui transmet » de la volatilité). Application multi-classes (actions, obligations souveraines, CDS, change), 2009-2016 : connectivité totale mesurée à ~5%, relativement FAIBLE en moyenne, mais **spillovers cross-marchés quasi inexistants avant la crise financière 2007-08, puis intensifiés fortement pendant, avec un canal obligations→autres marchés particulièrement marqué après Lehman**. Confirmation directe du point 3 de la mission (**la direction n'est PAS stable, elle change par régime**, et pas seulement en intensité — le SENS dominant de la transmission peut changer).

**Complément trouvé dans le pipeline `alpha_hunt` du dépôt** (arXiv 2605.30442, `_automation/alpha_hunt/promising/arxiv_econ_em_when_market_boundaries_weaken_crypto_cross_20260621.md`) — panel crypto/FX/actions 2017-2024, connectivité VAR + réseaux de corrélation glissante : la connectivité **s'intensifie précisément en régime turbulent**, et une classe d'actifs (crypto) migre structurellement de communauté au fil du temps. Ce papier est un panel différent de celui visé par cet axe (crypto, pas taux), mais la conclusion méthodologique — la structure de connectivité change de régime et de composition, pas seulement d'intensité — est directement transposable et renforce le point 3.

**Implication pour le design (§6)** : un signal de lead-lag calibré sur un historique complet, sans conditionnement de régime, risque de moyenner un régime « rates mènent » et un régime « actions mènent » et de produire un signal proche de zéro en moyenne, ou pire — un signal qui a l'air stable en échantillon complet mais qui inverse de signe par sous-période (signature exactement analogue à L44 : « le contraste cross-sectionnel piloté par le mécanisme est le falsificateur d'IC le moins cher » — ici, tester l'IC séparément en régime calme vs stress est le test le moins cher AVANT tout calibrage de sizing).

### 3.4 Capital lent et attention limitée (Duffie, Hendershott-Li-Menkveld-Seasholes)

**Duffie, *Presidential Address: Asset Price Dynamics with Slow-Moving Capital*, Journal of Finance 2010** — le capital circule vite À L'INTÉRIEUR d'une classe d'actifs, mais LENTEMENT ENTRE classes d'actifs (frictions de recherche, de segmentation réglementaire, fiscale), ce qui génère une déconnexion de court terme du prix du risque entre classes — le patron typique est une réaction brutale au choc puis un renversement étalé, PAS une dérive monotone.

**Hendershott, Li, [Menkveld, Seasholes ou co-auteurs similaires — filename `HLMS.pdf`], *Asset Price Dynamics with Limited Attention*, Review of Financial Studies 35(2), 2022** — extension directe de Duffie (2010) avec market makers + investisseurs attentifs et INATTENTIFS arrivant de façon stochastique (là où Duffie traite des chocs ponctuels type retrait d'indice S&P 500, ce papier traite des chocs répétés, non clairement identifiés, quotidiens). Résultat clé pour cet axe : le modèle est **cohérent avec des corrélations contemporaines, en avance et en retard aux fréquences quotidienne, hebdomadaire, bihebdomadaire ET mensuelle** — c'est-à-dire que le mécanisme économique invoqué par la mission (attention limitée entre classes) est explicitement calibré à ces fréquences, **jamais à l'intraday**. C'est la pièce la plus importante de tout ce cadrage littéraire : elle donne un fondement théorique daté au choix de granularité du §2.4, indépendamment de la contrainte L66.

### 3.5 Le piège en action — littérature microstructure (Epps effect, non-synchronicité)

Confirmation directe, hors du dépôt, du mécanisme derrière L66 : la littérature sur l'effet Epps établit que le lead-lag mesuré entre séries de prix est en partie un ARTEFACT de non-synchronicité de trading — la corrélation mesurée AUGMENTE quand on ne garde que les ticks synchrones. Point le plus utile pour cet axe : le phénomène de lead-lag intraday **n'est PAS constant dans la journée et change de comportement précisément aux publications macro et à l'ouverture US** — les deux moments qui intéressent le plus cet axe sont statistiquement les moments où l'artefact de non-synchronicité est documenté comme le plus actif. Ce n'est pas une coïncidence gênante à ignorer, c'est la confirmation externe la plus directe que L66 s'applique ici par défaut à l'intraday, et le motif principal du verdict de granularité au §2.4.

---

## 4. Granularité — synthèse opérationnelle

| Fréquence | Statut vis-à-vis de L66 | Fondement littérature | Verdict |
|---|---|---|---|
| Tick / minutes | Contamination maximale documentée (Epps, changement de comportement aux annonces/ouverture US) | Aucun mécanisme économique daté à cette échelle | **Ne pas tester sans TWAP + transitivité validés** |
| Intraday (heures) | Zone grise, horaires de session désalignés entre les 3 classes | Idem | **Déconseillé en première itération** |
| Journalier, close aligné par settlement | Zone grise réduite si horaires tick-matchés (discipline L52) | Duffie 2010 (choix d'exemples ponctuels), HLMS 2022 (quotidien = fréquence native du modèle) | **Fréquence recommandée pour la première itération** |
| Hebdomadaire+ | Hors zone de contamination par construction | Evans-Lyon (10-20j), HLMS (hebdo/bihebdo/mensuel) | **Fréquence de repli si le journalier échoue au test de transitivité** |

---

## 5. Le véhicule et les coûts — chiffré tôt, comme demandé

Compte de référence : ~13k€, CFD retail ou futures (mêmes contraintes que le reste du dépôt — pas de CME futures accessibles en propfirm FTMO, compte perso IBKR disponible en première classe depuis L53).

**Un lead-lag intraday** exige une exécution proche de la latence machine et paie le spread des DEUX côtés du trade à chaque jambe (entrée sur la classe en retard, éventuellement couverture ou sortie sur la classe en avance) : au tarif CFD retail mesuré ailleurs dans ce dépôt (L23b, L33, L43 : 2-7 bps RT par jambe, tier institutionnel 0.5-1.5 bps hors de portée retail), un trade à 2 jambes coûte déjà 4-14 bps RT, un trade à 3 jambes 6-21 bps RT — **face à un gross par trade qui, dans la littérature repérée, n'est jamais chiffré au-delà de quelques bps sur l'horizon intraday** (aucun chiffre agrégé cité par ABDV ; L43 mesure un gross exploitable FX sub-bps en intraday-flat). **Le pré-flight L43 (gross/coût ≥ 1.5, meilleur observé 0.36 sur FX pur) s'applique ici a fortiori** — un lead-lag cross-asset intraday hérite du même ordre de grandeur de coût que le FX intraday déjà fermé (L43), avec en plus 2-3 jambes au lieu d'une.

**Au journalier, sur futures** (ZN pour les taux, 6E ou M6E pour le change, ES/MES pour les actions) : coût round-trip proche de 0.4-1 bp par jambe (cf. Costs §CLAUDE.md, futures ~0.01% RT canonique ; L57 nuance à la baisse pour les gros contrats, à la hausse en bps sur les micro-contrats à faible notionnel). Pour 3 jambes, ~1.2-3 bps RT total — un ordre de grandeur largement plus favorable que le CFD 3-jambes. **Contrainte de marge** : marge combinée approximative 1 ZN (~1800$) + 1 6E (~2500$) + 1 MES (~1300$) ≈ 5600$, soit ~40% d'un compte de 13k€ (~14k$) — faisable en notionnel unitaire, mais **incompatible avec du vol-targeting fin** (L57 : « 1 lot ou rien coûte 0.35 de Sharpe, retourne le skew +0.99→-0.49 ») si le sizing doit varier par jambe selon la conviction du signal — problème de granularité de lot, pas de coût, à traiter distinctement.

**Verdict de véhicule** : le journalier sur futures (ZN/6E ou M6E/MES) est économiquement défendable en coût ; le CFD retail intraday ne l'est probablement pas (même ordre de grandeur d'échec que L43, en pire à 2-3 jambes). Le compte perso IBKR reste le véhicule de première classe (L53) — pas de propfirm crypto/CFD compatible avec cet axe de toute façon (aucune des classes visées n'est acceptée en delta-neutral crypto/CFD chez les propfirms de la maison).

---

## 6. Design de la meilleure version testable — protocole complet

### 6.1 Prérequis data (à vérifier AVANT tout code)
Confirmer la disponibilité, dans `data/` ou via téléchargement futur, de séries journalières avec horaires de settlement documentés et tick-matchables pour : futures de taux US (ZN ou équivalent), une paire de change majeure liquide (EURUSD ou DXY-proxy), un indice actions (ES/SPX). **Ne pas supposer que `data/deep_history_utc/` couvre les taux** — l'inventaire cité dans CLAUDE.md ne mentionne que FX et indices à cette granularité ; un futures de taux journalier existe probablement via yfinance (`ZN=F`) mais avec le piège L52 déjà documenté (Open = ouverture Globex jour précédent).

### 6.2 Spécification du signal (hard rules maison respectées)
- Signal à T-1, trade à T (hard rule).
- Rendements EXCESS (vs cash rate), HAC lag-6 (hard rule).
- Surprise macro = (réalisé − consensus) / écart-type historique de la surprise sur la série (standardisation minimale pour comparer across événements).
- Fenêtre d'intégration testée en walk-forward ≥5 folds expanding (hard rule) — **jamais un split unique**.
- Le décalage optimal (jours) entre classes est un PARAMÈTRE À ESTIMER, pas fixé a priori — mais préenregistré comme grille discrète (ex. J+0, J+1, J+2, J+3) avant tout test, pour éviter le raffinage post-hoc.

### 6.3 Ordre des tests — protocole séquentiel, chaque étape gratuite avant la suivante
1. **Test de stabilité de l'ordre par régime** (motivé par §3.3/3.4) : split calme vs stress (proxy VIX ou réalisée), vérifier que l'ordre rates→FX→actions (ou l'inverse) est le MÊME dans les deux régimes. Si l'ordre s'inverse par régime, condition IC nécessaire pour la suite — spécifier laquelle AVANT de continuer, ne pas la découvrir a posteriori (évite le piège L54 : le régime prédisant la variance doit prédire la moyenne dans le même sens, pas être ajouté après coup pour sauver l'IC).
2. **Test de transitivité** (§2.3b, nouveau par rapport à L66) : si rates→FX à délai d1 et FX→actions à délai d2 sont tous deux positifs et significatifs, rates→actions direct doit être cohérent avec d1+d2 (délai plus long, signe cohérent). Incohérence ⇒ kill mécanique immédiat, ne pas continuer.
3. **Test de saut à l'échelle de la session** (§2.3a) : décaler d'une session Globex/cash supplémentaire, mesurer la fraction d'effet conservée. Effondrement (<~25%, seuil L66) ⇒ artefact de désynchronisation, kill mécanique.
4. **TWAP vs dernier print** (§2.3c) : si la donnée le permet (voir §6.1). Effondrement ou inversion de signe ⇒ kill mécanique.
5. **Seulement si 1-4 passent** : test IC formel (HAC lag-6, seuil t>2.5 conforme au toolkit maison), walk-forward ≥5 folds, AMTP/Šidák si plusieurs paires de classes testées simultanément (probable : rates→FX, rates→actions, FX→actions = 3 tests minimum, donc AMTP obligatoire dès le départ, pas seulement si l'un d'eux passe).
6. **Test d'orthogonalité** (style L38) : régresser le P&L de la sleeve sur un buy-and-hold vol-targeté de la classe tenue — R²>30% ⇒ ce n'est pas un lead-lag, c'est du bêta déguisé (risque particulièrement plausible ici car « acheter des actions après que les taux ont bougé » ressemble structurellement à un simple market-timing sur le risque global).
7. **Coût et véhicule** (§5) : gate gross/coût ≥1.5 (style L43) avant tout sizing.

### 6.4 Test additionnel propre à cet axe — substituabilité du proxy
Différence avec L66 : ici, chaque classe a PLUSIEURS instruments substituables (ZN vs ZB vs ZF pour les taux ; EURUSD vs DXY vs 6E pour le change ; ES vs YM vs NQ pour les actions). Si l'effet mesuré est un vrai lead-lag économique, il doit être robuste au choix de l'instrument DANS la classe (résultat qualitativement semblable sur ZN et sur ZF, par exemple). Si l'effet est spécifique à un seul instrument précis et disparaît en changeant de proxy dans la même classe, c'est le signe d'un artefact de microstructure propre à CET instrument (liquidité, heures de cotation spécifiques), pas d'un phénomène économique cross-classe.

### 6.5 Test de breadth réelle (réutilisation directe de E_nowcast_consensus §8c)
Si plusieurs événements macro sont agrégés pour la breadth (façon axe E du round2), vérifier la corrélation croisée des surprises dans le même mois — évite de répéter le mécanisme L12b (demi-vie longue → N_eff effondré) sous sa forme cross-sectionnelle.

---

## 7. Ce qui falsifierait l'axe — liste préenregistrée

1. **Kill mécanique par L66 direct** : le test de saut à l'échelle session (§6.3.3) ou le TWAP (§6.3.4) effondre l'effet — **non rouvrable au même angle** (politique de réouverture du dépôt : un kill mécanique reste fermé).
2. **Kill mécanique par transitivité** (§6.3.2) : incohérence de signe entre les trois lead-lags pairwise — signature d'artefact, non rouvrable.
3. **Kill par instabilité de régime sans conditionneur pré-spécifié** (§6.3.1, §3.3) : l'ordre s'inverse par régime et aucun conditionneur économiquement motivé (pas ajouté a posteriori, cf. L54) ne le rattrape — rouvrable seulement sous la catégorie « géométrie/conditionnement », pas au même angle brut.
4. **Kill par substituabilité** (§6.4) : l'effet ne survit pas au changement de proxy dans la même classe — artefact d'instrument, non rouvrable pour cet instrument précis, potentiellement rouvrable sur un autre proxy si le mécanisme causal proposé change.
5. **Kill par orthogonalité** (§6.3.6, style L38) : R²>30% avec un buy-and-hold vol-targeté — ce n'est pas un lead-lag, c'est du bêta ; rouvrable seulement avec un signal explicitement neutralisé du bêta directionnel.
6. **Kill par coût** (§5) : si le journalier futures ne passe pas le gate gross/coût ≥1.5 — rouvrable (catégorie « coût », §politique de réouverture) si un jour le tarif institutionnel devient accessible, mais pas au tarif retail actuel.
7. **Kill par manque de puissance** (§6.1) : donnée taux journalière insuffisamment longue ou mal datée (piège L52) pour atteindre 5 folds walk-forward — rouvrable dès qu'une source de donnée correctement datée est identifiée (catégorie « puissance »).

**Ce qui validerait l'axe, a minima** : les 4 diagnostics mécaniques (1-4) passent, l'ordre est stable par régime OU conditionné explicitement, R²<30% à l'orthogonalité, gross/coût ≥1.5 au journalier futures, et un IC HAC t>2.5 après AMTP sur au moins une paire de classes avec un walk-forward ≥5 folds positif sur ≥3/5 folds (norme reprise du test Diebold-Mariano de l'axe E, cohérente avec la discipline maison).

---

## 8. Sources

- Andersen, Bollerslev, Diebold & Vega, *Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange*, AER 93(1), 2003 — https://www.aeaweb.org/articles?id=10.1257/000282803321455151 ; https://www.nber.org/system/files/working_papers/w8959/w8959.pdf
- Andersen, Bollerslev, Diebold & Vega, *Real-Time Price Discovery in Stock, Bond and Foreign Exchange Markets*, NBER WP 11312 (extension multi-marchés, déjà citée dans le dépôt)
- Kroner, *How Markets Process Macro News: The Importance of Investor Attention*, FEDS 2025-022 — https://www.federalreserve.gov/econres/feds/how-markets-process-macro-news-the-importance-of-investor-attention.htm
- Evans & Lyon, *Order Flow and Exchange Rate Dynamics*, JPE 2002 — https://faculty.georgetown.edu/evansm1/wpapers_files/orderflow.pdf
- Evans, *How Is Macro News Transmitted to Exchange Rates?* — https://haas.berkeley.edu/wp-content/uploads/Announcements.pdf
- Evans & Lyon, *Understanding Order Flow*, 2005/2006 — https://faculty.georgetown.edu/evansm1/wpapers_files/understandingv3.pdf ; https://onlinelibrary.wiley.com/doi/10.1002/ijfe.287
- Evans, *Exchange Rate Forecasting, Order Flow and Macroeconomic Information* — https://faculty.georgetown.edu/evansm1/conference/Panel%20OF%2016.pdf
- Diebold & Yilmaz, méthodologie spillover/connectedness — synthèse *On the Past, Present, and Future of the Diebold-Yilmaz Approach*, arXiv 2211.04184 — https://arxiv.org/pdf/2211.04184
- Application multi-classes (actions/obligations/CDS/change 2009-2016) — https://www.sciencedirect.com/science/article/abs/pii/S0927538X18305912
- *When market boundaries weaken: Network reconfiguration and regime-dependent cross-asset spillovers*, arXiv 2605.30442 — https://arxiv.org/pdf/2605.30442 (déjà dans le pipeline `alpha_hunt` du dépôt, `_automation/alpha_hunt/promising/arxiv_econ_em_when_market_boundaries_weaken_crypto_cross_20260621.md`)
- Duffie, *Presidential Address: Asset Price Dynamics with Slow-Moving Capital*, Journal of Finance, 2010 — https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2010.01569.x
- Hendershott, Li et al., *Asset Price Dynamics with Limited Attention*, Review of Financial Studies 35(2), 2022 — https://academic.oup.com/rfs/article/35/2/962/6226477 ; https://faculty.haas.berkeley.edu/hender/Limited_Attention.pdf
- Lead-lag / effet Epps, non-synchronicité intraday et changement de comportement aux annonces macro / ouverture US — *High Frequency Lead/lag Relationships - Empirical facts* https://ideas.repec.org/p/hal/wpaper/hal-00645685.html ; *On the origin of the Epps effect* https://arxiv.org/pdf/physics/0701110
- Fernandez-Perez et al., *Cross-Asset Time-Series Momentum: Crude Oil Volatility* (canal OVX→équities, Granger causality) — https://acfr.aut.ac.nz/__data/assets/pdf_file/0012/686829/1b-XTSMOM_Fernandez-Perez-et-al.,-2022-DMC.pdf
- Repère interne : `_meta/lessons_registry.md` L66 (texte intégral cité §2.1) ; `CLAUDE.md` §Costs, §L51-L57 (véhicule futures, granularité de lot, coûts)
