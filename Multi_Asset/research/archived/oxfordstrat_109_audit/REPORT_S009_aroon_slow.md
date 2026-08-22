# Rapport stratégie 9/109 — Aroon Indicator Breakout (Test : Setup 2 & Exit)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/aroon-indicator-breakout-3/ (rating site : **C**).
**Date :** 2026-06-05 · **Registre :** entrée **#9** de `_INDEX.md`.

> ⚠️ Règle : KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Aroon **slow** (`Aroon_Index=100`) ; entrée market-on-open ; sorties Time + ATR |
| **Angle distinct vs S007/S008** | `Aroon_Index` **fixé à 100** (le lookback lent = la région positive de S007/S008) ; sweep **Min_Aroon × Time_Index** |
| Univers | 30/40 instruments FTMO |
| Point réf. (Min_Aroon=50, Time=20) | **expR +0,0197 · PF 1,082 · Sharpe 0,44 · win 50,6 % · 5 689 trades · MaxDD −48,9 %** |
| **Gate 1 — Délai+1** | natif +0,44 → délai open[s+2] **+0,42** → ✅ **PASS** (signal lent robuste) |
| **Gate 2 — Two-sided** | long **+0,069** / short **−0,051** → ❌ **FAIL** (beta long) |
| **Gate 3 — DSR (N=20)** | meilleur Sharpe **0,610** ≪ E[max] 1,871 ; z −71 → ❌ **FAIL** |
| **Gate 4 — OOS** | train +0,0273 (Sh +0,52) → test **+0,0130** (Sh +0,36) → ✅ PASS |
| **VERDICT** | ❌ **DISCARD** (2/4 FAIL) |

**Lecture.** En fixant `Aroon_Index=100`, on isole **la version lente** de l'oscillateur — celle qui était positive dans les grilles S007/S008. Résultat : c'est un **signal de tendance robuste** (Gate 1 ✅ — l'edge survit à la latence, contrairement au burst new-high de S008 ; Gate 4 ✅ — tient OOS), **mais** c'est du **beta de tendance long** (Gate 2 ❌ : shorts perdent) **indistinguable du bruit** (Gate 3 ❌) et avec un **MaxDD −49 %**. Même profil que S003/S006 côté long-beta. **DISCARD.**

---

## 1. Spécification (reproduite fidèlement)
Identique à S007/S008 (Aroon, Chande, C), **sauf** : `Aroon_Index` **fixé à 100** ; `Min_Aroon` balayé [30,100] ; `Time_Index` balayé [1,40] ; axes de sensibilité **Min_Aroon × Time_Index**. Entrée buy-at-open ; sorties Time + Stop ATR(20)×6. Écarts vs site idem S001-S008.

## 2-5. Univers / données / coûts / look-ahead / archétype (partagés)
Identiques à S001-S008. **Archétype = entrée market-on-open** (pas de stop intrabar → pas d'artefact). Aroon vectorisé, `Aroon_Index=100` calculé une fois par instrument. Sim **`simulate_aroon`** (open, Time/ATR), `R=ATR×6`. Réutilise `ftmo_lab` v2-gates (coûts, `trade_metrics`, 4 gates). Mapping fills : `'stop'`=open[s+1] natif, `'next_open'`=open[s+2] (Gate 1), `'close'`=close[s+1].

## 6. Paramètres
`Aroon_Index=100` fixe · `Min_Aroon` balayé {30,50,70,90,100} (réf. 50) × `Time_Index` {1,10,20,40} (réf. 20) = **20 cellules** (DSR). `ATR` 20/6, `RISK_FRAC` 0,5 %.

---

## 7. Résultats
**Réf. :** 5 689 trades · win 50,6 % · expR +0,0197 · PF 1,082 · Sharpe 0,44 · MaxDD −48,9 % · 15/30 positifs.
**Par instrument :** XPDUSD (+0,152), XAUUSD (+0,094), ETHUSD (+0,071), XAGUSD (+0,069), BTCUSD (+0,064) ; bas : USDCAD, NZDUSD, AUDJPY, USDCHF (−0,158). Commodities/crypto portent, FX perd (signature trend, biais long).
**Sensibilité (`results/s009_sensitivity.png`) :** 80 % positif ; **Time=1 négatif** ; positif surtout en **hold long** (T40). `Min_Aroon` a peu d'effet (lignes similaires). Tous Sharpe ≤ 0,61 → DSR.

---

## 8. GATES — `results/s009_gates.csv`

| # | Gate | Résultat (MA=50, T=20) | Verdict |
|---|---|---|---|
| 1 | **Délai+1 (L26)** | natif +0,44 → open[s+2] **+0,42** | ✅ **PASS** (signal lent robuste à la latence) |
| 2 | **Two-sided (L25)** | long **+0,0687** (n=3353) / short **−0,0508** (n=2336) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=20)** | best Sharpe **0,610** ≪ E[max] 1,871 ; z −71 | ❌ **FAIL** — bruit |
| 4 | **OOS** | train +0,0273 → test +0,0130 | ✅ PASS |

Chance donnée au favorable (MA=30, T=40) : expR +0,048 mais two-sided **long +0,144 / short −0,087** (Gate 2) + DSR → **DISCARD** aussi.

**Lecture.** Contrairement à S008 (new-high, burst d'un jour tué au Gate 1), la version **lente** passe Gate 1 et Gate 4 — c'est un vrai signal de tendance — mais reste **long-beta** (Gate 2) et **statistiquement nul** (Gate 3). MaxDD −49 % en prime.

---

## 9. Limites & checklist
- Grille 20 cellules (DSR N=20, E[max]=1,87) ; structure inchangée.
- Cluster trend-following (S003-S009) : mort dominante **Gate 2** (beta long). Voir `REPORT_S006` pour la piste long-only vol-targetée — S009 (slow, Gate1+Gate4 OK) en serait un autre candidat *long-only* à comparer vs buy&hold.
- Frontière de bougie, couverture 30/40 : idem S001 §9.

## 10. Reproduction
```bash
cd oxfordstrat_109/code && python strat_s009_aroon_slow.py
```
Env : Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0. Sorties : `results/s009_*`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s009_aroon_slow.py`
Moteur `ftmo_lab.py` partagé (cf. `REPORT_S001` Annexe A). Machinerie Aroon identique à S007/S008 (cf. `REPORT_S007` Annexe) avec **`Aroon_Index=100` fixe** et **balayage `Min_Aroon × Time_Index`**. Source faisant foi : `code/strat_s009_aroon_slow.py`.
