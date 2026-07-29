# PRE-REGISTRATION (FROZEN before results) — CS macro momentum, FTMO-targeted

**Gelée le 2026-07-29, AVANT tout backtest.** Source : post promotionnel revendiquant
CAGR 21.4 %, MaxDD −22.8 %, vol 8.9 %, Sharpe 1.04, et FTMO 2-step 79 % / 85 % → **65.7 %**.

## 0. Métrique de DÉCISION — ce n'est PAS le Sharpe

L'objectif du projet est de **passer un challenge, vite**, pas de maximiser un ratio.
La décision se prend sur, dans cet ordre :

1. **p(pass global 2 phases)** — phase 1 (+10 %) puis phase 2 (+5 %), barrières FTMO
   −5 % daily / −10 % statique, sans limite de temps (le mur de 91 j est auto-imposé) ;
2. **durée médiane et p90** jusqu'au funded ;
3. décomposition des morts : barrière **journalière** vs **floor** statique.

Le Sharpe n'est rapporté qu'en contexte. Une variante à Sharpe inférieur mais p(pass)
supérieur **gagne** — c'est la correction d'objectif du 2026-07-29.

## 1. Incohérences de la source (documentées AVANT de tester)

Les métriques annoncées ne peuvent pas être vraies simultanément :

| Contrôle | Annoncé | Vérifié |
|---|---|---|
| Sharpe | 1.04 | CAGR/vol = 21.4/8.9 = **2.40** (1.96 net d'un rf 4 %) |
| P(phase 1) | 79 % | première traversée avec drift : **99.6 %** aux métriques annoncées, **91.2 %** à Sharpe 1.04 cohérent |
| MaxDD | −22.8 % | **2.3× le floor FTMO** → la série réelle traverse le plancher |

MaxDD/vol = **2.56** (une gaussienne à Sharpe ~1 sur 8 ans donne 1.0-1.5×) ⇒ pertes en
grappes. Un Monte-Carlo **iid** casse ces grappes et surestime p(pass). **On n'utilise donc
aucun de leurs chiffres** : on mesure les nôtres, en bootstrap par blocs.

## 2. Univers (16, FTMO-tradable, deep_history_utc true-UTC) et fenêtre

`2013-10-01 → 2026-06-05` — la première date où **tous** les instruments coexistent
(US30 et GER40 démarrent 2013-09-30). 12.7 ans, couvre COVID et 2022.

- **FX (7)** : EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD
- **Indices (4)** : US30, US100, US500, GER40
- **Métaux (3)** : XAUUSD, XAGUSD, COPPER
- **Énergie (3)** : UKOIL, USOIL, NGAS

**BTC est EXCLU du test principal** (Binance ne commence qu'en 2017). Il fera l'objet d'une
mesure séparée sur 2017+ pour isoler sa contribution — jamais mélangé à la fenêtre principale.

### Dérogation explicite à la hard rule N ≥ 30

N=16 < 30. Dérogation **assumée et bornée** : la règle N≥30 existe pour rendre un IC
cross-sectionnel estimable ; ici 16 instruments × 12.7 ans × 2 rebalances/semaine ≈
**21 000 instrument-observations**. En contrepartie : **haircut de breadth √N appliqué au
Sharpe rapporté**, et aucun IC cross-sectionnel ne sera cité comme significatif isolément.

## 3. Signal — figé

Ranking cross-sectionnel, recalculé à chaque rebalance, sur données **T-1** (signal à T-1,
trade à T — hard rule) :

- `trend` = signe du rendement 60 j
- `mom_risk_adj` = rendement 120 j / vol réalisée 60 j (annualisée)
- `volume_proxy` = |rendement| 20 j / vol 60 j (le volume tick n'est pas fiable en CFD ;
  ce proxy est déclaré ici et ne sera pas modifié après résultats)

Score = moyenne des rangs normalisés des trois composantes. **Top 4** retenus, équipondérés
en risque (inverse-vol). Long-only sur le score positif ; **une jambe short symétrique est
testée en contrôle L25** (un edge directionnel réel est positif des deux côtés).

Overlay de régime de vol : exposition × `clip(vol_cible / vol_réalisée_20j, 0.5, 1.5)`.

## 4. Coûts — mesurés, jamais supposés

- **spread** : mesuré par barre depuis `deep_history_utc` (colonne spread calibrée) ;
- **swap** : sur **notionnel tenu par jambe**, deux directions, ancres `measured_specs`
  du yaml v2.2.2, triple le jour de rollover par symbole ;
- commission incluse.

C'est le point où L36 mord ou pas : 4 positions tenues en permanence, rebalance 2×/semaine.
**On mesure, on ne suppose pas.**

## 5. Variantes — 4 essais pré-enregistrés (budget : 3 modifications)

| | Spec | Question tranchée |
|---|---|---|
| **V0** | base §3, rebalance 2×/semaine | la stratégie annoncée survit-elle à mes coûts ? |
| **V1** | V0 **sans** overlay de vol | « le ranking est cosmétique, l'edge vit dans l'overlay » est-il vrai ? |
| **V2** | V0, **rebalance mensuel** | sensibilité au carry/rotation (L36). Mesuré sur Strategy B : la rotation fait passer un Sharpe de +11 à −114 |
| **V3** | V0, **intraday-flat** | échappatoire L36 (zéro swap) — retombe alors sur L33b (le spread) |

**Balayage de taille (`vm`) pour CHAQUE variante** : ce n'est pas une modification de
stratégie mais du sizing, et c'est lui qui pilote p(pass) (mesuré sur le livre réel :
vm=8 → p 0.314 en 35 j ; vm=14 → p 0.195 en 16 j). Ne consomme pas le budget de modifications.

## 6. Kill rules — PRÉ-ENREGISTRÉES

La famille est **abandonnée** si, sur la fenêtre principale :

1. **V0 et V2 et V3** ont tous p(pass global) **≤ celui d'un placebo** (rendements
   démeanés, mêmes barrières, même sizing) ; **ou**
2. le test **two-sided** (L25) montre que la jambe short n'est pas significative même à
   **coût nul** — l'edge est alors du beta long, pas du momentum ; **ou**
3. la régression sur un buy-and-hold vol-targeté des indices (L38) donne **R² > 30 %** —
   c'est du timing de beta, à présenter comme tel et non comme une sleeve neuve ; **ou**
4. le gross par rebalance est **< 1.5 × le coût mesuré p95** (L43 : le meilleur observé en
   FX intraday était 0.36 — mort).

Aucun de ces seuils ne sera ajusté après avoir vu les résultats.

## 7. Ce qui invaliderait le test lui-même

- Un `MaxDD` simulé très inférieur à −22.8 % ⇒ suspicion que notre reconstruction n'est pas
  la même stratégie : le signaler plutôt que de s'en réjouir.
- Un p(pass) supérieur à 65.7 % ⇒ **même exigence** : vérifier d'abord les coûts et le
  bootstrap avant de conclure quoi que ce soit.
- Bootstrap **par blocs** obligatoire (Politis-Romano). iid interdit — c'est précisément le
  défaut suspecté de la source.

## 8. Comptabilité des essais

Famille **neuve** : `cs_macro_momentum` × `deep_history_utc 2013-2026` × `univers 16`.
Compteur de famille **N1 = 4** (V0-V3). Le compteur global (321) est du contexte, pas une
entrée de déflation — la déflation se fait **à N1 dans la famille** (correction du 2026-07-29).
DSR calculé avec `std_sr_trials` **déclaré et mesuré** (`dsr.py` recalibré), jamais le
défaut historique.
