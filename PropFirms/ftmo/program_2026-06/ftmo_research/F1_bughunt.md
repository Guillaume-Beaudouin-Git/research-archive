# F1 Bug Hunt — Verdict

**TL;DR — F1 EST UN ARTEFACT LOOK-AHEAD.** Confirmé par diagnostic ciblé. Bug localisé : `time_to_break_5min` est mal calculé pour les short trades (utilise `iu` au lieu de `idn`), créant une feature forward-looking sur 48.6% du dataset. Edge corrigé : Δ = **−0.025R** (légèrement négatif). **La validation NQ/DAX 2008-2025 n'est PAS justifiée.**

| Test | Hypothèse | Résultat |
|---|---|---|
| Delay 1-bar / 2-bar / next-open | Same-bar fill ? | F1 advantage stable (+0.30R) → **PAS un same-bar artefact** |
| Permutation placebo | Leak pipeline ? | z=11.6, p=0 → **PAS un leak pipeline structurel** |
| **Direction split LONG/SHORT** | **Direction misalignment ?** | **LONG F1 Δ = 0.001R ; SHORT buggy F1 Δ = +0.715R ; SHORT corrected = −0.053R** → **BUG CONFIRMÉ** |
| Inspection manuelle | Fill prices atteignables ? | Confirme: pour fast longs, NEXT_OPEN slip ≤ 20pts (visible mais pas catastrophique) |

**Le bug : `trade_features.py:180`** :
```python
time_to_break = (iu if iu < 10**9 else idn) - 0  # WRONG for direction=-1
```
Pour un short trade (idn<iu), le trade trigger est `idn`, mais la feature stocke `iu` (la up-break time observée APRÈS l'entry). Fix correct :
```python
time_to_break = bi - or_bars   # = iu for long, = idn for short, always correct
```

**Conséquence sur les rapports antérieurs** :
- `TRADE_MICROSTRUCTURE_filter.md` (filtre F1, "+22 à +45pt p_funded") → **INVALIDE**
- `F1_verification.md` (3 vérifs passées, DSR 3.49) → **les 3 vérifs étaient nécessaires mais aveugles au bug de direction**
- `OPTIM_ORB_propfirm.md` et `OPTIM_ftmo_2step_uncapped.md` (sizing optim + gate régime) → **toujours valides** (n'utilisent pas time_to_break)
- `AUDIT_VERDICT_ftmo_orb.md` (verdict NO-GO original) → **toujours valide** (baseline non affecté)
- **Le baseline edge ORB (+0.10R) est intact** — la feature ttb buggée ne contamine que le filtre, pas l'execution baseline.

---

## 1. Audit du code d'exécution (Suspect #1)

`audit/trade_features.py` ligne 226-228 et `audit/orb_core.py` ligne 110-112 :
```python
if delay_bars > 0:
    ...
    entry = O[entry_bar]   # next-bar-open
else:
    entry = level          # SAME-BAR fill at level (default)
```

**Mode par défaut = same-bar fill at level.** En live, ce n'est implementable qu'avec stop-buy/stop-sell orders placés à or_hi/or_lo AVANT le break. La fill prix est exactement le level seulement si la barre passe lentement à travers ; en pratique le break gappe et on slip.

→ Source potentielle d'inflation, MAIS pas le coupable principal (cf. test §2).

---

## 2. Test décisif #1 — Clean next-bar-open delay

`audit/f1_bughunt_delay.py` → `f1_bughunt_delay_test.csv` + `f1_bughunt_delay_output.txt`.

Re-extract trades avec 4 modèles d'exécution :
- **EXEC_0** : same-bar fill at level (mode actuel buggy)
- **EXEC_DELAY_1** : break détecté via H/L, entry next-bar-open
- **EXEC_DELAY_2** : break détecté via H/L, entry à bar+2 open
- **EXEC_NEXT_OPEN** : break détecté via close-confirmation, entry bar+1 open (le plus strict)

### Résultats : F1 advantage stable across exec models

| Exec model | baseline meanR | F1 meanR | F1 advantage (F1 − base) |
|---|---:|---:|---:|
| EXEC_0 (buggy same-bar) | +0.103 | +0.436 | +0.333 |
| EXEC_DELAY_1 | +0.081 | +0.420 | +0.339 |
| EXEC_DELAY_2 | +0.070 | +0.398 | +0.328 |
| **EXEC_NEXT_OPEN (clean)** | **+0.058** | **+0.355** | **+0.297** |

**Findings** :
- Baseline meanR chute de +44% (0.103 → 0.058) sous clean exec.
- F1 meanR chute de seulement -19% (0.436 → 0.355).
- **L'avantage F1 (F1 − baseline) reste structurellement présent (+0.30R) sur tous les modèles**.
- **Conclusion préliminaire** : F1 ne semble PAS être un same-bar artefact pur — c'était même contre-intuitivement *plus* attrayant sous clean exec (ratio F1/baseline plus élevé).

→ **Faux positif** : le delay test ne détecte pas ce bug parce que le bug n'est pas dans le fill, mais dans la **définition de la feature**.

---

## 3. Test décisif #2 — Placebo permutation

`audit/f1_bughunt_placebo.py` → `f1_bughunt_placebo_output.txt`.

Permutation de `time_to_break_5min` aléatoirement à travers les trades (1000 perms), puis re-application du filtre F1.

| Dataset | Observed F1 meanR | Perm mean | Perm std | z-score | p-value |
|---|---:|---:|---:|---:|---:|
| EXEC_0 buggy | +0.436 | +0.103 | 0.029 | **11.65** | 0.0000 |
| EXEC_NEXT_OPEN clean | +0.355 | +0.057 | 0.026 | **11.53** | 0.0000 |

**Le placebo PASSE éclatamment (z>11, 0/1000 permutations ≥ observed).**

→ **MAIS deuxième faux positif** : le placebo teste si `time_to_break_5min` est prédictif au-delà du hasard. Il ne teste **pas** si la prédiction vient d'un leak de la définition même de la feature. Si ttb encode du look-ahead pour les short trades, ce look-ahead reste lié à R après permutation casseé (parce que c'est l'apparemment de la feature qui est leakée, pas son contenu).

Le placebo permute la **colonne** ttb sans toucher au **calcul** de ttb. Le bug est en amont.

---

## 4. Test décisif #3 — Inspection manuelle (suspect #2-3, direction)

`audit/f1_bughunt_inspect.py` → `f1_bughunt_inspect_output.txt`.

8 fast winners + 8 slow losers imprimés bar-par-bar.

### Découverte critique sur US100 2023-11-23

Trade dans le dataset : `direction=-1` (short), `ttb=11`, OR=[16008.4, 16022.9], R=−1.21.

Inspection des bars :
- Bar 5 (idx 5) = dernière OR bar.
- Bar 6 (17:00) : low=16007.8 < 16008.4 = or_lo → **down-break sur bar 6 (idn=0)**
- Bar 17 (17:55) : high=16025.9 > or_hi=16022.9 → up-break sur bar 17 (iu=11)
- iu=11 > idn=0 donc direction=-1, bi=or_bars+idn=6 (= bar 6, trade trigger)
- **MAIS le dataset affiche ttb=11** (= iu, pas idn!)

### Le code coupable (trade_features.py:180)

```python
# 4. Time-to-break in 5-min bars (0 = broke immediately after OR)
time_to_break = (iu if iu < 10**9 else idn) - 0  # bars after OR close
```

**Pour les short trades, cette ligne stocke `iu` (UP-break time) comme feature, alors que le trade est triggered par `idn` (DOWN-break time).** `iu` est observable APRÈS l'entry (parce que iu > idn). C'est du **look-ahead pur**.

**Économie du look-ahead** :
- Short avec petit iu (= up break arrive vite après le short) → marché se retourne → loss.
- Short avec grand iu (= pas de up break pendant longtemps après le short) → down trend continue → win.

Donc faible iu prédit perte sur shorts, fort iu prédit gain — **mais c'est de l'info post-entry**, non utilisable en live.

Pour les **long trades**, iu=trade trigger time = correct par hasard (parce que iu<idn pour les longs).

---

## 5. Test décisif #4 — Direction split (le test qui révèle TOUT)

`audit/f1_bughunt_direction_bug.py` → `f1_bughunt_direction_bug.csv`.

Re-extract trades avec à la fois `ttb_buggy` (= ligne 180 actuelle) et `ttb_correct` (= `bi - or_bars`, le vrai trigger time). Application de F1 ≤ médian par subset.

### Distribution du bug

- Trades total : 3056
- Long : 1570 (51.4%)
- Short : 1486 (48.6%)
- **Trades avec ttb_buggy ≠ ttb_correct : 709 = 23.2% du total** (= 47.7% des shorts)

(Pour les autres 53% des shorts, iu était égal à idn ou idn était l'unique break — donc ttb_buggy = ttb_correct par accident.)

### Effet F1 par direction et définition

| Subset | ttb def | base meanR | F1 meanR | **Δ F1−base** | hit base | hit F1 |
|---|---|---:|---:|---:|---:|---:|
| ALL | buggy | +0.103 | **+0.436** | **+0.333** | 41.8% | 53.0% |
| ALL | **correct** | +0.103 | **+0.078** | **−0.025** | 41.8% | 40.0% |
| LONG | buggy = correct | +0.127 | +0.127 | **+0.001** | 44.8% | 43.8% |
| SHORT | **buggy (LOOK-AHEAD)** | +0.079 | **+0.793** | **+0.715** | 38.6% | 63.0% |
| SHORT | **correct** | +0.079 | +0.025 | **−0.053** | 38.6% | 35.9% |

### Verdict §5 (DÉCISIF)

1. **LONG only** : F1 Δ = +0.001R sous les deux définitions. ttb correctement aligné pour les longs → **aucune information utile dans ttb**.
2. **SHORT only buggy** : F1 Δ = **+0.715R** — l'edge spectaculaire vient ENTIÈREMENT des shorts avec ttb mal aligné.
3. **SHORT only correct** : F1 Δ = **−0.053R** (légèrement négatif). La vraie ttb (= idn) n'a aucun pouvoir prédictif positif.
4. **ALL trades correct** : F1 Δ = **−0.025R**. Le filtre est marginalement nuisible.

**100% de "l'edge" F1 vient du look-ahead sur les shorts.**

---

## 6. Pourquoi les 3 vérifs précédentes ont été fooled

### F1_verification.md §1 — Orthogonalisation
**ttb (avec bug) corr or_range = 0.02** → vrai, mais ne détecte pas que ttb est look-ahead. La feature pollutionne le coefficient sans corréler avec or_range.

### F1_verification.md §2 — Slip points-fixes
F1 buggé survit le slip parce que **les shorts avec look-ahead gardent leur edge artificiel quel que soit le slip** — c'est un edge "fantôme" qui n'existe pas en live, donc le slip ne l'affecte pas.

### F1_verification.md §3 — DSR Bailey-LdP
Le DSR corrige le multiple testing (combien de stratégies on a essayées). Il ne corrige PAS un edge issu d'un leak de feature. Un Sharpe authentiquement élevé causé par un leak survit la déflation parce que le DSR ne sait pas qu'il y a leak.

→ **Les 3 checks étaient méthodologiquement corrects mais structurellement aveugles à ce type de bug**. Le test qui aurait fallu : split par direction + recompute ttb correctement.

---

## 7. Impact sur les rapports antérieurs

| Rapport | Affecté ? | Action |
|---|---|---|
| `AUDIT_VERDICT_ftmo_orb.md` | NON | Baseline edge intact, conclusions valides |
| `OPTIM_ORB_propfirm.md` (sizing + gate) | NON | N'utilise pas time_to_break |
| `OPTIM_ftmo_2step_uncapped.md` (uncapped sizing + rv20 gate) | NON | N'utilise pas time_to_break |
| **`TRADE_MICROSTRUCTURE_filter.md`** | **OUI — INVALIDÉ** | Filtre F1 inutilisable, p_funded affichés erronés |
| **`F1_verification.md`** | **OUI — INVALIDÉ** | Les 3 vérifs étaient nécessaires mais pas suffisantes |

### Chiffres à NE PAS croire

- F1 "mean R × 4.2" → 0.10 → 0.44 est en réalité 0.10 → 0.08 (avec ttb correct) → **filtre fait perdre 0.025R/trade**
- F1 "p_funded 100% à 0.50% sizing" → faux, c'est ~78% (le baseline non-filtré)
- F1 "+91pt sous 3× slip" → faux, c'est l'edge fantôme qui ne se dégrade pas avec slip
- F1 "DSR déflaté 3.49" → faux Sharpe alimenté par look-ahead
- Régime fold décomposition (TRADE_MICROSTRUCTURE §5) "MaxDD -11% → -3% en chop" → faux, c'est l'edge fantôme qui sauve apparemment le chop

### Chiffres à GARDER

- Baseline meanR +0.10R, Sharpe daily ann 1.54 → confirmé (par f1_bughunt_delay et f1_bughunt_direction_bug, baselines convergent).
- Baseline p_funded uncapped à 0.50% = 78%, à 0.75% = 67.6%, à 1.25% = 55% → confirmés.
- Gate régime rv20_mid +16pt sur uncapped → indépendant du bug ttb, confirmé.
- DSR baseline déflaté = 0.70 à n_trials=18 → reste valide (échoue PROPFIRM_PASS 1.0).

---

## 8. Verdict final et leçons

### F1 est un artefact look-ahead — fix simple, fin de l'edge

```python
# WRONG (current trade_features.py:180):
time_to_break = (iu if iu < 10**9 else idn) - 0

# CORRECT:
time_to_break = bi - or_bars
# (= iu for long trades, = idn for short trades, always = real trigger bar after OR)
```

**Edge F1 corrigé : Δ ≈ −0.025R (le filtre nuit légèrement).** Le bug a inflated artificially. **F1 n'est pas un edge.**

### Conséquence opérationnelle

1. **NE PAS valider F1 sur 2008-2025**. C'était l'objectif du gate de vérification précédent — gate maintenant échoué.
2. **Revenir au verdict OPTIM_ftmo_2step_uncapped (0.50% + rv20_mid gate = 95.5%)** comme meilleur cas in-sample. Toujours soumis aux caveats N≈1 et data extension.
3. **Mettre à jour CLAUDE.md** : ajouter une leçon L20bis sur les features direction-asymétriques (un classique des breakouts).

### Leçons méthodologiques

1. **L19 (ablation) avait raison de demander un test décisif**, mais le delay test était **insuffisant** : un bug de définition de feature passe à travers.
2. **DSR aveugle au look-ahead** : confirme le principe que DSR corrige multiple testing only — pas leakage. Pour leakage, il faut des tests structurels (delay, direction-split, scramble-then-recompute).
3. **Magnitude IS the symptom** : raw Sharpe 4.39 sur un single-feature ORB intraday était le drapeau rouge. L'utilisateur a eu raison de demander le bug hunt.
4. **Direction asymétrie dans les features de breakout** est un pattern à pré-tester systématiquement : tout breakout strategy a deux directions, et toute feature peut être direction-asymétrique. Le test "split par direction" devrait être obligatoire avant tout claim d'edge intraday breakout.

### Recommandation actionnable

- **Revert à 0.50% sizing + rv20_mid gate** (95.5% p_funded in-sample).
- **Continuer paper-trade** sur cette config, **sans** filtre F1.
- **Mettre à jour CLAUDE.md** avec :
  - L25 : "Features de breakout strategy doivent être validées par split-by-direction. Un edge qui ne survit pas la séparation long/short est probablement direction-asymétrique = look-ahead."
- **Fix le code** `trade_features.py:180` pour les analyses futures (la feature reste utile correctement définie comme pure descripteur, mais pas pour filter).
- **Garde le dataset corrigé `f1_bughunt_trades_with_both_ttb.parquet`** pour référence.

---

## 9. Reproductibilité

| Script | Sortie |
|---|---|
| `audit/f1_bughunt_delay.py` | `f1_bughunt_delay_test.csv` + output txt |
| `audit/f1_bughunt_placebo.py` | `f1_bughunt_placebo_output.txt` |
| `audit/f1_bughunt_inspect.py` | `f1_bughunt_inspect_output.txt` |
| **`audit/f1_bughunt_direction_bug.py`** | **`f1_bughunt_direction_bug.csv` + `f1_bughunt_trades_with_both_ttb.parquet`** |

Tous seeded, déterministes. `cd audit && /usr/bin/python3 f1_bughunt_*.py`.

---

*Bug hunt réalisé 2026-06-01 — Claude Code (Opus 4.7 1M ctx). Verdict: F1 est un artefact look-ahead par bug de direction-misalignment. L'edge "+0.30R" est entièrement fictif. NE PAS valider sur data étendue.*
