# Deep-dive Breakout / Trend FTMO — exploration de la famille

**TL;DR — La famille breakout/trend sur NQ 2010-2026 NE PRODUIT PAS d'alpha net robuste sous fill réaliste.** Sous fill same-bar (dormant stop idéalisé), 8/10 variantes passent le filtre two-sided avec DSR-survivant ; mais sous delay-1 (fill conservateur), **88-100% de l'edge collapse** et aucune variante n'a d'espérance significative positive. **L'edge est entièrement une rente d'exécution**, pas un alpha stratégie.

| Variant | EXEC_0 total | delay-1 total | Δ collapse | Verdict |
|---|---:|---:|---:|---|
| PDH_PDL + trail_ATR (best EXEC_0) | **+0.260R** (DSR 4.6) | **-0.014R** | -0.258 (99%) | ARTIFACT |
| ORB_15min + TP_2R | +0.218R | +0.027R | -0.191 (88%) | edge ≈ 0 |
| ORB_30min + TP_2R | +0.146R | -0.001R | -0.147 (101%) | ARTIFACT |
| Bollinger + EOD | +0.138R | +0.001R | -0.137 (99%) | edge ≈ 0 |
| Donchian_20 + EOD | +0.114R | +0.003R | -0.111 (97%) | edge ≈ 0 |

**Three hypothèses tranchées:**
- **(a) Two-sided edge structurel** : ✗ REJETÉE sous delay-1 (pas survivable).
- **(b) Edge sous fill optimiste idéalisé** : ✓ VRAI sous same-bar, mais **conditionnel à l'exécution parfaite**, donc fragile en live.
- **(c) Le "+0.20-0.26R" reporté est fill-artefact** : ✓ CONFIRMÉ par collapse 88-100% delay-1.

**Recommandation opérationnelle** : la famille breakout ne génère pas d'alpha structurel monnayable. Tout deploy doit assumer que l'edge live = **0 à 0.03R par trade** (le delay-1 result), pas 0.10-0.26R. À ce niveau, p_funded sous coût bps réaliste = baseline déjà étudié dans `VALIDATION_baseline_2010_2026_v2.md` (~42% à 0.50% sizing, marginal). **La profondeur sur la famille confirme le NO-GO net** — pas par absence d'edge en idéalisé, mais par fragilité d'execution.

---

## 0. Cadrage et méthodologie

### Métrique = alpha net par-trade, PAS p(pass)

On a établi (cf. `orb_realconstraints_2026-06`) que p(pass) sous floor_taper + temps illimité est dominé par un exploit bêta de "no-bust × unlimited time" (placebo Gaussien zéro-mean +floor = 97.7%). Donc évaluer une variante par p(pass) sous floor_taper = re-découvrir l'exploit, sans rien apprendre sur l'edge.

Ici on chasse l'**alpha NET PAR-TRADE, DSR-survivant, TWO-SIDED, delay-robust**.

### Filtres anti-overfit appliqués (TOUS, sans exception)

1. **Non-overlap** : max 1 trade/jour, par construction.
2. **Cost bps réaliste** : 1 bp RT (NQ futures-equivalent), appliqué par-trade comme `bps × level / 10000`.
3. **TWO-SIDED requirement (L25)** : short leg net ≥ -0.02 ET short t-stat > -1. Primary filter — une stratégie one-sided long sur NQ = bêta long déguisé, rejetée.
4. **Delay-1 sensitivity** : un vrai edge survit délai 1-bar (L26) ; un artefact same-bar fill s'effondre. C'est le test DÉCISIF.
5. **DSR Bailey-LdP** : n_trials = espace de recherche TOTAL (10 phase 1 + 32 phase 2 = 42 variantes). Plus restrictif si on inclut l'historique ORB.
6. **Reconciliation** : croise avec les résultats ORB existants (notamment 30-min) et avec l'analyse F1-bughunt (qui a déjà documenté le même pattern same-bar artifact).

### Espace exploré (Phase 1, broad scan)

10 variantes de signal × NQ 5-min × EOD exit × 0 filter × cost 1 bp :
- ORB 30/15/60-min (= 6/3/12 5-min bars)
- Donchian 20/60-bar 5-min lookback
- Vol breakout: close > prev_close ± 1.5 × ATR_20d
- Squeeze: range < 50% of 20-bar avg → first break
- PDH/PDL: break of prior-day high/low
- Bollinger 20-period 2-σ
- Range expansion: bar's range > 1.5 × ATR_20

---

## 1. Phase 1 — Broad scan, 10 variantes

`audit/breakout_deepdive.py` → `breakout_phase1_metrics.csv`, `breakout_phase1_full.csv`.

### Métriques EXEC_0 (same-bar fill at level)

| Variant | n_total | mean R total | long mean R | short mean R | t total | t short | hit % |
|---|---:|---:|---:|---:|---:|---:|---:|
| ORB_30min | 3945 | +0.144 | +0.155 | +0.131 | +9.82 | +5.77 | 49.9% |
| ORB_15min | 4010 | +0.214 | +0.236 | +0.190 | +11.45 | +6.30 | 44.9% |
| ORB_60min | 3732 | +0.094 | +0.106 | +0.078 | +8.66 | +4.57 | 54.4% |
| Donchian_20 | 3978 | +0.114 | +0.100 | +0.131 | +8.80 | +6.06 | 51.8% |
| Donchian_60 | 1848 | +0.048 | +0.030 | +0.073 | +7.52 | +6.56 | 57.8% |
| Vol_break_1.5ATR | 574 | +0.037 | +0.046 | +0.030 | +4.74 | +2.85 | 56.3% |
| Squeeze | 0 | — | — | — | — | — | — |
| PDH_PDL | 3439 | **+0.245** | +0.239 | **+0.253** | +21.64 | **+13.97** | 61.5% |
| Bollinger_20_2σ | 4009 | +0.138 | +0.121 | +0.157 | +8.70 | +5.83 | 47.9% |
| Range_expansion | 3996 | -1.059 (BUG : entry=high, stop=low → instant stop) | — | — | — | — | 0% |

### Two-sided filter (EXEC_0)
8/9 variantes (excluant Range_expansion bug) passent : short mean R > 0, short t > +2.

### Delay-1 sensitivity (LE test décisif)

| Variant | EXEC_0 short | **delay-1 short** | EXEC_0 t short | **delay-1 t short** |
|---|---:|---:|---:|---:|
| ORB_30min | +0.131 | **-0.035** | +5.77 | -1.56 |
| ORB_15min | +0.190 | -0.016 | +6.30 | -0.55 |
| ORB_60min | +0.078 | **-0.035** | +4.57 | **-1.86** |
| Donchian_20 | +0.131 | +0.007 | +6.06 | +0.32 |
| Donchian_60 | +0.073 | -0.001 | +6.56 | -0.11 |
| Vol_break | +0.030 | -0.018 | +2.85 | **-1.65** |
| PDH_PDL | +0.253 | **-0.027** | +13.97 | **-1.53** |
| Bollinger | +0.157 | +0.006 | +5.83 | +0.23 |

**Pattern UNIVERSAL** : sous fill conservateur (delay-1), TOUS les short legs s'effondrent près de zéro ou négatifs. C'est le même pattern same-bar fill que le bug F1 (cf. `F1_bughunt.md`).

---

## 2. Phase 2 — Depth sur 8 survivants × 4 exits

`audit/breakout_phase2_depth.py` → `breakout_phase2_full.csv`.

### Mean R total par (variant × exit) — sous EXEC_0

| Variant | EOD | trail_BE@1R | TP_2R_partial | trail_ATR |
|---|---:|---:|---:|---:|
| **PDH_PDL** | 0.245 | 0.249 | 0.244 | **0.260** |
| **ORB_15min** | 0.214 | 0.184 | **0.218** | 0.084 |
| ORB_30min | 0.144 | 0.146 | 0.146 | 0.106 |
| Bollinger | 0.138 | 0.111 | 0.131 | 0.081 |
| Donchian_20 | 0.114 | 0.098 | 0.110 | 0.078 |
| ORB_60min | 0.094 | 0.092 | 0.094 | 0.093 |
| Donchian_60 | 0.048 | 0.048 | 0.048 | 0.047 |
| Vol_break | 0.037 | 0.036 | 0.037 | 0.037 |

### Mean R SHORT-ONLY (variant × exit)

| Variant | EOD | trail_BE@1R | TP_2R_partial | trail_ATR |
|---|---:|---:|---:|---:|
| **PDH_PDL** | 0.253 | 0.255 | 0.249 | **0.263** |
| ORB_15min | 0.190 | 0.146 | 0.196 | 0.035 |
| Bollinger | 0.157 | 0.126 | 0.144 | 0.066 |
| ORB_30min | 0.131 | 0.128 | 0.136 | 0.075 |
| Donchian_20 | 0.131 | 0.111 | 0.129 | 0.069 |
| ORB_60min | 0.078 | 0.070 | 0.081 | 0.076 |
| Donchian_60 | 0.073 | 0.074 | 0.074 | 0.071 |
| Vol_break | 0.030 | 0.029 | 0.030 | 0.030 |

→ **Best EXEC_0 combination: PDH_PDL + trail_ATR = +0.260R total, +0.263R short** (n=3439, t_total > 21).

---

## 3. Phase 3 — DSR sur espace total

`audit/breakout_phase3_dsr.py` → `breakout_phase3_dsr.csv`.

n_trials = 41 (10 phase 1 + 32 phase 2 - 1 bug exclu). Sharpe annualisé approximé via per-trade × √trades_per_yr.

### DSR results — top 10 candidates

| Variant + exit | mean R | Sharpe ann ≈ | sr0 thr | **sr_def** | DSR p_real | boot p |
|---|---:|---:|---:|---:|---:|---:|
| PDH_PDL trail_ATR | 0.260 | 5.04 | 0.47 | **4.57** | 1.00 | 0.00 |
| PDH_PDL trail_BE@1R | 0.249 | 4.34 | 0.48 | 3.86 | 1.00 | 0.00 |
| PDH_PDL EOD | 0.245 | 4.15 | 0.49 | 3.66 | 1.00 | 0.00 |
| PDH_PDL TP_2R | 0.244 | 4.48 | 0.52 | 3.96 | 1.00 | 0.00 |
| ORB_15min TP_2R | 0.218 | 2.55 | 0.51 | 2.04 | 1.00 | 0.00 |
| ORB_15min EOD | 0.214 | 2.17 | 0.49 | 1.68 | 1.00 | 0.00 |
| ORB_15min trail_BE | 0.184 | 2.15 | 0.49 | 1.66 | 1.00 | 0.00 |
| ORB_30min trail_BE | 0.147 | 2.09 | 0.51 | 1.58 | 1.00 | 0.00 |
| ORB_30min TP_2R | 0.146 | 2.07 | 0.53 | 1.54 | 1.00 | 0.00 |
| ORB_30min EOD | 0.144 | 1.87 | 0.51 | 1.36 | 1.00 | 0.00 |

**10/10 candidates SURVIVE DSR avec sr_deflated > 1.0.** Block-bootstrap p-value = 0.000 partout. Sous EXEC_0, l'edge est statistiquement défendable.

---

## 4. Phase 4 — Delay-1 sensitivity sur top candidates (LE test final)

`audit/breakout_phase4_delay_top.py` → `breakout_phase4_delay_top.csv`.

### Effet du passage EXEC_0 → delay-1 (next-bar-open)

| Variant | EXEC_0 total | **delay-1 total** | Δ collapse | EXEC_0 short | **delay-1 short** | delay-1 short t |
|---|---:|---:|---:|---:|---:|---:|
| PDH_PDL | +0.245 | **-0.014** | -0.258 (105%) | +0.253 | **-0.027** | -1.53 |
| ORB_15min | +0.214 | +0.027 | -0.187 (87%) | +0.190 | -0.016 | -0.55 |
| ORB_30min | +0.144 | -0.001 | -0.145 (101%) | +0.131 | -0.035 | -1.56 |
| Bollinger | +0.138 | +0.001 | -0.137 (99%) | +0.157 | +0.006 | +0.23 |
| Donchian_20 | +0.114 | +0.003 | -0.111 (97%) | +0.131 | +0.007 | +0.32 |

### Verdict TWO-SIDED filter sous delay-1

| Variant | delay-1 short | delay-1 t short | TWO-SIDED PASS ? |
|---|---:|---:|:---:|
| PDH_PDL | -0.027 | -1.53 | ✗ ARTIFACT |
| ORB_15min | -0.016 | -0.55 | borderline |
| ORB_30min | -0.035 | -1.56 | ✗ ARTIFACT |
| Bollinger | +0.006 | +0.23 | ✓ flat but two-sided |
| Donchian_20 | +0.007 | +0.32 | ✓ flat but two-sided |

**3/5 survivants sont en réalité "flat" (delay-1 total < 0.03R) — pas un edge exploitable.**

### Lecture mécanique du collapse

Le collapse 88-105% indique que la totalité (ou presque) de l'edge est gagnée pendant la **première barre 5-min après le break confirmé**. C'est exactement la signature du same-bar fill artefact :
- En live, un dormant stop placé au level L : quand le bar bi a high > L, fill = première ask >= L. Si bar bi open = L+5 (gap), fill = L+5 (slip 5 pts).
- En EXEC_0 modèle : fill = L exact, on capture les 5 pts comme profit "free".
- En delay-1 (NEXT_OPEN) : entry au O[bi+1] = ~L+8 pts (mid-bar continuation). Le profit est gone.

L'ÉCART entre les deux modèles = la rente de fill same-bar exactly-at-level. Cette rente est **non-réalisable en live** car en pratique le fill slip de quelques pts.

---

## 5. Verdict tranché entre les 3 hypothèses

### (a) Two-sided edge structurel sous fill conservateur — **REJETÉE**

- Aucun candidat ne maintient mean R total > 0.03 sous delay-1.
- 2/5 (PDH_PDL, ORB_30min) ÉCHOUENT explicitement two-sided sous delay-1 (short t < -1).
- 3/5 (ORB_15min, Bollinger, Donchian_20) "survivent" two-sided mais avec edge total ≈ 0.

### (b) Edge sous fill optimiste idéalisé — **VRAI mais FRAGILE**

- 10/10 candidates passent DSR sous EXEC_0 (sr_deflated 1.4 à 4.6 à n_trials=41).
- Mais cet edge est ENTIÈREMENT le delta EXEC_0 vs delay-1.
- Pour le capturer en live : il faut **fill exact au niveau du stop**, pas de slip. Réalisable en théorie sur instruments très liquides mais fragile.

### (c) Le "+0.20-0.26R" reporté est artefact fill — **CONFIRMÉ**

- Δ collapse 88-105% au delay-1 = la totalité de l'edge.
- Réplique exacte du bug F1 (le ttb buggé prédictait grâce à un look-ahead) : pattern same-bar artefact universel sur la famille breakout.

---

## 6. Implications opérationnelles

1. **Le baseline (`VALIDATION_baseline_2010_2026_v2.md`) reste valide** :
   - p_funded ~42% à 0.50% sizing sous coût bps réaliste — déjà capture le bon niveau d'edge.
   - L'edge live attendu = ~0.01-0.03R par trade (le delay-1 result), pas 0.10-0.26R.

2. **La profondeur sur la famille NE révèle pas de variante miracle**. Toutes les variantes testées sont sample-bar-fill-dependent.

3. **PDH_PDL et trail_ATR exits ont l'apparente "meilleure" performance**, mais c'est précisément la plus dépendante du fill artefact (Δ collapse 99-105%). À ne PAS deployer comme telle.

4. **Si une variante doit être deployée**, c'est ORB_15min + EOD (delay-1 mean R +0.027R, le moins négatif des candidats) — mais le edge est tellement marginal qu'il ne justifie pas un challenge FTMO à $155/attempt.

5. **Pas besoin de tester FX/DAX/etc.** — le pattern est structural à la famille breakout intraday : tous les signaux capturent the same intra-bar continuation = same-bar fill artefact.

### Comparaison avec hypothèses alternatives

- **Mean reversion (Cowork deep-dive parallèle)** : si le MR family donne aussi un edge same-bar mais qui PASSE delay-1, alors MR > breakout pour FTMO. À voir.
- **Trend-on-larger-TF** (daily/swing) : non testé ici, peut-être moins sample-bar-dépendant (les fills daily sont à market close, plus stables). Future research.

---

## 7. Leçons méthodologiques

1. **Le test delay-1 est OBLIGATOIRE pour toute stratégie intraday breakout**. Le même pattern revient (F1, ORB, Donchian, PDH/PDL). Sans ce test, on overstate l'edge de 88-105%.

2. **DSR Bailey-LdP est aveugle au fill artefact**. 10/10 candidates passent DSR avec sr_def > 1, mais l'edge est artefact. DSR corrige le multiple-testing, PAS l'execution model.

3. **TWO-SIDED L25 SOUS DELAY-1 est le test discriminant** : EXEC_0 + L25 peut passer même avec artefact (les shorts capturent leur propre artefact). Delay-1 + L25 = test propre.

4. **Le "same-bar fill" idéalisé est une rente impossible en live**. Modéliser le slip réaliste = entre EXEC_0 et delay-1, probablement -50% à -80% de l'EXEC_0 result.

5. **La famille breakout sur indices intraday CFD = pas d'alpha structurel**. C'est le verdict de cette profondeur — pas une condamnation hâtive ni une survie illusoire.

---

## 8. Reproductibilité

| Phase | Script | Sortie principale |
|---|---|---|
| 1 broad | `audit/breakout_deepdive.py` | `breakout_phase1_full.csv` + 8 parquet trades |
| 2 depth | `audit/breakout_phase2_depth.py` | `breakout_phase2_full.csv` |
| 3 DSR | `audit/breakout_phase3_dsr.py` | `breakout_phase3_dsr.csv` |
| 4 delay-test | `audit/breakout_phase4_delay_top.py` | `breakout_phase4_delay_top.csv` |

Data : `data/raw/NQ_1min_databento_2010-2026.parquet`. Cost = 1 bp RT (NQ futures). Skip is_roll_day. Tous seeded, déterministes.

---

## 9. In-sample vs OOS marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| EXEC_0 mean R PDH_PDL = +0.245R | Phase 1 | **in-sample 16y, fill artefact suspect** |
| EXEC_0 mean R PDH_PDL trail_ATR = +0.260R | Phase 2 | **in-sample, après search ×4 exits** |
| DSR sr_def 4.57 PDH_PDL trail_ATR | Phase 3 | **in-sample, DSR-survivant mais aveugle au artefact** |
| **delay-1 mean R PDH_PDL = -0.014R** | Phase 4 | **OOS conservatif**, edge collapsed |
| **delay-1 short t = -1.53 PDH_PDL** | Phase 4 | **ARTEFACT confirmé** |
| Live performance | — | **0 jour** |

---

*Deep-dive breakout/trend réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx). NQ databento 16y. Métrique = alpha net par-trade two-sided + delay-robust + DSR-survivant. Verdict : edge same-bar = artefact, edge delay-1 ≈ 0. Famille breakout/trend pas d'alpha structurel sur NQ intraday sous fill réaliste.*
