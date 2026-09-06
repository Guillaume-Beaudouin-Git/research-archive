# Macro round 3 — synthèse

**2026-09-07.** Quatre axes, tous briefés avec **balayage obligatoire du dépôt avant proposition**
(correctif de la faute L48 commise au round 2 sur B3). Δn_tests = 0 : conception seule.

---

## 1. Le résultat qui dépasse le macro

**Trois des quatre axes ont pour maison IBKR, pas FTMO. Le quatrième y est inerte.**

| axe | où il peut vivre |
|---|---|
| **F — variance d'événement** | **FTMO ne propose aucune option** ⇒ structurellement inexécutable sur le compte funded. XSP chez IBKR uniquement |
| **I — régime de corrélation** | le book FTMO (US100/GER40/or, **aucune duration**) est **inerte** ; seul le book perso a le levier |
| **H — offre de titres** | futures ZN ⇒ IBKR |
| **G — propagation** | forme viable = futures en journalier ⇒ IBKR |

Le dépôt avait déjà noté « troisième edge d'affilée dont la maison est IBKR et non FTMO ⇒ motif
structurel ». Ce round en ajoute quatre d'un coup. **Ce n'est plus un motif, c'est le résultat
principal** : la recherche produit des edges dont le véhicule n'est pas celui où le capital est
déployé, et **le compte IBKR n'est pas ouvert** (chemin critique ~2 semaines, calé nov.-déc.).

⇒ **Recommandation opérationnelle : avancer l'ouverture IBKR.** Elle bloque désormais quatre axes
plus la sleeve month-end ZN déjà validée (+17,6 %/an, Sharpe 0,92). Chaque mois d'attente coûte une
occasion sur celle-ci et interdit toute mesure de coût sur les autres.

## 2. Classement

| | axe | statut | ce qui décide |
|---|---|---|---|
| **1** | **I — corrélation** | **test gratuit disponible** | données déjà au dépôt, test spécifié, jamais exécuté |
| **2** | **H — surprise de refinancement** | **porte préalable gratuite** | existe-t-il un consensus publié ? sans lui, pas de surprise mesurable |
| **3** | **F — variance d'événement** | mécanisme réel, économie mince | prime 45-53 pb annualisés ; bloqué sur IBKR |
| **4** | **G — propagation** | fondation la plus mince | pas de canal cross-classe documenté ; risque d'artefact élevé |

## 3. Ce que chaque axe a réellement établi

### I — régime de corrélation actions-obligations *(le plus honnête des quatre)*

Mécanisme **vérifié en sources primaires** (Cieslak-Pflueger, Bonelli-Palazzo-Yamarthy) : le signe de
la corrélation suit le signe de `Cov(inflation, croissance)`. Bascule datée ~2000-2001, retour en
territoire positif documenté (pics +0,50 en mai 2021 et décembre 2022).

**Le verdict de prévisibilité est net et il plafonne l'ambition : nowcasting oui, forecasting non.**
Un proxy court (2-3 mois) détecte le régime en quasi temps réel, mais l'indicateur institutionnel
standard (36 mois) n'a confirmé la bascule de 2021 qu'en **2023** — un retard d'environ deux ans
**arithmétiquement inévitable**, pas un défaut corrigible.

Sur la question L54, l'agent refuse de trancher et spécifie un test à la place — c'est la bonne
réponse. Son argument : un régime portant sur **N ≥ 2 actifs** offre un degré de liberté que L54
n'avait pas (recomposer à risque constant, au lieu de couper l'exposition). **Mais** la théorie
elle-même dit que la prime de risque de l'actif délaissé monte exactement quand sa qualité de
couverture se dégrade — ce qui **réintroduit le piège L54 sous forme testable**. C'est cette
tension qui doit être mesurée, pas arbitrée.

Applicabilité : **le book FTMO est inerte** (pas de duration). Le book perso (trend + month-end
obligataire, ρ ≈ 0,01) est le seul point de levier.

### H — offre de titres

Le balayage a trouvé `treasury_auction_2026-07/` : la concession d'adjudication est **déjà tuée**
(jambe nulle, t 0,48 ; DSR 0,863 ; ΔSharpe négatif contre la sleeve month-end). Sans le balayage,
l'axe repartait pour un cycle complet.

L'angle survivant est la **surprise de taille du refinancement trimestriel** — mécanisme réellement
distinct (information sur l'offre future, pas pression de flux à date connue).

⚠ **Porte préalable, gratuite et décisive** : une surprise suppose une attente mesurable. Existe-t-il
un consensus publié sur les montants de refinancement ? **Sans lui, on régresse sur le NIVEAU** — et
le contrôle de dose révélera que le seuil sélectionne une période, exactement ce qui vient de tuer
B3. À vérifier avant toute ligne de code.

Les positions de primary dealers sont reléguées en **filtre de régime** : le décalage de publication
interdit d'en faire un déclencheur.

### F — variance d'événement

Mécanisme confirmé : l'implicite monte dès J-2/J-1 (jusqu'à +50 % en 0DTE), la réalisée ne bouge
qu'après l'annonce. Prime documentée **45 pb CPI / 53 pb NFP / 49 pb FOMC**, annualisés — soit
~1,5 %/an au total. **C'est mince face à des écarts sur options retail.**

Queue chiffrée et sévère : skew −4,86, kurtosis +45, pire mois −64× sur la famille VRP déjà mesurée
en interne ; Volmageddon (déclenché par un rapport emploi) et le CPI du 13 sept. 2022 (−4,32 % sur
un écart de 0,2 pt). Une straddle nue ne survit pas ⇒ structure à risque défini obligatoire.

⚠ Un skew de cette nature sur un compte à barrière plafonne la probabilité de passage indépendamment
du rendement moyen — raison supplémentaire pour laquelle cet axe n'a rien à faire sur FTMO, même si
les options y existaient.

Falsificateur unique : `brut/coût_p95 ≥ 1,5` mesuré sur XSP réel.

### G — propagation cross-asset

Axe neuf (aucun test antérieur), mais **la fondation théorique est plus mince que je ne l'avais
supposée en le briefant** : Evans-Lyon donne une prédictibilité hors échantillon réelle, mais
**intra-classe FX et sur 10-20 jours**. Aucun canal cross-classe n'est documenté. L'axe passe donc
de « réplication d'un résultat connu » à « hypothèse originale ».

Risque L66 réduit mais réel : pas d'identité comptable déterministe entre taux/change/actions
(contrairement aux trois pattes d'une croisée), mais l'effet Epps demeure — et le lead-lag intraday
**change de comportement précisément aux annonces macro et à l'ouverture américaine**, là où on
voudrait mesurer.

Contribution originale de l'agent, à retenir : un **quatrième diagnostic, la transitivité** —
si taux→change et change→actions sont réels, taux→actions doit en être cohérent. Un artefact de
synchronisation n'a aucune raison de respecter cette contrainte. Bon marché, difficile à truquer.

Intraday proscrit (CFD 3 jambes ≈ 6-21 bps RT ⇒ mort au coût comme le FX intraday). Journalier en
futures défendable (1,2-3 bps), mais marge combinée ~$5 600 sur €13k ⇒ vol-targeting fin impossible.

## 4. Prochaines actions, par coût croissant

1. **Gratuit, décisif** — vérifier l'existence d'un consensus publié sur le refinancement trimestriel
   (axe H). Sans lui, l'axe s'arrête sans écrire une ligne.
2. **Gratuit, données déjà présentes** — exécuter le test de régime de corrélation spécifié par
   l'agent I sur le book perso, avec le test L54 en forme testable.
3. **Bloqué sur IBKR** — F et la mesure de coût de G. Et la sleeve month-end ZN, déjà validée,
   attend le même compte.

## 5. Leçon candidate

**Candidate « désalignement véhicule/capital »** — quand plusieurs axes de recherche successifs
désignent un véhicule où le capital n'est PAS déployé, ce n'est pas une coïncidence de sujets : c'est
que la contrainte de véhicule filtre en amont ce qui peut survivre. Mesuré ici : 4 axes sur 4 en un
round, après 3 d'affilée aux rounds précédents. ⇒ **Traiter l'ouverture du véhicule manquant comme un
livrable de recherche prioritaire**, au même titre qu'un test — il conditionne la valeur de tous les
autres.
