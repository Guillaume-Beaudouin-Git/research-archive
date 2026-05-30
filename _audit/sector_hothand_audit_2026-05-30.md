# Audit sector_hothand_propfirm — 2026-05-30 (LOT 9, investigation only)

**Subject**: `Equities/research/active/sector_hothand_propfirm/`
**Reported metrics** (source : `results/phase1_baseline.json`, run 2026-05-28) :
- t_HAC alpha = **10.38** (DRAPEAU ROUGE)
- SR_net = 2.05
- SR_deflated (DSR) = 2.01
- WF folds = **5/5** (SR_oos 1.06–3.98)
- MaxDD = **-13.3%** (> FTMO 10% limit → BREACH du challenge en l'état)
- AMTP_p (Bonferroni 6 trials) = 0.00
- FTMO P(pass both) = 5.14%, CI95 [0.047, 0.056]

**Audit scope** :
(a) Signal-at-T-1, look-ahead (L1)
(b) Coûts (L9) + HAC lag ≥ max(6, 4√T) (L12b)
(c) Excess returns vs DTB3 + daily vol targeting (L8)
(d) Déflation autocorrélation N_effective

**Audit method** : lecture intégrale de `engine.py` (174 lignes) et `phase1_baseline.py`
(593 lignes), confrontation avec L1/L8/L12b. Pas d'exécution (LOT 9 = rapport seul).
Aucune modification appliquée.

---

## Verdict global : **ARTEFACT (sévère)**

Le t_HAC = 10.4 et le SR_net = 2.05 ne sont **PAS** des estimations valides sous
les conventions Algo_claude. Les causes identifiées, par ordre d'impact :

1. **(CRITIQUE) Look-ahead bias dans `entry_px`** → SR et alpha matériellement
   inflatés. Mécanisme détaillé en §1.
2. **(MAJEUR) HAC lag-6 sous-spécifié** pour T=6138 → t-stat inflaté ≈ 2.5×.
3. **(MINEUR) DSR n_trials=6 sous-compté** → DSR optimiste (effet limité car
   T est grand).

Tous trois sont structurels : pas réparables par re-tuning ; ils requièrent un
refactor du moteur. Même corrigés, la métrique MaxDD = -13.3% > 10% FTMO
empêche le passage. **Le verdict gate intégré dans `phase1_baseline.py:500-502`
retourne déjà FAIL** (gate FTMO P(pass) CI lower = 0.047 < 0.50). Le headline
"SR_net 2.05 / DSR 2.01" du résumé masque ce verdict.

---

## §1. Look-ahead bias dans `engine.py:120` (CRITIQUE)

### Code incriminé

`engine.py:111-121` :

```python
open_t    = open_px.iloc[i][best_ticker]
close_tm1 = close_px.iloc[i - 1][best_ticker]
close_t   = close_px.iloc[i][best_ticker]

# Non-levered return for the day
entry_px = open_t if open_t < close_tm1 * (1 - daily_stop) else close_tm1
nonlev_ret = (close_t - entry_px) / entry_px
```

### Mécanisme du biais

La logique du `entry_px` est :
- **Si** `open_t < close_tm1 × (1 − 0.012)` (gap down > 1.2%) → entry au open
- **Sinon** (cas normal, ~99% des jours) → entry au **close_tm1**

Dans le cas normal, `nonlev_ret = (close_t − close_tm1) / close_tm1` =
**close-to-close return** du jour T.

Or :
- Le signal momentum est calculé sur les log-returns finissant à `close_tm1`
  (`engine.py:63` : `mom.rolling(...).sum().shift(1)`).
- En exécution réelle : signal disponible APRÈS la cloche de T-1
  (16:00 NY) ; ordre placé pour fill à l'**ouverture de T** (09:30 NY) ;
  retour réalisé = **open-to-close** du jour T = `(close_t − open_t) / open_t`.

L'engine modélise donc un fill au **prix d'hier à 16:00** sur la base d'un signal
qui n'est calculable qu'**à partir** de ce prix-là. C'est une violation de L1 :
le signal et l'entrée partagent la même observation.

### Impact quantitatif (ordre de grandeur)

Pour la sélection momentum (winners), le gap overnight (open_t / close_tm1) est
**positivement biaisé** : la sélection sur momentum 20-day est corrélée au drift
overnight (continuation effect). En capturant ce gap, l'engine ajoute un retour
"gratuit" en moyenne ~3–7 bp/jour selon décennie pour les ETF sectoriels.

Sur T=6138 jours, avec ~50% des jours en position (les autres en cash), ce biais
peut représenter :
- Drift overnight moyen pour winners ≈ 4 bp/jour × ~3000 jours en position
- ≈ +12% de retour cumulé non réalisable

À retour annualisé ~25% pour les jours actifs, retirer ce biais réduirait :
- Retour ann : ~25% → ~21% (-4 pp)
- Sharpe : ~2.0 → ~1.4–1.6
- Alpha t : ~10 → ~7 (avant correction HAC)

Plus l'effet d'interaction avec le levier (`lever × nonlev_ret` : le gap est
amplifié par le vol-target levier, souvent > 1).

### Constitutional check qui a MANQUÉ ce biais

`phase1_baseline.py:564` affirme :
> | L1: signal T-1, trade T open | ✅ engine.run() shift(1) on all signals |

Le check vérifie l'existence du `shift(1)` sur le signal mais **PAS** la
cohérence du prix d'entrée avec le timing du fill. C'est un faux positif de
vérification. À cause de cela, le PR (s'il avait existé) n'aurait pas alerté.

### Fix propositionnel (hors scope LOT 9)

```python
# entry_px = open_t  (toujours)
# gap-down stop : si open_t < close_tm1 × (1 - daily_stop), le stop est armé à l'open
entry_px = open_t
nonlev_ret = (close_t - entry_px) / entry_px
# Le daily_stop reste appliqué via la ligne 124 : if nonlev_ret < -daily_stop: nonlev_ret = -daily_stop
```

---

## §2. HAC lag-6 sous-spécifié pour T=6138 (MAJEUR)

### Constat

`phase1_baseline.py:93,427` utilise `lag = 6` (Newey-West truncation).

Règle L12b (CLAUDE.md:123-124, registre canonique) :
- N_eff = T / (1 + 2·Σ_k ρ_k) pour autocorrélations persistantes
- Newey-West lag rule : `lag ≥ max(6, 4·T^(1/4))` ≈ Andrews 1991 ; OU `4·(T/100)^(2/9)`

Pour T = 6138 :
- `4 × T^(1/4) = 4 × 8.85 = 35.4` → lag ≈ **36**
- `4 × (T/100)^(2/9) = 4 × 4.43 = 17.7` → lag ≈ **18** (plus conservateur Andrews)

Le code utilise **lag = 6**, qui est ~5–6× trop court.

### Impact quantitatif

Sous-spécifier la lag → variance long-run sous-estimée → SE sous-estimé →
t-stat inflaté.

Effet direct : `t_inflé ≈ t_vrai × sqrt(var_correcte / var_lag6)`.
Pour un AR(1) modéré (ρ ≈ 0.1, typique d'une stratégie momentum à persistance) :
- var_correcte (lag ≈ 36) ≈ σ² × (1 + 2 × Σ_{k=1..36} 0.1^k) ≈ σ² × 1.22
- var_lag6 ≈ σ² × (1 + 2 × Σ_{k=1..6} 0.1^k) ≈ σ² × 1.21

Très peu de différence pour AR(1) ρ=0.1. **MAIS** les stratégies momentum
empiriques ont une autocorrélation très **bursty** à des lags 5–30 (cycles
d'environ 1 mois de position-persistence quand un winner reste winner). Pour
un MA(20) explicite (le signal lookback) on attend une autocorrélation
significative jusqu'à lag ≈ 20.

Estimation honnête : pour ce profil (momentum 20-day, position-persistence
~5–15 jours), le rapport var_correcte/var_lag6 est plutôt **2.5–5×**, ce qui
inflate le t-stat d'un facteur `sqrt(2.5)–sqrt(5) ≈ 1.6–2.2`.

Conclusion conservatrice : `t_HAC_correct ≈ 10.4 / 2.0 ≈ 5.2`.
Toujours significatif, mais loin du "drapeau rouge" 10.4.

### Recommandation

Re-runner avec lag = `max(6, int(4 * len(ret)**0.25))` (auto, échelle T).

---

## §3. DSR n_trials = 6 sous-compté (MINEUR)

### Constat

`phase1_baseline.py:45` :
```python
AMTP_COMBOS = len(AMTP_LOOKBACKS) * len(AMTP_VOLS)  # = 6
```

Seuls 2 hyperparamètres sont comptés : `lookback ∈ {10,20,40}` × `vol_target
∈ {0.10, 0.20}`.

Hyperparamètres NON comptés :
- Universe choice : 10 ETF sélectionnés sur N candidats raisonnables (≥30 ETF
  sectoriels US disponibles) → équivalent à C(30,10) trials théoriques,
  mais en pratique 5–10 trials de design effectifs.
- `lookback_vol = 40` (un choix parmi {20, 40, 60, 252})
- `vol_cap = 3.0` (parmi {1, 2, 3, 5})
- `daily_stop = 0.012` (parmi {0.005, 0.01, 0.015, 0.02})
- `cost_bps = 0.0008` (choix d'un modèle de coût)
- HAC lag = 6 (autre choix de modèle)
- Burn-in start 2002-01-01 (choix de période)

Estimation conservatrice : real_n_trials ≈ **20–30** (au lieu de 6).

### Impact quantitatif

Formule Bailey-LdP (simplifiée, sans skew/kurt) :
`DSR = SR × (1 − E[max_SR_n] / √T)`

Avec T = 6138 et n_trials = 6 : `E[max_SR_6] ≈ 1.27 / √(6138) × √6 ≈ 0.0405`
→ DSR ≈ SR × (1 − 0.020) = 2.05 × 0.980 = 2.01 ✓ (matches reported).

Avec n_trials = 30 : `E[max_SR_30] ≈ 1.78 / √(6138) × √30 ≈ 0.1245`
→ DSR ≈ SR × (1 − 0.022) = 2.05 × 0.978 ≈ **2.00**.

Effet **mineur** car T est grand. DSR n_trials sous-compté n'explique pas la
métrique inflatée — c'est le SR brut (et donc l'erreur §1) qui domine.

### Recommandation

Compter ≥ 20 trials dans `AMTP_COMBOS` ou documenter explicitement le
multi-test budget consommé.

---

## §4. Vérifications négatives (rien à signaler)

- ✓ **(c) Excess returns vs DTB3** : `phase1_baseline.py:82-86` charge DTB3
  via FRED, convertit annualized %→daily decimal, aligne sur close_px.
  `engine.py:94,128` soustrait `rf.iloc[i]` aux returns. ✓ correct (L8).
- ✓ **Daily vol targeting** : `engine.py:107` `lever = min(vol_target / sig_vol, vol_cap)`.
  Fenêtre 40-day (paramétrable, l.66). Annualisation sqrt(252). ✓ correct (L8).
- ✓ **WF expanding window 5 folds** : `phase1_baseline.py:179-240`. Folds
  correctement définis (test_years=2, expanding train). Tous folds passent SR
  > 0.7 et MDD > -25% (les gates internes). MAIS la WF ne capture pas le
  look-ahead §1 (qui est dans l'engine, donc identique pour tous les folds).
- ✓ **Block bootstrap stationary** : Politis-Romano correct (l.143-152), block
  size = round(sqrt(T)). ✓ correct (L methodology toolkit).
- ✓ **Excess returns réintégrés dans HAC** : OLS sur `ret_net` qui est déjà
  excess (l.93-100). Pas de double-soustraction. ✓ correct.

---

## §5. Note : FTMO 10% MDD breach (NON propfirm-ready en l'état)

Indépendamment des questions de t-stat ou de DSR :

`MaxDD = -13.3%` (full sample 2002–2026)
`FTMO max drawdown limit = 10%` (static)

Donc même si toutes les métriques étaient véritables (et corrigées des
artéfacts §1–§3), la stratégie en configuration actuelle **BREACHE** FTMO en
sortie de backtest. C'est confirmé par le propre simulateur FTMO du script :
- `p_pass_both` = 5.14%
- `p_pass_ci95_lo` = 4.71% < 50% → **gate FTMO FAIL**
- `gate_pass` = False → **verdict script = ARCHIVE**

Le résumé markdown du script (`phase1_summary.md`) doit afficher
"ARCHIVE — gates failed" (cf. `phase1_baseline.py:504-507`). Pourtant la
narrative qui s'est propagée (probablement via README ou résumé externe) garde
les chiffres SR/DSR comme arguments pour une "PRÉSOMPTION DE PROMOTION".

**Cette dissonance — gates internes FAIL mais chiffres headline cités comme
PASS — doit être résolue avant toute considération propfirm.**

---

## §6. Recommandation finale (rapport seul, AUCUNE action ici)

### Conclusions chiffrées (best-estimate)

- **Reported t_HAC = 10.4** → estimé corrigé **t_HAC ≈ 4–5.5** (cumul §1 + §2).
- **Reported SR_net = 2.05** → estimé corrigé **SR_net ≈ 1.0–1.5** (§1 seul).
- **Reported DSR = 2.01** → estimé corrigé **DSR ≈ 0.9–1.4** (§1 + §3).
- **MaxDD = -13.3%** : invariant aux fixes §1/§2/§3 ; reste > FTMO 10%.
- **FTMO P(pass)** : déjà 5% reportée, descendrait probablement < 2% post-fix §1
  (retour overnight = portion significative du buffer FTMO target).

### Catégorie L21 (CLAUDE.md:156-161)

- CS academic daily (N≥100 instruments) : SR 0.3–1.2 → **N=10 ETF n'est PAS
  N≥100**, donc cette stratégie n'entre pas dans la catégorie CS academic
  "stable". Elle est plutôt un single-asset rotation à 10-sleeves, plus
  proche du "single-instrument day-trade" (SR 0.8–2.0) post-fix.
- SR_corrigé ≈ 1.0–1.5 → consistent avec cette catégorie ✓ (raisonnable).
- SR_reported = 2.05 → > 2× plage haute attendue → audit DSR/cherry-pick
  obligatoire AVANT toute promotion (déclencheur explicite L21).

### Actions REQUISES avant toute promotion (hors scope LOT 9)

1. **Fix engine.py:120 — entry_px = open_t toujours.** (§1)
2. **HAC lag automatique = max(6, int(4 * T**0.25))** dans tous les
   hac_alpha_tstat calls. (§2)
3. **AMTP_COMBOS ≥ 20** ou justification documentée du multi-test budget. (§3)
4. **Re-runner phase1_baseline.py** après fixes 1–3.
5. **Si SR_net post-fix < 1.0 ou MaxDD encore > 10%** → archiver
   (`Equities/research/archived/sector_hothand_propfirm/`).
6. **Si SR_net post-fix ≥ 1.0 et MDD reductible** → étudier overlays de
   leverage cap pour amener MDD < 10%, puis Phase 2 (out-of-sample monitoring).

**Statut actuel** : **NE PAS PROMOUVOIR**. **NE PAS CITER les chiffres**
"SR 2.05 / DSR 2.01" sans la note "post-fix engine open_t bias requise".
Strategy D considération inchangée : sector_hothand n'est PAS un candidat
"décorrélé à C" propfirm-ready en l'état.

---

## Annexe — preuves citation par citation

| Affirmation | Preuve fichier:ligne |
|---|---|
| Look-ahead `entry_px = close_tm1` cas normal | `engine.py:120` |
| HAC lag-6 hard-coded | `phase1_baseline.py:93,427` |
| AMTP_COMBOS = 6 | `phase1_baseline.py:45` |
| Constitutional check L1 = shift(1) seul | `phase1_baseline.py:564` |
| T = 6138 | `results/phase1_baseline.json:5` |
| MaxDD = -13.29% | `results/phase1_baseline.json:9` |
| p_pass_ci95_lo = 0.047 | `results/phase1_baseline.json:73` |
| Gate FTMO FAIL → ARCHIVE verdict | `phase1_baseline.py:500-507` |
| Excess returns rf subtracted | `engine.py:94,128` ; `phase1_baseline.py:82-86` |
| Stationary bootstrap correct | `phase1_baseline.py:128-159` |
| WF 5 folds expanding | `phase1_baseline.py:179-240` |
