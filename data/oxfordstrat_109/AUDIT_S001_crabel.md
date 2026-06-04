# AUDIT critique S001 — Toby Crabel 2-Bar NR + ORB

**Objet :** vérification du rapport `REPORT_S001_crabel_nr_orb.md` (session Cowork du 2026-06-04)
sous nos gates constitutionnels (L25/L26/L31/L33 + DSR + bootstrap).
**Statut Cowork :** ✅ KEEP (borderline) sous barre « tout edge positif après coûts ».
**Statut audit :** ❌ **DISCARD** — 5/6 gates FAIL.
**Auteur :** Claude (session critique) · **Date :** 2026-06-04 · **Code :** `code/audit_s001.py`,
résultats `results/audit_s001_*.csv`.

> ⚠️ La barre « tout edge positif après coûts » utilisée par Cowork est **basse**. Les gates
> ci-dessous (délai+1, two-sided, DSR, OOS) sont la **vraie** barre. Un edge à Sharpe 0,22 qui
> passe une barre basse peut très bien échouer la vraie. Le verdict ci-dessous l'illustre.

---

## 0. Reproduction préalable

Pré-requis avant tout audit : confirmer que les chiffres du rapport sont reproductibles.

| Métrique | REPORT_S001 | Re-run `audit_s001.py` | Match |
|---|---|---|---|
| Trades poolés | 3 841 | 3 841 | ✓ |
| Win rate | 45,1 % | 45,1 % | ✓ |
| Expectancy R/trade | +0,0068 | +0,0068 | ✓ |
| Profit Factor | 1,050 | 1,050 | ✓ |
| Sharpe poolé | 0,22 | 0,22 | ✓ |
| MaxDD | −16,1 % | −16,1 % | ✓ |
| Best cell (6R, 40j) | +0,0387 R | +0,0387 R | ✓ |
| Grille 100 % positive | oui | oui | ✓ |

Reproduction parfaite — aucun drapeau rouge à ce stade. Le code Cowork est honnête sur sa
mesure. L'audit s'attaque donc aux **hypothèses** (intrabar, two-sided, multiple testing,
OOS), pas à la mesure brute.

---

## 1. Gate 1 — Délai+1 / fill close (L26) · **FAIL** — *gate le plus décisif*

Le rapport S001 §5.4 admet que l'engine est une **approximation daily** d'une stratégie
intraday : le fill est supposé se faire **au niveau exact du stop** sur la barre d'entrée.
Si la stratégie n'existe que parce que ce fill est généreux, ce n'est pas un edge tradable.

Deux variantes ont été testées (test « adversarial » du fill intrabar) :

- **V1a — entry at OPEN of i+2** : on ignore la barre d'entrée originale et on rentre à
  l'ouverture du jour suivant (l'information du déclenchement intrabar n'est consommée que
  le lendemain). Stop/target référencés depuis ce nouvel entry.
- **V1b — fill at CLOSE of entry bar** : on garde la même barre d'entrée mais on prend
  le close comme prix d'exécution (au lieu du niveau du stop). Mesure l'« honnêteté » du
  prix de remplissage.

**Résultats (3R / 10j, mêmes coûts) :**

| Variante | Trades | Win | expR | PF | Sharpe |
|---|---|---|---|---|---|
| Référence | 3 841 | 45,1 % | **+0,0068** | 1,050 | **+0,22** |
| V1a (entry i+2 open) | 3 748 | 41,4 % | **−0,0234** | 0,848 | **−0,72** |
| V1b (fill at close) | 3 841 | 41,7 % | **−0,0221** | 0,851 | **−0,72** |

**Lecture :** les **deux** variantes inversent complètement l'edge. Le signe de l'expectancy
change. Sharpe passe de **+0,22 à −0,72** dans les deux cas. La perte de **~3 points de win
rate** (45,1 → 41,4-41,7 %) est diagnostique : le « surplus » de wins ne vient pas du signal
mais du fait de **rentrer au niveau du stop sur une barre qui déclenche ce stop** (le high
qui touche le buy stop est par construction au-dessus de ce stop → le close, lui, n'a aucune
raison d'être supérieur).

**Verdict Gate 1 : FAIL — intrabar artefact.** L'edge n'existe que parce que l'engine
suppose une exécution **généreuse** à un niveau intra-bar qui, daily, n'est pas observable.
Avec un fill réaliste (close du jour ou next-open), la stratégie **perd**.

> Ce gate à lui seul est suffisant pour DISCARD : un signal qui ne survit pas à un fill
> next-open n'est pas tradable en CFD daily FTMO.

---

## 2. Gate 2 — Two-sided split (L25) · **FAIL**

Le rapport S001 mentionne que les **indices et quelques commodities portent**, **FX et
crypto sont faibles/négatifs**. Les indices ont **monté** 2000-2026. Si l'edge est porté
par les longs sur ces indices, ce n'est pas un edge breakout symétrique — c'est du **beta
long déguisé**.

**Split par direction (3R / 10j, pool global) :**

| Side | Trades | Win | expR | PF | Sharpe |
|---|---|---|---|---|---|
| Longs | 1 689 | **58,4 %** | **+0,0528** | 1,408 | **+1,05** |
| Shorts | 1 588 | 47,0 % | **−0,0096** | 0,940 | −0,18 |
| Both-hit (loss) | 564 | 0 % | (−2× Stretch + cost)/R | — | — |

**Contribution des longs au R poolé total : 341,6 %.** Les shorts soustraient ~241 %, le
both-hit complète à 100 %. Autrement dit :

- Longs seuls : Sharpe ≈ 1,05 (au-dessus de toutes les barres).
- Shorts seuls : Sharpe ≈ −0,18 (perdant).
- Both-hit (pénalité spec) : neutre à légèrement négatif.

Si la « stratégie » consistait à **prendre uniquement les longs**, on aurait un Sharpe 1,05.
Mais ce n'est pas la stratégie Crabel — c'est juste **acheter les indices** post-NR. La
stratégie réelle (symétrique) **donne tout** son edge à un côté de l'orderbook, ce qui n'est
pas un mécanisme breakout robuste mais un mécanisme **directionnel structurel**.

**Test complémentaire (mécanisme économique) :** un buy-and-hold timé des indices US500/
US100/US30/AUS200 sur 2000-2026 a un Sharpe ≈ 0,4-0,6 net de coûts. Les longs Crabel
(Sharpe 1,05) **améliorent** ce buy-and-hold, ce qui suggère que le NR fait un *timing*
correct dans la bonne direction — mais c'est un **filtre sur du long beta**, pas un edge
intrinsèque.

**Verdict Gate 2 : FAIL — long-bias / disguised beta on rising universe.** Le test
two-sided révèle que la moitié shortable de la stratégie ne fonctionne pas, ce qui est
incompatible avec un breakout symétrique. L'edge prétendument breakout est un filtre de
long-trend sur des actifs qui ont monté.

---

## 3. Gate 3 — Cost stress ×1,5 / ×2 (L33) · **PASS** (seul gate qui passe)

Test trivial : multiplier `cost_bps` par 1,5 et 2,0 avant le run.

| Multiplicateur | expR | PF |
|---|---|---|
| ×1,0 (ref) | +0,0068 | 1,050 |
| ×1,5 | +0,0052 | 1,038 |
| ×2,0 | +0,0036 | 1,026 |

L'edge **survit** au stress ×2,0 (PF reste > 1, expR reste positive). Mais l'edge est si
mince que l'amortissement par les coûts ne suffit pas seul à tuer la stratégie — d'autres
gates le font.

**Verdict Gate 3 : PASS.** *Note :* le PF à ×2,0 est 1,026 (vs 1,050) — l'edge net est
~50 % de l'edge nominal. À ×3,0 (non testé mais extrapolable linéairement), l'expectancy
tomberait à ~+0,0020 R, et à ×3,4 elle s'effondrerait. C'est-à-dire : **le coût marginal
qui tue la stratégie est ~ +5 bps round-turn supplémentaires**, ce qui n'est pas absurde
en CFD FTMO (slippage sur indices micro-cap, dérive de spread en news, etc.). Le PASS de
ce gate ne sauve pas le verdict global.

---

## 4. Gate 4 — DSR Bailey-Lopez de Prado (N_trials = 42) · **FAIL** — *catastrophique*

42 cellules de grille ont été testées (7 Target × 6 Time). Le rapport S001 met en avant
« 100 % des cellules positives » et la « meilleure cellule » (Target=6R / Time=40j →
+0,0387 R, PF 1,16). Sous quelle probabilité ces statistiques sont-elles compatibles avec
**du bruit pur** ?

**Formule Bailey-Lopez de Prado** (DSR, 2014). Sous H₀ « toutes les cellules sont des
tirages indépendants de Sharpe ≈ 0 », l'espérance du **maximum** de 42 essais est :

```
E[max(SR)] ≈ √(2·ln N) · (1 − γ/√(2·ln N))    avec γ = 0,5772 (Euler-Mascheroni)
```

Pour N=42 : `E[max(SR)] ≈ 2,157`. Le Sharpe observé est **0,216**. La déflation :

```
DSR_z = (SR_obs − E[max]) / σ_SR
```

avec `σ_SR ≈ √((1 − skew·SR + (kurt−1)/4·SR²) / (n−1))`. Avec n=3841 trades, skew=0,45,
kurt=5,69, on a `σ_SR ≈ 0,019`. Donc :

```
DSR_z = (0,216 − 2,157) / 0,019 ≈ −122,9
```

**DSR z-score = −122,9.** Probabilité que SR_obs > 0 *après* déflation : ≈ 0.

**Lecture :** le « 100 % positif » et le « best cell +0,0387 R » sont **catastrophiquement**
en-dessous de ce que 42 tirages aléatoires produiraient sur la même base de trades.
La cellule « best » n'est même pas dans le top-décile attendu pour un test de 42 essais
sur du bruit gaussien.

**Verdict Gate 4 : FAIL — DSR z = −122,9.** Le résultat poolé est **indistinguable de
zéro après correction pour multiplicité**. La mise en avant de la « meilleure cellule »
dans le rapport S001 est trompeuse : sous H₀, on attendrait `SR_max ≈ 2,16` et on observe
0,22.

> *Caveat :* le DSR Bailey-LdP est conservateur car il suppose des essais indépendants.
> Les 42 cellules Target × Time ne sont pas indépendantes (corrélation des PnL inter-cellules
> élevée). La correction réelle est moins sévère qu'un Bonferroni naïf, mais reste très
> dommageable au verdict. Une variante moins agressive (e.g., effective N=10 après PCA) ne
> sauverait pas non plus ce ratio.

---

## 5. Gate 5 — OOS split 2000-2015 / 2016-2026 (L31) · **FAIL**

Split temporel sur la date d'entrée :

| Split | Trades | expR | PF | Sharpe |
|---|---|---|---|---|
| Train 2000-2015 | 1 822 | **+0,0206** | 1,158 | **+0,58** |
| Test 2016-2026 | 2 019 | **−0,0056** | 0,960 | **−0,21** |

**Sign flip net.** L'edge prétendument robuste mesuré sur 2000-2026 est **entièrement
porté par 2000-2015**. La période OOS la plus récente (2016-2026, 11 ans, 2 019 trades)
**perd de l'argent** net. C'est une décomposition cohérente avec :

1. **Beta long indices 2000-2015** : forte trend dans les indices, NR-ORB capte le démarrage.
2. **Régime 2016-2026** : vol structurellement plus basse, gap-fade dominant (cf. les FTMO
   tests précédents qui ont montré que post-event reversal LOSES sur 2020-2025 — les
   markets continuent post-impulse, pas fade).
3. **HFT compresse l'ORB** : pré-2010, l'opening range breakout existait sur des frottements
   réels ; post-2010, les algos compressent le breakout naissant.

**Verdict Gate 5 : FAIL.** Edge fortement biaisé période-spécifique. Train 2000-2015 → test
2016-2026 = flip de signe complet. **Non déployable** sur le régime actuel.

---

## 6. Gate 6 — Block bootstrap 95 % CI · **FAIL** (CI straddles zero)

Block bootstrap (Politis-Romano, block=5 trades) sur les 3 841 R par trade poolés,
5 000 ré-échantillons :

```
Bootstrap mean expR : +0,0067
95 % CI            : [−0,0050, +0,0186]
```

L'IC inclut zéro. L'expectancy poolée **n'est pas statistiquement différente de zéro** au
seuil 5 %. La probabilité que l'edge mesuré (+0,0068 R) soit un tirage aléatoire de la loi
de bruit observée est non-négligeable.

**Verdict Gate 6 : FAIL.** Le « +0,0068 R » n'est pas un signal — c'est une moyenne dont
l'IC à 95 % traverse zéro. Combiné au DSR (gate 4), c'est cohérent.

---

## 7. Synthèse des 6 gates

| Gate | Verdict |
|---|---|
| 1 — Délai+1 / fill close | **FAIL** (collapse signe, Sharpe −0,72) |
| 2 — Two-sided split | **FAIL** (long-bias 341 %, shorts perdants) |
| 3 — Cost stress ×1,5 / ×2 | **PASS** (survit ×2,0, PF 1,026) |
| 4 — DSR (N_trials = 42) | **FAIL** (DSR z = −122,9) |
| 5 — OOS 2016-2026 | **FAIL** (flip de signe, Sharpe +0,58 → −0,21) |
| 6 — Bootstrap CI | **FAIL** (CI [−0,0050, +0,0186] straddles 0) |

**FAILS : 5 / 6** · **BORDERLINES : 0 / 6**

---

## 8. Verdict d'audit final

**🚨 DOWNGRADE Cowork KEEP (borderline) → DISCARD (artefact intrabar + beta long déguisé,
mort OOS, DSR catastrophique).**

**Lecture en une phrase :** la stratégie Crabel 2-Bar NR + ORB en daily n'est pas un edge —
c'est un **artefact d'exécution intrabar** (fill au stop level) qui, *quand on retire cet
artefact*, **inverse complètement le signe**. L'edge résiduel mesuré sur 2000-2026 est
**long-only beta** sur des indices qui ont monté, **mort post-2015**, et **statistiquement
indistinguable de zéro après correction pour multiplicité**.

**Mécanisme proposé (négatif rigoureux) :**

- Le NR pattern identifie des jours de compression de volatilité.
- L'ORB déclenche un breakout intrabar.
- L'engine remplit **exactement au niveau du stop**, ce qui surprime sur la mesure
  observable en daily (le high qui touche un stop est par construction au-dessus de ce stop ;
  le close du jour n'a aucune raison de l'être).
- Sur 2000-2015, le marché indices a un drift haussier suffisant pour que les longs Crabel
  bénéficient de ce drift résiduel post-NR. C'est du timing sur du beta, pas un edge
  symétrique.
- Sur 2016-2026, le régime structurel a changé : vol plus basse, post-event continuation
  domine vs reversal (cohérent avec les 25/142 strategies AMTP-significant negative sur le
  batch FTMO 2026-06-04). L'edge meurt.

**Recommandation pipeline :** rejeter la stratégie. Le rapport REPORT_S001 reste valide
comme **mesure** (les chiffres sont reproductibles), mais son **verdict** « KEEP borderline »
ne tient pas sous nos gates. Le pipeline doit ajouter L26 (délai+1) et L25 (two-sided
split) comme gates **obligatoires** avant tout verdict, en plus des barres existantes.

---

## 9. Audit des hypothèses critiques du rapport Cowork

Pour chaque hypothèse Cowork (cf. REPORT_S001 §9, A1-A9), notre verdict :

| A | Hypothèse Cowork | Audit |
|---|---|---|
| A1 | Look-ahead (signal i-1 → entry i) | ✓ Vérifié — le code est propre |
| A2 | Stop-avant-target (intrabar conservateur) | ✓ Conservateur — pas la source d'inflation |
| A3 | Frontière de bougie UTC vs EET | Non testé ici — peu d'impact attendu vu Gate 1/5 |
| A4 | Continuité futures yfinance | Non testé — non pertinent vu Gate 1/5 |
| A5 | Petits échantillons (XPD 25, USDCHF 31, EURGBP 25) | Confirmé : top-instruments fragiles, mais le poolé domine |
| A6 | Coûts ×1.5 / ×2 | ✓ Testé Gate 3 — PASS (seul) |
| A7 | Couverture 30/40 | Non bloquant |
| A8 | `≤` vs `<` pour NR | Non testé — peu d'impact attendu (3-5 % de trades) |
| A9 | Sharpe poolé conservateur | Note : la déflation Bailey-LdP est plus dommageable que A9 ne le suggère |

**Cowork a fait le diagnostic juste sur A1, A2, A6 ; mais a sous-estimé l'impact
catastrophique de la non-exécution de A6 + A1' (délai+1) + A5' (multiplicité grille).**

---

## 10. Reproduction de l'audit

```bash
cd <HOME>/Desktop/Algo_claude/data/oxfordstrat_109/code
python audit_s001.py
```

Sorties :
- `code/audit_s001.py` — script complet (variantes simulateur + 6 gates)
- `results/audit_s001_gates.csv` — table verdicts
- `results/audit_s001_pooled_by_variant.csv` — pooled metrics par variant

**Aucune modification de `code/ftmo_lab.py` ni du store `ohlc/`.** Les variantes V1a/V1b
sont implémentées dans un sim auxiliaire `_sim_core` qui réutilise `ftmo_lab.atr`,
`ftmo_lab.RISK_FRAC`, `ftmo_lab.round_turn_cost_bps`, et la fonction `crabel_signals` de
`strat_s001_crabel_nr_orb.py`.

---

*Fin de l'audit S001. Pipeline standard : appliquer L25, L26, L31, L33, DSR-grille,
bootstrap comme gates obligatoires sur S002, S003, ... avant tout verdict KEEP.*
