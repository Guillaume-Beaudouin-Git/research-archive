# Préenregistrement — Cohérence transitoire de cross-rate (fx_libre_2026-09)

Écrit AVANT tout accès aux séries de prix (seul le schéma des fichiers a été inspecté :
colonnes, plage de dates, format d'index). Axes interdits (couverts par des collègues en
parallèle) : score macro, carry conditionnel au swap, événements macro datés. Axes fermés
du dépôt (L43, L34, L23, carry G10, L36, fix-reversal, month-end FX, sentiment, MR intraday) :
non retentés sans angle neuf.

## 1. Angle

**La paire croisée cotée directement (EURJPY, AUDJPY, EURGBP) et sa réplication synthétique
via deux paires majeures partageant une devise commune (EURUSD×USDJPY, AUDUSD×USDJPY,
EURUSD/GBPUSD) peuvent transitoirement diverger.** L'arbitrage triangulaire PUR est mort
depuis 20 ans (exécution en microsecondes, consigne explicite de ne pas le retenter) — mais
l'écart lui-même, en tant que **signal prédictif** de la direction de la paire croisée sur
la barre suivante, n'a jamais été testé dans ce dépôt (`research_history.md` liste
« Pairs cointegration (0/19) » et « Gatev distance » = stat-arb classique sur DEUX séries de
prix indépendantes, mécanisme différent de la relation ARITHMÉTIQUE à trois pattes ici).

**Mécanisme hypothétique** : la paire croisée cotée en direct et la combinaison synthétique
peuvent être updatées par des pools de liquidité / market makers différents, à latence
différente. Un écart transitoire peut signaler qu'une des trois pattes est "en retard" sur
l'information — et donc prédire un mouvement correctif dans la jambe en retard.

**Pourquoi ce n'est PAS L43/L34/L23/carry/MR intraday** :
- Ce n'est pas un signal de momentum, de flux ordonné institutionnel, de fixing, ni de carry.
- Ce n'est pas un test de MR intraday générique (la famille fermée ~1454 cellules testait
  des signaux intra-paire ; ici le signal est une relation ARITHMÉTIQUE ENTRE TROIS PAIRES).
- Ce n'est pas de la cointégration statistique (Gatev/pairs) : la relation testée ici est une
  IDENTITÉ COMPTABLE (log-cross = log-major1 + log-major2), pas une relation estimée par
  régression sur historique de prix.

## 2. Grille (préenregistrée, aucune sélection ex post)

**3 triangles**, tous couverts en M1 UTC vrai 2007→2026-06 (cache parquet vérifié) :
1. EUR-USD-JPY : cross = EURJPY, synthèse = EURUSD × USDJPY
2. AUD-USD-JPY : cross = AUDJPY, synthèse = AUDUSD × USDJPY
3. EUR-GBP-USD : cross = EURGBP, synthèse = EURUSD / GBPUSD

**3 fréquences d'échantillonnage** (barres resamplées depuis M1 close, dernier prix de la
fenêtre) : 5min, 15min, 60min. Pas de sub-5min (zone bid-ask bounce déjà établie morte,
L60/artefacts_construction : t=19.8 pour 0.20 bps de gross à cette fréquence).

**2 fenêtres de lookback pour le z-score** de l'écart : 20 barres, 60 barres (normalise le
régime de volatilité de l'écart lui-même avant de le régresser).

→ **18 cellules.** Max attendu sous H0 : `sqrt(2*ln(18)) = 2.40`.

## 3. Signal et test

- `deviation_t = ln(cross_t) - ln(synthetic_t)` (synthetic = produit ou ratio des deux
  majeures selon la convention de cotation ci-dessus).
- `deviation_z_t = (deviation_t - rolling_mean) / rolling_std` sur la fenêtre de lookback.
- Signal à **T-1**, trade à **T** (règle dure) : régression OLS
  `forward_return_cross_{T} ~ deviation_z_{T-1}`, HAC lag-6 (en barres de la fréquence
  testée), two-sided (aucun signe imposé a priori — H1a économique = réversion, mais le
  signe empirique de chaque cellule est rapporté tel quel).
- `forward_return_cross` = rendement log de la paire croisée entre T-1 et T (bar close-close).

## 4. Placebo de construction identique (obligatoire, L61)

Décalage circulaire aléatoire (>10 000 barres) de la série `deviation_z` par rapport à la
série `forward_return`, même pipeline de régression, 200 tirages par cellule → distribution
null empirique des t. Casse l'alignement temporel réel en conservant la structure
d'autocorrélation propre à chaque série (contrôle L62-style : le placebo doit avoir la même
géométrie que le test réel, pas une géométrie fabriquée).

## 5. Validation (si une cellule dépasse le seuil de la distribution placebo)

- Walk-forward ≥5 folds expanding.
- Block-bootstrap (Politis-Romano) pour l'IC du coefficient — jamais iid.
- MDE à 80% de puissance (facteur 1.40, L65), ratio effet/MDE rapporté.
- Rupture temporelle : seulement si estimée (Bai-Perron / balayage), jamais imposée (L64).

## 6. Gate économique — 3 véhicules, coûts mesurés

Position tenue 1 barre (5-60 min) sur UNE seule paire (la croisée) = 1 aller-retour par
signal. Seuil retenu : **gross/cost ≥ 1.5** (barre économique standard FX intraday retail,
répliquée 4× dans ce dépôt à des mécanismes différents — appliquée ici comme barre
générique, pas comme citation de L43 pour le verdict).
- Eightcap Raw : ~0.75 bps RT (à vérifier empiriquement si disponible, sinon valeur déclarée)
- FTMO : 2.48 bps RT mesuré (table swap/spread du brief)
- IBKR : ~0.4-0.5 bps RT (+ minimum $2/ordre, L57 — négligeable au notionnel FX standard)

## 7. Comptage

Δn_tests attendu de cette session = **18** (grille principale) + tirages de placebo
(non comptés comme tests séparés, c'est un contrôle de la distribution nulle) + tout test de
validation sur cellule(s) survivante(s) (compté séparément si déclenché).

## 8. Verdict attendu, honnêtement

Compte tenu de : (a) l'arbitrage triangulaire instantané est mort depuis 20 ans (le marché
équilibre l'écart en microsecondes bien en-deçà de 5 min), (b) la littérature de
microstructure ne documente pas de prédictibilité de plusieurs minutes sur ce type d'écart
sur les majeures G10 liquides, l'hypothèse nulle est **favorite**. Un résultat "distribution
indiscernable du bruit" sera rapporté comme tel — c'est un livrable valide.
