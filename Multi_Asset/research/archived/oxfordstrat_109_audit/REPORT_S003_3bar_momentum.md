# Rapport stratégie 3/109 — 3-Bar Momentum Pattern + Trend Filter (Test : Filter & Exit)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/3-bar-momentum-pattern/ (rating site : **C**).
**Date :** 2026-06-04 · **Registre :** entrée **#3** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Momentum 3 barres (accélération) + filtre de tendance Donchian ; **entrée market-on-open** ; long+short |
| Univers | 30/40 instruments FTMO (idem S001/S002) |
| Point de référence | Filter_Look_Back=40, Time=35 (région recommandée par la fiche) → **expR +0,0433 · PF 1,17 · Sharpe 0,26 · win 34 % · 597 trades** |
| **Gate 1 — Délai+1 (latence)** | natif open[i+1] Sharpe **+0,26** → délai open[i+2] **+0,26** ; close[i+1] +0,22 → ✅ **PASS** |
| **Gate 2 — Two-sided** | long expR **+0,142** / short **−0,068** ; contrib long 174 % → ❌ **FAIL** |
| **Gate 3 — DSR (N=42)** | SR_obs **0,274** ≪ E[max bruit] **2,157** ; z **−63,7** → ❌ **FAIL** |
| **Gate 4 — OOS** | train +0,0496 (Sh +0,29) → test **+0,0388** (Sh +0,26) → ✅ **PASS** |
| **Gates** | **2/4 PASS** |
| **VERDICT** | ❌ **DISCARD** — *beta long déguisé* + *grille = bruit (DSR)* |

**Lecture (résultat le plus riche jusqu'ici).** Contrairement à S001/S002 (mortes au Gate 1 par **artefact de fill intrabar**), S003 a un **archétype d'entrée différent** : le pattern est **confirmé au close** puis l'entrée est **à l'open de la barre suivante** — un prix exécutable, **sans artefact intrabar**. Conséquence : **S003 est la première stratégie à passer le Gate 1** (l'edge survit à la latence : open[i+1] → open[i+2] inchangé, +0,26). Le pipeline distingue donc correctement les archétypes. **Mais elle meurt ailleurs**, pour des raisons rigoureuses et économiquement parlantes : (2) l'edge est **entièrement long** (les shorts perdent −0,068 ; c'est du **beta de tendance** sur des actifs qui ont monté, pas un momentum symétrique), et (3) il est **statistiquement indistinguable du bruit** (meilleur Sharpe de grille 0,27 vs ~2,16 attendu sous H₀ ; **seulement 597 trades**, 2-33 par instrument). C'est un *vrai* edge d'exécution mais **trop faible, asymétrique et trop rare** pour être retenu.

---

## 1. Spécification originale (reproduite fidèlement)

**Concept :** momentum court terme (3 barres en accélération) filtré par la tendance. **Source :** Hill, J. R. (1977), *Stock & Commodity Market Trend Trading*. **Rating site : C.** La fiche conclut elle-même : *« (i) le filtre de tendance améliore ; (ii) un holding plus long est préféré ; (iii) le pattern s'est détérioré depuis 2007 ».*

**Variables auxiliaires :** `TrueHigh=max(High,Close₋₁)`, `TrueLow=min(Low,Close₋₁)`, `TrueRange=TrueHigh−TrueLow`.

**Setup long (au close de la barre i) — 6 conditions A→F :**
- A : `TR[i]>TR[i-1]>TR[i-2]` (range en expansion) ;
- B : 3 bougies haussières (`Close>Open` sur i,i-1,i-2) ;
- C : `Close[i]>Close[i-1]>Close[i-2]` ;
- D : closes en accélération `(C[i]−C[i-1])>(C[i-1]−C[i-2])` ;
- E : highs en accélération `(H[i]−H[i-1])>(H[i-1]−H[i-2])` ;
- F : lows croissants `L[i]>L[i-1]>L[i-2]`.
**Setup short :** miroir exact.

**Filtre (Donchian) :** `UpperChannel=max(High, Filter_Look_Back)`, `LowerChannel=min(Low, FLB)`. Long accepté seulement si `High[i] > UpperChannel[i-1]` ; short si `Low[i] < LowerChannel[i-1]`. `FLB=2` ⇒ tous les trades acceptés. **`Filter_Look_Back ∈ [2,100]`**.

**Entrée :** **« A buy at the open is placed after a bullish Setup »** ⇒ market-on-open à **i+1**.

**Sorties (pas de profit target) :** Time Exit (`Time_Index ∈ [1,50]`) ; **Pattern Exit** (long : sell stop au plus-bas des 3 barres ; short : buy stop au plus-haut) ; **Stop ATR** (`ATR(20)×6`).

**Sensibilité :** `Filter_Look_Back × Time_Index`.

**Écarts assumés vs site** (idem S001/S002) : univers FTMO 30 instruments (vs 42 futures US) ; métriques recalculées (fiche en images) ; R-multiples 0,5 % ; coûts FTMO. Raison : univers cible + comparabilité.

---

## 2. Univers, données et coûts (partagés, inchangés)
**Identiques à S001/S002** — voir `REPORT_S001 §2-§4`. 30 instruments, store `ohlc/` partagé, `ftmo_lab.round_turn_cost_bps`. Rien n'a changé → comparabilité directe.

---

## 3. Pré-traitement des signaux (sans look-ahead)
Le setup (barres i-2…i) et le filtre (canal jusqu'à i-1, comparé à High/Low[i]) sont **entièrement connus au close de i**. L'entrée est à l'**open de i+1** ; `risk0 = ATR(20)[i]×6` (ATR connu au close de i). **Aucune information future** n'entre dans la décision. Signaux mis en cache par `(instrument, Filter_Look_Back)`.

---

## 4. Modèle de coûts FTMO
Inchangé (`ftmo_lab.round_turn_cost_bps`) : spread M1 + commission specs + slippage, plancher par classe, méd. ~2,9 bps round-turn.

---

## 5. Moteur de backtest et **ARCHÉTYPE D'ENTRÉE** (point clé)

> **🔑 Archétype = entrée MARKET-ON-OPEN (confirmée au close).** Le pattern 3 barres est validé au close de i ; l'ordre est exécuté à l'**open de i+1**. Ce **n'est pas** un stop/limit intrabar (≠ ORB de S001/S002). Donc **pas d'artefact de fill intrabar possible** : le prix d'entrée (open de i+1) est réellement exécutable. C'est pourquoi cet archétype « méritait sa chance » au Gate 1 — et l'a saisie (Gate 1 PASS).

Archétype « momentum + filtre » incompatible avec `simulate_bracket` (entrée open, sorties pattern/ATR, pas de target) → sim minimale fidèle **`simulate_momentum`** dans `strat_s003` (autorisé). **Réutilisés à l'identique de `ftmo_lab` v2-gates** : `atr`, `round_turn_cost_bps`, `RISK_FRAC`, `trade_metrics`, **les 4 gates** (`run_gates`).

**Mapping des fills (le moteur générique nomme `'stop'/'next_open'/'close'`) — pour CET archétype :**

| token moteur | sens réel S003 | rôle |
|---|---|---|
| `'stop'` | entrée **native** à `open[i+1]` (prix du spec) | base / mesure |
| `'next_open'` | entrée **différée** à `open[i+2]` | **Gate 1 délai+1** (latence) |
| `'close'` | entrée à `close[i+1]` | fill réaliste secondaire (reporté) |

⇒ **Pour cet archétype, le Gate 1 n'est pas un test d'artefact intrabar (inexistant) mais un test de robustesse à la latence d'exécution** (open[i+1] vs open[i+2]). Il PASSE → l'edge ne dépend pas d'un timing d'entrée irréaliste.

**Sorties / R / hypothèses intrabar :** `R = ATR×6` (comparabilité) ; stop = le plus proche entre stop ATR et stop-pattern ; un seul stop composite ; pas de positions superposées. Setups long/short mutuellement exclusifs (pas de catégorie « both »).

---

## 6. Paramètres
| Paramètre | Valeur(s) |
|---|---|
| `Filter_Look_Back` (filtre) | balayé {2,10,20,40,60,80,100} ; **réf. 40** |
| `Time_Index` (exit) | balayé {1,5,10,20,35,50} ; **réf. 35** |
| `ATR_Length` / `ATR_Stop` | 20 / 6 · `RISK_FRAC` 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

Choix du point de référence : la fiche recommande **filtre activé + holding long** → FLB=40 / Time=35 (région recommandée, **pas** le max de grille que le DSR pénaliserait). *Transparence : au point central FLB=20/Time=20, l'edge est ~nul (Sharpe 0,02) et l'OOS flippe — la stratégie n'est « présentable » que dans la région longue-durée, ce que le DSR corrige ensuite.*

---

## 7. Résultats (mesure brute, entrée native open[i+1])

### 7.1 Point de référence (FLB=40, Time=35)
**597 trades · win 34,0 % · expR +0,0433 R · PF 1,170 · Sharpe 0,26 · CAGR +0,2 % · MaxDD −12,4 %.** 17/30 instruments positifs.

### 7.2 Par instrument (extraits — `results/s003_per_instrument.csv`)
**Positifs :** ETHUSD (expR 0,50, n=17), COCOA (0,47, n=11), XAUUSD (0,46, n=17), XAGUSD (0,43, n=14), USDCAD (0,38, n=10)… **Négatifs :** US100 (−0,13, n=33), AUDUSD (−0,13), GBPUSD (−0,29), EURGBP (−0,52).
⚠️ **Échantillons minuscules** (2-33 trades/instrument, 597 au total) : le filtre+pattern est extrêmement sélectif → expectancies individuelles peu significatives (cœur de l'échec DSR).

### 7.3 Sensibilité Filter_Look_Back × Time (`results/s003_sensitivity.png`)
**83 %** des cellules positives ; la colonne **5 j est majoritairement négative** (le holding court ne marche pas → cohérent avec « holding long préféré ») ; l'expectancy monte avec FLB élevé + Time long (max FLB80/T50 ≈ +0,061). Mais **toutes les cellules ont un Sharpe ≤ 0,27** → cf. Gate DSR.

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

`ftmo_lab.run_gates(make_run(40,35), sharpe_grid, split='2015-12-31')`. Brut : `results/s003_gates.csv`.

| # | Gate (loi) | Résultat S003 | Verdict |
|---|---|---|---|
| 1 | **Délai+1 / latence (L26)** | natif `open[i+1]` Sharpe **+0,26** (expR +0,0433) → `open[i+2]` Sharpe **+0,26** (expR +0,0419) ; `close[i+1]` Sharpe +0,22 (expR +0,0366) | ✅ **PASS** |
| 2 | **Two-sided (L25)** | long expR **+0,1421** (n=316) / short expR **−0,0678** (n=281) ; contrib long 174 % | ❌ **FAIL** — beta long déguisé |
| 3 | **DSR (N=42)** | SR sélectionné **0,274** ≪ E[max bruit] **2,157** ; DSR_z **−63,7** | ❌ **FAIL** — grille = bruit |
| 4 | **OOS (≤2015 / ≥2016)** | train +0,0496 (Sh +0,29, n=250) → test **+0,0388** (Sh +0,26, n=347) — pas de flip | ✅ **PASS** |

**Gates FAIL : 2/4** (bloquant).

### 8.1 Lecture
- **Gate 1 — PASS (le résultat marquant).** L'edge survit à un délai d'exécution d'une barre (open[i+1]→open[i+2] : +0,26 → +0,26) **et** au fill close (+0,22). **Aucun artefact d'exécution intrabar** — l'archétype entrée-sur-open tient sa promesse. *Première stratégie des 3 à franchir ce gate ; cela valide que le Gate 1 discrimine bien stop-intrabar vs market-on-open.*
- **Gate 2 — FAIL.** Les **shorts perdent** systématiquement (−0,068) tandis que les longs gagnent (+0,142, contrib 174 %). Le « momentum » n'est pas symétrique : c'est un **filtre de tendance long sur un univers qui a monté** (indices, métaux, ETH). Mécanisme = **beta de tendance déguisé**, à re-tester contre un buy-and-hold timé — pas un edge momentum intrinsèque.
- **Gate 3 — FAIL (le plus dur).** Le meilleur Sharpe de la grille (0,27) est **très en-dessous** de l'espérance du max de 42 tirages de bruit (2,16). Avec **597 trades** (2-33 par instrument), la distribution est dominée par la variance d'échantillonnage. La « performance » est **indistinguable de zéro** après correction de multiplicité.
- **Gate 4 — PASS (à ce point).** L'edge tient OOS au point FLB40/T35 (test Sharpe +0,26). *Nuance de fragilité :* au point central FLB20/T20, l'OOS **flippe** (cohérent avec « détérioré depuis 2007 » de la fiche) — la robustesse OOS dépend du réglage, ce qui n'est pas rassurant.

### 8.2 Verdict final (règle stricte)
`edge_net>0` ✅, **Gate 1 ✅, Gate 4 ✅**, mais **Gate 2 ❌ et Gate 3 ❌** ⇒ **❌ DISCARD**.
Tags : **beta long déguisé · grille = bruit (DSR)**.
**Mort différente de S001/S002 :** pas un artefact de fill (Gate 1 OK) mais un **edge réel trop faible, asymétrique (long-beta) et statistiquement nul**. C'est précisément le cas intéressant : l'archétype a eu sa chance, le Gate 1 ne l'a pas tué — la rigueur statistique/économique l'a fait.

### 8.3 Récupérable ?
Marginalement intéressant **uniquement en version long-only** sur actifs en tendance (ce qui revient à un overlay de trend-following long, à comparer à un buy-and-hold timé via Gate 2) — mais le **Gate 3 (bruit)** reste rédhibitoire vu la rareté des trades. **Archivé DISCARD**, avec la note que le côté long isolé pourrait être ré-examiné comme *filtre d'entrée* d'un sleeve trend-following (pas comme stratégie autonome).

---

## 9. Limites & checklist d'audit complémentaire
- **Gate 1 testé sur 2 fills alternatifs** (open[i+2] + close[i+1]) : robuste (PASS).
- **Rareté des trades** (597) : significativité faible → le DSR est ici le gate décisif. Un bootstrap par blocs confirmerait un IC traversant zéro.
- **Sensibilité du point de référence** : FLB20/T20 ~plat et flippe OOS ; FLB40/T35 tient. Documenter cette dépendance = signal de fragilité.
- **Pattern Exit « ±1 tick »** approximé au niveau exact (tick négligé en daily CFD).
- Frontière de bougie, couverture 30/40, `≤`/`<` : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s003_3bar_momentum.py
```
Sorties : console (réf + grille + 4 gates + verdict + fill close), `results/s003_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s003_sensitivity.png`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s003_3bar_momentum.py`
Le moteur `ftmo_lab.py` (coûts + `trade_metrics` + 4 gates) est partagé (listé dans `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`). Source faisant foi : `code/strat_s003_3bar_momentum.py` (listing intégral ci-dessous, bloc heatmap allégé).

```python
"""
Strategy 3/109 — 3-Bar Momentum Pattern + Trend Filter (Filter & Exit). Source rating C.
ARCHETYPE: pattern confirmed at close[i] -> entry MARKET-ON-OPEN at open[i+1] (no intrabar fill).
Fill mapping: 'stop'=open[i+1] native, 'next_open'=open[i+2] (Gate1 delay+1), 'close'=close[i+1].
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
ATR_LEN, ATR_STOP = 20, 6.0
FLB_REP, TM_REP = 40, 35                       # site-recommended region (filter on, longer hold)

def momentum_signals(df, filter_lb):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    th = pd.concat([h, c.shift(1)], axis=1).max(axis=1)
    tl = pd.concat([l, c.shift(1)], axis=1).min(axis=1)
    tr = th - tl
    tr_up = (tr > tr.shift(1)) & (tr.shift(1) > tr.shift(2))
    Lb = (c > o) & (c.shift(1) > o.shift(1)) & (c.shift(2) > o.shift(2))
    Lc = (c > c.shift(1)) & (c.shift(1) > c.shift(2))
    Ld = (c - c.shift(1)) > (c.shift(1) - c.shift(2))
    Le = (h - h.shift(1)) > (h.shift(1) - h.shift(2))
    Lf = (l > l.shift(1)) & (l.shift(1) > l.shift(2))
    long_setup = tr_up & Lb & Lc & Ld & Le & Lf
    Sb = (c < o) & (c.shift(1) < o.shift(1)) & (c.shift(2) < o.shift(2))
    Sc = (c < c.shift(1)) & (c.shift(1) < c.shift(2))
    Sd = (c.shift(1) - c) > (c.shift(2) - c.shift(1))
    Se = (l.shift(1) - l) > (l.shift(2) - l.shift(1))
    Sf = (h < h.shift(1)) & (h.shift(1) < h.shift(2))
    short_setup = tr_up & Sb & Sc & Sd & Se & Sf
    if filter_lb <= 2:
        long_ok = short_ok = pd.Series(True, index=df.index)
    else:
        upper = h.rolling(filter_lb).max().shift(1); lower = l.rolling(filter_lb).min().shift(1)
        long_ok = h > upper; short_ok = l < lower
    dir_sig = np.where(long_setup & long_ok, 1, np.where(short_setup & short_ok, -1, 0))
    return pd.Series(dir_sig, index=df.index), l.rolling(3).min(), h.rolling(3).max()

def simulate_momentum(df, dir_sig, plow, phigh, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig.values; pl = plow.values; ph = phigh.values
    n = len(df); idx = df.index; trades = []; i = 2
    while i < n - 1:
        d = ds[i]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        if fill == 'stop':        eb = i + 1; entry = o[eb] if i+1 <= n-1 else np.nan
        elif fill == 'close':     eb = i + 1; entry = c[eb] if i+1 <= n-1 else np.nan
        elif fill == 'next_open': eb = i + 2; entry = o[eb] if i+2 <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        atr_lvl = entry - d * risk0; pat_lvl = pl[i] if d == 1 else ph[i]
        stop_lvl = max(atr_lvl, pat_lvl) if d == 1 else min(atr_lvl, pat_lvl)
        last = min(eb + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last:                    exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None: exit_j = last; exit_p, reason = c[last], 'eod'
        trades.append(dict(entry=idx[i], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d*(exit_p-entry)/risk0 - cost_R, hold=exit_j - eb))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, flb):
    if (t, flb) not in _SIG: _SIG[(t, flb)] = momentum_signals(df, flb)
    return _SIG[(t, flb)]
def run_point(filter_lb, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds, pl, ph = _signals(t, df, filter_lb)
        tr = simulate_momentum(df, ds, pl, ph, time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    FLBs = [2,10,20,40,60,80,100]; TMs = [1,5,10,20,35,50]
    grid = np.full((len(FLBs), len(TMs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, flb in enumerate(FLBs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(flb, tm)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    res = lab.run_gates(lambda fill='stop': run_point(FLB_REP, TM_REP, fill=fill), sharpe_grid, split='2015-12-31')
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s003_gates.csv", index=False)
    print(">>> VERDICT:", res['verdict'], "| gates FAIL:", res['n_fail'], "/4 |", res['reason'])
    # (per-instrument CSV + heatmap omitted here for brevity; present in code/.)
```
*Listing fonctionnellement identique à `code/strat_s003_3bar_momentum.py` (affichage console/heatmap allégé). Source faisant foi : le `.py`.*
