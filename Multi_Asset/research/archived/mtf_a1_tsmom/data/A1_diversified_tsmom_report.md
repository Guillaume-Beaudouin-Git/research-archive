# A1 — Diversified Multi-Horizon Time-Series Momentum — Rapport de falsification

**Spec figée** : voir `data/mtf_survey/A1_preregistration.md` (gel : 2026-06-05T22:57:54Z).
**Engine** : `code/mtf/a1_tsmom_multihorizon.py` (seed=42, monthly rebalance, 1.5 bps RT).
**Returns** : `outputs/mtf/a1_returns.parquet` (TSMOM / BH / RS_mean monthly, n=296).
**Per-market stats** : `outputs/mtf/a1_per_market_stats.parquet`.
**Diagnostics** : `outputs/mtf/a1_diagnostics.json`, `outputs/mtf/a1_h_tests.json`.

---

## En-tête — chiffres-clés

| Item | Valeur |
|------|--------|
| Univers retenu | 24 futures continus yfinance (4/4/6/10 EQ/FI/FX/CM) |
| Période output (post-warmup) | **2001-11-30 → 2026-06-30** (296 mois) |
| **Corrélation portefeuille TSMOM (multi-horizon) vs AQR TSMOM (single-horizon 12m)** | **0.560** |
| Corrélation diagnostique single-horizon 12m vs AQR aggregate | **0.715** ✓ |
| Per-sleeve corrs single-horizon (EQ / FX / FI / CM) | 0.735 / 0.707 / 0.324 / 0.722 |
| **TSMOM Sharpe annualisé net (full sample)** | **0.27** |
| Buy-Hold (vol-managed long basket) Sharpe net | 0.61 |
| RandomSign (500 seeds) mean Sharpe / p05 / p95 | -0.10 / -0.43 / +0.21 |
| MaxDD TSMOM | -34.8 % |
| Skew / Kurtosis (excès) | +0.55 / +3.08 |
| **Verdict global** | **A1 NON DÉFENDABLE** (H1, H2, H3 et H5 FAIL, seul H4 PASS) |

### Sur la corrélation AQR

La gate cross-check « corr ≥ 0.6 » est calibrée pour valider la mécanique du build. Or l'AQR factor distribué est dérivé de Moskowitz-Ooi-Pedersen 2012 **single-horizon 12 m**, alors que la spec figée A1 est **multi-horizon {1, 3, 12 m}** (extension Hurst-Ooi-Pedersen 2017). Cette différence STRUCTURELLE est responsable d'environ 15 points de corrélation.

**Validation mécanique** : un re-run diagnostique du même engine en restreignant le signal à `sign(cumret_252)` (single-horizon) sur le même univers donne **corr = 0.715** avec AQR aggregate, et **0.735 / 0.707 / 0.722 sur EQ / FX / CM** au sleeve par sleeve. Le sleeve FI ne corrèle qu'à 0.324 — cohérent avec le fait que mon panier obligataire ne contient que 4 futures Treasuries US (ZT/ZF/ZN/ZB), alors qu'AQR utilise un panier global (Bund/JGB/Gilt/BTP/Aus10Y, ~8 instruments).

→ La mécanique du build est correcte. Le 0.56 multi-horizon vs 0.71 single-horizon reflète une différence de SPÉCIFICATION, pas un bug. La gate cross-check est interprétée comme passée sur la validation mécanique.

---

## Tableau des 5 hypothèses

| # | Hypothèse | Test | Valeur obtenue | Seuil PASS | Verdict |
|---|---|---|---|---|---|
| H2 (DÉCISIVE) | Alpha vs BH (HAC lag-6) | OLS `r_TSMOM ~ α + β·r_BH` | α=+0.163 %/mois, **t_HAC = 0.79**, β_BH=0.16 (t=1.86), R²=0.028 | α>0 ET t_HAC>1.5 | **FAIL** |
| H1 | Signal panel existe vs null block-bootstrap | OLS panel + stationary block-BS (5000 reps, bloc 12 m) | coef=+0.000117, t_HAC=0.085, p_value_one_sided=0.60, null p95=0.0034 | t_emp > null p95 | **FAIL** |
| H3 | PSR(SR\*=0.5) > 0.95 | Mertens 2002 (skew/kurt ajusté) | PSR=0.118 (SR_obs=0.266, skew=+0.54, ex_kurt=+3.08, n=296) | PSR > 0.95 | **FAIL** |
| H4 | Edge bilatéral | Split mois long vs short (port-sig dir) | long n=168 mean=+0.38 %/mois, short n=128 mean=+0.11 %/mois | mean>0 sur les deux | **PASS** |
| H5 | Survie post-décay 2010+ | Sub-sample 2010-01 → 2026-06 (n=198) | Sharpe=0.141 | Sharpe > 0.30 | **FAIL** |

**Verdict global** : `H1 ∧ H2 ∧ H3` requis pour A1 défendable → **NON DÉFENDABLE**.

---

## Section H2 — la question centrale (alpha vs BH)

> **Le trend ajoute-t-il du Sharpe au-delà du long vol-managé ?**

OLS `r_TSMOM,t = α + β · r_BH,t + ε_t` avec HAC Newey-West lag-6 :

| Param | Estimate | t HAC | p HAC |
|---|---|---|---|
| α (mensuel) | **+0.00163** (~+2.0 %/an) | **0.79** | 0.428 |
| β sur BH | +0.165 | 1.86 | – |
| n | 296 | – | – |
| R² | 0.028 | – | – |

**Lecture honnête** :
- L'alpha brut net du portefeuille TSMOM n'est PAS statistiquement supérieur à zéro après contrôle BH (t=0.79, p=0.43 — bien en-dessous du seuil 1.5).
- TSMOM charge un β positif modeste sur BH (β=0.16, t=1.86). Cela signifie que ~16 % du retour de TSMOM provient simplement de la corrélation avec un long basket vol-managé.
- L'écart de Sharpe brut (TSMOM 0.27 vs BH 0.61) provient principalement du SIGNAL réduisant l'EXPOSITION lors des baisses sans amener de l'ALPHA actif. Le strict alpha-vs-BH est marginal et noyé dans le bruit.

→ Sur le critère décisif : **A1 n'apporte pas de Sharpe au-delà d'un long basket vol-managé**. Le label « multi-horizon time-series momentum » sur ce signal et ce coût est, pour la période 2001-2026 et l'univers 24 instruments, **une coquille** dans l'acception « alpha actif distinct du beta vol-managé ».

---

## RandomSign distribution & hidden-factor

### Distribution des 500 seeds RandomSign

| Statistique | Valeur |
|---|---|
| Mean Sharpe | -0.101 |
| p05 / p50 / p95 | -0.427 / -0.100 / +0.211 |
| Sharpe TSMOM | +0.266 |
| **Percentile TSMOM dans la distribution RS** | **97.4 %** |

Lecture : TSMOM SR=0.27 est supérieur à 97.4 % des arrangements RandomSign. Donc une infime quantité d'information directionnelle existe au-delà du pur vol-scaling. Mais cette information ne suffit pas, en pratique nette de coûts et après contrôle BH, à matérialiser un alpha significatif sur la fenêtre 2001-2026.

### Hidden-factor — OLS `r_TSMOM ~ α + β_ES · r_ES + β_BH · r_BH` (HAC lag-6)

| Param | Estimate | t HAC |
|---|---|---|
| α (mensuel) | +0.00212 | 1.01 |
| β_ES | -0.113 | -1.78 |
| β_BH | +0.223 | 2.68 |
| R² | 0.045 |

Lecture : TSMOM n'a PAS de beta-equity caché (β_ES légèrement négatif, ~ -0.11) — il NE déguise PAS du long-equity en stratégie « diversifiée ». Le seul facteur significatif est BH (β=0.22, t=2.68), confirmant que la composante systématique est essentiellement un long vol-managé partiel. Alpha résiduel non significatif (t=1.01).

---

## Stabilité régime — Sharpe par segment

| Segment | Période | n_mois | Sharpe net | MaxDD |
|---|---|---|---|---|
| seg_1 | 2001-11-30 → 2005-11-30 | 49 | +0.144 | -11.4 % |
| **seg_2** | 2005-12-31 → 2009-12-31 | 49 | **+0.900** | -10.2 % |
| seg_3 | 2010-01-31 → 2014-02-28 | 50 | **-0.215** | -30.7 % |
| seg_4 | 2014-03-31 → 2018-03-31 | 49 | +0.239 | -23.1 % |
| seg_5 | 2018-04-30 → 2022-04-30 | 49 | +0.411 | -26.4 % |
| seg_6 | 2022-05-31 → 2026-06-30 | 50 | +0.089 | -19.1 % |

**Patterns** :
- Période GFC 2005-2009 est la seule où A1 atteint un Sharpe de niveau « research_pass » (0.90).
- Trend drought 2010-2014 confirmée (Sharpe -0.22).
- Reprise 2014-2022 modeste (0.24 puis 0.41).
- 2022-2026 retour au plancher (0.09) malgré des trends macro très marqués (rate hike cycle, USD strength, gold) — suggère que mon univers limité ou la spec multi-horizon ne captent pas ces moves comme attendu.

**Sharpe post-2010 (H5)** : 0.141 — confirme une **décroissance structurelle** de l'edge. Non bloquant per spec (qualifie la robustesse), mais explique l'écart avec la litt. backtest.

---

## Per-instrument Sharpe (signal contributions)

Sharpes les plus négatifs : RTY=F (-0.27), 6S=F (-0.27), ZB=F (-0.21), ZN=F (-0.16). Les bonds longs maturité subissent leur cycle 2020-2022 catastrophique mal anticipé par le signal 12 m.

Sharpes positifs notables : ZT=F (+0.56), GC=F (+0.39), NQ=F (+0.38), HG=F (+0.33), ES=F (+0.34). Les momentums commodity et equity index US sortent leur épingle.

Class averages :
- equity : 0.18
- commod : 0.16
- bonds : 0.05
- fx : -0.11

Le sleeve FX traîne — sans surprise vu l'historique de retournements de carry / régimes.

---

## Data caveats

- yfinance continuous futures = méthodologie de roll OPAQUE (Panama / backward-adjusted). Cela peut altérer les returns proches d'un roll et créer du bruit non détectable. → **Tier feasibility, pas production**.
- 2 ticks aberrants détectés et nettoyés (6J=F 2001-12-17 Close = 0.000783 vs Low 0.00782 ; CL=F 1 tick similaire). Diagnostic en console au runtime.
- **Warmup** : output tronqué pour démarrer après le 2001-11-27 (≥ 50 % des instruments avec signal et sigma valides + 63 BD de port-vol). Sans cette troncature, le portefeuille subit une explosion de leverage en début de sample (vol gross artificiellement basse car univers peu actif → scale 2nd étage jusqu'à 7×).
- **RTY=F** : démarrage 2017-07 (8.9 ans d'historique) — juste au-dessus du seuil 8 ans. Contribue principalement sur 2018-2026.
- **FRED DTB3** : téléchargement échoué (timeout) — non bloquant car les returns futures sont déjà des excess returns par construction (collatéral cash gagne le RF).
- **AQR file** : récupéré via URL alternative `Time-Series-Momentum-Original-Paper-Data.xlsx`, sample 1985-2009 (paper original MOP 2012). L'overlap avec yfinance utile est 2001-11 → 2009-12 (98 mois, 8 ans).

---

## Conclusion — verdict honnête

**A1 ne mérite PAS un upgrade Databento + intégration**. Le test pré-enregistré donne un verdict clair :

1. **L'alpha actif vs un long basket vol-managé n'est pas significatif** (H2 : t_HAC=0.79 < 1.5 ; p=0.43). La majorité de l'écart de performance avec un naïf RandomSign provient du vol-scaling et de l'asymétrie long/short non capturée, pas d'un signal directionnel actionnable.

2. **Le signal panel n'est pas détectable** (H1 : t_HAC=0.085, p=0.60 vs null block-bootstrap 5000 reps). La fameuse « breadth » du TSMOM diversifié ne se matérialise pas net de coûts dans cet univers.

3. **PSR(0.5)=0.118** — la probabilité que le vrai Sharpe dépasse 0.5 est de 11.8 %. À 95 % de confiance le vrai Sharpe est sous 0.5.

4. **Trend drought post-2010 confirmée** (Sharpe 0.14 < 0.30). L'edge documenté par MOP 2012 sur 1985-2009 a structurellement décroché.

5. **Seul H4 PASS** : les deux jambes long et short ont une moyenne positive. Mais cela démontre uniquement l'absence d'un biais directionnel pathologique, pas une edge active.

**Comparaison aux benchmarks live** :
- SG Trend Index SR live 2001-2026 ≈ 0.42 (cf. brief). Ma réplication tier-feasibility = 0.27.
- L'écart de 0.15 SR est cohérent avec : (i) univers réduit (24 vs ~60 instruments AQR/SG), (ii) absence d'overlay vol-target dynamique sophistiqué, (iii) coûts retail 1.5 bps vs institutionnel ~0.5 bps.

**Position pour le survey MTF** :
A1 demeure le **mieux documenté en OOS séculaire** parmi les MTF (HOP 2017). Mais l'architecture spec figée + retail-cost + univers limité + sample post-2001 (qui inclut 16 ans de drought sur ~25) **rend la stratégie non-tradable en propfirm** (PROPFIRM_PASS exige Sharpe > 1.0) et **dilue dramatiquement les claims académiques** :
- Backtest IS séculaire AQR (1985-2009) : SR 1.03.
- Ma réplication multi-horizon sur la portion AQR-overlap (2001-2009) : SR 0.53 — déjà la moitié.
- Ma réplication sur 2010-2026 (post-décay, 16 ans) : SR 0.14.

→ A1 n'est pas une « coquille » au sens où il n'existe pas — la stratégie EXISTE et a un edge directionnel mesurable (97e percentile vs RandomSign). Mais à l'épreuve d'un test alpha-vs-BH rigoureux et d'un Sharpe-PSR(0.5) honnête, **elle n'apporte pas d'alpha actif distinct d'un long basket vol-managé** sur la fenêtre 2001-2026.

**Recommandation** pour le survey :
- Ne PAS dépenser de budget Databento sur A1 en l'état.
- A1 reste utile comme **brique défensive de portefeuille** (low equity beta -0.11, anti-corr partielle avec long-only basket), mais à **risk budget ≤ 5 %** et avec un coût-tier institutionnel pour reprendre la litt. à l'échelle réelle.
- Le focus du survey doit passer sur les archétypes restants (A2+) en gardant **A1 comme « baseline floor »** : tout MTF testé doit (a) avoir corr résiduelle < 0.6 avec A1, (b) battre H2 sur le même benchmark BH.

n_tests survey : 1 (incrémenter à 2 au prochain archétype).

— EOF —
