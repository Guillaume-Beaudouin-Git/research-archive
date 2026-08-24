# Audit méthodologique — G1 carry G10 conditionnel

**Date** : 2026-05-26
**Auditeur** : Claude Code (effort max, aucune complaisance)
**Rapport audité** : `report_v1.md` — "Viabilité retail 2026 d'un FX carry trade G10 conditionné par régime macro"
**Standard** : CLAUDE.md constitution (L1-L23b, RESEARCH METHODOLOGY, hard rules, research history)

---

## Verdict global : REVISE

**Le verdict du rapport (tuer G1) RÉSISTE à l'audit.** Plusieurs lignes de preuve
indépendantes convergent vers l'impossibilité retail 2026 — la conclusion n'est pas
fragile. Cependant, **5 gaps méthodologiques majeurs** empêchent la conformité
constitutionnelle et 2 d'entre eux sont des deal-breakers sur le protocole proposé :

1. **AMTP + n_tests budget complètement absents** (constitution : "Excess returns, HAC
   lag-6, AMTP if n_tests > 1" ; hard rule).
2. **Seuil HAC 1.96 vs constitution 2.5** dans le protocole : tout test qui passerait
   1.96 mais échouerait 2.5 serait archivé selon le standard officiel.
3. **Budget n_tests FX non audité** : FX-1→FX-4 déjà dépensé sur carry G10 (research
   history) — le limit de 3 modifications par hypothèse n'est pas vérifié avant G1.
4. **Macrosynergy Sharpe 0.67-0.78 transféré tel quel** depuis un univers 24+ devises
   vers G10-only sans quantification de la dégradation.
5. **Proxy VXY >0.90 corrélation non sourcée** — claim empirique non instrumenté.

Ces issues sont **révisables sans changer la conclusion**. Corriger le protocole (seuil
2.5, AMTP, WF) et les claims non instrumentés renforcerait le dossier d'archivage G1,
pas l'inverserait.

---

## Sévérité des fragilités

| ID | Description courte | Sévérité | Section(s) impactée(s) | Action requise |
|----|--------------------|-----------|-----------------------|----------------|
| **F9** | AMTP + n_tests budget absents | **Deal-breaker** | TL;DR, Protocol, tout | Ajouter n_tests count, AMTP p-value |
| **F12** | Seuil HAC 1.96 vs constitution 2.5 | **Deal-breaker** | Protocol Step 2 | Corriger à t > 2.5 |
| **F3b** | Budget FX-1→FX-4 + 3-mod limit non vérifié | **Deal-breaker** | TL;DR, Recs | Vérifier avant toute ouverture G1 |
| **F7** | Macrosynergy SR 0.67-0.78 sans haircut G10-only | **Major** | Details 1a, Recs G2B | Quantifier dégradation ou caveat explicite |
| **F1** | Cost gate sans décomposition IR formelle | **Major** | Details 3, 4 | Ajouter IC × √breadth ; vérifier 3× gate |
| **F5** | Endogénéité VXY identifiée, non résolue | **Major** | KF4, Caveat 4 | Proposer proxy non-endogène ou conclure "aucun disponible retail" |
| **F6** | Corrélation VXY proxy >0.90 non sourcée | **Major** | Details 5b | Source ou recalifier "estimation" |
| **F11** | WF ≥5 folds absent du protocole (hard rule) | **Major** | Protocol | Ajouter Step 4 obligatoire si Steps 1-3 PASS |
| **F2** | L16 n'existe pas ; concern G10 momentum mort valide | **Minor** | Recs G2A | Remplacer "L16" par ref research history |
| **F3a** | L16 n'existe pas ; REER finding partiellement mitigé | **Minor** | Recs G2B | Remplacer "L16" par ref research history |
| **F8** | Seuil 0.25 vs RESEARCH_PASS 0.7 non réconcilié | **Minor** | Protocol Step 3 | Labeler comme pre-filter, non critère final |
| **F10** | Corrélations portfolio théoriques, outil non cité | **Minor** | Section 7 | Référencer Portfolio/risk/correlation.py |
| **F13** | Vol proxy 21d peut inclure T-day (T-1 rule) | **Minor** | Details 2d | Clarifier lag |
| **F4** | Tension L15 vs empirique (faux positif audit) | **Résolu** | n/a | L15 et résultat empirique alignés — aucune action |

---

## Audit section par section

### TL;DR

**Claim** : "Sharpe nets espérés : personal book Dukascopy ECN ≈ 0.15–0.30 ; OANDA ≈ ≤ 0.0 ; EV(challenge) négative."

**Standard** : Hard rules : "Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1."

**Verdict** : NEEDS_REVISION (F9)

**Justification** : Les Sharpe nets sont dérivés des Sharpe gross littérature + soustraction coût, sans mention que les figures littérature sont bien sur excess-return basis. Plus grave : n_tests n'est pas cité. Si ce rapport est enregistré avec 1 test (baseline carry conditionnel) + 2 variations (VXY filter, Fed filter), n_tests global passe de 321 à 324, et le protocole en 3 étapes consomme au minimum 3 sous-hypothèses → AMTP obligatoire selon la constitution.

**Révision** : Ajouter en TL;DR : "n_tests dépensés par ce rapport : +3 (baseline + VXY + Fed). Budget global FX : vérifier vs FX-1→FX-4 + L23-closure."

---

**Claim** : "Alternatives carry-adjacentes prometteuses (à instruire en G2 dédié) : (a) carry × momentum hybride AMP 2013, Sharpe net retail estimé 0.35–0.55 ; (b) carry valuation-adjusted Macrosynergy, Sharpe net retail estimé 0.30–0.45."

**Standard** : Research history (CLAUDE.md) : "CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)". Methodology toolkit : "require gross > 3×cost_drag."

**Verdict** : NEEDS_REVISION (F2, F7)

**Justification** : Le Sharpe net 0.35–0.55 pour G2A (AMP 2013) suppose que le momentum G10 FX est vivant. Or la constitution archive explicitement "CS momentum, TSMOM G10: dead post-Menkhoff". Si le momentum FX est IC≈0, additionner carry + momentum produit carry + bruit, pas carry + diversification. L'argument AMP ne se transfère pas mécaniquement de cross-asset à G10-FX-only sans vérification IC momentum G10 post-2010.

**Révision** : Conditionner la recommandation G2A sur un IC test momentum G10 préalable. Citer research history.

---

### Key Finding 1

**Claim** : "Le carry G10 inconditionnel est mort post-2010. Accominotti et al. 2021 : SR as high as 1.08 before GFC and drops to only 0.25 after. Macrosynergy : 'around 80 % of all value generation took place in the 2000s'."

**Standard** : Methodology toolkit : "FX carry regime-dependence: 2005-2007 pre-GFC drives all G10 carry IC. Always check per-decade IC breakdown before calling carry feasible."

**Verdict** : PASS

**Justification** : Le rapport passe explicitement le per-decade breakdown (pre-GFC vs post-GFC). La citation de Macrosynergy "80% in the 2000s" et d'Accominotti et al. sur le SR pre-GFC/post-GFC est exactement ce que la constitution exige. C'est la section la plus solide du rapport.

---

### Key Finding 2

**Claim** : "Dupuy 2021 : augmented strategy only exhibits a small, insignificant increase in the Sharpe ratio from 0.45 to 0.53. Macrosynergy : volatility adjustment 'delivered a slightly lower Sharpe ratio over the past 20 years'."

**Standard** : L15 (CLAUDE.md) : "Regime overlays on high-Sharpe (SR>1.0) strategies: sub-threshold lift (~1.7%/yr, Δ=+0.022%/day). Only useful for strategies with MaxDD>20%."

**Verdict** : PASS (F4 — résolu)

**Justification** : L15 stipule "sub-threshold lift" pour les régime overlays, ce qui est exactement cohérent avec "small, insignificant increase" de Dupuy. L'audit prompt supposait une contradiction entre L15 ("overlay DEVRAIT aider sur SR<1.0") et les résultats empiriques — mais cette lecture est incorrecte. L15 s'applique aux stratégies SR>1.0 et décrit la lift comme "sub-threshold". Pour SR<1.0 (carry G10 post-2010 ≈ 0.25), L15 ne prédit pas un gain significatif, seulement que l'overlay peut être utile si MaxDD>20%. La lift sub-threshold de Dupuy (0.45→0.53, non significative) est COHÉRENTE avec L15. Pas de contradiction, pas de révision nécessaire.

---

### Key Finding 3

**Claim** : "Filtrage Fed stance (Bauer-Swanson 2023) : coefficient pente négatif et non-significatif sur 2021-2022 (Yoldas Fed FEDS Note mai 2024). Canal carry/UIP partiellement rompu."

**Standard** : Hard rule #1 : "Signal at T-1, trade at T. No exceptions." ; methodology toolkit HAC lag-6.

**Verdict** : PASS

**Justification** : La citation de Yoldas est précise et contemporaine (2024). La reconnaissance que le canal UIP est rompu sur le cycle de tightening est cohérente avec les observations empiriques et ne viole aucun standard.

---

### Key Finding 4

**Claim** : "Le crash du 5 août 2024 : le conditionnement vol n'a PAS évité ce crash car l'unwind carry CAUSE le spike de vol (endogénéité fatale au filtre VXY-percentile)."

**Standard** : Aucun L spécifique ; constitutionnellement, toute fragilité structurelle doit être identifiée ET résolue ou déclarée non-résolvable.

**Verdict** : NEEDS_REVISION (F5)

**Justification** : Le rapport identifie correctement l'endogénéité (VXY_t est endogène au carry_unwind_t) et la confirme empiriquement avec le 5 août 2024. Mais s'arrête là. La constitution n'exige pas de proposer une solution, mais si aucun proxy non-endogène n'est accessible retail (credit spread HY-IG via VIX ? CFTC positioning via COT public ? 3M-OIS basis via FRED ?) l'audit exige de le conclure explicitement et de mesurer la charge que cela impose sur le verdict. Le Caveat 4 reprend partiellement ce point mais sans conclusion formelle.

**Révision** : Ajouter en KF4 : "Aucun proxy non-endogène accessible retail identifié ([vérifier COT JPY, FRED 3M-OIS, VIX vs JPMVXYG7]). L'endogénéité est donc structurellement non-mitgeable retail → argument additionnel pour l'archivage G1."

---

### Key Finding 5

**Claim** : "Coûts retail Dukascopy ECN tolérable, OANDA spread-only prohibitif. Dukascopy : EUR/USD 0.3-0.4 pip + $3.5 RT/lot. OANDA : EUR/USD 1.4 pip, NZD/USD 1.7 pip — équivalent 300-450 bps annualisés."

**Standard** : Methodology toolkit : "IC → net Sharpe (Israel-Jiang-Ross 2017): expected_gross_alpha ≈ 0.40 × IC × √breadth × σ_target; require gross > 3×cost_drag."

**Verdict** : NEEDS_REVISION (F1)

**Justification** : Le rapport calcule correctement le drag annualisé (80-120 bps Dukascopy + 100-200 bps swap = 180-320 bps/an) mais ne fait pas le pré-vol formel Israel-Jiang-Ross. Vérification analytique :

```
IC_implied = SR_gross / √breadth
           = 0.53 / √(7 × 12)  # 7 paires × 12 mois = breadth 84
           = 0.053

gross_alpha = 0.40 × IC × √breadth × σ_target
            = 0.40 × 0.053 × 9.17 × 10%
            = 1.94 % /an

Mais : si SR_gross = 0.53 et σ_target = 10%, alors gross_alpha = 5.3%/an directement.
La décomposition IR via 0.40 factor donne 1.94% ≠ 5.3% — divergence.
```

La divergence vient du fait que le facteur 0.40 dans la formule IR est une réduction pour impact de marché implicitement supposée dans la formule académique ; pour un carry mensuel avec impact quasi nul, ce facteur est une surestimation du haircut. L'application directe `SR × σ = gross_alpha` est plus correcte ici.

Vérification du 3× gate :
- `gross_alpha = 0.53 × 10% = 530 bps`
- `cost_drag = 180-320 bps/an`
- `3 × cost_drag = 540-960 bps`
- `ratio = 530 / 540 à 530 / 960 = 0.98 à 0.55`
- **Gate 3× : FAIL dans tous les cas** (sous 1.0 même pour coûts minimaux)

**C'est l'argument kill le plus fort et il n'est pas explicité dans le rapport.** Le rapport conclut "Sharpe net 0.15-0.30, insuffisant" par soustraction arithmétique — correct mais moins percutant que le 3× gate FAIL qui est une règle constitutionnelle formelle.

**Révision** : Ajouter en Section 4d (ou équivalent) :
```
3× gate (Methodology Toolkit) : gross > 3 × cost_drag
gross_alpha = SR_gross_optimal × σ_target = 0.53 × 10% = 530 bps/an
3 × cost_drag (Dukascopy best case) = 3 × 180 = 540 bps/an
Ratio = 530/540 = 0.98 → FAIL (seuil ≥ 1.0)
3 × cost_drag (OANDA) = 3 × 450 = 1 350 bps/an → ratio 0.39 → FAIL massif
```

---

### Key Finding 6

**Claim** : "Swap broker asymétrique retail = killer sous-estimé. NZD/USD long −2.42%/short +0.31% ; USD/CHF long +2.82%/short −4.92%."

**Standard** : Aucun L spécifique. Methodology toolkit : "require gross > 3×cost_drag."

**Verdict** : PASS

**Justification** : Le rapport identifie correctement un coût structurel absent des études académiques (Burnside et al.) car celles-ci n'utilisent que le bid-ask spot. La quantification via OANDA février 2026 est sourcée et précise. C'est une contribution originale du rapport.

---

### Key Finding 7

**Claim** : "Propfirm-fit : techniquement permis, économiquement perdant. DD attendu 15-25% vs max-loss 6-10% → EV challenge négative."

**Standard** : L22 (CLAUDE.md) : "MC propfirm eval simulation mandatory before any propfirm purchase. Four findings: (b) consistency cap is binding... (d) Gaussian generator materially overestimates bust."

**Verdict** : NEEDS_REVISION (minor)

**Justification** : L22 exige une simulation MC calibrée avant tout jugement propfirm. Le rapport conclut "EV négative" par argument qualitatif (DD attendu 15-25% > max-loss 6-10%) sans simulation MC trade-based. La conclusion est probablement correcte mais n'est pas instrumentée selon le standard constitutionnel.

**Révision** : Mention en KF7 : "Simulation MC (trailing_dd_simulator.py) non lancée car verdict kill décidé en amont ; la simulation est recommandée uniquement si les gates literature-level passent."

---

### Key Finding 8

**Claim** : "L'hybride carry × momentum AMP 2013 reste l'alternative robuste : corrélation carry/momentum ≈ −0.50/−0.60, combinaison réduit la variance. Recommandé comme Strategy G2."

**Standard** : Research history : "CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)."

**Verdict** : FAIL (F2)

**Justification** : La recommandation G2A repose sur AMP 2013 qui démontre la diversification carry × momentum cross-asset. Mais le rapport transpose ce résultat à G10 FX spécifiquement avec `signal = 0.5 × rank(carry) + 0.5 × rank(12-1 momentum spot)`. Or la constitution archive "CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)". Si IC(momentum G10 spot) ≈ 0 post-2010, la combinaison avec carry ne produit pas de diversification — elle additionne carry + bruit. L'argument AMP tient cross-asset (actions, obligataires, matières premières, FX) mais le momentum FX alone est mort. Le rapport n'instrumente pas l'IC momentum G10 post-2010 avant de recommander G2A.

Note : l'audit prompt supposait que L16 = "G10 momentum dead post-Menkhoff". **L16 n'existe pas dans la constitution.** Cependant la finding est bien constitutionnellement registrée dans le Research History. Conséquence : le standard applicable est Research History (pas un L numéroté), mais la fragilité est identique.

**Révision** : Conditionner G2A sur : "Step 0 G2A : tester IC(12-1 momentum spot, G10, 2010-2025) avec HAC t > 2.5. Si IC ≈ 0 ou wrong direction → G2A invalide, G2B devient seule option ou G2 → tuer."

---

### Details 1a — État de la preuve

**Claim** : "Macrosynergy Advanced FX carry valuation-adjusted : Sharpe unadjusted 0.48, valuation-adjusted 0.67–0.78, sur 24-year sample."

**Standard** : Aucun L spécifique. Hard rules RESEARCH_PASS (Sharpe>0.7).

**Verdict** : NEEDS_REVISION (F7)

**Justification** : Les Sharpe Macrosynergy 0.67–0.78 sont sur un univers de 24 devises incluant les marchés émergents. Le rapport limite l'univers retail à 8 devises G10 (section 2a). Deux problèmes :
1. La dégradation G10-only vs 24 devises n'est pas quantifiée. La valeur ajoutée du signal valuation-adjusted sur EM (où le REER gap et les déséquilibres réels sont plus grands) est probablement supérieure à celle sur G10.
2. Les données JPMaQS que Macrosynergy utilise ne sont pas disponibles retail (accès stage/hedge fund uniquement, mentionné en Recommandations sans quantifier l'impact sur le Sharpe).

**Révision** : Ajouter caveat sur le SR Macrosynergy : "Valeurs obtenues sur 24 devises dont ~6-8 EM à spread carry élevé. Sharpe G10-only estimé [X.XX ± incertitude] — non quantifiable sans test empirique. Haircut a minima 20-30% du gain conditionnel vs univers 24."

---

### Details 2d — Filtre régime VXY proxy

**Claim** : "Corrélation avec JPMVXYG7 historiquement > 0.90 sur 2010-2024."

**Standard** : Hard rules : tout claim empirique non sourcé → requalifier "estimate" ou sourcer.

**Verdict** : FAIL (F6)

**Justification** : Cette corrélation est affirmée sans source académique ni backtest maison. La construction du proxy est précisée (panier 6 paires, pondérations BIS Triennial 2022, EWMA 21j) mais le chiffre 0.90 est non instrumenté. JPMVXYG7 n'étant pas accessible retail (Bloomberg seulement), la corrélation ne peut être vérifiée par le lecteur.

**Révision** : Remplacer ">0.90" par "[corrélation estimée, non vérifiée vs JPMVXYG7 non accessible retail ; proxy utilisé faute de mieux ; VIX comme backup (corrélation ≈ 0.75, cité dans section 5b)]". Le VIX correlation de 0.75 est lui-même non sourcé mais au moins cohérent avec la pratique académique.

---

### Details 2c/2d — Signal at T-1, trade at T

**Claim** : Le proxy VXY utilise `std(log_r_21d)` sur les paires G10, calculé sur 21 jours glissants.

**Standard** : Hard rule #1 : "Signal at T-1, trade at T. No exceptions."

**Verdict** : NEEDS_REVISION (F13, minor)

**Justification** : Si la vol 21j est calculée en incluant le jour T de rebalancement, le signal contient de l'information du jour T → violation de la règle T-1. Pour le carry signal (FRED 3M interbank avec latence 1 mois) ce problème ne se pose pas (signal est T-1 par construction). Mais le proxy vol doit être calculé sur `[T-22, T-1]`, pas `[T-21, T]`.

**Révision** : Préciser dans le pseudo-code section 2d : `vol_proxy = ... .shift(1)` ou calculé sur `[T-22, T-1]`.

---

### Details 4 — Coûts retail et propfirm-fit

**Claim** : "Total drag annualisé rotation mensuelle Dukascopy : ~80-120 bps/an ; swap asymétrique −100 à −200 bps/an."

**Standard** : COSTS (CLAUDE.md) : "Crypto: 0.17% | Futures MNQ: ~$2.15 RT | FX: 0.15% | Commodity futures: 0.015%"

**Verdict** : PASS

**Justification** : FX cost est calibré à 0.15% RT dans la constitution. 80-120 bps/an pour rotation mensuelle sur 7 paires = ~(90 bps/12 mois × 7 paires × 2) / 7 ≈ 12 bps/trade RT → 0.12% RT. Cohérent avec le standard constitutionnel 0.15% FX. Le haircut swap est une addition correcte absent des coûts FX de base.

---

### Details 5b — Données VXY

**Claim** : "JPM VXY (Bloomberg ticker JPMVXYG7:US) : non accessible API gratuite."

**Standard** : Vérité factuelle, aucun L applicable.

**Verdict** : PASS

---

### Details 6a — Publication effect

**Claim** : "Brunnermeier-Nagel-Pedersen 2008 (~4 000 citations) et MSSS 2012 ont rendu publiques les conditions de carry crashes. Macrosynergy : 'almost no positive PnL contribution since 2010'."

**Standard** : Methodology toolkit : "IC → net Sharpe... require gross > 3×cost_drag" + research history "dead post-GFC".

**Verdict** : PASS

**Justification** : La thèse de dégradation post-publication est solidement instrumentée par deux sources indépendantes. Cohérent avec la constitution qui archive le carry G10.

---

### Details 6c — Convergence carry/momentum

**Claim** : "AMP 2013 : corrélation value/momentum ≈ −0.50/−0.60 across asset classes."

**Standard** : Research history : "CS momentum, TSMOM G10: dead post-Menkhoff."

**Verdict** : FAIL (F2, répétition)

**Justification** : La corrélation cross-asset −0.50/−0.60 est documentée pour un univers multi-asset (actions, obligations, matières premières, FX multi-devises). Elle n'implique pas que momentum G10 FX isolated produit un IC positif. Le G2A recommandé est une extrapolation d'un résultat cross-asset vers un sous-ensemble (G10 FX) dont la constitution archive l'IC momentum comme mort.

---

### Details 7 — Décorrélation vs portfolio

**Claim** : "B (HL carry) : +0.30 à +0.50 théorique. C (NQ ORB) : ~0. F2 (Asian range) : +0.05 à +0.20."

**Standard** : Aucun L applicable. Portfolio/risk/correlation.py existe.

**Verdict** : NEEDS_REVISION (F10)

**Justification** : Toutes ces corrélations sont théoriques. Le rapport lui-même dit "À vérifier empiriquement avant ajout au portfolio." La constitution dispose de `Portfolio/risk/correlation.py` pour cet usage exact. Le rapport ne suggère pas son utilisation.

**Révision** : Ajouter : "Empirical check : si Steps 1-3 du protocole passent, lancer `Portfolio/risk/correlation.py` avec returns carry G10 simulés vs returns B, C, F2. Corrélation empirique > 0.60 avec B → G1 invalide pour portfolio (diversification marginale)."

---

### Recommendations — Protocole 3 étapes

**Claim** : "Étape 2 — Critère pass : Sharpe gross conditionnel > 0.40 ET t-stat HAC > 1.96."

**Standard** : Methodology toolkit : "Significance: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC feasibility."

**Verdict** : FAIL (F12 — Deal-breaker)

**Justification** : La constitution fixe le seuil d'IC feasibility à t > 2.5. Utiliser t > 1.96 baise le bar à ~5% α (bilatéral) au lieu de ~1.3% α. Or FX strategies avec n_tests > 1 requièrent correction AMTP, qui élève encore le seuil effectif. Un résultat qui passe 1.96 mais échoue 2.5 serait archivé selon les standards constitutionnels. Le protocole est sous-exigeant sur le critère critique de significativité.

**Révision** : Remplacer "t-stat HAC > 1.96" par "t-stat HAC > 2.5 (seuil IC feasibility, CLAUDE.md Methodology Toolkit)".

---

**Claim** : "Étape 3 — Critère final : Sharpe net > 0.25 ET MaxDD < −15%."

**Standard** : RESEARCH_PASS (CLAUDE.md) : "Sharpe>0.7, MaxDD<-25%, WF>50%". Hard rule : "Walk-forward ≥5 folds — never single split."

**Verdict** : NEEDS_REVISION (F8, F11)

**Justification** : Deux problèmes distincts :

1. **Threshold 0.25 vs RESEARCH_PASS 0.7** : Le critère "Sharpe net > 0.25" est un pre-filter de faisabilité, pas le critère de validation final. Présenté comme "critère final", il crée l'ambiguité qu'une stratégie passant 0.25 net serait validée — or elle échouerait RESEARCH_PASS (0.7) immédiatement après. Le protocole devrait être labellisé "feasibility gate pré-WF, non critère de validation".

2. **Walk-forward absent** : La constitution stipule "Walk-forward ≥5 folds — never single split." Le protocole 3 étapes ne comporte aucun step WF. C'est une violation de hard rule si le protocole est utilisé comme validation (et non uniquement comme IC feasibility screen). La mention "scoping strictement académique" atténue le problème mais ne suffit pas constitutionnellement.

**Révision** : Renommer l'étape 3 "feasibility gate" et ajouter :
```
Step 4 (obligatoire si Steps 1-3 PASS) — Walk-forward ≥5 expanding folds
Critère WF : WF > 50% (RESEARCH_PASS), >60% (PROPFIRM_PASS)
Critère Sharpe WF moyen : > 0.7 net (RESEARCH_PASS)
```

---

**Claim** : [Absence de discussion n_tests et AMTP dans tout le protocole]

**Standard** : Hard rule : "Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1." AMTP est exigé dès n_tests > 1.

**Verdict** : FAIL (F9 — Deal-breaker)

**Justification** : Le protocole 3 étapes teste au minimum :
- Test 1 : carry G10 inconditionnel (baseline)
- Test 2 : carry G10 + VXY filter
- Test 3 : carry G10 + Fed filter
- Test 4 : carry G10 + VXY + Fed combinés

n_tests = 4 pour ce protocole seul. Global : 321 → 325+. La constitution exige AMTP à partir de n_tests > 1. Le protocole ne mentionne ni n_tests ni p-value AMTP corrigée. Pour n_tests = 4 (Bonferroni simple), le seuil α effectif par test = 0.05/4 = 0.0125 → t critique ≈ 2.50 (se retrouve par hasard proche du seuil constitutionnel). Mais l'absence totale de discussion AMTP est une violation formelle.

**Révision** : Ajouter en tête du protocole :
```
n_tests consommés par ce protocole : 4 (baseline + VXY + Fed + combiné)
Budget FX total : 180 (historical) + 4 = 184 → vérifier cohérence vs n_tests global
AMTP (Bonferroni conservative) : seuil par test α = 0.05/4 = 0.0125 → t ≥ 2.50
```

---

### Caveats

**Caveat 1** (survivorship et look-ahead) — PASS. Bien identifié.

**Caveat 2** (absence de paper post-2018 G10-only avec VXY discret rigoureux) — PASS. L'absence de preuve directe est correctement signalée comme limitation.

**Caveat 3** (swap broker retail sous-estimé en littérature) — PASS. Critique originale et correcte.

**Caveat 4** (endogénéité VXY) — NEEDS_REVISION (F5, répétition). Identifié sans résolution. Ajout requis : "Aucun proxy non-endogène accessible retail identifié."

**Caveat 5** (dataset Bauer-Swanson latence trimestrielle) — PASS.

**Caveat 6** (spreads NOK/SEK non vérifiés) — PASS. Honnête.

**Caveat 7** (propfirm = simulated accounts post-2025) — PASS. Utile.

**Caveat 8** (valeur pédagogique même sur stratégie morte) — PASS. Pertinent.

**Caveat 9** (confusion JPMorgan vs BIS sur taille carry trade yen) — PASS.

---

## Fragilités additionnelles (hors F1-F10)

### F11 — Walk-forward absent du protocole [Major]
**Constitution** : "Walk-forward ≥5 folds — never single split."
Le protocole en 3 étapes constitue une validation incomplète : même si Steps 1-3 passent, aucun WF n'est prévu. Le protocole se présente comme "scoping strictement académique" mais sans Step 4 WF explicite, un lecteur non averti pourrait le considérer suffisant. Voir Revision en section Recommendations.

### F12 — HAC threshold 1.96 vs 2.5 [Deal-breaker]
**Constitution** : "Significance: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC feasibility."
Le protocole Step 2 utilise t > 1.96. Voir Revision en section Key Finding 8 et Recommendations.

### F13 — Proxy vol T vs T-1 [Minor]
**Constitution** : "Signal at T-1, trade at T. No exceptions."
Le pseudo-code section 2d calcule `vol_proxy = std(log_r_21d)` sur fenêtre glissante sans préciser le lag. Si la fenêtre inclut le jour T, violation de la hard rule. Voir Revision en section Details 2d.

### F14 — FX n_tests budget et 3-mod limit non audités [Deal-breaker]
**Constitution** : "Max 3 modifications per strategy hypothesis." Research history : "G10 carry (FX-1 to FX-4): dead post-GFC."

Les strategies FX-1 à FX-4 ont consommé 4 tests sur la famille carry G10. Selon l'hypothèse que FX-1 = carry inconditionnel de base, les modifications FX-2, FX-3, FX-4 représentent déjà 3 modifications. G1 (carry conditionnel) serait une **4ème modification**, au-delà du budget constitutionnel de 3.

Ce point n'est ni adressé ni même mentionné dans le rapport. Si FX-1→FX-4 sont des hypothèses indépendantes (pas des modifications de la même hypothèse), le budget est intact. Mais si FX-1 = plain carry et FX-2/FX-3/FX-4 = variations du carry, le budget est épuisé.

**Révision** : Clarifier la structure FX-1→FX-4 dans le research history avant toute ouverture G1. Si FX-1 = plain carry G10 et FX-2, FX-3, FX-4 = modifications (e.g., with momentum, with REER, with vol filter), alors G1 conditionnel est modification #4 → **interdit constitutionnellement sans ouverture d'une nouvelle hypothèse dédiée**.

---

## Implications pour la décision G1 archive vs run protocole

### Conclusion : ARCHIVE G1 IMMÉDIATEMENT

Les fragilités majeures ne sont pas solubles de manière à rendre G1 viable. L'analyse de robustesse est claire :

1. **3× gate FAIL (F1)** : gross_alpha = 530 bps, 3× cost_drag (Dukascopy best) = 540 bps → le carry G10 conditionnel échoue le gate constitutionnel même avec des coûts minimaux. Fixing F1 (ajouter la décomposition IR) ne sauve pas la stratégie — elle la tue plus formellement.

2. **AMTP aggrave le verdict (F9)** : avec 4 tests dans le protocole, le seuil effectif α/4 ≈ 0.0125 correspond à t ≈ 2.5 — le carry conditionnel ne passe pas ce gate (Dupuy 2021 Sharpe 0.45→0.53 est explicitement insignificant).

3. **Budget FX potentiellement épuisé (F14)** : si FX-1→FX-4 = 4 tests sur la même famille hypothèse, G1 est interdit par la règle 3-modifications.

4. **Endogénéité non résolvable retail (F5)** : le seul mécanisme potentiellement résolvable (CFTC COT, credit spread) n'est pas instrumenté dans le rapport mais est probablement accessible retail. Mais même si un proxy non-endogène existait, le 3× gate FAIL reste.

**Le protocole 3 étapes peut cependant être maintenu à titre pédagogique** (Caveat 8 du rapport) à condition de corriger les deux deal-breakers (AMTP et threshold 2.5) et d'ajouter Step 4 WF. La valeur est l'apprentissage du processus, pas la validation de la stratégie.

### Fragilités résolubles sans impact sur le verdict kill

- F6 (sourcer VXY proxy) → ne change pas la conclusion
- F7 (G10-only haircut sur Macrosynergy) → uniquement renforce le KILL
- F8 (threshold 0.25 vs RESEARCH_PASS) → clarification, pas changement de conclusion
- F10 (référencer correlation.py) → outil existe, ne change rien
- F11 (ajouter WF en Step 4) → renforce le protocole mais la stratégie killa déjà avant WF
- F12 (t 1.96→2.5) → relève encore plus le bar, tue plus vite
- F13 (vol proxy lag) → correction technique, pas d'impact sur verdict

---

## Implications pour le pivot G2

### G2A — Carry × Momentum hybride AMP 2013

**Validité conditionnelle.** Le pivot G2A repose sur deux hypothèses :

1. **IC(momentum G10 FX, 2010-2025) > 0** — non vérifiée et contredite par research history.
2. **Corrélation carry × momentum ≈ −0.5 sur G10 spécifiquement** — documentée cross-asset (AMP 2013) mais non testée G10-only post-2010.

**Verdict sur G2A** : Invalide tel que présenté. La combinaison carry + momentum FX G10 ne peut pas être recommandée sans instrumentation préalable de l'IC momentum G10 post-2010. L'argument "corrélation −0.50" vient d'un papier multi-asset ; l'extrapolation à G10 FX seul est non instrumentée. Research history dit explicitement "CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)".

**Alternative** : Si G2A doit être testé, la gate entry doit être :
```
Step 0 G2A (1 semaine, 0 coût data) :
- Télécharger G10 spot data (Dukascopy gratuit depuis 2003)
- Calculer IC(12-1 momentum spot, rendements mois+1, 2010-2025) avec HAC t
- Gate : IC t > 2.5 ET IC > 0 → proceed G2A
- Si IC ≤ 0 ou t ≤ 2.5 → G2A invalide, kill
```

### G2B — Carry valuation-adjusted Macrosynergy

**Partiellement valide, sous conditions sévères.** 

L'audit prompt supposait que "L16 = BIS REER ≠ bilateral USD valuation" invalide G2B. **L16 n'existe pas dans la constitution.** Le finding est bien dans le research history : "BIS REER ≠ bilateral USD valuation: unsuitable as carry signal modifier." Mais ce finding porte sur l'utilisation du BIS REER comme *filtre ou modificateur carry* — mécanisme différent de l'ajustement valuation Macrosynergy qui mesure des *gaps PPP/REER* sur long horizon.

**Distinction mécanistique** :
- Finding archivé : BIS REER level ≠ signal pour carry bilatéral vs USD
- Macrosynergy G2B : gap(PPP_long_run − spot_rate) comme mesure d'over/undervaluation au-delà du carry nominal

Ces deux usages du REER sont différents. Le finding archivé ne tue pas directement G2B.

**Cependant deux problèmes subsistent** :
1. **Universe mismatch (F7)** : Sharpe 0.67-0.78 Macrosynergy est sur 24 devises dont EM ; G10-only degradation non quantifiée.
2. **Data retail vs JPMaQS** : Macrosynergy utilise les données JPMaQS propriétaires ; l'implémentation retail avec "OECD REER monthly (gratuit)" est un downgrade significatif dont l'impact sur le Sharpe n'est pas estimé.

**Verdict sur G2B** : Conditionnellement valide, mais avec Sharpe net attendu 0.30-0.45 (estimé rapport) probablement sur-estimé de 20-40% en G10-only retail. Sharpe net réel retail estimé 0.18-0.36 → sous RESEARCH_PASS (0.7). La piste est viable pédagogiquement mais l'espérance de passer RESEARCH_PASS est faible.

### Alternative G2 non proposée par le rapport

**G2C — Carry G10 avec hedging de la queue by options implicites (VXY-like) via VIX**

Le rapport identifie correctement l'endogénéité VXY comme le problème structurel central. Une alternative non adressée : acheter du VIX call spread (1-2% de carry budget/an) comme hedge tail-risk explicite plutôt que comme signal. Ce n'est pas du conditionnement — c'est du hedging du crash carry par instrument non-endogène. Faisabilité retail : CBOE mini VIX options ou SPX options courtes. Complexité élevée, hors scope solo retail $25k, mais conceptuellement sounder que le filtre VXY.

**Pourquoi non proposé** : coût du hedge (~100-200 bps/an) s'ajoute au drag déjà prohibitif. La stratégie coûterait 280-520 bps/an → ratio gross/cost aggravé. Donc non viable, mais mérite mention comme raison supplémentaire de tuer le carry G10 retail.

**G2D — Carry cross-asset (Koijen et al. 2018, JF)**

Koijen-Moskowitz-Pedersen-Vrugt (2018) montrent que carry works **across** asset classes (equity index, FX, bonds, commodity futures) même quand il est mort within FX. L'implémentation necessiterait des futures CME (bonds ZN, equity ES, commodity CL) + FX spot — infrastructure multi-asset accessible retail via IBKR. Ceci est une piste G2 non explorée dans le rapport, potentiellement plus robuste que G10 carry + momentum FX pur.

---

## Résumé des actions constitutionnelles

| Priorité | Action | Raison |
|----------|--------|--------|
| **Immédiat** | Archiver G1 sans lancer le protocole | 3× gate FAIL + AMTP + n_tests budget |
| **Avant G2A** | Tester IC(momentum G10, 2010-2025) avec HAC t > 2.5 | Research history dit "dead", vérification formelle requise |
| **Avant G2B** | Quantifier dégradation G10-only vs Macrosynergy 24-devises | SR 0.67-0.78 non transférable tel quel |
| **Si protocole pédagogique lancé** | Corriger threshold → 2.5, ajouter AMTP, ajouter WF Step 4 | Deal-breakers F9, F12, F11 |
| **Optionnel** | Clarifier structure FX-1→FX-4 dans research history | Budget 3-mod limit potentiellement épuisé |
