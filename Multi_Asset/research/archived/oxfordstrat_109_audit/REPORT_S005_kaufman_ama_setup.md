# Rapport stratégie 5/109 — Kaufman Adaptive Moving Average (KAMA) (Test : Setup seul)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/adaptive-moving-average-2/ (rating site : **C**).
**Date :** 2026-06-05 · **Registre :** entrée **#5** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | KAMA **setup seul** (filtre quasi-désactivé, `Filter_Index=0,01`) ; entrée market-on-close ; always-in reversal |
| **Angle distinct vs S004** | balaye **ER_Length × FastMA_Length** (réactivité du bout rapide), filtre fixé ≈ off — S004 balayait `Filter_Index` |
| Point canonique (ER=10, FastMA=2) | **expR −0,0065 · PF 0,947 · Sharpe −0,40 · 16 146 trades · MaxDD −55,7 %** → **edge NÉGATIF (pire que S004)** |
| Meilleur cell favorable (ER=60, FastMA=20) | expR +0,0586 · Sharpe 0,47 — mais two-sided **long +0,183 / short −0,066** |
| **Gate 1 — Délai+1** | close[i]→open[i+1] : edge ~inchangé → ✅ PASS (pas d'artefact) |
| **Gate 2 — Two-sided** | long porte tout, shorts perdent partout → ❌ **FAIL** (beta long) |
| **Gate 3 — DSR (N=42)** | meilleur Sharpe **0,507** ≪ E[max] 2,157 ; z −158 → ❌ **FAIL** |
| **Gate 4 — OOS** | négatif des deux côtés au canonique → ❌ FAIL |
| **VERDICT** | ❌ **DISCARD** |

**Découverte distincte (que S004 ne montrait pas).** Le balayage de **FastMA_Length** révèle que **l'adaptativité de la KAMA est contre-productive** sur cet univers : à `FastMA=2` (bout rapide réactif, réglage de Kaufman) la stratégie **whipsaw** (16 146 trades, Sharpe −0,40) et **perd** ; elle ne devient positive qu'en **ralentissant le bout rapide** (`FastMA=20-28` → `Fast≈Slow`), c.-à-d. **quand on neutralise l'aspect adaptatif** et que l'AMA dégénère en simple EMA lente. Autrement dit : **le mécanisme « adaptatif » a une valeur ajoutée négative ici** ; ce qui « marche » n'est qu'un filtre de tendance lent — et, comme S004, c'est du **beta long déguisé** (Gate 2) noyé dans le **bruit** (Gate 3).

---

## 1. Spécification originale (reproduite fidèlement)

**Même KAMA que S004** (Kaufman 1995, rating C) : `ER`, `c[i]=(ER·(Fast−Slow)+Slow)²`, `AMA[i]=AMA[i−1]+c[i]·(Close[i]−AMA[i−1])`. Setup = AMA tourne (pivots MinAMA/MaxAMA). Entrée **market-on-close** quand `(AMA[i]−MinAMA) > Filter[i]`. Sortie = **stop ATR seul**.

**Différences spec vs S004 (le « Test: Setup ») :**

| | S004 (Setup & Filter) | **S005 (Setup)** |
|---|---|---|
| `Filter_Index` | balayé [0,1] | **fixé à 0,01** (≈ off) |
| `FastMA_Length` | fixé à 2 | **balayé [2,28]** |
| Axes de sensibilité | ER × Filter_Index | **ER × FastMA_Length** |
| `SlowMA_Length` | 30 | 30 |

`Fast = 2/(FastMA_Length+1)` : FastMA=2 → 0,667 (très réactif) ; FastMA=28 → 0,069 ≈ `Slow=2/31=0,065` (le bout rapide rejoint le lent).

**Écarts assumés vs site** (idem S001-S004) : univers FTMO 30 instruments, métriques recalculées, R-multiples 0,5 %, coûts FTMO.

---

## 2-4. Univers, données, coûts, look-ahead (partagés, inchangés)
**Identiques à S001-S004.** 30 instruments, store `ohlc/` partagé, `ftmo_lab.round_turn_cost_bps`. Signaux KAMA sur close (entrée native close[i]), `risk0=ATR[i]×6`, sans look-ahead. Signaux cachés par `(instrument, ER_Length, FastMA_Length)`.

---

## 5. Moteur de backtest et **ARCHÉTYPE D'ENTRÉE**

> **🔑 Archétype = IDENTIQUE à S004 : entrée MARKET-ON-CLOSE, système ALWAYS-IN REVERSAL + disaster-stop ATR.** Pas de stop intrabar → pas d'artefact de fill → Gate 1 a sa chance. Sortie documentée = stop ATR seul ; lecture cohérente = renversement au signal opposé (cf. `REPORT_S004 §5`).

Sim **`simulate_ama`** dans `strat_s005` (mécanique identique à S004 ; `kama`/`ama_signals` acceptent `FastMA_Length` en variable, `Filter_Index=0,01` fixe). **Réutilisés à l'identique de `ftmo_lab` v2-gates :** coûts, `trade_metrics`, **4 gates**. **Mapping des fills** identique à S004 (`'stop'`=close[i] natif, `'next_open'`=open[i+1], `'close'`=close[i+1]).

---

## 6. Paramètres
| Paramètre | Valeur(s) |
|---|---|
| `ER_Length` | balayé {2,10,20,40,60,80,100} ; **réf. 10** |
| `FastMA_Length` | balayé {2,4,8,14,20,28} ; **réf. 2** (canonique) |
| `Filter_Index` | **0,01 (fixe, spec)** · `SlowMA` 30 · `N` 20 · `ATR` 20/6 · `RISK_FRAC` 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

Point de référence = canonique Kaufman (ER=10, FastMA=2). *Transparence :* edge **négatif** ici ; la région positive est `FastMA≥14` (cf. §7.3, §8.2).

---

## 7. Résultats

### 7.1 Point canonique (ER=10, FastMA=2, Filter=0,01)
**16 146 trades · win 26,0 % · expR −0,0065 R · PF 0,947 · Sharpe −0,40 · MaxDD −55,7 %.** 13/30 positifs. two-sided : long +0,019 / short −0,032.
**Pire que S004** (qui avait 8 002 trades, Sharpe −0,12) : **retirer le filtre double le whipsaw** et aggrave le drawdown.

### 7.2 Par instrument (canonique — `results/s005_per_instrument.csv`)
**Positifs :** ETHUSD (+0,054), USDCHF (+0,048), BTCUSD (+0,036), XPDUSD (+0,027), USDJPY (+0,027). **Négatifs :** US100 (−0,027), USDCAD (−0,030), US2000 (−0,031), EU50 (−0,043), EURGBP (−0,061). Indices en bas (whipsaw).

### 7.3 Sensibilité ER_Length × FastMA_Length — **le résultat clé** (`results/s005_sensitivity.png`)
**90 %** des cellules positives, mais **gradient horizontal frappant** :

| FastMA → | 2 | 4 | 8 | 14 | 20 | 28 |
|---|---|---|---|---|---|---|
| effet | négatif/plat | ~0 | + | ++ | **+++** | +++ |

À `FastMA=2` (réactif, canonique) : **négatif/plat** sur toute la colonne. À `FastMA=20-28` (bout rapide ralenti → `Fast≈Slow`) : **fortement positif** (jusqu'à +0,0586 à ER=60/FastMA=20). **L'`ER_Length` importe peu ; c'est le ralentissement du bout rapide qui crée le « positif ».** ⇒ **l'adaptativité (réactivité) détruit la performance ; la neutraliser la restaure** — un verdict sévère sur la valeur ajoutée de la KAMA. Mais tous les Sharpe ≤ 0,51 → cf. DSR.

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

### 8.1 Au point canonique (ER=10, FastMA=2) — `results/s005_gates.csv`
`edge_net = −0,0065 < 0` ⇒ condition nécessaire échoue → **DISCARD (pas d'edge après coûts)**. (Gate 3 DSR : best Sharpe 0,507 ≪ 2,157, z −158.)

### 8.2 Chance donnée à l'archétype — meilleur cell favorable (ER=60, FastMA=20)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 (latence) | edge survit close[i]→open[i+1] (région positive) | ✅ PASS |
| 2 | **Two-sided** | long expR **+0,1829** (n=1755) / short **−0,0660** (n=1752) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=42)** | meilleur Sharpe **0,507** ≪ E[max] 2,157 | ❌ **FAIL** — bruit |
| 4 | OOS | (positif au cell, mais grille dominée par le bruit) | — |

**Même au meilleur réglage : Gate 2 + Gate 3 FAIL → DISCARD.**

### 8.3 Lecture
- **Gate 1 — PASS.** Archétype entrée-sur-close → pas d'artefact d'exécution (cohérent S003/S004). *(Au canonique le Gate 1 « échoue » seulement parce que l'edge natif est déjà négatif ; le tag « artefact intrabar » du moteur ne s'applique pas.)*
- **Gate 2 — FAIL (le juge, comme S004).** Partout, **longs porteurs, shorts perdants** (favorable : long +0,183 / short −0,066). Beta de tendance long, pas d'edge adaptatif symétrique.
- **Gate 3 — FAIL.** Meilleur Sharpe de grille 0,51 ≪ 2,16 attendu sous H₀ → la région « positive » est du bruit après multiplicité.
- **Gate 4.** Négatif des deux côtés au canonique.

### 8.4 Verdict final
Au canonique : `edge<0` → DISCARD. Au favorable : `edge>0` mais **Gate 2 ❌ + Gate 3 ❌** → DISCARD. Tags : **pas d'edge (canonique) · beta long déguisé · bruit (DSR)**.

### 8.5 Apport vs S004 (pourquoi ce n'est pas un copier-coller)
S004 et S005 meurent du même Gate 2, mais S005 **ajoute une information** : en isolant `FastMA_Length`, on montre que **l'adaptativité de la KAMA est nuisible** (FastMA réactif = whipsaw/perte) et que le seul « positif » vient de la **dé-adaptification** (FastMA→Slow ⇒ EMA lente), elle-même du long-beta. **Conclusion de fond : sur cet univers, la composante « adaptative » de Kaufman n'apporte pas de valeur ajoutée — ni filtrée (S004) ni non filtrée (S005).**

---

## 9. Limites & checklist d'audit complémentaire
- Hypothèse de sortie (always-in reversal + ATR) explicitée §5 (idem S004).
- 16 146 trades au canonique : coûts massifs ; cost-stress aggraverait.
- Dépendance au réglage (FastMA) = signal de non-robustesse ; le « positif » n'est qu'une EMA lente long-biaisée.
- Frontière de bougie, couverture 30/40 : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s005_kaufman_ama_setup.py
```
Sorties : console (réf + grille + 4 gates + verdict + cell favorable), `results/s005_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s005_sensitivity.png`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s005_kaufman_ama_setup.py`
Moteur `ftmo_lab.py` partagé (cf. `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`). La machinerie KAMA (`kama`, `ama_signals`, `simulate_ama`) est identique à S004 avec `FastMA_Length` en variable et `Filter_Index=0,01` fixe — voir `REPORT_S004` Annexe pour le listing complet (seuls changent : `kama(close, er_len, fast_len)`, le balayage `ER × FastMA`, et `FILTER_INDEX=0.01`). Source faisant foi : `code/strat_s005_kaufman_ama_setup.py`.
