# ORB V2+E7 — Grille p(funded) FTMO 2-step (horizon × sizing × coût) — 2026-06-03

**Continuation de** `data/ftmo_research/ORB_at_0p4bps_2026-06.md`. Même ledger canonique `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades NQ databento 2010-2026 V2 baseline + lift E7 +0.015 R/trade). Spec **FIGÉE V2+E7** (L10/L19 respect). MC block-bootstrap blocs 21 trades, **12000 paths par cellule**, seed fixé, chemins contigus (NOT IID).

**Règles FTMO 2-step SETTLED** : Phase 1 +10% / Phase 2 +5% ; daily 5% (anchored midnight balance) ; floor STATIQUE $9k sur $10k (max total −10%) ; **no time limit** ; **min 4 trades/phase**. Sizing = fixed dollar risk = % capital initial. Account $10k.

**⚠ Le coût est un AXE** — pas une hypothèse. 0.4 bps = borne haute mesurée à 18h (session calme), PAS à 15h30 l'open où l'ORB entre. **À lire dès la mesure 15h30 disponible.**

ORB ≈ 1 trade / RTH day. Horizons en trades = semaines × 5 ; terminal = 5 ans × 2 phases.

---

## Table principale — p(funded) cumulé [horizon × sizing] par coût

### Coût = 0.4 bps RT (borne haute mesurée hors-open) — mean_R V2+E7 = +0.0552

| Sizing | 1w | 2w | 4w | 8w | 12w | 26w | **Terminal** | Placebo zero-μ | Lift signal | P1 pass 2015 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0% | 0.0% | 0.0% | 0.4% | 4.7% | 12.1% | 36.0% | **57.2%** | 44.3% | +12.8 | **9.3%** |
| 1.5% | 0.0% | 0.4% | 4.2% | 17.2% | 28.4% | 44.9% | **47.8%** | 39.2% | +8.6 | **16.9%** |
| 2.5% | 0.0% | 3.5% | 16.2% | 32.7% | 37.7% | 39.2% | **39.3%** | 21.2% | +18.0 | **31.4%** |

### Coût = 1.0 bps RT — mean_R V2+E7 = +0.0417

| Sizing | 1w | 2w | 4w | 8w | 12w | 26w | **Terminal** | Placebo zero-μ | Lift signal | P1 pass 2015 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0% | 0.0% | 0.0% | 0.4% | 4.2% | 10.7% | 31.4% | **50.9%** | 32.5% | +18.4 | **7.2%** |
| 1.5% | 0.0% | 0.3% | 3.9% | 15.9% | 26.4% | 41.1% | **43.8%** | 31.3% | +12.5 | **15.4%** |
| 2.5% | 0.0% | 3.1% | 14.9% | 29.8% | 34.8% | 36.5% | **36.5%** | 17.5% | +19.0 | **29.4%** |

### Coût = 2.0 bps RT — mean_R V2+E7 = +0.0192 (frontière approche)

| Sizing | 1w | 2w | 4w | 8w | 12w | 26w | **Terminal** | Placebo zero-μ | Lift signal | P1 pass 2015 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0% | 0.0% | 0.0% | 0.4% | 3.4% | 8.5% | 25.7% | **40.7%** | 29.8% | **+10.8 ⚠** | **4.5%** |
| 1.5% | 0.0% | 0.2% | 3.2% | 13.5% | 22.3% | 34.3% | **36.6%** | 28.8% | **+7.8 ⚠** | **11.9%** |
| 2.5% | 0.0% | 3.0% | 13.7% | 26.4% | 30.5% | 32.1% | **32.1%** | 19.5% | **+12.6** | **25.7%** |

### Coût = 3.0 bps RT (conservatif open) — mean_R V2+E7 = −0.0032 ❌ FRONTIÈRE DE MORT

| Sizing | 1w | 2w | 4w | 8w | 12w | 26w | **Terminal** | Placebo zero-μ | Lift signal | P1 pass 2015 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0% | 0.0% | 0.0% | 0.4% | 2.9% | 7.0% | 19.4% | **31.0%** | 33.4% | **−2.4 ❌** | **3.2%** |
| 1.5% | 0.0% | 0.2% | 3.0% | 11.6% | 18.9% | 29.2% | **31.0%** | 31.1% | **−0.1 ❌** | **9.6%** |
| 2.5% | 0.0% | 2.7% | 12.1% | 23.5% | 27.2% | 28.4% | **28.4%** | 21.2% | +7.1 | **22.7%** |

---

## Frontière de mort — surlignée

```
COÛT (bps RT)    │  0.4    1.0    2.0    3.0    4.0*   6.0*
mean_R V2+E7     │ +0.055 +0.042 +0.019 -0.003 -0.026 -0.071
p(funded) 1.0%   │ 57.2%  50.9%  40.7%  31.0%  23.4%  11.6%
Placebo zero-μ   │ ~44%   ~33%   ~30%   ~33%   ~29%   ~29%
Signal lift      │ +13 pts +18 pts +11 pts -2 pts  -6 pts -17 pts
                                          ↑
                                  ━━━━━━━━━━━━━━━━━━━━
                                  FRONTIÈRE DE MORT
                                  signal indistinguable
                                  du bruit container
                                  (et sous-placebo)
                                  ━━━━━━━━━━━━━━━━━━━━
```
(*) extrapolation step3 du délivrable précédent.

**Le signal s'éteint à coût ≈ 2.5 bps RT.** Au-delà, p(funded) ≤ placebo container (~30%) = math no-bust pure (DLL 5% + floor 10% + unlimited time + min 4j). À **3 bps sizing 1%, real (31.0%) tombe SOUS le placebo (33.4%)** — le coût a complètement détruit l'edge.

---

## Résumé [coût × sizing] : terminal + bust + temps

| Coût | Sizing | p(funded) | p(bust) | p10 (trades / sem) | Médian (trades / sem / mois) | p90 (trades / sem) |
|---:|---:|---:|---:|---:|---:|---:|
| **0.4** | 1.0% | **57.2%** | 43% | 44 / 9w | **105 / 21w / 4.9mo** | 229 / 46w |
| 0.4 | 1.5% | 47.8% | 52% | 22 / 4w | 52 / 10w / 2.4mo | 112 / 22w |
| 0.4 | 2.5% | 39.3% | 61% | 11 / 2w | 24 / 5w / 1.1mo | 48 / 10w |
| 1.0 | 1.0% | 50.9% | 49% | 44 / 9w | 107 / 21w / 5.0mo | 232 / 46w |
| 1.0 | 1.5% | 43.8% | 56% | 21 / 4w | 51 / 10w / 2.4mo | 111 / 22w |
| 1.0 | 2.5% | 36.5% | 64% | 11 / 2w | 24 / 5w / 1.1mo | 49 / 10w |
| 2.0 | 1.0% | 40.7% | 59% | 43 / 9w | 105 / 21w / 4.9mo | 231 / 46w |
| 2.0 | 1.5% | 36.6% | 63% | 21 / 4w | 51 / 10w / 2.4mo | 114 / 23w |
| 2.0 | 2.5% | 32.1% | 68% | 11 / 2w | 23 / 5w / 1.1mo | 50 / 10w |
| **3.0** | 1.0% | **31.0%** ❌ | 69% | 42 / 8w | 106 / 21w / 4.9mo | 238 / 48w |
| **3.0** | 1.5% | **31.0%** ❌ | 69% | 21 / 4w | 50 / 10w / 2.3mo | 110 / 22w |
| 3.0 | 2.5% | 28.4% | 72% | 11 / 2w | 23 / 5w / 1.1mo | 48 / 10w |

(p10/p90 = percentiles du nombre de trades pour atteindre funded **parmi ceux qui passent** ; trades = trading days RTH ; semaines = trades / 5 ; mois = semaines / 4.3.
Lecture : à coût 0.4 bps sizing 1.0%, les 10% les plus rapides sont funded en 9 semaines, médiane **5 mois**, les 10% les plus lents en 46 semaines (~10.5 mois). À sizing 2.5% c'est 5× plus rapide mais bust 61%.
**Note** : la médiane temps est ~invariante au coût mais varie 5× avec le sizing.)

---

## Décomposition placebo par coût — signal vs container math

Le placebo Gaussien zero-μ avec **std matché au coût** mesure ce qu'on récupère par pure math du conteneur FTMO (unlimited time + floor static 10% + DLL 5% + min 4j) sans aucun edge. Comparer à la cellule réelle isole la contribution du signal.

| Coût | mean_R V2+E7 | Real terminal | Placebo terminal | **Signal lift** | Verdict |
|---:|---:|---:|---:|---:|---|
| 0.4 bps | +0.055 | 39 – 57 % | 21 – 44 % | **+9 à +18 pts** | Signal présent mais placebo MC élevé (voir note) |
| 1.0 bps | +0.042 | 37 – 51 % | 18 – 33 % | **+13 à +19 pts** | Signal franchement identifiable |
| 2.0 bps | +0.019 | 32 – 41 % | 20 – 30 % | **+8 à +13 pts** ⚠ | Frontière : signal commence à se confondre |
| **3.0 bps** | **−0.003** | **28 – 31 %** | **21 – 33 %** | **−2 à +7 pts** ❌ | **Signal mort : real ≤ placebo à sizing 1.0 / 1.5%** |

**Note variance MC du placebo** : chaque cellule placebo tire un échantillon Gaussien zero-μ indépendant de 4013 valeurs. La SE de la mean tirée est ≈ σ/√4013 ≈ 0.019, ce qui produit une variation de ±5–10 pts de p(funded) entre cellules placebo *avec mean_R proche de zéro*. La référence "container math" stable se situe **autour de 29–33% à sizing 1.0%** (cohérent avec délivrable précédent : 24% pour un autre seed). Le `+9 pts` à 0.4 bps sizing 1% est probablement sous-estimé du fait du placebo à 44% — la vraie référence est ~30%, ce qui donnerait un lift ~+27 pts. Pour interpréter prudemment : **regarder la TENDANCE entre coûts, pas le chiffre absolu d'une cellule placebo isolée.**

---

## Régime fragility — Stress 2015 (worst year)

À côté de la moyenne 16 ans, voici ce qui se passe si tu démarres ton challenge dans un régime comme 2015 (n=254 trades, mean_R 2015 négatif partout) :

| Coût | mean_R 2015 | P1 pass 2015 @ 1% | @ 1.5% | @ 2.5% | Bust @ 1% |
|---:|---:|---:|---:|---:|---:|
| 0.4 | −0.087 | **9.3%** | 16.9% | 31.4% | 90.7% |
| 1.0 | −0.101 | 7.2% | 15.4% | 29.4% | 92.8% |
| 2.0 | −0.124 | 4.5% | 11.9% | 25.7% | 95.5% |
| 3.0 | −0.147 | **3.2%** | 9.6% | 22.7% | 96.8% |

**La moyenne 16 ans (57.2 % à 0.4 bps sizing 1%) cache une loterie de régime** : sous le régime 2015, P1 pass tombe à **9.3 %** à sizing 1% (×6 dégradation). Le ratio se conserve à tous les coûts : sizing 1% est toujours le plus impacté par 2015, sizing 2.5% le moins (mais paie au bust). **3/17 années sont négatives même à 0.4 bps** (2010, 2013, 2015).

---

## Verdict en 1 ligne

> **Lis la cellule au coût que ta mesure 15h30 confirmera. Au-dessus de ≈ 2.5 bps RT à l'open, l'ORB V2+E7 ≡ placebo container ; à 3 bps real_pf passe SOUS le placebo (−2 pts à sizing 1.0/1.5%). En-dessous de 2 bps, le signal ajoute +10 à +20 pts — mais la médiane 5 mois à sizing 1 % et la queue 2015 (P1 pass 9–10 %) restent inchangées.**

---

## Comment lire ce tableau dès la mesure du coût à 15h30

1. Le candidat mesure spread + slippage à 15:30:00 / 15:33:00 / 15:35:00 EET sur US100.cash démo, 5 sessions ≥ 20 trades chacune.
2. Convertit en bps RT : `bps_RT = (spread_points + slip_points) / price × 1e4 × 2`.
3. Localise la ligne du tableau au coût mesuré (ou interpole).
4. **Si bps_RT ≤ 1.0** : signal franchement positif (lift +13 à +19 pts) — re-examine sérieusement.
5. **Si 1.0 < bps_RT ≤ 2.0** : signal atténué (+8 à +13 pts) — vérifie médiane 5 mois et queue 2015.
6. **Si bps_RT ≥ 2.5** : signal indistinguable du placebo — **NO-GO** ; à 3 bps, real ≤ placebo à sizings 1.0/1.5%.
7. **Quel que soit le coût** : à sizing 1%, médian 5 mois ; bust 43–69 % selon coût ; régime 2015 collapse à 3–9 %.

---

## Honnêteté résiduelle

- Spec FIGÉE V2+E7 (E7 lift = +0.015 R uniform, doc4 canonical). **Aucune modification du signal.**
- `min_4j/phase` enforced ; `floor STATIQUE $9k` (PAS taper) ; `unlimited time` ; `block bootstrap 21j contigu` ; seed fixé. Toutes les hypothèses du dossier sont SETTLED.
- 12000 paths × 12 cellules réelles + 12 placebos + 12 stress 2015 = **432 000 chemins simulés**. Variance MC sur p(funded) ≈ ±0.5 pts pour real, ±5 pts pour placebo (qui dépend du draw).
- Le placebo varie entre 17 % et 44 % selon (coût, sizing) — c'est dû au noise sampling du draw Gaussien indépendant par cellule, pas à un vrai changement de "free lunch container". La référence stable est **~29–33 % à sizing 1%, ~18 % à sizing 2.5%**.
- Mesure 0.4 bps = mesure démo session calme, **pas** open. Le verdict 1-ligne ci-dessus traite explicitement le coût comme axe à lire.
- Toutes les versions / horizons / sizings convergent sur la même conclusion structurale : **l'edge ORB existe à coût bas, disparaît à coût réaliste open ≥ 2.5–3 bps**. Le ceiling régime ~33% (ORB_reconciliation full sample) est cohérent avec **cellule (3 bps, 1.0–1.5%) = 31%** dans cette grille.

---

## Artéfacts

- `data/ftmo_research/audit/orb_ppass_grid_v2.py` — script MC grille (costs = 0.4, 1, 2, 3 bps)
- `data/ftmo_research/audit/orb_ppass_grid_main_v2.csv` — 24 lignes (12 real + 12 placebo) × {variant, cost_bps, sizing, mean_R, pf_1w…pf_26w, pf_terminal, p1_pass, p1_bust, p_bust_total, med/p10/p90 trades}
- `data/ftmo_research/audit/orb_ppass_grid_stress2015_v2.csv` — 12 lignes (4 coûts × 3 sizings) régime 2015
- `data/ftmo_research/audit/orb_ppass_grid_v2_log.txt` — sortie d'exécution complète
- Réutilise : `data/ftmo_research/audit/nq_v2_trades.parquet` (ledger canonical) + `orb_v2e7_0p4bps_per_trade.parquet`
- Cohérent avec : `data/ftmo_research/ORB_at_0p4bps_2026-06.md` + `ORB_reconciliation_2026-06.md` + memory `[[orb-realconstraints-2026-06]]` (placebo floor-taper 97 % vs ici floor-statique 29–33 % — montre que **le type de floor compte autant que le coût**)

### Note sur la version

Cette grille remplace la première version (`orb_ppass_grid_main.csv` avec coûts {0.2, 0.5, 1, 2}). La présente v2 utilise les coûts {**0.4, 1, 2, 3**} qui couvrent :
- 0.4 bps = borne haute mesurée hors-open (à confirmer 15h30)
- 1.0 bps = ordre intermédiaire futures direct (NQ commission seule)
- 2.0 bps = médiane historique des grilles cost
- 3.0 bps = **frontière de mort identifiée** (real ≤ placebo à sizing 1.0/1.5%)
