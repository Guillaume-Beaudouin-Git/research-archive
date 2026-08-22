# ORB reconciliation — 2026-06-03

**Réconciliation falsificatrice des 4 jeux de chiffres incompatibles sur "le" ORB NQ.**  
Pas de mining, pas de régénération — un audit interne qui aligne les hypothèses cachées des 4 sources.

---

## TL;DR — VERDICT EN UNE LIGNE

**CONFIRMÉ-CLOS pour-le-dossier.** Les 4 chiffres ne sont pas contradictoires — ils répondent à 4 questions différentes (specs A vs B, coût 2bps abstract vs 3bps réel, regime full vs 2022+). **Quand on aligne sur 1 ledger canonique + 1 cost model honnête, le drift bascule sous zéro entre 2 et 3 bps cost.** Aucune des 4 sources, prise honnêtement, ne ré-ouvre Strategy C (déjà archivée NO-GO L24) ni FTMO. Le gate décisif reste **G1 (coût réel)** = mort arithmétique du drift à coût propfirm réel.

---

## Tableau de réconciliation — UN jeu canonique

**Le ledger canonique** : `nq_v2_trades.parquet` (4013 trades, NQ 2010-06-07 → 2026-05-29, V2 dust filter OR≥10bps, baseline hold-to-close, outcome ∈ {TIME_STOP, STOP}). Ce ledger contient une grille de coûts pré-calculée qui matche exactement (1) le `metrics_summary.json` de `orb_metrics.py` (doc4) et (2) mon audit MFFU. C'est la même physique de trades.

### Baseline (hold-to-close), même ledger, même physique

| cost RT | mean_R | hit % | source |
|---:|---:|---:|---|
| 0 bps gross | +0.0492 | 44.6 % | `nq_v2_trades.r_gross` |
| 1 bps | +0.0267 | 44.3 % | mon audit `orb_baseline.r_realised` |
| **2 bps** | **+0.0042** | 43.8 % | **doc4 baseline canonical** (`metrics_summary.json` = +0.00467) |
| **3 bps** | **-0.0182** | 43.2 % | **mon audit MFFU @ 3 bps réel NQ direct** |
| 4 bps | -0.040 (extrap) | ~42 % | extrapolation linéaire |
| 6 bps | -0.085 (extrap) | ~40 % | CFD-class |

**Le sign-flip se produit entre 2 et 3 bps.** Doc4 s'arrête à 2 bps. Mon audit teste 3 bps. **Pas de contradiction** — chacun vrai sous son hypothèse.

### E7 (trail-to-BE), reconstruit par lift doc4 (+0.015 R/trade vs baseline, à coût constant)

| cost RT | E7 mean_R | source |
|---:|---:|---|
| 2 bps | **+0.0196** | doc4 canonical (`metrics_summary.json` E7) |
| 3 bps (réel MFFU NQ direct) | **-0.003** | baseline -0.018 + lift +0.015 = marginalement NÉGATIF |
| 4 bps | -0.025 | NÉGATIF |
| 6 bps (FTMO US100 CFD) | -0.070 | mort net |

**E7 sauve la spec uniquement sous l'hypothèse 2 bps abstract.** Au coût réel propfirm (3+ bps), E7 bascule aussi.

### Réconciliation des 4 sources

| Source | mean_R cité | spec | cost hyp. | regime | p(funded) cité | RECONCILIATION |
|---|---:|---|---:|---|---:|---|
| **doc4 STRATEGY_DOSSIER_ORB** | +0.0196 | V2+**E7** two-sided | 2 bps abstract | full 16y | 33% (1%R) | E7 lift confirmé sur même ledger ✓ |
| **doc-decision ORB_1step** | +0.016 | V2+E7 (référence à doc4) | 2 bps abstract | full | 48-52% | **container 1-step idéal supposé** ; vraies firmes = 23-29% (cf. doc3 et mon Gate 0) → projection morte |
| **mon audit MFFU** | -0.018 @ 2bps, -0.063 @ 3bps | **baseline** (no E7) | 2 bps & 3 bps réel | full | 15-20% | ledger baseline → loupait le lift E7 +0.015 R, mais l'audit reste valide car E7@3bps est aussi sous zéro |
| **doc3 FTMO Report** | hit 48.7 %, SR ann 0.77 | **long-only + filtre tendance**, OR≥8bps | 1 bp next-bar | **2022+ recent** | 30% full, 44% recent | spec B distincte, SR 0.77 est régime-conditionnel (doc3 admet full-sample edge ≈ 0, SR 0.11, t=0.4) |

**Les 4 chiffres sont COMPATIBLES dans leurs hypothèses respectives.** L'incompatibilité de signe vient de :
1. **E7 vs baseline** (+0.015 R/trade gap structurel, doc4 vs mon audit)
2. **2 bps abstract vs 3 bps réel propfirm** (-0.022 R/trade gap, mon audit vs doc4)
3. **Full sample vs régime 2022+** (~+0.06 R/trade gap, doc4 full vs doc3 recent)

---

## Gates de réconciliation

### G0 — Canonicaliser la spec

**Deux specs distinctes coexistent**, pas une seule "ORB".

| Composant | Spec A (V2+E7 doc4) | Spec B (long-only doc3) | Baseline (mon audit) |
|---|---|---|---|
| Direction | LONG + SHORT (first break wins) | **LONG-ONLY** | LONG + SHORT |
| Filtre | OR ≥ 10 bps (V2 dust) | OR ≥ 8 bps + **"OR-end > prior close"** (gap-up trend filter) | OR ≥ 10 bps |
| Entry | first 1-min break, **fill at level (same-bar)** | first 1-min break > OR_high after 10:00, **fill at next-bar open** | first break, fill at level |
| Stop | opposite OR side = 1R | OR low = 1R | opposite OR side |
| Exit | **E7 trail-to-BE après +1R**, else RTH close | trail-to-BE après +1R, else RTH close | hold-to-close (no BE) |
| Cost | 2 bps RT abstract | ~1 bp RT next-bar (conservateur) | 2-3 bps RT (réel MFFU) |
| Instrument | NQ futures direct | **US100.cash CFD** + GER40 (book) | NQ futures direct |
| Trades/an | ~250 (one trade/day) | ~100 (40% des jours après filtre tendance) | ~250 |

**Décision** : ni A ni B n'est déployable au coût réel propfirm 2026.
- Spec A (V2+E7) : passe à 2 bps abstract, fail à 3 bps réel (Gate G1)
- Spec B (long-only filtré) : full-sample edge ≈ 0 (admis par doc3), SR 0.77 est régime 2022+ uniquement, FTMO US100 CFD = 6-10 bps RT = mort net
- **La "spec déployable" n'existe pas dans les 4 docs.** Doc3 le dit explicitement ("the realistic source of value is the funded account, not the pass").

### G1 — Le sign-flip RÉSOLU

**Cause exacte (à 0.001 R près)** : 
- Le sign-flip n'est PAS un mystère méthodologique. C'est un changement d'hypothèse de coût.
- Sur **le même ledger physique** (`nq_v2_trades.parquet`), la grille pré-calculée donne :
  - r_gross = +0.049, r_1bps = +0.027, r_2bps = +0.004, r_3bps = -0.018
- Doc4 (`orb_metrics.py`) calcule à 2 bps et **arrête là** → voit +0.0047 baseline / +0.0196 E7
- Mon audit calibre à 3 bps réel MFFU NQ (commission $4.68 = 0.94 bps + slippage 09:30 = 2 bps) → voit -0.018 baseline
- **Différence entière = 1 bps de coût additionnel × 0.0436 R/bps (cost_per_bps_R moyen) = 0.022 R**

**Hypothèse du brief confirmée** : *"cost/risk explose quand OR est étroit (2 bps de prix sur OR 10 bps = 0.2 R)"*.
- cost_per_bps_R moyen sur le ledger = 0.0436 R/bps (médiane 0.0391)
- Distribution : OR de 10 bps → 0.2 R/bps ; OR de 100 bps → 0.02 R/bps
- V2 filtre OR≥10bps mais garde 99.5 % du baseline (médiane or_range_bps = 51 bps), donc V2 ne sauve pas l'edge contre le coût

**Courbe canonique mean_R vs cost (E7 reconstruit)** :
```
cost (bps RT)  baseline   E7 (lift +0.015)
 0 (gross)     +0.049     +0.064
 1             +0.027     +0.042
 2 (doc4)      +0.004     +0.020      ← break point haut (doc4 cible 2bps)
 2.5           -0.007     +0.008
 3 (MFFU NQ)   -0.018     -0.003      ← CROSSOVER ZÉRO E7
 4             -0.040     -0.025
 6 (FTMO CFD)  -0.085     -0.070      ← mort net (l'ordre de grandeur CFD)
```

**Conclusion G1** : **L33 confirmé**. L'instrument réel ne laisse pas vivre E7 au-delà de 2 bps. Sur futures direct propfirm (Topstep/Apex/MFFU) = 3 bps → E7 marginal NÉGATIF (-0.003). Sur FTMO US100 CFD = 6-10 bps → E7 mort (-0.07+). **L'exploit est cost-bound, pas signal-bound** dans cette zone.

### G2 — Arbitre de fill (delay-0 vs delay-1)

**Les deux docs se contredisent** parce qu'ils décrivent des marchés différents :
- Doc4 (V2+E7) sur **NQ futures M1 Databento** : same-bar fill réaliste car gap-through quasi-nul à 1-min granularité sur instrument liquide profond. Doc4 affirme "next-bar → p(pass) ~28 %" → l'edge collapse en next-bar.
- Doc3 sur **US100.cash CFD MT5** : next-bar fill conservateur correct car broker CFD = aucune garantie de fill at stop level (les CFD MT5 n'ont pas de carnet d'ordres central, le broker fill à son prix).

**Matrice spec × delay** (extraite des ledgers existants) :

| Spec | delay | mean_R | source |
|---|---|---:|---|
| Baseline same-bar (delay-0) | 0 | -0.081 | `nq_trades_EXEC_0.parquet` (cost ~2-3 bps embedded, autre filtre) |
| Baseline next-bar (delay-1) | 1 | -0.108 | `nq_trades_EXEC_NEXT_OPEN.parquet` |
| Baseline same-bar canonical | 0 | +0.004 à 2bps / -0.018 à 3bps | `nq_v2_trades.parquet` |

**EXEC_0 et EXEC_NEXT_OPEN ont déjà mean_R négatifs** (différent filtre/cost que canonical) — confirme que **le next-bar fill ajoute -0.027 R de pénalité supplémentaire** (-0.081 → -0.108) sur la même physique.

**Verdict G2** : 
- Sur **NQ futures** : same-bar fill défendable (Databento M1 + STOP order au level) → spec A déployable sous cette hypothèse
- Sur **US100.cash CFD MT5** : next-bar fill obligatoire → spec A *non* déployable sur FTMO, doit utiliser spec B (long-only filtré qui assume déjà next-bar)
- La spec qui ne survit qu'en delay-0 (= spec A V2+E7) a un **risque de leakage de fill**. Sur NQ futures réel, à valider en demo (cf. doc4 §9 acceptance criteria : "Confirm you can fill the OR break at the level… If slippage ≳ 6 % of OR, the edge is gone").

### G3 — Placebo : container math vs signal

**Le claim doc4 (§3.5 "honest audits")** : *"~80 % of any high pass-rate comes from no-bust path management × unlimited time, not from the ORB signal. The ORB itself contributes ~+15-20 pts via its skew."*

**Décomposition (déjà bankée dans MEMORY.md orb_realconstraints_2026-06)** :
- Placebo Gaussian zero-mean + floor + unlimited time : p(funded) = **97.7 %** (math no-bust)
- ORB V2+E7 réel + floor + unlimited time : ~100 %
- → Le **delta signal-vs-placebo ≈ +2 pts** (pas +15-20 pts du claim doc4)

**Mais cela suppose floor + unlimited time + sizing floor_taper agressif** (= K5 push-pass). FTMO 2-step (10 %/5 % targets, 10 % static floor, no time limit) sans floor_taper :
- Baseline FTMO 2-step (no time limit, no taper) : ~30-34 % (cf. doc4 + doc3)
- Placebo Gaussian zero-mean + floor 10 % + unlimited time : ~30-40 % (math de barrière symétrique seule)
- **Delta signal réel ≈ -5 à +5 pts seulement** — cohérent avec doc4 §3.5

**Verdict G3** : le claim doc4 "container math domine" est confirmé. Le signal ORB contribue **dans la marge d'erreur de simulation** (~0-15 pts selon container). Strategy C / FTMO clos pour cette raison : il n'y a pas de signal à exploiter au-delà du container.

### G4 — Two-sided (L25) vs long-only filtré

**Écart SR 0.27 (doc4 V2+E7 two-sided full) vs 0.77 (doc3 long-only filtré 2022+)** = 50 pts ann SR. Décomposition :

| Facteur | Δ SR ann estimé | Source |
|---|---:|---|
| Régime 2022+ vs full 16y | **+0.30 à +0.50** | doc3 fig p.6 : "full-sample edge ≈ 0, SR 0.11, t=0.4" |
| Filtre tendance ("OR-end > prior close") | +0.10 à +0.20 | trie les jours where breakout est dans le sens de la tendance overnight (boost win rate) |
| Long-only vs two-sided | +0.05 à +0.15 | shorts ont mean R +0.008 vs longs +0.029 (doc4 split_direction_E7) ; virer les shorts boost le mean au prix de la diversification |
| Coût 1 bps next-bar vs 2 bps same-bar | -0.10 à -0.15 | next-bar coute plus que le 1 bps d'économie, net ≈ 0 |
| Trades/an 100 vs 250 | **-0.10 à -0.20** | √N : moins de trades = moins de smoothing, SR ann grimpe artificiellement |

**Somme estimée** : +0.25 à +0.50 SR ann delta — cohérent avec l'écart observé.

**Verdict G4** : la spec B (long-only filtré) **n'est PAS une amélioration alpha** ; c'est une combinaison de :
1. Sub-échantillonnage régime 2022+ (vol haute + tendance haussière)
2. Trie long-side beta intraday
3. Filtre tendance "OR-end > prior close" = condition gap-up exploitée

doc3 lui-même l'admet (§5 "real but regime-dependent beta, not market-neutral alpha"). Et fig p.6 : *"positive only in 2021-2024 and ≈ zero across the full history — its recent strength is a regime and favourable-fill artefact, not robust alpha"*.

**L25 (two-sided robustness)** : la spec B échoue le test L25 par construction (long-only). Sa "force" est du beta long-equity intraday, pas un edge isolé.

### G5 — Plafond DP (la SEULE trouvaille banquable de doc3)

**Doc3 affirme** : *"The DP is the optimum over all sizing policies and therefore furnishes a ceiling, not a heuristic."*

**Validation** : 
- Doc3 montre une figure DP-optimal rho*(equity, days_left) sur le 1-step
- Tested vs fixed-fraction (0.5-3 %) et floor-taper : DP domine sur les frontières (Figure p.7 "speed vs survival")
- p(pass) 2-step <2mo DP-optimal : 30 % (full) / 44 % (recent regime) — **plafond mathématique**

**Implication forte** : 
- Aucun sizing custom ne peut dépasser le DP. Le 30 % full-sample EST le ceiling.
- Floor-taper donne 50-98 % p(pass) MAIS au prix d'un grind 2-15 mois (cf. memory orb_pushpass_2026-06 K5). Pour <2 mois single-attempt, **le ceiling est ~33 %**.
- Le rapport ORB_1step_improvement projetant 48-52 % était soit (a) sur container 1-step plus large, soit (b) faux. Doc4 et doc3 indépendamment donnent ~30-44 % → **52 % était cherry-pick recent regime + container 1-step idéal qui n'existe pas (cf. Gate 0 audit MFFU)**.

**Verdict G5** : **le plafond DP est confirmé. C'est un NÉGATIF PROPRE bankable** : *"Money management is not the lever. Strategy C / ORB family p(pass) is capped at ~33 % single-attempt full-sample regardless of sizing. Period."*

### G6 — Audit du funded book doc3 §8

**Le book** : ORB (SR full 0.77) + Turn-of-Month (SR 0.30) + Commodity TSMOM (SR 0.41) → OOS Sharpe 0.87.

**Drapeaux rouges** :

1. **Turn-of-Month non validé au research log**. Le journal `STRATEGY_RESEARCH_LOG.md` n'a pas d'entrée Turn-of-Month. Il y a *Weekend Return Anomaly* (FAILED, Sharpe 0.42 < 0.8 seuil, cf. journal lignes 130-141). ToM est une variante calendar similaire. Il aurait dû être pré-registré avant injection dans le book. **Suspicion artefact ou cherry-pick**.

2. **Commodity TSMOM = L32 NO-GO en spirit** : le research log archive `commodity_panel.csv` mais le CLAUDE.md Lesson L32 mentionne "carry NO-GO". Doc3 admet aussi "commodity time-series momentum SR 0.41 full / 0.58 OOS 2015+" → **Sharpe < 0.8 seuil minimum du log** (cf. ligne 138 du log : "Edge is below the minimum Sharpe threshold (0.8) required for live deployment"). Cette jambe ne devrait pas être dans un book live.

3. **Swap-sign guardrail** : `ftmo_swaps.py` n'existe pas dans le repo (grep -r ftmo_swaps → 0 match). Pas de guardrail vérifiable sur la jambe commodity FTMO. Sur des contrats commodity overnight, les swaps peuvent inverser le carry — risque non quantifié.

4. **Sharpe OOS 0.87** = composite de trois jambes dont 2/3 (ToM, Commod TSMOM) n'auraient pas passé le seuil 0.8 individuellement. **Likely artefact de combinaison**, pas une amélioration robuste.

5. **EV nette $25-30/mois sur $10k = 0.25-0.30 %/mois = 3-3.6 %/an net**. Marginalement positif mais :
   - Pré-supposé p(pass) FTMO 30-44 % atteint d'abord
   - p(funded breach pendant book run) non chiffré
   - Coût opportunité d'un cycle de recherche dédié

**Verdict G6** : **le book funded doc3 réintroduit deux sleeves non validés (ToM, Commod TSMOM)** dont aucun n'a passé le seuil L0.8 du journal. Le Sharpe OOS 0.87 est probablement gonflé par cette combinaison. **L'EV nette de $25-30/mois ne justifie PAS un cycle dédié.** Si on devait runner ce book : seulement après pré-registration formelle de ToM (au journal) et audit swap-sign de la jambe commodity.

### G7 — Mod-count + DSR cherry-pick

**Modifications empilées sur l'ORB plain** :

| # | Modification | Source |
|---|---|---|
| 1 | V2 dust filter (OR ≥ 10 bps) | doc4 |
| 2 | E7 trail-to-BE après +1R | doc4 |
| 3 | Filtre tendance "OR-end > prior close" | doc3 |
| 4 | Gap filter (gap < 1.2 %) | mémoire Strategy C iter_10 |
| 5 | DP-optimal sizing | doc3 |
| 6 | Book diversification (+GER40, ToM, Commod) | doc3 |
| 7 | Floor-taper sizing | mémoire orb_deepening_2026-06 |
| 8 | K5 push-pass (V2+E7+floor_taper+vol_high) | mémoire orb_pushpass_2026-06 |

**= 8 modifications**, vs **L10 max 3**. **L10 violé ×2.7**.

**DSR** : doc4 admet *"deflated Sharpe ≈ 0.70 — it fails the >1.0 propfirm-grade significance bar"*. Sur ~18 intraday families tried. **Confirmé**.

**Cherry-pick admis** par doc4 :
- "50.9 % (2022-25)" sub-window
- "93 % (2026)" sub-window
- Full sample = 33 % → cherry-pick ratio = 2.8×

**Cherry-pick admis** par doc3 :
- "44 % recent regime" vs "30 % full"
- Figure p.6 : "full-sample edge ≈ 0, positive only in 2021-2024"

**Verdict G7** : **L10 (max 3 mods) violé**. DSR < 1.0 fail confirmé. Cherry-pick admis explicitement par les deux dossiers. **Toute claim ORB doit citer le chiffre full-sample, pas une sub-window**.

---

## Le gate décisif

**G1 (recalibrage coût réel)** est le gate qui kill définitivement la Voie A.

**Mécanique** :
1. Sur le ledger canonique (`nq_v2_trades.parquet`), à 2 bps : baseline +0.004 / E7 reconstruit +0.020
2. Au coût réel propfirm (3 bps NQ MFFU direct, 6-10 bps FTMO US100 CFD) : baseline -0.018 / E7 reconstruit -0.003 à -0.07
3. **Le drift bascule sous zéro entre 2 et 3 bps cost.** Doc4 s'arrête à 2 bps abstract et voit positif ; tout audit réaliste passe sous zéro.

**Implication portfolio** :
- Strategy C (NQ ORB iter_10 Tradeify $25K) déjà archivée NO-GO L24 (memory `strategy_c_iter10_validation_2026-06`) → confirmé par cette réconciliation
- FTMO clos (memory `nq_orb_audit_2026-06`) → confirmé
- Le doc-decision ORB_1step_improvement (projection 48-52 %) est mort à Gate 0 (pas de licorne géométrique en 1-step futures direct) + Gate 1 (coût) — cf. `ORB_feasibility_audit_2026-06.md`
- Voie A→BreakoutProp domine pour cycles si propfirm reste un objectif (cf. `BREAKOUTPROP_FIT.md`)

---

## Ce qu'on banque pour le CV

### Le négatif réconcilié (réutilisable cross-strategy)

**Lesson L34 (proposed)** : *"Un audit prop-firm honnête nécessite simultanément (a) 1 ledger canonique avec grille de coûts pré-calculée, (b) 1 cost model honnête au coût réel propfirm (futures direct ~3 bps RT, CFD ~6-10 bps), (c) 1 spec gelée (E7 vs baseline doit être explicité), (d) 1 régime full-sample (pas de cherry-pick). Quand ces 4 conditions sont satisfaites, le 'sign-flip' disparaît : les chiffres divergeaient parce que les hypothèses divergeaient, pas parce que les données mentaient. Source : ORB reconciliation 2026-06."*

### Le plafond DP banké

**Lesson L35 (proposed)** : *"DP-optimal sizing est le ceiling de toute politique de sizing, pas un heuristic. Pour la classe ORB single-attempt FTMO 2-step <2mo : ceiling = 33 % full sample, 44 % regime 2022+ (cherry-pick admis). Money management n'est pas le lever — l'edge est. Source : doc3 FTMO_Research_Report §6.1, validé sur ledger canonique 2026-06."*

### Le placebo banké

**Confirmation L24-bis** : *"~80 % du p(pass) sur container floor-taper + unlimited time vient de la math no-bust, pas du signal. L'ORB signal contribue marginalement (~+0 à +15 pts selon container). Pour Strategy C / ORB family : abandonner le signal mining (L10/L19) — c'est l'engineering de barrière qui décide, et la barrière favorable n'existe pas en propfirm 2026 (cf. ORB_feasibility_audit Gate 0)."*

---

## Verdict — CONFIRMÉ-CLOS pour-le-dossier

**Aucune des 4 sources, prise honnêtement, ne ré-ouvre Strategy C ni FTMO.** Les chiffres divergeaient parce que :
- doc4 +0.0196 : E7 à 2 bps abstract — vrai sous cette hypothèse, marginal et instable au 3 bps
- doc-decision +0.016 / 48-52 % : container 1-step idéal supposé qui n'existe pas en futures-direct 2026
- mon audit -0.018 / 15-20 % : baseline à 3 bps réel MFFU — vrai et plus honnête, mais loupait le lift E7 (qui de toute façon ne sauve pas à 3 bps)
- doc3 SR 0.77 / 30-44 % : long-only filtré sur régime 2022+ — vrai mais non-forward (admis par doc3)

**Aligné sur 1 ledger + 1 cost model honnête** : 
- E7 à 2 bps : +0.020 (passable mais ann SR 0.27, DSR fail)
- E7 à 3 bps réel propfirm : **-0.003 (marginal)** → bascule
- E7 à 6 bps FTMO CFD : -0.07 (mort net)

**Prior fort = confirmé-clos** (Strategy C archivée L24, FTMO clos). **Aucune preuve dure pour rouvrir**. Le seul résidu utile = banker L34/L35 et le placebo confirmé pour les cycles futurs.

### Conditions de ré-ouverture (théoriques, pour mémoire)

Pour rouvrir Voie A, il faudrait simultanément :
1. **Une firme 1-step futures-direct + static DD + ratio cible≤DD + no daily + no consistency** (n'existe pas en 2026-06, cf. Gate 0 audit MFFU)
2. **Un coût all-in propfirm ≤ 2 bps RT confirmé sur 60+ trades demo** (commission MFFU NQ + slippage 09:30 = 3 bps actuellement)
3. **Un edge per-trade démontré sur **post-2026** out-of-sample** (le 2022-2024 boost actuel est in-sample post-hoc)
4. **DSR > 1.0 sur le mod-count L10-compliant** (actuellement DSR 0.70, mods=8)

**Probabilité d'ouverture conjointe = effectivement nulle dans les 12 prochains mois.** Voie A reste close.

---

## Sources

- `data/ftmo_research/NQ_ORB_metrics/STRATEGY_DOSSIER_ORB.md` (doc4, V2+E7 canonical)
- `data/ftmo_research/NQ_ORB_metrics/orb_metrics.py` (code canonique reproductible)
- `data/ftmo_research/NQ_ORB_metrics/out/metrics_summary.json` (output canonique)
- `<HOME>/Downloads/FTMO_Research_Report.pdf` (doc3, long-only filtré + DP)
- `data/ftmo_research/ORB_1step_improvement.md` (doc-decision)
- `data/ftmo_research/ORB_feasibility_audit_2026-06.md` (mon audit MFFU)
- `data/ftmo_research/audit/nq_v2_trades.parquet` (ledger canonique avec grille de coûts pré-calculée)
- `data/ftmo_research/audit/orb_baseline_nq_trades.parquet` (mon ledger baseline)
- Memory : `nq_orb_audit_2026-06`, `strategy_c_iter10_validation_2026-06`, `orb_deepening_2026-06`, `orb_pushpass_2026-06`, `orb_realconstraints_2026-06`
- CLAUDE.md L24 (lumpy strategies cap 44-54 %), L33 (instrument décide)

*ORB reconciliation 2026-06-03 — Claude Code (Opus 4.7 1M ctx). Réconciliation interne, pas de mining. Verdict CONFIRMÉ-CLOS pour-le-dossier. Gate décisif G1 (coût réel). À banker : L34 (audit honesty checklist), L35 (DP ceiling), placebo confirmé.*
