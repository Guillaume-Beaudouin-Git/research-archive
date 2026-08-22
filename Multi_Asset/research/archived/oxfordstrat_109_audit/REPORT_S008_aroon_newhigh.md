# Rapport stratégie 8/109 — Aroon Indicator Breakout (Test : Setup 1 & Exit)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/aroon-indicator-breakout-2/ (rating site : **C**).
**Date :** 2026-06-05 · **Registre :** entrée **#8** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Aroon **new-high breakout** (`Min_Aroon=100`) ; entrée market-on-open ; sorties Time + ATR |
| **Angle distinct vs S007** | `Min_Aroon` **fixé à 100** (entrée sur nouveau plus-haut sur Aroon_Index barres) ; **Time_Index balayé** (S007 fixait Time=20 et balayait Min_Aroon) |
| Univers | 30/40 instruments FTMO |
| Point réf. (Aroon_Index=25, Time=20) | **expR +0,0049 · PF 1,020 · Sharpe 0,10 · win 49,8 % · 4 844 trades · MaxDD −21,9 %** (edge marginal) |
| **Gate 1 — Délai+1** | natif +0,10 → délai open[s+2] **−0,07** → ❌ **FAIL** (micro-edge non robuste à la latence) |
| **Gate 2 — Two-sided** | long **+0,060** / short **−0,068** → ❌ **FAIL** (beta long) |
| **Gate 3 — DSR (N=20)** | meilleur Sharpe **0,591** ≪ E[max] 1,871 ; z −91 → ❌ **FAIL** |
| **Gate 4 — OOS** | train +0,0058 → test +0,0040 → ✅ PASS |
| **VERDICT** | ❌ **DISCARD** (3/4 FAIL) |

**Lecture.** Même famille que S007 mais avec `Min_Aroon=100` → entrée sur **nouveau plus-haut** (un breakout new-high entré à l'open, cousin de S006-Donchian mais sans stop intrabar). Cela donne un edge de base **marginalement positif** (+0,0049, là où S007 était négatif), mais : (1) **le Gate 1 le tue** — le micro-edge est un *burst de momentum d'un jour* qui s'inverse dès qu'on retarde l'entrée d'une barre (open[s+2]) ; (2) **Gate 2** : long-biaisé (shorts perdent) = beta de tendance ; (3) **Gate 3** : indistinguable du bruit. Bref, un breakout new-high réel mais **trop faible, fragile à l'exécution et asymétrique**.

---

## 1. Spécification originale (reproduite fidèlement)

Identique à S007 (Aroon, Chande, rating C), **sauf** :

| | S007 (Setup) | **S008 (Setup 1 & Exit)** |
|---|---|---|
| `Min_Aroon` | balayé [30,100] | **fixé à 100** (AroonUp=100 = nouveau plus-haut) |
| `Time_Index` | fixé 20 | **balayé [1,40]** |
| Axes sensibilité | Aroon_Index × Min_Aroon | **Aroon_Index × Time_Index** |

`AroonUp[i−1] ≥ 100` ⇔ le plus-haut des `Aroon_Index+1` dernières barres est `i−1` (nouveau plus-haut). **Entrée :** buy at open `i` après setup long. **Sortie :** Time(`Time_Index`) + Stop ATR(20)×6. Pas de target.

**Écarts assumés vs site** (idem S001-S007) : univers FTMO 30 instruments, métriques recalculées, R-multiples 0,5 %, coûts FTMO.

---

## 2-4. Univers, données, coûts, look-ahead (partagés, inchangés)
Identiques à S001-S007. Aroon vectorisé (sliding-window), entrée open `i` (signal `i−1`), `risk0=ATR[i−1]×6`, sans look-ahead.

## 5. Archétype d'entrée
> **🔑 Entrée MARKET-ON-OPEN** (signal new-high à `i−1`). Pas de stop intrabar → pas d'artefact de fill. Mapping fills : `'stop'`=open[s+1] natif, `'next_open'`=open[s+2] (Gate 1), `'close'`=close[s+1]. Sim **`simulate_aroon`** (entrée open, Time/ATR), `R=ATR×6`. Réutilise `ftmo_lab` v2-gates (coûts, `trade_metrics`, 4 gates).

## 6. Paramètres
`Aroon_Index` balayé {10,25,50,100,200} (réf. 25) × `Time_Index` {1,10,20,40} (réf. 20) = **20 cellules** (DSR). `Min_Aroon=100` fixe, `ATR` 20/6, `RISK_FRAC` 0,5 %.

---

## 7. Résultats
**Réf. (AI=25, Time=20) :** 4 844 trades · win 49,8 % · expR +0,0049 · PF 1,020 · Sharpe 0,10 · MaxDD −21,9 % · 16/30 positifs.
**Par instrument :** ETHUSD (+0,257), USDCHF (+0,166), BTCUSD (+0,146), GBPUSD (+0,070), US500 (+0,047) ; bas : USDCAD, NZDUSD, AUDUSD (−0,153), EURGBP (−0,157). Crypto/quelques FX/indices portent, FX majoritairement négatif.
**Sensibilité (`results/s008_sensitivity.png`) :** 80 % positif ; **Time=1 négatif** (le burst new-high ne tient pas 1 jour net de coûts), positif surtout en **AI lent + hold long** (AI200/T40 +0,068). Tous Sharpe ≤ 0,59 → DSR.

---

## 8. GATES CONSTITUTIONNELS — `results/s008_gates.csv`

| # | Gate | Résultat (AI=25, T=20) | Verdict |
|---|---|---|---|
| 1 | **Délai+1 (L26)** | natif open[s+1] Sharpe **+0,10** → open[s+2] **−0,07** | ❌ **FAIL** — micro-edge non robuste à la latence |
| 2 | **Two-sided (L25)** | long **+0,0601** (n=2755) / short **−0,0680** (n=2089) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=20)** | best Sharpe **0,591** ≪ E[max] 1,871 ; z −91 | ❌ **FAIL** — bruit |
| 4 | **OOS** | train +0,0058 → test +0,0040 | ✅ PASS |

Chance donnée au favorable (AI=200, T=40) : expR +0,068 mais two-sided **long +0,168 / short −0,130** (Gate 2) + DSR → **DISCARD** aussi.

**Lecture.** Particularité vs les autres trend-followers : ici l'edge de base est **positif mais si mince** que le **Gate 1** le tue (le breakout new-high a un effet de continuation d'**un jour** qui ne survit pas à un retard d'exécution d'une barre). Plus Gate 2 (beta long) + Gate 3 (bruit). Verdict **DISCARD (3/4)**.

---

## 9. Limites & checklist
- Grille réduite à 20 cellules (DSR N=20, E[max]=1,87) pour le runtime ; structure inchangée.
- Cluster trend-following (S003-S008) : même mort dominante Gate 2 ; voir `REPORT_S006` pour la piste long-only vol-targetée.
- Frontière de bougie, couverture 30/40, Aroon « most-recent » : idem S001/S007 §9.

## 10. Reproduction
```bash
cd oxfordstrat_109/code && python strat_s008_aroon_newhigh.py
```
Env : Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0. Sorties : `results/s008_*`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s008_aroon_newhigh.py`
Moteur `ftmo_lab.py` partagé (cf. `REPORT_S001` Annexe A). La machinerie Aroon (`aroon_updown`, `simulate_aroon`) est identique à S007 (cf. `REPORT_S007` Annexe) avec **`Min_Aroon=100` fixe** et **balayage `Aroon_Index × Time_Index`**. Source faisant foi : `code/strat_s008_aroon_newhigh.py`.
