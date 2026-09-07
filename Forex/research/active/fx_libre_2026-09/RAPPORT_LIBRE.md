# Cohérence transitoire de cross-rate — fx_libre_2026-09

Session axe libre. Trois collègues couvrent en parallèle score macro, carry conditionnel au
swap, événements macro datés — axes explicitement écartés ici. Préenregistrement complet
avant tout accès aux données : `PREREGISTRATION.md`.

## 1. L'angle et pourquoi il n'est couvert par aucun kill existant

**Hypothèse testée** : l'écart entre une paire croisée cotée directement (EURJPY, AUDJPY,
EURGBP) et sa réplication synthétique via deux paires majeures partageant une devise
(EURUSD×USDJPY, AUDUSD×USDJPY, EURUSD/GBPUSD) prédit le rendement de la paire croisée à la
barre suivante (T-1 → T).

Ce n'est ni L43 (momentum/reversal/saisonnalité intra-paire), ni L34 (flux institutionnel),
ni L23 (fixing réformé), ni le carry G10, ni la cointégration statistique déjà fermée
(`research_history.md` : « Pairs cointegration 0/19, Gatev distance » — mécanisme de
régression sur historique de prix, PAS une identité arithmétique à trois pattes). L'arbitrage
triangulaire pur (exécution instantanée) est mort depuis 20 ans et n'a pas été retenté — ce
qui a été testé est un usage complètement différent de l'écart : comme **signal prédictif**,
pas comme opportunité d'exécution simultanée.

## 2. La grille — et un résultat qui a failli être un faux PASS

**18 cellules préenregistrées** (3 triangles × 3 fréquences × 2 lookbacks), signal T-1 /
trade T, HAC lag-6, two-sided :

| triangle | 5min lb20 | 5min lb60 | 15min lb20 | 15min lb60 | 60min lb20 | 60min lb60 |
|---|--:|--:|--:|--:|--:|--:|
| EUR-USD-JPY | t=-18.96 | t=-19.35 | t=-7.23 | t=-7.81 | t=-2.16 | t=-2.60 |
| AUD-USD-JPY | t=-22.91 | t=-23.57 | t=-10.68 | t=-16.00 | t=-14.91 | t=-14.47 |
| EUR-GBP-USD | t=-32.33 | t=-28.07 | t=-14.59 | t=-17.02 | t=-10.11 | t=-10.04 |

Max attendu sous H0 : `sqrt(2*ln(18)) = 2.40`. **18/18 cellules dépassent ce seuil, 17/18
dépassent |t|>2.5, TOUTES de même signe (négatif = réversion).** Un mécanisme mort donne une
distribution indiscernable de N(0,1) ; celle-ci ne l'est manifestement pas. **Le placebo
préenregistré (décalage circulaire >10 000 barres, 200 tirages/cellule, même pipeline) confirme :
placebo mean_t≈0.00-0.17, std_t≈1.0 (bien calibré, N(0,1)), max|t| placebo 2.5-4.1 — et les
18 t réels sont TOUS au 98.5-100e percentile de |placebo|.**

**Par la lettre du préenregistrement, ceci déclenche la validation formelle (§5).** Sur la
cellule la plus forte (EUR-GBP-USD, 15min, lb20) :
- **Walk-forward 4/4 folds** (schéma expanding, 5 découpes) : t = -5.54 / -4.21 / -3.94 /
  -8.71, signe constant.
- **Block-bootstrap** (Politis-Romano, blocs de 200 barres, 1000 tirages) : IC 95%
  [-0.156, -0.119] bps, exclut zéro.
- **MDE à 80% de puissance (L65)** : effet -0.138 bps, MDE 0.0265 bps, **ratio effet/MDE =
  5.21** — largement au-dessus de son propre plancher.

**Un signal qui passe la grille, le placebo temporel préenregistré, le walk-forward ET le
block-bootstrap ressemble, sur le papier, à un PASS en béton.** C'est exactement le piège :
avant de conclure quoi que ce soit, un contrôle supplémentaire était nécessaire — la
magnitude (t jusqu'à 32, aucun autre test FX de ce dépôt n'a produit un tel chiffre) et la
nature de la construction (une identité arithmétique entre trois instruments **cotés
séparément**, ré-échantillonnés en barres fixes) sont le signal d'alarme classique du
**non-synchronous trading (Fisher 1966)** : quand trois séries mises à jour de façon
asynchrone sont figées à un pas de temps commun, le « dernier print » de chaque série dans
la barre n'a pas le même âge — ce qui fabrique mécaniquement de la prédictibilité sans aucune
information économique. Le placebo à décalage circulaire ne teste QUE l'alignement temporel
d'une relation, jamais sa construction — donc il ne peut pas voir ce piège-là (c'est
précisément l'avertissement L62 : « vérifier l'artefact de son propre artefact »).

**Trois diagnostics ciblés, non préenregistrés mais motivés par ce risque spécifique**,
tranchent :

**(a) Test de saut (gap-test)** — sauter une barre entre le signal et la mesure du
rendement (prédire T→T+1 avec un signal à T-1, au lieu de T-1→T) :

| triangle | t (T-1→T) | t (GAP, T→T+1) | fraction conservée |
|---|--:|--:|--:|
| EUR-USD-JPY | -7.23 | **-0.47** | 6% |
| AUD-USD-JPY | -10.68 | -4.93 | 46% |
| EUR-GBP-USD | -14.59 | -3.42 | 23% |

Un décalage d'une seule barre supplémentaire fait s'effondrer l'essentiel de l'effet.
Une vraie information économique se dissipe progressivement ; un artefact de synchronisation
se résorbe dès la barre suivante — c'est exactement ce qui est observé.

**(b) Décomposition — l'écart prédit-il SEULEMENT la croisée, ou les trois pattes ?**
À 15min/lb20, `deviation_z(T-1)` prédit aussi les deux majeures, avec un t comparable et de
**signe systématiquement opposé** à celui de la croisée :

| triangle | fwd_cross | fwd_major1 | fwd_major2 |
|---|--:|--:|--:|
| EUR-USD-JPY | -7.23 | **+14.91** | **+11.23** |
| AUD-USD-JPY | -10.68 | **+12.57** | **+5.45** |
| EUR-GBP-USD | -14.59 | **+13.03** | **-11.88** |

Si l'écart révélait une vraie information sur la croisée, sa correction ne devrait pas se
répartir symétriquement sur les DEUX autres pattes avec des t du même ordre de grandeur.
C'est la signature d'un mécanisme qui ne « sait » pas laquelle des trois pattes est
« en retard » — cohérent avec un artefact de staleness générique, pas avec une information
dirigée sur la croisée.

**(c) Reconstruction TWAP (moyenne du bin) au lieu du dernier print** — si l'effet vient du
dernier print figé, moyenner sur le bin doit l'atténuer ou le détruire :

| triangle | t (last print) | t (TWAP/mean) |
|---|--:|--:|
| EUR-USD-JPY | -7.23 | -3.63 (÷2) |
| AUD-USD-JPY | -10.68 | **+0.51 (détruit, signe inversé)** |
| EUR-GBP-USD | -14.59 | -5.86 (÷2.5) |

AUD-USD-JPY — le triangle le plus fort de la grille brute — **s'effondre à zéro** sous
construction TWAP. Les deux autres perdent 50-60% de leur magnitude. Aucune ne survient
intacte.

**Verdict sur l'angle** : les 18 t-stats et leur passage du placebo préenregistré + WF +
bootstrap ne trahissent PAS une information tradable, mais un **artefact de construction**
(non-synchronous trading sur ré-échantillonnage multi-instruments) — assez robuste
statistiquement pour franchir tous les gates conventionnels, ce qui en fait un piège plus
dangereux qu'un simple bruit. Kill **MÉCANIQUE au sens de la politique de réouverture**
(l'effet s'annule sous une reconstruction TWAP identique en substance, et se résorbe en une
barre) — **non rouvrable** sans un changement de nature (p. ex. exécuter réellement sur des
ticks synchronisés, ce qui replace le sujet dans l'arbitrage triangulaire pur, déjà jugé mort
depuis 20 ans par consigne).

## 3. Gross/coût aux trois véhicules (même en ignorant le point 2, pour mémoire)

Position tenue 1 barre, coût = 1 aller-retour sur la seule paire croisée. Coûts RT mesurés
(`data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv`) : EURJPY 1.64 bps, AUDJPY 2.35 bps,
EURGBP 2.19 bps (FTMO). Eightcap Raw ~0.75 bps (valeur déclarée du brief, non vérifiée en
natif faute de données Eightcap dans ce dépôt). IBKR ~0.45 bps.

**Brut (grille non corrigée), meilleure cellule par triangle :**

| triangle | gross max (bps) | ratio @FTMO | ratio @Eightcap | ratio @IBKR |
|---|--:|--:|--:|--:|
| EUR-USD-JPY | 0.123 (60min/lb60) | 0.075 | 0.164 | 0.274 |
| AUD-USD-JPY | 1.085 (60min/lb60) | 0.461 | 1.447 | 2.412 |
| EUR-GBP-USD | 0.394 (60min/lb60) | 0.180 | 0.525 | 0.876 |

Seul AUD-USD-JPY à 60min approche/dépasse le seuil 1.5 — et exclusivement chez Eightcap/IBKR,
jamais chez FTMO. **Corrigé du test de saut** (résidu après un décalage d'une barre = borne
haute de ce qui pourrait survivre à une exécution réelle) :

| triangle | gross résiduel (bps) | ratio @Eightcap | ratio @IBKR |
|---|--:|--:|--:|
| EUR-USD-JPY | 0.005 | 0.007 | 0.012 |
| AUD-USD-JPY | 0.073 | 0.097 | 0.162 |
| EUR-GBP-USD | 0.026 | 0.035 | 0.058 |

Aucune cellule ne s'approche de 1.5 à aucun véhicule une fois la staleness retirée. Le seul
cas marginal (AUD-USD-JPY brut chez Eightcap/IBKR) est précisément celui que le test TWAP
détruit entièrement (t: -10.68 → +0.51).

## 4. Comptage

Δn_tests = **42** : 18 cellules de la grille préenregistrée (l'hypothèse testée) + 24
régressions de diagnostic (3 triangles × 2 constructions × 4 cibles) menées pour élucider
la nature du résultat de la grille — root-cause sur un résultat déjà signalé, pas une
recherche de signal alternatif. Walk-forward (4 folds) et block-bootstrap (1000 tirages) sur
1 cellule = validation d'UNE hypothèse déjà comptée, non recomptés séparément.

## 5. Verdict

**REJECTED — kill mécanique (artefact de construction, pas d'information).** L'angle
« cohérence transitoire de cross-rate » est neuf pour ce dépôt et a produit, sur sa grille
préenregistrée, une distribution de t qui a d'abord semblé être exactement le signal
recherché (18/18 au-dessus du seuil H0, placebo temporel dégagé, WF 4/4, bootstrap serré,
MDE ratio 5.2). Trois diagnostics ciblés (test de saut, décomposition symétrique sur les
trois pattes, reconstruction TWAP) montrent que cette robustesse statistique est la signature
d'un artefact de non-synchronicité de ré-échantillonnage, pas d'une prédictibilité
économique : l'effet se résorbe en une barre, se répartit symétriquement sur les trois
pattes au lieu de cibler la croisée, et s'effondre (jusqu'à disparaître, AUD-USD-JPY) sous
une construction TWAP qui devrait être neutre si le signal était réel. Le gross/coût,
lui-même déjà sous 0.9× à FTMO en brut et sous 0.2× partout une fois l'artefact retiré,
confirme qu'il n'y a rien à monétiser même en ignorant le diagnostic de construction.

**Leçon candidate (nommée, non gravée)** : *resampling_nonsync_fx* — Ré-échantillonner
plusieurs instruments cotés indépendamment vers un pas de temps commun (dernier print par
bin) fabrique une prédictibilité artificielle inter-instruments par staleness différentielle,
assez robuste pour passer placebo temporel + walk-forward + block-bootstrap (t jusqu'à 32,
MDE ratio 5.2). Diagnostics qui la détectent : (1) test de saut d'une barre — un vrai signal
se dissipe progressivement, un artefact de synchronisation s'effondre en une barre ; (2)
l'écart doit prédire SEULEMENT l'instrument visé, pas se répartir symétriquement sur les
autres pattes de l'identité ; (3) reconstruction TWAP (moyenne du bin) au lieu du dernier
print — si l'effet fond ou s'inverse, c'est la staleness, pas l'information. Un placebo à
décalage circulaire (temporel) ne détecte PAS ce piège car il ne teste que l'alignement, pas
la construction — famille L61/L62 (« vérifier l'artefact de son propre artefact ») étendue au
ré-échantillonnage multi-instruments plutôt qu'au sizing dépendant du chemin.

## Fichiers

- `PREREGISTRATION.md` — angle, grille, méthode, écrit avant tout accès aux données
- `run_grid.py`, `grid_results.csv` — grille principale (18 cellules) + audit barres plates L60
- `placebo_circular_shift.py`, `placebo_results.csv` — placebo préenregistré (décalage
  circulaire, 200 tirages/cellule)
- `diagnostics.py`, `diagnostics_out.log` — test de saut, décomposition, reconstruction TWAP
- `validation_wf_bootstrap.py` — walk-forward, block-bootstrap, MDE sur la cellule la plus
  forte
- `fasthac.py` — implémentation Newey-West manuelle (validée à 10 chiffres significatifs
  contre `statsmodels`, ~90× plus rapide — nécessaire pour les 200+ tirages de placebo sur
  jusqu'à 1.45M lignes)
