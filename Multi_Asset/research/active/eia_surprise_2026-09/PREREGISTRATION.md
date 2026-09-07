# PRÉ-ENREGISTREMENT — surprise d'inventaires EIA sur le pétrole

> **GELÉ avant tout contact avec les rendements.** À la rédaction j'ai vérifié la provenance du
> consensus et la structure des séries de prix ; **aucun rendement**. 2026-09-08.
> Origine : `macro_round4_2026-09/IDEES.md`, idée classée n°2.

## 1. Hypothèse

Une variation d'inventaires de brut **plus élevée que le consensus** (accumulation surprise) pousse
le prix du pétrole **à la baisse**, et réciproquement. Question : ce mouvement est-il exploitable
après le délai d'une barre, ou entièrement intégré à la publication ?

**Prior défavorable assumé** : c'est une publication très suivie. L'attente raisonnable est que le
mouvement soit instantané et que le résidu négociable soit nul. Le test sert à le **mesurer**, pas à
espérer le contraire.

## 2. Données — provenance vérifiée avant gel

**Consensus** : `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv`,
événement `EIA Crude Oil Stocks Change`, **438 observations** avec `actual` ET `forecast`,
2018-01-04 → 2026-06-03.

Contrôles de contamination passés :
- `forecast == actual` exactement : **0 fois** (une égalité systématique signalerait un remplissage
  a posteriori) ;
- `forecast == previous` : **0 fois** (exclut la copie paresseuse) ;
- corrélation prévision/réalisé **0,443** — compétence réelle mais imparfaite, cohérent avec un
  vrai consensus ;
- écart-type de la surprise **stable à ~4-6 Mb** sur les huit années, sans rupture.

**Prix** : `data/deep_history_utc/USOIL_M1.csv` (M1, vrai UTC, 4,43 M barres depuis 2013).

**Horodatage** : les heures de publication du calendrier sont utilisées **telles quelles**
(14:30 UTC l'été / 15:30 l'hiver, plus quelques décalages de semaines fériées). C'est le motif DST
exact que L56 impose de respecter ; le fournisseur porte l'heure réelle, on ne la reconstruit pas.

## 3. Signal — paramètres gelés

- **Surprise** = `actual − forecast`, en millions de barils.
- **Côté** = `−signe(surprise)` : accumulation surprise ⇒ vente.
- **AUCUN SEUIL — tous les événements sont tradés.** Choix délibéré : un seuil introduit une
  sélection dont le contrôle de dose a montré (sur B3) qu'elle peut sélectionner une période plutôt
  qu'une dose. En tradant tout, la relation dose-effet devient un **diagnostic** et non un paramètre.
- **Entrée** : première barre M1 dont l'horodatage est **strictement postérieur** à la publication
  (délai d'une barre, règle maison).
- **Horizons** : 15, 60, 240 minutes, et clôture de séance.
- **Coût** : mesuré sur la colonne `spread` de la série si elle est peuplée, sinon sur le panel de
  coûts mesurés. Brut **et** net rapportés séparément.

## 4. Critères, écrits avant de voir quoi que ce soit

**KILL MÉCANIQUE** — brut indistinguable de zéro aux quatre horizons (|t_HAC| < 2,0 partout) ⇒ le
mouvement est intégralement dans la publication, famille fermée.

**KILL DE DOSE** — brut significatif mais **réponse plate en terciles de |surprise|** ⇒ ce n'est pas
la surprise qui agit mais la fenêtre ou la période. C'est le contrôle qui a invalidé B3, appliqué
ici en diagnostic principal. Une réponse non monotone est un échec au même titre qu'une réponse plate.

**KILL DE COÛT** — brut positif et monotone en dose, mais `brut < 3 × coût` (gate Israel-Jiang-Ross)
⇒ mort au coût, catégorie **rouvrable** si un véhicule matériellement moins cher apparaît.

**PASS** — brut positif, **monotone en terciles de dose**, et `brut > 3 × coût` sur au moins deux
horizons. Alors seulement : placebo apparié au jour de semaine, et test de stabilité par
sous-période.

## 5. Breadth

**~52 paris par an**, événements datés et non chevauchants. C'est la meilleure breadth de tout le
programme macro — les axes précédents plafonnaient entre 2 et 32.

## 6. Comptage

**4 essais** (un par horizon). Programme macro : 9 → 13. Global figé.
