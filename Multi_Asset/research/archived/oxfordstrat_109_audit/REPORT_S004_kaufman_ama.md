# Rapport stratégie 4/109 — Kaufman Adaptive Moving Average (KAMA) (Test : Setup & Filter)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/adaptive-moving-average-1/ (rating site : **C**).
**Date :** 2026-06-05 · **Registre :** entrée **#4** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET les 4 gates PASS.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | KAMA (Kaufman) — filtre adaptatif ; **entrée market-on-close** ; système **always-in reversal** ; long+short |
| Univers | 30/40 instruments FTMO (idem S001-S003) |
| Point canonique (ER=10, Filter=0,2) | **expR −0,0042 · PF 0,978 · Sharpe −0,12 · win 32 % · 8 002 trades** → **edge NÉGATIF** |
| Région lente favorable (ER=100, Filter=0,3) | expR +0,0206 · Sharpe 0,27 (positif mais voir gates) |
| **Gate 1 — Délai+1 (latence)** | natif close[i] → open[i+1] : edge ~inchangé (canonique −0,12→−0,05 ; favorable +0,27→+0,26) → ✅ **PASS** (pas d'artefact) |
| **Gate 2 — Two-sided** | **long porte tout, shorts perdent** (favorable : long +0,123 / short **−0,082**) → ❌ **FAIL** |
| **Gate 3 — DSR (N=42)** | meilleur Sharpe de grille **0,343** ≪ E[max] 2,157 ; z −189 → ❌ **FAIL** |
| **Gate 4 — OOS** | flip au point favorable ER=60 (train +0,032→test −0,005) ; marginal à ER=100 | mixte |
| **VERDICT** | ❌ **DISCARD** — *pas d'edge au réglage canonique ; et en version lente c'est du **beta long déguisé** + bruit (DSR)* |

**Lecture.** L'archétype est **entrée-sur-close** (KAMA sur close, signal au close, exécution market-on-close) — comme S003, **pas d'artefact de fill intrabar** : le **Gate 1 PASSE** partout (l'edge ne dépend pas du timing d'exécution intrabar). Mais la KAMA est un **trend-follower always-in**, et le **Gate 2 le condamne exactement comme prévu** : sur un univers qui a monté (indices, métaux, crypto), **les longs portent tout (+0,10 à +0,14) et les shorts saignent systématiquement (−0,08 à −0,10)**. Ce n'est pas un edge « adaptatif » symétrique — c'est du **beta de tendance long déguisé**. Et au réglage **canonique de Kaufman (ER=10)**, il n'y a même **pas d'edge** (−0,0042, Sharpe −0,12) : seule une version **très lente** (ER≈100) devient positive, mais elle reste **indistinguable du bruit** (meilleur Sharpe de grille 0,34 vs ~2,16 attendu sous H₀).

---

## 1. Spécification originale (reproduite fidèlement)

**Développeur :** Perry Kaufman (KAMA), *Smarter Trading* (1995). **Rating site : C.** **Concept :** moyenne mobile à filtre de bruit adaptatif.

**KAMA :** `ER[i] = |Direction[i]/Volatility[i]|`, `Direction = Close[i]−Close[i−ER_Length]`, `Volatility = Σ|ΔClose|` sur ER_Length. `c[i] = (ER[i]·(Fast−Slow)+Slow)²`, `Fast = 2/(FastMA+1)` (FastMA=2), `Slow = 2/(SlowMA+1)` (SlowMA=30). `AMA[i] = AMA[i−1] + c[i]·(Close[i]−AMA[i−1])`.

**Setup :** Long si l'AMA tourne vers le haut (`AMA[i]>AMA[i−1] & AMA[i−1]<AMA[i−2]`, pivot `MinAMA=AMA[i−1]`). Short si elle tourne vers le bas (pivot `MaxAMA`).

**Filtre :** `Filter[i] = Filter_Index · StdDev(AMA[i]−AMA[i−1], N=20)`. **`Filter_Index ∈ [0,1]`**.

**Entrée :** **« A buy at the close »** quand `AMA[i]>AMA[i−1] & (AMA[i]−MinAMA) > Filter[i]` (symétrique short). Exécution **market-on-close**.

**Sortie (Table 1) :** **uniquement un stop ATR** (`ATR(20)×6`). **Sensibilité :** `ER_Length [2,100] × Filter_Index [0,1]`.

**Écarts assumés vs site** (idem S001-S003) : univers FTMO 30 instruments (vs 42 futures US) ; métriques recalculées ; R-multiples 0,5 % ; coûts FTMO. Raison : univers cible + comparabilité.

---

## 2. Univers, données et coûts (partagés, inchangés)
**Identiques à S001-S003** — voir `REPORT_S001 §2-§4`. 30 instruments, store `ohlc/` partagé, `ftmo_lab.round_turn_cost_bps`. Comparabilité directe.

---

## 3. Pré-traitement des signaux (sans look-ahead)
KAMA, pivots et filtre sont calculés sur `Close` jusqu'à `i`. `risk0 = ATR(20)[i]×6` (connu au close de i). L'entrée native est à `close[i]` (market-on-close). **Subtilité d'optimisme :** le signal *et* le fill utilisent le même `close[i]` — léger optimisme, **précisément ce que teste le Gate 1** (vs `open[i+1]`). Signaux cachés par `(instrument, ER_Length, Filter_Index)`.

---

## 4. Modèle de coûts FTMO
Inchangé (`ftmo_lab.round_turn_cost_bps`).

---

## 5. Moteur de backtest et **ARCHÉTYPE D'ENTRÉE**

> **🔑 Archétype = entrée MARKET-ON-CLOSE, système ALWAYS-IN REVERSAL.** Le signal (AMA tourne + dépasse le filtre) est connu au close de `i` ; l'ordre est exécuté au **close de `i`**. **Pas de stop/limit intrabar** (≠ S001/S002) → pas d'artefact de fill ⇒ le Gate 1 a une chance (et l'a saisie).
>
> **Lecture des sorties (assumée, documentée) :** la fiche ne liste qu'un **stop ATR**. Un stop fixe seul rendrait le système **dégénéré** (que des pertes, jamais de prise de profit). La lecture fidèle d'un système AMA trend-following est donc **always-in** : on tient la position jusqu'au **signal opposé** (l'AMA tourne dans l'autre sens → on se renverse) **ou** le stop ATR (disaster-stop), au premier des deux. C'est la seule interprétation cohérente ; elle est notée ici explicitement.

Sim minimale **`simulate_ama`** dans `strat_s004` (archétype incompatible avec les sims S001-S003). **Réutilisés à l'identique de `ftmo_lab` v2-gates :** `atr`, `round_turn_cost_bps`, `RISK_FRAC`, `trade_metrics`, **les 4 gates**.

**Mapping des fills (tokens moteur `'stop'/'next_open'/'close'`) — pour CET archétype :**

| token | sens réel S004 | rôle |
|---|---|---|
| `'stop'` | entrée **native** à `close[i]` (spec) | base / mesure |
| `'next_open'` | entrée à `open[i+1]` | **Gate 1** (réaliste, agir à la barre suivante) |
| `'close'` | entrée à `close[i+1]` | fill réaliste secondaire (reporté) |

⇒ **Gate 1 = test de robustesse au timing d'exécution (close[i] vs open[i+1]), pas un test d'artefact intrabar** (inexistant ici). `R = ATR×6` ; renversement au signal opposé ; stop ATR intrabar (fill au niveau du stop = conservateur pour un stop protecteur).

---

## 6. Paramètres
| Paramètre | Valeur(s) |
|---|---|
| `ER_Length` | balayé {2,10,20,40,60,80,100} ; **réf. canonique 10** |
| `Filter_Index` | balayé {0,0 ; 0,1 ; 0,2 ; 0,3 ; 0,5 ; 1,0} ; **réf. 0,2** |
| `FastMA/SlowMA/N` | 2 / 30 / 20 · `ATR_Length/Stop` 20 / 6 · `RISK_FRAC` 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

**Point de référence = canonique Kaufman (ER=10, Filter=0,2)** — pas de recommandation explicite dans la fiche, donc on prend le réglage **textbook** (non arbitraire). *Transparence :* ce point donne un edge **négatif** ; seule la région **lente (ER 60-100)** devient positive (cf. §7.3 et §8.3).

---

## 7. Résultats

### 7.1 Point canonique (ER=10, Filter=0,2)
**8 002 trades · win 32,0 % · expR −0,0042 R · PF 0,978 · Sharpe −0,12 · CAGR −0,9 % · MaxDD −36,2 %.** 11/30 positifs. **Edge négatif** : au réglage canonique, la KAMA whipsaw (8 000 trades) et perd net.

### 7.2 Par instrument (canonique — `results/s004_per_instrument.csv`)
**Positifs :** ETHUSD (+0,191, n=164), USDCHF (+0,104), GBPUSD (+0,091), BTCUSD (+0,078), XPTUSD (+0,051), XAGUSD (+0,029). **Négatifs :** US100 (−0,030), EURUSD (−0,032), EU50 (−0,048), US500 (−0,049), EURGBP (−0,113). Les **indices whipsaw** au réglage rapide.

### 7.3 Sensibilité ER_Length × Filter_Index (`results/s004_sensitivity.png`)
**67 %** des cellules positives, mais **structure nette** : ER rapide (2-20) **négatif** (whipsaw), ER lent (60-100) **positif** (jusqu'à +0,022 à ER100). C.-à-d. : la stratégie ne « marche » qu'en version **très lente** = un simple filtre de tendance lent. **Mais tous les Sharpe ≤ 0,34** → cf. Gate DSR.

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

### 8.1 Au point canonique (ER=10, Filter=0,2) — `results/s004_gates.csv`
`edge_net = −0,0042 < 0` ⇒ **la condition nécessaire échoue d'emblée** → **DISCARD (pas d'edge après coûts)**. (Gate 2 y montre déjà long +0,049 / short −0,058 = long-biais.)

### 8.2 Chance donnée à l'archétype — région lente favorable (ER=100, Filter=0,3)
Pour ne pas condamner sur un seul point, on teste les gates là où l'edge est **positif** (réglage lent, non-max de grille) :

| # | Gate | Résultat (ER=100, FI=0,3) | Verdict |
|---|---|---|---|
| 1 | **Délai+1 (latence)** | natif close[i] Sharpe **+0,27** → open[i+1] **+0,26** ; close[i+1] aussi positif | ✅ **PASS** |
| 2 | **Two-sided** | long expR **+0,1229** (n=2097) / short expR **−0,0818** (n=2093) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=42)** | meilleur SR de grille **0,343** ≪ E[max bruit] **2,157** ; z −189 | ❌ **FAIL** — bruit |
| 4 | **OOS (≤2015/≥2016)** | train +0,0383 → test **+0,0057** (tient marginalement ; **flippe à ER=60** : +0,032→−0,005) | ⚠️ fragile |

**Même au réglage le plus favorable : 2-3 gates FAIL → DISCARD.**

### 8.3 Lecture
- **Gate 1 — PASS (archétype confirmé).** L'edge (quand il existe) survit au passage close[i]→open[i+1] (+0,27→+0,26). **Aucun artefact d'exécution** — cohérent avec l'archétype entrée-sur-close. *(Le tag générique « artefact de fill intrabar » du moteur ne s'applique PAS ici : l'entrée n'est pas un stop intrabar ; au point canonique le Gate 1 « échoue » simplement parce que l'edge natif est déjà négatif.)*
- **Gate 2 — FAIL (le juge, comme prévu).** Sur toute la région favorable, **les longs gagnent (+0,10 à +0,14), les shorts perdent (−0,08 à −0,10)**. Une KAMA always-in shorte des actifs qui ont monté → elle saigne du côté court. **Le « filtre adaptatif » ne crée pas d'edge symétrique : c'est du beta de tendance long**, à comparer à un buy-and-hold timé.
- **Gate 3 — FAIL.** Le meilleur Sharpe de la grille (0,34) est très en-dessous de l'espérance du max de 42 tirages de bruit (2,16). La « performance » de la région lente est **statistiquement nulle** après multiplicité.
- **Gate 4 — fragile.** Tient marginalement à ER=100 (test +0,006) mais **flippe à ER=60** → robustesse OOS dépendante du réglage.

### 8.4 Verdict final (règle stricte)
Au canonique : `edge<0` → DISCARD. En version lente favorable : `edge>0` mais **Gate 2 ❌ + Gate 3 ❌** → DISCARD.
Tags : **pas d'edge (canonique) · beta long déguisé · grille = bruit (DSR)**.
**Cohérent avec la prédiction :** pour une AMA trend-following, le **Gate 2 (two-sided) est le juge** — shorts perdants, longs porteurs ⇒ beta, pas edge adaptatif.

### 8.5 Récupérable ?
Seulement comme **overlay de tendance long-only** (ce que le Gate 2 dénonce) sur actifs en hausse — donc redondant avec un trend-following long classique, et de toute façon **noyé dans le bruit** (Gate 3). **Archivé DISCARD.**

---

## 9. Limites & checklist d'audit complémentaire
- **Hypothèse de sortie** (always-in reversal + disaster-stop ATR) explicitée §5 : la fiche ne liste que le stop ATR ; un autre choix (exit-to-flat) changerait le nombre de trades mais pas le biais long (Gate 2) ni le bruit (Gate 3).
- **`contrib_long_pct` ininterprétable au canonique** (total net négatif → % de signe instable) ; on lit directement long expR>0 / short expR<0.
- **Dépendance au réglage** : canonique négatif, lent positif, OOS flippe à ER=60 — signal de non-robustesse.
- **8 002 trades** au canonique (whipsaw) : coûts importants ; cost-stress ×2 aggraverait. Frontière de bougie, couverture 30/40 : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s004_kaufman_ama.py
```
Sorties : console (réf + grille + 4 gates + verdict + fill close), `results/s004_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s004_sensitivity.png`. Pour la région favorable : changer `ER_REP, FI_REP` en tête. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s004_kaufman_ama.py`
Moteur `ftmo_lab.py` (coûts + `trade_metrics` + 4 gates) partagé (listé dans `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`). Source faisant foi : `code/strat_s004_kaufman_ama.py` (listing intégral ci-dessous, bloc heatmap allégé).

```python
"""
Strategy 4/109 — Kaufman Adaptive Moving Average (Setup & Filter). Source rating C.
ARCHETYPE: KAMA on close; entry MARKET-ON-CLOSE; always-in reversal + ATR disaster-stop.
Fill mapping: 'stop'=close[i] native, 'next_open'=open[i+1] (Gate1), 'close'=close[i+1].
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
FAST_LEN, SLOW_LEN, FILTER_N, ATR_LEN, ATR_STOP = 2, 30, 20, 20, 6.0
ER_REP, FI_REP = 10, 0.2                          # canonical Kaufman ER=10, modest filter

def kama(close, er_len, fast_len=FAST_LEN, slow_len=SLOW_LEN):
    change = (close - close.shift(er_len)).abs()
    vol = close.diff().abs().rolling(er_len).sum()
    er = (change / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fast, slow = 2.0/(fast_len+1), 2.0/(slow_len+1)
    sc = (er*(fast-slow)+slow)**2
    vals = close.values; scv = sc.values; ama = np.full(len(vals), np.nan); start = er_len
    if start < len(vals):
        ama[start] = vals[start]
        for i in range(start+1, len(vals)):
            ama[i] = ama[i-1] + (scv[i] if np.isfinite(scv[i]) else 0.0)*(vals[i]-ama[i-1])
    return pd.Series(ama, index=close.index)

def ama_signals(df, er_len, filter_index):
    ama = kama(df['close'], er_len); d1 = ama.diff()
    turn_up = (d1 > 0) & (d1.shift(1) < 0); turn_dn = (d1 < 0) & (d1.shift(1) > 0)
    min_ama = ama.shift(1).where(turn_up).ffill(); max_ama = ama.shift(1).where(turn_dn).ffill()
    filt = filter_index * d1.rolling(FILTER_N).std()
    long_entry = (d1 > 0) & min_ama.notna() & ((ama - min_ama) > filt)
    short_entry = (d1 < 0) & max_ama.notna() & ((max_ama - ama) > filt)
    return long_entry.fillna(False), short_entry.fillna(False)

def simulate_ama(df, long_entry, short_entry, *, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                 cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open','high','low','close'))
    A = lab.atr(df, atr_len).values; le, se = long_entry.values, short_entry.values
    n = len(df); idx = df.index; off = 0 if fill == 'stop' else 1; use_open = (fill == 'next_open')
    trades = []; pos = d = 0; entry = stop = risk0 = cost_R = 0.0; ebar = 0; t_in = None
    def rec(t_out, reason, px):
        return dict(entry=t_in, exit=t_out, reason=reason, dir=d, netR=d*(px-entry)/risk0 - cost_R, hold=np.nan)
    i = 0
    while i < n:
        if pos != 0 and i > ebar and np.isfinite(stop):
            if (d == 1 and l[i] <= stop) or (d == -1 and h[i] >= stop):
                trades.append(rec(idx[i], 'stop', stop)); pos = 0
        sig = 1 if le[i] else (-1 if se[i] else 0)
        if sig == -1 and not allow_short: sig = 0
        if sig != 0 and sig != pos and np.isfinite(A[i]) and A[i] > 0:
            eb = i + off
            if eb <= n - 1:
                price = o[eb] if use_open else c[eb]
                if pos != 0: trades.append(rec(idx[eb], 'reverse', price))
                d = pos = sig; entry = price; ebar = eb
                risk0 = A[i]*atr_stop; cost_R = (cost_bps/1e4)*abs(entry)/risk0
                stop = entry - d*risk0; t_in = idx[eb]
        i += 1
    if pos != 0: trades.append(rec(idx[n-1], 'eod', c[n-1]))
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, er, fi):
    if (t, er, fi) not in _SIG: _SIG[(t, er, fi)] = ama_signals(df, er, fi)
    return _SIG[(t, er, fi)]
def run_point(er_len, filter_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        le, se = _signals(t, df, er_len, filter_index)
        tr = simulate_ama(df, le, se, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    ERs = [2,10,20,40,60,80,100]; FIs = [0.0,0.1,0.2,0.3,0.5,1.0]
    grid = np.full((len(ERs), len(FIs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, er in enumerate(ERs):
        for b, fi in enumerate(FIs):
            m = lab.trade_metrics(run_point(er, fi)); grid[a, b] = m['expR']; sg[a, b] = m['sharpe']
    res = lab.run_gates(lambda fill='stop': run_point(ER_REP, FI_REP, fill=fill), sg, split='2015-12-31')
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s004_gates.csv", index=False)
    print(">>> VERDICT:", res['verdict'], "| gates FAIL:", res['n_fail'], "/4 |", res['reason'])
    # (per-instrument CSV + heatmap present in code/.)
```
*Listing fonctionnellement identique à `code/strat_s004_kaufman_ama.py` (affichage/heatmap allégés). Source faisant foi : le `.py`.*
