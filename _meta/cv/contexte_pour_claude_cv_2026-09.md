# Contexte complet — projets quant de Guillaume Beaudouin (au 2026-09-04)

> Message à transmettre au chat Claude dédié à la recherche de stage / CV.
> Rédigé par l'assistant qui travaille sur le dépôt depuis avril 2026, à partir du dépôt lui-même
> (chiffres vérifiés par `git`, pas de mémoire approximative). Tout ce qui n'est pas vérifiable est
> marqué **[À COMPLÉTER PAR GUILLAUME]**.

---

## 0. Ce qu'il faut comprendre avant de lire le reste

Le CV de Guillaume ne doit **pas** se vendre sur des stratégies gagnantes. Il doit se vendre sur
**la discipline avec laquelle il a tué les siennes**.

Tu as écrit toi-même : *« un quant qui ouvre ton GitHub cherche une seule chose — est-ce que ce type
sait ce qu'est un backtest honnête »*. C'est précisément l'actif principal ici. Le dépôt
`Algo_claude` contient environ **350 hypothèses de stratégie testées** sur cinq classes d'actifs, dont
la quasi-totalité ont été **rejetées**, chaque rejet étant documenté avec sa cause mécanique. Il y a un
registre formel de leçons méthodologiques numérotées, un ledger de comptage de tests pour la
correction de multiple testing, et une politique écrite de ré-ouverture des familles archivées.

C'est un profil de **chercheur qui sait détruire ses propres résultats**. C'est rare et c'est
exactement ce qu'un desk de recherche systématique cherche. Le positionnement du CV et du repo doit
partir de là, pas de « j'ai une stratégie à Sharpe X ».

---

## 1. Profil académique et linguistique

- **M2 IEF** (Ingénierie Économique et Financière), Université de Rennes 1 — rentrée septembre 2026.
- **M1 IEF** Rennes 1, validé.
- **Double diplôme Universität Augsburg** — **[À COMPLÉTER : années exactes, intitulé du diplôme
  allemand, statut (obtenu / en cours)]**.
- Langues : français (natif), anglais, **allemand** (niveau **[À COMPLÉTER]**).
- Recherche : **stage de fin de M2, semestre 2** (soit **[À COMPLÉTER : dates exactes, durée
  minimale validante selon la scolarité]**). Cette contrainte de durée est le premier filtre à
  vérifier — tu l'as bien identifié.

---

## 2. L'actif principal : le dépôt de recherche `Algo_claude`

### Volumétrie vérifiée (`git`, 2026-09-04)

| métrique | valeur |
|---|---|
| Commits | **2 115** |
| Période | 2026-04-14 → aujourd'hui (**~5 mois**) |
| Fichiers trackés | 5 994 |
| Fichiers Python | 1 591 (**~303 000 lignes**) |
| Fichiers Markdown (rapports de recherche) | 1 950 |
| Fichiers MQL5 (EA MetaTrader) | 13 (~5 000 lignes) |
| Fichiers de tests | 49 |
| Dossiers de recherche | **115** (78 actifs, 37 archivés) |
| Classes d'actifs couvertes | Crypto, FX, Futures, Actions, Commodités, Multi-Asset |

Ce n'est pas un dépôt de notebooks. C'est une infrastructure de recherche avec une constitution
écrite (`CLAUDE.md`), une gouvernance de données, une CI, et du code en production.

### Ce que contient l'arborescence

- `Crypto/ Forex/ Futures/ Equities/ Commodities/ Multi_Asset/` — chacun avec
  `research/active/` et `research/archived/`. Chaque dossier de recherche contient code, données de
  sortie, et un rapport écrit avec verdict.
- `Portfolio/` — bibliothèque maison : `risk/` (sizing, corrélation, simulateur de drawdown
  propfirm), `validation/` (CPCV, multi-test, pipeline), `admission/` (critère d'admission d'une
  sleeve dans un book : ΔSharpe au poids ERC, barrières, p(pass)), `reporting/` (tearsheets).
- `ftmo_live/` — code de production réellement déployé (voir §3).
- `_automation/` — pipelines automatisés : scraping d'idées (Reddit/HN/Quantocracy/SSRN/GitHub),
  scan arXiv q-fin quotidien, synthèse cross-papers hebdomadaire, orchestrateur de faisabilité à
  3 niveaux (gate A : IC ; gate B : walk-forward + bootstrap + DSR ; gate C : sanity checks).
- `_meta/` — le registre de leçons, le ledger de tests, les décisions.
- `PropFirms/` — spécifications de règles de propfirms, simulations d'achat.
- `tools/check_register_integrity.py` — un vérificateur d'intégrité qui **échoue bruyamment** si un
  rapport cite un chemin qui n'existe pas ou n'est pas tracké par git, ou si la chaîne de comptage
  de tests n'est pas monotone. Lancé à la clôture de chaque session.

---

## 3. Track record live et vérifiable

### FTMO — compte funded réel (le plus solide à mettre en avant)

- Véhicule : **FTMO $10 000 Swing, 2-step** (challenge → vérification → funded).
- **Challenge passé en 23 jours** : phase 1 **+10,06 %**, phase 2 **+5,39 %**.
- **Compte funded depuis le 2026-08-17**, toujours actif.
- Exécution : **Expert Advisor MQL5 v2.8** développé en propre, tournant sur MetaTrader 5 sur un
  **VPS Linux Hetzner** sous supervision (superviseur Python, watchdog, keepalive, réconciliation
  EOD, kill-file d'arrêt d'urgence).
- Le book déployé combine plusieurs sleeves : **drift overnight sur indices** (GER40 / US100,
  restreint aux nuits lundi et mardi), **or** (XAUUSD), **ORB sur indices**, un moteur **USDJPY**
  (désactivé). Chaque sleeve a été validée séparément puis auditée en portefeuille.
- Honnêteté nécessaire : le compte est **en drawdown au 1er septembre** (solde 9 931,55 contre
  10 000 initial), et une décision de désarmement de la sleeve ORB est planifiée en octobre sur un
  critère pré-enregistré de coût de transaction mesuré. **Ce point est un atout en entretien, pas une
  faiblesse** — il montre un critère d'arrêt écrit à l'avance.

**Ce que ça démontre concrètement** : capacité à faire passer une stratégie de la recherche à
l'exécution réelle sous contrainte de risque dure (perte journalière max 5 %, floor statique à
−10 %), avec du capital tiers, du code en production, et de la supervision opérationnelle.

### Crypto — Hyperliquid

- **Strategy A — TSMOM crypto** (time-series momentum, signal `tanh(rendement cumulé / vol
  annualisée)`, BTC/ETH/SOL), déployée en live sur testnet Hyperliquid + un compte propfirm crypto.
  Gelée depuis mai 2026 après avoir touché un plafond structurel identifié (le bêta crypto rend le
  respect d'une limite de drawdown journalière de 3 % improbable — taux de passage ~39 %).
- **Strategy B — carry delta-neutre** sur perpétuels Hyperliquid (collecte de funding, jambes
  spot/perp neutralisées), live sur testnet depuis mai 2026, rebalancement toutes les 8 h, kill
  switch, sélection d'univers par volume et plancher de carry.
  **Honnêteté** : le Sharpe backtest de 4,10 a été **rétracté par Guillaume lui-même** après avoir
  découvert que le backtest décrivait une rotation lente alors que la config live tourne en 8 h — aux
  coûts réels la config live est négative. Le walk-forward disponible (3 folds) est sous la règle
  maison de 5 folds, donc **aucun Sharpe n'est citable**. C'est exactement le genre d'auto-réfutation
  à raconter en entretien.
- API REST/WebSocket Hyperliquid, gestion d'ordres, réconciliation d'état.

### Futures

- **Strategy C — momentum d'ouverture NQ** (opening range breakout sur le Nasdaq). Backtest initial
  Sharpe 1,52 sur données Kaggle 2022-2025 → **re-baseliné à 0,41** après ré-achat de données
  Databento propres 2014-2026 et mesure honnête du slippage. Projet annulé faute de véhicule
  (FTMO ne supporte pas les futures CME). **Le passage 1,52 → 0,41 est une des meilleures histoires
  du dossier** : il isole exactement les deux causes (fenêtre d'échantillon favorable + hypothèse de
  coût optimiste).

---

## 4. Le registre de leçons — l'artefact le plus distinctif

`_meta/lessons_registry.md` contient une **soixantaine de leçons méthodologiques numérotées
(L11 → L67)**, chacune formulée comme un verdict + un chiffre opérationnel + un chemin vers la
dérivation. Elles ne sont pas des généralités : ce sont des pièges **mesurés** sur ce dépôt.

Échantillon représentatif (utile pour un entretien technique — ce sont de vraies découvertes) :

- **L43** — Le FX intraday retail est mort au coût. Critère pré-flight :
  `gross_par_trade / coût_p95 ≥ 1,5`. Meilleur ratio jamais observé sur ~1 500 configurations :
  **0,36**. Répliqué **quatre fois indépendamment** (0,336 / 0,36 / 0,38 / 0,36), y compris hors FX
  → c'est devenu une constante empirique du tier de coût retail.
- **L52** — Ne jamais faire confiance au nom d'un champ de fournisseur de données. Le champ `Open`
  du contrat ZN chez yfinance est en réalité l'ouverture Globex 18:00 ET **du jour calendaire
  précédent** (vérifié : 71,6 % de correspondance exacte au tick). Une conclusion
  « intraday vs overnight » bâtie dessus est fausse. Corollaire : *tick-matcher* les barres daily
  contre des barres horaires indépendantes avant toute décomposition.
- **L56** — Un drift de session est ancré à l'horloge de l'**échange avec son DST**, pas à UTC. Test
  de falsification gratuit : corréler le profil horaire hiver-vs-été dans les deux horloges. Ici
  0,70/0,86 en heure de New York contre **0,04/0,20 en UTC** — la fenêtre héritée était juste en
  hiver et une heure en retard tout l'été. Corollaire : une barre H1 agrège silencieusement le gap
  de halt non tradable (jusqu'à **59 % du mouvement** sur l'argent).
- **L59** — Le décalage d'un pas de temps (*delay+1*) ne certifie que **l'entrée**. Les sorties au
  stop exact sont irréalistes : 25 % des barres de stop ouvrent au-delà. Re-pricer les sorties fait
  passer un Sharpe de 0,99 à **0,49**. Cela invalide partiellement toute une famille classique
  (Crabel, ORB, NR7).
- **L61** — L'entrée échelonnée (*sizing* dépendant du chemin) **fabrique un t-stat positif sur du
  bruit pur** : 18 cellules sur 18 au-dessus de 2,5, un t net de +4,81 sur des données aléatoires.
  Le HAC ne le voit pas, parce que le biais est dans le sizing, pas dans le résidu.
- **L64** — Une rupture temporelle doit être **estimée** (Bai-Perron / CUSUM), jamais imposée, et
  corrigée du nombre de dates balayées. Une rupture « évidente » en 2022 s'est révélée au 73ᵉ
  percentile du bruit (p = 0,266).
- **L66** — Ré-échantillonner des instruments cotés indépendamment sur un horodatage commun
  **fabrique de la prédictibilité cross-instrument** (effet Epps / Lo-MacKinlay). Les placebos
  temporels ne l'attrapent pas ; il faut trois diagnostics spécifiques.
- **L67** — Dans la loi fondamentale de Grinold `IR = TC × IC × √BR`, **BR compte les paris
  indépendants, pas les observations**. Mesurer TC au lieu de le supposer.
- **L49 / L58** — Tout claim calendaire doit passer un **placebo apparié**, et la baseline du
  placebo doit elle-même être validée contre l'espérance inconditionnelle (sinon le placebo fabrique
  un faux PASS).

Il y a aussi une **politique écrite de ré-ouverture** des familles archivées, qui classe les
rejets par nature : un rejet *mécanique* (le signal n'existe pas) reste fermé définitivement ; un
rejet *véhicule*, *coût*, *puissance* ou *géométrie* est ré-ouvrable, mais uniquement avec un angle
nouveau écrit **avant** de toucher aux données.

---

## 5. Boîte à outils méthodologique effectivement utilisée

Ce ne sont pas des lignes de CV, c'est du code qui tourne :

- **Significativité** : t-stat HAC Newey-West (lag 6), seuil t > 2,5 pour la faisabilité.
- **Multiple testing** : pénalité approchée quand n_tests > 1 ; **Deflated Sharpe Ratio**
  (Bailey–López de Prado) dès 2 modifications. Un **ledger de comptage de tests** maintenu à
  l'échelle du dépôt (321 tests figés + compteurs par programme) pour que la déflation soit honnête.
- **Bootstrap par blocs** (Politis-Romano) — le bootstrap iid est interdit quand les trades
  cluster.
- **Walk-forward à fenêtre expansive, minimum 5 folds** — le split unique est interdit par la
  constitution du dépôt.
- **CPCV** (Combinatorial Purged Cross-Validation).
- **Gate IC → Sharpe net** (Israel-Jiang-Ross 2017) : `gross ≈ 0,40 × IC × √breadth × σ_cible`,
  exiger `gross > 3 × coût`. Ce gate a tué la majorité des candidats **avant** tout backtest.
- **Placebos appariés** (calendaires, à autocorrélation appariée, à duty cycle identique).
- **MDE avec puissance** — `(z_{1-α/2}+z_{1-β})·σ/√n`, pas la version naïve.
- **Rendements en excès** du taux sans risque (FRED DTB3), vol targeting quotidien, coût mesuré et
  jamais supposé.
- **Simulateur de barrière propfirm** trade-based, calibré par firme, pour estimer p(pass) et durée
  avant achat d'un challenge.

Stack : **Python** (pandas, numpy, statsmodels, scipy), **MQL5**, bash, SQL **[À CONFIRMER]**,
git, GitHub Actions, Linux/VPS, MetaTrader 5, APIs REST/WebSocket (Hyperliquid, Tradovate,
Databento), yfinance / FRED / Dukascopy (décodeur de format binaire `.bi5` écrit maison).

---

## 6. Ingénierie et opérations (souvent sous-vendu, très regardé en entretien)

- **CI/CD** : workflow GitHub Actions de 201 lignes qui auto-merge les PR après checks verts, avec
  **trois gardes** qui bloquent durement toute PR touchant du code live, du code de portefeuille, ou
  la CI elle-même — plus une notification Telegram sur échec.
- **Gouvernance de données formelle** : `data/raw/` immuable avec manifeste, caches régénérables
  gitignorés, règle « une série = un fichier canonique », interdiction de copier une série dans un
  dossier de recherche. Suite à un audit, le `.git` est passé de **2,1 Go à 65 Mo**.
- **Réparation de données** : trous 2018-2021 dans un historique FX/indices M1 tick-par-tick
  réparés et vérifiés aux jointures.
- **Détection d'un bug de fuseau horaire** dans les données historiques : des panneaux étiquetés
  `timestamp_utc` étaient en réalité en EET/EEST (vérifié au tick, décalage −2 h), ce qui signifiait
  que **38,7 % de la session de trading américaine n'avait jamais été testée**. Migration complète
  vers un historique en vrai UTC.
- **Isolation de sessions par git worktree**, après un incident réel où deux sessions parallèles
  partageant un `.git/HEAD` ont fait atterrir un commit sur la mauvaise branche.
- **Post-mortems écrits** sur les incidents live (une violation de compte sur un flash move USDJPY,
  un latch d'état non purgé au rollover, un problème de réalignement de seam sur GER40).

---

## 7. L'histoire à raconter en entretien : l'audit « Dédale »

C'est la meilleure démonstration de compétence du dossier, et elle est récente (août-septembre 2026).

**Contexte** : un ami de Guillaume vend une formation de trading algorithmique et publie un Expert
Advisor MQL5 (« Dédale ») avec un backtest affichant **+60,33 % sur 6,5 ans** et un **Sharpe de
1,56**. Guillaume a voulu savoir si ça tenait.

**Ce qui a été trouvé, en reverse-engineering complet du code source (806 lignes de MQL5) :**

1. **Un biais d'anticipation structurel.** L'EA filtre ses entrées sur le sens du portage en lisant
   `SymbolInfoDouble(SYMBOL_SWAP_LONG)`. Or MT5 **n'a aucun historique de swaps** — cette fonction
   renvoie le swap *actuel du courtier*, constant sur toute la passe de backtest. Le filtre applique
   donc rétroactivement le portage du jour du backtest à tout l'historique. Backtest lancé en 2024
   ⇒ il sélectionne la direction qui venait justement de payer sur les croisées yen en 2022-2024.
   **Vérifié empiriquement** : sur un serveur démo aux swaps différents, le même EA prend **zéro
   trade** sur USDJPY 2018-2024. Le backtest n'est reproductible ni dans le temps, ni entre courtiers.
2. **Un veto direction-aveugle.** Une ligne de contrôle de distance minimale de stop
   (`if(bid < sl + sl_distance_min || ...)`) est écrite sans distinguer achat et vente : pour une
   vente, le stop est au-dessus du prix, donc le test est toujours vrai. **Toute vente est rejetée.**
   Mesuré au binaire avec un EA de diagnostic écrit pour l'occasion : **0 vente acceptée sur 30**.
   L'auteur constate le symptôme dans sa vidéo (« c'est que du long, quasiment ») sans en identifier
   la cause.
3. **Un bug de sélection** : un appel à `MathMin` sur un buffer réutilisé entre appels rend la
   sélection stop/target dépendante de l'appel précédent ; 4 appels sur 60 ne sélectionnent rien.
4. **Un Sharpe caduc.** Le 1,56 vient de `quantstats` appelé avec ses défauts
   (`periods_per_year=252`, `rf=0`) sur une série **indexée par trade** (~99 trades/an). Correction :
   **0,68 brut / 0,48 en excès**.
5. **Une erreur de loi fondamentale.** Son modèle macro annexe affiche un IR de 0,87 via
   `IR = TC × IC × √BR` en comptant **1 755 observations quotidiennes comme 1 755 paris
   indépendants**, alors que son score est un noyau à décroissance exponentielle (deux jours
   consécutifs sont le même pari). Avec une breadth réaliste, le même IC donne 0,22–0,55.
   Détail savoureux : son TC codé en dur à 0,20 (au lieu de 0,50 mesuré) compense partiellement la
   breadth gonflée — les deux erreurs se neutralisent pour produire un chiffre d'apparence plausible.

**Puis la partie constructive** : reproduction du moteur en Python (moteur intra-barre M1, arrondi
identique à MT5, différentiel de taux **historique** trade par trade) → la version **sans biais**
donne **+16 à 21 %** sur la même période au lieu de +60 %, avec un taux de réussite identique
(63,6 %). L'écart mesure exactement le prix du biais.

**Pourquoi c'est une bonne histoire d'entretien** : elle contient de la lecture de code dans un
langage non standard, une hypothèse falsifiable, une **vérification empirique décisive** (relancer
sur un courtier aux swaps différents), une reproduction indépendante, et un chiffrage de l'écart.
C'est littéralement le travail d'un quant de validation de modèle.

---

## 8. Autres briques mobilisables

- **Décodeur binaire Dukascopy `.bi5`** écrit à la main (ordre des octets O,C,L,H non documenté,
  découvert par rétro-ingénierie) pour construire un historique FX M5 sur 19 ans.
- **Pipeline de veille automatisée** : scraping quotidien de sources d'idées + scan arXiv q-fin +
  synthèse hebdomadaire cross-papers, avec déduplication et filtres de plausibilité à 3 niveaux.
- **Simulateur de barrière propfirm** générique par firme (modèle de drawdown statique vs trailing,
  consistency cap, minimum de jours tradés, mécanisme de lock), utilisé pour décider **avant achat**
  si un programme est mathématiquement passable.
- **Module d'admission de sleeve** : au lieu du critère naïf « Sharpe > seuil », le critère implémenté
  est **ΔSharpe du book > 0 au poids ERC**, testé au block-bootstrap, avec effet minimum détectable
  rapporté — et pour un challenge à barrière, la décision se prend sur **Δp(pass) et Δdurée**, pas sur
  ΔSharpe. C'est un raisonnement de gestion de risque sous barrière, pas de la finance de manuel.
- **Étude de véhicule systématique** : la comparaison chiffrée entre compte propfirm et compte
  personnel IBKR pour une même stratégie (le propfirm vend du levier sur du capital qu'on n'a pas ;
  si la marge du lot minimum tient dans le capital personnel, il n'apporte rien — mesuré :
  +17,6 %/an à 100 % du P&L en personnel contre 80 % d'un contrat sous barrière en propfirm).

---

## 9. Projets hors dépôt — **[À COMPLÉTER PAR GUILLAUME]**

Tu as mentionné dans ta réponse précédente des éléments que **je ne peux pas documenter** parce
qu'ils ne sont pas dans ce dépôt. Guillaume doit te les décrire lui-même :

- **Hawkline** — statut, rôle exact, stack, ce qui tourne réellement, taille de l'équipe, dates.
  (Ton conseil de positionnement — « construction d'infrastructure de données et de recherche »
  plutôt que « co-fondateur de startup » — me semble juste.)
- **Pipeline crypto ML** — quels modèles, quelles features, quel horizon, résultat honnête.
- **Framework EV** — de quoi il s'agit exactement.
- **Activité de développement quant facturée** — clients, missions, volume, période. C'est le seul
  élément du dossier qui prouve que quelqu'un a **payé** pour ce travail : à ne pas enterrer.
- Cursus Augsburg, dates, notes/classement si favorable.
- Compétences non couvertes ici : C++, SQL, Rust, machine learning en production, etc.

---

## 10. Ce qu'il ne faut **pas** surclamer (garde-fous)

Guillaume tient à l'honnêteté intellectuelle et le dépôt en porte la trace. Le CV doit rester
défendable ligne par ligne face à un quant qui creuse :

- **Ne pas écrire « Sharpe 1,33 » pour la stratégie crypto.** Ce chiffre est un brut avant taux sans
  risque sur un univers de 14 coins ; la configuration réellement déployée donne **0,57 en excès**,
  avec un intervalle de confiance à 95 % qui **contient zéro**. Le dépôt a lui-même rétracté le
  chiffre.
- **Ne pas écrire « Sharpe 4,10 » pour le carry delta-neutre.** Rétracté. Aucun Sharpe n'est citable
  tant qu'un walk-forward à 5 folds sur la config live n'existe pas.
- **Ne pas écrire « Sharpe 1,52 » pour la stratégie NQ.** Re-baselinée à 0,41.
- **Ne pas écrire « Sharpe 2,31 » pour le portefeuille.** Ce chiffre a été démontré fabriqué au
  niveau composant et retiré.
- Le compte funded est **en drawdown** actuellement. Le dire si on est interrogé dessus, avec le
  critère de désarmement pré-enregistré — c'est plus impressionnant que de l'esquiver.

**Formulations sûres et vraies** :
> « Compte propfirm funded de $10 000 obtenu en 23 jours (deux phases, +10,1 % et +5,4 %), exécuté
> par un EA MQL5 développé en propre sur VPS Linux supervisé, en production depuis août 2026. »

> « ~350 hypothèses de stratégie testées sur 6 classes d'actifs ; la quasi-totalité rejetées, chaque
> rejet documenté par sa cause mécanique dans un registre de ~60 leçons méthodologiques numérotées. »

> « Détection et chiffrage d'un biais d'anticipation dans un EA tiers commercialisé : le backtest
> affiché à +60 % tombe à +16-21 % une fois le biais retiré ; vérification empirique par re-exécution
> sur un courtier aux paramètres différents (0 trade pris). »

---

## 11. Ma lecture stratégique (à confronter à la tienne)

Je suis d'accord avec ton diagnostic sur le mauvais ordre du plan, et avec ta hiérarchie de cibles.
J'ajouterais quatre choses :

1. **Le repo public à montrer ne doit pas être `Algo_claude` tel quel.** Il contient des clés
   redigées, des états de compte live, des post-mortems d'incidents, et une constitution interne. Il
   faut en **extraire un dépôt vitrine** : une étude, complète, avec données reproductibles,
   out-of-sample propre, coûts mesurés, et une section « ce qui n'a pas marché ». Mon candidat
   naturel est **l'audit Dédale** (§7) — c'est autonome, c'est une histoire, ça montre du code, de la
   statistique et du jugement, et ça ne divulgue aucune position. Second candidat : le
   **re-baselining NQ 1,52 → 0,41**, qui est la démonstration la plus pure de « backtest honnête ».
2. **Le registre de leçons est un actif de communication sous-exploité.** Publié seul, proprement
   rédigé, c'est le genre de document qui circule et qui fait qu'un desk se souvient d'un nom. Il n'y
   a pas de risque concurrentiel : ce sont des méthodes, pas des signaux.
3. **La cible « crypto prop / market making » que tu proposes est particulièrement bien alignée** —
   le travail Hyperliquid (API, carry de funding, exécution, réconciliation d'état) est directement
   pertinent, et c'est le seul segment où l'expérience live de Guillaume vaut plus qu'un pedigree.
4. **Francfort mérite d'être testé en priorité**, pas en option. Le double diplôme Augsburg +
   l'allemand transforment un dossier français ordinaire en dossier local différenciant, et le format
   du stage long y est mieux compris qu'aux États-Unis. Ça contourne aussi entièrement le problème
   de visa et de durée que tu as identifié sur les prop shops américains.

Dernier point, sur la contrainte que tu as bien vue : le vrai goulot n'est ni le CV ni le niveau,
c'est **la durée du stage et le visa**. Tant que la scolarité de Rennes n'a pas répondu sur la durée
minimale validante et l'acceptabilité d'une dérogation, une partie des candidatures est du travail
potentiellement perdu. C'est le premier appel à passer.
