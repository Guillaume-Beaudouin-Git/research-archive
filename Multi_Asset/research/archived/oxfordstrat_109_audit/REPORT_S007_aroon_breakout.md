# Rapport stratégie 7/109 — Aroon Indicator Breakout (Test : Setup)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/aroon-indicator-breakout-1/ (rating site : **C**).
**Date :** 2026-06-05 · **Registre :** entrée **#7** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Oscillateur **Aroon** (Chande) trend-following ; entrée market-on-open ; sorties Time(20) + ATR |
| Univers | 30/40 instruments FTMO |
| Point défaut (Aroon_Index=25, Min_Aroon=70) | **expR −0,0071 · PF 0,972 · Sharpe −0,16 · win 48,7 % · 5 764 trades** → **edge NÉGATIF** |
| **Gate 1 — Délai+1** | open[s+1]→open[s+2] : edge ~inchangé (≈0) → ✅ PASS (pas d'artefact) |
| **Gate 2 — Two-sided** | long **+0,0513** / short **−0,0845** → ❌ **FAIL** (beta long) |
| **Gate 3 — DSR (N=42)** | meilleur Sharpe **0,739** ≪ E[max] 2,157 ; z −101 → ❌ **FAIL** |
| **Gate 4 — OOS** | train −0,0008 → test −0,0126 → ❌ **FAIL** (décay) |
| **VERDICT** | ❌ **DISCARD** — *pas d'edge au défaut ; ailleurs = beta long déguisé + bruit* |

**Lecture.** Quatrième trend-follower d'affilée (après S003-S004-S005), **même mort** : archétype **entrée-sur-open** → **Gate 1 OK** (pas d'artefact), mais l'edge est **entièrement long** (shorts −0,085) = **beta de tendance** sur un univers haussier (crypto/métaux/énergie portent, indices/FX perdent). De plus, **au lookback par défaut de l'oscillateur (Aroon_Index=25), il n'y a pas d'edge** (toute la ligne est plate, ±0,01) ; seul un **Aroon_Index très lent (150-200)** devient positif — c'est-à-dire quand l'« oscillateur » se transforme en **filtre de tendance lent**, lui-même long-biaisé et **indistinguable du bruit** (DSR z −101).

---

## 1. Spécification originale (reproduite fidèlement)

**Développeur :** Tushar Chande (Aroon). **Rating site : C.** **Concept :** oscillateur de tendance.

- `AroonUp = 100·(Aroon_Index − périodes_depuis_plus_haut) / Aroon_Index` sur `Aroon_Index+1` barres (100 = plus-haut aujourd'hui, 0 = il y a `Aroon_Index` barres). `AroonDown` symétrique sur les plus-bas.
- **Setup :** Long si `AroonUp[i−1] > AroonDown[i−1]` ET `AroonUp[i−1] ≥ Min_Aroon` ; Short symétrique.
- **Entrée :** **« A buy at the open after a bullish Setup »** ⇒ market-on-open à `i` (signal sur `i−1`).
- **Sortie :** **Time Exit** (`Time_Index = 20`, fixe) + **Stop ATR** (`ATR(20)×6`). Pas de target.
- **Sensibilité :** `Aroon_Index [10,200] (défaut 25) × Min_Aroon [30,100] %`.

**Écarts assumés vs site** (idem S001-S006) : univers FTMO 30 instruments, métriques recalculées, R-multiples 0,5 %, coûts FTMO.

---

## 2-4. Univers, données, coûts, look-ahead (partagés, inchangés)
**Identiques à S001-S006.** Aroon calculé sur barres `≤ i−1`, entrée open `i` ; `risk0=ATR[i−1]×6`. Sans look-ahead. AroonUp/Down vectorisés (sliding-window argmax/argmin) et cachés par `(instrument, Aroon_Index)`.

---

## 5. Moteur de backtest et **ARCHÉTYPE D'ENTRÉE**

> **🔑 Archétype = entrée MARKET-ON-OPEN (signal Aroon confirmé à `i−1`).** Comme S003/S007, pas de stop intrabar → pas d'artefact de fill → Gate 1 a sa chance. **Mapping des fills :** `'stop'`=open[s+1] natif, `'next_open'`=open[s+2] (Gate 1 délai+1), `'close'`=close[s+1].

Sim **`simulate_aroon`** dans `strat_s007` (entrée open, sorties Time(20)/ATR, une position à la fois, ré-entrée après sortie pour la participation au trend). **Réutilisés à l'identique de `ftmo_lab` v2-gates :** coûts, `trade_metrics`, **4 gates**. `R = ATR×6`.

---

## 6. Paramètres
| Paramètre | Valeur(s) |
|---|---|
| `Aroon_Index` | balayé {10,25,50,75,100,150,200} ; **réf. 25 (défaut site)** |
| `Min_Aroon` | balayé {30,50,70,80,90,100} ; **réf. 70 (seuil « trend fort » canonique)** |
| `Time_Index` | **20 (fixe, spec)** · `ATR` 20/6 · `RISK_FRAC` 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

Point de référence = défauts canoniques (Aroon_Index=25 du site ; Min_Aroon=70 standard). *Transparence :* la ligne `Aroon_Index=25` est **plate** (±0,01) quel que soit Min_Aroon ; le positif n'apparaît qu'à `Aroon_Index≥150` (cf. §7.3, §8.2).

---

## 7. Résultats

### 7.1 Point défaut (Aroon_Index=25, Min_Aroon=70)
**5 764 trades · win 48,7 % · expR −0,0071 R · PF 0,972 · Sharpe −0,16 · MaxDD −34,5 %.** 14/30 positifs. two-sided long +0,051 / short −0,085.

### 7.2 Par instrument (`results/s007_per_instrument.csv`)
**Gagnants :** ETHUSD (+0,188), USDCHF (+0,174), BTCUSD (+0,147), XPTUSD (+0,090), UKOIL (+0,085). **Perdants :** UK100 (−0,090), EU50 (−0,093), EURUSD (−0,097), EURGBP (−0,116), AUDUSD (−0,135). → Crypto/métaux/énergie portent ; indices/FX perdent (signature trend-following, biais long).

### 7.3 Sensibilité Aroon_Index × Min_Aroon (`results/s007_sensitivity.png`)
**88 %** positif, mais **gradient vertical** : `Aroon_Index` court (10-25, dont le **défaut**) **plat/négatif** ; `Aroon_Index` lent (150-200) **positif** (jusqu'à +0,046). Le `Min_Aroon` n'a pas d'effet robuste. ⇒ **l'oscillateur ne « marche » qu'en version très lente** (= filtre de tendance), pas dans sa plage nominale. Tous les Sharpe ≤ 0,74 → cf. DSR.

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

`results/s007_gates.csv`. Point défaut (AI=25, MA=70).

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | **Délai+1 (L26)** | open[s+1] Sharpe −0,16 → open[s+2] +0,02 (edge ≈ 0 des deux côtés) | ✅ PASS (pas d'artefact) |
| 2 | **Two-sided (L25)** | long expR **+0,0513** (n=3285) / short **−0,0845** (n=2479) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=42)** | meilleur Sharpe **0,739** ≪ E[max] 2,157 ; z **−101** | ❌ **FAIL** — bruit |
| 4 | **OOS** | train −0,0008 (Sh −0,02) → test **−0,0126** (Sh −0,34) | ❌ **FAIL** — décay |

**Edge au défaut : négatif ⇒ condition nécessaire échoue → DISCARD.** Chance donnée au favorable (AI=200, MA=100) : expR +0,046 mais two-sided **long +0,0998 / short −0,076** (Gate 2) + DSR (best Sharpe 0,74) → **DISCARD** aussi.

### 8.1 Lecture
- **Gate 1 — PASS** (archétype open, pas d'artefact ; mais edge ≈ 0).
- **Gate 2 — FAIL (le juge).** Longs porteurs, shorts perdants partout → beta de tendance long.
- **Gate 3 — FAIL.** Meilleur Sharpe 0,74 ≪ 2,16 → bruit de multiplicité.
- **Gate 4 — FAIL.** Décroissance OOS (test négatif).

### 8.2 Verdict final
DISCARD. Tags : **pas d'edge (défaut) · beta long déguisé · bruit (DSR) · décay OOS**.

---

## 9. Limites & checklist
- Aroon « last occurrence » du plus-haut/plus-bas (most-recent), vectorisé ; tester « first occurrence » (impact marginal).
- `Time_Index=20` fixe (spec) — non balayé.
- Cluster trend-following (S003-S007) : même mort Gate 2 ; voir `REPORT_S006` pour la piste long-only vol-targetée.
- Frontière de bougie, couverture 30/40 : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s007_aroon_breakout.py
```
Sorties : console (réf + grille + 4 gates + verdict + cell favorable), `results/s007_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s007_sensitivity.png`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s007_aroon_breakout.py`
Moteur `ftmo_lab.py` partagé (cf. `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`). Source faisant foi : `code/strat_s007_aroon_breakout.py` (listing intégral ci-dessous, bloc heatmap allégé).

```python
"""
Strategy 7/109 — Aroon Indicator Breakout (Setup). Source rating C. Tushar Chande.
ARCHETYPE: setup on Aroon[i-1] -> entry MARKET-ON-OPEN at i. Exits = Time(20) + ATR (no target).
Fill mapping: 'stop'=open[s+1] native, 'next_open'=open[s+2] (Gate1), 'close'=close[s+1].
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
TIME_INDEX, ATR_LEN, ATR_STOP = 20, 20, 6.0
AI_REP, MA_REP = 25, 70

def aroon_updown(df, aroon_index):
    W = aroon_index + 1; hv, lv = df['high'].values, df['low'].values; n = len(hv)
    up = np.full(n, np.nan); dn = np.full(n, np.nan)
    if n >= W:
        swh = np.lib.stride_tricks.sliding_window_view(hv, W)
        swl = np.lib.stride_tricks.sliding_window_view(lv, W)
        ps_high = swh[:, ::-1].argmax(axis=1).astype(float)   # periods since most-recent highest high
        ps_low = swl[:, ::-1].argmin(axis=1).astype(float)
        up[W-1:] = 100.0 * (aroon_index - ps_high) / aroon_index
        dn[W-1:] = 100.0 * (aroon_index - ps_low) / aroon_index
    return up, dn

def simulate_aroon(df, dir_sig, *, time_index=TIME_INDEX, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                   cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig; n = len(df); idx = df.index
    trades = []; s = 1
    while s < n - 1:
        d = ds[s]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[s]) or A[s] <= 0:
            s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = o[eb] if eb <= n-1 else np.nan
        elif fill == 'close':     eb = s + 1; entry = c[eb] if eb <= n-1 else np.nan
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry): s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; last = min(eb + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last:                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None: exit_j = last; exit_p, reason = c[last], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_AR = {}
def _updown(t, df, ai):
    if (t, ai) not in _AR: _AR[(t, ai)] = aroon_updown(df, ai)
    return _AR[(t, ai)]
def run_point(aroon_index, min_aroon, fill='stop'):
    frames = []
    for t, df in uni.items():
        up, dn = _updown(t, df, aroon_index)
        ds = np.where((up > dn) & (up >= min_aroon), 1, np.where((dn > up) & (dn >= min_aroon), -1, 0))
        tr = simulate_aroon(df, ds, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    AIs = [10,25,50,75,100,150,200]; MAs = [30,50,70,80,90,100]
    grid = np.full((len(AIs), len(MAs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ai in enumerate(AIs):
        for b, ma in enumerate(MAs):
            m = lab.trade_metrics(run_point(ai, ma)); grid[a, b] = m['expR']; sg[a, b] = m['sharpe']
    res = lab.run_gates(lambda fill='stop': run_point(AI_REP, MA_REP, fill=fill), sg, split='2015-12-31')
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s007_gates.csv", index=False)
    print(">>> VERDICT:", res['verdict'], "| gates FAIL:", res['n_fail'], "/4 |", res['reason'])
    # (per-instrument CSV + heatmap present in code/.)
```
*Listing fonctionnellement identique à `code/strat_s007_aroon_breakout.py`. Source faisant foi : le `.py`.*
