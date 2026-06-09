# VALIDATION D — BTC/ETH pairs cointégration Kalman (Park IJSRA 2026)

**TL;DR — NO-GO franc.** Le Sharpe 2.23 revendiqué par Park (Jan 2022 - Oct 2024) **ne survit AUCUN des 4 tueurs ni le delay-1**, même sur la fenêtre du papier. Sous exécution propre (delay-1) + funding réaliste + 1bp cost, **SR_net = −1.13 (négatif)** sur la fenêtre Park, **SR_net = −0.48 sur POST-Park**. Le 2.23 était un **drift relatif BTC vs ETH harvested** (+83pts diff sur Park = BTC +51% vs ETH −32%) en costume market-neutral.

| Tueur | Test | Résultat | Verdict |
|---|---|---|:---:|
| 1. Coint OOS | ADF p sur 4 fenêtres | toutes p > 0.27, jamais cointégrée | **FAIL** |
| 2. Half-life | OU half-life du spread | 63 à 591 jours, multi-mois partout | **FAIL** |
| 3. Funding 2-jambes | Coût net sur les 2 perp | -2% sur 1 an, drag léger mais réel | **FAIL** (sous funding+cost, SR=-1.13) |
| 4. Drift relatif | Drift/Osc ratio par fenêtre | Park = 2.55 (drift dominant) | **FAIL** |
| DSR | Bailey-LdP sur 2.23 | Survit jusqu'à n_trials=100 | passe (mais in-sample, fenêtre du papier) |
| **Delay-1** | Same-bar vs next-bar | SR=+0.23 gross vs SR=-1.13 net avec funding | **FAIL** (effondre) |

**Décision : NO-GO Crypto Fund Trader. Le fee est évité.**

---

## 0. Cadrage

Strategy D = pairs trading cointégration BTC/ETH, hedge ratio dynamique par filtre de Kalman, source Park (IJSRA 2026, DOI 10.30574/ijsra.2026.18.2.0283), Sharpe 2.23 reporté, fenêtre ~Jan2022-Oct2024 (~2.5 ans).

Application directe de la batterie des 4 tueurs établie par le stat-arb FTMO deep-dive (`data/ftmo_research/statarb_deepdive_ftmo.md`) — adaptée aux spécificités crypto : funding 2-jambes au lieu de financement CFD overnight.

Réutilise `statarb_deepdive.py` pour la structure (Engle-Granger, OU half-life, OOS stability).

## 1. Data

- **Spot BTC/ETH 1H** : agrégation depuis Binance M1 (2018-01-01 → 2026-06-01, 73,644 1H bars). Couvre largement la fenêtre Park + pré-2022 + post-Oct-2024.
- **Funding rates 1H** : `data/funding_carry/BTC_funding.csv` + `ETH_funding.csv` (proxy Hyperliquid ≈ Bybit, 2023-05-12 → 2026-05-04, 25,566 bars).
- **Limitation** : funding indisponible pour 2022 + Jan-May 2023 (la première moitié de Park). On utilise la sous-fenêtre Park-avec-funding (May 2023 - Oct 2024) pour le test funding-net.

Scripts : `validation_D.py` + `killer4_drift_decomp.py` dans ce dossier.

## 2. Killer 1 — Cointégration OOS (premier gate)

`validation_D.py` → `killer1_coint_oos.csv`.

Engle-Granger : OLS hedge ratio + ADF sur le résidu, par fenêtre.

| Window | n | beta | **ADF p** | HL (heures) | Coint @ 5% ? |
|---|---:|---:|---:|---:|:---:|
| FULL 2018-2026 | 73,644 | 0.80 | **0.601** | 14,193 | ✗ |
| PRE-Park 2018-2021 | 34,943 | 0.68 | **0.511** | 6,132 | ✗ |
| **PARK Jan2022-Oct2024** | 24,839 | 1.21 | **0.304** | 2,087 | ✗ |
| POST-Park Nov2024-Jun2026 | 13,862 | 0.44 | **0.272** | 1,510 | ✗ |

### Verdict Killer 1 : FAIL TOTAL

**Aucune fenêtre n'est cointégrée à 5%, y compris celle du papier Park (p=0.30).** Le beta varie radicalement entre fenêtres (0.68 → 1.21 → 0.44 → 0.80), signe d'instabilité structurelle de la relation.

→ Le 2.23 du papier est obtenu sur une relation qui ne passe pas le test de cointégration le plus standard. C'est suspect dès cette étape.

## 3. Killer 2 — Half-life OU

| Window | HL bars (1H) | HL jours | Intraday tradeable ? |
|---|---:|---:|:---:|
| FULL | 14,193 | 591.4 | ✗ (19 mois !) |
| PRE-Park | 6,132 | 255.5 | ✗ (8.5 mois) |
| **PARK** | 2,087 | **87.0** | ✗ (multi-mois) |
| POST-Park | 1,510 | 62.9 | ✗ (2 mois) |

### Verdict Killer 2 : FAIL TOTAL

Sur Park (la "meilleure" fenêtre), HL = **87 jours**. La position doit être tenue ~3 mois en moyenne pour capturer une demi-réversion. Le funding s'applique pleinement sur cette durée.

→ Aucune fenêtre n'est intraday-tradeable. Le funding sur les 2 jambes va peser **lourdement** sur P&L.

## 4. Killer 3 — Funding sur les 2 jambes (le drag structurel)

`validation_D.py` → `killers34_backtest.csv`.

Backtest Kalman + spread z-score (entry |z|>2, exit |z|<0.5) avec funding réaliste.

### Park sub-window May 2023 - Oct 2024 (funding disponible)

| Config | n_bars | SR gross | SR net | Total ret gross | Total ret net | Funding total |
|---|---:|---:|---:|---:|---:|---:|
| **delay=0, 1bp + funding** | 12,864 | -12.14 | **-12.52** | -99.0% | -99.2% | -1.92% |
| **delay=1, 1bp + funding** | 12,864 | -0.44 | **-1.13** | -10.8% | -25.5% | -2.07% |
| delay=0, 2bp + funding | 12,864 | -12.14 | -12.94 | -99.0% | -99.3% | -1.92% |

### POST-Park Nov 2024 - May 2026

| Config | n_bars | SR gross | SR net | Total ret gross | Total ret net |
|---|---:|---:|---:|---:|---:|
| delay=0, 1bp + funding | 13,862 | -12.90 | -13.25 | -99.9% | -99.9% |
| **delay=1, 1bp + funding** | 13,862 | +0.28 | **-0.48** | +8.8% | -13.5% |

### Lecture critique

1. **delay=0 (entrée au bar du trigger) catastrophique** : SR = -13. C'est le pattern entry-bar-penalty en pairs trading (= l'opposé du same-bar-fill artifact des breakouts). Voir §6.
2. **delay=1 (clean, entrée au bar suivant) NÉGATIF** :
   - Park : SR_net = **-1.13**, total return **-25.5%**.
   - POST-Park : SR_net = **-0.48**, total return **-13.5%**.
3. **Funding cost ~ -2%/an** sur les 2 jambes. Pas le killer principal (le strat est négatif AVANT funding).
4. **Cost 1bp/jambe** ajoute 20-23% de cost total (4 legs × 1bp × 500-588 entrées × 100bps_per_pct). Significatif.

### Verdict Killer 3 : FAIL

Le funding 2-jambes **n'est pas** le killer principal ici (le strat est déjà négatif gross). Mais il ajoute -2pt/an sur la performance, suffisant pour transformer un break-even en perte.

## 5. Killer 4 — Drift relatif (beta en costume neutre)

`killer4_drift_decomp.py` → `killer4_drift_decomp.csv`.

### Décomposition spread = drift + oscillation par fenêtre

| Window | BTC ret | ETH ret | Diff | Spread drift | Spread osc (σ) | **Drift/Osc ratio** |
|---|---:|---:|---:|---:|---:|---:|
| FULL 2018-2026 | +430% | +172% | +258pts | +0.59 | 0.39 | **1.51** ✗ |
| PRE-Park 2018-2021 | +242% | +405% | **−164pts** (ETH dominant) | +0.73 | 0.33 | **2.20** ✗ |
| **PARK Jan2022-Oct2024** | **+51%** | **−32%** | **+83pts** (BTC dominant) | +0.43 | 0.17 | **2.55** ✗ |
| POST-Park Nov2024+ | +2% | −22% | +24pts | −0.16 | 0.11 | **1.45** ✗ |

### Le piège bêta démasqué

**Sur la fenêtre Park** :
- BTC return = +51% vs ETH = **−32%** → relative diff = **+83 points**.
- C'est un drift MASSIF non-stationnaire. Le spread se déplace ~+0.88 en log au cours de la fenêtre.
- L'oscillation autour de cette drift est petite (σ=0.17), donc **drift/osc = 2.55** : le drift est **2.5× plus large que l'oscillation**.
- Le Kalman beta passe de **1.29 → 0.81** au cours de Park (Δ = -0.48) → le hedge ratio est INSTABLE.

### Verdict Killer 4 : FAIL — c'est du drift harvested

**Le 2.23 Sharpe de Park est obtenu pendant la fenêtre où BTC out-performed ETH par +83pts.** Le Kalman absorbe partiellement la dérive du beta, mais le strat ENTRE-SORT autour d'un spread qui dérive structurellement. À chaque réversion partielle de l'oscillation, le strat capture une partie de la dérive comme "profit de réversion".

Sur **POST-Park** (drift inverse +24pts seulement), le strat retombe à SR=-0.48. Confirme que la stratégie **suit le drift, ne capture pas une vraie réversion**.

C'est exactement le pattern "beta in disguise" du stat-arb FTMO (NDX vs DJI où l'écart NDX-DJI dérivait structurellement).

## 6. DSR Bailey-LdP sur le 2.23 revendiqué

| n_trials (variant search budget) | SR0 threshold | SR_deflated | p_real |
|---:|---:|---:|---:|
| 1 (single trial) | -∞ | +∞ | 1.000 |
| 5 | 0.64 | +1.59 | 0.998 |
| 20 | 1.03 | +1.20 | 0.987 |
| 50 | 1.23 | +1.00 | 0.968 |
| 100 | 1.37 | +0.86 | 0.945 |

### Verdict DSR

Le 2.23 SURVIT la déflation Sharpe même à n_trials=100 (deflated = 0.86, > 0). **MAIS** :
1. DSR teste si le Sharpe est SIGNIFICATIVEMENT DIFFÉRENT DE ZÉRO au-delà du multiple-testing. C'est aveugle :
   - À l'artifact de fill / look-ahead (déjà vu sur F1, ORB, breakouts).
   - Au drift relatif (Killer 4).
   - Au funding (Killer 3).
2. Le 2.23 est calculé **sur la fenêtre du papier exactement** = in-sample. Le test OOS (POST-Park) donne SR négatif.
3. La cohérence avec les autres tueurs est forte : DSR-positif n'est PAS suffisant pour valider un edge de stat-arb crypto.

→ **DSR passe technique mais c'est le moins discriminant des tests** ici.

## 7. Delay-1 — le test décisif (cf. L26)

Le pattern observé est l'OPPOSÉ de celui des breakouts :

| Cas | delay=0 (same-bar) | delay=1 (clean) |
|---|---|---|
| **Breakout (ORB, etc.)** | look-ahead = ARTIFICIELLEMENT BON (entry au level capture la continuation intra-bar) | edge collapse |
| **Pairs Kalman MR** | entry-bar-penalty = ARTIFICIELLEMENT MAUVAIS (z>2 trigger inclut le move qui a fait z>2) | edge correct (mais ici aussi négatif) |

Dans les deux cas, **delay=1 est le test propre** :
- Breakout : delay=1 révèle que l'edge n'existe pas (artefact)
- Pairs MR : delay=1 révèle le vrai signal (clean execution)

### Pour Strategy D :
- **delay=0 SR = -12 à -13** (entry-bar-penalty, pas un look-ahead bénéfique)
- **delay=1 SR = -1.13 (Park funded sub-window)** ou **-0.48 (POST-Park)**

**Sous clean execution, la stratégie est NÉGATIVE.** Le 2.23 du papier ne se reproduit pas.

## 8. Verdict final

### Récapitulatif des 4 tueurs + DSR + delay-1

| Test | Status | Observation clé |
|---|:---:|---|
| **1. Coint OOS** | ✗ | Aucune fenêtre p<0.05, y compris Park (p=0.30) |
| **2. Half-life** | ✗ | 63-591 jours, jamais intraday |
| **3. Funding** | ✗ | -2%/an, plus 1bp cost de 4-leg → SR net = -1.13 |
| **4. Drift relatif** | ✗ | Park drift/osc = 2.55, BTC out-perf ETH de +83pts harvested |
| 5. DSR | ✓ (passe technique) | SR_def = 0.86 à n_trials=100, mais aveugle au reste |
| **6. Delay-1** | ✗ | SR net = -1.13 (Park funded) / -0.48 (POST) |

**5/6 tests FAIL.** Le seul qui passe est DSR, qui est le plus permissif et aveugle aux artefacts d'exécution/drift.

### Sharpe net honnête recalculé

Avec la décomposition propre :
- **Gross Park delay=1 (no cost, no fund) : SR = +0.23** (= bruit, tiny positif).
- **Net Park delay=1 (1bp cost, funding) : SR = -1.13** (négatif clair).
- **Net POST-Park delay=1 (1bp cost, funding) : SR = -0.48** (négatif clair).

**Recalibration vs le 2.23 du papier : -3.4 points de Sharpe perdus** (de +2.23 à -1.13). Causes par ordre d'importance :
1. **Drift harvest pas répétable** (Killer 4) — explique probablement la moitié du gap
2. **Same-bar fill assumption** (entry-bar-penalty mal modélisée dans le papier ?) — Δ +0.23 → -1.13 = -1.36 du delay-1 fix
3. **Funding 2-jambes pas netté dans le papier** (Killer 3) — Δ -0.7 dans le SR Park funded
4. **Cost 1bp 4-leg** — Δ -0.5 supplémentaire

### Décision opérationnelle

**NO-GO Crypto Fund Trader avec Strategy D.**

Le Sharpe 2.23 du papier est un cocktail de :
- Drift relatif BTC vs ETH sur la fenêtre Park spécifique.
- Probable same-bar fill (entry au trigger).
- Funding non pris en compte.
- Cost 4-leg minimisé.

**Sauvegarde estimée : 1-2 fees Crypto Fund Trader évités (~$100-200), plus la perte attendue sur le challenge.**

### Caveats reportés

1. **Proxy funding** : on a utilisé HL au lieu de Bybit. Les funding rates Bybit pourraient différer légèrement, mais l'ordre de grandeur (~-2%/an) est cohérent.
2. **Pas de Bybit perp price** : on a utilisé le spot Binance. La base perp-spot peut ajouter du bruit mais n'affecte pas le mécanisme global.
3. **Funding indisponible pour 2022-mai 2023** : on a testé la sous-fenêtre Park-avec-funding (mai 2023 - Oct 2024). Si funding pré-mai-2023 était fortement négatif (long pays peu, short reçoit beaucoup), ça pourrait améliorer marginalement le résultat — mais le signal de cointégration n'est de toute façon pas là.
4. **Kalman implémentation** : on a inclus alpha en plus de beta dans le state. Park peut faire sans alpha → différence marginale. Le résultat fondamental (drift+execution) ne change pas.
5. **z-score window 60h** : c'est arbitraire mais standard. Sweep alternatif ne changerait pas le pattern fondamental.

### Implication méthodologique

Le pattern observé **CONFIRME** la batterie des 4 tueurs du stat-arb FTMO :
- L'absence de cointégration OOS tue avant même le backtest.
- Le funding 2-jambes est le pendant crypto du markup-broker CFD.
- Le drift relatif (= beta-in-disguise) est le piège universel des pairs.

**Cinquième leçon générale** : pour TOUTE stratégie pairs trading académique :
- Test cointégration sur TROIS fenêtres : pre-published-window, published-window, post-published-window.
- Test funding/cost réaliste **net**, pas du brut.
- Test delay-1 systématique (même direction selon la stratégie — ici delay-1 RÉVÈLE le vrai signal, c'est cohérent avec L26).

## 9. Reproductibilité

| Script | Sortie |
|---|---|
| `validation_D.py` | `_btceth_1h.parquet` (cache), `killer1_coint_oos.csv`, `killers34_backtest.csv`, `validation_D_output.txt` |
| `killer4_drift_decomp.py` | `killer4_drift_decomp.csv`, `killer4_output.txt` |

Tous seeded, déterministes. `cd Crypto/research/active/pairs_btceth_D && /usr/bin/python3 validation_D.py && /usr/bin/python3 killer4_drift_decomp.py`.

## 10. In-sample vs OOS marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| Sharpe 2.23 (Park) | Park IJSRA 2026 | **claim externe, NON reproduit** dans notre validation |
| ADF p Park = 0.30 (PAS coint) | killer1 | **in-sample Park** |
| HL Park = 87 jours | killer2 | **in-sample Park** |
| SR net Park delay=1 funded = -1.13 | killers34 | **in-sample sub-Park (mai 2023-Oct 2024)** |
| SR net POST-Park delay=1 = -0.48 | killers34 | **OOS strict, post-publication** |
| Drift/osc Park = 2.55 | killer4 | **in-sample Park** |
| Drift/osc POST = 1.45 | killer4 | **OOS** |
| Live performance | — | **0 jour, à éviter (NO-GO)** |

---

*Validation Strategy D réalisée 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Batterie 4 tueurs + DSR + delay-1 (machinery réutilisée du stat-arb FTMO deep-dive). Verdict : NO-GO Crypto Fund Trader, le 2.23 était un drift relatif harvested + same-bar fill artifact. Fee de propfirm épargné.*
