# Rapport stratégie 6/109 — ADX Filter sur breakout Donchian (Test 1 : Filter Threshold & Entry)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** (mais **résultat le plus vivant à ce jour : 3/4 gates PASS**) · **Source :** https://oxfordstrat.com/trading-strategies/adx/ (rating site : **D**).
**Date :** 2026-06-05 · **Registre :** entrée **#6** de `_INDEX.md`.

> ⚠️ Règle de verdict : KEEP ⇔ `edge_net>0` ET les 4 gates PASS. S006 passe 3 gates et meurt sur le Gate 2 → DISCARD.

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Breakout **Donchian** (trend-following) + filtre **ADX** ; entrée stop ; sortie canal opposé (50 %) + ATR |
| Univers | 30/40 instruments FTMO |
| Cas de base (Entry_Channel=20, ADX_Threshold=0) | **expR +0,0440 · PF 1,256 · Sharpe 0,98 · win 39,5 % · 5 507 trades · MaxDD −70,1 %** |
| **Gate 1 — Délai+1** | stop natif Sharpe **+0,98** → open[i+1] **+0,66** (survit) → ✅ **PASS** |
| **Gate 2 — Two-sided** | long **+0,1007** / short **−0,0200** → ❌ **FAIL** (beta long) |
| **Gate 3 — DSR (N=42)** | meilleur Sharpe **3,81** > E[max] 2,157 ; z +6,3 → ✅ **PASS** (signal réel) |
| **Gate 4 — OOS** | train +0,0512 (Sh +0,95) → test **+0,0378** (Sh **+1,02**) → ✅ **PASS** |
| **Gates** | **3/4 PASS** (le meilleur score des 6) |
| **VERDICT** | ❌ **DISCARD** — *beta long déguisé (Gate 2)* + *MaxDD −70 % intradeable FTMO* |

**Lecture (à signaler).** S006 est le **résultat le plus solide** rencontré : le breakout Donchian est un **vrai edge de trend-following** — il **survit au fill réaliste** (premier **stop-entry** à passer le Gate 1, car la position est tenue longtemps → l'artefact de fill est dilué, contrairement à l'ORB de S001/S002), il est **statistiquement réel** (DSR z>0, pas du bruit) et **robuste hors échantillon** (test Sharpe +1,02). **Mais il échoue le Gate 2** : l'edge est **entièrement long** (shorts −0,02), c'est-à-dire du **beta de tendance long** sur des actifs qui ont monté (crypto, métaux, énergie). Et le **MaxDD −70 %** le rend de toute façon **intradeable sur FTMO** (limite ~10 %). Enfin — comme le dit la fiche elle-même — **l'ADX n'apporte pas de valeur** : le cas de base (ADX=0) porte tout.

---

## 1. Spécification originale (reproduite fidèlement)

**Développeurs :** J. Welles Wilder (ADX) ; Richard Donchian (canaux). **Concept :** trend-following sur canaux de Donchian, filtré par l'ADX. **Rating site : D.** **Conclusion de la fiche :** *« The ADX does not add value to the base case trend-following model. »*

- **Entrée (stop intrabar) :** Long = buy stop 1 tick au-dessus de `UpperChannelOne[i−1]` (plus-haut sur `Entry_Channel` barres) ; Short = sell stop sous `LowerChannelOne[i−1]`.
- **Filtre ADX :** trader seulement si `ADX[i−1] ≥ ADX_Threshold` (ADX_Look_Back=14). `ADX_Threshold ∈ [0,60]`.
- **Sortie :** **Channel Exit** (canal opposé de période `Exit_Channel = 50 % × Entry_Channel`) + **Stop ATR** (`ATR(20)×6`, sert à normaliser le risque/sizing).
- **Sensibilité :** `Entry_Channel [5,200] × ADX_Threshold [0,60]`.

**Écarts assumés vs site** (idem S001-S005) : univers FTMO 30 instruments, métriques recalculées, R-multiples 0,5 %, coûts FTMO. **1 tick** négligé (daily CFD).

---

## 2-4. Univers, données, coûts, look-ahead (partagés, inchangés)
**Identiques à S001-S005.** Canaux et ADX calculés sur barres `≤ i−1` (`.shift(1)`), entrée stop sur barre `i` ; `risk0=ATR[i]×6`. Sans look-ahead. Cache des canaux par `(instrument, Entry_Channel)`, ADX par instrument.

---

## 5. Moteur de backtest et **ARCHÉTYPE D'ENTRÉE**

> **🔑 Archétype = STOP-entry intrabar (breakout Donchian) — même FAMILLE que l'ORB (S001/S002).** MAIS, différence cruciale : la position est **tenue longtemps** (sortie sur canal opposé + ATR), pas refermée le jour même. Donc le prix d'entrée (niveau du canal touché intrabar) ne représente qu'une **petite fraction** du P&L du trade → **l'artefact de fill est dilué**. C'est pourquoi, contrairement à l'ORB, **le Gate 1 PASSE** ici. *(Validation du pipeline : le Gate 1 distingue un artefact d'exécution court terme d'un vrai edge de tendance tenu.)*

Sim **`simulate_donchian`** dans `strat_s006` (breakout + sortie canal/ATR ; flat entre trades). **Réutilisés à l'identique de `ftmo_lab` v2-gates :** coûts, `trade_metrics`, **4 gates**. **Mapping des fills (archétype stop, comme S001/S002) :** `'stop'`=niveau du canal intrabar (natif/optimiste), `'next_open'`=open[i+1] (Gate 1 réaliste), `'close'`=close[i]. Les sorties (canal/ATR) sont des stops protecteurs → fill au niveau = réaliste.

---

## 6. Paramètres
| Paramètre | Valeur(s) |
|---|---|
| `Entry_Channel` | balayé {5,10,20,50,100,150,200} ; **réf. 20** |
| `ADX_Threshold` | balayé {0,10,20,30,40,60} ; **réf. 0 (cas de base, ADX off)** |
| `Exit_Channel` | 50 % × Entry_Channel · `ADX_Look_Back` 14 · `ATR` 20/6 · `RISK_FRAC` 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

Point de référence = **cas de base** : canal 20 (turtle court terme), ADX désactivé — la fiche conclut que l'ADX n'ajoute rien, donc le cas de référence honnête est le Donchian pur.

---

## 7. Résultats

### 7.1 Cas de base (Entry_Channel=20, ADX_Threshold=0)
**5 507 trades · win 39,5 % · expR +0,0440 R · PF 1,256 · Sharpe 0,98 · CAGR +3,1 % · MaxDD −70,1 %.** 20/30 positifs.
Signature trend-following : win rate bas (39 %), gains qui courent (PF 1,26), mais **drawdown catastrophique (−70 %)** — typique d'un trend follower en R-sizing sans contrôle de vol.

### 7.2 Par instrument (`results/s006_per_instrument.csv`)
**Gagnants (gros trends) :** ETHUSD (+0,317), XPTUSD (+0,219), BTCUSD (+0,170), XPDUSD (+0,153), XAGUSD (+0,139), UKOIL (+0,099). **Perdants (FX mean-reverting) :** AUDJPY, AUDUSD, EURUSD, NZDUSD (−0,06), EURGBP (−0,147).
→ **Manuel du trend-following :** ça marche sur crypto/métaux/énergie (qui ont fait de grands trends, surtout à la hausse), ça saigne sur le FX (range-bound). D'où le **biais long** (Gate 2).

### 7.3 Sensibilité Entry_Channel × ADX_Threshold (`results/s006_sensitivity.png`)
**95 %** positif. L'expectancy **croît fortement avec Entry_Channel** (EC200 ≫ EC20) — mais les grands canaux ont **très peu de trades** (EC200 : ~200 trades, gros trends rares = queue droite épaisse). **L'ADX n'aide pas de façon robuste :** la colonne `ADX=0` est solide ; les seuils ADX élevés ne font surtout que **raréfier** les trades (quelques cellules « chanceuses » sparse). **Confirme la conclusion de la fiche.**

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

`results/s006_gates.csv`. Cas de base (EC=20, ADX=0).

| # | Gate (loi) | Résultat | Verdict |
|---|---|---|---|
| 1 | **Délai+1 (L26)** | stop natif Sharpe **+0,98** (expR +0,044) → open[i+1] **+0,66** (expR +0,029) | ✅ **PASS** |
| 2 | **Two-sided (L25)** | long expR **+0,1007** (n=2919) / short expR **−0,0200** (n=2588) | ❌ **FAIL** — beta long |
| 3 | **DSR (N=42)** | meilleur Sharpe de grille **3,811** > E[max bruit] **2,157** ; z **+6,3** | ✅ **PASS** — signal réel |
| 4 | **OOS (≤2015/≥2016)** | train +0,0512 (Sh +0,95) → test **+0,0378** (Sh **+1,02**) — tient | ✅ **PASS** |

**Gates FAIL : 1/4** (bloquant).

### 8.1 Lecture
- **Gate 1 — PASS (notable).** Premier **stop-entry** à survivre : Sharpe +0,98 → +0,66 en fill réaliste (open[i+1]). La perte (~1/3) reflète le slippage d'un breakout, mais l'edge **reste clairement positif** car il vient de la **tenue du trend** (jours/semaines), pas de l'exécution intrabar. *(Contraste net avec S001/S002 où le fill réaliste inversait le signe.)*
- **Gate 2 — FAIL (le juge).** **Longs +0,10, shorts −0,02.** Le breakout Donchian capte les hausses (crypto/métaux/énergie) mais ne gagne pas du côté court → **beta de tendance long**, pas un edge symétrique. À comparer à un buy-and-hold timé de ces actifs.
- **Gate 3 — PASS.** Le meilleur Sharpe de grille (3,8) dépasse l'espérance du max de 42 tirages de bruit (2,16) : **il y a un vrai signal trend-following** (pas du bruit de multiplicité). *Caveat :* porté par les grands canaux **sparse** (queue droite de quelques très gros trends) — signal réel mais **concentré**.
- **Gate 4 — PASS.** Robuste OOS (test Sharpe +1,02, supérieur au train). Le trend-following Donchian ne s'est pas décayé sur 2016-2026.

### 8.2 Verdict final
`edge_net>0` ✅, **Gate 1 ✅, Gate 3 ✅, Gate 4 ✅**, mais **Gate 2 ❌** → **DISCARD**. Tag : **beta long déguisé**.
**Second clou, décisif en pratique :** **MaxDD −70 %** — intradeable sur FTMO (limite de drawdown ~10 %), même si le côté long était retenu.

### 8.3 Récupérable ? (la nuance honnête)
C'est le **premier candidat avec un vrai signal** (DSR + OOS + Gate 1 OK). Il n'est PAS retenu car (a) **asymétrique (long-beta)** — le mérite réel doit être mesuré **vs buy-and-hold timé** des actifs porteurs, et (b) **−70 % de DD**. Piste légitime pour plus tard : un **sleeve long-only trend-following vol-targeté** (Donchian long sur crypto/métaux/énergie), évalué en *excess vs beta* et avec contrôle de drawdown — **pas** comme stratégie symétrique autonome. À ce stade : **DISCARD**, mais noté comme le profil le plus prometteur des 6.

---

## 9. Limites & checklist d'audit complémentaire
- **DSR concentré** : porté par peu de gros trends (grands canaux sparse) → vérifier par bootstrap par blocs et par exclusion des 5 plus gros trades.
- **MaxDD −70 %** : rédhibitoire FTMO ; un vol-targeting changerait le profil (à tester si on revisite).
- **Gate 2 / buy&hold** : quantifier l'excès du long Donchian sur un buy-and-hold timé des actifs porteurs (le « vrai » test du mérite).
- 1 tick négligé, frontière de bougie, couverture 30/40 : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s006_adx_donchian.py
```
Sorties : console (réf + grille + 4 gates + verdict + cell favorable + value-add ADX), `results/s006_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s006_sensitivity.png`. Moteur `ftmo_lab.py` partagé/inchangé.

---

## Annexe — `code/strat_s006_adx_donchian.py`
Moteur `ftmo_lab.py` partagé (cf. `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`). Source faisant foi : `code/strat_s006_adx_donchian.py` (listing intégral ci-dessous, bloc heatmap allégé).

```python
"""
Strategy 6/109 — ADX Filter on Donchian breakout (Filter Threshold & Entry). Source rating D.
ARCHETYPE: STOP-entry (Donchian channel breakout) held long (channel/ATR exit) -> fill artefact diluted.
Fill mapping: 'stop'=channel level (native), 'next_open'=open[i+1] (Gate1), 'close'=close[i].
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
ADX_LEN, ATR_LEN, ATR_STOP = 14, 20, 6.0
EC_REP, ADX_REP = 20, 0                          # base case: 20-bar Donchian, ADX off

def compute_adx(df, period=ADX_LEN):
    h, l, c = df['high'], df['low'], df['close']
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def _precompute(df, entry_channel):
    ec = max(1, int(round(entry_channel * 0.5)))
    u1 = df['high'].rolling(entry_channel).max().shift(1); l1 = df['low'].rolling(entry_channel).min().shift(1)
    u2 = df['high'].rolling(ec).max().shift(1); l2 = df['low'].rolling(ec).min().shift(1)
    return u1.values, l1.values, u2.values, l2.values, compute_adx(df).shift(1).values

def simulate_donchian(df, pc, *, adx_threshold, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; u1, l1, u2, l2, ax = pc; n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(ax[i]) and ax[i] >= adx_threshold and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        long_brk = np.isfinite(u1[i]) and h[i] >= u1[i]
        short_brk = allow_short and np.isfinite(l1[i]) and l[i] <= l1[i]
        if not (long_brk or short_brk): i += 1; continue
        d = 1 if long_brk else -1; risk0 = A[i] * atr_stop
        if fill == 'stop':        entry = max(o[i], u1[i]) if d == 1 else min(o[i], l1[i]); eb = i
        elif fill == 'close':     entry = c[i]; eb = i
        elif fill == 'next_open':
            if i + 1 > n - 1: i += 1; continue
            entry = o[i + 1]; eb = i + 1
        else: raise ValueError(fill)
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0; atr_lvl = entry - d * risk0
        exit_p = exit_j = reason = None; j = eb + 1
        while j <= n - 1:
            ch = l2[j] if d == 1 else u2[j]
            ex = (max(atr_lvl, ch) if np.isfinite(ch) else atr_lvl) if d == 1 else \
                 (min(atr_lvl, ch) if np.isfinite(ch) else atr_lvl)
            if d == 1 and l[j] <= ex:  exit_p, reason, exit_j = ex, 'chan/atr', j; break
            if d == -1 and h[j] >= ex: exit_p, reason, exit_j = ex, 'chan/atr', j; break
            j += 1
        if exit_p is None: exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=d,
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_PC = {}
def _pc(t, df, ec):
    if (t, ec) not in _PC: _PC[(t, ec)] = _precompute(df, ec)
    return _PC[(t, ec)]
def run_point(entry_channel, adx_threshold, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_donchian(df, _pc(t, df, entry_channel), adx_threshold=adx_threshold, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    ECs = [5,10,20,50,100,150,200]; ADXs = [0,10,20,30,40,60]
    grid = np.full((len(ECs), len(ADXs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ec in enumerate(ECs):
        for b, ad in enumerate(ADXs):
            m = lab.trade_metrics(run_point(ec, ad)); grid[a, b] = m['expR']; sg[a, b] = m['sharpe']
    res = lab.run_gates(lambda fill='stop': run_point(EC_REP, ADX_REP, fill=fill), sg, split='2015-12-31')
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s006_gates.csv", index=False)
    print(">>> VERDICT:", res['verdict'], "| gates FAIL:", res['n_fail'], "/4 |", res['reason'])
    # (per-instrument CSV + heatmap present in code/.)
```
*Listing fonctionnellement identique à `code/strat_s006_adx_donchian.py` (affichage/heatmap allégés). Source faisant foi : le `.py`.*
