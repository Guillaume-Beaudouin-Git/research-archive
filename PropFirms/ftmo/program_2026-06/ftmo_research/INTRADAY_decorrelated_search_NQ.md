# Recherche — stratégie intraday simple, décorrélée de l'ORB, Sharpe>1 (single-asset FTMO)

> **TL;DR — Aucun signal intraday simple décorrélé à Sharpe>1 robuste trouvé.** 6 signaux canoniques testés sur NQ 2010-2026 + cross-check EURUSD. Tout se réduit à du **beta long one-sided** (intraday momentum) ou à du **bruit après coûts** (gap-fade, overnight). Le seul candidat apparent — **gap-fade sur gros gaps (|gap|>2 %, SR 1,47)** — est un **artefact low-N** : bootstrap CI95 [−1,87 ; +4,50], 85 % du PnL sur 2 années, et s'effondre à SR 0,07 dès qu'on élargit le seuil à 1,5 %. Cohérent avec les ~1 100 trials de l'arc (plafond robuste 0,34). **Décorrélation OK (corrORB ≈ 0,00) — c'est l'EDGE qui manque, pas la décorrélation.**

---

## 1. Périmètre & méthode

- **Donnée** : NQ 1-min databento 2010-2026, sessions RTH ET, 3 970 jours. Panel `outputs/nq_intraday_panel.parquet` (gap overnight, r_first30, r_last30, r_rest 10:00-16:00, r_rth open-close, rv20).
- **Coûts** : 2 bps RT (CFD US100). Intraday → pas de financement overnight (avantage : pas de swap).
- **Rigueur** (règles maison) : Sharpe NET, t-HAC lag-6, two-sided (L25), stabilité 5 folds, **corrélation au PnL ORB**, bootstrap CI sur le Sharpe, sensibilité au seuil, conscience multiple-testing.
- **Décorrélation cible** : |corr| au PnL quotidien de l'ORB V2+E7 < ~0,3.

## 2. Résultats — premier passage (signaux bruts)

| Signal (fenêtre tenue) | SR net | t-HAC | two-sided L/S | 5 folds | corr ORB |
|---|---:|---:|---|---|---:|
| IntraMom last30 ~first30 (Gao) | −1,15 | −0,53 | −1,22 / −1,09 | tous − | +0,08 |
| IntraMom rest 10-16 ~first30 | +0,25 | +1,41 | **+0,60 / −0,11** | instable | +0,32 |
| Gap-FADE open-close ~ −gap | −0,28 | +1,24 | +0,27 / −0,76 | mixte | **+0,00** |
| Gap-FADE rest ~ −gap | −0,54 | +0,54 | −0,08 / −0,95 | − | +0,02 |
| Gap-CONT rest ~ +gap | −0,15 | −0,54 | +0,21 / −0,55 | − | −0,02 |
| Overnight-CONT rest | −0,23 | +0,01 | +0,12 / −0,60 | − | +0,13 |

**Lecture :** le seul SR positif (IntraMom rest +0,25) est **one-sided** (long +0,60, short −0,11) = il capture la dérive haussière du matin = **beta**, et il est **corrélé à l'ORB (+0,32)**. Échoue L25. Tous les autres sont nuls/négatifs après coûts. Le gap-fade est **parfaitement décorrélé (0,00)** mais sans edge.

## 3. Deuxième passage — gap-fade conditionnel par taille

| bucket |gap| | n | SR fade | two-sided L/S |
|---|---:|---:|---|
| 0,0-0,3 % | 1713 | −0,76 | −0,12 / −1,38 |
| 0,3-0,6 % | 1062 | −0,03 | +0,41 / −0,37 |
| 0,6-1,0 % | 620 | −0,10 | −0,77 / +0,38 |
| 1,0-2,0 % | 417 | −0,33 | +1,48 / −2,14 |
| **>2,0 %** | **94** | **+1,47** | **+1,91 / +0,88** |

L'edge n'apparaît **que** dans le bucket extrême >2 % (le 1-2 % est mauvais). Discontinuité = drapeau rouge sur-ajustement.

## 4. Post-mortem du candidat (la discipline qui sauve du capital)

Le gap-fade >2 % (SR 1,47, two-sided, 4/5 folds +) **ressemblait** à un gagnant. La vérification le tue :

| test | résultat | verdict |
|---|---|---|
| **Bootstrap CI95 (Sharpe)** | **[−1,87 ; +4,50]** | inclut 0 et négatifs → non-significatif à n=94 |
| Concentration annuelle | **85 % du PnL sur 2 années** (2022, 2025) | non robuste |
| Années positives | 9/15 (60 %) | ≈ pile ou face |
| **Sensibilité seuil** (>1,5 % au lieu de >2 %) | SR **1,47 → 0,07** (n=221) | l'effet n'existe que sur 94 points extrêmes |
| corr ORB | +0,01 | décorrélé (mais sans edge) |

→ **Faux positif typique L12 (low-event-count).** Sans la vérification, on aurait risqué du capital sur du bruit. C'est le livrable réel de cette recherche.

## 5. Cross-check autre actif — EURUSD (2020-2026, m5)

Gap-fade daily SR +0,15 ; gap-cont −1,51. **Rien.** (Cohérent avec l'arc FX : London ORB, fix-flow, round numbers — tous morts.)

## 6. Verdict & avenues restantes

**Verdict :** pas de stratégie intraday simple décorrélée à Sharpe>1 robuste sur NQ/EURUSD. La décorrélation est facile (le gap-fade l'est) ; c'est l'**edge** qui n'existe pas en price-pattern simple, exactement comme sur les 1 100 trials précédents.

**Avenues NON encore testées** (si l'équipe veut pousser, à greenlighter une par une pour limiter le multiple-testing) :
1. **Ouverture-range mean-reversion intraday** (fade du 1er mouvement DANS la session, pas le breakout) — variante non couverte ici.
2. **Conditionnement événementiel** : jours FOMC / NFP / OPEX (drift pré-FOMC documenté), day-of-week.
3. **Autres actifs FTMO intraday** : Gold (XAUUSD), US30, GER40 — micro-structures différentes (données intraday à fetcher).
4. **Gao et al. — paires de demi-heures fines** (autres que first→last) — MAIS forte inflation multiple-testing, DSR obligatoire.
5. **Microstructure** (order-flow imbalance, VWAP-deviation fine) — sort du cadre "simple/basic".

**Recommandation :** avenue 2 (conditionnement événementiel) et 3 (Gold/indices) sont les meilleurs rapports signal/risque-de-mining. Les autres sont soit redondantes avec l'arc, soit hors périmètre "simple".

---

## 7. CONTINUATION — saisonnalité intraday + overlays calendaires

### 7.1 Fenêtres horaires (long-only)
| fenêtre | SR net | note |
|---|---:|---|
| close 15:30-16:00 (MOC) | −1,01 (t −4,03) | **faux signal** : moyenne brute ≈ 0, le SR = juste le coût 2bp ; shorter paie le même coût. Non-tradable. |
| rest 10:00-16:00 | +0,02 | nul |

### 7.2 Calendaire
- **Turn-of-Month** : ToM long r_rth SR +0,46 (t 0,87, n 768) vs non-ToM +0,08. Décorrélé (corr +0,05) mais **t<2, pas >1**. Cohérent avec l'arc (ToM ~0,33).
- **Day-of-week (long r_rth)** : Lun **+1,31** (t 2,15) · Mar +0,35 · Mer +0,11 · Jeu −0,36 · Ven −0,45.

### 7.3 Post-mortem du candidat « Lundi » (SR 1,31, décorrélé)

Meilleur lead de toute la recherche intraday — et plus solide que le gap-fade (bootstrap CI **[+0,14 ; +2,47]** entièrement positif, lift **+1,16** vs beta unconditionnel, corrORB +0,06). **Mais il échoue les gates OOS/multiple-testing :**

| test | résultat | verdict |
|---|---|---|
| 5 folds temporels | [−0,04, +0,15, −0,77, **+2,78, +3,86**] | **absent 2010-2019, concentré 2020-2026** |
| Concentration | **90 % du PnL sur 3 années** (2022-24) | régime bull récent |
| Année min/max | −3,5 (2018) / +9,3 (2023) | instable |
| Bonferroni ×5 (5 weekdays) | p 0,024 → **0,119** | **ÉCHOUE multiple-testing** |

→ **Artefact de régime, pas edge durable.** L'effet « lundi haussier » 2022-2024 = la dérive bull récente clusterisée le lundi, absente la décennie précédente. Même schéma que tout l'arc : signal in-sample/régime-récent qui s'évapore OOS. *(Réplication cross-asset S&P/Dow/DAX prévue mais bloquée par instabilité réseau sandbox ; le split OOS intra-NQ tranche déjà.)*

### 7.4 Verdict de continuation
Deux passes supplémentaires (saisonnalité + calendaire) → **toujours aucun Sharpe>1 robuste décorrélé.** Le « lundi » était le plus proche (décorrélé, CI in-sample positif) mais purement régime-récent. **Deux faux positifs déjà attrapés par la discipline (gap-fade, lundi)** — preuve que le risque dominant en continuant est le faux positif, pas le faux négatif. La décorrélation reste facile ; l'edge durable n'existe pas en price-pattern simple sur NQ.

---
*Recherche 2026-06-02 (+ continuation). Données : `outputs/nq_intraday_panel.parquet`, NQ 1-min databento 16y, EURUSD m5. Tout backtest, 0 jour live. Sharpe net de coûts, bootstrap 3000 tirages, corr vs ORB V2+E7, Bonferroni multiple-testing.*
