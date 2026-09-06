# Macro round 2 — synthèse des cinq axes et ordre de marche

**2026-09-06.** Cinq axes indépendants, briefés pour produire *la version la plus forte* de leur
idée et non un verdict. Δn_tests = 0. Résultat : **quatre axes survivent sous une forme précisée,
un est reclassé en outil transverse, et deux hypothèses que j'avais avancées sont réfutées.**

---

## 1. Classement, avec le motif

| | Axe | Statut | Ce qui décide |
|---|---|---|---|
| **1** | **B3 — drift post-annonce sur les taux** | **prioritaire** | gross documenté **14 bps / 50 j** pour un choc de 10 bps, très au-dessus du coût futures ; bilatéral **natif** au signe du choc ; données gratuites ; véhicule ZN à ~$1 800 de marge |
| **2** | **D — carry conditionné** | vivant, à spécifier | carry G10 **pas mort** mais régime-dépendant ; un seul conditionneur répliqué (régime de vol globale, +30-50 % de Sharpe sur 3 études) |
| **3** | **A — flag calendaire de saut** | vivant, étroit | la version « régime de vol » est réfutée ; seule survit la coupe **événementielle bornée**. Bon marché à tester, protège le book live |
| **4** | **E — nowcast − consensus** | conditionnel | prémisse **en échec sur GDPNow** ; test préalable gratuit et définitif à faire avant tout code |
| **—** | **C — dispersion** | **reclassé : outil, pas candidat** | ce n'est pas une stratégie, c'est un correctif de construction qui s'applique à tous les autres axes |

---

## 2. Le résultat le plus utile du round : la construction plafonne la breadth

L'agent C a dérivé algébriquement, et la vérification est bonne.

Avec un facteur commun $F$ et des idiosyncrasies $e_i$ de variance égale, construire l'univers **en
étoile** (tout contre un pivot — la construction FX standard) donne $Y_i = e_i - e_0$, donc

$$\rho(Y_i, Y_j) = \tfrac{1}{2} \quad\Longrightarrow\quad BR_{\text{eff}} \to \tfrac{1}{\rho} = 2$$

**quel que soit N.** Trente paires ou trois, c'est identique. Ce n'est pas une propriété du macro :
c'est la construction qui pose le plafond, avant tout signal. C'est l'explication mécanique du
« facteur dollar omniprésent » qu'on observait sans savoir d'où il venait.

Le correctif est gratuit : **démoyenner en coupe** (soustraire la moyenne de l'univers au lieu de
diviser par un pivot) donne $\rho = -1/(N-1)$ et une breadth théorique de $N-1$.

⚠ **Le gain est mécanique, pas économique.** Il ne dit rien sur la présence d'un signal dans le
résidu — c'est le falsificateur central de l'agent. Mais il retire un plafond qu'on se posait
soi-même.

**Conséquence opérationnelle : toute construction transversale future démoyenne, ne pivote pas.**
S'applique à D et à tout ce qui viendra.

---

## 3. Deux hypothèses réfutées — dont deux des miennes

### 3.1 « La barrière change l'arbitrage de L54 » — FAUX

J'avais avancé que p(ruine) étant convexe en volatilité, réduire l'exposition quand la vol est
prévisible aurait une valeur positive même à espérance inchangée — donc que L54, établie sur le
Sharpe, ne s'appliquerait pas sous barrière.

L'agent A a dérivé la loi de premier passage. La convexité exige $z = B/(\sigma\sqrt{T}) > \sqrt 2$
(vérifié : $\partial^2 p/\partial\sigma^2 \propto -(2 - z^2)$). Condition satisfaite pour un compte
FTMO, où $z \approx 4\text{-}6$. **Mais à cette distance $\varphi(z)$ s'effondre**
($\varphi(5)\approx 1.5\times10^{-6}$) : la probabilité de ruine ne réagit quasiment plus à la vol.
Le gain de convexité est négligeable, quand le manque à gagner mesuré par L54 est gros
(**+218 bps contre +21 bps** sur les jours coupés).

**L54 tient aussi sous barrière.** Mon erreur : j'ai vérifié le signe de la convexité, pas son
amplitude au point où l'on se trouve.

### 3.2 « Le pré-FOMC est rouvrable sur la puissance » — MAL CLASSÉ

J'avais proposé de rouvrir le drift pré-FOMC en doublant l'échantillon (49 → 102 événements) et en
construisant un vrai test bilatéral.

L'agent B montre que le **drift pré-annonce** (Lucca-Moench) est une prime de résolution
d'incertitude, donc **structurellement non directionnelle : il n'a pas de jambe symétrique testable
en théorie.** Nos colonnes miroir n'étaient pas une erreur réparable — il n'y avait rien à tester.
Et l'effet est **mort depuis 2015-2016** (Kurov-Wolfe-Gilbert), pour un motif structurel.

⇒ **Reclassement : kill « puissance / rouvrable » → kill MÉCANIQUE, reste fermé.** À corriger dans
la politique de ré-ouverture.

---

## 4. Les quatre axes retenus, avec leur point de rupture

### B3 — drift post-annonce sur les taux *(prioritaire)*

Après un choc de politique monétaire, le prix continue de dériver dans le sens du choc. Mécanisme de
flux identifié (fonds mutuels → arbitragistes), ce qui donne un **test bilatéral natif** : la jambe
inverse est le choc de signe opposé, pas un miroir artificiel.

- **Gross** : 14 bps sur 50 jours pour un choc de 10 bps (Brooks-Katz-Lustig, NBER 2018 ;
  Neuhierl-Weber pour la version bilatérale propre).
- **Prérequis non négociable** : décomposition **Jarociński-Karadi** séparant choc de politique et
  choc d'information — sans elle on mélange deux effets aux dynamiques opposées.
- **Données gratuites vérifiées** : USMPD (SF Fed, à jour 2026), séries JK (Fed juil. 2025, BCE
  avr. 2025, CC-BY-4.0), EA-MPD (BCE), calendriers officiels.
- **Breadth** : 8 réunions/an/banque, 32 sur 4 banques — mais fenêtres de drift **chevauchantes**
  (HAC et bootstrap obligatoires) et **chaque banque centrale compte comme un test AMTP séparé**.
- **Véhicule** : ZN chez IBKR, ~$1 800 de marge, tient dans €13k.
- **Point de rupture** : le mécanisme repose sur des flux retail. Rien dans la littérature trouvée
  ne dit s'il survit au régime post-2020 (QT, hausses rapides). **Premier test, isolé sur 2020-2026.**

### D — carry conditionné

- Le carry G10 **n'est pas mort** : ressuscité par le cycle Fed/BoJ 2022-2023, puis frappé par un
  dénouement de manuel (yen +14 % en un mois, juillet-août 2024) — concordant avec la compression
  des différentiels JPY qu'on avait mesurée.
- **Seul conditionneur répliqué** : le régime de **volatilité FX globale** (+30-50 % de Sharpe,
  3 études indépendantes). Momentum et valeur sont des stabilisateurs de queue, pas des
  amplificateurs de Sharpe.
- ⚠ **Le filtre « sens du portage » de Dédale n'appartient à aucune famille académique testée.**
  C'est une hypothèse maison. Statut : hypothèse originale à valider, pas application d'un résultat
  connu.
- **Breadth mesurée** : PC1+PC2 expliquent **82-88 %** de la variance G10 ⇒ 12 paires chargées en
  yen valent **2 à 4 paris**, pas 12.
- **Le portage EST le signal**, pas un coût annexe : toute comparaison de véhicule sans portage net
  par sens ne mesure rien.
- **Dépendance externe** : les swaps historiques par paire ET par sens. Sources à obtenir avant tout
  code (démo Eightcap pour la table, ou fallback différentiel de taux **marqué comme proxy**).

### A — flag calendaire de saut *(étroit, bon marché)*

Seule formulation survivante : couper l'exposition sur **fenêtre étroite autour d'un événement daté**
(CPI, FOMC, emploi), en visant le risque de **saut**, pas la diffusion sur la journée.

Converge avec une observation de juillet : la géométrie du book **rate** FOMC et les événements
européens — cette protection est gratuite.

⚠ **Piège d'implémentation documenté** : à $z\approx5$, un Monte Carlo gaussien ne produira
quasiment aucune ruine ⇒ zéro événement et faux négatif. Il faut du **rééchantillonnage historique
des queues** ou de la simulation d'événement rare.

**Falsification** : Δp(pass) contre un dé-levier piloté par la **vol réalisée seule**, à duty cycle
apparié. Jamais un ΔSharpe.

### E — nowcast − consensus *(conditionnel, test gratuit d'abord)*

- **La prémisse est en échec là où on peut la vérifier** : GDPNow **ne bat pas** Blue Chip en moyenne
  sur 2011-2025 (RMSE 1,17 pt). Le nowcast public de référence ne bat pas le consensus.
- La sous-réaction des prévisionnistes est réelle (Coibion-Gorodnichenko, coefficient ~1,0-1,3) mais
  **pas une constante** — rupture structurelle documentée récemment.
- **Kroner (Fed, 2025)** : la réaction du prix à une surprise est pilotée par **l'attention** et
  n'est **pas stable dans le temps**. Une fonction de réaction estimée sur un régime ne transfère pas.
- **Fuite pré-annonce** : ~40 % de l'ajustement se produit dans les 30 min **avant** la publication,
  sur 9 des 20 annonces majeures (Kurov et al.).
- **Goulot** : la donnée de consensus. Bloomberg hors de portée ; le survey de Philadelphie est
  gratuit mais **trimestriel**, trop grossier ; aucune source gratuite ne garantit un point-in-time
  mensuel fiable.
- **Test préalable, gratuit et définitif** : Diebold-Mariano (HAC lag-6, ≥5 folds walk-forward,
  p<0,05 sur ≥3/5 folds). Si le nowcast ne bat pas le consensus en erreur quadratique hors
  échantillon, **il n'y a rien à trader** — on s'arrête sans avoir touché un prix.

---

## 5. La composition que personne n'a été briefé pour voir

Le seul conditionneur répliqué du carry (axe D) est une **prévision de volatilité**. C'est le
domaine de l'axe A. Et l'infrastructure d'événements datés + millésimes point-in-time sert
simultanément B3, A et E.

⇒ **Il y a un noyau commun à construire une seule fois**, avant de trancher entre les axes :

1. `event_calendar.py` — événements horodatés à l'heure de publication réelle, horloge de l'échange
   avec DST, jamais UTC calendaire. Sert A, B3, E.
2. `vintage_loader.py` — ALFRED + millésimes FRED-MD/QD. **Contrat : toute requête prend une date
   d'observation et ne peut pas retourner la série révisée par accident.** Sert B3, E.
3. `mp_shocks.py` — chargement des séries de chocs publiées (USMPD, Jarociński-Karadi) + la
   décomposition politique/information. Sert B3.
4. `vol_forecast.py` — prévision de volatilité, avec le contrôle « vol réalisée seule » intégré
   comme baseline obligatoire. Sert A et D.
5. `breadth.py` — calcul de $N_{\text{eff}}$ (ACP transversale + noyau temporel). **Doit refuser de
   rendre un t-stat sans rendre le $N_{\text{eff}}$ correspondant.** Sert tout.

---

## 6. Ordre de marche

**Étape 0 — le noyau commun** (modules 1, 2, 5 ci-dessus). Sert quatre axes, ne présuppose aucun
résultat.

**Étape 1 — B3.** Meilleur rapport gross/coût, données gratuites, véhicule propre, test bilatéral
natif. Premier geste : **isoler 2020-2026** et vérifier que le mécanisme survit. S'il ne survit pas,
l'axe se ferme proprement et on n'a perdu qu'un test.

**Étape 2 — A**, en parallèle : bon marché, et le résultat protège le book actuellement en live.

**Étape 3 — E**, mais **uniquement le test préalable Diebold-Mariano**. Gratuit, définitif, et il
décide s'il y a un projet.

**Étape 4 — D**, une fois la table de swaps historiques obtenue. C'est la dépendance externe la plus
lente, à lancer dès maintenant en tâche de fond humaine.

**Transverse — C** s'applique dès qu'une construction transversale apparaît : démoyenner, jamais
pivoter.

---

## 7. Leçons candidates

Non numérotées, à graver à la réconciliation.

- **Candidate D** : la construction de l'univers plafonne la breadth avant tout signal. Une
  construction en étoile (tout contre un pivot) fixe $\rho=0{,}5$ et $BR\to 2$ quel que soit N ;
  démoyenner en coupe donne $\rho=-1/(N-1)$. **Choisir la construction est une décision de breadth,
  pas de présentation.**
- **Candidate E** : vérifier le SIGNE d'une convexité ne suffit pas, il faut son AMPLITUDE au point
  d'opération. p(ruine) est bien convexe en vol pour $z>\sqrt2$, mais à $z\approx5$ le gain est
  négligeable — la conclusion s'inverse entre « convexe » et « convexe et matériel ».
- **Candidate F** : une prime de résolution d'incertitude n'a pas de jambe symétrique **par
  construction**. Exiger un test bilatéral sur ce type d'effet est une erreur de catégorie, et
  l'absence de bilatéral n'y est pas un défaut réparable — c'est un motif de kill mécanique.
