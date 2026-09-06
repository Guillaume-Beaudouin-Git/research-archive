# Le macro prédit-il le RISQUE (et non le rendement) sous une barrière absorbante ? — Version la plus forte de l'axe A

**Round 2, dossier A_risque — 2026-09-06**
**Mandat** : construire la version la plus défendable de l'axe « macro → volatilité/queues, pas macro → rendement », spécifiquement pour un compte FTMO funded $10k (plancher statique -10 %, perte journalière max -5 %) — PAS rendre un verdict de faisabilité générique. Confronter frontalement L54.

---

## 0. Résumé exécutif

**Verdict directionnel : l'axe n'est PAS mort, mais il est beaucoup plus étroit que « macro prédit la vol donc on dé-levier ».** Trois affaiblissements successifs de l'idée naïve, et une reformulation qui survit :

1. **La littérature macro→vol est réelle et solide** (JLN, GARCH-MIDAS, EPU) mais l'effet est **lent** (horizon mensuel/trimestriel, composante long-run) — mal assorti à une barrière testée **quotidiennement**.
2. **L54 n'est pas invalidé par l'argument barrière en général** : p(ruine) est bien **convexe** en volatilité au point de fonctionnement typique d'un compte FTMO (loin de la barrière), donc il existe une valeur de survie à zéro alpha — mais **le gain convexe est mathématiquement petit à cette distance de barrière (z ≈ 4-6 écarts-types/jour)**, alors que le manque à gagner en moyenne mesuré par L54 (+218 vs +21 bps) est **gros**. À magnitudes comparables, L54 gagne.
3. **L'argument barrière peut néanmoins échapper à L54 sous une condition précise et testable** : que le signal macro utilisé soit **orthogonal** au mécanisme qui rémunère le book (test L38 réutilisé), ce qui n'est PAS le cas d'un flag générique « régime de vol élevé » (il attrape les régimes tendanciels, qui paient précisément ce book). Un flag de **calendrier d'événements macro programmés** (CPI/FOMC/NFP) est structurellement différent : il ne provient pas d'un modèle de régime endogène au book, il est connu avec certitude (le jour, l'heure), et il capture un risque de **saut**, pas de diffusion — c'est là, et seulement là, que la convexité de barrière a une chance de dominer.
4. **Meilleure version constructible** : remplacer, dans l'estimateur de volatilité qui alimente le vol-targeting EXISTANT, la vol réalisée glissante par un **nowcast macro-augmenté** (GARCH-MIDAS-style) qui anticipe — au lieu d'un flag binaire additionnel qui coupe le book. Et séparément, un **évitement de fenêtre calendaire programmée** (pas un régime endogène) autour des annonces à risque de saut. Les deux se testent par le protocole de falsification demandé : Δp(pass) contre un contrôle dé-levier-sur-vol-réalisée-seule à duty cycle apparié — **jamais ΔSR**.
5. **Piège d'implémentation identifié et documenté** : à z ≈ 4-6, la probabilité de ruine quotidienne gaussienne est de l'ordre de 1e-5 à 1e-8 — un Monte Carlo gaussien naïf ne verra JAMAIS assez d'événements de ruine pour trancher statistiquement entre macro et vol-réalisée-seule. Les vraies cassures de barrière viennent de sauts (queues grasses), pas de diffusion — il faut un rééchantillonnage historique des pires séances (cf. L57 déjà gravée) ou une simulation d'événement rare (tilting exponentiel), jamais du gaussien pur.

Ce document développe ces cinq points avec la littérature primaire, la mathématique de la convexité calibrée aux chiffres du dépôt, et une spécification opérationnelle du test de falsification.

---

## 1. Le cœur du dossier : L54 s'applique-t-il à l'argument barrière ?

### 1.1 Ce que L54 a établi, précisément

L54 (registre `_meta/lessons_registry.md`) : *« La condition liante d'un overlay de régime n'est PAS le MaxDD : c'est que le régime prédisant la VARIANCE prédise la MOYENNE dans le MÊME SENS. »* Mesuré : le book déployé a un MaxDD de -81 % (condition initiale L15 remplie), et l'overlay a quand même échoué parce que les flags prédisent bien la variance (vol stress 9.8 % vs 4.2 %) **mais le book gagne +218 bps vs +21 bps sur ces mêmes jours** — la coupe retranche systématiquement les jours qui paient. Aucune variante ne bat son propre **dé-levier à volatilité égale** (comparaison à duty cycle apparié, déjà pratiquée dans le dépôt).

C'est un résultat sur l'**espérance conditionnelle** (le Sharpe, le rendement moyen du book sur les jours flaggés). L54 ne dit rien, explicitement, sur la probabilité de franchir une barrière absorbante — c'est exactement la faille que ce dossier doit examiner, ni plus ni moins.

### 1.2 La thèse à tester : pourquoi une barrière pourrait changer l'arbitrage

Sous une barrière absorbante, le critère de décision n'est pas E[rendement] mais **P(ruine avant l'horizon)**, une fonctionnelle de toute la trajectoire. Si p(ruine) est **convexe** en volatilité (voir §3), alors par l'inégalité de Jensen, **comprimer la dispersion journalière de la vol autour de sa moyenne a une valeur de survie strictement positive même à espérance de rendement inchangée** — un mécanisme qui n'existe simplement pas dans le calcul du Sharpe. C'est la seule raison structurelle pour laquelle « macro prédit la vol » pourrait valoir quelque chose alors que « macro prédit le rendement » ne vaut rien : la convexité de la fonction de survie, pas un edge de rendement caché.

### 1.3 Le verdict, chiffré

Voir la dérivation complète en §3. Le résultat qui tranche : **oui, p(ruine) est convexe en σ dans le régime où opère un compte FTMO bien dimensionné (z = B/(σ√T) ≳ √2), donc l'effet Jensen existe et est du bon signe. Mais sa TAILLE, au point de fonctionnement réel du dépôt (z de l'ordre de 4 à 6 sur la barrière journalière), est du second ordre et petite en valeur absolue — alors que le manque à gagner en moyenne mesuré par L54 est du premier ordre et gros.** Un overlay générique de régime de vol échoue donc PROBABLEMENT sous le critère barrière pour la même raison qu'il échoue sous Sharpe : parce que le flag est corrélé positivement avec la moyenne du book, et ce corrélat positif domine le gain de convexité à cette distance de barrière. **L54 n'est pas formellement invalidé par l'argument barrière — il est probablement encore vrai sous ce critère, sauf changement de la NATURE du flag** (voir §4).

---

## 2. Revue de littérature

### 2.1 Macro → volatilité : l'effet est réel, mais lent et de bas horizon-fréquence

- **Jurado, Ludvigson & Ng (2015), "Measuring Uncertainty", AER** — construisent un indice économétrique direct de l'incertitude macro (composante *inforecastable* de centaines de séries, pas juste la volatilité brute des séries). Point clé pour ce dossier : *« uncertainty in a series is not the same as the conditional volatility of the raw series »* — distinction cruciale, un proxy de volatilité n'est pas un proxy d'incertitude structurelle, et les épisodes d'incertitude véritablement macro sont **rares mais gros et persistants**, pas un signal journalier à haute fréquence. [Measuring Uncertainty (AEA)](https://www.aeaweb.org/articles?id=10.1257%2Faer.20131193) · [NBER WP19456](https://www.nber.org/system/files/working_papers/w19456/revisions/w19456.rev0.pdf) · [Macrosynergy — macro uncertainty as predictor of vol](https://macrosynergy.com/research/macro-uncertainty-as-predictor-of-market-volatility/)
- **Baker, Bloom & Davis (2016), "Measuring Economic Policy Uncertainty", QJE** — l'EPU (comptage d'articles de presse) est associé à une **volatilité boursière accrue** et à une baisse d'investissement/emploi dans les secteurs sensibles à la politique. Mécanisme narratif solide (élections serrées, guerres du Golfe, 9/11, Lehman, plafond de la dette). [QJE](https://academic.oup.com/qje/article-abstract/131/4/1593/2468873) · [NBER WP21633](https://www.nber.org/papers/w21633) · [texte complet Hoover](https://www.hoover.org/sites/default/files/research/docs/15111_-_baker_bloom_and_davis_-_measuring_economic_policy_uncertainty.pdf)
- **Engle, Ghysels & Sohn (2013), "Stock Market Volatility and Macroeconomic Fundamentals", Review of Economics and Statistics** — le modèle **GARCH-MIDAS** sépare une composante GARCH journalière court terme d'une composante long-terme pilotée par un polynôme MIDAS sur des variables macro basse fréquence (inflation, croissance de la production industrielle). Résultat central : **l'inclusion macro améliore significativement la prévision à LONG HORIZON (trimestre+)**, pas nécessairement à l'horizon d'un jour. [Kenan Institute synthèse](https://kenaninstitute.unc.edu/publication/stock-market-volatility-and-macroeconomic-fundamentals/) · [NBER WP14269](https://www.nber.org/system/files/working_papers/w14269/w14269.pdf) · [SSRN — On the Economic Sources of Stock Market Volatility](https://doi.org/10.2139/ssrn.971310)
- **Extensions HAR + EPU/IV** — des variantes du modèle HAR-RV augmentées de la volatilité implicite et/ou de l'EPU battent le HAR nu **out-of-sample**, à plusieurs horizons court et long terme. Le signal existe donc aussi à fréquence plus fine que le GARCH-MIDAS pur, mais la littérature ne teste presque jamais l'horizon **intra-journalier** qui importe pour une barrière testée quotidiennement.
- **Dispersion des prévisionnistes** (Survey of Professional Forecasters, Zarnowitz-Lambros) — la dispersion cross-sectionnelle des prévisions macro est un proxy d'incertitude complémentaire à l'EPU ; appliquée au pétrole, elle améliore la prévision de volatilité des rendements. Même caveat : fréquence trimestrielle de la donnée source (SPF), pas quotidienne. [Philadelphia Fed — Forecast Disagreement](https://www.philadelphiafed.org/the-economy/macroeconomics/forecast-disagreement-in-the-survey-of-professional-forecasters) · [Patton & Timmermann — Why Do Forecasters Disagree](https://public.econ.duke.edu/~ap172/Patton_Timmermann_Dispersion_dec08.pdf)

**Verdict fréquence** : toute cette littérature (JLN, EPU, GARCH-MIDAS) opère à un horizon **mensuel/trimestriel** (composante long-terme). Le book FTMO du chercheur teste sa barrière **chaque jour**. Il y a un **mismatch d'horizon fondamental** entre le signal macro (lent) et le test (rapide). Le seul canal macro à fréquence quotidienne compatible avec la barrière journalière est le **calendrier connu des annonces** (CPI/FOMC/NFP à date et heure fixes) — pas un indice d'incertitude filtré. Ce point structure toute la recommandation du §5.

### 2.2 Macro → corrélation et régimes de co-mouvement

La littérature confirme qualitativement que la volatilité (et par extension l'incertitude macro) et la corrélation montent ensemble : *« il y a un plus fort co-mouvement pendant les périodes de haute volatilité »* dans les modèles à changement de régime et en théorie des valeurs extrêmes ; *« si la volatilité d'un facteur augmente, la corrélation est censée augmenter »* dans un modèle à facteur donné. L'incertitude de politique économique amplifie mesurablement les canaux de transmission entre marchés développés et émergents (« wake-up call » hypothesis). **Mais** cette littérature est presque exclusivement construite sur des données mensuelles/basse fréquence de crises historiques (contagion 1997-98, GFC), et le signal utile pour un compte à barrière journalière — « est-ce que DEMAIN les corrélations vont se resserrer » — n'est démontré nulle part à cet horizon. C'est un résultat de **structure** (vol haute ⇒ corrélation haute, presque tautologique via la théorie des copules/facteurs), pas un résultat de **prévision incrémentale** apportée spécifiquement par une variable macro plutôt que par la vol réalisée elle-même.

### 2.3 Macro → queues et clustering de drawdown

- **Adrian, Boyarchenko & Giannone (2019), "Vulnerable Growth", AER** — le concept de *Growth-at-Risk* : les conditions financières (spreads de crédit, vol implicite actions, levier) prédisent fortement la **queue gauche** de la distribution de croissance, beaucoup plus que la moyenne. *« Tighter financial conditions sharply worsen downside risk while leaving the upper part of the distribution comparatively stable »* — asymétrie exacte de ce que cherche le chercheur (prédire le risque de queue sans prédire la moyenne). Horizon opérationnel : fréquence FOMC (~6-7 semaines), pas quotidien. [IMF WP18180](https://www.imf.org/-/media/files/publications/wp/2018/wp18180.pdf) · [structural determinants (IJCB)](https://www.ijcb.org/sites/default/files/journal/v19n2/ijcb-v19n2-structural-determinants-growth-risk.pdf)
- **VIX / structure par terme** — la VIX se décompose en variance réalisée + prime de risque de variance + queue réalisée + prime de risque de queue (~1/3 de la VIX vient de la composante « prime de risque de queue »). La structure par terme donne une indication de la probabilité d'un événement de queue à court terme. C'est la version marché-implicite, **quotidienne**, du signal GaR — et elle est directement disponible sans construction macro artisanale (VIX9D/VIX/VIX3M déjà utilisés en pratique dans les stratégies de vente de vol pour gérer le gap risk).

**Verdict** : la prédictibilité des queues existe, et à la différence de la prédictibilité macro→vol pure, elle a un analogue **quotidien** exploitable (structure par terme de la vol implicite) — mais c'est un signal de MARCHÉ (options), pas un signal MACRO au sens strict de la mission. Si l'axe doit rester « macro », le canal le plus proche de cette fréquence est le calendrier programmé d'annonces, pas un indice composite lentement mis à jour.

### 2.4 Contrôle optimal sous contrainte de drawdown/barrière

- **Grossman & Zhou (1993), "Optimal Investment Strategies for Controlling Drawdowns", Math. Finance** — premiers à résoudre, en horizon infini, l'allocation optimale sous contrainte W_t ≥ α·M_t (richesse ≥ fraction α du maximum historique). Résultat qualitatif clé, repris par Cvitanić-Karatzas : **imposer une contrainte de drawdown équivaut essentiellement à changer l'aversion au risque effective de l'investisseur** — pas à changer son edge. [Math Finance abstract](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9965.1993.tb00044.x)
- **Cvitanić & Karatzas (1995)** — généralisent à plusieurs actifs, montrent que le problème contraint se ramène à un problème non contraint via un processus auxiliaire — cadre plus général, même conclusion qualitative.
- **Klass & Nowicki (2005)** — contre-point : la stratégie Grossman-Zhou n'est **pas toujours optimale en temps discret**. Rappel utile : ces résultats sont continus/asymptotiques, une barrière FTMO est discrète (reset journalier), donc l'application directe demande prudence.
- **CPPI (Constant Proportion Portfolio Insurance, Black & Jones 1987)** — c'est la version *praticien* la plus proche du problème du chercheur : exposition = multiplicateur × coussin (valeur − plancher). Le **gap risk** — perte qui dépasse le coussin entre deux rééquilibrages — est précisément l'analogue du risque de franchir la barrière FTMO intra-journée. Point directement transférable : **« dans certaines implémentations, le multiplicateur est ajusté à la baisse en période de volatilité élevée et inversement »** — c'est EXACTEMENT l'overlay que L54 a testé et fait échouer sur ce book. La littérature CPPI confirme que c'est la pratique standard de l'industrie de l'assurance de portefeuille — mais ne prouve PAS qu'elle ajoute de la valeur nette de coûts/manque à gagner en dehors du cas où le sous-jacent n'a pas de prime de risque conditionnelle liée à sa propre vol (ce qui est faux pour un book trend/carry, cf. §2.5). [QuantPedia — introduction CPPI](https://quantpedia.com/introduction-to-cppi-constant-proportion-portfolio-insurance/) · [Wikipedia CPPI](https://en.wikipedia.org/wiki/Constant_proportion_portfolio_insurance)

### 2.5 Le contrepoint empirique obligatoire : Moreira & Muir

- **Moreira & Muir (2017), "Volatility-Managed Portfolios", Journal of Finance** — c'est la référence la plus directement pertinente et la plus dangereuse à ignorer : des portefeuilles qui réduisent le risque quand la volatilité RÉALISÉE est haute **augmentent** le Sharpe sur marché actions, value, momentum, carry FX — parce qu'en réponse à un choc de variance, **la variance conditionnelle grimpe initialement beaucoup plus que le rendement attendu**, rendant le couple rendement/risque transitoirement défavorable. C'est la preuve empirique qu'un mécanisme du type recherché **existe** ailleurs. [NBER WP22208](https://www.nber.org/system/files/working_papers/w22208/w22208.pdf) · [JoF publié](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf)
- **MAIS, critique directement applicable** : une fois coûts de transaction et risque d'estimation inclus, **le Sharpe devient négatif pour 5 des 9 portefeuilles vol-managés testés individuellement** ; hors le marché actions large (le facteur le plus arbitrable), le vol-timing des autres facteurs **ne produit plus d'alpha net de coûts**. Et surtout : *« si le rendement conditionnel attendu est positivement lié à la vol décalée, le bénéfice du vol-timing est probablement annulé par le mauvais sens du market-timing »* — c'est **exactement** ce que L54 a mesuré sur le book du chercheur (le rendement grimpe AVEC la vol flaggée). Moreira-Muir n'est donc pas un contre-exemple à L54 ; c'est une **confirmation de sa condition liante**, à l'échelle académique : le vol-timing marche seulement quand rendement conditionnel et vol conditionnelle sont **découplés ou inversés**, jamais quand ils montent ensemble. Le book du chercheur (trend/carry overnight) est structurellement du côté « montent ensemble » — cohérent avec le fait connu que le TSMOM est un profil « long vol » (Fung-Hsieh, straddle-like payoff).

**Conclusion de la revue** : la littérature macro→risque est solide sur le PRINCIPE (vol, corrélation, queues sont plus prévisibles que le rendement) mais quasi unanimement construite à des horizons **mensuels ou trimestriels**, alors que la barrière opérationnelle est **journalière**. Le seul canal véritablement macro et véritablement quotidien est le **calendrier connu d'annonces programmées**, pas un indice d'incertitude filtré. Et la condition de succès d'un vol-timing (Moreira-Muir, en écho exact à L54) est que le flag soit **découplé** du mécanisme qui rémunère le book — condition non triviale, testable, et probablement ÉCHOUÉE par un flag de régime générique sur ce book précis.

---

## 3. La mathématique de la convexité sous barrière (dérivation, calibrée)

### 3.1 Cadre

Approximation par un mouvement brownien arithmétique : X_t = μt + σW_t, X_0=0, barrière absorbante en −B (B>0, en unités de rendement cumulé). Formule de réflexion (temps de premier passage, horizon T) :

P(ruine avant T) = Φ[(−B−μT)/(σ√T)] + exp(−2μB/σ²)·Φ[(−B+μT)/(σ√T)]

Cas μ=0 (le cas pertinent pour isoler l'effet PUR de la vol, à espérance nulle par construction — exactement l'hypothèse « zéro alpha » du mandat) :

**P(ruine | T) = 2·Φ(−B/(σ√T)) = 2·Φ(−z), avec z = B/(σ√T)**

### 3.2 Convexité en σ

En posant z = k/σ (k=B/√T constant), on calcule (dérivation complète faite, disponible sur demande) :

**f''(σ) = [2k·φ(z)/σ³]·(z² − 2)**

→ **P(ruine) est CONVEXE en σ si et seulement si z > √2 ≈ 1.414**, et CONCAVE si z < √2.

C'est le résultat pivot : **la convexité n'est pas automatique**. Elle n'existe que dans le régime où la barrière est « loin » relativement à la vol horizon — ce qui est heureusement (et logiquement) le régime dans lequel un compte funded bien dimensionné doit opérer (sinon le firme ne le financerait pas).

### 3.3 Calibration aux chiffres du dépôt

- Barrière journalière FTMO : B = 5 % (perte journalière max).
- Vol journalière typique d'un book multi-actifs vol-targeté à ~12-18 %/an (cf. VOL_TARGET_LIVE=0.18 de la Stratégie A, ordre de grandeur comparable pour le book Multi_Asset) : σ_jour ≈ 15 %/√252 ≈ **0.94 %**.
- **z = B/σ_jour ≈ 5.3** (sur un horizon T=1 jour, k=B).

**z ≈ 5.3 ≫ √2** : on est loin dans la zone convexe — l'effet Jensen existe bel et bien, du bon signe. Mais à z=5.3, φ(z) ≈ 5.5×10⁻⁷ (densité normale quasi nulle à cette distance) — **la dérivée seconde f''(σ) est elle-même minuscule à ce point** (elle est proportionnelle à φ(z), qui s'effondre exponentiellement). Concrètement : Φ(−5.3) ≈ **6×10⁻⁸** — la probabilité de ruine gaussienne UN JOUR DONNÉ est de l'ordre de 6 chances sur 100 millions. Comprimer la dispersion de σ autour de sa moyenne (gain Jensen = ½·f''(σ)·Var(σ)) ne peut rapporter, en probabilité absolue, que des fractions de cette quantité déjà minuscule.

**Comparaison de magnitude avec le coût mesuré par L54** : L54 a mesuré un manque à gagner de rendement de (218−21) = **197 bps sur les jours flaggés**, un effet de PREMIER ordre sur l'espérance, mesurable en dizaines/centaines de points de base. Le gain Jensen de survie, à z≈5.3, est de l'ordre de grandeur de la dérivée seconde d'une fonction déjà à 6×10⁻⁸ — **plusieurs ordres de grandeur plus petit** en probabilité absolue de ruine journalière. **Sur une base purement Gaussienne/diffusive, à ce point de fonctionnement, le gain de convexité barrière NE PEUT PAS compenser un manque à gagner de rendement de cette taille.** C'est le calcul quantitatif qui règle, pour la version NAÏVE de l'axe (flag générique de régime de vol, delever proportionnel), la question posée par le mandat : **non, l'argument barrière n'échappe pas à L54 dans sa forme générique.**

### 3.4 Où le calcul change : sauts, pas diffusion, et barrière répétée

Deux angles morts du calcul ci-dessus, qui sont exactement les deux portes de sortie de ce dossier :

**(a) Queues grasses / sauts.** Le calcul gaussien ci-dessus suppose que le risque de queue est de la diffusion (σ plus grand mais toujours gaussien). Les vraies cassures de barrière FTMO viennent de **sauts discrets** (surprise CPI/NFP, gap d'ouverture, flash crash — cf. incident réel du dépôt, breach <ACCOUNT_ID>, USDJPY flash) — un régime où la loi n'est plus gaussienne mais a une composante de saut de Poisson. Sous un mélange saut-diffusion, la probabilité de franchir la barrière sur un jour à risque de saut n'est PAS 6×10⁻⁸ — elle peut être de plusieurs ordres de grandeur plus élevée (queue exponentielle/puissance, pas gaussienne), et surtout **elle est concentrée sur un sous-ensemble de jours identifiables avec certitude à l'avance** : le calendrier des annonces programmées. Sur CES jours-là (et seulement ceux-là), z effectif est beaucoup plus bas (le saut consomme une fraction non négligeable de B directement), et le calcul de §3.3 (z≫√2, gain négligeable) ne s'applique plus — on peut se retrouver dans une zone où le gain de convexité est bien plus grand en valeur absolue, potentiellement comparable au manque à gagner de rendement d'éviter quelques heures autour d'une annonce (un coût BEAUCOUP plus petit que le manque à gagner sur un jour entier flaggé « régime de vol »).

**(b) Barrière répétée, pas terminale unique.** Grossman-Zhou/Cvitanić-Karatzas résolvent un problème à horizon infini avec UNE contrainte de drawdown glissante. La structure FTMO est différente : une barrière **journalière qui se réinitialise chaque jour** (test répété N fois sur l'horizon de la campagne), plus un plancher statique de vie du compte. La probabilité qui compte n'est pas « la vol moyenne de l'année » mais **le maximum sur N tests indépendants (ou faiblement dépendants) du pire jour** — un problème de statistique des valeurs extrêmes, pas de diffusion agrégée. Dans ce cadre, éviter/réduire l'exposition sur les quelques jours qui portent l'essentiel du risque de queue (jours d'annonce) a une valeur disproportionnée par rapport à sa part dans le nombre total de jours — exactement le mécanisme derrière lequel CPPI ajuste son multiplicateur en pratique, et exactement le point qui échappe à un calcul fait en moyenne sur l'année.

**Ces deux portes convergent vers la même conclusion pratique : la version de l'axe qui a une chance de survivre n'est PAS un flag de régime de vol lissé (macro uncertainty index, EPU, GARCH-MIDAS long-run), mais un flag d'ÉVÉNEMENT PROGRAMMÉ DISCRET (CPI/FOMC/NFP à heure connue), qui cible spécifiquement le risque de saut et non la diffusion.**

---

## 4. Le verdict sur L54 — sous quelles conditions précises l'argument barrière y échappe

Synthèse opérationnelle, formulée comme une condition **testable avant toute simulation** (ordre de test imposé, pas de simulation coûteuse avant ce filtre gratuit) :

**Condition de sortie de L54 — trois clauses, toutes nécessaires :**

1. **Orthogonalité du flag** (réutilisation directe de L38/L54) : sur les jours flaggés par le signal macro candidat, le rendement moyen conditionnel du book NE DOIT PAS être significativement positif. Test gratuit, à faire EN PREMIER, avant toute simulation de barrière : `mean(book_return | flag=1)` vs `mean(book_return | flag=0)`, HAC. Si le flag capture un régime tendanciel (comme le flag générique de vol testé par L54), cette clause échoue et le dossier s'arrête là, quel que soit le calcul de convexité.
2. **Nature « saut », pas « diffusion »** : le signal doit cibler des jours à risque de discontinuité identifiable à l'avance avec quasi-certitude (calendrier programmé), pas un indice lissé de régime (EPU, GARCH-MIDAS long-run, incertitude JLN) dont la fréquence naturelle (mensuelle/trimestrielle) est structurellement trop lente pour une barrière journalière (§2.1, §3.4).
3. **Distance de barrière au point de fonctionnement réel** : le calcul de §3.3 doit être refait avec le z RÉEL du jour flaggé (pas le z moyen de l'année) — si le book n'est PAS déjà dimensionné loin de la barrière (z proche de √2 ou en dessous, ce qui NE DEVRAIT PAS arriver sur un compte bien sizé, mais doit être vérifié empiriquement, pas supposé), l'argument de convexité peut s'inverser (zone concave).

**Verdict** : l'argument barrière échappe à L54 **uniquement pour un sous-ensemble étroit de signaux macro** — le calendrier programmé d'annonces à risque de saut — et seulement si la clause 1 (orthogonalité) est vérifiée empiriquement sur CE book, pas supposée. Il n'échappe PAS à L54 pour un signal de régime de vol lissé de type EPU/JLN/GARCH-MIDAS, qui est très probablement corrélé positivement avec les régimes tendanciels qui rémunèrent ce book précis — la même faille que L54 a déjà documentée.

---

## 5. La meilleure version constructible de l'axe (classée)

### Variante 1 (la plus forte) — évitement de fenêtre calendaire programmée, pas overlay de régime

Ne pas construire un score macro composite ni un flag de régime endogène. Utiliser directement le **calendrier connu** des publications à risque de saut (CPI US, décision FOMC, NFP, et équivalents EUR/GBP si le book trade du FX/indices européens) et réduire l'exposition (ou fermer les positions) dans une fenêtre étroite pré-spécifiée autour de l'heure de publication (ex. ±30-60 min), PAS toute la journée. Différences décisives avec ce que L54 a testé :
- Le signal n'est pas un modèle de régime dérivé du book — c'est un fait calendaire externe, connu avec certitude, donc c'est un cas d'orthogonalité *a priori* plausible (à VÉRIFIER, clause 1, pas supposer).
- La fenêtre est étroite (minutes/heures), donc le manque à gagner en moyenne est structurellement borné (une fraction d'une journée), alors que le risque de saut évité est concentré exactement dans cette fenêtre — bien meilleur ratio gain-convexité / coût-moyenne que couper une journée entière.
- C'est directement compatible avec la structure barrière **répétée** de §3.4(b) : on cible le sous-ensemble de tests qui porte le risque de queue, pas la moyenne de l'année.

### Variante 2 — remplacer l'ESTIMATEUR de vol dans le vol-targeting existant, pas ajouter un overlay

Le book a déjà un vol-targeting (Stratégie A : `vol_28d`, vol-targeting quotidien mandaté par les Hard Rules du dépôt). La proposition n'est PAS d'ajouter un flag binaire par-dessus, mais de remplacer l'estimateur de volatilité future (aujourd'hui vol réalisée glissante, par construction RÉTROSPECTIVE et donc en retard sur un choc de régime) par un **nowcast macro-augmenté façon GARCH-MIDAS** (composante long-run pilotée par EPU/JLN) qui anticipe la transition de régime avant que la vol réalisée ne la révèle. Ceci **ne change pas la décision de « couper ou pas »**, seulement la PRÉCISION/PRÉCOCITÉ du dénominateur de sizing déjà en place — un claim de forecasting testable indépendamment de la question « faut-il timer l'exposition sur la vol » (précisément la question tranchée négativement par L54/Moreira-Muir pour ce book). Impact attendu : plus petit, plus diffus, mais moins exposé à l'objection L54 puisqu'il n'introduit aucune décision de coupe discrétionnaire — seulement un lissage/anticipation de la taille déjà déterminée par une règle existante et validée.

**Ce qui NE fait PAS partie de la version défendable** : un score composite macro cross-sectionnel généraliste (déjà falsifié par le round précédent), un flag de régime de vol endogène de type « stress index » calqué sur celui que L54 a testé et fait échouer, ou toute variante qui coupe l'exposition sur la totalité d'une journée flaggée sans distinguer diffusion et saut.

---

## 6. Spécification précise du test de falsification (protocole à exécuter avant tout déploiement)

**Étape 0 — filtre gratuit (clause 1 de §4), à faire avant toute simulation.** Pour chaque candidat de flag (fenêtre calendaire CPI/FOMC/NFP, ou nowcast macro-augmenté), calculer `mean(book_return | flag) − mean(book_return | ¬flag)` en HAC lag-6. Si positif et significatif → ARRÊT, le candidat reproduit la faille de L54, ne pas simuler de barrière.

**Étape 1 — construction des trois politiques à duty cycle apparié.**
- **Baseline B0** : sizing actuel, aucun overlay.
- **Contrôle vol-réalisée C_vol** : dé-levier déclenché uniquement par la vol réalisée récente (ex. percentile glissant de la vol réalisée sur N jours), calibré pour retrancher EXACTEMENT le même nombre de jours-exposition (ou d'heures-exposition pour la Variante 1) et la même réduction moyenne de taille que le candidat macro — **aucune donnée macro, seulement des données de prix**.
- **Variante macro C_macro** : le candidat (fenêtre calendaire ou nowcast), dé-levier calibré au MÊME duty cycle que C_vol (même nombre de jours/heures retranchés, même réduction moyenne de taille).

**Étape 2 — métrique de décision.** Jamais ΔSR (convention déjà établie dans `Portfolio/admission/marginal.py`). Utiliser Δp(pass) et Δdurée médiane de campagne, via le simulateur barrière existant (`Portfolio/risk/trailing_dd_simulator.py` / équivalent Multi_Asset), avec la config FTMO canonique (`Portfolio/risk/propfirm_canonical.py`).

**Étape 3 — critère de PASS.** Le candidat macro passe SI ET SEULEMENT SI Δp(pass)_macro > Δp(pass)_vol-only par une marge excédant l'intervalle de confiance du block-bootstrap (Politis-Romano, jamais iid — cf. hard rules). Autrement dit : **le macro doit battre un contrôle gratuit et déjà disponible (vol réalisée seule), pas simplement battre l'absence d'overlay.** Un ΔSR positif dans le bruit n'est pas un PASS (convention déjà actée pour l'admission de sleeves) — même règle ici.

**Étape 4 — piège d'implémentation à corriger AVANT de lancer la simulation.** À z ≈ 4-6 (§3.3), une simulation Monte Carlo gaussienne standard générera quasiment ZÉRO événement de ruine sur un nombre raisonnable de tirages — impossible de distinguer statistiquement C_macro de C_vol avec un simulateur qui ne produit jamais l'événement qu'on cherche à réduire. Deux corrections obligatoires, pas optionnelles :
  - **Rééchantillonnage historique des pires séances réelles** (pas gaussien) pour calibrer la queue — cohérent avec L57 déjà gravée (« rapporter le skew et la queue single-session de toute sleeve déployée »).
  - **Simulation d'événement rare** (tilting exponentiel / importance sampling, standard en théorie de la ruine actuarielle) si un intervalle de confiance fiable sur p(pass) est requis avec un budget de calcul raisonnable.
  Sans cette correction, tout Δp(pass) mesuré sera du bruit d'échantillonnage, pas un signal — un piège de la même famille que celui déjà documenté sur ce dépôt (placebo apparié qui fabrique un faux PASS, L58).

---

## 7. Conclusion opérationnelle

L'axe « macro prédit le risque, pas le rendement » a une base théorique solide (convexité de p(ruine) en volatilité, §3) et une littérature macro→vol/queue réelle (§2). **Mais, calibré aux chiffres réels du dépôt, l'argument ne sauve PAS la version générique déjà testée et falsifiée par L54** : à la distance de barrière où opère un compte FTMO bien dimensionné, le gain de convexité d'un flag de régime lissé est mathématiquement trop petit pour compenser le manque à gagner en moyenne que L54 a mesuré — et Moreira-Muir confirme, à l'échelle académique, que c'est précisément la condition d'échec attendue quand rendement et vol conditionnels montent ensemble.

**La seule porte de sortie identifiée, précise et testable** : un signal de calendrier programmé (CPI/FOMC/NFP), ciblant le risque de SAUT sur une fenêtre étroite plutôt que la diffusion sur une journée entière, vérifié orthogonal au mécanisme du book (clause 1) AVANT toute simulation, et jugé par Δp(pass) contre un contrôle vol-réalisée à duty cycle apparié (jamais ΔSR) — avec une méthode de simulation d'événement rare, pas gaussienne, faute de quoi le test n'a tout simplement pas la puissance de trancher.

**Ce document ne clôt PAS l'axe.** Il retire la version générique (score/régime macro composite, déjà deux fois falsifiée) et retient deux formulations précises et un protocole de falsification prêt à l'emploi pour la prochaine session de simulation.
