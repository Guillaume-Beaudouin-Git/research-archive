# Macro — round 2 : cinq axes indépendants

**2026-09-06.** Le round 1 a testé UNE formulation (score cross-sectionnel tenu, N≥30, mensuel,
capital €13k) et l'a tuée. Correctif de cadrage : c'était une configuration, pas l'espace macro. Le
round 2 attaque cinq axes qui **échouent pour des raisons différentes s'ils échouent**, ce qui est
la condition pour apprendre quelque chose.

## Ce que le round 1 a réellement établi (à ne pas re-démontrer)

1. **La breadth est la contrainte liante.** 2-15 paris indépendants/an pour un score continu
   multi-pays. Tout axe du round 2 doit dire, en une phrase, **comment il obtient sa breadth**.
2. **Un score tenu mensuellement meurt au portage sur CFD** (~6,75 %/an) et à la granularité 1-lot
   sur futures à €13k. Tout axe tenu doit nommer son véhicule d'emblée.
3. **Le régime prédit souvent la variance sans prédire la moyenne** (Ang-Timmermann 2012, théorème,
   pas accident). Tout axe directionnel doit passer ce test.

Ces trois points sont des **contraintes de conception**, pas des verdicts. Un axe qui les affronte
explicitement est recevable.

---

## Les cinq axes

### A — Le macro prédit le RISQUE, pas le rendement

**L'idée.** Toute la littérature macro→rendement est faible (IC 0,02-0,08). La littérature
macro→**volatilité** est nettement plus solide. Or notre problème vivant n'est pas de prédire un
rendement : c'est un **compte funded avec un plancher**, où la probabilité de survie dépend de la
forme de la distribution quotidienne face à une barrière.

**Pourquoi ça échappe à la contrainte de breadth.** Le gate n'est plus `IC × √BR`. Prédire la
variance ne demande pas d'IC directionnel : ça demande d'améliorer un modèle de risque, ce qui se
mesure en vraisemblance et en calibration, pas en Sharpe.

**Pourquoi ça échappe aussi à L54.** L54 dit qu'un overlay de régime n'aide pas l'espérance si le
régime ne prédit pas la moyenne. Vrai pour le Sharpe. **Faux pour une barrière** : p(ruine) est
convexe en volatilité, donc réduire la vol quand elle est prévisible a une valeur positive *même à
espérance inchangée*. C'est un argument que L54 ne couvre pas et qu'il faut trancher.

**Ce qui le falsifie.** Si le gain de p(pass) d'un dé-levier piloté par le macro ne bat pas celui
d'un dé-levier piloté par la vol réalisée seule (contrôle à duty cycle identique), le macro
n'apporte rien — c'est le contrôle qui a tué l'overlay de régime en juillet.

### B — Le repricing des ANTICIPATIONS, pas la macro réalisée

**L'idée.** Ce qui bouge les prix n'est pas la croissance, c'est la révision du chemin de taux
anticipé. Trader la courbe OIS / les futures Fed funds contre le chemin réalisé, et les
communications de banques centrales (le ton, les diffs de communiqué — littérature
Hansen-McMahon).

**Breadth.** Le nombre de réunions de banques centrales et de publications qui déplacent la courbe :
~8 FOMC + 8 BCE + les publications majeures ⇒ **30-60 événements/an, datés, non chevauchants**. C'est
une breadth honnête d'un ordre de grandeur au-dessus du score continu.

**Véhicule.** Futures de taux (ZN, ZF, ZT) chez IBKR ou indices en fenêtre courte — pas de portage
si la tenue est brève.

**Ce qui le falsifie.** Si le repricing est déjà intégré à la publication (efficience), le gross
mesuré sur fenêtre courte sera sub-bps ⇒ mort au coût, comme le FX intraday.

### C — Dispersion et macro RELATIVE + flux contraints

**L'idée.** Le facteur commun est ce qui détruit la breadth transversale. On le différencie : au lieu
de « l'économie américaine va bien », on trade « les États-Unis surprennent **relativement** à la zone
euro ». Le résidu est structurellement plus indépendant que le niveau. Complété par les données de
positionnement (COT hebdomadaire, flux TIC) qui portent une histoire d'**acteur contraint** — la
frontière que le dépôt a lui-même identifiée comme la seule échappatoire crédible.

**Breadth.** C'est l'attaque directe : différencier tue le facteur commun, donc augmente
mécaniquement le nombre de paris indépendants. À quantifier, pas à supposer.

**Ce qui le falsifie.** Si la corrélation résiduelle entre paires différenciées reste élevée, le
gain de breadth est illusoire. Se mesure directement, avant tout backtest.

### D — Le carry CONDITIONNÉ par le macro, proprement

**L'idée.** Le carry est le seul résultat académique qui a survécu au round 1. Et la piste « Dédale »
est déjà ouverte dans ta mémoire projet : entrer seulement sur la jambe qui encaisse le portage.
Notre reproduction non biaisée donnait +16 à 21 % sur 6,5 ans — faible, mais non nul, et jamais
testée proprement.

**Les quatre correctifs à appliquer**, déjà écrits : swaps **historiques** réels et non le swap du
jour ; filtre de carry recalculé trade par trade ; **bilatéral réellement autorisé** (le veto
direction-aveugle rejetait toutes les ventes) ; et sous les différentiels de 2026, pas de 2022.

**Ce qui le falsifie.** Si l'edge disparaît une fois le biais d'anticipation retiré et le portage
comprimé de 2026 appliqué, la famille se ferme proprement — et on saura enfin pourquoi.

### E — L'écart NOWCAST − CONSENSUS

**L'idée.** Ne pas prédire la macro : prédire **la surprise**. Construire un nowcast à partir de ce
qui est déjà publié, le comparer au consensus, et trader l'écart. Le signal n'est pas « la croissance
est bonne » mais « l'anticipation du marché est périmée par rapport à ce qui est déjà connaissable ».
C'est en substance ce que fait Fulcrum, et c'est le seul usage du nowcasting qui produit un pari.

**Breadth.** Une décision par publication couverte : ~12 CPI + 12 emplois + 12 PMI + 4 PIB par zone,
et l'écart se **résout** à chaque publication ⇒ pas de noyau lent, pas d'autocorrélation qui écrase
le compte.

**Ce qui le falsifie.** Si le nowcast ne bat pas le consensus en erreur quadratique moyenne
out-of-sample, il n'y a pas d'écart à trader — c'est un test préalable, gratuit, à faire **avant**
tout backtest de rendement.

---

## Règles communes aux cinq agents

- Le livrable n'est **pas** un verdict de faisabilité. C'est **la version la plus forte de l'axe** et
  la spécification de ce qui la falsifierait.
- Les trois contraintes du round 1 sont des cibles de conception : chaque axe doit dire comment il
  obtient sa breadth, quel véhicule il vise, et comment il évite le piège variance/moyenne.
- Un axe qu'on ne peut pas falsifier n'est pas retenu.
- Sources primaires, chiffres ou « non trouvé ». Aucune invention.

Δn_tests = 0 sur ce round : conception uniquement.
