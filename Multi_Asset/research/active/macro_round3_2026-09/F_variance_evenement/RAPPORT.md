# Vendre l'ÉVÉNEMENT, pas son sens — la prime de variance autour des annonces macro

**Round 3, dossier F_variance_evenement — 2026-09-07**
**Mandat** : construire la version la plus défendable de l'axe « vendre l'incertitude implicite
autour d'un événement macro daté (FOMC, CPI, emploi) plutôt que de parier sur son sens », et
spécifier ce qui la falsifierait — PAS rendre un verdict de faisabilité. Δn_tests = 0 : conception
et revue de littérature uniquement, aucune donnée téléchargée, aucun backtest lancé.

---

## 0. Résumé exécutif

**Verdict directionnel : l'axe est VIVANT et NEUF dans ce dépôt, mais il est structurellement
incompatible avec le véhicule FTMO (pas d'options), et la prime documentée dans la littérature
primaire est mesurée en unités qui ne disent pas encore si elle franchit le coût réel retail.**

1. Le dépôt a déjà tué **deux formes voisines mais distinctes** de VRP (§1) : (a) la vente
   mensuelle non conditionnelle sur options réelles (SPY iron condor, coûts réels) — cost-dead,
   SR 0,09 avec IC contenant zéro ; (b) le **timing** de la même prime par seuil VIX_z sur pricing
   synthétique — la prime statique existe (IC +0,152, t 3,671) mais le conditionnement la détruit.
   **Aucune des deux n'est ancrée à un événement macro daté** (FOMC/CPI/emploi) avec fenêtre courte
   — c'est l'angle neuf de ce dossier, pas une répétition.
2. La littérature primaire (Wright 2025 JTSA, Fed Notes 2025-10, Amengual-Xiu 2018, arXiv
   2608.10693) confirme un mécanisme réel et documenté : l'IV implicite se construit **avant**
   l'événement (dès J-2), la vol réalisée ne bouge qu'**après** le début de l'annonce — c'est
   exactement le décalage temporel qu'une vente d'événement doit capturer. La prime est
   **significativement plus grande sur les jours FOMC** (Wright) et diffère par type d'événement :
   CPI 45 pb, emploi 53 pb, FOMC 49 pb (annualisés, Fed Notes 2025).
3. **LE VÉHICULE TUE LE COMPTE FTMO EN PREMIER, PAS EN DERNIER : FTMO ne propose aucune option.**
   Cet axe ne peut vivre que sur le compte personnel IBKR (€13k), jamais sur le funded CFD à
   plancher statique. C'est un fait structurel, pas un risque à mitiger.
4. Sur le compte personnel, le véhicule le plus défendable est **XSP** (mini-SPX, multiplicateur
   ×100, cash-settled, européen — pas d'exercice anticipé) via IBKR EU (accessible sous PRIIPs par
   account-flagging) — SPX lui-même est trop gros en notionnel pour €13k (une seule straddle ATM
   peut valoir plusieurs milliers de dollars).
5. **Le risque de queue n'est pas une nuance, c'est le point de rupture.** La même famille
   (vente de variance) mesurée dans ce dépôt affiche skew −4,86 / kurtosis +45 / pire mois à
   −64× la moyenne. Le 13 septembre 2022, un CPI raté de 0,2 point de pourcentage a fait perdre
   4,32 % au S&P 500 en une séance — un mouvement qu'aucune straddle vendue à un prix raisonnable
   n'aurait absorbé. Cette forme de distribution est **la pire configuration possible** devant une
   barrière statique (Amengual : p(ruine) est convexe en vol seulement en régime, et le régime
   n'aide qu'à la marge une fois la barrière loin ; ici on parle de sauts, pas de régime).
6. **Ce qui la falsifie, précisément (§7)** : le pré-flight `brut/coût_p95 ≥ 1,5` mesuré sur XSP
   réel (pas sur une formule VIX²−RV synthétique) ; le `N_eff` de la breadth une fois la
   corrélation inter-événements comptée ; et — condition non négociable pour ce compte — une
   structure à risque défini (pas de straddle nue) dont la perte maximale par événement est connue
   à l'avance et bornée à un budget de risque explicite.

---

## 1. Ce que le dépôt a déjà tué, et ce qu'il ne tue PAS

Balayage exécuté avant toute recherche externe :
`grep -ril "vrp\|variance risk\|straddle\|implied\|option" --include='*.md' .` (30 fichiers),
`research_history.md`, `_meta/lessons_registry.md`, et les mémoires de session
(`vrp_options_real_data_2026-07.md`, `sharpe231_doc_audit`, etc.).

### 1.1 Verdict A — SPY iron condor sur données réelles : COST-DEAD (2026-07)

`Options_Vol/research/archived/vrp_spx_angle_c/` et mémoire `vrp_options_real_data_2026-07.md`.
Iron condor mensuel 16Δ/10Δ, ~35 DTE, sur chaînes d'options **réelles** (Kaggle
`dudesurfin/spy-options-eod-volatility-surface-2010-2023`, bid/ask réels des deux côtés) :

| Variante | Sharpe | Lecture |
|---|--:|---|
| Hold-to-expiry, cross-spread | **0,09** (IC95 [−0,39; 0,74]) | zéro statistique |
| + hedge de queue au skew réel (put −4Δ à l'ask réel) | **−0,51** | le hedge **saigne**, il n'est pas gratuit |
| Géré (tastytrade 50%PT/21DTE), mid-fills | −0,05 | optimiste, quasi inatteignable sur 4 jambes |
| Géré, cross-spread réaliste | **−0,55** | réaliste |

**Ce que ça tue** : toute idée qu'un « VRP sûr » existe au tarif retail avec du pricing
synthétique (flat-VIX, sans skew). Le skew réel rend le hedge de queue coûteux, pas protecteur.
**Ce que ça ne tue PAS** : c'est un test **mensuel, non conditionnel, sans ancrage événementiel**
— aucune tentative de vendre spécifiquement autour d'un CPI/FOMC/emploi daté à fenêtre courte.

### 1.2 Verdict B — SPX VRP Angle C (timing VIX_z, pricing synthétique) : IC gate FAIL (2026-05)

`Options_Vol/research/archived/vrp_spx_angle_c/POSTMORTEM.md`. Straddle ATM courte vendue selon
un seuil `VIX_z > 1,0`, P&L proxy par approximation VIX² (**pas** de chaîne d'options réelle) :

- **Prime statique non conditionnelle : IC = +0,152, t_HAC = 3,671** sur tout l'échantillon —
  la prime existe.
- **Conditionner sur VIX_z > 1,0 la détruit** : IC = −0,009, t_HAC = −0,144. Le seuil sélectionne
  exactement les régimes où la vol réalisée peut dépasser l'implicite (COVID, inflation 2022) —
  paradoxe de sélection : le déclencheur touche la zone de danger, pas la zone de profit.
- **Leçon portée par ce verdict, directement pertinente ici** : *timer* une prime statique par un
  seuil de régime ne marche pas mieux que la vendre en continu ; le risque de queue n'est pas un
  problème de timing, il est intrinsèque à la structure.

**Ce que ça tue** : un filtre de régime binaire naïf comme sélecteur de moments favorables.
**Ce que ça ne tue PAS** : un filtre événementiel (CPI/FOMC/emploi daté), qui est une catégorie
différente d'un seuil de régime continu — l'agent A du round 2 (macro→risque) a d'ailleurs conclu
que **seule la coupe événementielle bornée** de ce type survit, la version « régime de vol »
généraliste étant, elle, réfutée (`macro_round2_2026-09/SYNTHESE_ROUND2.md` §1, axe A).

### 1.3 L13 — l'erreur d'unité, à ne pas refaire

`_meta/lessons_registry.md:15` : *« VRP unit error: academic VRP is variance units, not %
notional. B-S conv: BTC gross ~4.4%/yr vs costs 8.9%/yr → net -4.46%/yr. »* Tout chiffre de
prime cité plus bas dans ce dossier (pb annualisés, points de vol) doit être reconverti en
notionnel réel de la structure choisie avant toute comparaison au coût — ne jamais comparer un
pourcentage de variance à un pourcentage de prix sans passer par la formule de conversion.

### 1.4 Le « meilleur edge trouvé » du dépôt est la même famille, et il porte l'avertissement

`yt_strategy_replications/VALIDATED_EDGES.md` et `.../reports/module_5_structural_edges.md` : le
**seul edge jugé réel et significatif sur 13 stratégies testées dans 5 vidéos** est la vente de
variance implicite VIX contre variance réalisée SPY, non-conditionnelle, mensuelle, non
chevauchante, 2004-2026 (methodologie **VIX²−RV, donc synthétique, pas P&L d'options réelles** —
même limite que §1.2, à ne pas confondre avec un edge net de coûts) :

| Métrique | Valeur |
|---|--:|
| Mois où IV > RV réalisée à terme | **83,7 %** |
| Sharpe annualisé | **+0,52** |
| Skew / kurtosis | **−4,86 / +45** |
| Pire mois ÷ moyenne | **−64×** |
| Drawdown cumulé (proxy) | **−53 %** |

Le fichier conclut explicitement : *"Naive OTM-option selling is how undercapitalised traders
blow up (Feb 2018 'Volmageddon,' Mar 2020). Tradable only with hard tail hedging / position
limits / regime gating."* C'est la même conclusion que ce dossier doit tirer pour la version
événementielle — avec en plus la contrainte du plancher statique FTMO (**qui ne s'applique
d'ailleurs pas ici, cf. §4**, puisque le véhicule funded ne fait pas d'options).

### 1.5 Le programme macro round 2 (5 axes, 2026-09-06) n'a PAS testé cet axe

`macro_round2_2026-09/SYNTHESE_ROUND2.md` couvre cinq axes (B3 drift post-annonce taux, D carry
conditionné, A macro→risque, E nowcast−consensus, C dispersion). **Aucun ne vend de la variance
d'option autour d'un événement.** Le plus proche, l'axe A, conclut l'inverse de cet axe : il
recommande de **couper l'exposition** dans la fenêtre événementielle pour se protéger d'un saut
(la géométrie du book déployé « rate » déjà FOMC et les événements européens — protection
gratuite). Vendre une straddle sur cette même fenêtre est le pari **contraire** : parier que le
saut ne se matérialisera pas au-delà de ce qui est déjà pricé. Les deux ne se contredisent pas
forcément (l'un gère un book existant, l'autre est une position nouvelle) mais partagent le même
risque sous-jacent — l'agent A a mesuré que only bounded event-window cuts survivent, pas les
coupes de régime généralistes ; la leçon candidate F du round 2 (*« une prime de résolution
d'incertitude n'a pas de jambe symétrique par construction »*) s'applique **conceptuellement** ici
aussi : une vente de variance événementielle n'a pas de miroir testable en two-sided — le test
pertinent n'est pas directionnel, il est sur la magnitude (implicite vs réalisé), voir §7.

**Conclusion du balayage : l'axe « vendre l'événement macro par options, fenêtre courte, ancré à
une date de publication » n'a jamais été testé dans ce dépôt. Ce qui a été tué, c'est (a) la
version mensuelle continue sur options réelles, (b) le timing par seuil de régime continu sur
pricing synthétique. Ni l'un ni l'autre ne couvre l'ancrage événementiel à fenêtre courte.**

---

## 2. La prime de risque de variance autour des annonces — littérature primaire

### 2.1 Le mécanisme documenté : l'implicite se construit avant, le réalisé bouge après

**Wright, J. (2025), "Event-Day Options", Journal of Time Series Analysis** (NBER WP 28306,
2021) — options hebdomadaires sur futures Treasury et actions expirant chaque mercredi/vendredi,
comparées la veille des jours FOMC et des jours d'emploi contre les mardis/jeudis ordinaires.
Résultat central, cité verbatim : *« Average variance risk premia are large and significantly
positive, especially for FOMC days. »* L'auteur construit aussi des densités risque-neutre
implicites la veille de ces publications — la prime FOMC domine la prime emploi.

**Arxiv 2608.10693, "When the Fed Speaks: Dynamics and Forecasts of the Volatility Surface"**
(2026, options SPX CBOE, 2016-2025) — le résultat le plus directement actionnable pour ce
dossier :
- L'IV **0DTE** (options expirant le jour même) monte **jusqu'à +50 %** relativement aux jours
  ordinaires, avec un début de hausse statistiquement significatif **dès J-1**, et un
  frémissement dès J-2.
- Terme structure très abrupte : l'effet est concentré sur le très court terme (2 jours et moins) ;
  à 10 jours de maturité, **quasi aucun effet**.
- **Le point de rupture temporel** : *« the realised volatility only starts rising after the
  start of the FOMC conference »* — la vol implicite anticipe, la vol réalisée réagit. C'est
  précisément la fenêtre exploitable : vendre entre J-2/J-1 et la clôture après l'annonce.
- ⚠ Les auteurs eux-mêmes : *« our results lack the verification in an actual trading
  environment »* — aucune analyse de coût, aucun test de rentabilité nette. Le papier documente
  le mécanisme, pas sa tradabilité.

**Amengual, D. & Xiu, D. (2018), "Resolution of Policy Uncertainty and Sudden Declines in
Volatility", Journal of Econometrics 203(2), 297-315.** Sauts de vol à la baisse liés à la
résolution de l'incertitude de politique monétaire, essentiellement via les communiqués FOMC et
les discours du président de la Fed. Un modèle log-vol avec au moins un facteur Ornstein-
Uhlenbeck et des sauts à double sens domine, dans leur évaluation, un modèle affine standard pour
capturer cette dynamique et pricer des variance swaps. **Avertissement méthodologique central des
auteurs, à retenir** : ignorer ces sauts biaise les estimations de la prime de risque de variance
— tout calcul naïf de VRP autour de FOMC qui ne modélise pas le saut comme composante à part
risque de surestimer la prime « pure ».

### 2.2 Magnitude documentée par type d'événement

**Fed Notes, "Which Days Matter for Global Equity Markets? Using Options to Price Events in the
Global Calendar" (2025-10-03).** Prime de risque équity implicite (annualisée, points de base),
extraite d'options quotidiennes sur indices, S&P 500 et Stoxx 50, échantillon **sept. 2023 –
juil. 2025** :

| Événement | Marché testé | Prime annualisée |
|---|---|--:|
| CPI américain | S&P 500 (domestique) | **45 pb** |
| Emploi américain (NFP) | S&P 500 (domestique) | **53 pb** |
| FOMC (taux directeur) | S&P 500 (domestique) | **49 pb** |
| CPI américain (spillover) | Stoxx 50 | 24 pb |
| Emploi américain (spillover) | Stoxx 50 | 35 pb |
| CPI zone euro (domestique) | Stoxx 50 | 31 pb |
| BCE (taux directeur) | Stoxx 50 | 28 pb |
| CPI zone euro (spillover) | S&P 500 | 18 pb |

Le CPI zone euro du 29 septembre 2023 a payé une prime jusqu'à **+79 % plus élevée** que les jours
environnants côté euro et **+77 %** côté américain — preuve que la prime elle-même a de la
variance et n'est pas une constante à extrapoler linéairement.

⚠ **Ces chiffres sont des primes de risque annualisées au sens de la construction en variance
forward, PAS un rendement de straddle en pourcentage de prime engagée.** Convertir cette prime en
un rendement de position réelle (vol points capturés par événement, ou % de la prime vendue)
exige une étape de reconstruction que ce dossier ne fait pas — c'est explicitement la Phase 1 de
falsification (§7). Ne jamais citer ce tableau comme un Sharpe ou un edge net.

**Non-Spanning Identification of Scheduled Event Risk in Option Pricing (arXiv 2606.12872v2,
2026)** — options SPX PM-settled, **mai 2022 – août 2025**, 101 événements exploitables (**39
CPI, 23 FOMC, 39 NFP**). Résultat qui affine la sélection d'événements pour ce dossier : un
modèle à sauts d'événement (gaussien / mixture) améliore nettement le pricing hors-échantillon
pour **CPI et FOMC**, plus faiblement pour **NFP** — *« gains strongest for CPI and FOMC, weaker
for NFP »*. Traduction opérationnelle : la structure de risque d'événement est **mieux définie
et plus stable** sur CPI/FOMC que sur l'emploi, malgré une prime brute (Fed Notes) plus élevée sur
NFP. C'est un arbitrage direct entre magnitude (NFP gagne) et propreté du mécanisme (CPI/FOMC
gagnent) — à trancher empiriquement, pas par supposition.

**Beber, A. & Brandt, M. (Review of Finance, "Pricing event risk: evidence from concave implied
volatility curves")** — établit que les rendements de straddles delta-neutres (et strangles, et
calendar straddles vega-neutres) sont **négatifs et significativement plus bas** en présence de
courbes IV concaves avant une date d'annonce. Mécanisme : la concavité reflète une distribution
risque-neutre **bimodale** (le marché price « le prix montera de x% OU baissera de y% », pas une
diffusion continue) — cette bimodalité fait payer aux acheteurs de straddle une prime de gamma
substantielle. **C'est la confirmation académique la plus directe que les vendeurs de straddle
d'événement sont historiquement du bon côté du trade en moyenne** — chiffre exact non extrait
(accès restreint), mais le signe et le mécanisme sont confirmés par une source indépendante des
papiers Fed déjà cités.

### 2.3 Ce que la littérature ne dit PAS (à ne pas halluciner)

Aucune des sources primaires consultées ne fournit : un Sharpe net de coûts pour une stratégie de
vente d'événement ; une distribution de queue (skew/kurtosis) spécifique à la fenêtre événementielle
courte (le −4,86/+45 du §1.4 vient du VRP mensuel continu, pas d'un test événementiel) ; ni un
chiffre de bid-ask réel sur XSP/SPX aux dates d'événement. Ce sont exactement les trous que la
Phase 1 (§7) doit combler avant tout code.

---

## 3. Le risque de queue — le point qui tue habituellement cette famille

### 3.1 La forme documentée dans ce dépôt

§1.4 : skew −4,86, kurtosis +45, pire mois à **−64× la moyenne** des mois gagnants, sur la version
mensuelle continue. Cette forme n'est PAS spécifique à la fenêtre événementielle courte (aucune
mesure interne n'existe pour elle), mais elle caractérise **la famille** — vendre de la variance
produit structurellement ce type de distribution, indépendamment de l'horizon, car le mécanisme
générateur (compensation pour risque de queue, Carr-Wu 2009, Bondarenko) est le même.

### 3.2 Le pire événement historique documenté, et pourquoi il est structurellement pertinent ici

**5 février 2018 (« Volmageddon »)** — déclenché par un rapport emploi publié le 2 février (le
même TYPE d'événement que ce dossier cible), montrant une croissance des salaires à 2,9 %, la plus
rapide en huit ans. Le VIX est passé de 18,44 à l'ouverture à 37,32 à la clôture le 5 février —
**+115 % en une séance, le plus grand mouvement journalier de son histoire**. Les produits short-vol
(XIV, SVXY) ont perdu plus de 90 % de leur valeur en une journée par un mécanisme de boucle de
rétroaction (rachat forcé de futures VIX pour rester delta-neutres). **Ce n'est pas un simple
accident de marché : c'est un rapport d'emploi qui a déclenché la chaîne.**

**13 septembre 2022 (CPI américain)** — l'inflation cœur a surpris de **0,2 point de pourcentage**
(hausse de 0,1 % au lieu de la baisse de 0,1 % attendue). Le S&P 500 a chuté de **−4,32 %** en une
séance, sa pire journée depuis juin 2020, le Nasdaq **−5,2 %**. Un écart de consensus minuscule
(0,2 pt) a produit un mouvement de marché que quasiment aucune straddle vendue à un prix
raisonnable n'aurait absorbé sans perte substantielle — c'est l'exemple concret et daté qui
illustre pourquoi une vente d'ATM straddle nue sur CPI est structurellement dangereuse : la
distribution des surprises macro n'a pas de rapport stable avec la magnitude du mouvement de
marché qu'elles déclenchent.

### 3.3 Compatibilité avec une barrière statique — le point que le round 2 a déjà tranché

`macro_round2_2026-09/SYNTHESE_ROUND2.md` §3.1 (falsification de ma propre hypothèse round 2) :
la convexité de p(ruine) en volatilité **existe** (z > √2 pour un compte FTMO, z ≈ 4-6), mais à
cette distance de la barrière **φ(z) s'effondre** — le gain de convexité devient négligeable face
au manque à gagner en moyenne. Ce résultat concernait un **overlay de régime continu**, pas un saut
discret. **Un saut discret est un cas différent et pire** : ce n'est pas une variance qui monte
progressivement (contre laquelle un dé-levier a le temps d'agir), c'est un déplacement de prix en
une barre qui peut directement traverser la barrière quel que soit le z de départ — exactement le
mécanisme du 13 septembre 2022 (−4,32 % en une séance, sans avertissement intra-journalier
utilisable). **Une structure à skew −4,86/kurtosis +45 est, par construction, la forme la plus
incompatible qui soit avec un compte à plancher statique** — mais voir §4 : le point n'est même
pas là, puisque ce compte n'a pas accès aux options.

---

## 4. LE VÉHICULE — à traiter en premier, comme demandé

### 4.1 Le compte FTMO funded ne peut PAS exécuter cet axe. Point.

FTMO est un CFD broker (forex, indices CFD, métaux, crypto, quelques actions CFD) — **il ne
propose aucun contrat d'option**. Toute la mécanique de ce dossier (vendre une prime implicite
matérialisée par un prix d'option) est **structurellement inexécutable** sur le véhicule funded.
Ce n'est pas un risque à mitiger avec un filtre ou un sizing plus prudent : c'est une incompatibilité
de catégorie, comme le crypto/delta-neutral l'est déjà pour les propfirms (cf. CLAUDE.md, section
Portfolio context). **Il faut le dire tôt et fort, comme demandé : cet axe ne concerne QUE le
compte personnel €13k, jamais le book funded.**

### 4.2 Le compte personnel : SPX est trop gros, XSP est le véhicule qui tient

- **SPX (options standard sur indice)** — multiplicateur ×100 sur le niveau plein de l'indice
  (~6 000+ en 2026). Une straddle ATM à ~30-45 jours peut coûter plusieurs milliers de dollars de
  prime engagée par contrat ; même à horizon événementiel court (prime plus faible car moins de
  temps-valeur, mais IV rehaussée par l'effet §2.1), le notionnel sous-jacent par contrat (~600 000
  $) est disproportionné pour un compte de 13 000 €. Impossible de diversifier sur plusieurs
  événements simultanément sans concentrer tout le capital sur un seul contrat.
- **XSP (mini-SPX)** — 1/10 de la taille de SPX (multiplicateur ×100 sur un indice à 1/10 du
  niveau), **cash-settled, exercice européen** (pas de risque d'assignation anticipée — important
  pour une position tenue sur un week-end ou une nuit d'événement). Volume quotidien courant :
  50 000 à 150 000 contrats, spreads resserrés sur les strikes ATM et les échéances hebdomadaires,
  mais **2 à 5 cents plus larges que sur SPX en relatif** pour les échéances courtes. Pour des
  tailles de position retail (1-20 contrats), gérable en ordre limite au midpoint ; au-delà de
  50 contrats, le slippage devient significatif — non pertinent à €13k, où la taille de position
  restera de toute façon dans la fourchette gérable.
- **Accès EU/PRIIPs** : IBKR (IBIE) reste, dans les sources consultées, le courtier qui donne accès
  à la chaîne complète SPX/XSP pour un client de détail européen via un flagging au niveau du
  compte (questionnaire de connaissance/expérience, acceptation des produits sans KID) — les
  options listées classiques ne sont pas des PRIIPs « packagés » au même titre qu'un ETF à levier,
  mais **ce point n'est pas vérifié de première main dans ce dossier** (sources secondaires
  seulement) : à confirmer directement auprès d'IBKR avant tout engagement de capital.
- **Risque de change** : compte probablement libellé EUR, options XSP/SPX réglées en USD. Le P&L
  et la marge portent un risque de change non couvert par défaut — à budgéter séparément, ne
  jamais l'oublier dans un calcul de Sharpe net.

### 4.3 Substituts sans option — mesurés, pas supposés

- **Futures VIX / Mini VIX (/VXM)** — capture la structure par terme du VIX (le « kink » construit
  puis résorbé autour de FOMC, §2.1 arXiv 2608.10693), mais c'est une prime **différente** (portage
  de la structure par terme, pas la variance réalisée vs implicite d'un sous-jacent equity
  spécifique). Marge Mini VIX ~1 800-2 800 $/contrat (VX standard : 8 000-12 000 $) — tient dans
  13k€ mais en granularité fine (quelques contrats maximum), ce qui rouvre le problème de
  granularité déjà documenté en interne (L57 : lot minimum interdit le vol-targeting fin). **Le
  dépôt a déjà testé — et TUÉ 3 fois — la version calendaire non-événementielle de ce trade** :
  `ETF_Vol/research/archived/vix_term_carry/`, root cause = drag de roulement de l'ETF, alpha de
  timing quasi nul vs. short-VIXY statique (α t = 0,711). Le phase0 des VRP options notait déjà
  que la version **futures directe** (pas ETF) pourrait contourner ce problème de véhicule mais
  **n'a jamais été testée** — c'est un angle rouvrable (catégorie véhicule, politique de
  ré-ouverture 2026-07-30), pas une répétition interdite, mais distinct de la vente d'option pure
  ciblée par ce dossier.
- **Réplication delta-neutre sans options (variance swap synthétique via futures + rebalancement)**
  : mécaniquement possible mais demande un rebalancement delta quasi-continu autour de l'annonce —
  coût de rebalancement (spread + slippage sur chaque ajustement) probablement du même ordre de
  grandeur que la prime cherchée (45-53 pb annualisés, §2.2) ; non chiffré ici, à traiter comme un
  gate de coût, pas une hypothèse.

**Conclusion véhicule : XSP sur IBKR est le seul candidat qui tient sans hypothèse
supplémentaire. Le pré-flight de coût réel sur XSP (bid-ask mesuré, pas supposé) est un
prérequis absolu avant tout code — voir §7.**

---

## 5. La breadth — honnêtement comptée

**Nominal : ~8 FOMC + ~12 CPI + ~12 emploi (NFP) = ~32 événements/an**, datés, connus à l'avance,
non chevauchants en général (mais parfois la même semaine — CPI et FOMC tombent occasionnellement
dans la même fenêtre calendaire, ce qui réduit l'indépendance). Confirmé indépendamment par le
comptage d'événements de l'arXiv 2606.12872v2 (39 CPI + 23 FOMC + 39 NFP sur mai 2022-août 2025,
soit ~3,3 ans → ~12/12/7 par an, cohérent avec le nominal).

**Ce que le round 2 a déjà établi et qui s'applique ici sans nouvelle dérivation** (§B3,
`SYNTHESE_ROUND2.md`) : *« chaque banque centrale compte comme un test AMTP séparé »* et les
fenêtres de drift/vol autour d'événements macro-financiers sont **chevauchantes** dans le temps —
tous les événements macro-US partagent un facteur commun de régime de vol globale (le VIX monte
ou baisse en bloc, pas événement par événement indépendamment). **N_eff < 32.**

Deux effondrements à quantifier avant tout backtest, exactement comme le round 1 l'a fait pour le
score macro cross-sectionnel (`macro_score_2026-09/SYNTHESE.md` §2) :
- **Corrélation inter-type** : CPI, FOMC et NFP se produisent tous en régime macro similaire
  (2022-2023 = vol élevée sur les trois types simultanément, 2017 ou 2024-2025 calmes sur les
  trois). Si la corrélation résiduelle du P&L entre types d'événements reste élevée une fois le
  facteur commun de régime retiré, la breadth effective se rapproche de 3 (un pari par régime de
  vol, pas 32).
- **Mémoire courte, contrairement au score continu** : chaque événement se résout (§7.5 du round 2,
  E-nowcast) — pas de noyau de décroissance lent à soustraire ici, contrairement à l'indice de
  surprise Citi (demi-vie 45j). C'est un avantage net de cet axe sur les axes A-E du round 2 :
  la breadth n'est pas rongée par l'autocorrélation temporelle, seulement par la corrélation
  transversale entre types d'événement.

**Valeur défendable : 8 à 15 paris indépendants par an**, pas 32 — à vérifier empiriquement
(module `breadth.py` déjà spécifié par le round 2, réutilisable tel quel), jamais supposé.

---

## 6. LA VERSION LA PLUS FORTE DE L'AXE

Synthèse de conception, pas un test :

1. **Instrument** : XSP, IBKR, EU. Jamais SPX (notionnel) pour ce compte.
2. **Structure** : **à risque défini dès le départ** — iron condor ou credit spread à ailes
   étroites, jamais de straddle/strangle nue. Le dépôt a déjà mesuré que le « hedge de queue »
   acheté séparément **saigne** au skew réel (§1.1, SR −0,51) : la protection honnête n'est pas un
   hedge ajouté après-coup, c'est une structure dont la perte maximale est connue à la
   construction. Perte max par événement plafonnée à un budget de risque explicite (à fixer en
   Phase 0, jamais après avoir vu les résultats).
3. **Fenêtre** : ouverture J-1 à J-2 (là où l'IV commence à monter, §2.1), fermeture à la clôture
   du jour de l'annonce ou au plus tard J+1 — jamais tenue jusqu'à expiration si l'expiration
   dépasse la fenêtre de résorption de l'IV documentée (le « crush » se produit dans les heures/
   jour qui suivent l'annonce, pas sur plusieurs semaines).
4. **Sélection d'événements** : prioriser CPI et FOMC sur NFP — le NFP porte la prime brute la
   plus élevée (53 pb, Fed Notes) MAIS la structure de saut la moins bien modélisée (arXiv
   2606.12872v2 : gains de modèle « weaker for NFP ») — c'est un arbitrage magnitude vs propreté
   du mécanisme à trancher empiriquement, pas par défaut.
5. **Filtre de régime** : à construire, mais avec la leçon de l'Angle C en tête (§1.2) — un seuil
   qui *coupe l'exposition* en régime déjà dangereux (VIX élevé, term structure backwardée) est
   probablement plus robuste qu'un seuil qui *sélectionne* les moments d'entrée, car c'est
   exactement l'inverse qui a échoué (le seuil sélectionnait la zone de danger). À tester comme
   filtre d'ÉVITEMENT, jamais comme timer d'entrée.
6. **Sizing** : par budget de perte maximale (connu grâce à la structure à risque défini), jamais
   par Sharpe historique d'une prime qui n'a pas encore été mesurée nette de coûts réels.

---

## 7. Ce qui FALSIFIE cet axe — spécifié avant tout code

### Phase 0 — pré-enregistrement (aucune donnée)
- Liste close des événements (CPI + FOMC en priorité, NFP en secondaire), fenêtre d'entrée/sortie
  gelée, structure (iron condor, largeur d'ailes) gelée, budget de perte max par événement gelé.
- Geler la métrique : vol points capturés nets de coût, PAS un Sharpe théorique sur pricing
  VIX²−RV synthétique (répéter cette erreur reproduirait exactement §1.4/§1.2).

### Phase 1 — le gate qui décide tout, avant tout autre travail
**`brut/coût_p95 ≥ 1,5` (seuil L43), mesuré sur XSP réel** : bid-ask observé sur les strikes ATM
concernés dans les jours précédant un échantillon d'événements passés (ou, à défaut de données
tick historiques XSP, un relevé live sur plusieurs cycles CPI/FOMC avant tout engagement de
capital). **Si ce ratio est sous 1,5, l'axe se ferme mécaniquement, comme la SPY iron condor
(§1.1) s'est fermée sur le même type de gate.** C'est le test le moins cher et le plus décisif —
à faire en premier, avant la moindre ligne d'event-study.

### Phase 2 — breadth réelle
Calculer `N_eff` (corrélation inter-événements + absence de mémoire temporelle, §5) avant de citer
un seul t-stat. Un t-stat sans `N_eff` à côté est refusé par construction (discipline héritée du
round 2, module `breadth.py`).

### Phase 3 — étude d'événement, coût mesuré, queue non tronquée
- Étude d'événement en rendements/points de vol réalisés vs implicites, HAC dimensionné sur la
  fenêtre courte (pas de dérogation lag-45 nécessaire ici, contrairement à l'axe B3 du round 2 —
  la mémoire est courte).
- **La queue ne se coupe pas** : le 13 septembre 2022 et l'équivalent CPI/FOMC doivent apparaître
  dans l'échantillon de test s'ils tombent dans la période choisie. Un test qui exclut les pires
  événements pour améliorer le Sharkpe apparent est un test frauduleux au sens des lessons déjà
  gravées (L58 : valider tout placebo/filtre contre l'espérance inconditionnelle, jamais contre un
  sous-échantillon choisi après coup).
- Effet/MDE à 80 % de puissance, pas seulement le t-stat — avec N_eff ~8-15/an, un échantillon de
  5 ans donne 40-75 paris effectifs : rapporter explicitement la taille d'effet minimale détectable
  à cette taille avant de conclure à un « edge ».

### Phase 4 — compatibilité barrière (uniquement si Phase 1-3 passent)
Même sur le compte personnel sans plancher formel, chiffrer la queue (skew, kurtosis, pire
événement en unités de compte, pas en %) et vérifier qu'un seul événement mal tombé ne consomme
pas plus qu'un budget de perte annuel prédéfini — sinon la structure a été mal dimensionnée en
Phase 0, retour à la case départ, pas d'ajustement post-hoc.

**Falsificateur unique et suffisant, s'il faut n'en retenir qu'un** : si le ratio brut/coût mesuré
sur XSP réel (Phase 1) est sous 1,5, l'axe est mort — exactement le même motif de mort que la SPY
iron condor (§1.1) et que le FX intraday (L43) : un edge institutionnel réel (§2, sources
académiques, tier de coût sub-bps) qui ne survit pas au tier de coût retail (spreads en dizaines
de points de base, pas en points de base uniques). C'est l'hypothèse par défaut à réfuter, pas à
confirmer.

---

## Sources

- Wright, J. (2025 / NBER WP 28306, 2021), *Event-Day Options*, Journal of Time Series Analysis. https://onlinelibrary.wiley.com/doi/10.1111/jtsa.12819 · https://www.nber.org/papers/w28306
- Federal Reserve, FEDS Notes (2025-10-03), *Which Days Matter for Global Equity Markets? Using Options to Price Events in the Global Calendar*. https://www.federalreserve.gov/econres/notes/feds-notes/which-days-matter-for-global-equity-markets-using-options-to-price-events-in-the-global-calendar-20251003.html
- Amengual, D. & Xiu, D. (2018), *Resolution of Policy Uncertainty and Sudden Declines in Volatility*, Journal of Econometrics 203(2), 297-315. https://www.ssrn.com/abstract=2348137 · https://dachxiu.chicagobooth.edu/download/VOLJUMP.pdf
- Arxiv 2608.10693 (2026), *When the Fed Speaks: Dynamics and Forecasts of the Volatility Surface*. https://arxiv.org/html/2608.10693
- Arxiv 2606.12872v2 (2026), *Non-Spanning Identification of Scheduled Event Risk in Option Pricing*. https://arxiv.org/html/2606.12872v2
- Beber, A. & Brandt, M., *Pricing event risk: evidence from concave implied volatility curves*, Review of Finance. https://academic.oup.com/rof/article/29/4/963/8079062
- CNBC (2022-09-13) et Forbes (2022-09-13) sur la séance CPI du 13 septembre 2022 (S&P −4,32 %).
- CFA Institute (2021), *Volmageddon and the Failure of Short Volatility Products*. https://rpc.cfainstitute.org/research/financial-analysts-journal/2021/volmageddon-failure-short-volatility-products
- Repo interne : `Options_Vol/research/archived/vrp_spx_angle_c/` (POSTMORTEM.md, phase0_bootstrap.md), mémoire `vrp_options_real_data_2026-07.md`, `yt_strategy_replications/VALIDATED_EDGES.md` + `reports/module_5_structural_edges.md`, `_meta/lessons_registry.md` (L13), `Multi_Asset/research/active/macro_round2_2026-09/SYNTHESE_ROUND2.md`, `Multi_Asset/research/active/macro_score_2026-09/SYNTHESE.md`.
- Recherches secondaires non vérifiées de première main (à confirmer avant usage) : spreads XSP/SPX 0DTE, accès IBKR EU sous PRIIPs, marges VIX futures/Mini VIX — sources agrégées par moteur de recherche, citées comme indicatives §4, jamais comme mesurées.
