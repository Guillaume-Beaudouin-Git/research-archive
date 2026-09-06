# Axe D — Carry FX conditionné par le macro
### Spécification institutionnelle + protocole de falsification
Round 2 macro, dossier `Multi_Asset/research/active/macro_round2_2026-09/D_carry_conditionne/`
Rédigé 2026-09-06. Statut : **spec-only, pré-implémentation**. Aucun backtest, aucune donnée, dans ce document.

---

## 0. Cadrage

Ce document ne rend PAS de verdict de faisabilité. Il fait deux choses :
1. spécifie la version **la plus forte, académiquement défendable** de « carry FX conditionné par le sens du portage », en corrigeant les trois défauts déjà identifiés sur l'EA Dédale (biais d'anticipation, veto direction-aveugle, Sharpe caduc) ;
2. liste, pour chaque choix de design, **ce qui le falsifierait** — le test précis à faire tourner avant d'investir plus loin, pas après.

Le point de départ n'est pas un backtest à réparer, c'est un patrimoine académique : le carry est le seul facteur du round précédent qui survit une revue critique (Koijen-Moskowitz-Pedersen-Vrugt, *JFE* 2018). La question n'est donc pas « le carry marche-t-il », c'est « quelle version conditionnée survit à la fois à la théorie du crash risk et au coût retail/FTMO mesuré ».

---

## 1. La littérature du carry conditionné

### 1.1 Le carry nu — ce qu'il vaut, et pourquoi il n'est pas gratuit

**Koijen, Moskowitz, Pedersen, Vrugt (KMPV), « Carry », *Journal of Financial Economics* 127(2), 2018.** Cadre unifié : le carry (rendement attendu si le prix ne bouge pas, mesure model-free) prédit le rendement cross-sectionnel ET time-series sur actions, obligations souveraines, matières premières, Treasuries, crédit et options — pas seulement le FX. Résultats-clé :
- Sharpe moyen ~0.8 par stratégie de carry individuelle (par classe d'actif) ;
- Sharpe ~1.2 sur le portefeuille DIVERSIFIÉ multi-classes d'actifs — c'est le chiffre "1,1" cité dans le brief, à la précision près (~1.2 selon la lecture retenue du papier, l'ordre de grandeur est le même) ;
- un « carry timing » global (surpondérer les classes d'actifs où le carry est élevé PAR RAPPORT À SON PROPRE HISTORIQUE) donne un Sharpe ~0.9 — **inférieur** au carry statique diversifié. Le carry timing CROSS-ASSET n'ajoute rien ; c'est la diversification cross-asset, pas le market-timing, qui fait le Sharpe 1.2.

⚠ Implication directe pour cet axe : la partie du Sharpe KMPV qui vient de la diversification CROSS-ASSET (actions+bonds+FX+commo) **n'est pas accessible** à une stratégie mono-classe (FX only, 12 paires). Le Sharpe FX-only du carry pur, isolé dans la littérature, est historiquement plus proche de 0.3-0.6 hors crash years, pas 1.2. Ne jamais citer le 1.2 KMPV comme référence pour un carry FX seul — c'est le nombre du panier multi-actifs.

**Brunnermeier, Nagel, Pedersen (BNP), « Carry Trades and Currency Crashes », NBER Macroeconomics Annual 2008 (NBER WP 14473).** Le résultat structurant : le carry trade a un **skew négatif documenté** — les devises high-yield chutent brutalement contre les devises low-yield, par à-coups, pas en glissando. Le mécanisme n'est pas macro (surprise de taux) mais **funding liquidity** : quand la liquidité de financement se resserre (VIX ↑, spreads interbancaires ↑), les carry traders sont contraints de dénouer en même temps, ce qui auto-réalise le crash. Conséquence directe pour la spec : un carry qui ne se couvre pas contre ce risque **encaisse une prime de risque**, pas un free lunch — et l'historique récent (cf. §2) EST cet unwind, en miniature, sur le yen en 2024.

**Menkhoff, Sarno, Schmeling, Schrimpf (MSSS), « Carry Trades and Global Foreign Exchange Volatility », *Journal of Finance* 67(2), 2012.** Formalise le canal : les devises high-carry ont une exposition **négative** aux innovations de volatilité FX globale (elles chutent quand la vol saute), les devises low-carry servent de **couverture** (elles montent). Le carry trade est donc, structurellement, une vente d'assurance contre les sauts de volatilité globale — pas un pari sur le différentiel de taux en tant que tel. C'est la fondation théorique du conditionneur le plus robuste trouvé dans la littérature suivante.

### 1.2 Quel conditionneur améliore réellement le Sharpe hors échantillon ?

Trois familles de conditionneurs sont testées dans la littérature académique, avec des résultats de robustesse très inégale :

| Conditionneur | Mécanisme théorique | Effet Sharpe documenté | Robustesse |
|---|---|---|---|
| **Volatilité globale (régime)** | MSSS 2012 : high-carry = short vol ; exclure le carry en régime de vol haute retire l'exposition au crash sans retirer le portage moyen | Bakshi-Panayotov (2013), Lu-Jacobsen (2016), Nakagawa-Sakemoto (2023) : carry brut Sharpe ~0.76 → version conditionnée-vol ~0.84 ; conditionnement sur le forward discount (UIP) seul ~0.99 ; **combinaison des deux jusqu'à ~1.07**. Ordre de grandeur convergent sur plusieurs papiers indépendants : **uplift ~+30 à +50 % de Sharpe**, gain surtout par réduction du crash risk (skew moins négatif), pas par ajout de rendement | **La plus robuste** — répliquée par ≥3 équipes indépendantes sur des échantillons et méthodes distincts |
| **Momentum FX** | Corrélation carry/momentum FX historiquement faible → diversifiant, pas amplificateur (MSSS ont un papier sœur sur le momentum FX, même équipe, même année) | Combiner carry+momentum réduit la vol du book combiné et améliore le Sharpe du COMBINÉ, mais n'améliore PAS le Sharpe du carry LUI-MÊME | Diversifiant, pas conditionneur — à traiter comme une SLEEVE SÉPARÉE, pas un filtre d'entrée sur le carry |
| **Valeur / PPP** | Asness-Moskowitz-Pedersen, « Value and Momentum Everywhere », *JF* 2013 : le value FX (écart au PPP long terme) est négativement corrélé au carry — protège dans les années où le carry crashe (le carry est cher justement dans les devises qui montent, donc chères en PPP) | Combiner value+carry réduit le drawdown maximal du panier carry (les pires années carry, ex. 1998, 2008, sont amorties par la jambe value) sans dégrader le Sharpe moyen | Même verdict que momentum : c'est un **stabilisateur de queue**, pas un amplificateur de rendement moyen |

**Verdict de littérature, tranché** : le seul conditionneur qui améliore MATÉRIELLEMENT le Sharpe hors échantillon (par réduction de la composante crash, documentée et répliquée) est le **régime de volatilité globale FX** (proxy : VIX, ou un indice de vol réalisée cross-currency équipondéré). Momentum et value sont des diversifiants de PORTEFEUILLE utiles en overlay multi-sleeve, pas des filtres qui rendent le carry FX lui-même meilleur. **Le filtre « sens du portage » de Dédale n'apparaît dans AUCUNE de ces trois familles** — ce n'est ni un régime de vol, ni du momentum, ni de la valeur. C'est un filtre de **SIGNE STRUCTUREL** (qui encaisse vs qui paie), orthogonal à la littérature académique du carry conditionné. Cela ne le disqualifie pas mais cela veut dire : **aucune borne de Sharpe académique ne le couvre**, il faut le traiter comme une hypothèse maison, pas un résultat répliqué — voir §3.

---

## 2. Le carry FX G10 est-il encore vivant ?

Le carry G10 est réputé mort après 2008. La littérature nuance ceci de façon précise, importante pour cadrer l'axe :

**Décomposition post-GFC.** La recherche montre que le déclin de performance post-2008 ne vient PAS d'un effondrement des différentiels de taux — ceux-ci sont restés étonnamment stables (~5-6 %/an d'écart moyen sur la décennie post-crise selon plusieurs études citées). Ce qui a changé : la **disparition du risque de baisse asymétrique qui rémunérait le carry avant 2008** — les contraintes de funding liquidity (BNP §1.1) ne deviennent contraignantes qu'À PARTIR de 2008. Autrement dit : avant 2008, le carry payait une prime de crash risk réelle et rare ; après 2008 (taux zéro partout, QE synchronisé, vol FX compressée par les banques centrales), la prime de risque a été arbitrée à la baisse ou masquée, sans jamais disparaître structurellement. Des modèles à changement de régime (Markov-switching) documentent explicitement deux régimes : un régime bas-vol où l'UIP est violée et le carry paie, un régime haut-vol où le carry est massivement négatif — cohérent avec MSSS.

**2022-2024 : le retour, PUIS le retour de bâton, exactement dans le manuel BNP.** Le cycle de hausse des taux Fed 2022-2023, non répliqué par la BoJ (taux négatifs jusqu'à fin 2024), a rouvert un différentiel USD/JPY massif — cité dans les sources : USD/JPY +2000 pips depuis 2022, carry trade JPY-funded redevenu l'un des plus actifs au monde. Puis, en juillet-août 2024, la BoJ relève ses taux de façon inattendue et signale un tapering du QE : le yen s'apprécie de **14 % en moins d'un mois**, déclenchant un dénouement en cascade — c'est un unwind BNP-textbook, funding-liquidity-driven, pas un simple ajustement de fondamentaux. **C'est un fait qui ferme et rouvre l'axe en même temps** : il prouve que le mécanisme carry-crash BNP est vivant et opérationnel EN CE MOMENT (donc le carry existe bien comme prime de risque, pas comme anomalie morte), et il confirme le constat interne : le moteur JPY-funded s'est comprimé/inversé exactement dans la fenêtre où la BoJ est passée de −0.08 % à +1.00 % (2024-2026).

**Verdict sur la vivacité** : le carry G10 n'est pas mort, il est **régime-dépendant de façon prévisible** — vivant quand les différentiels de taux sont larges ET la vol FX est basse, tué par bouffées quand les banques centrales convergent ou surprennent. Le retour des différentiels 2022+ a bien ressuscité la PRIME moyenne (cohérent avec le +16-21 % non biaisé mesuré en interne, faible mais non nul, sur une fenêtre 2019-2026 qui contient à la fois la phase d'ouverture ET la phase de compression). **Le point décisif pour la suite de l'axe n'est donc pas « le carry est-il mort » (réponse : non) mais « quelle fraction de l'edge mesuré vient du régime porteur JPY 2022-2023, aujourd'hui en train de se refermer »** — directement lié à la question de breadth (§4) : si le moteur est à 80 % un seul pari macro (short JPY), l'edge suit le cycle BoJ, point.

---

## 3. La spécification propre de la reprise

Quatre défauts à corriger, un protocole exact et vérifiable pour chacun.

### (a) Swaps historiques réels, par paire ET par sens

**Le problème.** MT5 ne stocke aucun historique de swap ; le champ lu par un EA en backtest est TOUJOURS la valeur courante du jour d'exécution, appliquée rétroactivement à tout l'historique. C'est la cause-racine du biais d'anticipation déjà vérifié (zéro trade reproduit sur un courtier à swaps différents).

**Sources possibles, à ce jour :**
1. **ForexBenchmark** (forexbenchmark.com) — service dédié de comparaison de swaps historiques multi-courtiers, filtrable par paire et par courtier. À vérifier : couverture temporelle réelle (années disponibles), granularité (quotidien ? swap triple le mercredi inclus ?), et si le courtier utilisé en live (FTMO ou Eightcap) y figure nommément.
2. **Demande directe au courtier** — FTMO et Eightcap peuvent, sur demande support, fournir un export CSV de l'historique de leurs swaps par instrument. C'est la source la PLUS FIABLE (swap réellement appliqué, y compris majorations de weekend/triple-swap), mais dépend de la réactivité du support et n'est pas garanti disponible sur toute la fenêtre 2019-2026.
3. **Reconstruction par différentiel de taux interbancaires** (fallback si (1)/(2) incomplets) : SOFR (USD), €STR (EUR), SARON (CHF), TONA (JPY), SONIA (GBP), taux RBA/RBNZ/BoC au jour le jour, disponibles gratuitement (FRED, BIS, banques centrales), moins un spread de financement forfaitaire (majoration courtier retail, typiquement 0.5-2 points de swap). **Ce n'est PAS le swap réel** — c'est une approximation de l'UIP théorique. À utiliser SEULEMENT en fallback, avec un marquage explicite `swap_source = "reconstructed_proxy"` dans chaque ligne de donnée, jamais mélangé silencieusement avec du swap mesuré.

**Vérification anti-triche obligatoire, quelle que soit la source :** tracer la série temporelle du swap PAR PAIRE et PAR SENS sur toute la fenêtre. Un swap constant sur >90 jours consécutifs est un DRAPEAU ROUGE (signe qu'on a re-figé une valeur courante). Croiser les dates de changement de signe avec les dates de décision de banque centrale connues (ex. BoJ juillet 2024, Fed 2022-2023) — un swap qui ne bouge jamais aux dates de décision de taux n'est pas un swap réel, c'est un artefact de source.

### (b) Filtre de carry recalculé trade par trade, pas figé

**Implémentation.** Le filtre `sign(swap_long(pair, t))` doit être un **as-of join** : à chaque instant `t` d'entrée potentielle, on lit la ligne du tableau swap historique dont la date est la PLUS RÉCENTE ≤ t (jamais une valeur globale unique, jamais une valeur lue en avance sur `t`). Concrètement en pandas : `pd.merge_asof(trades, swap_history, on='date', by='pair', direction='backward')`.

**Test de non-triche.** Calculer, pour l'échantillon complet, la variance du signe du filtre dans le temps. Si `sign(swap)` ne change JAMAIS pour une paire donnée sur toute la fenêtre 2019-2026, c'est suspect (sauf paires structurellement stables, ex. AUD/JPY quasi toujours positif JPY-funded — à documenter comme cas légitime, pas comme bug). Le cas qui DOIT changer de signe et qu'on DOIT observer changer : CHF/JPY (BoJ −0.08 %→+1.00 % documenté en interne) — si le backtest ne montre pas ce flip à la bonne date, le pipeline est encore biaisé.

### (c) Bilatéral réellement autorisé

**Le problème.** Le veto de Dédale rejetait 30/30 ventes — direction-aveugle, pas conditionné par l'économie. Cela transforme de facto un filtre de carry en un filtre long-only, ce qui reproduit exactement le biais β-dominance déjà documenté ailleurs dans le repo (L11, L25 : un edge qui ne fonctionne QUE dans un sens n'est pas un edge de carry, c'est un beta directionnel déguisé — ici, beta anti-yen).

**Spécification corrigée.** Le signe du swap ne doit JAMAIS être un veto binaire par direction. Il doit être un **conditionneur continu ou un simple ré-étiquetage** : on autorise le trade dans les deux sens, et le signe du swap détermine seulement s'il y a un PORTAGE POSITIF ou NÉGATIF associé à la position — les deux cas restent tradables, avec un budget de risque éventuellement réduit sur la jambe qui paie (portage négatif), jamais mis à zéro.

**Test de non-triche.** Logger, sur des fenêtres glissantes de 3 mois, le ratio achats/ventes réellement pris. Si ce ratio reste à 0 % de ventes (ou proche), le filtre est encore direction-aveugle malgré le changement de code — c'est le test qui a immédiatement démasqué le veto de Dédale (0/30) et doit être reproduit systématiquement, pas une fois.

### (d) Évalué sous les différentiels de 2026

**Le problème.** Une passe unique 2019-2026 moyenne un régime porteur (2022-2023, différentiels JPY larges) et un régime compressif (2024-2026, BoJ +1.00 %, différentiels US-CHF/JPY -34 à -67 % vs pic). Un Sharpe unique sur toute la fenêtre masque un edge qui s'éteint.

**Spécification.** Rapporter SYSTÉMATIQUEMENT deux sous-périodes distinctes, jamais une seule moyenne : (i) pré-resserrement BoJ (jusqu'à fin 2023), (ii) post-resserrement BoJ (2024 à aujourd'hui). Si (ii) est significativement plus faible ou négatif, ce n'est pas un problème de méthode — **c'est le message central du dossier** : le régime qui a produit l'edge historique est en train de se refermer, et le carry conditionné sur cette base doit être réévalué chaque fois qu'un facteur institutionnel de la BoJ (ou de toute banque centrale funding-currency) bouge. C'est la même discipline walk-forward ≥5 folds déjà en vigueur ailleurs dans le repo — appliquée ici avec un DÉCOUPAGE par régime de politique monétaire en plus du découpage temporel mécanique.

---

## 4. Le véhicule et le coût — le portage EST le signal

Trois candidats, avec un principe qui doit gouverner toute la comparaison : **pour un carry, le financement n'est pas un coût annexe qu'on soustrait après coup — c'est la moitié du rendement attendu.** Toute comparaison de véhicule doit donc chiffrer prix ET portage ensemble, jamais le coût de transaction seul.

| Véhicule | Coût transactionnel mesuré | Portage | Statut |
|---|---|---|---|
| **CFD FTMO** | ~2.48 bps RT (mesuré, cf. L34/registre) | Swaps ASYMÉTRIQUES mesurés (ex. `ftmo_swaps.py`, L30 : US100 long −3.31 bps/nuit) — mesuré pour les indices, **pas encore chiffré paire par paire pour le FX** dans le registre existant | Coût connu, portage FX à mesurer avant tout backtest — ne PAS réutiliser les chiffres indices comme proxy FX (classes d'actifs différentes, L33) |
| **CFD Eightcap** | ~0.75 bps EURUSD (mesuré, bien inférieur à FTMO) | **NON MESURÉ chez ce chercheur** — à vérifier avant toute hypothèse. Un swap Eightcap moins cher en spread mais plus cher en portage annulerait tout l'avantage apparent | Coût transactionnel séduisant MAIS INCOMPLET — l'avantage n'est démontré qu'à moitié tant que le swap n'est pas mesuré. Ne jamais supposer un swap "normal" par analogie avec FTMO ou un autre courtier : chaque courtier fixe sa propre majoration (L46-style : un coût réel mesuré, pas déclaratif) |
| **Futures FX CME (IBKR : 6E EUR, 6J JPY, 6B GBP)** | Commission ~$2.15-2.50 RT par lot (ordre de grandeur futures déjà validé sur MNQ dans le repo), donc en bps quasi négligeable SI le notionnel du lot est assez gros pour diluer le fixe (cf. L57 : le coût fixe domine en bps sur petit notionnel) | **Pas de swap séparé** — le portage est intégré en continu dans la courbe de base (contango/backwardation du future vs spot, reflet direct du différentiel de taux). Le "coût de portage" apparaît au roll trimestriel comme un ajustement de base, pas comme un débit quotidien — c'est en réalité une mesure PLUS PROPRE du carry que le swap courtier retail (pas de markup retail dessus, directement arbitré par le marché interbancaire) | Vehicle le plus honnête pour MESURER le carry, mais granularité de lot lourde : 1×6E = €125 000 de notionnel (~$135-140k), largement au-dessus d'un compte FTMO 10k ou d'un book perso de quelques dizaines de k€ pour une position "carry FX" typiquement petite en risque. À chiffrer précisément (marge initiale par lot, ~2-3% du notionnel selon CME, donc ~$2 700-4 000/contrat) avant d'envisager le déploiement — test L53 (si la marge d'1 lot minimum tient dans le capital perso, le propfirm n'apporte rien) s'applique ici aussi et doit être refait paire par paire |

**Conséquence méthodologique du principe "le portage est le signal".** Si l'UIP tenait exactement (marché efficient, pas de prime de risque), le rendement attendu d'un carry FX serait NUL par construction — le gain de taux serait exactement compensé par la dépréciation attendue de la devise haut-rendement. Le fait qu'un carry FX ait un rendement moyen positif documenté (§1-2) EST la preuve empirique que l'UIP est violée en moyenne, et cette violation est justement la prime de risque de crash (BNP, MSSS). Donc : **évaluer un véhicule sur le seul coût de transaction, sans le portage net asymétrique par sens, ne mesure rien** — un véhicule "moins cher en spread" (Eightcap 0.75 bps) peut très bien avoir un swap qui mange toute la prime de risque si son markup de financement dépasse celui de FTMO. Il n'y a pas de raccourci : le portage doit être mesuré, jamais supposé, pour chacun des trois véhicules, avant toute décision.

---

## 5. La question de breadth — combien de paris VRAIMENT indépendants ?

C'est la contrainte qui a déjà tué l'axe précédent (crypto CS, hard rule N≥30) et elle s'applique ici avec une torsion spécifique : **12 paires ne veut pas dire 12 paris**.

**Le fait structurel documenté par la littérature des facteurs de devises** (Lustig-Roussanov-Verdelhan et la littérature "dollar factor" citée en §1) : le rendement cross-sectionnel des devises G10 est dominé par **deux facteurs**, un facteur dollar (PC1, comouvement quasi uniforme de toutes les devises contre l'USD) et un facteur carry/pente (PC2, structure monotone haut-rendement vs bas-rendement). Ensemble, PC1+PC2 expliquent typiquement **82-88 % de la variance commune** du panier de portefeuilles triés par carry. Ce n'est pas 12 degrés de liberté, c'est **~2 facteurs dominants + du bruit idiosyncratique résiduel**.

**Torsion spécifique à cet axe.** Le moteur Dédale est déjà identifié en interne comme largement mono-devise-de-financement : les six paires les plus affectées par la compression 2026 sont TOUTES des croix JPY (CAD/JPY, NZD/JPY, EUR/JPY, USD/JPY, CHF/JPY, et implicitement GBP/JPY/AUD/JPY par le même mécanisme). Cela veut dire que sur les ~100 trades/an à 12 paires, une fraction dominante du book est en réalité **UN SEUL pari macro répété douze fois** : "la BoJ va rester accommodante / le yen va rester la devise de financement". Le reste (paires non-JPY, ex. AUD/USD, EUR/GBP) porte un second facteur, plus faible, moins documenté dans l'historique interne.

**Estimation de breadth effective, à chiffrer précisément en implémentation (pas ici) :** avec une structure PC1(dollar)+PC2(carry/JPY-funding) expliquant ~85% de la variance commune, et sachant que le moteur mesuré est concentré sur le bloc JPY, une estimation de travail raisonnable est **N_eff ≈ 2 à 4 paris indépendants**, pas 12. C'est très en dessous de la hard rule N≥30 pour les stratégies cross-sectionnelles du repo — mais attention, cette hard rule est écrite pour du cross-sectional PUR ; ici l'axe est plus proche d'un pari macro directionnel répété (comme le TSMOM crypto mono-facteur déjà refermé sous L11) que d'un vrai panier diversifié. **Le protocole doit donc calculer explicitement une ACP (ou une matrice de corrélation des rendements par paire) et rapporter le nombre de composantes principales nécessaires pour expliquer 90% de la variance AVANT tout calcul de Sharpe ou de t-stat** — sinon tout t-stat calculé sur 12 "paires" traitées comme indépendantes est mécaniquement gonflé (le problème AMTP habituel, mais ici c'est la CORRÉLATION intra-panier, pas seulement le nombre d'essais, qui gonfle artificiellement la significativité apparente).

---

## 6. Ce qui falsifierait cet axe — liste de tests, pas de verdict

Dans l'ordre où ils doivent être exécutés (chaque test peut arrêter le développement avant le suivant) :

1. **Falsificateur de source de swap** : si la reconstruction par différentiel de taux interbancaires (fallback (a) ci-dessus) ne matche pas le swap réellement mesuré chez FTMO/Eightcap (quand les deux sont disponibles pour croisement), le proxy est invalide et toute passe qui s'appuie dessus doit être jetée, pas corrigée a posteriori.
2. **Falsificateur de non-triche du filtre recalculé** : si `sign(swap)` ne varie PAS aux dates de décision de banque centrale connues (BoJ juillet 2024 en premier lieu), le pipeline reproduit encore le biais d'anticipation malgré le correctif apparent.
3. **Falsificateur du bilatéral** : si, une fois le veto retiré, le ratio ventes/(achats+ventes) réel reste proche de 0% sur des fenêtres glissantes de 3 mois, OU si le Sharpe des ventes seules est négatif alors que les achats seuls sont positifs, l'axe n'est pas un carry conditionné — c'est un carry long-only anti-JPY déguisé (même famille de biais que L11/L45 déjà refermées pour le crypto et le CFD momentum). Documenter et renommer honnêtement (L37-style : ne jamais appeler "carry conditionné" ce qui est en réalité un pari directionnel unique).
4. **Falsificateur de breadth** : si l'ACP du panier de rendements par paire montre N_eff < 3 avec un t-stat sur le facteur dominant < 2.5 en HAC lag-6, l'axe DOIT être traité comme un seul pari macro (short JPY conditionné), avec toute la prudence de sizing que cela implique — pas comme un portefeuille diversifié de 12 positions.
5. **Falsificateur de régime** : si le Sharpe post-resserrement BoJ (2024-2026) est matériellement inférieur (ou négatif) au Sharpe pré-2024, le régime porteur qui a produit l'edge historique s'est refermé et le carry conditionné doit être suspendu jusqu'à un nouvel élargissement documenté des différentiels de taux (pas seulement attendu).
6. **Falsificateur de véhicule** : si le swap Eightcap, une fois mesuré, s'avère aussi asymétrique et coûteux que FTMO (ou pire), l'avantage apparent en spread (0.75 vs 2.48 bps) ne suffit pas à sauver l'axe — le carry se joue sur le portage, pas sur le spread d'entrée.
7. **Falsificateur académique de fond** : si, une fois isolé des paires non-JPY, le facteur JPY-funding résiduel ne montre PAS l'exposition négative documentée à la volatilité FX globale (MSSS) — c.-à-d. si le filtre "sens du portage" ne se comporte pas comme un carry factor canonique — alors l'hypothèse de départ (« c'est du carry ») est fausse, c'est autre chose (momentum déguisé, saisonnalité, ou bruit), et aucune littérature de conditionnement du carry ne s'applique pour le justifier.

---

## 7. Résumé de la meilleure version spécifiable

La version la plus forte de cet axe n'est PAS le filtre binaire de Dédale corrigé au minimum — c'est :
- un carry FX **bilatéral**, conditionné en CONTINU (pas en veto) par le signe et l'AMPLEUR du portage recalculé jour par jour depuis des swaps historiques réels (source mesurée, jamais reconstruite seule) ;
- **doublé** d'un conditionneur de régime de volatilité FX globale (le seul conditionneur académiquement répliqué, §1.2), en overlay séparé du filtre de sens ;
- évalué en respectant la vraie breadth (ACP du panier, pas 12 paires nominales) ;
- chiffré sur véhicule futures CME en priorité pour la MESURE (portage propre, sans markup retail) avant toute décision de déploiement CFD ;
- et rapporté en DEUX sous-régimes temporels (pré/post resserrement BoJ), jamais en un seul chiffre moyen.

C'est une spec plus lourde que l'EA d'origine, mais chaque alourdissement corrige un biais déjà mesuré ou une lacune déjà identifiée dans la littérature du carry conditionné — rien n'est ajouté par précaution générique.

---
*Sources académiques citées : Koijen-Moskowitz-Pedersen-Vrugt (JFE 2018) ; Brunnermeier-Nagel-Pedersen (NBER WP14473, 2008) ; Menkhoff-Sarno-Schmeling-Schrimpf (JF 2012) ; Bakshi-Panayotov (2013), Lu-Jacobsen (2016), Nakagawa-Sakemoto (2023) sur le conditionnement vol/forward-discount ; Asness-Moskowitz-Pedersen, "Value and Momentum Everywhere" (JF 2013) ; littérature dollar-factor/PC1-PC2 (Lustig-Roussanov-Verdelhan et suites). Historique interne : `fx_carry_dedale_2026-08.md` (MEMORY), registre L (L11, L25, L30, L33, L37, L45, L46, L53, L57).*
