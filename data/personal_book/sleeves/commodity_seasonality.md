# Commodity seasonality (return diversifier brick)

> **Statut** : VALIDÉ comme brique de combinaison. **NE PAS déployer seul.** Diversificateur de RENDEMENT décorrélé, pas une brique de FORME (skew daily négatif).
> **Source canonique** : `data/skew_research/session_basic_trend/exploration_mechanism_2026-06.md` (#5) + `session_basic_trend/commodity_seasonality_oos.csv`.
> **Référence archive** : `session_3/exploration_2026-06.md` (B3-4) — keeper archive cité non re-prouvé (Sharpe archive 0,30) ; le 0,33 OOS ci-dessous est la mesure session_basic_trend, plus récente et opérationnalisée.

---

## Ce que c'est

Calendar-driven seasonality sur le set commodities FTMO-tradeable : signe saisonnier par commodity × month-of-year, dérivé d'une fenêtre train (2006-15), appliqué OOS (2016-26). Mécanisme = cycles physiques production/demande (natgas hiver, gasoline été, ag harvest…).

## Spec figée

| Champ | Valeur |
|---|---|
| Signal | sign(seasonal_avg) par commodity × mois, dérivé en train 2006-15, **fixé** ensuite |
| Direction | two-sided (signe pris du train, appliqué OOS sans recalcul) |
| Univers | commodities FTMO-tradeables (XAUUSD, XAGUSD, XBRUSD, XTIUSD, XNGUSD, etc. — vérifier univers FTMO commodities courant) |
| Fréquence | mensuelle (signal fixe par mois calendaire) |
| Hold | semaines à mois (calendar window) |

## Métriques mesurées

| Sample | Sharpe | daily-skew | corr → equity | **corr → TSMOM** |
|---|---:|---:|---:|---:|
| Train 2006-15 (in-sample, référence) | +1,84 | — | — | — |
| **OOS 2016-26** | **+0,33** | **−0,83** | +0,03 | **+0,10** |

→ Décay IS→OOS **1,84 → 0,33** (substantiel mais OOS-stable, cohérent archive keeper).
→ **Seul candidat de la session basic_trend qui est BOTH décorrélé de TSMOM (0,10) ET OOS-stable.** Contrairement aux trend-bricks (corr ~0,5 → redondant) et à MACD (near-zero return), commodity seasonality ajoute une **source de rendement décorrélée** — calendrier, pas trend, d'où la corrélation basse.

## Gate-0 FTMO

✅ **FTMO-tradeable.** Univers commodities FTMO (XAUUSD, XAGUSD, oil CFD, natgas CFD, etc.) couvre le set. Pas d'ETF, pas de futures-direct nécessaire.

→ Reste à vérifier au déploiement : (i) liste commodities FTMO actuelle 2026 ; (ii) spread/coût par symbole (certaines commodities CFD ont des spreads larges en heures off-peak).

## Distinction par rapport aux autres briques

| Brique | Mécanisme | Skew | Corr→TSMOM | Type |
|---|---|:---:|:---:|---|
| **TSMOM** | trend multi-actifs | mixte | 1,00 | moteur |
| **MACD** | fast-trend | +4,2 trade | +0,08 | shape (convexité) |
| **Commodity seasonality** | calendar physical cycles | **−0,83 daily** | **+0,10** | **return diversifier** |
| B1 (bond) | dash-for-cash event | ~0 horizon | (non mesuré) | event return |

→ MACD et commodity seasonality sont **décorrélés du moteur ET entre eux** (trend-shape vs calendar-return) → genuinely complémentaires *si* le moteur survit au swap test.

## ⚠ Caveats explicites

> **(a) Skew daily négatif (−0,83) → c'est un diversificateur de RENDEMENT, PAS une brique de FORME / convexité.** Peut prendre un grand jour saisonnier adverse. Ne pas l'attendre à protéger le tail.

> **(b) Décay IS → OOS (1,84 → 0,33).** Le décay est documenté ; le 0,33 peut continuer à dériver. À monitorer en re-mesurant OOS tous les ~2 ans.

> **(c) Held weeks → swap (L33).** Comme MACD, le hold long erode le 0,33 net. Pour commodities CFD FTMO, swap typiquement asymétrique — à mesurer broker (cohérent avec la mesure equity à −3,08 bps/nuit pour NQ ; commodities probablement variable selon symbole).

## Pourquoi dans personal_book

Comme MACD : brique de **combinaison**. Standalone SR 0,33 n'est pas un livre. La valeur vit dans la matrice de corrélation avec TSMOM (et MACD, et B1). Documenté ici comme composant du portefeuille combiné perso (qui restera la prochaine étape de construction).

## Pré-requis avant intégration

1. **Vérifier univers commodities FTMO 2026** (XAUUSD/XAGUSD/XBRUSD/XTIUSD/XNGUSD couverts ; vérifier ag/grains si visés).
2. **Mesurer swap par symbole** (les commodities CFD ont des swaps très asymétriques selon direction).
3. **Re-mesurer OOS** sur fenêtre roulante : le 0,33 OOS 2016-26 peut être devenu 0,2-0,3 sur 2020-26. Vérifier avant d'allouer.
4. **Comme pour MACD** : validation du swap crypto TSMOM avant d'optimiser les overlays — un return diversifier 0,33 n'aide pas si le moteur est net-négatif après swap.

## Réconciliation archive

- **Keeper archive** (session_3 B3-4) : Sharpe 0,30 cité, **non re-prouvé** par signe-saisonnier naïf (t=−0,52 sur proxy expanding). L'edge archive est **method-specific** (sign train→apply OOS), pas saisonnalité naïve.
- **session_basic_trend** opérationnalise proprement (sign mois×commodity train 06-15 → OOS 16-26) et confirme 0,33 OOS.
- Pas re-prouvé en backtest indépendant ; à valider sur le set commodities FTMO précis avant déploiement.

## Leçons (candidates)

- *« commodity seasonality = la seule brique genuinement additionnelle décorrélée (corr 0,10, OOS Sharpe 0,33) »* — un diversificateur de rendement calendrier (skew−, donc pas convexité), seul OOS-stable de l'archive, FTMO-tradeable.
- *« day-of-week sans mécanisme pré-spécifié = mining »* (rejected #4 BTC-Monday t=3,29 : max sur ~60 combos sans mécanisme cité d'abord).
- *« crypto = strongest trend sub-component (Sh 1,12, skew+) »* — implication = TSMOM doit surpondérer crypto, pas un sleeve séparé.
