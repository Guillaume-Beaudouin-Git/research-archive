# Taxonomie d'hypothèses par profil de distribution — FTMO CFD 2-step

**Statut : N0 (screening/conception). Zéro backtest exécuté. Zéro `n_tests` consommé.**
Ce document classe des hypothèses par **forme de distribution attendue face à une barrière
journalière**, pas par promesse de Sharpe. Toute mesure appartient à une session ultérieure,
pré-enregistrée, sur le compte de `n_tests` réel.

**Sources consultées** : `CLAUDE.md` (constitution, registre L11-L60), mémoires de session
(`~/.claude/projects/.../memory/*.md`), et surtout deux artefacts très récents (2026-07-30) qui
changent la donne par rapport à un screening à froid :
- `Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.md` — fouille exhaustive de 118
  edges mesurés dans tout le repo, classés par cause de mort (mécanique/puissance/coût/géométrie/
  véhicule/données) et par ré-ouvrabilité.
- `Multi_Asset/research/active/decorrelated_sleeves_2026-07/` — trois pistes MR/range/stat-arb
  testées **spécifiquement pour FTMO** il y a trois semaines, avec le même vocabulaire two-sided/
  délai+1/DSR que ce document emploie, et falsifiées mécaniquement.

Ces deux artefacts changent la mission : une bonne partie de ce que le brief demande d'explorer a
**déjà été exploré**, sous des formes plus rigoureuses qu'un simple z-score (OU half-life, ADX+
bandwidth causal, RSI2/RSI14/Bollinger %b, causal-vs-oracle). La contribution de ce document n'est
donc pas de re-proposer un premier passage — c'est de (a) dire honnêtement ce qui est déjà mort et
pourquoi ce n'est pas la peine de le retester, (b) isoler les formulations **mécanistiquement
distinctes** qui n'ont pas encore été essayées, et (c) signaler que la famille la plus prometteuse du
repo entier n'est ni la MR ni la microstructure de session au sens étroit — c'est une famille que le
cadrage du brief pré-disqualifie à tort.

---

## 1. Le filtre de profil — ce qu'il élimine, et mon désaccord

### 1.1 Le filtre tel que posé

| # | Exigence | Ce qu'elle élimine |
|---|---|---|
| 1 | Queue gauche courte (kurtosis excessive négative disqualifiante) | Tout ce qui accumule un petit edge régulier puis blow-up rare (short-vol, carry, martingale) |
| 2 | Intraday-flat OU gross ≫ swap | Tout portage tenu dont le carry agrégé mange la prime (L36) |
| 3 | Si intraday-flat : gross > 3 bps | Tout micro-signal retail sub-bps (L33b, L43, L34) |
| 4 | Fréquence suffisante mais contrainte **relâchée** (pas de mur de temps) | Rien — c'est un assouplissement, pas une exclusion |

C'est un bon filtre. Il élimine correctement, et pour des raisons **déjà mesurées dans ce repo** :
short-vol (VRP réel −0.37 à −0.51 sur données réelles), carry FX/commodity (mort post-GFC, un-
collectable côté retail L32/L32b), stat-arb de spread classique (financing 2× markup L28, piège de
beta hérité L27).

### 1.2 Où je suis en désaccord — trois points, chacun soutenu par une mesure existante

**(a) « Momentum/trend disqualifié » est vrai pour le trend swing, faux pour la dérive de session
ancrée à l'horloge d'échange.** Le brief regroupe momentum/trend comme une seule famille
disqualifiée par le profil (win-rate bas, win/loss élevé, L24 : plafond structurel ~44-54 % sous
barrière symétrique). C'est exact pour le TSMOM multi-jours classique — `edge_inventory` le confirme
: M047 (TSMOM multi-actifs FTMO, le moteur du book) a un gross ~0.9 mais un **net 0.0** une fois le
portage agrégé soustrait (L36), et le re-test sur futures ne donne que SR 0.35-0.47 (drought de trend
moderne, cohérent AQR). Mais la **dérive de session ancrée à l'horloge d'échange** (or/argent/WTI
overnight, réouverture Globex 18:00 ET) n'est **pas** du trend-following : c'est un flux de
rééquilibrage récurrent, à faible bêta (R² 0.001-0.002 mesuré, β_or 0.004), avec **le t-stat le plus
élevé du repo entier hors month-end** (E002 or overnight t_HAC 4.82, DSR 0.99, WF 5/5 ; E003 argent
t 4.55 DSR 1.00 ; E004 WTI t 3.64 DSR 0.94). Le `edge_inventory` classe ces trois entrées comme
**GÉOMÉTRIE + VÉHICULE**, jamais mécanique : elles ont été jugées « FTMO NON-VIABLE » uniquement à
cause (i) du mur de 91 jours **auto-imposé** (que ce brief demande justement de relâcher), (ii) de la
barrière journalière percée à un vol-targeting agressif (résoluble par un vol-targeting plus prudent,
pas par le signal), (iii) de la dilution en panier plutôt qu'en sleeve autonome. **Sous le cadrage
exact de ce brief (pas de mur de temps, profil de distribution d'abord), cette famille n'est pas une
hypothèse à concevoir — c'est une ré-ouverture déjà instruite, avec le test décisif déjà écrit.** Je
la place en tête de la section microstructure de session (§3.2, formulation 2.1) plutôt que de la
laisser disqualifiée sous l'étiquette « momentum ».

**(b) Le breakout n'est pas mal formé, il est vide — deux diagnostics différents.** ORB/Crabel/NR7
sont exclus par le brief sur la base du profil de distribution. Mais la mesure existante (`ORB
structure diagnostic`) montre une distribution **skew +1.78, kurt +11.29** — une queue droite grasse,
pertes bornées par le stop — c'est-à-dire **exactement** la forme qu'une barrière journalière
récompense (le risque baissier est plafonné, l'upside est convexe). Le problème n'est pas la forme,
c'est que l'edge per-trade est **nul** une fois le coût et le délai+1 correctement pricés (L59 : les
sorties bracket perdent 25 % de leur edge à la re-pricing exacte du stop ; DSR per-trade FAIL sur
toutes les variantes testées). Conclusion pratique différente du brief : je ne recommande pas de
chasser un « meilleur ORB » (le repo l'a fait ~8 fois, toujours DSR-FAIL), mais je ne l'exclus pas non
plus de la taxonomie — je le garde comme **infrastructure de ballast** (le book actuel documente ORB
comme le socle d'éligibilité en jours de trading, +81.8 pt marginal sur le p(pass) via la couverture
de jours, pas via le P&L). Ce n'est pas une famille à concevoir, c'est une ligne de produit déjà
comprise à conserver telle quelle.

**(c) L'événementiel tenu n'est pas uniformément mort — mais chaque instance testée l'est, pour trois
raisons différentes (régime, mécanisme absent, artefact de fenêtre), et cette hétérogénéité est un
signal que la famille reste ouverte en principe, fermée en pratique sur tout ce qui a été essayé.**
Pré-FOMC GER40/US30 : effet de régime (pré-2020 t 0.01). Cycle d'adjudication Treasury : jambe du
mécanisme absente (concession pré-adjudication t 0.48). Pré-CPI : porté par une année aberrante (2025
+121 bps). Aucun de ces trois n'est un kill de **profil de distribution** — je suis d'accord avec le
brief que l'événementiel tenu est disqualifié par le **profil** (tenir une position à travers un
événement macro programmé = s'exposer précisément au moment où la kurtosis de la barre spike), mais
je note que ce n'est pas la seule raison de sa mort empirique ici — les trois raisons réelles sont
mécaniques et ne se rouvriraient pas même si le profil était acceptable. Je le laisse fermé.

### 1.3 Où j'ajoute une nuance au filtre lui-même

Le filtre suppose implicitement que « intraday-flat » et « held avec gross≫swap » sont les deux seules
voies. Il en existe une troisième, invisible dans le cadrage du brief mais présente dans le repo :
**tenue courte, calée sur horloge d'échange, à bêta quasi-nul** (l'or/argent/WTI overnight). Ce n'est
ni intraday-flat (elle tient une nuit) ni un carry classique (elle n'encaisse pas un swap positif,
elle traverse une fenêtre où le swap FTMO est spécifiquement nul car le rollover serveur ne tombe pas
dedans). C'est une catégorie à part, que je nomme **§3.2 — dérive de session tenue, bêta-nulle**, et
qui domine le classement final.

---

## 2. Familles retenues

1. **Mean-reversion intraday-flat** (priorité du brief) — fortement pré-exploré, §3.1
2. **Microstructure de session** (priorité du brief, redéfinie plus large que le sens étroit
   « fix/ouverture ») — §3.2, contient la meilleure ligne du classement
3. **Momentum de funding crypto sur véhicule FTMO CFD** (famille bonus, jamais testée sous ce
   véhicule précis) — §3.3
4. **Positionnement dealer / expiry d'options comme signal de nowcast** (famille bonus, contrainte
   par la donnée) — §3.4

---

## 3. Formulations mécanistes détaillées

### 3.1 Mean-reversion intraday-flat

**Where things stand avant toute nouvelle idée** : `piste_C_mr_daily` (4 indices × RSI2/RSI14/
Bollinger %b × 2 seuils × 2 sorties, 84 cellules) et `piste_B_range` (ADX+bandwidth causal, 56
cellules, 7 instruments) ont déjà testé la version rigoureuse de « juste un z-score ». Le verdict est
net et se répète sur les deux études indépendamment : **sur les indices, la jambe short de toute
MR est nette négative** (short-leg mean −0.8 à −4.0 bps/jour-en-position, 0/48 significatif) — ce
n'est pas un signal faible, c'est le **signe inverse de ce qu'il faudrait** : les indices sont en
tendance haussière structurelle, et fader la force = vendre le bêta. La jambe long « marche » (jusqu'à
+50 bps/jour sur RSI14 US100) mais c'est *acheter le dip*, donc du bêta long timé, pas un edge
symétrique (L25). Sur le FX/l'or en intraday, le signal causal existe mais est cost-dead (gross/cost
ratio 1.00 sur XAUUSD, la meilleure cellule ; 0/56 cellules franchissent le seuil L33b de 3×). Le
piège du brief — « on ne va pas juste tester un z-score » — est donc déjà résolu dans le sens négatif
pour la forme la plus simple, avec des méthodes qui dépassent largement le z-score naïf.

Sur ce constat, voici les formulations qui restent mécanistiquement distinctes de ce qui a été testé.

#### 1.1 — OU calibré sur le niveau de prix (classique)
- **Mécanisme** : un teneur de marché absorbe un déséquilibre d'ordre transitoire et se fait payer
  pour le risque d'inventaire ; le prix reviendrait vers une moyenne mobile locale à une vitesse
  calibrable (demi-vie OU).
- **Profil attendu** : win-rate élevé, petits gains fréquents, perte bornée par stop — *si* le signe
  est le bon. Déjà réfuté sur indices (signe inverse, beta trap) et cost-dead sur FX/or.
- **Conditions de mort déjà remplies** : deux études indépendantes (piste_C, prop_suitable C1/C3),
  cinq instruments, trois définitions d'excès (RSI2/RSI14/Bollinger), causal ET oracle testés.
- **Test décisif** : aucun — le test a été fait. **Ne pas retester tel quel.**
- **Univers** : clos sur indices US/EU, FX majeures, gold intraday. Reste non-testé : futures autres
  (pas d'instrument FTMO) — sans objet.
- **Verdict** : FERMÉ (mécanique). Conservé ici pour l'honnêteté du document, pas comme piste.

#### 1.2 — Fade de range / compression de volatilité (ADX + bandwidth)
- **Mécanisme** : dans un régime de faible directionnalité, les extrêmes locaux d'une bande de
  Bollinger sont statistiquement plus susceptibles de revenir vers le milieu.
- **Profil attendu** : identique à 1.1 mais conditionné à un régime détecté.
- **Conditions de mort déjà remplies** : `piste_B_range` a isolé le mécanisme exact de mort — la
  détection de range **causale** (ADX<seuil ET bande compressée, trailing) donne un Sharpe brut
  médian **−0.06**, alors que la détection **oracle** (en sachant que les 8 barres suivantes restent
  calmes) donne **+2.66**. Autrement dit : la totalité de l'edge apparent était dans le fait de savoir
  à l'avance qu'on était en range — l'information que le trading en temps réel n'a jamais. C'est un
  artefact de sélection look-ahead, pas un signal faible.
- **Exception honnête** : XAUUSD a un signal causal réel (gross SR +1.30, pas un artefact) mais
  cost-dead net (gross/cost = 1.00 pile au seuil, net SR 0.14). C'est un kill de **coût/véhicule**, pas
  mécanique — reste théoriquement rouvrable via une exécution moins chère (voir test décisif).
- **Test décisif (le seul valable ici)** : simuler l'exécution en **ordre limite au niveau de la
  bande** plutôt qu'au marché (retire le slippage actif-fill, ajoute un risque de non-remplissage) sur
  XAUUSD seul — lecture de la grille déjà stockée + une hypothèse d'exécution, zéro nouvelle donnée.
  Si le gross/cost ne dépasse pas ~1.5-2 après ce changement, fermer définitivement.
- **Univers** : XAUUSD seul a un thread vivant ; indices et FX fermés.
- **Verdict** : FERMÉ sauf le fil XAUUSD/exécution-limite (faible priorité, §4).

#### 1.3 — MR sur valeur relative intraday-flat (spread, pas prix) — **candidat neuf principal**
- **Mécanisme** : deux instruments fortement co-mouvants (ratio d'indices, ratio de métaux, paire
  FX à composante dollar commune) ont un flux d'ordre asynchrone — l'un réagit plus vite qu'un
  panier de référence ou qu'un ETF de réplication. Le ratio des deux se dilate transitoirement puis
  se referme dans la même séance par arbitrage de panier/création-rachat ou simplement par le retour
  du flux normal, **sans jamais tenir la position la nuit**. C'est différent du stat-arb classique
  (piste_A, cointégration à horizon semaines) : ici l'horizon est intra-jour, donc **aucun financing
  n'est payé** (l'échec de piste_A et le L28 — 2× markup swap — ne s'appliquent pas, puisqu'il n'y a
  pas de nuit tenue). C'est aussi différent de 1.1/1.2 : on trade un **écart entre deux séries**, pas
  un niveau contre sa propre moyenne — la dérive directionnelle commune (le bêta qui tue 1.1/1.2 sur
  indices) s'annule par construction dans le ratio si les deux jambes ont un bêta de marché comparable.
- **Profil de distribution attendu** : fréquence modérée (l'écart ne se creuse pas tous les jours),
  perte bornée (stop sur l'écart, pas sur le niveau), et surtout **kurtosis plus faible que sur un
  instrument seul** — un choc de marché large (crash, macro print) déplace les deux jambes ensemble et
  ne creuse pas nécessairement le ratio, donc le jour où la queue gauche d'un instrument seul est la
  pire est souvent un jour neutre pour le spread. C'est la propriété recherchée par le filtre §1.
- **Conditions d'existence** : la co-intégration doit tenir à l'échelle intra-jour (pas nécessairement
  à l'échelle semaine — piste_A a testé l'échelle lente et l'a trouvée non-stationnaire ; l'échelle
  intraday n'a pas été testée séparément). **Condition de mort** : si le ratio a lui-même un bêta
  directionnel net (ex. US100/US500 monte structurellement parce que la tech surperforme sur toute la
  période — auquel cas on retombe dans le piège L25/beta déjà vu sur piste_C, cette fois sur le ratio
  plutôt que sur le niveau).
- **Test décisif le moins cher** : sur `US100/US500`, `XAUUSD/XAGUSD`, `EURUSD/GBPUSD` (dollar commun),
  calculer le ratio intraday (M1→H1 resamplé, cache déjà construit dans `decorrelated_sleeves_2026-07/
  lib/data.py`), tester la **dérive inconditionnelle du ratio lui-même** en premier (L58 : valider
  contre l'espérance inconditionnelle avant tout signal) — si le ratio dérive significativement dans
  une direction sur tout l'échantillon, la famille est un beta trap déguisé et se ferme en une lecture
  de table. Si le ratio est stationnaire (dérive ≈ 0, HAC t < 1), alors seulement tester le
  causal-vs-oracle exactement comme piste_B (le même garde-fou anti-look-ahead doit s'appliquer ici).
- **Univers FTMO** : indices (US100/US500/US30/GER40 — 6 ratios possibles), métaux (XAUUSD/XAGUSD),
  FX dollar-bloc (EURUSD/GBPUSD, AUDUSD/NZDUSD). Coût : deux spreads au lieu d'un — le gate L33b (gross
  > 3 bps) doit être relu comme gross > 3 bps **du spread**, ce qui est une barre plus dure à passer
  qu'il n'y paraît (deux jambes = deux commissions/slippages).
- **Priorité** : moyenne-haute — mécanisme réellement distinct, infra déjà construite, test cheap,
  mais échec plausible (le ratio pourrait très bien avoir son propre bêta, comme le niveau).

#### 1.4 — MR conditionnée à la volatilité réalisée
- **Mécanisme** : la friction de tenue de marché augmente avec la vol, donc les dépassements
  transitoires sont plus probables ET plus susceptibles de revenir en régime de vol élevée.
- **Profil attendu** : si vrai, edge concentré dans peu de jours à haute vol — mais haute vol
  actions = souvent régime baissier (effet de levier, corrélation vol-rendement négative) → risque
  fort de retomber dans « acheter le dip en régime de stress », qui est exactement le beta trap déjà
  mesuré, avec en prime une queue gauche PIRE (les vrais crashs continuent, ne reviennent pas).
- **Condition de mort probable** : le repo a déjà mesuré ce pattern sous une autre forme — l'overlay
  de régime (vol stress) prédit bien la variance mais PAS le sens du rendement dans la bonne direction
  (L54 : book gagne +218 bps vs +21 bps précisément les jours de stress qu'un filtre couperait). Rien
  ne garantit que la MR-conditionnelle-vol échappe au même piège, sur un mécanisme voisin.
- **Test décisif** : avant tout backtest, relire le résultat déjà stocké de piste_C par tercile de vol
  réalisée (lecture de table, la colonne existe potentiellement dans `backtest_grid.csv`) — si le
  short-leg reste négatif même dans le tercile de vol élevée, fermer sans nouveau code.
- **Univers** : indices (là où la vol-stress-beta est la plus documentée).
- **Priorité** : basse — prior défavorable déjà mesuré sur un mécanisme cousin.

#### 1.5 — MR d'ordre 2 (décélération / courbure du momentum) — **candidat neuf, spéculatif**
- **Mécanisme** : distinct de la MR de niveau (1.1) et de l'épuisement par oscillateur (1.6). On ne
  parie pas sur un retournement de la tendance, mais sur son **ralentissement** — si la tendance est
  encore active (1ère dérivée positive) mais que sa vitesse décélère (2e dérivée négative, ex. la
  pente d'une régression glissante sur les 20 dernières barres se réduit alors que le prix continue de
  monter), les derniers entrants tardifs (retail momentum-chasing, algos de suivi) s'épuisent avant
  que le prix ne se retourne — la conséquence attendue n'est pas un retournement mais une
  **consolidation/range**, structurellement différente d'un pari directionnel. Le trade n'est donc pas
  « vendre », c'est « ne plus suivre la tendance / réduire la conviction directionnelle », ce qui en
  fait presque une famille de *timing d'exposition* plutôt qu'un signal directionnel pur.
- **Profil de distribution attendu** : si le mécanisme est réel, on s'attend à un **win-rate élevé,
  gains petits et fréquents** (on gagne à chaque fois que la tendance marque une pause, ce qui est
  fréquent), et une perte bornée par un stop serré (le risque, c'est que la tendance accélère au lieu
  de décélérer — perte contenue si on sort vite). C'est le profil recherché par le filtre §1, mais
  c'est aussi le profil que **tout le monde cherche**, donc à haute suspicion de curve-fitting si le
  mécanisme économique n'est pas net.
- **Risque explicite de confusion avec ce qui a déjà échoué** : ce mécanisme ressemble structurellement
  à un timing de régime (vol/momentum), catégorie où L54 et `regime_markov_sleeves` ont montré à deux
  reprises que « prédire la variance » n'implique pas « prédire le rendement dans le bon sens ». Le
  risque concret : la décélération pourrait très bien précéder une **accélération** (pause avant la
  jambe suivante d'un vrai trend, cas fréquent en régime de trend fort) aussi souvent qu'une
  consolidation — auquel cas le signal est nul, pas juste faible.
- **Test décisif le moins cher** : sur les 3-4 instruments les plus liquides (US100, EURUSD, XAUUSD),
  calculer la corrélation entre la décélération de pente (régression glissante 20 barres, delta de
  pente) et le rendement futur (h=1 à h=10 jours), en HAC, **sans aucun paramètre de stop/TP** — un
  test de corrélation pur avant tout habillage en stratégie. Si l'IC n'est pas significatif (t<2.5), la
  famille se ferme en un script, pas en une étude complète.
- **Univers** : indices majeurs + FX + gold, daily et intraday (H1/H4).
- **Priorité** : moyenne — mécanisme réellement distinct de tout ce qui a été testé, mais prior faible
  vu la proximité avec les échecs de timing-de-régime déjà mesurés.

#### 1.6 — Épuisement de momentum par divergence d'oscillateurs croisés (RSI/MACD multi-horizon)
- **Mécanisme** : le prix marque un nouvel extrême mais l'oscillateur (RSI, MACD) ne confirme pas —
  signature classique de divergence baissière/haussière, interprétée comme l'épuisement du flux
  d'ordre marginal (les derniers acheteurs sont à bout, le volume ne suit plus).
- **Déjà testé, à re-vérifier avant tout nouveau travail (discipline L48)** : cette classe précise a
  été essayée au moins quatre fois sur NQ intraday (D1 fade post-ORB, D2 fade VWAP post-midi, D4
  RSI reversal déjeuner) — toutes FAIL, deux avec signe inversé (D2 IC_t −0.86, wrong direction) — et
  via piste_C sur RSI2/RSI14 daily indices (beta trap, même verdict). C'est la classe de mécanisme la
  plus testée du repo entier sans jamais passer, sur deux échelles de temps et deux classes
  d'instruments (NQ intraday, indices daily).
- **Angle réellement neuf, s'il existe un** : remplacer la divergence *prix vs oscillateur du même
  instrument* par une divergence *cross-sectionnelle* (breadth) — ex. US100 marque un nouveau plus
  haut mais l'écart US100−US500 (proxy de largeur tech-vs-broad) ne confirme pas. C'est mécanistiquement
  différent (leadership sectoriel, pas oscillateur univarié) mais l'univers FTMO n'offre que 3-4
  indices majeurs — trop peu pour une vraie mesure de largeur (N≥30 imposé par la constitution pour du
  cross-sectionnel ne serait de toute façon pas applicable ici, donc ce n'est même pas un cross-
  sectionnel formel, plutôt un contraste à 2 séries).
- **Test décisif** : NE PAS retester la version univariée (fermée 4×). Si l'angle breadth est tenté,
  test décisif = contraste mécanique L44 (le sous-groupe où le mécanisme devrait jouer vs celui où il
  ne devrait pas) avant tout backtest complet.
- **Univers** : très limité (2-3 paires d'indices disponibles).
- **Priorité** : basse — la version testable est fermée mécaniquement 4 fois ; l'angle neuf est
  contraint par un univers trop petit pour être décisif.

---

### 3.2 Microstructure de session (redéfinie large : tout effet ancré à une horloge d'échange ou de calendrier, tenu ou non)

#### 2.1 — Dérive de session tenue, ancrée à l'horloge d'échange (or/argent/WTI overnight) — **priorité n°1 du document, ré-ouverture pas hypothèse**
- **Mécanisme** : la réouverture Globex (18:00 ET) concentre un flux de rééquilibrage (ordres
  stop/limite accumulés pendant la pause de settlement, ajustements de positions institutionnelles en
  début de session électronique) qui crée une dérive directionnelle mesurable dans la première heure
  post-réouverture — **avant** l'ouverture de Tokyo, donc ce n'est pas de la demande physique
  asiatique (mythe falsifié, L56) mais un artefact de microstructure d'horaire d'échange. Le mécanisme
  a été vérifié par un test de falsification gratuit et décisif : la corrélation du profil horaire
  hiver-vs-été **en heure d'échange** (0.70 or / 0.86 argent) contre **en UTC** (0.04 / 0.20) — preuve
  que l'ancrage est l'horloge CME/COMEX, pas une session géographique.
- **Profil de distribution mesuré (pas attendu — déjà chiffré)** : Sharpe 1.10 (or, OOS 0.96), t_HAC
  4.82, DSR 0.99, WF 5/5, MaxDD −19.4 %, **β 0.004, R² 0.001**, skew +0.35, 17-20 ans positifs sur
  20 ans d'historique. Argent : Sharpe gross 1.45, t 4.55, DSR 1.00, mais régime-conditionnel négatif
  2003-2009 (avant 2010). WTI : Sharpe 1.09, t 3.64, DSR 0.94, skew **+0.43**, 11/14 ans, seul sans
  patch de régime.
- **Pourquoi c'est une ré-ouverture et pas une hypothèse neuve** : les trois raisons de mort
  (`edge_inventory` E002/E003/E004) sont **toutes spécifiques à la géométrie FTMO du brief que ce
  document doit précisément relâcher** : (i) le mur de 91 jours — auto-imposé, FTMO n'a aucune limite
  de temps ; (ii) la barrière journalière percée par le *low* intraday à un vol-targeting agressif —
  résoluble en dimensionnant la sleeve à un vol-target plus bas, pas en changeant le signal ; (iii) la
  dilution en panier (or+argent+WTI combinés perdent contre chaque jambe seule) — résoluble en la
  traitant comme **une sleeve autonome décorrélée**, exactement le rôle qu'occupe déjà le gold sleeve
  du book déployé aujourd'hui (SR 0.39, moteur principal à 65 % de variance) — sauf que E002 mesure un
  Sharpe 1.10, **presque 3× le sleeve actuellement déployé**, sur une fenêtre/paramétrage différent
  qu'il faudrait réconcilier avec l'existant avant tout déploiement.
- **Conditions de mort restantes à vérifier** : le coût aller-retour réel du micro-contrat (MGC ≈
  $40k/lot — la marge tient dans un compte modeste mais le *notionnel* impose 1 lot ou rien, donc le
  vol-targeting est mécaniquement dégradé, cf. L57 — perte de Sharpe ~0.35, skew qui peut s'inverser
  +0.99→−0.49 en configuration lot-fixe selon L57/L59 mesuré sur un cousin très proche, l'or-overnight
  MGC du growth-engine). C'est un problème de **granularité du véhicule CFD FTMO** (spread/commission
  sur XAUUSD cash, pas de contrainte de lot-fixe puisque le CFD est fractionnable) — probablement
  **moins pénalisant sur un CFD FTMO fractionnable que sur un micro-future**, ce qui est une raison de
  plus de le retester spécifiquement sous véhicule FTMO plutôt que sous l'angle futures déjà mesuré.
- **Test décisif le moins cher** : reprendre le générateur de premier-passage FTMO déjà construit
  (`barrier_engine`, `Portfolio/risk/trailing_dd_simulator.py` / `PropFirms/ftmo/program_2026-06/
  propfirm_pass_plan/code/`) sur la série de rendements or-overnight **déjà calculée** (E002), avec (a)
  horizon illimité au lieu du cutoff 91 jours, (b) un vol-target dimensionné pour que le p1 de la
  distribution (−1.96 % mesuré) ne perce pas −5 % daily même au pire jour historique (worst night
  midweek −6.26 % mesuré ailleurs sur un cousin proche — donc dimensionner à L ≤ 0.5-0.75× comme déjà
  suggéré dans `overnight_verification_2026-06`), (c) en sleeve seule, pas en panier. **Zéro nouvelle
  donnée, zéro nouveau backtest — relecture d'une série existante dans un simulateur existant.**
- **Univers FTMO** : XAUUSD, XAGUSD, USOIL (WTI) — tous trois disponibles en CFD FTMO (catégorie
  Commodities confirmée par le FAQ). Coût : commodities CFD 0.015 % par le mémo du repo — nettement
  sous le seuil de rentabilité mesuré (break-even WTI ~3.5 bps, marge confortable sur or).
- **Priorité** : **la plus haute de tout ce document.** Ce n'est techniquement pas une hypothèse à
  concevoir — c'est une ligne déjà instruite à quatre-cinquièmes, où il manque une relecture de
  simulateur, pas une recherche.

#### 2.2 — Saisonnalité Q1 des métaux précieux (effet janvier or/argent/platine)
- **Mécanisme** : effet calendaire documenté (réallocation de portefeuille de début d'année,
  flux de rebalancement institutionnel vers les valeurs refuges post-bonus/post-fiscal), concentré sur
  ~21 séances de janvier.
- **Profil mesuré** : survit au coût CFD le plus lourd testé dans le repo (21 nuits à swap −3.5 bps +
  spread ≈ −81 bps/mois cumulé), robuste à 2× l'hypothèse de swap. t net-CFD 3.07 (argent) / 3.00
  (platine) / 3.22 (or).
- **Pourquoi rouvrable** : tuée par la **sparsité** (1 fenêtre/an face à un mur de 91 jours), pas par
  le signal — exactement le type de contrainte que « no time limit » élimine. Sur un horizon
  pluriannuel sans horloge, un sleeve qui ne porte de risque que 21 jours/an et gagne ~+1.1 %/janvier
  est *le* profil recherché par un compte sans échéance.
- **Piège de véhicule à vérifier avant tout enthousiasme** : le platine n'a pas de contrat micro-future
  (PL = 50 oz) — mais en **CFD FTMO le platine (XPTUSD) est fractionnable**, donc ce piège spécifique
  aux futures ne s'applique probablement pas ici. En revanche, L60 (gravé 2026-07-31) signale que
  XPTUSD/XPDUSD sur yfinance ont 61-69 % de barres à fourchette **nulle** (print de règlement, pas un
  prix) — **le même risque existe très probablement sur les flux de données utilisés pour re-mesurer
  cette saisonnalité** : contrôle obligatoire avant tout retest (part de barres à `high==low==close`
  par instrument et par année), sur la série FTMO/MT5 réelle, pas sur un proxy yfinance.
- **Test décisif** : (i) lire la table de sensibilité au spread déjà publiée pour or/argent janvier
  (aucun nouveau calcul) ; (ii) contrôle L60 gratuit sur XPTUSD si le platine est envisagé ; (iii) si
  le platine échoue le contrôle L60, la revendication se réduit honnêtement à « or+argent janvier,
  corrélation 0.86 » — un seul pari, pas trois, à énoncer avant tout travail (le repo l'a déjà noté
  pour le véhicule futures, la même prudence s'applique côté CFD).
- **Univers** : XAUUSD, XAGUSD, (XPTUSD sous condition L60).
- **Priorité** : haute, juste sous 2.1 — même logique de ré-ouverture géométrique, sparsité au lieu de
  mur de temps, mais fenêtre plus étroite (moins de puissance statistique par an) et un caveat de
  qualité de donnée à lever avant toute mesure.

#### 2.3 — Catch-up de session à l'ouverture (indices cash EU vs mouvement overnight des futures US)
- **Mécanisme** : les indices cash européens (GER40, US30/US100/US500 en cotation continue via CFD)
  ouvrent leur session de liquidité principale plusieurs heures après que les futures américains (ou
  les indices asiatiques) aient déjà bougé sur la nuit ; la littérature de contagion intermarché
  documente un décalage d'incorporation d'information — le marché le moins liquide au moment du choc
  rattrape avec retard. C'est le même type de mécanisme que H1 (réversion FX de la session asiatique à
  l'ouverture de Londres, déjà testé et mort par le coût), mais appliqué à un **couple d'actifs
  différent** (indices cash vs futures overnight, pas FX vs FX) où le gross attendu par mouvement est
  a priori plus élevé (les indices bougent en points/pourcents, pas en pips FX) pour un coût CFD
  indices comparable ou inférieur (commission zéro sur indices FTMO, confirmé blog).
- **Profil attendu** : catch-up = continuation (pas réversion) du mouvement overnight — fréquent
  (chaque séance), petit par occurrence, mais gross potentiellement > 3 bps sur les gros gaps
  overnight (contrairement au H1 FX où le gross mesuré était sub-bps).
- **Conditions de mort probables** : (a) si le CFD GER40/US100 est déjà coté en continu sur la session
  asiatique/US overnight via le flux 24h du broker, il n'y a pas de "catch-up" à proprement parler —
  seulement un gap d'ouverture de séance de référence (Xetra 09:00 CET) qui peut déjà avoir été
  incorporé heure par heure ; **ce point doit être vérifié en premier** (à quel moment le CFD
  GER40 cote-t-il vraiment, avant tout signal) ; (b) le mécanisme pourrait n'être qu'une redite du
  drift overnight NQ déjà mesuré et classé beta-proxy (corr +0.57 avec le buy-hold, L36) — à
  distinguer explicitement d'un vrai catch-up cross-marché avant toute conclusion.
- **Test décisif le moins cher** : vérifier d'abord (gratuit, lecture de spec MT5) si GER40/US100 CFD
  cotent en continu 24h ou seulement en heures de séance de référence — si continu, la famille est
  vide par construction, fermeture immédiate sans backtest.
- **Univers** : GER40, US100, US30, US500 (tous CFD indices FTMO, commission zéro).
- **Priorité** : moyenne — mécanisme plausible et jamais testé sous cette forme précise, mais premher
  test (spec MT5) peut la fermer avant tout code.

#### 2.4 — Gap de dénouement hebdomadaire (Friday close → Monday open)
- **Mécanisme** : les fonds systématiques à rebalancement hebdomadaire (CTA, vol-target) réduisent
  l'exposition avant le week-end pour limiter le risque de gap non-tradable (weekend risk), créant une
  pression de prix transitoire le vendredi qui se résorbe le lundi quand le flux normal reprend — un
  mécanisme distinct de la dérive intra-semaine déjà mesurée (overnight midweek, L36) car ancré sur la
  **périodicité hebdomadaire**, pas journalière.
- **Profil attendu** : fréquence faible (1×/semaine), gain/perte modéré, risque borné (pas de position
  tenue pendant le week-end lui-même — le trade se termine lundi, avant la fenêtre de risque qu'il
  exploite).
- **Conditions de mort probables** : ce mécanisme ressemble structurellement au dossier « Reversal
  1 jour SPX » de l'inventaire (E016, t 3.61) dont le repo signale un effondrement suspect au délai+1
  (0.57→0.08, jamais vérifié en open→close) — un avertissement direct que ce type de réversion
  courte peut être un artefact de fill/close-print plutôt qu'un vrai edge.
- **Test décisif le moins cher** : **avant tout nouveau code**, terminer le test décisif déjà écrit et
  jamais exécuté pour E016 (open→close vs close→close sur ES, données déjà en cache) — si l'edge
  disparaît en open→close, cela ferme définitivement à la fois E016 et informe directement la
  plausibilité de 2.4 (même famille de suspicion d'artefact). Ne pas construire 2.4 avant d'avoir cette
  réponse, gratuite et déjà pré-enregistrée ailleurs dans le repo.
- **Univers** : indices majeurs (US100/US500/GER40), éventuellement FX.
- **Priorité** : basse-moyenne — mécanisme distinct et jamais testé en tant que tel, mais un
  prérequis gratuit et déjà en attente ailleurs doit être soldé avant d'y toucher.

#### 2.5 — Flux de rééquilibrage d'indice (reconstitution trimestrielle, distinct du month-end générique)
- **Mécanisme** : à la date effective de reconstitution trimestrielle d'un indice majeur (ex. S&P/DAX
  rebalancing), les fonds indiciels doivent exécuter un volume connu et daté à l'avance, créant une
  pression de prix mesurable sur l'indice cash dans la fenêtre d'exécution (souvent la dernière heure
  de cotation du jour de rebalancement) — mécanisme **plus étroit et plus daté** que le "month-end"
  générique déjà classé bêta dans `personal_book_research` (« calendriers actions (beta) » — rejeté).
- **Discipline L48 obligatoire avant tout travail** : le rejet antérieur portait-il sur ce mécanisme
  précis (date de reconstitution connue) ou sur un "turn-of-month" générique plus large ? Le mémoire
  ne précise pas la spécification exacte testée — **balayer le registre (chemins historiques ET
  consolidés) avant de considérer ceci comme neuf**, sans quoi ce serait retester un kill mécanique
  déjà rendu sous un autre nom.
- **Profil attendu si le mécanisme est distinct** : fréquence très faible (4×/an par indice), fenêtre
  de quelques heures, gross concentré et potentiellement élevé sur cette fenêtre étroite (analogue
  structurellement à l'ancrage horaire de 2.1 mais sur un calendrier trimestriel plutôt que journalier).
- **Test décisif le moins cher** : lire d'abord le rapport source du kill « calendriers actions (beta)
  » cité dans `personal_book_research_2026-07` pour vérifier sa spécification exacte — lecture, pas
  calcul. Si le mécanisme testé était bien la reconstitution datée et non un effet générique, fermer
  ici. Sinon, un event-study à fenêtre unique sur les dates de reconstitution publiques (gratuites,
  connues à l'avance) suffit à trancher.
- **Univers** : GER40, US500 (proxy CFD des indices sous-jacents à reconstitution connue).
- **Priorité** : basse — probablement déjà couvert par un kill existant ; à vérifier avant tout travail,
  pas à designer comme neuf tant que la vérification n'est pas faite.

#### 2.6 — Fenêtres de fixing / déséquilibre d'enchère (mention négative, pour complétude)
- **Mécanisme** : déséquilibre d'ordre à un fixing programmé (WMR 16:00 Londres) ou à une enchère de
  clôture, exploité par le flux qui doit s'exécuter exactement à l'heure du fixing.
- **Déjà fermé, deux fois, mécanisme réel mais tier de coût institutionnel** : Pattern B (t 3.55, deux
  jambes réelles) meurt uniquement au tarif retail (besoin <1 bp/jambe vs 2.48 bps mesuré, L34) —
  un kill de **coût institutionnel**, en principe rouvrable seulement avec un accès à un tarif
  professionnel qui n'existe pas ici. `H1` (réversion Londres de la session asiatique) meurt pour la
  même raison de coût, gross ~0.5 bps.
- **Test décisif s'il fallait vraiment y revenir** : aucun nouveau test tant que le tarif d'exécution
  ne change pas — c'est un problème de courtier, pas de recherche.
- **Priorité** : nulle sous le véhicule FTMO actuel. Listé pour ne pas laisser un angle mort silencieux.

---

### 3.3 Momentum de funding crypto sur véhicule FTMO CFD (famille bonus)

- **Mécanisme** : le funding rate des perpétuels crypto (Binance/HL) est un signal de positionnement
  extrême — quand il atteint un niveau élevé dans sa distribution historique (percentile trailing),
  cela signale un excès de demande de levier long, et la littérature + un test déjà répliqué
  indépendamment dans ce repo (L50 : réplication Binance 2020-26, 13 perpétuels, 2195 événements)
  montre que l'extrême de funding précède une **continuation** (pas une contrarian-réversion) à 8h/24h/
  72h. C'est un signal exogène (funding, pas prix) appliqué comme nowcast directionnel — **jamais
  testé comme signal d'exécution sur le véhicule FTMO CFD crypto** (BTCUSD/ETHUSD, disponibles côté
  FTMO Swing, commission 0.065 % RT confirmée, weekend trading disponible).
- **Profil de distribution attendu** : ressemble à du momentum (continuation), donc a priori dans la
  famille disqualifiée par le brief — **mais le déclencheur n'est pas un signal de prix/tendance,
  c'est un indicateur de positionnement/crowding**, ce qui change le profil : les épisodes sont rares
  (percentile extrême = peu fréquent), la durée de tenue est courte (jusqu'à normalisation du funding,
  typiquement quelques jours), et le risque principal n'est pas la lenteur d'un trend qui se retourne
  mais la **queue grasse intrinsèque du crypto** (les extrêmes de funding coïncident souvent avec les
  pics de volatilité — risque de gap violent exactement pendant la fenêtre tenue). C'est le point de
  tension que ce document doit nommer explicitement : mécanisme réel et déjà répliqué, mais forme de
  distribution incertaine sous barrière journalière stricte — à ne pas déployer sans mesurer d'abord
  la kurtosis et le skew empiriques de cette fenêtre précise (pas supposer qu'elle hérite du profil
  doux du reste de la taxonomie).
- **Conditions de mort probables** : (a) le swap FTMO crypto et le DLL réduit le week-end ne sont **pas
  confirmés publiquement** (`rules.md` : « must be confirmed with FTMO support ») — un coût/contrainte
  inconnu peut suffire à tuer la faisabilité avant tout signal ; (b) si la kurtosis empirique de la
  fenêtre post-funding-extrême est élevée (probable, le crypto a une kurtosis structurellement forte),
  le profil échoue le critère §1 du filtre malgré un mécanisme réel — ce serait un cas où le mécanisme
  passe mais le **profil** échoue, l'inverse de l'or-overnight.
- **Test décisif le moins cher** : (i) confirmer via le support FTMO ou `ftmo_specs.csv` (script déjà
  écrit dans `rules.md`) le swap et le DLL crypto week-end — préalable gratuit ; (ii) sur les données
  déjà utilisées pour L50 (Binance/HL, funding + prix), calculer skew/kurtosis/MaxDD de la fenêtre
  8-72h post-extrême, **avant** tout habillage en stratégie exécutable — si la kurtosis dépasse un
  seuil disqualifiant (à définir contre le profil du book actuel, gold kurt 84 étant la référence haute
  déjà tolérée), documenter ce compromis explicitement plutôt que déployer à l'aveugle.
- **Univers** : BTCUSD, ETHUSD (FTMO Swing uniquement — Standard interdit le weekend-hold crypto).
- **Priorité** : moyenne — mécanisme validé ailleurs, jamais testé sous ce véhicule précis, mais
  préalables de coût/DLL non confirmés et tension explicite mécanisme-réel/profil-incertain à lever
  avant tout enthousiasme.

---

### 3.4 Positionnement dealer / expiry d'options comme signal de nowcast (famille bonus, contrainte donnée)

- **Mécanisme** : autour des échéances mensuelles/trimestrielles d'options sur indices (triple
  witching), le hedging delta/gamma des teneurs de marché d'options crée un régime de faible
  volatilité réalisée avant l'échéance (pinning) suivi d'une expansion de volatilité après — un
  mécanisme **d'information sur le régime**, pas de récolte de prime (donc distinct de la famille VRP
  déjà fermée, L13, VRP réelle falsifiée sur données réelles). L'idée n'est pas de vendre de la
  volatilité mais d'utiliser la proximité d'une échéance connue comme **signal de timing** pour
  d'autres sleeves (réduire l'exposition MR juste avant l'expiry, l'augmenter juste après).
- **Profil attendu** : très faible fréquence (4-12 événements/an par indice), effet sur le RÉGIME plus
  que sur la direction — donc plus proche d'un filtre d'admission pour d'autres familles que d'une
  sleeve autonome.
- **Contrainte décisive, à vérifier avant tout travail** : une mesure fiable de l'exposition gamma des
  dealers (type SqueezeMetrics/GammaLab) n'est **pas confirmée comme accessible gratuitement** dans ce
  repo — sans elle, on ne peut construire qu'un proxy grossier (jours calendaires d'expiry connus,
  sans magnitude d'exposition), ce qui réduit fortement la valeur informative face aux régimes déjà
  testés et jugés faibles (L15, L54 : les overlays de régime prédisent la variance mais pas
  systématiquement le sens).
- **Test décisif le moins cher** : vérifier l'existence d'une source gratuite de proxy gamma
  (recherche web, 15 min) — si aucune n'existe, fermer immédiatement sans backtest ; sinon, tester en
  premier le contraste mécanique (RV pré-expiry vs post-expiry, sans aucune position) avant d'habiller
  en signal.
- **Univers** : US500/US100 (les indices avec la littérature d'options la plus documentée) — mais le
  véhicule exécutable reste le CFD indice, pas les options elles-mêmes.
- **Priorité** : basse — contrainte de donnée probablement bloquante ; à vérifier avant tout autre
  investissement de temps.

---

## 4. Classement (valeur attendue × faisabilité) avec test décisif

| Rang | Formulation | Valeur att. | Faisabilité | Test décisif le moins cher | Coût du test |
|---|---|---|---|---|---|
| **1** | 2.1 Or/argent/WTI overnight, sleeve autonome, horizon illimité | **Très haute** (t 3.6-4.8 déjà mesuré, DSR 0.94-0.99) | **Très haute** (série existante, simulateur existant) | Relire `barrier_engine` sur la série E002 avec horizon illimité + vol-target abaissé + sleeve seule | Zéro nouvelle donnée, zéro nouveau backtest |
| **2** | 2.2 Saisonnalité Q1 métaux précieux | Haute (t net-CFD 3.0-3.2, survit au coût CFD le plus lourd testé) | Haute (table déjà publiée) sous réserve du contrôle L60 | Lire la table de sensibilité existante + contrôle barres-nulles L60 sur XPTUSD | Quasi nul |
| 3 | 1.3 MR sur valeur relative intraday-flat (spread) | Moyenne (mécanisme neuf, échec plausible) | Haute (infra `decorrelated_sleeves_2026-07/lib/` réutilisable) | Dérive inconditionnelle du ratio (L58) avant tout signal ; puis causal-vs-oracle | Faible (script + cache existant) |
| 4 | 3 (§3.3) Funding-extrême crypto sur FTMO CFD | Moyenne-haute (mécanisme validé ailleurs, L50) mais tension profil incertaine | Moyenne (swap/DLL crypto non confirmés) | Confirmer swap/DLL (support FTMO) + skew/kurtosis de la fenêtre sur données L50 existantes | Faible (une question support + lecture de données existantes) |
| 5 | 2.3 Catch-up session cash EU vs futures overnight US | Moyenne (jamais testé, gross potentiellement > FX) | Moyenne (dépend de la cotation continue ou non du CFD) | Vérifier spec MT5 cotation continue avant tout code | Nul (lecture spec) |
| 6 | 1.5 MR d'ordre 2 / décélération de momentum | Moyenne (mécanisme distinct mais prior faible, proche des échecs de régime) | Moyenne | IC pur (corrélation delta-pente / rendement futur), sans stratégie habillée | Faible |
| 7 | 2.4 Gap hebdomadaire Friday→Monday | Basse-moyenne | Moyenne (prérequis E016 gratuit à solder d'abord) | Finir le test open→close vs close→close déjà pré-enregistré pour E016 | Nul (déjà en attente) |
| 8 | 1.2 (fil XAUUSD/exécution-limite) | Basse (gross/cost pile au seuil) | Haute (grille déjà stockée) | Simuler exécution en ordre limite sur la grille XAUUSD existante | Nul |
| 9 | 2.5 Flux de reconstitution d'indice | Basse (probablement déjà couvert par un kill « calendriers actions ») | Haute (vérification) | Relire la spécification exacte du kill antérieur (L48) avant tout calcul | Nul |
| 10 | 4 (§3.4) Nowcast expiry/gamma dealer | Basse (contrainte donnée probable) | Basse | Vérifier l'existence d'un proxy gamma gratuit | Nul |
| — | 1.1, 1.4, 1.6, 2.6 | — | — | **Fermés, ne pas retester** | — |

**Lecture du classement** : les deux premières lignes ne sont pas des découvertes de ce document —
ce sont des ré-ouvertures déjà instruites que le cadrage du brief (momentum/trend disqualifié en bloc)
laissait fermées à tort. Le reste du classement est la vraie contribution de conception : trois
formulations réellement neuves (1.3, 3, 2.3) valent la peine d'un test IC avant tout engagement plus
lourd, et quatre autres (1.5, 2.4, 1.2-fil, 2.5) ont un préalable gratuit à solder avant même de
mériter un script.

---

## 5. Ce qui est écarté, et pourquoi

- **Trend/momentum swing multi-jours (TSMOM classique)** : profil disqualifié par L24 (plafond ~44-
  54 % sous barrière symétrique, win-rate bas, win/loss haut) ET mesuré nul net sur FTMO (M047,
  gross 0.9 → net 0.0, portage agrégé L36). Fermé mécaniquement, pas de nouvel angle identifié qui
  échappe au win-rate structurel de la famille.
- **Événementiel tenu (pré-FOMC, pré-CPI, adjudication Treasury)** : disqualifié par le profil (kurtosis
  spike au moment de l'événement tenu) ET chaque instance testée meurt pour une raison mécanique
  distincte (régime, mécanisme absent, année aberrante) — donc même si un jour le profil s'améliorait,
  ces instances précises resteraient closes. D'accord avec le brief ici, sans réserve.
- **Carry (FX, commodity, crypto delta-neutral)** : disqualifié par construction (queue gauche par
  design — peso problem) et mort mécaniquement à répétition (FX carry post-GFC, commodity carry
  one-sided-uncollectable L32/L32b, crypto delta-neutral walk-forward négative −1.55). D'accord sans
  réserve — c'est le cas le plus propre du filtre §1.
- **Short-vol / VRP** : disqualifié par construction (négative skew par définition) et falsifié sur
  données réelles d'options (SPY iron condor : plain SR 0.09, hedge de skew réel −0.51, managed
  −0.05/−0.55). D'accord sans réserve.
- **Stat-arb de spread classique (cointégration semaines)** : disqualifié par le financing 2× markup
  (L28) et le piège de bêta hérité (L27) — confirmé indépendamment par `piste_A_statarb`
  (0/12 OOS-cointégré, ~1.0 Sharpe = dérive relative sur 80 jours de tenue = beta trap). D'accord.
  **Nuance ajoutée en 1.3** : la version *intraday-flat* du même principe (spread, pas cointégration
  tenue) n'hérite pas du financing et mérite un test séparé — ce n'est pas la même famille de risque.
- **Breakout (ORB/Crabel/NR7)** : voir §1.2(b) — pas disqualifié par la forme (skew/kurt favorables),
  disqualifié par l'absence d'edge per-trade mesurée ~8 fois. Conservé comme infrastructure de jours de
  trading, pas comme cible de recherche.
- **Fixing/enchère retail (WMR, London open reversal)** : mécanisme réel mais tier de coût
  institutionnel inaccessible (L34, L23b). Fermé, listé par complétude en 2.6.
- **MR de niveau classique (z-score, RSI, Bollinger, ADX-range) sur indices/FX/gold** : voir §3.1 —
  testé plus rigoureusement que ce que demanderait un premier passage (deux études indépendantes,
  causal-vs-oracle, cinq instruments), mécaniquement mort (beta trap sur indices, cost-dead sur
  FX/gold sauf un fil résiduel). Ne pas retester la forme de niveau ; seule la forme relative (1.3) et
  la forme de courbure (1.5) restent à explorer.

---

## 6. Note de méthode — avant toute exécution

Ce document ne consomme aucun `n_tests`. Avant de transformer une ligne du §4 en test réel :
1. Relire la discipline L48 (balayer chemins historiques ET consolidés) pour toute formulation qui
   ressemble à un kill déjà rendu sous un autre nom (2.5 en particulier).
2. Pré-enregistrer falsifiablement (mécanisme, seuils, gates two-sided/délai+1/DSR AVANT tout résultat)
   — le format `PREREGISTRATION.md → RESULTS.md` de `decorrelated_sleeves_2026-07/` est directement
   réutilisable, de même que `lib/ftmo_costs.py`, `lib/data.py`, `lib/stats.py`.
3. Toute formulation qui touche à la barrière journalière (2.1, 2.2, 3) doit être passée dans le
   simulateur de premier-passage FTMO (`barrier_engine`) avec le modèle de barrière **statique** (10 %
   floor, 5 % daily depuis l'initial, jamais trailing) — voir `ftmo_dd_model_static_2026-07`.
4. Signal à T-1, trade à T ; excess returns ; HAC lag-6 ; AMTP/DSR si n_tests>1 ; walk-forward ≥5 folds
   — sans exception, y compris pour les tests décisifs « lecture de table » du §4 s'ils débouchent sur
   un chiffre cité comme edge.
