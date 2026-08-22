# Rapport stratégie 2/109 — Toby Crabel : 2-Bar Narrow Range + ORB (Test : Setup & Exit)

**Projet :** filtrage systématique des 109 revues oxfordstrat.com sur l'univers FTMO.
**Pipeline :** `ftmo_lab v2-gates` — **KEEP impossible sans les 4 gates constitutionnels (§8).**
**Statut :** ❌ **DISCARD** · **Source :** https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-2/ (rating site : **C**).
**Date :** 2026-06-04 · **Registre :** entrée **#2** de `_INDEX.md`.

> ⚠️ Règle de verdict : edge positif après coûts **nécessaire mais non suffisant**. KEEP ⇔ `edge_net>0` ET Gate 1 (délai+1) ET Gate 2 (two-sided) ET Gate 3 (DSR) ET Gate 4 (OOS).

---

## 0. Résumé exécutif

| Élément | Valeur |
|---|---|
| Stratégie | Crabel 2-Bar NR + ORB, **sans target** ; sorties Time / Stretch / ATR (long+short) |
| Univers | 30/40 instruments FTMO (idem S001) |
| Point de référence | Look_Back=20, Time_Index=10 → **expR +0,0225 · PF 1,295 · Sharpe 1,11 · win 26,3 % · 4 366 trades** |
| Robustesse grille | **100 %** des 42 cellules (Look_Back×Time) à expectancy positive |
| **Gate 1 — Délai+1** | optimiste Sharpe **+1,11** → réaliste **−0,35** (next_open) / **−0,37** (close) → ❌ **FAIL** |
| **Gate 2 — Two-sided** | long +0,0566 / short **+0,0263** (les deux positifs) → ✅ **PASS** |
| **Gate 3 — DSR (N=42)** | SR_obs **2,38** > E[max] 2,16, z **+5,0** → ✅ **PASS** |
| **Gate 4 — OOS** | train +0,0303 (Sh +1,28) → test **+0,0153** (Sh +0,90) → ✅ **PASS** |
| **Gates** | **3/4 PASS** |
| **VERDICT** | ❌ **DISCARD** — *artefact de fill intrabar* (Gate 1) |

**Lecture (cas d'école).** Contrairement à S001, cette variante est **statistiquement saine** : edge **symétrique** (longs *et* shorts gagnants → pas de beta déguisé), grille **au-dessus du bruit** (DSR z>0), et edge qui **tient hors échantillon** (Sharpe +1,28 → +0,90). Elle passe **3 gates sur 4**. Mais elle **meurt au Gate 1** : tout l'edge provient de l'hypothèse d'exécution **au niveau exact du stop intrabar**. Avec un fill réaliste (open du lendemain *ou* close du jour de breakout), le Sharpe passe de **+1,11 à ≈ −0,36** et le PF sous 1. **C'est un artefact d'exécution, pas un edge tradable en CFD daily FTMO.** Illustration nette de pourquoi le Gate 1 est le plus décisif.

---

## 1. Spécification originale (reproduite fidèlement)

Même développeur/source que S001 (Crabel 1990), même **concept** (expansion de volatilité), même **setup** 2-bar NR et même **entrée** ORB. Ce qui change dans la fiche « Setup & Exit » :

| Élément | S001 (Exits) | **S002 (Setup & Exit)** |
|---|---|---|
| Variable setup | Look_Back = 20 (fixe) | **Look_Back balayé [10, 50]** (NR lookback) |
| Profit target | **Oui** (Target_Index × risque) | **Non** |
| Sorties | Target / Time / Stretch / ATR | **Time / Stretch / ATR** (pas de target) |
| Grille de sensibilité | Target × Time | **Look_Back × Time_Index** |

Détail des sorties S002 (Table 1 de la fiche) :
- **Time Exit :** clôture au n-ième jour, `n = Time_Index ∈ [1,40]`.
- **Stretch Exit :** long → sell stop à `[Open − Stretch]` ; short → buy stop à `[Open + Stretch]` (calculés au jour d'entrée). C'est un stop à la bande de stretch opposée.
- **Stop Loss ATR :** `ATR(20) × 6` (long : `Entry − ATR×6` ; short : `Entry + ATR×6`).
- `Stretch = SMA(Noise,10) × 2`, `Noise = min(High−Open, Open−Low)` (inchangé).

**Écarts assumés vs site** (identiques à S001) : univers FTMO 30 instruments (vs 42 futures US 1980-2013) ; résultats recalculés (la fiche n'a que des images) ; sizing en R-multiples 0,5 % (vs fixed-fractional 1 %) ; modèle de coûts FTMO. Raison : univers cible + comparabilité des 109.

---

## 2. Univers, données et coûts (partagés, inchangés)

**Identiques à S001** — voir `REPORT_S001 §2-§4`. 30 instruments FTMO (10 indices 2000-2026, 9 FX 2018/2021+, 9 commodities 2005+, BTC/ETH), store `ohlc/` partagé (`build_ohlc_store.py`), modèle de coûts `ftmo_lab.round_turn_cost_bps` (spread M1 + commission specs + slippage, plancher par classe, méd. ~2,9 bps round-turn). **Aucune donnée ni coût n'a changé entre S001 et S002** → comparabilité directe.

---

## 3. Pré-traitement des signaux (sans look-ahead)

- `rng2[i] = max(High[i],High[i-1]) − min(Low[i],Low[i-1])` ; setup `i` ⇔ `rng2[i] ≤ min(rng2[i-Look_Back…i-1])` via `rolling(Look_Back).min().shift(1)` (jamais la barre courante).
- `Stretch[i]` calculé ≤ barre `i`. **Entrée à `i+1`** (le moteur consomme `setup[i-1]`/`Stretch[i-1]`).
- Les signaux ne dépendent du paramètre balayé `Look_Back` que via `prev_min` ; `Stretch` est indépendant de `Look_Back` (mis en cache par instrument).

---

## 4. Moteur de backtest et hypothèses

Archétype **ORB stop-entry + bracket**, mais le bracket diffère de `simulate_bracket` (pas de target, ajout d'un **Stretch Exit**) → sim minimale fidèle **`simulate_setupexit`** écrite dans `strat_s002` (autorisé par le protocole). **Réutilisés à l'identique de `ftmo_lab` v2-gates** : `atr`, `round_turn_cost_bps`, `RISK_FRAC`, `trade_metrics`, et **les 4 gates** (`run_gates`).

- **Normalisation du risque :** `R = ATR(20) × 6` (sizing du site), comme S001 → R comparable entre stratégies.
- **Entrée :** ORB `Open ± Stretch` ; remplissage selon `fill` (le levier L26) : `'stop'` (optimiste), `'close'`, `'next_open'`.
- **Sortie :** premier touché parmi { stop le plus proche entre ATR et Stretch ; Time Exit }. Le « stop » combine les deux protections : long → `max(Entry−ATR×6, Open−Stretch)` ; short → `min(Entry+ATR×6, Open+Stretch)`.
- **Hypothèses intrabar (conservatrices, identiques S001) :** un seul stop composite touché → sortie au niveau du stop ; double-touche à l'entrée → trade perdant ; pas de positions superposées.
- **Chaque trade porte `dir`** (+1/−1/0) pour le gate two-sided.

---

## 5. Paramètres

| Paramètre | Valeur(s) |
|---|---|
| `Look_Back` (setup) | **balayé** {10,15,20,25,30,40,50} ; **réf. 20** |
| `Time_Index` (exit) | **balayé** {1,3,5,10,20,40} ; **réf. 10** |
| `Stretch_Length` / `Stretch_Multiple` | 10 / 2 |
| `ATR_Length` / `ATR_Stop` | 20 / 6 |
| `RISK_FRAC` | 0,5 % |
| Grille DSR | 7 × 6 = **42 cellules** |

---

## 6. Résultats (mesure brute, fill optimiste `stop`)

### 6.1 Point de référence (Look_Back=20, Time=10)
**4 366 trades · win 26,3 % · expR +0,0225 R · PF 1,295 · Sharpe 1,11 · CAGR +1,7 % · MaxDD −38,0 %.** 23/30 instruments positifs.
Profil typique d'un **breakout sans target** : win rate bas (26 %) compensé par des gains qui courent (PF 1,3) — mais MaxDD élevé (−38 %).

### 6.2 Par instrument (extraits — `results/s002_per_instrument.csv`)
**Top 8 :** XPDUSD (comm, expR 0,184, PF 9,5), XPTUSD (0,123), XAGUSD (0,104), AUS200 (idx, 0,071), COCOA (0,061), COFFEE (0,050), ETHUSD (crypto, 0,039), US2000 (idx, 0,037).
**Bottom 5 :** XAUUSD −0,021, USDCAD −0,027, NZDUSD −0,030, EURUSD −0,048, EURGBP −0,064.
→ **Commodities** dominent, indices/crypto contribuent, **FX en bas**. Edge plus **large et symétrique** que S001.

### 6.3 Sensibilité Look_Back × Time (expectancy R/trade) — `results/s002_sensitivity.png`
**100 % des 42 cellules positives** ; expectancy croît avec la sortie longue (40 j), assez **stable en Look_Back** (peu d'overfit sur ce paramètre setup). *(À ce stade tout semble bon — c'est le Gate 1 qui tranche.)*

---

## 7. (réservé — voir §6 mesure / §8 gates)

---

## 8. GATES CONSTITUTIONNELS (v2) — OBLIGATOIRE

Appel : `ftmo_lab.run_gates(make_run(20,10), sharpe_grid, split='2015-12-31')`. Brut : `results/s002_gates.csv`.

| # | Gate (loi) | Résultat S002 | Verdict |
|---|---|---|---|
| 1 | **Délai+1 / fill réaliste (L26)** | optimiste Sharpe **+1,11** (expR +0,0225, PF 1,30) → **next_open** Sharpe **−0,35** (expR −0,0067, PF 0,93) ; **close** Sharpe **−0,37** (expR −0,0071, PF 0,92) | ❌ **FAIL** — artefact de fill intrabar |
| 2 | **Two-sided (L25)** | long expR **+0,0566** (n=1914) / short expR **+0,0263** (n=1786) — **les deux positifs** ; contrib long 110 % | ✅ **PASS** |
| 3 | **DSR (N=42)** | SR sélectionné **2,380** > E[max bruit] **2,157** ; DSR_z **+5,0** | ✅ **PASS** |
| 4 | **OOS (≤2015 / ≥2016)** | train expR +0,0303 (Sh +1,28, n=2092) → test expR **+0,0153** (Sh +0,90, n=2274) — pas de flip | ✅ **PASS** |

**Gates FAIL : 1/4** (mais bloquant).

### 8.1 Lecture
- **Gate 1 — FAIL (décisif).** Les **deux** fills réalistes (next_open *et* close) inversent le signe : Sharpe +1,11 → ≈ −0,36, PF 1,30 → 0,92. Le win rate chute (26,3 % → 24,8-26,9 %) et surtout la distribution des gains s'effondre. **Tout l'edge venait d'entrer au niveau exact du stop de breakout** ; le high qui touche le buy-stop est par construction au-dessus de ce stop, donc une entrée réaliste (close du jour ou open du lendemain) ne capte pas la continuation intra-barre. **Non tradable.**
- **Gate 2 — PASS.** Edge **symétrique** : shorts aussi positifs (+0,0263). Pas de beta long déguisé (contraste net avec S001 où les shorts perdaient). Le mécanisme breakout fonctionne des deux côtés — *sous le fill optimiste*.
- **Gate 3 — PASS.** Le Sharpe sélectionné (2,38) **dépasse** l'espérance du max de 42 tirages de bruit (2,16) ; la grille n'est pas du bruit de multiplicité.
- **Gate 4 — PASS.** Edge **robuste OOS** : positif et de même signe sur 2016-2026 (Sharpe +0,90). Pas de décroissance de régime.

### 8.2 Verdict final (règle stricte)
`edge_net>0` ✅ mais **Gate 1 FAIL** ⇒ **❌ DISCARD**. Tag : **artefact de fill intrabar**.
**Le plus instructif :** S002 passe 3/4 gates (symétrie, multiplicité, OOS) — il aurait été *KEEP* sous une barre laxiste — et n'est tué que par l'exécution réaliste. C'est la démonstration que **le Gate 1 est le filtre qui sépare un vrai edge d'un artefact de microstructure.**

### 8.3 Récupérable ?
Non en l'état : l'edge **est** le fill intrabar. Une version « honnête » entrerait au close/next-open et **perd** (Sharpe −0,36). Aucun réglage de Look_Back/Time ne sauve un edge dont la source est l'exécution irréaliste. **Archivé DISCARD.**

---

## 9. Limites & checklist d'audit complémentaire
- **Gate 1 testé sur 2 fills** (next_open + close) — les deux échouent, robuste.
- **Cost-stress ×1,5/×2 (L33)** et **block-bootstrap CI** non bloquants ici (le Gate 1 tranche avant) — recommandés en routine.
- **R = ATR×6** comme risque de sizing alors que le Stretch Exit peut être plus serré : choix de comparabilité (mêmes R que S001) ; tester R = distance au stop composite en sensibilité.
- **MaxDD −38 %** (fill optimiste) déjà rédhibitoire pour FTMO (limites de drawdown) — second clou.
- Frontière de bougie UTC/EET, couverture 30/40, `≤`/`<` NR : idem S001 §9.

---

## 10. Reproduction
**Env :** Python 3.10.12 · numpy 2.2.6 · pandas 2.3.3 · matplotlib 3.10.8 · pyarrow 24.0.0.
```bash
cd oxfordstrat_109/code && python strat_s002_crabel_nr_setupexit.py
```
Sorties : console (réf + grille + 4 gates + verdict), `results/s002_{gates,per_instrument,sensitivity_expectancy}.csv`, `results/s002_sensitivity.png`. Moteur partagé : `ftmo_lab.py` (inchangé). Résultat vérifié reproductible.

---

## Annexe — `code/strat_s002_crabel_nr_setupexit.py`
Le moteur `ftmo_lab.py` (cost model + `trade_metrics` + 4 gates) est partagé et listé dans `REPORT_S001` Annexe A / `PIPELINE_v2_gates.md`. Source faisant foi : `code/strat_s002_crabel_nr_setupexit.py`.

```python
"""
Strategy 2/109 — Toby Crabel 2-Bar Narrow Range + ORB (Test: Setup & Exit).
Source: https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-2/  (rating C)
SETUP swept: Look_Back in [10,50]. NO target. Exits = Time | Stretch (Open-/+Stretch) | ATR stop.
Cost model, R-normalisation, metrics and the 4 gates reused from ftmo_lab v2-gates UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 10, 2.0, 20, 6.0
LB_REP, TM_REP = 20, 10

def crabel_signals(df, look_back):
    h, l, o = df['high'], df['low'], df['open']
    rng2 = (pd.concat([h, h.shift(1)], axis=1).max(axis=1)
            - pd.concat([l, l.shift(1)], axis=1).min(axis=1))
    prev_min = rng2.rolling(look_back).min().shift(1)
    setup = (rng2 <= prev_min) & rng2.notna() & prev_min.notna()
    noise = pd.concat([h - o, o - l], axis=1).min(axis=1).clip(lower=0)
    stretch = noise.rolling(STRETCH_LEN).mean() * STRETCH_MULT
    return setup, stretch

def simulate_setupexit(df, setup, stretch, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                       cost_bps=2.0, allow_short=True, fill='stop'):
    """ORB stop entry; exits = Time | Stretch-band stop | ATR stop (no profit target).
    `fill` ('stop'|'close'|'next_open') = L26 lever. R = ATR*atr_stop. Trades carry `dir`."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit, short_hit = h[e] >= buy, (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if long_hit and short_hit:
            trades.append(dict(entry=idx[e], exit=idx[e], reason='both', dir=0,
                               netR=-2*st[i-1]/risk0 - cost_R, hold=0)); i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1
        if fill == 'stop':
            entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1:
                i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        atr_lvl = entry - d * risk0
        str_lvl = o[e] - d * st[i-1]
        stop_lvl = max(atr_lvl, str_lvl) if d == 1 else min(atr_lvl, str_lvl)
        last = min(e + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last:                    exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[e], exit=idx[exit_j], reason=reason, dir=d,
                           netR=grossR - cost_R, hold=exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, lb):
    k = (t, lb)
    if k not in _SIG: _SIG[k] = crabel_signals(df, lb)
    return _SIG[k]

def run_point(look_back, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        setup, stretch = _signals(t, df, look_back)
        tr = simulate_setupexit(df, setup, stretch, time_index=time_index,
                                cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    pool = run_point(LB_REP, TM_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s002_per_instrument.csv")
    LBs = [10, 15, 20, 25, 30, 40, 50]; TMs = [1, 3, 5, 10, 20, 40]
    grid = np.full((len(LBs), len(TMs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, lb in enumerate(LBs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb, tm)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"{x}d" for x in TMs]).to_csv("s002_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, TM_REP, fill=fill), sharpe_grid, split='2015-12-31')
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s002_gates.csv", index=False)
    print(">>> VERDICT:", res['verdict'], "| gates FAIL:", res['n_fail'], "/4 |", res['reason'])
    # (heatmap code identical in spirit to S001 — omitted here for brevity; present in code/.)
```

*Note : le listing ci-dessus est fonctionnellement identique à `code/strat_s002_crabel_nr_setupexit.py` (bloc d'affichage console/heatmap allégé). Source faisant foi : le fichier `.py`.*
