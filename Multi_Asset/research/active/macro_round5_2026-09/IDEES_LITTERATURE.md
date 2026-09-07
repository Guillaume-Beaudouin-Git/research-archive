# Macro round 5 — idées issues du corpus académique et des ouvrages de référence

**2026-09-07.** Mandat distinct des rounds 1-4 : ne pas re-balayer le web généraliste, mais
exploiter le corpus **livres de référence quant/macro + revues à comité de lecture** — ce qui vit
dans Ilmanen, Pedersen, Grinold-Kahn, López de Prado, Carver, Burstein, Drobny et les revues
(JFE/RFS/JF/JPM/FAJ/JFI), souvent absent d'une recherche web classique. Δn_tests = 0 : aucune
donnée téléchargée, aucun backtest lancé, aucun fichier modifié hors de ce dossier. Aucun accès
direct au texte intégral des ouvrages cités (pas de PDF/scan disponible dans cette session) : les
citations reposent sur ma connaissance de leur contenu et, pour les points chiffrés, sur les
articles à comité de lecture qui les recoupent ou les précèdent — jamais un numéro de page inventé.
Quand un numéro de chapitre m'est incertain, je l'indique explicitement comme non vérifié.

## Balayage effectué (obligatoire, disque + git)

Lu intégralement : `CLAUDE.md`, `_meta/lessons_registry.md` (L11→L67 + candidates), extrait de
`research_history.md`, `Multi_Asset/research/active/macro_score_2026-09/{SYNTHESE.md,
01_academique/RAPPORT.md}` (le rapport académique du round 1 — lu en entier, c'est la référence la
plus proche de ce mandat et je m'en sers pour éviter tout doublon), `SYNTHESE_ROUND2.md`,
`SYNTHESE_ROUND3.md`, `macro_review_2026-09/REVUE_INDEPENDANTE.md` (en entier), `macro_round4_2026-
09/IDEES.md` (en entier). `find`/`grep -r` sur le disque réel (pas seulement `git ls-files`),
y compris `.worktrees/` (aucun chantier macro non recensé par les synthèses déjà lues). Vérifié
spécifiquement, pour éviter de reproposer sous un autre nom :
- `Forex/research/active/g2d_carry_cross_asset/report_v1.md` — le carry cross-asset (Koijen-
  Moskowitz-Pedersen-Vrugt, *JFE* 2018) est **déjà** un dossier vivant complet (verdict :
  conditionnel oui, capital minimum $50-100k, meilleur sur bonds+commodités, FX exclu) — je
  n'aborde donc PAS le carry cross-asset ci-dessous, il est pris.
- `Multi_Asset/research/active/forced_flow_cooccurrence_2026-08/RESULTS.md` — **REJECTED** :
  month-end, quarter-end, triple-swap, OPEX, roll de futures et rebalancement d'indice, seuls et
  co-occurrents, ont déjà été testés (19 instruments, 59 687 jours-instrument) et rendent une
  courbe de dose plate une fois les confondants retirés (jour de semaine, double-comptage du
  trimestre) — le résidu vaut 6 bps/an au coût central. **Toute idée de flux forcé calendaire
  générique (rebalancement pension, fin de trimestre, etc.) est donc déjà tuée** dans ce dépôt,
  pas seulement pour les futures propres à ce test : j'écarte en conséquence les pistes Drobny
  fondées sur ce mécanisme (§Écartées rapidement).
- `Multi_Asset/research/active/macro_round3_2026-09/I_correlation/RAPPORT.md` — le régime de
  corrélation actions-obligations est déjà cadré (littérature + protocole), classé « déjà couvert »
  par le brief — je ne le reprends pas.
- `01_academique/RAPPORT.md` couvre déjà, en détail et avec critique hors-échantillon : macro
  momentum (Brooks/AQR), carry cross-asset (KMPV), régimes croissance/inflation (Ang-Timmermann),
  primes obligataires (Cochrane-Piazzesi, Ludvigson-Ng, Cieslak-Povala, + la réfutation Bauer-
  Hamilton 2018), surprises d'annonces (ABDV, **Savor-Wilson** — c'est la base du flag calendaire
  FOMC déjà construit et validé cette semaine), FX-fondamentaux (Meese-Rogoff, Engel-West,
  Fratzscher-Rime-Sarno-Zinna), nowcasting (Giannone-Reichlin-Small). Le rapport note lui-même,
  explicitement, ne PAS avoir traité les autres contributions FX notables de **Della Corte**
  (carry trade, dollar risk factor) — c'est le point d'entrée de l'idée 3 ci-dessous.

**Ce que ce round ajoute donc, qui n'est nulle part ailleurs dans le dépôt** : les ouvrages
professionnels au sens strict (Grinold-Kahn, López de Prado, Carver) traités comme **méthode
d'implémentation**, pas comme source de signal — exactement l'angle que le brief demande et qui a
été identifié dans `REVUE_INDEPENDANTE.md` comme la question la plus défendable à ce stade
(« couche de risque bon marché » et éviter la famille régime-overlay tuée 4×) — et une contribution
académique peer-reviewed sur la prime de variance FX, non couverte par le round 1.

---

## Classement

| # | Idée | Nature | Probabilité de survie honnête |
|---|---|---|---|
| 1 | **Meta-labeling (López de Prado) en sur-couche des axes événementiels déjà validés/en attente** | implémentation — sizing, pas signal neuf | ~15-20 %, séquencé pour limiter le risque de sur-ajustement petit-N |
| 2 | **Coefficient de transfert (Clarke-de Silva-Thorley / Grinold-Kahn) appliqué à la granularité IBKR** | implémentation — récupère de l'IR perdu, ne prédit rien de neuf | ~15-25 %, coût de test quasi nul |
| 3 | **Prime de variance FX (Della Corte-Ramadorai-Sarno, JFE 2016)** | signal — nouvelle classe d'actif, nouveau mécanisme | ~10-15 %, porte de données à vérifier avant tout code |
| — | Écartées rapidement (Ilmanen illiquidité, Drobny flux institutionnels, Burstein courbe/Fed-cycle, VRP obligataire) | — | voir §4, ~0-5 % chacune |

---

## 1. Meta-labeling comme sur-couche de dimensionnement, pas comme nouveau signal

**Référence.** López de Prado, Marcos, *Advances in Financial Machine Learning*, Wiley, 2018 —
chapitre 3 « Labeling », section sur le **meta-labeling** (numéro de section non vérifié au
chiffre près dans cette session, contenu bien identifié : entraîner un second modèle qui prédit
**si un pari primaire déjà pris gagnera**, pas la direction du pari — ce qui transforme le problème
en classification binaire bien posée et permet de moduler la TAILLE du pari sans toucher au signal
directeur). Complété par le chapitre sur l'échantillonnage (unicité des échantillons, bootstrap
séquentiel) et par l'avertissement transversal du livre : en finance, le nombre d'observations
réellement indépendantes est presque toujours trop petit pour un modèle complexe — préférer un
classifieur simple, régularisé, à un modèle riche.

**Mécanisme économique.** Ce n'est pas une prime de risque — c'est un gain d'**implémentation**
(même famille que l'idée 2) : un signal directionnel déjà validé (le flag calendaire de l'axe A,
« construit et validé cette semaine » par le round 2, ou le drift post-annonce de l'axe B3 une fois
construit) prend systématiquement le même pari de même taille à chaque occurrence. Le meta-label
apprend, sur les occurrences passées, quelles conditions contextuelles (déjà mesurées, jamais
nouvelles : régime de vol réalisée, distance à l'ATH — **en diagnostic, jamais en conditionneur
direct**, cf. `ath_regime_review_2026-08` et L54 — largeur du choc, jour de la semaine) sont
associées à un pari gagnant plutôt que perdant, et **réduit ou coupe la taille** des occurrences
les moins prometteuses. Le gain espéré n'est PAS un nouveau flux de rendement : c'est un TC
(coefficient de transfert, cf. idée 2) meilleur sur un pari qui existe déjà.

**Pourquoi ce n'est pas la famille « score d'état » tuée 4× (L54, `regime_markov_sleeves`,
`ath_regime_review`, `fx_macro_score`).** La revue indépendante (`REVUE_INDEPENDANTE.md` §1.1)
tranche : tout objet qui informe une décision doit être gaté comme un signal. Le meta-label EST
gaté comme un signal ici, explicitement : (a) walk-forward ≥5 folds sur les occurrences passées de
l'axe primaire, (b) DSR obligatoire dès qu'on compte le meta-modèle comme une deuxième
modification (L20), (c) **test L54 appliqué au sous-ensemble filtré** : le sous-groupe que le
meta-label retient à pleine taille doit avoir une moyenne PLUS HAUTE que le groupe qu'il réduit,
pas seulement une variance plus basse — sinon c'est exactement l'erreur que L54 corrige. La
différence avec un score d'état classique : le meta-label ne prédit JAMAIS un sens de marché à
partir de rien, il ne fait que trier des paris DONT LE SENS est déjà fixé par un signal
pré-enregistré et déjà validé séparément — c'est un problème strictement plus étroit et mieux posé.

**Acteur contraint.** Aucun — hérité de l'axe primaire choisi.

**Breadth annuelle.** Héritée de l'axe primaire, non additive : le meta-label ne crée AUCUN pari
supplémentaire, il ne fait que retenir/couper une partie des paris existants. **Point de
séquencement, dicté par l'avertissement anti-sur-ajustement de López de Prado lui-même** : ne pas
commencer par un axe à trop peu d'occurrences. L'axe B3 (drift post-annonce, prioritaire au round
2, gross documenté 14 bps/50j) est le meilleur candidat de départ une fois construit — s'il couvre
l'ensemble des annonces macro programmées (FOMC+NFP+CPI+PIB), il tourne autour de **20-40
occurrences/an** (cf. §5.1 de `01_academique/RAPPORT.md`), ordre de grandeur où un classifieur à
2-3 features peut encore être walk-forwardé sans être un pur artefact. L'axe A (flag calendaire de
saut, déjà construit) est un candidat de test PLUS PETIT — utile pour roder le code, pas pour
conclure sur la valeur réelle du meta-label avec un N aussi faible.

**Véhicule.** Celui de l'axe primaire — ZN (IBKR, ~$1 800 marge, ~0,4 bps RT) pour B3.

**Données.** Aucune nouvelle — uniquement les features déjà mesurées par le desk (vol réalisée,
ATH distance en diagnostic, calendrier). C'est la force de cette idée : coût marginal ≈ zéro.

**Ce qui la falsifierait.** (1) AUC du meta-modèle ≈ 0.5 hors échantillon (walk-forward) → le
contexte ne contient aucune information sur l'issue du pari, kill immédiat, coût = une session.
(2) Le sous-groupe retenu à pleine taille n'a pas une moyenne strictement supérieure au sous-groupe
coupé (test L54 sur le split) → c'est un filtre de variance déguisé, kill. (3) Le Δp(pass)/Δdurée
du book (pas le ΔSharpe, cf. `Portfolio/admission/`) ne s'améliore pas à duty cycle apparié contre
un dé-levier uniforme de même ampleur → l'overlay ne fait que réduire l'exposition sans discriminer,
équivalent à un simple sizing plus petit, aucune valeur ajoutée du meta-label lui-même.

**Probabilité de survie honnête : ~15-20 %.** Le risque dominant est exactement celui que López de
Prado nomme lui-même : un N annuel de 20-40 événements donne, sur un historique de 10-15 ans,
200-600 occurrences au mieux — praticable pour un classifieur à 2-3 features avec bootstrap
séquentiel, mais à la limite basse de ce qui évite l'overfitting. Séquencer (commencer petit, sur
l'axe déjà construit, avant de le porter sur B3) réduit le coût d'un échec sans réduire la valeur
d'un succès.

---

## 2. Coefficient de transfert (Grinold-Kahn / Clarke-de Silva-Thorley) appliqué à la granularité IBKR

**Référence.** Grinold, Richard C. & Kahn, Ronald N., *Active Portfolio Management*, 2ᵉ éd.,
McGraw-Hill, 2000 — traite des contraintes et de leur coût en information ratio dans le cadre de la
« loi fondamentale » (`IR = TC × IC × √BR`), déjà au cœur de la méthodologie du dépôt via L67.
Le **coefficient de transfert (TC)** au sens strict — corrélation entre le vecteur de poids
RÉELLEMENT détenu et le vecteur de poids qu'un optimiseur non contraint aurait choisi à partir des
mêmes alphas — est formalisé par **Clarke, Roger G., de Silva, Harindra & Thorley, Steven,
« Portfolio Constraints and the Fundamental Law of Active Management », *Financial Analysts
Journal*, vol. 58, no. 5, 2002, pp. 48-66 (PEER-REVIEWED, FAJ)** ; numéro de chapitre exact où
Grinold-Kahn l'intègre non vérifié dans cette session (le livre discute les contraintes dans sa
partie sur l'implémentation, sans que j'aie le texte sous la main pour citer une page précise).
Complété par **Carver, Rob, *Systematic Trading*, Harriman House, 2015 et *Advanced Futures
Trading Strategies*, Harriman House, 2023** — chapitres sur la sélection d'instruments et le
dimensionnement à petit capital (déjà partiellement gravé ici sous **L57** : le coût fixe domine en
bps sur petit notionnel, et 1 lot ou rien coûte 0,35 de Sharpe et retourne le skew).

**Ce que cette idée ajoute par rapport à L57 (déjà engravée)** : L57 est un CONSTAT qualitatif
(le lot entier dégrade le Sharpe et le skew). Le TC de Clarke-de Silva-Thorley donne un OUTIL DE
MESURE et un critère de décision explicite pour un choix concret et imminent : **le compte IBKR
ouvre cette semaine** — quel micro-contrat/quelle granularité choisir pour le book perso
(trend + bond month-end) afin de MAXIMISER le TC réellement atteint, plutôt que de re-découvrir
qualitativement, après coup, que le lot était trop gros ?

**Mécanisme.** Ce n'est PAS une prime de risque — c'est un audit d'implémentation. Calcul : à
partir de l'historique déjà backtesté du book perso (poids cibles continus, non contraints, déjà
produits par le moteur de sizing), comparer au vecteur de poids RÉELLEMENT atteignable une fois
discrétisé en lots entiers sur chaque instrument candidat (ZN plein contrat vs micro-Treasury si
disponible ; ES vs MES ; etc.), et calculer TC = corrélation(poids réel discrétisé, poids cible
continu) sur la période. **La perte d'IR attendue est `IR_réel ≈ TC × IR_idéal`** — un chiffre,
pas une intuition, permettant de trancher objectivement entre deux instruments candidats pour le
MÊME risque économique (ex. ZN plein contrat, marge ~$1 800, granularité grossière sur un compte
de 13k€, vs. un micro-Treasury si le contrat existe et est liquide).

**Acteur contraint.** Aucun — c'est un audit interne, pas un pari sur un acteur de marché.

**Breadth annuelle.** Sans objet — pas un générateur de pari, un multiplicateur d'IR sur les paris
déjà pris par les sleeves existantes du book perso (trend + bond month-end).

**Véhicule.** Choix D'INSTRUMENT au sein d'IBKR (ZN vs micro-Treasury, ES vs MES, etc.) — c'est
littéralement l'objet de la décision.

**Données.** Aucune nouvelle donnée de marché — uniquement l'historique de sizing déjà produit par
les sleeves existantes (poids cibles continus) et les spécifications de contrat IBKR (taille de
tick, marge, disponibilité micro) déjà publiques.

**Ce qui la falsifierait.** (1) TC déjà proche de 1 sur l'historique existant (le capital est
suffisant pour que la discrétisation ne coûte quasiment rien) → rien à gagner, ne pas construire
d'infrastructure supplémentaire, coût du test = une après-midi de calcul sur des données déjà en
cache. (2) Le meilleur micro-contrat candidat a un spread/commission relatif tel que le gain de TC
est annulé par le coût fixe relatif plus élevé (retour à L57 dans l'autre sens — un contrat plus
petit peut avoir un coût EN BPS plus élevé, cf. L57 « MGC vs 1 lot »). Les deux issues sont
informatives à coût quasi nul.

**Probabilité de survie honnête : ~15-25 %** de révéler un gain matériel et actionnable (le book
perso est peut-être déjà assez peu contraint pour que le TC soit proche de 1) — mais le test lui-
même coûte presque rien (pas de téléchargement, calcul sur historique déjà produit), donc le
rapport coût/information est favorable même si la probabilité de « découverte » est modeste.

---

## 3. Prime de variance FX comme prédicteur de rendement (Della Corte, Ramadorai, Sarno)

**Référence.** Della Corte, Pasquale, Ramadorai, Tarun & Sarno, Lucio, « Volatility Risk Premia and
Exchange Rate Predictability », *Journal of Financial Economics*, vol. 120, no. 1, 2016, pp. 21-40
(**PEER-REVIEWED, JFE** — même revue de premier rang que Koijen-Moskowitz-Pedersen-Vrugt déjà cité
dans ce dépôt pour le carry). Explicitement **non couvert** par `01_academique/RAPPORT.md` du round
1, qui note lui-même n'avoir pas traité « les autres contributions FX notables de Della Corte
(carry trade, dollar risk factor) » faute de correspondance avec le brief d'origine — c'est le trou
exact que cette idée comble. Cadre théorique complémentaire, contexte plus large des primes de
volatilité par classe d'actif : Ilmanen, Antti, *Expected Returns*, Wiley, 2011, et *Investing Amid
Low Expected Returns*, Wiley, 2022 — chapitres sur la vente de volatilité comme flux de rendement
distinct du carry et du trend (numéro de chapitre non vérifié, contenu narratif bien identifié :
Ilmanen classe la prime de volatilité comme une prime « assurantielle » structurellement proche du
carry mais distincte par sa source de risque).

**Mécanisme économique.** La prime de variance FX (implicite moins réalisée, extraite d'options sur
devises) **prédit** — pas seulement « rémunère en moyenne » — les rendements excès futurs des
devises, en coupe ET en série temporelle : une prime de variance élevée sur une devise précède un
rendement excès plus faible. C'est distinct du carry (spread de taux, déjà couvert par G2D) : le
mécanisme proposé par les auteurs est une compensation pour le risque de désincertaine
(**incertitude sur l'incertitude**), pas un différentiel de taux directeur. Deux jambes testables
en théorie (contrairement au drift pré-FOMC, structurellement à jambe unique) : prime haute →
rendement futur bas, prime basse → rendement futur haut.

**Acteur contraint.** Aucun acteur unique forcé — c'est une prime de risque, pas un flux
mécanique. C'est la même réserve structurelle que pour le carry cross-asset (G2D) ou le carry
conditionné (axe D) : pas de contrepartie obligée, donc le signal est plus fragile face à
l'arbitrage institutionnel que les mécanismes à acteur forcé (B3, month-end ZN).

**Breadth annuelle.** Signal mensuel (fréquence typique de reconstruction dans la littérature),
cross-sectionnel sur les devises à options CME liquides (EUR, GBP, JPY, AUD, CAD ≈ 5-8 paires) —
nominal ~60-96/an (5-8 × 12), mais la prime de variance est probablement autocorrélée (elle
partage une composante de vol globale, cf. le même calcul de noyau de décroissance que le round 1)
→ **ordre de grandeur plausible 15-30 paris indépendants/an**, à mesurer avant toute conclusion, pas
à supposer — même discipline que L67.

**Véhicule.** Options sur futures FX CME (6E, 6B, 6J, 6A, 6C — EUR, GBP, JPY, AUD, CAD) via IBKR,
coté sur échange, coût nettement inférieur à un OTC retail — mais **non mesuré ici** : à vérifier
en premier (spread bid-ask réel sur options ATM 1 mois, profondeur) avant tout calcul d'IC, exactement
le réflexe L23b (tier institutionnel vs retail) qui a déjà tué le flow-anchored FX (L34) et pourrait
tuer celui-ci de la même manière si le spread d'options FX retail-accessible est trop large.

**Données.** **Porte gratuite à trancher avant tout code, comme pour l'axe H du round 3 et la
piste 2 du round 4** : existe-t-il une série d'implied volatility FX (ou un proxy exploitable
— ex. écart entre un indice de vol FX type historique CVIX/JPMVXYG et la vol réalisée correspondante)
suffisamment longue et gratuite ? Si non, l'axe s'arrête sans qu'aucune donnée de prix n'ait été
touchée. Vol réalisée = gratuite (deep_history_utc). Vol implicite = **goulot probable**, à vérifier
en premier.

**Ce qui la falsifierait.** (1) Porte de données ci-dessus : pas de série d'IV FX gratuite et
suffisamment longue → arrêt immédiat, coût nul. (2) Si la donnée existe : IC HAC lag-6 sur
rendement excès FX à 1 mois, walk-forward ≥5 folds avec diagnostic fold-par-fold OBLIGATOIRE (le
piège qui a fait s'effondrer `fx_macro_score` était invisible à un simple bootstrap — cf.
`REVUE_INDEPENDANTE.md` §1.4) : si l'effet est porté à plus de 60 % par un seul fold ou un seul
régime (ex. GFC/COVID), même un t-stat significatif poolé est disqualifié. (3) Coût de spread
d'options mesuré au tier retail IBKR > le gross documenté par les auteurs (2016, échantillon
institutionnel) → tier check L23b, kill si échec.

**Probabilité de survie honnête : ~10-15 %.** Le point fort réel : c'est un vrai résultat
peer-reviewed JFE, distinct du carry (déjà pris) et de la VRP actions (déjà morte au coût, cf.
`vrp_options_real_data_2026-07`), sur une classe d'actif où le véhicule (options FX listées CME via
IBKR) vient tout juste de s'ouvrir. Le point faible : deux portes non résolues avant même un
premier chiffre (disponibilité de la donnée d'IV, tier de coût réel des options FX retail) — c'est
structurellement la même position que la piste 2 du round 4 (surprise EIA) ou l'axe H du round 3
(offre de titres) : mécanisme réel, documenté, mais bloqué en amont par une porte de données à
trancher avant tout investissement de temps.

---

## 4. Écartées rapidement

**Ilmanen — prime d'illiquidité** (*Expected Returns*, chapitre sur l'illiquidité comme style
d'investissement, numéro non vérifié). Mécanisme réel et bien documenté (private equity, closed-end
funds, small/illiquid credit) mais **incompatible avec le profil de véhicule** de ce chercheur (CFD
FTMO, futures IBKR à lot entier, crypto) — aucun des trois ne donne accès à une prime d'illiquidité
au sens propre. Écartée sur le véhicule, pas sur le mécanisme (rouvrable si l'infrastructure
change radicalement, ex. accès à des fonds fermés cotés).

**Drobny — flux institutionnels forcés (recyclage pétrodollar, rebalancement de pension, flux
d'assureurs-vie japonais).** Mécanismes réels, discutés dans les entretiens de praticiens, mais
**déjà tués par construction** dans ce dépôt : `forced_flow_cooccurrence_2026-08` a testé
exactement la classe « flux forcé calendaire daté à l'avance » (dont le rebalancement de fin de
trimestre) sur 19 instruments et 59 687 jours-instrument, courbe de dose plate une fois les
confondants retirés. Le recyclage pétrodollar et les flux d'assureurs japonais ont en outre le même
problème de comptage que le plafond de dette (round 4, piste 3) : événements trop rares pour un
test défendable avec les données publiques accessibles à ce chercheur.

**Burstein — trades de courbe conditionnés au cycle Fed (steepener/flattener via Fed funds
futures-implied).** Mécanisme réel et documenté dans la littérature practitioner, mais recoupe deux
terrains déjà fermés : l'axe G (propagation cross-asset, round 3, dead) et le macro momentum AQR
déjà couvert par le round 1 (le thème « politique monétaire », Sharpe 0.9 par thème, décroissance
2010-2016). Pas d'angle mécaniquement nouveau au sens de la politique de ré-ouverture.

**Prime de variance obligataire (Mueller-Vedolin-Yen et littérature adjacente sur les options ZN/
ZB).** Même famille que l'idée 3 mais sur les taux plutôt que le FX — écartée en second rang
uniquement par choix de priorité (une seule classe d'actif VRP à la fois pour ne pas diluer le
budget de test), pas par un défaut du mécanisme. Candidate de repli si l'idée 3 échoue sur sa porte
de données FX mais que la donnée d'IV obligataire (options CME sur ZN/ZB, généralement mieux
documentées et plus liquides que les options FX) s'avère plus accessible.

---

## Résumé (20 lignes max)

**Balayage** : le carry cross-asset (KMPV) est déjà pris (`g2d_carry_cross_asset`, vivant) ; tout
flux forcé calendaire générique (Drobny-style) est déjà mort (`forced_flow_cooccurrence`,
REJECTED, courbe plate) ; la corrélation actions-obligations est déjà couverte. Le rapport
académique du round 1 couvre déjà macro momentum, régimes, primes obligataires, surprises
d'annonces, FX-fondamentaux, nowcasting — et note lui-même n'avoir pas traité Della Corte, d'où
l'idée 3.

**Classement.** (1) **Meta-labeling (López de Prado)** en sur-couche de sizing sur un axe
événementiel déjà validé ou en construction (A puis B3) — implémentation, pas signal neuf, coût
marginal quasi nul, risque principal = petit N pour un modèle même simple ; séquencer du plus
petit N vers le plus grand. (2) **Coefficient de transfert (Clarke-de Silva-Thorley/Grinold-Kahn)**
appliqué au choix d'instrument IBKR (ZN vs micro, ES vs MES) au moment précis où le compte ouvre —
raffine L57 avec un chiffre au lieu d'une intuition, testable sur des données déjà en cache. (3)
**Prime de variance FX (Della Corte-Ramadorai-Sarno, JFE 2016)** — vraie contribution peer-reviewed
non couverte, nouvelle classe d'actif, mais deux portes de données/coût à trancher avant tout code
(disponibilité IV FX gratuite, tier de spread options retail).

**Point commun des trois** : aucune ne redemande un score d'état bullish/bearish (famille tuée 4×
selon `REVUE_INDEPENDANTE.md`) — les deux premières sont de l'implémentation pure sur des paris déjà
pris, la troisième est un signal correctement bilatéral sur un mécanisme jamais testé ici. **Rien
d'écarté n'est ré-ouvert sans angle mécaniquement neuf** (illiquidité = véhicule incompatible ;
flux Drobny = mort mécaniquement ; courbe Fed-cycle = doublon de terrain déjà fermé).
