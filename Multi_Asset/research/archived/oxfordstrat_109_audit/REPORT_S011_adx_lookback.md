# Rapport stratégie #7/109 (registre) — ADX Filter / Donchian (Test 2 : Filter Threshold & Look Back)

> **Note de numérotation :** position **#7** du registre maître (`/resources/`), URL `average-directional-index`. Fichiers nommés **S011** (la #7 avait été sautée initialement ; les fichiers `REPORT_S007–S010` correspondent aux #8–#11). Cf. en-tête de `_INDEX.md`.

**Pipeline :** `ftmo_lab v2-gates`. **Statut :** ❌ **DISCARD (2/4)** · **Source :** https://oxfordstrat.com/trading-strategies/average-directional-index/ (rating site : **D**). · 2026-06-05.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | **Identique à #6** (Donchian breakout + filtre ADX) mais **Entry_Channel=50 fixe** ; sweep **ADX_Look_Back × ADX_Threshold** |
| Cas de base (ADX_LB=14, ADX_Thr=0 = Donchian-50 pur) | **expR +0,0705 · PF 1,244 · Sharpe 0,57 · win 37,4 % · 2 242 trades · MaxDD −55,4 %** |
| **Gate 1 — Délai+1** | stop natif +0,57 → open[i+1] **+0,48** → ✅ **PASS** (breakout tenu long) |
| **Gate 2 — Two-sided** | long **+0,2155** / short **−0,0971** → ❌ **FAIL** (beta long, encore plus marqué que #6) |
| **Gate 3 — DSR (N=20)** | meilleur Sharpe **0,607** ≪ E[max] 1,871 → ❌ **FAIL** |
| **Gate 4 — OOS** | train +0,0700 → test **+0,0709** → ✅ **PASS** (robuste) |
| **VERDICT** | ❌ **DISCARD** (2/4) |

**Lecture.** Sœur de la #6 (la plus solide à 3/4). Même conclusion qualitative : le **breakout Donchian est un vrai signal de tendance** — **Gate 1 ✅** (stop tenu long, pas d'artefact) et **Gate 4 ✅** (test Sharpe +0,071, robuste OOS) — **mais c'est du beta long** (Gate 2 : long +0,22 / short −0,10, encore plus asymétrique que #6) **et indistinguable du bruit** (Gate 3 : ici la grille ADX_LB×ADX_Threshold ne contient pas l'outlier sparse à grand canal qui faisait passer le DSR de #6 ; le meilleur Sharpe n'est que 0,61). **ADX n'ajoute aucune valeur robuste** (la colonne `ADX_Threshold=0` est constante à +0,0705 ; les seuils élevés raréfient et déstabilisent) — **confirme la conclusion de la fiche.**

---

## 1. Spécification (reproduite fidèlement)
Donchian breakout + ADX (Wilder/Donchian), **identique à #6** sauf : **`Entry_Channel=50` fixe** (`Exit_Channel=25`) ; **sensibilité `ADX_Look_Back [10,60] × ADX_Threshold [0,35]`** (#6 balayait Entry_Channel × ADX_Threshold). Entrée stop breakout ; sorties canal opposé (25) + ATR(20)×6 ; filtre `ADX[i−1] ≥ ADX_Threshold`. Écarts vs site idem S001-S010.

## 2-5. Univers / données / coûts / archétype (partagés)
Identiques. **Archétype = STOP-entry (breakout) tenu long** → artefact de fill dilué (cf. `REPORT_S006 §5`). Sim `simulate_donchian` (réutilisée de S006, `Entry_Channel=50`, `compute_adx(ADX_Look_Back)` variable). Réutilise `ftmo_lab` v2-gates (coûts, `trade_metrics`, 4 gates). Mapping fills : `'stop'`=niveau canal, `'next_open'`=open[i+1], `'close'`=close[i].

## 6. Paramètres
`Entry_Channel=50`/`Exit_Channel=25` fixes · `ADX_Look_Back` {10,14,20,30,60} (réf. 14) × `ADX_Threshold` {0,10,20,30} (réf. 0) = **20 cellules** (DSR) · `ATR` 20/6 · `RISK_FRAC` 0,5 %.

---

## 7. Résultats
**Cas de base :** 2 242 trades · win 37,4 % · expR +0,0705 · PF 1,244 · Sharpe 0,57 · MaxDD −55,4 % · 18/30 positifs.
**Par instrument (`results/s011_per_instrument.csv`) :** XAUUSD (+0,79), BTCUSD (+0,61), ETHUSD (+0,49), USDCHF (+0,36), XPTUSD (+0,29) ; bas : WHEAT (−0,10), AUDUSD (−0,19), NZDUSD (−0,24), EURGBP (−0,29). Crypto/métaux portent, FX/grains perdent (trend long classique).
**Sensibilité (`results/s011_sensitivity.png` / csv) :** colonne **ADX_Threshold=0 constante** (+0,0705 — sans filtre, le Look_Back est sans effet) ; seuils ADX élevés = marginal puis instable (LB30/60 négatifs à ADX≥30, sparse). **ADX value-add quasi nul** (+0,0705 vs +0,0874 « best »). Tous Sharpe ≤ 0,61 → DSR.

## 8. GATES — `results/s011_gates.csv`

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | stop +0,57 → open[i+1] **+0,48** | ✅ **PASS** |
| 2 | **Two-sided** | long **+0,2155** / short **−0,0971** | ❌ **FAIL** — beta long |
| 3 | **DSR (N=20)** | best Sharpe **0,607** ≪ 1,871 | ❌ **FAIL** — bruit |
| 4 | OOS | train +0,0700 → test +0,0709 | ✅ **PASS** |

**Verdict : DISCARD (2/4).** Vrai signal trend (Gate1+OOS), mais **beta long** (Gate 2) + **bruit** (Gate 3) ; **MaxDD −55 %** intradeable FTMO. **Différence vs #6 :** #6 passait le DSR grâce à un outlier sparse (grand canal) ; ici la grille n'en a pas → DSR FAIL. Les deux ADX confirment : **l'ADX n'ajoute rien** au Donchian de base.

## 9. Disposition
Même que #6 : candidat éventuel pour un **sleeve long-only trend vol-targeté vs buy&hold**, pas une stratégie symétrique. **Archivé DISCARD.** Clôt le sous-cluster ADX/Donchian (#6-#7).

## 10. Reproduction
`cd oxfordstrat_109/code && python strat_s011_adx_lookback.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3 ; matplotlib 3.10.8 ; pyarrow 24.0.0). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s011_adx_lookback.py`.
