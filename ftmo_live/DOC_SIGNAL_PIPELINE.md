# DOC_SIGNAL_PIPELINE — couches de signal & sizing du book FTMO v2.2 (LECTURE SEULE)

> Mission 4 (2026-06-19). **Aucune ligne de code modifiée.** Documente le pipeline
> de signal/sizing tel qu'exécuté en live, et répond aux trois questions posées.
> Références : `ftmo_live/lib/signals.py`, `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`
> (= code path des 462 cohortes, importé tel quel), `ftmo_live/lib/governor.py`, `ftmo_live/brain.py`.

## 0. Chaîne live (qui appelle quoi)

```
brain.py (cron 21:50 Paris)
  └─ signals.weights_for(T, cache)            # lib/signals.py:28
       └─ engine.build_signals()              # engine.py:95  → WT[XAUUSD, USDJPY], ON
  └─ governor.preview(phase, wt_row, …)        # lib/governor.py:56
       └─ engine._target_for_segment(…)        # engine.py:343 → cibles USD = WT × scale × eq
  └─ statefiles.build_targets(…) → targets.json
```

`build_signals()` produit des **poids par jambe** `WT` (causaux, `shift(1)` → données ≤ T-1).
Le **gouverneur** (`_target_for_segment`) transforme `WT.loc[T]` en **cibles USD** en
multipliant par `scale × eq`. **L'EA ré-applique le gouverneur sur SON equity au moment des
fills** (sémantique sim, `brain.py:11-12`) — donc l'equity de compte qui *lie* le sizing est
celle de l'EA à 22:05, pas celle du preview brain.

> ⚠️ **Correction d'un implicite de la mission.** Les couches « equity-gate MA100 »,
> « book-vol 60d » et « vol-derisk 20d » **ne s'appliquent QU'À LA JAMBE OR (XAUUSD)**, pas à
> J1/USDJPY (cf. §1 vs §2, `engine.py:117-131` vs `134-138`). USDJPY n'a que : momentum 12-1
> + vol-target 60d par-jambe. L'equity de compte ($11k) agit sur USDJPY **uniquement via le
> gouverneur** (§3), jamais via l'equity-gate MA100.

---

## 1. Jambe OR (XAUUSD) — 5 couches (`engine.py:104-131`)

| # | Couche | Code | Effet |
|---|--------|------|-------|
| 1 | **Sign-blend TSMOM** (multi-lookback, carry-adj) | `:105-112` | `sig = moyenne_{L∈{60,120,250}} sign(base/base.shift(L)−1)`, sur prix carry-ajusté. **Deadband `theta=0.34`** : `sig` mis à 0 si `|sig|<0.34` ⇒ il faut **≥ 2 des 3 lookbacks d'accord** (|±1/3|=0.33 exclu). |
| 2 | **Vol-target 10% (par-jambe, 60d)** | `:113-114` | `w = sig × clip(0.10/rv60, ≤5)`, `.shift(1)`. `rv60` = vol réalisée 60d annualisée. |
| 3 | **Book-vol 60d** | `:117-119` | `bvol = std60(w·ret_or)×√252` ; `scale = clip(0.10/bvol, ≤10)`. Cible 10% de vol du *book or*. |
| 4 | **Vol-derisk 20d** | `:120-121` | `v20 = std20(w·ret_or)×√252` ; `scale ×= min(1, 0.10/v20)`. **Ne coupe QUE** (jamais de levier) quand la vol 20d récente > 10% → un pic de vol récent réduit l'OR. |
| 5 | **Equity-gate MA100** | `:123-131` | voir ci-dessous. |

**Couche 5 — equity-gate MA100 (détail).**
```python
net = (pos*ret_or) − coûts_half_RT + swaps        # engine.py:125-128  (P&L net simulé de la jambe OR)
eq  = (1+net).cumprod()                            # :129  COURBE D'EQUITY SIMULÉE de la sleeve OR
gate = (eq > eq.rolling(100).mean()) ? 1.0 : 0.4   # :130  puis .shift(1)
w_gold = (pos × gate).clip(-1.5, 1.5)              # :131
```
- C'est un **filtre de tendance sur la PROPRE courbe d'equity simulée de la sleeve OR**, PAS
  l'equity du compte FTMO. `eq` est un `cumprod` de rendements nets de la sleeve.
- **Action = réduction de poids, pas coupe binaire** : poids OR × **1.0** si la courbe OR est
  au-dessus de sa moyenne mobile 100 jours, sinon × **0.4** (plancher 40 %, jamais 0).
- `.shift(1)` ⇒ causal (état de la courbe ≤ T-1).
- Le commentaire `:123-124` note que cette couche est **un composant du pipeline auteur, signalé
  par l'audit comme non documenté dans la spec du rapport** (répliqué pour test).

---

## 2. Jambe J1 (USDJPY) — 12-1 long-only, vol-target 60d (`engine.py:134-138`)

```python
mom = pj.shift(21)/pj.shift(252) − 1.0       # momentum 12-1 mois (saute le dernier mois)
sj  = (mom > 0) ? 1.0 : 0.0                   # LONG-ONLY : long si mom>0, sinon FLAT
w_jpy = (sj × clip(0.10/rvj60, ≤5)).shift(1).clip(-1.5, 1.5)
```
- **Pas d'equity-gate MA100. Pas de book-vol 60d. Pas de vol-derisk 20d.** (Ces 3 couches sont
  dans la branche OR.)
- **Seul mécanisme de vol pour USDJPY** = le **vol-target 60d par-jambe** :
  `w_jpy ∝ 1/rvj60`, plafonné à 5×, clippé `[-1.5, 1.5]` (long-only ⇒ `[0, 1.5]`).
  → **la taille USDJPY MONTE quand sa vol 60d BAISSE, et baisse quand sa vol 60d monte.**
- **On/off de USDJPY = uniquement le signe du momentum 12-1** : `mom ≤ 0 ⇒ sj=0 ⇒ flat`.

**Réponse à M4(b) « comment la taille USDJPY varie avec la volatilité » :** par le seul
vol-target 60d par-jambe (`0.10/rvj60`, cap 5×). Les couches book-vol 60d et vol-derisk 20d
mentionnées dans la mission s'appliquent à l'OR, pas à USDJPY. *Au niveau book*, la vol n'entre
plus pour USDJPY que via le gouverneur (§3), dont `taper`/`glide`/`pace` dépendent de l'equity et
du temps, pas de la vol instrument.

---

## 3. Gouverneur (book-level) — où l'equity de compte entre (`engine.py:343-354`)

```python
eq    = bal + mtm(positions)                              # EQUITY DU COMPTE
room  = (eq − FLOOR)/INIT                                  # FLOOR=9000, INIT=10000 (engine.py:36-38)
taper = clip(room / cfg.taper, 0, 1)         # cfg.taper=0.02 ⇒ plein si room≥2% init, →0 vers le floor
prog  = (eq/INIT − 1) / cfg.target                        # target P1=0.10, P2=0.05
glide = cfg.glide(=0.5) si prog>0.8 sinon 1.0             # demi-taille quand ≥80% de la cible (lock-in)
pace  = clip(1 + pace_k·(frac_temps − prog), 0.8, 2.0)    # accélère si en retard, freine si en avance
scale = vm × taper × glide × pace                          # vm=14 (CFG_V2)
# cible 22:05 (s=4) :
tgt_USDJPY = w_jpy × scale × eq                            # engine.py:368
# puis margin-cap : si Σ|tgt|·MRATE > 0.60·eq → tout ramené (engine.py:373-379), MRATE_JPY=0.01
```

Donc **l'equity de compte agit sur USDJPY de 3 façons (gouverneur, pas equity-gate)** :
1. **`× eq`** direct : notionnel ∝ equity.
2. **`taper`** : `clip((eq−9000)/10000 / 0.02, 0, 1)` → coupe TOUT le book linéairement quand
   l'equity approche le floor statique 9000 $ ; plein dès que la marge au floor ≥ 2 % d'init.
3. **`glide`** : demi-taille (×0.5) tout le book dès que ≥80 % de la cible de phase.

---

## 4. État live au 2026-06-19 (réconciliation avec `state.json`)

| Grandeur | Valeur | Calcul | state.json |
|---|---|---|---|
| equity | 11 023,11 $ | — | `equity` ✓ |
| FLOOR / INIT | 9 000 / 10 000 | engine.py:36-38 | `static_floor=9000` ✓ |
| room | 0,2023 | (11023,11−9000)/10000 | — |
| **taper** | **1,0** | clip(0,2023/0,02,0,1)=clip(10,1)=1 | `governor.taper=1.0` ✓ |
| prog (P1) | 1,02 | (0,10231)/(0,10) — **cible P1 déjà DÉPASSÉE** | `target_equity≈11002` ✓ |
| **glide** | **0,5** | prog 1,02 > 0,8 ⇒ 0,5 | `governor.glide=0.50` ✓ |
| pace | 0,8 | borne basse (en avance sur le calendrier) | `governor.pace=0.80` ✓ |
| **scale** | **5,6** | 14 × 1,0 × 0,5 × 0,8 | `governor.scale=5.60` ✓ |

**Tout réconcilie au centième avec le state.json live.** Le compte a déjà dépassé la cible P1
(11 023 > 11 002) mais reste P1 car `open_days 2 < min_days 4` (FTMO impose 4 jours tradés).
Conséquence directe : **`glide=0.5` est ACTIF — tout le book, USDJPY compris, est sizé à demi-taille**
(verrou de cible), tant que l'equity reste ≥ 80 % de la cible.

---

## 5. Réponse à M4(c) — à ~$11k, USDJPY peut-il être coupé/réduit par l'equity-gate, indépendamment du momentum 12-1 ?

**NON par l'equity-gate MA100.** Cette couche (i) ne s'applique qu'à la **jambe OR**, et (ii)
utilise la **courbe d'equity SIMULÉE de la sleeve OR**, pas l'equity du compte ($11k). Elle ne
touche jamais USDJPY. L'equity de compte **n'entre même pas** dans `build_signals()`.

- **On/off USDJPY** : purement le **momentum 12-1** (`mom>0` ⇒ long ; `mom≤0` ⇒ flat). Indépendant
  de l'equity.
- **Taille USDJPY** : `w_jpy × scale × eq`. L'equity de compte la module via le **gouverneur** :
  - **aujourd'hui** : `glide=0.5` (cible P1 dépassée) ⇒ **USDJPY à demi-taille** ; `taper=1.0`
    (marge au floor 20 % ≫ 2 %) ⇒ **aucune réduction par le floor**.
  - **réduction par le floor** seulement si l'equity retombait vers ~9 200 $ (room < 2 %) — il
    faudrait perdre ~1 800 $ depuis l'equity actuelle. Et c'est le **gouverneur (taper)**, pas
    l'equity-gate MA100.
- **Risque de coupe « indépendamment du momentum »** : oui mais via le **gouverneur**
  (taper→0 près du floor, glide→0,5 près de la cible, margin-cap 60 %), jamais via l'equity-gate
  MA100. À l'equity actuelle, le seul effet actif sur USDJPY hors momentum est `glide=0.5`
  (demi-taille de verrou de cible).

---

## 6. Notes transverses

- **Causalité (T-1)** : toutes les couches portent un `.shift(1)` — `WT.loc[T]` n'utilise que
  des données ≤ T-1 (`signals.py:5-7`). Conforme à la règle « signal à T-1, trade à T ».
- **ON-day** : `ON=1` lundi/mardi (`engine.py:142`) — gère US100/GER40 (pas USDJPY/OR).
- **Equity-gate audit flag** : composant du pipeline auteur, **non spécifié dans le rapport**,
  répliqué dans le cleanroom pour fidélité de calcul (`engine.py:123-124`). À garder en tête si
  un rapport ultérieur prétend que le book OR est « pur TSMOM » : il est en réalité TSMOM ×
  filtre-courbe-MA100.
